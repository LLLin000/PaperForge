---
phase: ANN14
plan: ANN14-01
type: execute
status: complete
wave: 1
depends_on: []
requirements:
  - CONN-01
  - CONN-02
  - CONN-03
requirements_addressed:
  - CONN-01
  - CONN-02
  - CONN-03
decision_coverage:
  - D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09
  - D-14, D-15, D-17, D-19, D-20
files_created:
  - paperforge/plugin/src/canvas/connectors.js
  - paperforge/plugin/tests/canvas-connectors.test.mjs
files_modified:
  - paperforge/plugin/src/canvas/index.js
tech_stack_added: []
tech_stack_patterns:
  - "CommonJS module pattern (module.exports) matching canvas/navigation.js and canvas/anchors.js"
  - "Pure helper functions with serializable plain object outputs — no DOM refs, timers, Obsidian objects"
  - "Frozen constants (Object.freeze) for state enums"
  - "node --check compile verification on all .js files"
  - "vitest ESM test imports via dynamic import('../src/canvas/connectors.js')"
key_decisions:
  - "Connector eligibility uses exact-only D-01/D-02/D-03 rule: page-level and unresolved anchors always return hidden"
  - "Selected state takes priority over hover per D-03; hover is fallback when selected is empty"
  - "Geometry hides on any invalid state: missing/non-finite/zero-size rects, outside-canvas, narrow canvas"
  - "No DOMRect.getBoundingClientRect() calls or canvas coordinate transforms — accepts pre-measured rects"
  - "Closest-edge endpoint computation via _computeClosestEdge with overlap detection (horizontal/vertical)"
  - "All hidden states return explicit HIDDEN_REASONS for debugging — no silent drops"
duration: ~15 min
completed_date: "2026-07-06"
commits:
  - "2b289a8: feat(ANN14-01): implement connector eligibility and geometry helpers"
  - "f885574: feat(ANN14-01): export connector helpers from canvas/index.js"
---

# Phase ANN14 Plan 01: Pure Connector Eligibility and Geometry Helpers

Implementation of the pure helper layer for focused card-anchor connector decisions and conservative DOMRect geometry. No DOM rendering, CSS, runtime listeners, or Obsidian integration.

## Tasks

| # | Name | Type | Status | Commit | Key Files |
|---|------|------|--------|--------|-----------|
| 1 | Define Exact-Only Connector Eligibility | auto | ✅ Complete | `2b289a8` | `connectors.js`, `canvas-connectors.test.mjs` |
| 2 | Implement Conservative DOMRect Geometry | auto | ✅ Complete | `2b289a8` | `connectors.js`, `canvas-connectors.test.mjs` |
| 3 | Export Connector Contracts Without Runtime Coupling | auto | ✅ Complete | `f885574` | `index.js`, `canvas-connectors.test.mjs` |

## Deliverables

### New file: `paperforge/plugin/src/canvas/connectors.js`

Pure CommonJS module with:

**Constants:**
- `CONNECTOR_STATES` (frozen) — `VISIBLE: 'visible'`, `HIDDEN: 'hidden'`
- `HIDDEN_REASONS` (frozen) — 15 distinct reason strings for all hidden states
- `MIN_CANVAS_DIMENSION` (number: 50)

**Functions:**
- `computeFocusedConnectorCandidate(input)` — exact-only connector eligibility
  - Accepts `{ navState, hoverState, cards, paperKey }`
  - Prefers selected over hover; falls back to hover when selected is empty
  - Requires card.anchor.status === 'exact'; page-level/unresolved → hidden
  - Guards: missing nav, missing card list, missing card, missing anchor, stale, mismatched IDs, no focus
  - Returns serializable `{ state, cardId, anchorId, reason, card, anchor }`

- `measureConnectorGeometry(input)` — conservative DOMRect geometry
  - Accepts `{ candidate, canvasRect, cardRect, anchorRect }`
  - Validates all rects present, non-zero, finite, within visible canvas bounds
  - Hides on: null candidate, hidden candidate, missing rects, zero-size, non-finite, outside-canvas, narrow canvas
  - Computes closest-edge endpoints with overlap-aware edge selection
  - Returns serializable `{ state, cardEndpoint, anchorEndpoint, cardRect (frozen), anchorRect (frozen) }`

### New file: `paperforge/plugin/tests/canvas-connectors.test.mjs`

46 focused unit tests covering:

| Section | Tests | Coverage |
|---------|-------|----------|
| Connector constants | 3 | CONNECTOR_STATES, HIDDEN_REASONS, frozen |
| Exact selected pairs | 3 | Visible candidate, multi-card, serialization |
| Exact hovered pairs | 3 | Selected-preferred, hover-fallback, no-focus |
| Page-level / unresolved | 3 | D-01/D-02 hidden for page-level, unresolved, source-unavailable |
| Missing/stale/mismatched | 9 | Card not found, missing anchor, stale paper, mismatched IDs, missing nav, empty/null cards, no geometry |
| MIN_CANVAS_DIMENSION | 1 | Positive number |
| Valid left/right geometry | 4 | Visible geometry, frozen rects, right-edge endpoint, serialization |
| Zero-size / missing rects | 4 | Zero width/height, negative height, null card/canvas rect |
| Non-finite values | 2 | NaN, Infinity |
| Outside canvas | 2 | Left of canvas, below canvas |
| Narrow canvas | 2 | Too narrow, too short |
| Hidden candidate | 3 | Hidden candidate input, null/undefined candidate |
| Input guards | 2 | Null/undefined input |
| Serialization contract | 4 | JSON-serializes candidates/geometry, no DOM/timer/Obsidian keys |
| No anchor resolver imports | 2 | No resolveCanvasAnchor, narrow 5-key export surface |

### Modified file: `paperforge/plugin/src/canvas/index.js`

Added `require('./connectors')` and exported 5 connector symbols:
- `CONNECTOR_STATES`, `HIDDEN_REASONS`, `MIN_CANVAS_DIMENSION`
- `computeFocusedConnectorCandidate`, `measureConnectorGeometry`

## Verification

| Check | Result |
|-------|--------|
| `node --check src/canvas/connectors.js` | ✅ Pass (no errors) |
| `node --check src/canvas/index.js` | ✅ Pass (no errors) |
| `npm test canvas-connectors.test.mjs` | ✅ 46/46 tests passed |
| `npm test canvas-navigation.test.mjs` | ✅ 28/28 tests passed (regression) |
| Combined: 2 test files | ✅ 74/74 tests passed |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All hidden states have explicit reasons. All geometry paths return proper hidden/visible results.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced. The module is a pure helper with no I/O, DOM, or Obsidian API surface.

## Self-Check: PASSED

- [x] `paperforge/plugin/src/canvas/connectors.js` exists
- [x] `paperforge/plugin/tests/canvas-connectors.test.mjs` exists
- [x] `paperforge/plugin/src/canvas/index.js` modified
- [x] Commit `2b289a8` exists
- [x] Commit `f885574` exists
- [x] 46 connector tests pass
- [x] 28 navigation regression tests pass
- [x] `node --check` passes on both .js files
