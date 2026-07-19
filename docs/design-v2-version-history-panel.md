# Design: Version History Panel (Phase 2a + 2b)

## Data Model

After #37 (backup), each paper's OCR directory looks like:

```
paper/ocr/{key}/
  render/
    fulltext.md              ← current version
    render-map.json
    heading-events.json
  versions/
    manifest.json            ← version index for this paper
    v1/                      ← pre-rebuild backup
      fulltext.md
      render-map.json
      heading-events.json
    v2/                      ← second rebuild backup
      ...
```

`versions/manifest.json`:
```json
{
  "versions": [
    {
      "label": "v1",
      "created_at": "2026-07-09T14:30:00+08:00",
      "source": "pre-rebuild",
      "renderer_version": "2.0.0",
      "structured_content_hash": "adbebf8c13e4e250",
      "fulltext_size": 42156,
      "pages": 3
    }
  ],
  "current": {
    "label": "v2",
    "created_at": "2026-07-10T10:00:00+08:00",
    "source": "rebuild",
    "renderer_version": "2.1.0",
    "structured_content_hash": "7f8e3a2b1c4d6e5f",
    "fulltext_size": 43892,
    "pages": 3
  }
}
```

## Entry Points

### 1. Maintenance Tab — Per Paper
Existing maintenance table adds a [版本历史] button for papers with backups.

### 2. Paper Mode — Dashboard  
In PaperForge ItemView's paper mode (`_renderPaperMode`), add [版本历史] button in the status strip area.

### 3. Dedicated Panel — New ItemView Mode
A new "versions" mode, accessible from:
- Maintenance tab header button: "版本历史 (N)"
- Paper dashboard [版本历史] button
- Command palette: "PaperForge: Open Version History"

## Panel Layout (File Recovery-inspired)

```
+--------------------------------------------------+
| <- Back   版本历史                                  |
+----------------+---------------------------------+
|                |  Glueck_2005_Osteolysis          |
|  filter papers |  -----------------------         |
|  +----------+  |  Versions                        |
|  | search.. |  |                                  |
|  +----------+  |  [v3] (current) 2026-07-10       |
|                |     43KB, renderer 2.1.0         |
|  Glueck_2005   |                                  |
|  v1 v2 v3      |  [v2]  (rebuild) 2026-07-09     |
|                |     42KB, renderer 2.0.0         |
|  Gao_2020      |      [restore] [compare]         |
|  v1            |                                  |
|                |  [v1] (original) 2026-06-01      |
|                |     38KB, OCR v1.5.15            |
|                |      [restore] [compare]         |
|                |                                  |
|                |  +-- Compare (v2 vs current) --+ |
|                |  | 2/15 paragraphs changed     | |
|                |  | Methods: restructured       | |
|                |  | Results: table format fix   | |
|                |  +------------------------------+ |
+----------------+---------------------------------+
| [restore selected]  [clear old versions (free N MB)] |
+------------------------------------------------------+
```

### UI States

| State | Display |
|---|---|
| No backups | "No version history available" |
| Single version | No compare, just restore |
| Multiple versions | Timeline + compare + single-select restore |
| Loading | Skeleton |
| Error | "Cannot read version data" + retry |

## Compare View (Paragraph-level Diff)

Block-level comparison using `block_id` from structured blocks (if available) or paragraph-level text diff.

```
+---------------------------------------+
| Compare: Glueck_2005                  |
| v2 (2026-07-09) vs current (2026-07-10) |
+---------------------------------------+
| Overview                               |
| -- Word count: 4250 -> 4310 (+60)     |
| -- Paragraphs changed: 2/15           |
| -- Figures/tables: unchanged          |
|                                        |
| +-- Changes ------------------------+  |
| | Introduction                      |  |
| |   block_4: background paragraph  |  |
| |   - The purpose of this study..  |  |
| |   + This study aimed to..        |  |
| |                                    |  |
| | Methods                           |  |
| |   block_12: statistics paragraph  |  |
| |   + We used SPSS version 26..     |  |
| +------------------------------------+  |
|                                        |
| [Restore this version]                  |
+---------------------------------------+
```

## Implementation Plan

### Phase 2a (#37): Backup (Python)

Modified files:
- `paperforge/worker/ocr_rebuild.py` — call `_backup_render_before_rebuild()` before phase 4
- New function in `paperforge/worker/ocr_versions.py`:
  - Check if `versions/manifest.json` exists
  - Copy render/ files to `versions/v{N}/`
  - Write/update `versions/manifest.json`
  - Returns version label (v1, v2, ...)

### Phase 2b (#38): Panel (TypeScript)

Modified files:
- `paperforge/plugin/src/views/dashboard.ts`:
  - New `_renderVersionMode()` method
  - Add [version history] button in `_renderPaperMode()`
  - Add mode switch case for "versions"
- New file `paperforge/plugin/src/services/version-history.ts`:
  - `scanVersionBackups(vaultPath, paperKey)` — read manifest.json
  - `listPapersWithBackups(vaultPath)` — scan all OCR dirs
  - `restoreVersion(vaultPath, paperKey, versionLabel)` — file copy
  - `compareVersions(vaultPath, paperKey, vA, vB)` — paragraph diff
- `paperforge/plugin/styles.css` — panel layout + timeline + diff view
- `paperforge/plugin/src/i18n.ts` — new localization strings

### Data Contract

The `versions/manifest.json` format is the contract between Python (backup) and TypeScript (display). Must match exactly.

## Decisions

- Comparison granularity: **paragraph-level diff** (not line-level)
- Version badge: NOT in search results (user rejected)
- Entry points: maintenance tab + paper dashboard + dedicated panel
