---
phase: 20
plan: 20
subsystem: plugin
tags: obsidian-plugin, settings, persistence, data-model, debounce, settings-tab

# Dependency graph
requires:
  - phase: 19
    provides: tested deployment pipeline, plugin exists with sidebar status view and quick actions
provides:
  - Plugin settings tab with DEFAULT_SETTINGS data model (8 fields, 3 sections)
  - Debounced 500ms persistence via Obsidian `loadData()`/`saveData()` API
  - In-memory settings state surviving tab switches via `display()` lifecycle
affects:
  - Phase 21 (One-Click Install & Polished UX) — settings tab will receive install button

# Tech tracking
tech-stack:
  added: Obsidian PluginSettingTab API, Setting form builder, loadData/saveData persistence
  patterns: Debounced save (500ms setTimeout/clearTimeout), in-memory state on change + deferred disk write

key-files:
  created: []
  modified:
    - paperforge/plugin/main.js — DEFAULT_SETTINGS constant, loadSettings/saveSettings, PaperForgeSettingTab class

key-decisions:
  - "All code in main.js (no build system) — CommonJS require already works in Obsidian"
  - "Debounced save at 500ms — in-memory settings update immediately on input change, disk write deferred"
  - "String fields only — no toggles/selects needed for this phase (all 8 settings are text inputs)"
  - "No styles.css changes — Obsidian's built-in .setting-item styles render settings properly"

patterns-established:
  - "Debounced persistence: clearTimeout/setTimeout wrapper with 500ms delay"
  - "display() lifecycle: reconstruct DOM from this.plugin.settings on each call, preserve in-memory state"
  - "Null-safe merge: Object.assign({}, DEFAULTS, await this.loadData()) prevents TypeError on fresh install"

requirements-completed: [SETUP-01, SETUP-02]

# Metrics
duration: 2min
completed: 2026-04-29
---

# Phase 20 Plan 20: Plugin Settings Shell & Persistence Summary

**Obsidian Plugin settings tab with DEFAULT_SETTINGS data model, in-memory state, debounced 500ms persistence, and 8 configuration fields across 3 sections (基础路径, API 密钥, Zotero 链接)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-29T22:18:50Z
- **Completed:** 2026-04-29T22:20:18Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- **Settings Data Model**: `DEFAULT_SETTINGS` constant with 8 fields (vault_path, system_dir, resources_dir, literature_dir, control_dir, agent_config_dir, paddleocr_api_key, zotero_data_dir) with sensible defaults for system/resource dirs
- **Plugin Persistence**: `loadSettings()` with null-safe merge via `Object.assign({}, DEFAULTS, await this.loadData())` and `saveSettings()` via Obsidian's `saveData()` API — handles fresh install gracefully
- **Settings Tab UI**: `PaperForgeSettingTab` class extending `PluginSettingTab` with 3 logically grouped sections and debounced 500ms auto-save on every field change
- **Input Types**: 7 regular text inputs + 1 password field (`paddleocr_api_key`) with `inputEl.type = 'password'`
- **Zero Regression**: Existing `PaperForgeStatusView` sidebar and command palette actions (Sync Library, Run OCR) continue functioning unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1 + 2: Settings Data Model + Settings Tab UI** - `dfffc05` (feat)
2. **Task 3: Styles (minimal)** — No changes needed (Obsidian defaults render Settings properly)

**Plan metadata:** (pending — metadata commit follows)

_Note: Tasks 1 and 2 are both in main.js and functionally interdependent (tab UI calls plugin.settings and plugin.saveSettings()). Combined into one atomic commit._

## Files Created/Modified
- `paperforge/plugin/main.js` — +87 lines: DEFAULT_SETTINGS constant, loadSettings/saveSettings methods, PaperForgeSettingTab class with 8 fields across 3 sections, debounced save

## Decisions Made
- **CommonJS in main.js**: All settings code stays in main.js with no build system — Obsidian's `require('obsidian')` works natively, and a second file would add path complexity
- **Debounced save pattern**: In-memory settings update immediately on `onChange`, but disk write is deferred 500ms via `setTimeout`/`clearTimeout` to prevent thrashing `data.json`
- **display() lifecycle**: `display()` reconstructs DOM from `this.plugin.settings` on each tab switch — in-memory settings preserve state with zero data loss
- **No CSS additions**: Obsidian's built-in `.setting-item` styles render the settings tab perfectly; no custom styles needed per plan guidance

## Deviations from Plan

None — plan executed exactly as written. The code was already implemented in the working tree matching the plan's specifications.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required for this phase. User access to the settings tab is via Obsidian's native Settings UI (Settings > Community Plugins > PaperForge gear icon).

## Next Phase Readiness
- Settings tab shell and persistence are ready for Phase 21 (One-Click Install & Polished UX)
- Phase 21 will add the install button, field validation, subprocess orchestration, and human-readable Chinese notices
- All 8 settings fields are accessible via `this.plugin.settings` from any plugin code

---

## Self-Check: PASSED

- [x] `paperforge/plugin/main.js` exists on disk
- [x] Commit `dfffc05` exists in git log
- [x] Commit message contains `20-20` scope matching plan

*Phase: 20-plugin-settings-shell-persistence*
*Completed: 2026-04-29*
