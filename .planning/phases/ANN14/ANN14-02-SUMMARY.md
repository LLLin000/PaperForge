---
phase: ANN14
plan: ANN14-02
status: completed
wave: 2
depends_on:
  - ANN14-01
completed_date: 2026-07-06
duration: 28m
metrics:
  tasks_completed: 3
  files_modified: 5
  commits: 3
  tests_passed: 163
requirements_addressed:
  - CONN-01
  - CONN-02
decisions_coverage:
  - D-01, D-02, D-03, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-20
key_files:
  created: []
  modified:
    - paperforge/plugin/src/canvas/render.js
    - paperforge/plugin/src/canvas/index.js
    - paperforge/plugin/styles.css
    - paperforge/plugin/tests/canvas-render.test.mjs
    - paperforge/plugin/tests/canvas-card-dom.test.mjs
subsystem: reading-canvas
---

# Phase ANN14 Plan 02: Namespaced Connector SVG Layer and CSS Summary

Adds the focused connector presentation surface: namespaced SVG layer with path rendering helpers and restrained CSS that renders a single selected or hovered exact connector. No runtime measurement, listeners, or lifecycle.

## Tasks Executed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Render an empty namespaced connector layer | `feat` | `6331313` | ✅ Done |
| 2 | Render only focused exact connector paths | `test` | `10a708f` | ✅ Done |
| 3 | Add restrained connector CSS and narrow forbidden assertions | `feat` | `979af82` | ✅ Done |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `6331313` | feat | Add namespaced connector SVG layer rendering helpers to render.js + index.js |
| `10a708f` | test | Add connector layer render tests for Tasks 1 and 2 in canvas-render.test.mjs |
| `979af82` | feat | Add restrained connector CSS in styles.css; update DOM test CSS assertions |

## Files Modified

### `paperforge/plugin/src/canvas/render.js`
- Added `require('./connectors')` for `CONNECTOR_STATES` constant
- Added `renderCanvasConnectorLayer(containerEl)` — creates an empty namespaced SVG layer with `paperforge-canvas-connector-layer` class, `aria-hidden="true"`, `role="presentation"`. Returns the SVG element for later updates.
- Added `updateCanvasConnectorLayer(layerEl, connectorState, modifier)` — clears existing paths then renders at most one `<line>` element when connector state is `VISIBLE`, with `paperforge-canvas-connector` base class and `--selected` or `--hovered` modifier. Hidden connector states leave the layer empty.
- Exported both new functions.

### `paperforge/plugin/src/canvas/index.js`
- Imported `renderCanvasConnectorLayer` and `updateCanvasConnectorLayer` from render module.
- Exported both in the module entry point.

### `paperforge/plugin/styles.css`
- Added `SECTION 42` block with connector CSS rules under `.paperforge-reading-canvas-view`:
  - `.paperforge-canvas-connector-layer`: absolute positioning, overflow visible, pointer-events none, z-index 5
  - `.paperforge-canvas-connector`: thin solid stroke (1.5px), `var(--text-muted)` color, fill none, stroke-linecap round, pointer-events none
  - `.paperforge-canvas-connector--hovered`: opacity 0.35
  - `.paperforge-canvas-connector--selected`: opacity 0.55
  - No transitions, animations, markers, arrowheads, or color-following (per D-10/D-11/D-12)

### `paperforge/plugin/tests/canvas-render.test.mjs`
- Added `renderCanvasConnectorLayer` and `updateCanvasConnectorLayer` to the import.
- **Task 1 tests** (`ANN14-02 Task 1 — renderCanvasConnectorLayer`): 8 tests verifying:
  - Creates namespaced SVG layer element
  - Sets aria-hidden and role=presentation
  - Creates no connector path by default
  - Returns SVG element for later updates
  - Does not appear in idle, empty, missing-paper, or unsupported shell states (D-13/D-17/D-20)
- **Task 2 tests** (`ANN14-02 Task 2 — updateCanvasConnectorLayer`): 15 tests verifying:
  - Renders at most one line for visible connector state (D-03)
  - Line uses --selected or --hovered modifier class based on parameter
  - Line endpoint coordinates match cardEndpoint and anchorEndpoint
  - Line has aria-hidden attribute
  - Renders nothing for all hidden states: page-level, unresolved, no-focus, stale, missing-dom, hidden-candidate (D-01/D-02/D-13/D-17)
  - Replaces previous connector path on update
  - Guards against null, undefined, and missing endpoints
  - Connector classes do not leak into ANN12 anchor render (D-22/D-24)
  - Connector classes do not leak into ANN12 source surface (D-22/D-24)
  - Default modifier is --selected when none provided

### `paperforge/plugin/tests/canvas-card-dom.test.mjs`
- Updated CSS content test: was `has no paperforge-canvas-connector classes [D-22]`, now `defines namespaced connector CSS under .paperforge-reading-canvas-view [ANN14-02]` — verifies connector CSS classes exist and are namespaced under `.paperforge-reading-canvas-view`
- Updated SVG geometry test: clarified that ANN12 SVG rules remain forbidden, ANN14 connector SVG class-based selectors are allowed

## Deviations from Plan

- **None** — plan executed exactly as written. All 3 tasks completed with atomic commits.

## Verification

- `node --check src/canvas/render.js` — PASS
- `node --check src/canvas/index.js` — PASS
- `npm test -- canvas-render.test.mjs` — **114 tests passed** (includes 23 new ANN14-02 tests)
- `npm test -- canvas-card-dom.test.mjs` — **49 tests passed** (includes updated CSS assertions)
- **Total: 163 tests pass across both suites**

## Key Decisions

- **Connector state import**: render.js imports `CONNECTOR_STATES` directly from `./connectors` rather than threading through index.js, keeping the dependency explicit and avoiding circular imports.
- **CSS class-name constants**: Defined as local variables in render.js rather than shared from a constants file, keeping the CSS class convention local to the render module.
- **Modifier parameter**: `updateCanvasConnectorLayer` accepts an explicit `modifier` string ('selected' or 'hovered') since the geometry output from `measureConnectorGeometry()` does not carry the selection type. Defaults to 'selected'.
- **SVG element type**: Uses `<line>` rather than `<path>` since connectors are always straight lines between card and anchor endpoints (closest-facing edge midpoints).

## Self-Check: PASSED

All created files verified via `Test-Path`, all commits confirmed in `git log`, all tests pass (163/163). No shared orchestrator artifacts modified.
