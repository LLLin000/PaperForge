# Architecture Research: v1.8 AI Discussion & Deep-Reading Dashboard

**Domain:** Obsidian plugin dashboard + Python CLI hybrid
**Researched:** 2026-05-06
**Confidence:** HIGH (verified against existing source code at `paperforge/plugin/main.js` and `paperforge/worker/asset_index.py`)

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Obsidian Plugin (JS/TS) — THIN SHELL          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              PaperForgeStatusView (_detectAndSwitch)        │  │
│  │   Mode Detection:                                           │  │
│  │     no file      → 'global'                                 │  │
│  │     .base file   → 'collection'                             │  │
│  │     deep-reading.md → 'deep-reading'    ←── NEW v1.8        │  │
│  │     .md + zotero_key → 'paper'                            │  │
│  │     .md other    → 'global'                                 │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  _renderGlobalMode()    │ _renderCollectionMode()          │  │
│  │  _renderPaperMode()     │ _renderDeepReadingMode() ← NEW   │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  _getCachedIndex() ──reads── formal-library.json           │  │
│  │  _renderDeepReadingMode ──reads── deep-reading.md         │  │
│  │                         ──reads── ai/discussion.json       │  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                     File System (Obsidian Vault)                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Literature/{domain}/{key} - {title}/                       │  │
│  │    ├── {key} - {title}.md          (formal note)            │  │
│  │    ├── deep-reading.md             (extracted from note)    │  │
│  │    ├── fulltext.md                 (OCR output)             │  │
│  │    ├── figures/                    (extracted charts)       │  │
│  │    └── ai/                         ←── v1.6 created         │  │
│  │         ├── discussion.json        ←── NEW v1.8 JS reads   │  │
│  │         └── discussion.md          ←── NEW v1.8 Python writes│  │
│  └────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                     Python CLI (paperforge)                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  paperforge/worker/sync.py     — generates deep-reading.md  │  │
│  │  paperforge/worker/asset_index.py — builds formal-library.json│ │
│  │  paperforge/skills/literature-qa/ld_deep.py — /pf-deep      │  │
│  │  paperforge/commands/context.py — AI context packs          │  │
│  │  [NEW] AI discussion recorder  — writes ai/discussion.*     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Owner | Modified in v1.8 |
|-----------|----------------|-------|------------------|
| `_detectAndSwitch()` | Active file → mode resolution | JS | **YES** — add `deep-reading.md` detection |
| `_switchMode()` | Dispatch to mode renderer | JS | **YES** — add `case 'deep-reading'` |
| `_renderDeepReadingMode()` | Deep-reading dashboard UI | JS | **NEW** — entirely new method |
| `_renderPaperMode()` | Per-paper dashboard | JS | **YES** — add "Jump to Deep Reading" button |
| `_buildEnvelope()` | Index envelope with version | Python | **YES** — add `paperforge_version` |
| `_fetchStats()` | Global dashboard data | JS | **YES** — read version from envelope |
| AI discussion recorder | Write `discussion.json` + `discussion.md` | Python | **NEW** — agent-level module |
| `ld_deep.py` / `/pf-deep` | Deep reading scaffold + validation | Python | No change |
| `sync.py` `migrate_to_workspace()` | Creates `ai/` directory | Python | No change (already done) |

## Mode Detection Flow (v1.8)

```
_detectAndSwitch()
    │
    ├─ activeFile === null ──────────────────────────→ 'global'
    │
    ├─ activeFile.extension === 'base' ──────────────→ 'collection'
    │
    ├─ activeFile.extension === 'md'
    │    │
    │    ├─ basename === 'deep-reading'               ←── NEW CHECK (BEFORE zotero_key)
    │    │    AND path matches workspace pattern
    │    │    │
    │    │    ├─ extract parent key from path → 'deep-reading'
    │    │    │   (Literature/{domain}/{key} - {title}/deep-reading.md)
    │    │    └─ set _currentDeepReadingKey, _currentDeepReadingEntry
    │    │
    │    └─ frontmatter has zotero_key ──────────────→ 'paper'
    │
    └─ fallback ────────────────────────────────────→ 'global'
```

**Critical ordering**: The `deep-reading.md` check must come BEFORE the generic `.md + zotero_key` check. Why: `deep-reading.md` is extracted from the formal note and may carry the same frontmatter (including `zotero_key`). We need to route it to the deep-reading dashboard, not the per-paper dashboard.

**Detection strategy**: Check `activeFile.basename === 'deep-reading'` AND verify the parent directory matches workspace naming pattern `{8-char key} - {slug}`. Extract the zotero_key from the parent directory name (first 8 characters before ` - `).

## deep-reading.md Detection — Integration Details

The detection needs to handle the workspace path structure:

```
Literature/{domain}/{zotero_key} - {title_slug}/deep-reading.md
```

```javascript
// Proposed addition to _detectAndSwitch(), inserted before the .md + zotero_key check:
if (ext === 'md' && activeFile.basename === 'deep-reading') {
    // Check if parent directory matches workspace pattern
    const parentDir = activeFile.parent ? activeFile.parent.name : '';
    const workspaceMatch = parentDir.match(/^([A-Z0-9]{8})\s+-\s+(.+)$/);
    if (workspaceMatch) {
        const extractedKey = workspaceMatch[1];
        this._currentPaperKey = extractedKey;
        this._currentPaperEntry = this._findEntry(extractedKey);
        this._currentDomain = null;
        this._switchMode('deep-reading');
        return;
    }
    // Not in a workspace dir — fall through to global
    this._switchMode('global');
    return;
}
```

## New: _renderDeepReadingMode() Component Design

### Data Sources
| Source | How Read | Fields Used |
|--------|----------|-------------|
| `formal-library.json` | `_findEntry(key)` via `_getCachedIndex()` | lifecycle, health, ocr_status, deep_reading_status, maturity, title, year, authors |
| `deep-reading.md` | `this.app.vault.getAbstractFileByPath()` → `read()` | Pass 1 summary, full text sections |
| `ai/discussion.json` | `fs.readFileSync()` (same pattern as index) | AI Q&A history, session metadata |

### Sub-Components
```
_renderDeepReadingMode()
    │
    ├─ [Status Bar] — inline row showing:
    │     lifecycle badge, ocr_status badge, deep_reading_status badge, maturity level
    │
    ├─ [Paper Info Header] — title, authors, year, domain
    │     (reuses existing _renderPaperMode header pattern)
    │
    ├─ [Pass 1 Summary Section] — "## 1. 第一遍：概览" content from deep-reading.md
    │     Rendered as formatted callout block
    │
    ├─ [AI Discussion History] — "## AI 问答记录" section
    │     ├─ discussion.json → rendered as Q&A accordion/cards
    │     │   Each session: model badge, timestamp, command, message pairs
    │     └─ Empty state: "No AI discussions yet. Use /pf-deep or /pf-paper in OpenCode."
    │
    └─ [Navigation] — "← Back to Paper" link
          Opens the formal note: this.app.workspace.openLinkText(entry.main_note_path, '')
```

### discussion.json Schema (Python → JS contract)

```json
{
  "format_version": "1",
  "zotero_key": "ABCDEFGH",
  "sessions": [
    {
      "session_id": "2026-05-06T143022",
      "timestamp": "2026-05-06T14:30:22+08:00",
      "model": "deepseek-v4-pro",
      "command": "/pf-deep",
      "summary": "三阶段精读：生物力学分析",
      "message_count": 12,
      "messages": [
        {
          "role": "user",
          "content": "/pf-deep ABCDEFGH",
          "timestamp": "2026-05-06T14:30:22+08:00"
        },
        {
          "role": "assistant",
          "content": "## Pass 1: 概览\n\n...",
          "timestamp": "2026-05-06T14:31:05+08:00"
        }
      ]
    }
  ]
}
```

**Design rationale**: Sessions array allows append-only writes. The `summary` field provides a one-line title for the dashboard card. `message_count` enables quick size display without parsing all messages. Individual messages are kept (not just summary) for potential future expand/collapse UI.

## Python vs JS Ownership Boundaries

| Concern | Python Owns | JS Owns | Rationale |
|---------|-------------|---------|-----------|
| Lifecycle computation | ALL (`compute_lifecycle`) | Reads result | Business logic stays in Python |
| Health computation | ALL (`compute_health`) | Reads result | Business logic stays in Python |
| Maturity computation | ALL (`compute_maturity`) | Reads result | Business logic stays in Python |
| Next-step recommendation | ALL (`compute_next_step`) | Reads result | Business logic stays in Python |
| `discussion.json` writing | ALL (agent commands) | Reads only | Agent interaction produces the data |
| `discussion.md` writing | ALL (agent commands) | Reads only | Human-readable companion to JSON |
| Deep-reading content | ALL (`ld_deep.py`, `sync.py`) | Reads via vault API | Parsing/building is Python domain |
| Deep-reading dashboard rendering | None | ALL (CSS + DOM) | Plugin renders, never computes |
| "Jump to" button logic | None | ALL (openLinkText) | Obsidian API operation |
| Version number | Writer (`build_envelope`) | Reader (`_fetchStats`) | Source of truth: `paperforge/__init__.py` |

**Thin-shell rule preserved**: The JS plugin NEVER computes lifecycle, health, maturity, or next-step. It only reads pre-computed values from `formal-library.json` or directly from workspace files. All business logic remains in Python.

## Key Data Flow: AI Discussion Recording

```
User runs /pf-deep <key> in OpenCode Agent
    ↓
ld_deep.py prepares scaffold, generates deep-reading content
    ↓
Agent conversation complete
    ↓
[NEW: AI Discussion Recorder module] (Python)
    ├─ Captures conversation messages
    ├─ Writes ai/discussion.md  (human-readable markdown log)
    └─ Writes ai/discussion.json (structured JSON)
    ↓
User opens deep-reading.md in Obsidian
    ↓
_detectAndSwitch() detects deep-reading.md → 'deep-reading' mode
    ↓
_renderDeepReadingMode() reads:
    ├─ formal-library.json → lifecycle/health/maturity badges
    ├─ deep-reading.md → Pass 1 summary text
    └─ ai/discussion.json → AI Q&A history cards
```

## "Jump to Deep Reading" Button — Integration Point

**Location**: `_renderPaperMode()`, after the next-step card, as an additional contextual action.

**Condition**: Show when `entry.deep_reading_path` is non-empty AND `entry.deep_reading_status === 'done'`.

```javascript
// In _renderPaperMode(), after _renderNextStepCard():
if (entry.deep_reading_path && entry.deep_reading_status === 'done') {
    const drBtn = view.createEl('button', { cls: 'paperforge-contextual-btn deep-reading-btn' });
    drBtn.createEl('span', { cls: 'paperforge-contextual-btn-icon', text: '\uD83D\uDD0D' });
    drBtn.createEl('span', { text: 'Jump to Deep Reading' });
    drBtn.addEventListener('click', () => {
        this.app.workspace.openLinkText(entry.deep_reading_path, '');
    });
}
```

## Bug Fix Analysis

### 1. Version Number Not Displaying

**Root cause**: `_fetchStats()` at line 358 uses `version: this._cachedStats?.version || '\u2014'` but the `formal-library.json` envelope (from `build_envelope()`) has no `version` field — only `schema_version`, `generated_at`, `paper_count`, `items`.

**Fix strategy**:
- **Python** (`asset_index.py`): Add `paperforge_version` to `build_envelope()`:
  ```python
  from paperforge import __version__
  return {
      "schema_version": CURRENT_SCHEMA_VERSION,
      "paperforge_version": __version__,
      "generated_at": ...,
      "paper_count": len(items),
      "items": items,
  }
  ```
- **JS** (`main.js`): Read from envelope in `_fetchStats()`:
  ```javascript
  version: index.paperforge_version || index.version || '\u2014'
  ```

### 2. Meaningless "ai" Row in Dashboard

**Root cause**: Unknown — likely a leftover from an earlier Phase 25-26 UI experiment. Need to inspect what creates this row. Based on the state report (`STATE.md` line 61: 'Dashboard bug: "ai" row is meaningless'), this is a rendering artifact in the global dashboard view.

**Fix strategy**: Audit `_renderGlobalMode()` and `_fetchStats()` for any rendering that produces an "ai" label or row. The canonical index entry has `ai_path` as a path string, and the lifecycle includes `ai_context_ready`. If any UI component renders raw field names, filter it out or map to a human label.

## Architectural Patterns Used

### Pattern 1: Mode Dispatch (existing, extended)

**What**: `_detectAndSwitch()` → `_switchMode()` → `case 'mode': renderX()`
**When**: Adding any new dashboard context
**v1.8 extension**: Add `case 'deep-reading': this._renderDeepReadingMode()` to the switch
**Trade-offs**: Linear dispatch is simple but the switch statement grows. Acceptable for 4 modes.

### Pattern 2: File-based Index as Bridge

**What**: `formal-library.json` is the contract between Python and JS. Python writes derived fields (lifecycle, health, maturity, next_step). JS reads and renders.
**When**: Any time JS needs to display computed state
**v1.8 use**: Deep-reading dashboard reads lifecycle/health/maturity from index, only reads `discussion.json` directly for AI-specific data.
**Trade-offs**: Adds a file dependency but eliminates cross-runtime communication complexity.

### Pattern 3: ReadFileSync Data Loading

**What**: JS reads JSON files with `fs.readFileSync(indexPath, 'utf-8')` + caching via `_cachedItems`
**When**: All dashboard data loading
**v1.8 extension**: Same pattern for `discussion.json`: `fs.readFileSync(discussionPath, 'utf-8')` from `ai/` directory.
**Trade-offs**: Requires vault-relative path resolution. OK because `this.app.vault.adapter.basePath` provides vault root.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Business Logic in JS

**What people do**: Re-implement lifecycle or health computation in JavaScript
**Why it's wrong**: Creates configuration drift between Python and JS, violates thin-shell constraint
**Do this instead**: Only read pre-computed values from the canonical index. The JS plugin is a view layer only.

### Anti-Pattern 2: Two Frontmatter Sources of Truth

**What people do**: Read deep-reading status from frontmatter AND from the index, compare them
**Why it's wrong**: Creates reconciliation bugs. The index IS the canonical source.
**Do this instead**: Deep-reading dashboard gets all status fields from `_findEntry(key)` which reads from `_getCachedIndex()`.

### Anti-Pattern 3: Filename-based heuristic for mode detection

**What people do**: Check if filename === "deep-reading.md" without verifying workspace context
**Why it's wrong**: A user could have any file named "deep-reading.md" anywhere in their vault
**Do this instead**: Verify parent directory matches workspace pattern `{8-char key} - {title_slug}` and the file is inside `Literature/{domain}/`

## Recommended Build Order

Based on dependency analysis, the suggested build order for v1.8 phases:

1. **Phase 31a: Fix version number display** — 1 change Python (build_envelope), 1 change JS (_fetchStats). Low risk, no dependencies.

2. **Phase 31b: Fix "ai" row bug** — Audit and remove. Depends on understanding current rendering, which we already have.

3. **Phase 32: Add deep-reading mode detection** — Extend `_detectAndSwitch()` and `_switchMode()`. Pure JS change. No dependency on Python.

4. **Phase 33: Build _renderDeepReadingMode() component** — New render method with status bar, Pass 1 summary, and placeholder for AI history. Depends on Phase 32.

5. **Phase 34: Add "Jump to Deep Reading" button** — Modify `_renderPaperMode()`. Depends on Phase 33 (need consistent deep-reading path resolution).

6. **Phase 35: AI discussion recorder (Python)** — Write `discussion.md` + `discussion.json` in `ai/`. Depends on nothing (standalone Python module).

7. **Phase 36: Wire AI Q&A history into deep-reading dashboard** — Read `discussion.json` in `_renderDeepReadingMode()`. Depends on Phase 33 and Phase 35.

**Rationale**: Fixes first (low risk, quick wins), then detection infrastructure, then rendering, finally data pipeline.

## Scaling Considerations

| Scale | Architecture Note |
|-------|-------------------|
| ~10 papers | All modes fast. Direct file reads adequate. |
| ~100 papers | Index scan for `_findEntry()` is O(n). Acceptable for this scale. |
| ~1000 papers | `_findEntry()` is still linear scan of items array. Consider Map-based lookup if performance becomes issue. |
| ~10K papers | `_getCachedIndex()` loads full JSON into memory (potentially 10+ MB). Consider paginated index or lazy loading. |

*For v1.8: Current scale is ~100 papers. Existing linear scan is fine. No premature optimization needed.*

## Integration Points Summary

| Point | From | To | Data | Trigger |
|-------|------|----|------|---------|
| Index reading | `formal-library.json` | `_getCachedIndex()` | All entry fields | On mode switch, on modify event |
| Deep-reading content | `deep-reading.md` | `_renderDeepReadingMode()` | Markdown text | On deep-reading mode entry |
| AI discussion history | `ai/discussion.json` | `_renderDeepReadingMode()` | Session array | On deep-reading mode entry |
| AI discussion writing | Agent command (/pf-deep, /pf-paper) | `ai/discussion.*` | Full conversation | After agent interaction complete |
| Version number | `build_envelope()` | `_fetchStats()` | `paperforge_version` string | On index rebuild |
| Jump to deep-reading | `_renderPaperMode()` button | `app.workspace.openLinkText()` | `deep_reading_path` | User click |

## Sources

- **Verified against source**: `paperforge/plugin/main.js` (lines 1-2067) — existing mode detection, switch, and rendering
- **Verified against source**: `paperforge/worker/asset_index.py` (lines 1-577) — `_build_entry()`, `build_envelope()`, `read_index()`
- **Verified against source**: `paperforge/worker/asset_state.py` (lines 1-243) — lifecycle, health, maturity, next-step computation
- **Verified against source**: `paperforge/worker/sync.py` (lines 1677-1749) — `migrate_to_workspace()`, ai/ directory creation
- **Project context**: `.planning/PROJECT.md` — v1.8 requirements and thin-shell constraint
- **Project state**: `.planning/STATE.md` — bug reports (ai row, version number)

---

*Architecture research for: PaperForge v1.8 AI Discussion & Deep-Reading Dashboard*
*Researched: 2026-05-06*
*Confidence: HIGH — all integration points verified against existing source code*
