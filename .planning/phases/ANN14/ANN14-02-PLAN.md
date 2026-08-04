---
phase: ANN14
plan: ANN14-02
type: execute
status: planned
wave: 2
depends_on:
  - ANN14-01
files_modified:
  - paperforge/plugin/src/canvas/render.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/canvas-render.test.mjs
  - paperforge/plugin/tests/canvas-card-dom.test.mjs
requirements:
  - CONN-01
  - CONN-02
requirements_addressed:
  - CONN-01
  - CONN-02
user_setup: []
autonomous: true
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16
  - D-17
  - D-18
  - D-20
must_haves:
  truths:
    - "D-02/D-13/D-17: A namespaced connector SVG layer can exist only as focused Reading Canvas presentation state, not as persistent layout state."
    - "D-01/D-03/D-13: Render tests allow connector paths only for exact connector data and keep page-level/unresolved states line-free."
    - "D-10/D-11/D-12: Connector visuals are thin, solid, low-opacity, selected slightly stronger than hovered, and contain no arrows, endpoint dots, animation, or annotation-color palette."
    - "D-14/D-15/D-16/D-18/D-20: CSS stays restrained, responsive, read-only, and namespaced while ANN13 selected/focus/fallback visuals remain visible when connectors are absent."
  artifacts:
    - path: "paperforge/plugin/src/canvas/render.js"
      provides: "Namespaced connector SVG layer and path rendering helpers"
    - path: "paperforge/plugin/styles.css"
      provides: "Restrained connector CSS under .paperforge-reading-canvas-view"
    - path: "paperforge/plugin/tests/canvas-render.test.mjs"
      provides: "Render coverage for connector layer, exact-only path rendering, and forbidden states"
    - path: "paperforge/plugin/tests/canvas-card-dom.test.mjs"
      provides: "CSS and DOM namespace regression coverage"
  key_links:
    - from: "paperforge/plugin/src/canvas/connectors.js"
      to: "paperforge/plugin/src/canvas/render.js"
      via: "render helper accepts visible geometry output and hidden states from connector helpers"
      pattern: "visible|hidden"
    - from: "paperforge/plugin/src/canvas/render.js"
      to: "paperforge/plugin/styles.css"
      via: "paperforge-canvas-connector-layer and modifier classes share exact names"
      pattern: "paperforge-canvas-connector"
---

# ANN14-02 Plan: Namespaced Connector Layer Rendering and CSS

## Objective

Add the focused connector presentation surface: a namespaced SVG layer and restrained CSS that can render a single selected or hovered exact connector without changing canvas data, navigation, fallback, or source anchoring semantics.

## Scope

- Connector layer/path render helpers in `render.js`.
- Export additions in `src/canvas/index.js`.
- Namespaced connector CSS in `styles.css`.
- DOM/render tests that narrow prior "no connector" assertions to allow only the ANN14 focused connector layer.

## Out of Scope

- No runtime measurement, hover listeners, scroll/resize listeners, `requestAnimationFrame`, or lifecycle cleanup.
- No always-on connector web, page-level/unresolved lines, native PDF viewer DOM selectors, arrows, endpoint dots, animation, annotation-color connector palettes, mutation controls, persistence, or fallback behavior changes.

## Tasks

### Task 1: Render an Empty Namespaced Connector Layer

**Files:** `src/canvas/render.js`, `src/canvas/index.js`, `tests/canvas-render.test.mjs`

**Action:** Add and export a render helper such as `renderCanvasConnectorLayer(containerEl)` that creates exactly one empty SVG layer under `.paperforge-reading-canvas-view` using namespaced classes such as `paperforge-canvas-connector-layer`. The helper must be callable by runtime after loaded canvas rendering and must not appear in idle, missing-paper, missing-db, missing-source, unsupported, or card-only shell tests unless explicitly called by the test per D-13/D-17/D-20.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check src/canvas/render.js
node --check src/canvas/index.js
npm.cmd test -- canvas-render.test.mjs
Pop-Location
```

**Done:** Tests prove the helper creates one SVG layer in the Reading Canvas namespace, creates no connector path by default, and remains absent from non-loaded shell rendering.

### Task 2: Render Only Focused Exact Connector Paths

**Files:** `src/canvas/render.js`, `tests/canvas-render.test.mjs`, `tests/canvas-card-dom.test.mjs`

**Action:** Add a helper such as `updateCanvasConnectorLayer(layerEl, connectorState)` that clears the layer and renders at most one `path` or `line` element when connector helper output is visible. It must apply selected/hovered modifier classes from the connector state, set accessible-hidden/presentation attributes, and render nothing for hidden states, page-level/unresolved anchors, missing geometry, stale candidates, or source-unavailable candidates per D-01/D-02/D-03/D-13/D-17.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs
Pop-Location
```

**Done:** Tests prove selected exact and hovered exact connector states draw at most one connector; page-level, unresolved, stale, missing, and hidden connector states leave the SVG empty.

### Task 3: Add Restrained Connector CSS and Narrow Forbidden Assertions

**Files:** `styles.css`, `tests/canvas-render.test.mjs`, `tests/canvas-card-dom.test.mjs`

**Action:** Add CSS only under `.paperforge-reading-canvas-view` for `.paperforge-canvas-connector-layer`, `.paperforge-canvas-connector`, `.paperforge-canvas-connector--hovered`, and `.paperforge-canvas-connector--selected`. Use pointer-events none, thin solid strokes, low opacity, selected slightly stronger than hovered, and no transition/animation, marker, endpoint, arrowhead, color-following, or graph-like styling per D-10/D-11/D-12/D-14/D-15/D-16. Update existing ANN12/ANN13 tests that assert no connector/SVG so they still forbid connector leakage outside the focused layer while allowing the ANN14 layer and exact-only path tests.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs
Pop-Location
```

**Done:** CSS tests find only namespaced restrained connector selectors; tests continue to fail for mutation controls, native PDF selectors, page-level/unresolved connector paths, arrows, dots, animations, and non-namespaced SVG rules.

## Acceptance Criteria

- CONN-01 has a renderable focused connector layer.
- CONN-02 remains enforced at render time for page-level, unresolved, stale, hidden, and unsupported states.
- D-10 through D-13 visual-language constraints are encoded in CSS and tests without changing runtime behavior.
