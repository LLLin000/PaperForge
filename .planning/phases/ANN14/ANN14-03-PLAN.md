---
phase: ANN14
plan: ANN14-03
type: execute
status: planned
wave: 3
depends_on:
  - ANN14-01
  - ANN14-02
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
requirements:
  - CONN-01
  - CONN-02
  - CONN-03
requirements_addressed:
  - CONN-01
  - CONN-02
  - CONN-03
user_setup: []
autonomous: true
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-05
  - D-06
  - D-07
  - D-08
  - D-09
  - D-14
  - D-15
  - D-16
  - D-17
  - D-19
  - D-20
must_haves:
  truths:
    - "D-01/D-02/D-03/D-04: Runtime draws connectors only for selected or hovered exact card/source pairs using PaperForge-owned card and anchor DOM hooks."
    - "D-05/D-06/D-07/D-08/D-14/D-15: Runtime measurement recomputes from current DOM rectangles and hides instead of guessing when endpoints are missing, zero-size, stale, offscreen, clipped, or unreadable."
    - "D-09/D-17: Refresh, stale render, paper change, Escape, and teardown clear the connector layer and transient hover state."
    - "D-16/D-19/D-20: ANN13 selected/focus/fallback semantics remain visible and anchor precision/fallback behavior is consumed, not changed."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Runtime connector state, delegated hover/selection updates, measurement scheduling, and cleanup"
    - path: "paperforge/plugin/tests/canvas-main-runtime.test.mjs"
      provides: "Runtime coverage for selected, hovered, hidden, recompute, and cleanup connector behavior"
  key_links:
    - from: "paperforge/plugin/src/canvas/connectors.js"
      to: "paperforge/plugin/main.js"
      via: "runtime builds candidate and geometry from current VM plus measured DOM rects"
      pattern: "computeFocusedConnectorCandidate|measureConnectorGeometry"
    - from: "paperforge/plugin/src/canvas/render.js"
      to: "paperforge/plugin/main.js"
      via: "runtime creates and updates the connector SVG layer after loaded canvas render"
      pattern: "renderCanvasConnectorLayer|updateCanvasConnectorLayer"
---

# ANN14-03 Plan: Runtime Hover, Selection Measurement, and Cleanup

## Objective

Wire the pure connector helpers and rendered SVG layer into `PaperForgeReadingCanvasView` so selected or hovered exact pairs produce a transient measured connector, and all lifecycle changes clear or recompute it safely.

## Scope

- Runtime transient connector fields and delegated hover/selection integration in `main.js`.
- Measurement scheduling and layer update using PaperForge-owned DOM hooks.
- Runtime tests with `getBoundingClientRect()` doubles and event simulation.

## Out of Scope

- No new source anchor resolution, no native PDF viewer DOM selectors, no page-level/unresolved connector lines, no viewport-edge hints, no persistent layout state, no mutation controls, no fallback contract changes, and no live Obsidian PDF harness claims.

## Tasks

### Task 1: Add Runtime Connector State and Layer Ownership

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`

**Action:** Add transient fields on `PaperForgeReadingCanvasView` for hovered card/anchor IDs, connector layer element, pending frame handle, and bound scroll/resize/hover handlers. Create the connector layer after `_renderLoadedCanvas` renders the loaded canvas DOM, using the ANN14 render helper. Cleanup must remove delegated hover listeners, scroll/resize listeners, pending animation frame, connector layer contents, and transient hover state during `_cleanupNavigation`, `onClose`, and paper context replacement per D-06/D-09/D-17.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check main.js
npm.cmd test -- canvas-main-runtime.test.mjs
Pop-Location
```

**Done:** Runtime tests prove the loaded canvas owns a connector layer and `onClose`/paper replacement leaves no pending connector frame, hover state, or connector DOM residue.

### Task 2: Measure and Draw Selected or Hovered Exact Pairs

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`

**Action:** Add a single runtime update path that calls `computeFocusedConnectorCandidate`, queries only PaperForge-owned `[data-card-id]` and `[data-anchor-id][data-anchor-status="exact"]` endpoints inside `this.contentEl`, calls `getBoundingClientRect()` on the canvas root, card, and exact anchor, then calls `measureConnectorGeometry` and `updateCanvasConnectorLayer`. Invoke this path after card/source selection, delegated `mouseover`/`mouseout` or focus-compatible hover changes, and explicit connector recompute requests. It must render at most one connector and must hide for page-level/unresolved anchors, missing endpoints, zero-size rectangles, stale VM/card mismatch, and offscreen geometry per D-01/D-02/D-03/D-04/D-05/D-07/D-08/D-14/D-15/D-19/D-20.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-main-runtime.test.mjs
Pop-Location
```

**Done:** Tests prove selected exact card-anchor and hovered exact card-anchor pairs draw one connector; selected page-level/unresolved cards, missing DOM endpoints, zero-size endpoints, and offscreen endpoints leave the layer empty while selected card/source state remains visible.

### Task 3: Recompute or Clear on Runtime Lifecycle Events

**Files:** `main.js`, `tests/canvas-main-runtime.test.mjs`

**Action:** Schedule connector recomputation with one pending animation frame or equivalent conservative throttle after scroll, resize, explicit selection changes, hover changes, refresh/re-render completion, and source/card DOM updates. Clear the connector before refresh/stale render if endpoints may disappear, on Escape, paper change, and teardown. Preserve ANN13 behavior: Escape still clears selection, refresh preservation never scrolls, fallback buttons still open only on explicit click, and v0.2 fallback paths remain untouched per D-06/D-09/D-16/D-17/D-19.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-main-runtime.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
Pop-Location
```

**Done:** Tests prove scroll/resize schedule recomputation, refresh/stale/paper-change/teardown/Escape clear dangling lines, and existing ANN13 fallback tests still pass.

## Acceptance Criteria

- CONN-01 works through real runtime selected and hovered exact endpoints.
- CONN-02 is enforced in runtime for every non-exact or unmeasurable state.
- CONN-03 is enforced for scroll, resize, refresh, paper change, and teardown.
