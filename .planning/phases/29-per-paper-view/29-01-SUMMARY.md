---
phase: 29-per-paper-view
plan: 01
subsystem: ui
tags: obsidian-plugin, dashboard, per-paper, lifecycle, health-matrix, maturity-gauge, next-step, css
requires:
  - phase: 27-component-library
    provides: _renderLifecycleStepper, _renderHealthMatrix, _renderMaturityGauge, _renderSkeleton, _renderEmptyState
  - phase: 28-dashboard-shell-context-detection
    provides: _detectAndSwitch, _switchMode, _findEntry, _currentPaperEntry, ACTIONS, _runAction
provides:
  - Full _renderPaperMode() implementation wired to Phase 27 components
  - _renderNextStepCard() 6-state recommendation engine
  - _openFulltext() Obsidian vault file opener
  - CSS Section 15: Per-Paper View Layout
  - CSS Section 16: Next-Step Recommendation Card
affects: [30-collection-view]
tech-stack:
  added: []
  patterns:
    - Contextual action row created inline in _renderPaperMode before components
    - Next-step action dispatch using ACTIONS.find(cmd) + _runAction for sync/ocr/repair
    - Clipboard API (navigator.clipboard.writeText) for /pf-deep key copy
    - Obsidian vault API (getAbstractFileByPath + openLinkText) for Open Fulltext
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/styles.css
key-decisions:
  - "Next-step action button for /pf-deep copies zotero_key to clipboard (no CLI command exists for deep reading)"
  - "Ready state next-step card shows Copy Context shortcut instead of action trigger"
  - "Copy Context button reuses existing paperforge-copy-context ACTIONS entry with needsKey"
requirements-completed: [PAPER-01, PAPER-02, PAPER-03, PAPER-04]
duration: 10 min
completed: 2026-05-04
---

# Phase 29: Per-Paper View Summary

**Full per-paper dashboard rendering pipeline: lifecycle stepper, health matrix, maturity gauge, next-step recommendation card, contextual actions, and paper metadata header**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-04T08:16:09Z
- **Completed:** 2026-05-04T08:26:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Replaced `_renderPaperMode()` placeholder with full rendering pipeline: metadata header (title, authors, year), lifecycle stepper, 2x2 health matrix, 6-segment maturity gauge with blocking checks, next-step recommendation card with action trigger
- Added `_renderNextStepCard()` helper with 6-state stepInfo mapping: sync, ocr, repair, rebuild index, /pf-deep, ready -- each with human-readable label + contextual action button
- Added `_openFulltext()` helper using Obsidian vault API to open fulltext.md files
- Added CSS Section 15 (Per-Paper View Layout) and Section 16 (Next-Step Recommendation Card)
- Contextual action buttons: Copy Context (reuses existing `paperforge-copy-context` action with `_runAction`) and Open Fulltext (conditional on `entry.fulltext_path`)
- All verification criteria pass -- JS syntax check clean, old placeholder text removed, all CSS classes defined

## Task Commits

Each task was committed atomically:

1. **Task 1: Add per-paper view CSS layout and next-step card styles** - `de26116` (style)
2. **Task 2: Replace _renderPaperMode() placeholder with full per-paper view** - `47c8093` (feat)

## Files Created/Modified
- `paperforge/plugin/styles.css` - Added Section 15 (Per-Paper View Layout) with .paperforge-paper-view, .paperforge-paper-header, .paperforge-paper-title, .paperforge-paper-meta, .paperforge-paper-authors, .paperforge-paper-year, .paperforge-paper-actions, .paperforge-contextual-btn classes; Added Section 16 (Next-Step Recommendation Card) with .paperforge-next-step-card, .paperforge-next-step-label, .paperforge-next-step-text, .paperforge-next-step-trigger classes
- `paperforge/plugin/main.js` - Replaced `_renderPaperMode()` placeholder (14 lines) with full implementation (133 lines) including contextual action buttons row, paper metadata header, lifecycle stepper render, health matrix render, maturity gauge render, next-step card render; Added `_renderNextStepCard(container, entry, key)` with 6-state mapping; Added `_openFulltext(fulltextPath)` using Obsidian vault API

## Decisions Made
- **Next-step button for /pf-deep**: Copies zotero_key to clipboard via `navigator.clipboard.writeText(key)` since there's no CLI command for deep reading -- the user pastes the key in OpenCode Agent. For ready state, shows "Copy Context" shortcut.
- **Action dispatch pattern**: Next-step card for sync/ocr/repair calls `ACTIONS.find(a => a.cmd === info.cmd)` then `_runAction(action, trigger)` -- same pattern used by the Quick Actions grid, ensuring consistent behavior.
- **Contextual action row**: Created inside `_renderPaperMode()` before the components, with Copy Context on the left and Open Fulltext conditional on `entry.fulltext_path` existence.
- **Open Fulltext implementation**: Uses Obsidian's `app.vault.getAbstractFileByPath()` + `app.workspace.openLinkText()` to open the fulltext.md file in the editor.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## Known Stubs
- `_renderCollectionMode()` at line 956 remains a placeholder ("Phase 30 will add") -- intentional, planned for Phase 30.

## Next Phase Readiness
- Per-paper view fully wired: Phase 28 `_switchMode('paper')` -> `_renderPaperMode()` now renders complete per-paper dashboard with all 4 Phase 27 component methods
- Ready for Phase 30 (Collection View) to wire `_renderCollectionMode()` with aggregated lifecycle bar chart, health summary, and paper count
- No blockers

---
## Self-Check: PASSED

- [x] `paperforge/plugin/styles.css` exists
- [x] `paperforge/plugin/main.js` exists
- [x] Commit `de26116` exists (Task 1)
- [x] Commit `47c8093` exists (Task 2)

*Phase: 29-per-paper-view*
*Completed: 2026-05-04*
