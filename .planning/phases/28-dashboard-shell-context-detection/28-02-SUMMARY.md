---
phase: 28-dashboard-shell-context-detection
plan: 02
subsystem: ui
tags: [obsidian, plugin, dashboard, context-detection, mode-switching, event-subscriptions]

# Dependency graph
requires:
  - phase: 28-01
    provides: Index utilities (_loadIndex, _findEntry, _filterByDomain), CSS mode shell
provides:
  - Context-aware mode detection (_detectAndSwitch) routing .base/.md/no-file to correct view
  - Event-driven auto-refresh via workspace/vault subscriptions
  - Mode-aware header rendering with badge + context text
  - Lifecycle cleanup (onClose unsubscribes events, clears timers, nulls cache)
  - Mode-specific render stubs for Phase 29 (per-paper) and Phase 30 (collection)
affects:
  - 29-per-paper-view
  - 30-collection-view

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Mode switching via _currentMode state with _detectAndSwitch -> _switchMode dispatch
    - Debounced active-leaf-change handler (300ms) to avoid rapid re-renders
    - Event subscription tracking via _modeSubscribers array for cleanup
    - Vault modify handler filtered to formal-library.json path suffix

key-files:
  created: []
  modified:
    - paperforge/plugin/main.js

key-decisions:
  - "Debounce active-leaf-change at 300ms — balances responsiveness with avoiding rapid re-renders"
  - "OCR section (_ocrSection, _ocrBadge, etc.) created as instance vars in _renderGlobalMode() rather than _buildPanel() to keep structural shell lean — maintains backward compatibility with _renderOcr()"
  - "Event refs stored as {event, ref} objects in _modeSubscribers for unified onClose cleanup"
  - "Orphaned duplicate code from previous edit removed (duplicate _runAction handlers and _showMessage)"

patterns-established:
  - "Mode detection: getActiveFile() -> ext checks -> _switchMode(mode) -> render"
  - "Event lifecycle: constructor initializes -> _setupEventSubscriptions() in onOpen -> onClose() tears down"
  - "Index cache invalidation triggered on both refresh button and vault modify event"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, REFR-01, REFR-02]

# Metrics
duration: 5 min
completed: 2026-05-04
---

# Phase 28 Plan 02: Context Detection, Mode Switching & Auto-Refresh

**Mode-aware dashboard routing with _detectAndSwitch, _switchMode, debounced event subscriptions, mode header rendering, and lifecycle cleanup in PaperForgeStatusView**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-04T15:00:11Z
- **Completed:** 2026-05-04T15:05:30Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Context detection infrastructure (D-01 through D-04): Active file type resolved to global/per-paper/collection mode via `_detectAndSwitch()`
- Mode switching dispatch (D-05, D-06): `_switchMode()` clears content, updates header, and renders correct mode view
- Mode-aware header (D-07): `_renderModeHeader()` shows badge (Global/Paper/Collection) + context name + not-found warning
- Event subscriptions (D-08, D-09, D-19): `_setupEventSubscriptions()` wires `active-leaf-change` (debounced 300ms) and vault `modify` (filtered to `formal-library.json`)
- Lifecycle cleanup: `onClose()` unsubscribes all events, clears timers, nulls cached data
- Render stubs: `_renderGlobalMode()` (functional dashboard), `_renderPaperMode()` and `_renderCollectionMode()` (placeholders for Phase 29/30)
- Index cache invalidation: `_invalidateIndex()` called on refresh button and vault modify

## Task Commits

Each task was committed atomically:

1. **Task 1: Mode detection infrastructure** - `0fa589f` (feat)
2. **Task 2: Event subscriptions, header rendering, cleanup** - `424931d` (feat)

## Files Created/Modified

- `paperforge/plugin/main.js` - Mode detection, switching, event subscriptions, header rendering, lifecycle cleanup (+309 lines net)

## Decisions Made

- **300ms debounce** for `active-leaf-change` — balances responsiveness with preventing rapid re-renders during tab switching (per agent discretion in CONTEXT.md)
- **OCR components created in _renderGlobalMode()** rather than _buildPanel() — keeps structural shell lean while maintaining backward compatibility with existing _renderOcr() and _fetchStats() methods (deviation from plan, required to prevent null reference crash)
- **Event refs stored as `{event, ref}`** objects for unified cleanup regardless of Obsidian version (ref may be number or function)
- **Orphaned duplicate code removed** — cleaned up leftover duplicate `_runAction` handlers and duplicate `_showMessage` method that were causing potential parse issues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] OCR instance variables created in _renderGlobalMode**
- **Found during:** Task 1 (_renderGlobalMode implementation)
- **Issue:** Plan's _renderGlobalMode created `this._metricsEl` but not `this._ocrSection`, `this._ocrBadge`, `this._ocrTrack`, `this._ocrCounts`, `this._ocrEmpty` — these are required by existing `_renderOcr()` which references them as instance variables
- **Fix:** Added full OCR section creation in _renderGlobalMode() matching old _buildPanel() structure
- **Files modified:** paperforge/plugin/main.js
- **Verification:** _renderOcr() accesses all references correctly, manual code inspection
- **Committed in:** 0fa589f (Task 1 commit)

**2. [Rule 3 - Blocking] Removed orphaned duplicate code blocks and duplicate _showMessage**
- **Found during:** Task 1 (orphaned code before insertion point)
- **Issue:** Main.js contained orphaned duplicate `child.on('close', ...)` and `child.on('error', ...)` handlers outside any method (lines 785-817), plus duplicate `_showMessage` method definition (lines 826-831) — would cause parse error in strict mode
- **Fix:** Removed both orphaned blocks, kept single `_showMessage` definition
- **Files modified:** paperforge/plugin/main.js
- **Verification:** File parses cleanly, all call sites reference existing method
- **Committed in:** 0fa589f (Task 1 commit)

**3. [Rule 3 - Blocking] Removed duplicate closing brace from cleanup**
- **Found during:** Task 1 (after removing orphaned block)
- **Issue:** Orphaned block removal created a double `}` at class level which would cause parse error
- **Fix:** Removed the extra closing brace
- **Files modified:** paperforge/plugin/main.js
- **Verification:** File now has clean class structure with correct brace matching
- **Committed in:** 0fa589f (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 blocking)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- Duplicate/orphaned code in main.js (from previous editing session) required careful cleanup to avoid inserting new methods into broken class structure
- Unicode/encoding challenges running Python verification scripts on Windows with UTF-8 source files

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Dashboard shell complete: context detection routes .base/.md/no-file to correct mode
- Phase 29 can consume `_currentMode === 'paper'` + `_findEntry(key)` for per-paper view with lifecycle stepper, health matrix, maturity gauge
- Phase 30 can consume `_currentMode === 'collection'` + `_filterByDomain(domain)` for collection view with distribution bar chart and aggregated health
- Auto-refresh pipeline ready: file switch and formal-library.json modification trigger correct mode re-render

## Self-Check: PASSED

- [x] `.planning/phases/28-dashboard-shell-context-detection/28-02-SUMMARY.md` — exists
- [x] Commits exist: `0fa589f` (Task 1), `424931d` (Task 2)
- [x] `paperforge/plugin/main.js` — modified with all required methods (_detectAndSwitch, _switchMode, _renderModeHeader, _setupEventSubscriptions, _refreshCurrentMode, _renderActions, _renderGlobalMode, _renderPaperMode, _renderCollectionMode, _invalidateIndex)
- [x] Event subscriptions: active-leaf-change (debounced 300ms), vault modify (filtered to formal-library.json)
- [x] Mode badge CSS classes: paperforge-mode-badge, paperforge-mode-warning
- [x] Lifecycle cleanup: workspace.off(), vault.off(), clearTimeout, cache null
- [x] Plan requirements DASH-01..04, REFR-01..02 covered

---

*Phase: 28-dashboard-shell-context-detection*
*Completed: 2026-05-04*
