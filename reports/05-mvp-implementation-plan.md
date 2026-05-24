# MVP Implementation Plan

> 2-3 weeks total | Phase 1: DB+CLI (1 week) | Phase 2: Plugin Overlay (1-2 weeks)

## File Structure

### New Python Modules

```
paperforge/
├── annotation/                    ← NEW: annotation package
│   ├── __init__.py
│   ├── probe.py                  ← Zotero SQLite read-only parser
│   ├── db.py                     ← annotations.db connection + schema
│   ├── schema.py                 ← annotations.db DDL + migration
│   ├── import_annotations.py     ← import pipeline (Zotero → annotations.db)
│   └── export.py                 ← JSON / annotated PDF export
├── commands/
│   ├── annotation.py             ← `paperforge annotation` CLI
│   └── ...
├── memory/
│   └── ...                       ← unchanged (paperforge.db untouched)
└── services/
    └── sync_service.py           ← unchanged
```

### New TS Modules (Obsidian Plugin)

```
paperforge/plugin/src/
├── main.ts                       ← patched: add ribbon/cmd for annotation overlay
├── pdf-overlay/
│   ├── patch-pdf-viewer.ts       ← monkey-around patches
│   ├── overlay-layer.ts          ← overlay DOM management per page
│   ├── rect-renderer.ts          ← rect placement + color theming
│   ├── selection-handler.ts      ← text selection → annotation
│   ├── popover.ts                ← click annotation → edit comment/color
│   ├── annotation-fetcher.ts     ← execFile → paperforge annotation list
│   └── types.ts                  ← shared interfaces
└── testable.js                   ← extend
```

## New CLI Commands

```bash
# Import annotations from Zotero SQLite
paperforge annotation import
    [--zotero-db PATH]           # override auto-detected Zotero data dir
    [--copy-db]                  # copy zotero.sqlite to temp before reading
    [--paper KEY]                # specific paper only
    [--dry-run]                  # preview without writing
    [--json]

# List annotations for a paper
paperforge annotation list
    <paper_key>                  # zotero_key of the paper
    [--page N]                   # filter by page
    [--type TYPE]                # filter by type
    [--json]
    [--limit N]

# Create a local annotation
paperforge annotation create
    --paper KEY
    --type TYPE
    --page-index N
    [--page-label TEXT]
    [--selected-text TEXT]
    [--comment TEXT]
    [--color HEX]
    [--position JSON]
    [--sort-index TEXT]
    [--json]

# Update annotation
paperforge annotation patch
    <annotation_id>
    [--comment TEXT]
    [--color HEX]
    [--json]

# Soft delete annotation
paperforge annotation delete
    <annotation_id>
    [--hard]                     # permanent delete
    [--json]

# Export annotations
paperforge annotation export
    <paper_key>
    [--format json|markdown]     # default: json
    [--output PATH]
    [--json]

# Check annotation DB status
paperforge annotation status
    [--json]
```

## New DB Table (annotations.db)

See `reports/03-paperforge-schema-design.md` for full schema.

Key decisions:
- `sync_state` includes `pending_push` from day 1, even though v1 won't push
- `sync_queue` table is pre-defined for future Web API push
- FTS5 on `selected_text` + `comment` + `tags_json`
- Soft delete via `deleted_at`

## API Routes (for Plugin execFile interaction)

```
→ paperforge annotation list <key> --json
← {
    "ok": true,
    "data": {
        "paper_id": "ABCD1234",
        "annotations": [
            { id, type, page_index, selected_text, comment, color, position_json, ... }
        ],
        "count": 15
    }
}

→ paperforge annotation create --paper KEY --type highlight --page-index 3 --json
← {
    "ok": true,
    "data": { "id": "uuid-here", ... }
}
```

## Plugin ↔ Python Interaction

```typescript
// In annotation-fetcher.ts
import { execFile } from 'child_process';

async function fetchAnnotations(paperKey: string): Promise<Annotation[]> {
    const result = await runSubprocess(
        pythonExe,
        ['-m', 'paperforge', 'annotation', 'list', paperKey, '--json'],
        vaultPath,
        30000
    );
    return JSON.parse(result.stdout).data.annotations;
}

async function createAnnotation(paperKey: string, data: CreateAnnotationPayload): Promise<Annotation> {
    const args = [
        '-m', 'paperforge', 'annotation', 'create',
        '--paper', paperKey,
        '--type', data.type,
        '--page-index', String(data.pageIndex),
        '--selected-text', data.selectedText || '',
        '--comment', data.comment || '',
        '--color', data.color || '#ffd400',
        '--position', JSON.stringify(data.position),
        '--sort-index', data.sortIndex,
        '--json'
    ];
    const result = await runSubprocess(pythonExe, args, vaultPath, 10000);
    return JSON.parse(result.stdout).data;
}
```

## UI Interaction Flow

```
1. User opens PDF in Obsidian (native PDF viewer)
2. Plugin patches PDFViewerChild.loadFile() → fetches annotations from annotations.db
3. Plugin renders overlay rects on each page
4. User sees highlights/underlines/notes on PDF

User creates annotation:
  1. Select text in PDF (native text selection works)
  2. Plugin detects selection, shows "Add highlight" floating button
  3. User clicks → execFile → paperforge annotation create
  4. Plugin receives new annotation → adds to overlay immediately (optimistic)

User views annotation:
  1. Hover over highlight → tooltip shows comment
  2. Click → popover shows full annotation details
  3. If is_readonly=1 → show lock icon, no edit buttons
  4. If is_readonly=0 → show edit/delete buttons

User edits annotation:
  1. Click edit in popover → inline textarea
  2. Save → execFile → paperforge annotation patch
  3. Plugin updates overlay

Zotero annotations:
  - Imported with is_readonly=1, sync_state='zotero_synced'
  - Displayed with lock icon
  - First version: user reads them in PDF, cannot edit
```

## Not In MVP

| Feature | Reason |
|---------|--------|
| Zotero Web API write-back | Requires API key management, rate limiting, conflict UI |
| PDF file export with embedded annotations | Complex PDF manipulation, post-MVP |
| Ink annotation editing | Zotero's ink rendering is complex |
| EPUB annotation | Different position model (CSS selector) |
| Group library support | Zotero SQLite has different path resolution for groups |
| Multi-device sync | Out of scope for first version |
| Template-driven annotation notes | ZotFlow's feature, good but not required |

## Testing Strategy

### Python Tests
```bash
# Unit tests for annotation DB
python -m pytest tests/unit/test_annotation_db.py -v

# Integration test: probe Zotero SQLite
python experiments/zotero_annotation_probe.py --zotero-db fixtures/test_zotero.sqlite --limit 10

# CLI tests
python -m pytest tests/cli/test_annotation_commands.py -v
```

### JS Tests
```bash
# Unit tests for overlay components (no Obsidian dependency)
cd paperforge/plugin && npx vitest run

# Test: annotation-fetcher mock responses
# Test: coordinate transformation
# Test: rect placement logic
```

### Fixtures
```bash
fixtures/
├── test_zotero.sqlite          ← minimal Zotero SQLite with 1 paper + annotations
├── sample_annotations.json     ← known-good annotation JSON
└── sample_annotation_probe.json ← expected probe output
```

## Risk & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Zotero SQLite schema changes | Low | High | Schema version check; fail gracefully with clear error |
| Zotero running locks DB | Medium | Medium | Copy to temp before reading; detect lock errors |
| Obsidian PDF viewer internal API changes | High | Medium | version-gate patches; plugin auto-disables on major version mismatch |
| Monkey-patching conflicts with PDF++/other plugins | Medium | Low | Document conflicts; PaperForge checks for other patchers |
| Large annotations (500+) performance | Low | Medium | Rects merged per page; debounced rerender; cache computed positions |
