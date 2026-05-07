---
phase: 28-dashboard-shell-context-detection
plan: 01
subsystem: ui
tags: [obsidian-plugin, dashboard, css, index-loading, caching]

# Dependency graph
requires:
  - phase: 27-component-library
    provides: Render methods (_renderStats, _renderLifecycleStepper, _renderHealthMatrix, _renderMaturityGauge, _renderBarChart)
provides:
  - _loadIndex() — reads formal-library.json, returns parsed JSON or null
  - _getCachedIndex() — lazy-loads and caches items array from index
  - _findEntry(key) — looks up single paper entry by zotero_key
  - _filterByDomain(domain) — filters index items by domain name
  - CSS Section 13: Mode-aware content area with switching state and placeholder
  - CSS Section 14: Header mode context with color-coded badges, truncated mode name, warning text
affects:
  - 28-02-context-detection-mode-switching

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Path resolution: app.vault.adapter.basePath + plugin.settings.system_dir + 'PaperForge/indexes/formal-library.json'
    - Index access: Lazy-loaded cached array in this._cachedItems, invalidatable via null assignment
    - CSS sections: New Section 13 (content area) and Section 14 (header context) using Obsidian CSS variables only

key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/styles.css

key-decisions:
  - "_loadIndex() returns null (not empty object) on failure, so callers can distinguish 'file missing/corrupt' from 'empty index' (D-17)"
  - "_getCachedIndex() returns empty array [] on missing index, not null (D-14)"
  - "_findEntry() returns null when key is falsy or entry not found (D-18)"
  - "_filterByDomain() returns empty array [] when domain is falsy (D-16)"
  - "Path resolution duplicates _fetchStats() intentionally — self-contained, no hidden coupling"

patterns-established:
  - "Index access methods: All four methods (_loadIndex, _getCachedIndex, _findEntry, _filterByDomain) follow class method syntax on PaperForgeStatusView"
  - "Error handling: null returned for missing/corrupt file (distinguishable from empty)"
  - "CSS variables only: All new styles use var(--) references, zero hardcoded hex/rgb values"
  - "CSS section numbering: Continues from Phase 27 (Section 13 and 14)"

requirements-completed:
  - DASH-01
  - DASH-02
  - REFR-01

# Metrics
duration: 1 min
completed: 2026-05-04
---

# Phase 28 Plan 01: Dashboard Shell & Context Detection Summary

**Index loading utilities (_loadIndex, _getCachedIndex, _findEntry, _filterByDomain) on PaperForgeStatusView + CSS Sections 13-14 for mode-aware dashboard content area and header context**

## Performance

- **Duration:** 1 min
- **Started:** 2026-05-04T14:56:57Z
- **Completed:** 2026-05-04T14:58:26Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_loadIndex()` — reads `formal-library.json` using established path resolution pattern, returns parsed JSON or `null` on failure
- Added `_getCachedIndex()` — lazy-loads and caches items array in `this._cachedItems`; returns `[]` when index missing
- Added `_findEntry(key)` — lookup single paper by `zotero_key` via `Array.find`, returns entry or `null`
- Added `_filterByDomain(domain)` — filters index items by domain field via `Array.filter`, returns array or `[]`
- Added CSS Section 13 — `.paperforge-content-area` container with `opacity` switching transition and `.paperforge-content-placeholder` dashed-border styling
- Added CSS Section 14 — `.paperforge-mode-context` header area with `.paperforge-mode-badge` in 3 color states (global/accent, paper/cyan, collection/purple), `.paperforge-mode-name` with ellipsis truncation, and `.paperforge-mode-warning`

## Task Commits

Each task was committed atomically:

1. **Task 1: Index loading utilities** — `8944ecc` (feat)
2. **Task 2: Mode-aware CSS** — `8574a61` (feat)

**Plan metadata:** (docs: complete plan — after state updates below)

## Files Created/Modified

- `paperforge/plugin/main.js` — Added 4 methods to PaperForgeStatusView (+35 lines)
- `paperforge/plugin/styles.css` — Added Sections 13 and 14 (+80 lines)

## Decisions Made

- `_loadIndex()` returns `null` on failure (not empty object) — per D-17, callers can distinguish "file missing/corrupt" from "empty index"
- `_getCachedIndex()` returns `[]` when index is missing — per D-14, callers iterate safely without null checks
- `_findEntry()` returns `null` when key is falsy or not found — per D-18, single paper not found is a distinguishable state
- `_filterByDomain()` returns `[]` when domain is falsy — per D-16, empty filter results are just an empty array
- Path resolution in `_loadIndex()` duplicates `_fetchStats()` intentionally — self-contained, no hidden coupling; existing `_fetchStats()` left untouched

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- None

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Index data access layer complete — `28-02 Context Detection & Mode Switching` can use `_loadIndex()`, `_findEntry(key)`, `_filterByDomain(domain)`, and `_getCachedIndex()` directly
- CSS shell in place — Section 13 provides the content area container (.paperforge-content-area, .paperforge-content-placeholder) and Section 14 provides the header context (.paperforge-mode-context, .paperforge-mode-badge, .paperforge-mode-name, .paperforge-mode-warning) for Plan 28-02 to wire up
- `_cachedItems` invalidatable via `this._cachedItems = null` — Plan 28-02 can trigger refresh when file changes

---

*Phase: 28-dashboard-shell-context-detection*
*Completed: 2026-05-04*
