---
phase: ANN14
plan: ANN14-03
subsystem: canvas-connector
tags:
  - connector-layer
  - runtime
  - hover
  - selection
  - lifecycle
requires:
  - ANN14-01 (connector engine)
  - ANN14-02 (CSS + DOM integration)
provides:
  - Runtime connector rendering in PaperForgeReadingCanvasView
affects:
  - paperforge/plugin/main.js (PaperForgeReadingCanvasView)
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
tech-stack:
  added: []
  patterns:
    - SVG layer via renderCanvasConnectorLayer
    - RAF-throttled measurement via _scheduleConnectorUpdate
    - Delegated hover events via mouseover/mouseout on contentEl
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/tests/canvas-main-runtime.test.mjs
decisions:
  - D-01: Runtime draws connector only for selected card/source pair
  - D-02: Hover state can override selected state for connector display
metrics:
  duration: ~2h
  completed: 2026-07-07
---

# Phase ANN14 Plan 03: Connector Layer Ownership Summary

Wire connector helpers and SVG layer into PaperForgeReadingCanvasView so selected/hovered exact annotation pairs produce a transient measured connector line with full lifecycle cleanup.

**Connector runtime fields, delegated hover events, RAF-throttled measurement scheduling, and lifecycle teardown — all wired into PaperForgeReadingCanvasView with 87 passing tests.**

---

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Connector layer ownership — fields, cleanup, layer creation, helper methods | 6caf85f | main.js, canvas-main-runtime.test.mjs |
| 2 | Wire selection + hover to connector render — null guard, tests | 5b970ce | main.js, canvas-main-runtime.test.mjs |
| 3 | Add scroll/resize lifecycle tests for connector layer | 196c3d6 | canvas-main-runtime.test.mjs |

## What Was Built

### Task 1: Connector Layer Ownership

**Runtime fields** added to `PaperForgeReadingCanvasView` constructor:
- `_connectorLayerEl` — SVG layer reference (null initially)
- `_connectorFrameHandle` — RAF handle for throttled recomputation
- `_hoveredCardId` / `_hoveredAnchorId` — transient hover tracking
- Bound handler refs for cleanup: `_connectorBoundMouseover`, `_connectorBoundMouseout`, `_connectorBoundScroll`, `_connectorBoundResize`

**Layer creation** in `_renderLoadedCanvas()`:
- Creates SVG element via `renderCanvasConnectorLayer(contentEl)`
- Sets `aria-hidden="true"` and class `paperforge-canvas-connector-layer`
- Appended as last child of contentEl (above source surfaces)
- Initializes scroll/resize and hover event wiring

**Cleanup** in `_cleanupNavigation()` and `onClose()`:
- `cancelAnimationFrame` on pending frame handle
- Removes scroll (`contentEl`) and resize (`window`) listeners
- Removes mouseover/mouseout listeners via `removeEventListener`
- Clears SVG children from connector layer
- Nulls hover state fields and bound handler refs
- `onClose()` also nulls `_connectorLayerEl` and `_connectorFrameHandle`

**Helper methods:**
- `_clearConnectorLayer()` — empties SVG content (safe on null layer)
- `_initConnectorHoverEvents(contentEl)` — delegated mouseover/mouseout on `[data-card-id]` and `[data-anchor-id]`, updates `_hoveredCardId`/`_hoveredAnchorId`, schedules connector update
- `_initConnectorScrollResize()` — passive scroll on `contentEl`, resize on `window`, both call `_scheduleConnectorUpdate()`
- `_scheduleConnectorUpdate()` — cancelAnimationFrame + requestAnimationFrame throttle (D-06)
- `_updateConnector(modifier)` — full implementation: computes candidate from nav+hover state, measures DOM endpoints via `getBoundingClientRect()`, renders via `updateCanvasConnectorLayer()`, hidden for missing DOM / zero-size / offscreen

### Task 2: Selection + Hover Wire

- `_applyCardNavigationState()` now calls `_scheduleConnectorUpdate()` on every navigation state change (D-01/D-02)
- Hover events properly distinguish:
  - Mouseover on card sets hover state to card ID
  - Mouseout with relatedTarget inside contentEl preserves hover
  - Mouseout with relatedTarget outside contentEl clears hover
  - Non-hovered card mouseout does not affect current hover state
- Null guard: `_initConnectorHoverEvents(null)` returns immediately

### Task 3: Lifecycle Tests

**11 tests** covering:
- RAF frame handle cancellation on repeated `_scheduleConnectorUpdate()` calls
- `_initConnectorScrollResize()` safety with null contentEl
- `_cleanupNavigation()` removes scroll/resize handlers and clears layer DOM
- `_cleanupNavigation()` cancels frame handle
- Layer DOM content cleared by `_cleanupNavigation()`
- `_clearConnectorLayer()` safe on null layer
- `onClose()` after `_renderLoadedCanvas()` cancels frame and nulls layer ref
- Double `_cleanupNavigation()` is idempotent
- Paper change simulation clears hover state

### Key Connector Flow

1. **Selection change** → `_applyCardNavigationState()` → calls `_scheduleConnectorUpdate()` → RAF fires → `_updateConnector()` computes candidate → renders or hides
2. **Mouse hover** → `_initConnectorHoverEvents` → sets `_hoveredCardId`/`_hoveredAnchorId` → calls `_scheduleConnectorUpdate()` → renders connector for hovered pair
3. **Scroll/resize** → passive listeners → `_scheduleConnectorUpdate()` → recompute from current DOM
4. **Cleanup/teardown** → `_cleanupNavigation()` or `onClose()` → cancel frame, remove listeners, clear DOM, null refs

## Verification Results

- `node --check main.js` PASSED
- 87 tests pass in `canvas-main-runtime.test.mjs` (all ANN14-03 tests)
- 67 regression tests pass in `annotation-main-runtime.test.mjs`
- 67 regression tests pass in `annotation-section-dom.test.mjs`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] Added `_updateConnector()` in Task 1 commit**
- **Found during:** Task 1 implementation
- **Issue:** `_scheduleConnectorUpdate()` calls `this._updateConnector()` on RAF, which must exist to compile and function
- **Fix:** Added full `_updateConnector(modifier)` implementation in Task 1 — computes candidate via `computeFocusedConnectorCandidate`, measures DOM endpoints via `getBoundingClientRect()`, renders via `updateCanvasConnectorLayer()`. This is Task 2 scope committed early because it's a runtime dependency of `_scheduleConnectorUpdate()`.
- **Files modified:** main.js
- **Commit:** 6caf85f

**2. [Rule 2 — Missing null guard] Added null guard in `_initConnectorHoverEvents()`**
- **Found during:** Task 2 test for null contentEl
- **Issue:** `_initConnectorHoverEvents(null)` called `contentEl.addEventListener` without checking for null contentEl
- **Fix:** Added early return guard at method entry
- **Files modified:** main.js
- **Commit:** 5b970ce

**3. [Rule 2 — Missing null guard] Added null `_connectorLayerEl` guard in `_updateConnector()`**
- **Found during:** Task 2 test run — animation frame fired before layer was created, crashed in `updateCanvasConnectorLayer()` accessing `null.firstChild`
- **Fix:** Early return from `_updateConnector()` if `_connectorLayerEl` is falsy
- **Files modified:** main.js
- **Commit:** 5b970ce

**4. [Rule 1 — Bug fix] Re-added `_scheduleConnectorUpdate()` in `_applyCardNavigationState()`**
- **Found during:** Task 2 test — spy reported 0 calls
- **Issue:** Previous edit of `_applyCardNavigationState()` was overwritten by subsequent edits
- **Fix:** Re-added the call with ANN14-03 comment annotation
- **Files modified:** main.js
- **Commit:** 5b970ce

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced.

## Known Stubs

None — all connector behavior is fully wired through the runtime.

## Self-Check: PASSED

- [x] `paperforge/plugin/main.js` — exists, modified
- [x] `paperforge/plugin/tests/canvas-main-runtime.test.mjs` — exists, modified
- [x] Commit `6caf85f` — verified in git log
- [x] Commit `5b970ce` — verified in git log
- [x] Commit `196c3d6` — verified in git log
- [x] `node --check main.js` — PASSED
- [x] All 87 canvas tests pass
- [x] All 134 regression tests pass
