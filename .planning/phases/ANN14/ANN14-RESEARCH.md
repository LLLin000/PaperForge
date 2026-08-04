# ANN14 Research: Focused Connector Layer and Visual Polish

## Research Complete

ANN14 can be planned as a focused presentation layer on top of ANN12 anchors and ANN13 navigation. The existing code already provides the required identity and lifecycle surface:

- `paperforge/plugin/src/canvas/anchors.js` owns exact/page-level/unresolved precision semantics.
- `paperforge/plugin/src/canvas/navigation.js` owns selected card/source/page-group state and lifecycle clearing.
- `paperforge/plugin/src/canvas/render.js` already renders `data-card-id`, `aria-selected`, `data-anchor-id`, and `data-anchor-status` on PaperForge-owned Reading Canvas DOM elements.
- `paperforge/plugin/main.js` already delegates click/keydown events, applies selected card state, uses `scrollIntoView`, and has existing `getBoundingClientRect()` patterns for local overlay placement.
- `paperforge/plugin/styles.css` already has a Reading Canvas namespace, selected-card styling, source-anchor styling, and fallback button styling.

## Key Implementation Findings

### Eligibility

Connector eligibility should be a pure decision before any DOM measurement. Inputs should be the current navigation state, optional hovered card/anchor id, and card anchor metadata already produced by the canvas view-model. A connector candidate is allowed only when:

- the interaction source is selected or hovered;
- the card id and anchor id resolve to the same card;
- the card has an anchor with `status === 'exact'`;
- the source/card are current for the loaded canvas view-model.

The helper should return hidden for page-level, unresolved, stale, missing-card, missing-anchor, source-unavailable, unsupported, unmeasured, and mismatched ids. It must not call anchor resolution again and must not inspect native Obsidian PDF viewer DOM.

### Geometry

Geometry should be measured from PaperForge-owned DOM only:

- card endpoint: `[data-card-id="<id>"]`;
- anchor endpoint: `[data-anchor-id="<id>"][data-anchor-status="exact"]`;
- coordinate frame: the Reading Canvas root or a dedicated connector layer root.

The measurement helper should accept DOMRect-like objects so unit tests can verify zero-size, offscreen, and clipped cases without a browser. If either endpoint or the canvas bounds are missing, zero-size, stale, or outside the visible canvas bounds, it should return hidden rather than estimating.

### Rendering

`render.js` should add a stable, namespaced connector layer container to the loaded Reading Canvas shell or source/card canvas area. Runtime can update its children after measurement. Use an SVG element inside `.paperforge-reading-canvas-view` with namespaced classes such as `paperforge-canvas-connector-layer`, `paperforge-canvas-connector`, and `paperforge-canvas-connector--selected`.

The visual language should be deliberately restrained: thin solid line, low opacity, selected slightly stronger than hover, no arrows, no endpoint dots, no animation, no annotation color palette.

### Runtime Lifecycle

`PaperForgeReadingCanvasView` should own transient connector state because it already owns the current VM, content root, delegated event handlers, selection state, refresh, paper change, and teardown.

Likely runtime responsibilities:

- track hovered card/anchor id as transient fields;
- update connector after selection, hover enter/leave, scroll, resize, render refresh, paper changes, and teardown;
- schedule measurement with a single pending animation frame or similarly conservative throttle;
- clear connector layer on stale render, unsupported state, refresh start if endpoints are unavailable, paper change, teardown, and Escape;
- preserve ANN13 selected/focus/fallback behavior when connector is hidden.

### Tests

Focused test coverage should be split by responsibility:

- pure connector helper tests in a new `canvas-connectors.test.mjs`;
- render tests proving the connector layer exists only in the Reading Canvas namespace and does not appear for legacy card-only assertions/page-level/unresolved states;
- runtime tests proving selected/hovered exact endpoints update the layer while page-level, unresolved, missing, zero-size, offscreen, refresh, resize, paper change, and teardown hide it;
- forbidden-scope tests adjusted from ANN12/ANN13 so connector/SVG is allowed only for the focused connector layer and still forbidden for mutation controls, native PDF DOM coupling, page-level/unresolved connector lines, and persistent layout.

## Recommended Plan Split

1. `ANN14-01`: Pure connector eligibility and geometry helpers.
2. `ANN14-02`: Namespaced SVG layer rendering and restrained CSS.
3. `ANN14-03`: Runtime measurement, hover/selection updates, and lifecycle cleanup.
4. `ANN14-04`: Responsive/readability hardening, forbidden-scope scans, and validation matrix.

## Risks

- Existing ANN12/ANN13 tests intentionally assert absence of connector/SVG strings. ANN14 must narrow these assertions so they still catch forbidden leakage without blocking the intended focused connector layer.
- DOM measurement in jsdom requires test doubles for `getBoundingClientRect`; avoid relying on actual layout.
- Connector lines can accidentally imply stronger grounding than the data supports. Eligibility and hidden reasons should stay conservative and should not include page-level/unresolved fallback lines.
- Runtime listeners should be cleaned up with existing navigation cleanup to avoid stale lines after view teardown.

## Research Complete
