---
phase: 25-surface-convergence-doctor-repair
plan: 02
subsystem: plugin
tags: plugin, dashboard, formal-library, direct-json-read, quick-actions

# Dependency graph
requires:
  - phase: 23-canonical-asset-index-safe-rebuilds
    provides: canonical formal-library.json with envelope format
  - phase: 24-derived-lifecycle-health-maturity
    provides: lifecycle, health, maturity, next_step fields in index
provides:
  - Plugin dashboard reads formal-library.json directly via readFileSync
  - Dashboard falls back to CLI spawn when index file is missing
  - Doctor and repair as one-click Quick Action buttons
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Plugin reads canonical index JSON instead of spawning Python CLI
    - Actions remain thin CLI shells (sync, ocr, doctor, repair)

key-files:
  created: []
  modified:
    - paperforge/plugin/main.js

key-decisions:
  - "Use this.app.plugins.plugins['paperforge'].settings for system_dir instead of re-reading paperforge.json"
  - "Keep version badge from cached CLI stats (index has schema_version, not package version)"
  - "Single-pass aggregation loop computes all counts within one iteration (D-06)"
  - "Actions grid CSS already handles 4 cards via auto-fit minmax(160px, 1fr) -- no CSS changes needed"

patterns-established:
  - "Plugin reads canonical index JSON directly via readFileSync for dashboard stats"
  - "Plugin actions remain thin CLI shells: spawn python -m paperforge {cmd}"
  - "CLI spawn fallback when canonical index file is missing or corrupt"

requirements-completed:
  - SURF-03

# Metrics
duration: 2min
completed: 2026-05-04
---

# Phase 25: Surface Convergence Plan 02 — Plugin Dashboard Direct JSON Read + Doctor/Repair Quick Actions

**Plugin dashboard reads formal-library.json directly via readFileSync instead of spawning Python CLI, with doctor and repair as one-click Quick Action buttons**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-04T11:22:28Z
- **Completed:** 2026-05-04T11:24:24Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Refactored `_fetchStats()` to read `formal-library.json` from `{vault}/{system_dir}/PaperForge/indexes/` via `fs.readFileSync` instead of spawning `python -m paperforge status --json`
- Single-pass aggregation loop computes paper count, lifecycle distribution, health aggregates, and OCR counts without holding references beyond loop scope (D-06)
- CLI spawn preserved as fallback when index file is missing or corrupt (D-07)
- Added `paperforge-doctor` Quick Action: runs `python -m paperforge doctor`
- Added `paperforge-repair` Quick Action: runs `python -m paperforge repair`
- ACTIONS array now has 4 entries (sync, ocr, doctor, repair)
- Existing `_runAction()` method handles new commands unchanged (thin CLI shell per SURF-03 / D-05)

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor _fetchStats() to read canonical index JSON directly** - `86d142e` (feat)
2. **Task 2: Add doctor and repair as plugin Quick Action buttons** - `d143c2e` (feat)

**Plan metadata:** `pending` (will be committed after state updates)

## Files Created/Modified

- `paperforge/plugin/main.js` — Refactored `_fetchStats()` for direct JSON read; added doctor/repair to ACTIONS

## Decisions Made

- Used `this.app.plugins.plugins['paperforge'].settings.system_dir` to access plugin settings from the view (standard Obsidian pattern — avoids changing view constructor or registration)
- Version badge shown from cached CLI stats (`this._cachedStats?.version`) since the index only carries `schema_version` (internal schema number, not package version)
- Single-pass loop computes all aggregates per D-06 (no item references retained after loop scope)
- No CSS changes needed — the actions grid already uses `grid-template-columns: repeat(auto-fit, minmax(160px, 1fr))` which auto-adapts to 4 cards

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None

## Next Phase Readiness

- Ready for 25-03-PLAN.md: Base views lifecycle columns + repair source-first rebuild pattern
- Plugin dashboard now reads canonical index directly — no CLI spawn needed for normal operation
- Doctor and repair available as one-click dashboard actions

## Self-Check: PASSED

- [x] `paperforge/plugin/main.js` exists
- [x] Commit `86d142e` exists (feat: refactor _fetchStats)
- [x] Commit `d143c2e` exists (feat: add doctor and repair Quick Actions)
- [x] `25-02-SUMMARY.md` exists

---

*Phase: 25-surface-convergence-doctor-repair*
*Completed: 2026-05-04*
