---
phase: ANN14
plan: ANN14-01
type: execute
status: planned
wave: 1
depends_on: []
files_modified:
  - paperforge/plugin/src/canvas/connectors.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-connectors.test.mjs
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
  - D-17
  - D-19
  - D-20
must_haves:
  truths:
    - "D-01/D-02/D-03: Connector eligibility is exact-only, selected-or-hovered-only, and page-level/unresolved anchors return hidden states instead of weak lines."
    - "D-04/D-19/D-20: Eligibility consumes PaperForge card/anchor state from ANN12/ANN13 and does not inspect native Obsidian PDF DOM or recompute anchor precision."
    - "D-05/D-07/D-08/D-14/D-15: Geometry is derived from current DOMRect-like endpoint rectangles and hides on missing, zero-size, stale, offscreen, clipped, or unreadable geometry without viewport-edge hints."
    - "D-06/D-09/D-17: Helper outputs are transient derived presentation state suitable for recomputation and cleanup after selection, hover, refresh, paper change, and teardown."
  artifacts:
    - path: "paperforge/plugin/src/canvas/connectors.js"
      provides: "Pure connector eligibility, hidden-reason, and DOMRect geometry helpers"
    - path: "paperforge/plugin/src/canvas/index.js"
      provides: "CommonJS export surface for focused connector helpers"
    - path: "paperforge/plugin/tests/canvas-connectors.test.mjs"
      provides: "Focused helper coverage for exact-only eligibility and conservative geometry"
  key_links:
    - from: "paperforge/plugin/src/canvas/navigation.js"
      to: "paperforge/plugin/src/canvas/connectors.js"
      via: "selectedCardId/selectedAnchorId and hover input become focused connector candidates"
      pattern: "selectedCardId|selectedAnchorId"
    - from: "paperforge/plugin/src/canvas/anchors.js"
      to: "paperforge/plugin/src/canvas/connectors.js"
      via: "anchor.status is consumed exactly; no anchor resolver is called"
      pattern: "status === 'exact'"
---

# ANN14-01 Plan: Pure Connector Eligibility and Geometry Helpers

## Objective

Create the pure helper layer that decides whether a focused connector may exist and converts measured PaperForge-owned endpoint rectangles into connector geometry. This plan creates no DOM rendering, CSS, runtime listeners, or Obsidian integration.

## Scope

- New `paperforge/plugin/src/canvas/connectors.js`.
- Export connector helpers from `paperforge/plugin/src/canvas/index.js`.
- New focused unit tests in `paperforge/plugin/tests/canvas-connectors.test.mjs`.

## Out of Scope

- No SVG rendering, CSS, event listeners, `getBoundingClientRect()` calls, `requestAnimationFrame`, or Obsidian workspace APIs.
- No native Obsidian PDF DOM anchoring, page-level/unresolved connector lines, offscreen hints, edge-cropped lines, persistence, mutation controls, write-back, fuzzy matching, or anchor re-resolution.

## Tasks

### Task 1: Define Exact-Only Connector Eligibility

**Files:** `src/canvas/connectors.js`, `tests/canvas-connectors.test.mjs`

**Action:** Create a CommonJS helper module with exported constants for visible and hidden connector states plus `computeFocusedConnectorCandidate(input)`. The helper must accept current navigation state, optional hover state, current card list/map, and current paper key. It must prefer selected state over hover when both are present, require the card and anchor IDs to resolve to the same current card, require `card.anchor.status === 'exact'`, and return hidden reasons for page-level, unresolved, source-unavailable, unsupported, stale, missing-card, missing-anchor, missing-DOM, and mismatched IDs per D-01/D-02/D-03/D-04/D-19/D-20. It must not import or call `resolveCanvasAnchor`, read native PDF viewer selectors, or infer precision from source text.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check src/canvas/connectors.js
npm.cmd test -- canvas-connectors.test.mjs
Pop-Location
```

**Done:** Tests prove exact selected and exact hovered pairs return connector candidates; page-level, unresolved, missing, stale, unsupported, source-unavailable, and mismatched pairs return hidden states with explicit reasons and no geometry.

### Task 2: Implement Conservative DOMRect Geometry

**Files:** `src/canvas/connectors.js`, `tests/canvas-connectors.test.mjs`

**Action:** Add `measureConnectorGeometry(input)` over DOMRect-like `canvasRect`, `cardRect`, and `anchorRect` objects. It must compute connector endpoints in the Reading Canvas coordinate frame only after all rectangles are present, non-zero, finite, and within the visible canvas bounds. If either endpoint is outside or clipped beyond the visible canvas region, if the canvas has unreadable narrow dimensions, or if input has stale/hidden candidate state, it must return hidden rather than guessing, clipping to edges, or adding direction hints per D-05/D-07/D-08/D-14/D-15/D-17.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-connectors.test.mjs
Pop-Location
```

**Done:** Tests cover valid left/right geometry, zero-size endpoints, missing rectangles, non-finite values, endpoint outside canvas, endpoint clipped by canvas bounds, narrow canvas, and hidden candidate input.

### Task 3: Export Connector Contracts Without Runtime Coupling

**Files:** `src/canvas/connectors.js`, `src/canvas/index.js`, `tests/canvas-connectors.test.mjs`

**Action:** Export only the narrow ANN14 helper surface from `index.js`: eligibility constants, `computeFocusedConnectorCandidate`, and `measureConnectorGeometry`. Keep helper outputs serializable plain objects with no DOM element references, timers, Obsidian objects, persisted layout fields, or mutation/write-back fields per D-04/D-17/D-18/D-20.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check src/canvas/index.js
npm.cmd test -- canvas-connectors.test.mjs canvas-navigation.test.mjs
Pop-Location
```

**Done:** `src/canvas/index.js` exposes the helpers; connector helper objects JSON-serialize cleanly; ANN13 navigation tests still pass.

## Acceptance Criteria

- CONN-01 and CONN-02 have pure, testable exact-only connector decisions.
- CONN-03 has pure geometry hidden-state foundations for future runtime recomputation.
- D-01 through D-09, D-14, D-15, D-17, D-19, and D-20 are covered before any SVG or runtime work exists.
