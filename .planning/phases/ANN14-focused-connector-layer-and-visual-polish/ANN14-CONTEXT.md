# Phase ANN14: Focused Connector Layer and Visual Polish - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase ANN14 adds the first focused connector layer for the PaperForge Reading Canvas after ANN13's bidirectional navigation work.

In plain terms: when a user selects or hovers a precisely grounded card/source pair, the canvas may draw a restrained connector line between the side annotation card and the exact source anchor. The connector is a visual reading aid and an evidence claim, so it must appear only when both endpoints are exact, visible, current, measurable, and owned by PaperForge's canvas DOM.

This phase also hardens responsive/readable canvas presentation around connector visibility. It does not add always-on relationship webs, page-level connector lines, unresolved connector lines, offscreen direction hints, persistent freeform layout, local annotation editing, Zotero write-back, native Obsidian PDF viewer DOM anchoring, or AI-generated cards.

</domain>

<decisions>
## Implementation Decisions

### Connector Eligibility
- **D-01:** ANN14 should draw connectors only for `exact` anchors. Page-level, unresolved, stale, unsupported, missing-DOM, unmeasured, or source-unavailable anchors must not draw connector lines.
- **D-02:** Connectors appear only for selected or hovered card-anchor pairs. ANN14 must not introduce an always-on web of connector lines.
- **D-03:** Page-level anchors may keep existing page-level selection/group/status styling from ANN13, but must not receive weak connector lines in ANN14. The absence of a line is the honesty signal.
- **D-04:** Connector eligibility must be derived from PaperForge-owned card/anchor state and DOM hooks, not from native Obsidian PDF viewer DOM internals.

### Geometry Lifecycle
- **D-05:** Connector geometry should be measured conservatively from the current DOM rectangles of the selected/hovered card and exact anchor.
- **D-06:** Geometry should be recomputed after explicit selection/hover changes and after scroll, resize, refresh, paper change, and relevant re-render events.
- **D-07:** If either endpoint cannot be measured, has a zero-size rect, is stale, or is outside the canvas-visible region, the connector must be hidden rather than guessed or extended.
- **D-08:** ANN14 should not draw connector lines to viewport edges or use offscreen direction hints. Those would be new UI semantics for a later phase.
- **D-09:** Refresh, stale render, paper change, and teardown must clear or hide connectors so no dangling line remains after underlying card/source state changes.

### Visual Language
- **D-10:** Connector visuals should use a restrained thin solid line with low opacity.
- **D-11:** Selected connectors may be slightly stronger than hovered connectors, but both should remain quiet reading aids rather than graph-like relationship objects.
- **D-12:** ANN14 should not add arrowheads, endpoint dots, annotation-color-following connector palettes, animated paths, or heavy relationship polish.
- **D-13:** Connector classes and SVG elements are allowed in ANN14 only for the focused connector layer. They must be namespaced under the Reading Canvas and must not leak into page-level/unresolved states.

### Responsive Readability
- **D-14:** On narrow layouts, clipped panes, offscreen endpoints, or unreadable measured geometry, connectors should hide conservatively.
- **D-15:** ANN14 should not crop connector lines to visible edges, fade them to imply offscreen continuation, or show directional edge badges.
- **D-16:** Selection/focus/card/source states from ANN13 should remain visible when connectors hide, so users still understand what is selected.
- **D-17:** Connector visibility should be treated as derived presentation state, not persisted layout state.

### Scope and Safety Boundaries
- **D-18:** ANN14 must preserve the read-only boundary: no create, edit, delete, save, import, apply, write-back, evidence mutation, or concept-card mutation controls.
- **D-19:** ANN14 must not change ANN12 anchor precision rules or ANN13 navigation/fallback semantics. It consumes exact selected/hovered relationships; it does not re-resolve or fuzzy-match source text.
- **D-20:** ANN14 should not claim full live native-PDF overlay reliability. Connector work belongs to the PaperForge-owned Reading Canvas; ANN15 remains the broader live verification phase.

### the agent's Discretion
The planner may choose exact helper names, SVG/path construction details, measurement throttling strategy, CSS class names, and test file split as long as the locked eligibility, geometry, visual, responsive, and safety decisions above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` - annotation v0.3 Visual Reading Canvas goal, read-only scope, and connector direction.
- `.planning/REQUIREMENTS.md` - CANVAS-05, CONN-01, CONN-02, CONN-03, TEST-02, TEST-03, and rejected alternatives around always-on connector webs.
- `.planning/ROADMAP.md` - ANN14 goal, dependency on ANN13, success criteria, and ordering rationale.
- `.planning/STATE.md` - Current milestone state, completed ANN12/ANN13 decisions, and connector precision risk note.

### Prior Canvas Phases
- `.planning/phases/ANN13/ANN13-CONTEXT.md` - Locked navigation, selection, fallback, accessibility, read-only, and deferral boundaries that ANN14 must consume.
- `.planning/phases/ANN13/ANN13-01-PLAN.md` - Pure selection/navigation reducers that define selected card/source/page-group state.
- `.planning/phases/ANN13/ANN13-02-PLAN.md` - Fallback eligibility and metadata; useful to avoid connector/fallback scope confusion.
- `.planning/phases/ANN13/ANN13-03-PLAN.md` - DOM hooks, ARIA, selected classes, and fallback button rendering that connector measurement should use.
- `.planning/phases/ANN13/ANN13-04-PLAN.md` - Runtime integration, event delegation, lifecycle, and explicit fallback opening; connector lifecycle should align with these hooks.
- `.planning/phases/ANN13/ANN13-VALIDATION.md` - ANN13 safety gates, including forbidden connector/mutation/native-PDF scans that ANN14 intentionally narrows.
- `.planning/phases/ANN12/ANN12-CONTEXT.md` - Source anchor precision levels and exact/page-level/unresolved semantics.
- `.planning/phases/ANN12/ANN12-VALIDATION.md` - Exact/page-level/unresolved validation matrix and prior connector deferral.

### Codebase Maps
- `.planning/codebase/CONVENTIONS.md` - Plugin CommonJS conventions, DOM safety, naming, and test style.
- `.planning/codebase/STRUCTURE.md` - Where plugin UI/runtime/test code belongs.
- `.planning/codebase/STACK.md` - Obsidian plugin, Vitest, jsdom, and no-new-framework stack constraints.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - `PaperForgeReadingCanvasView`, ANN13 runtime event handling, lifecycle, and existing overlay measurement examples using DOM rects.
- `paperforge/plugin/src/canvas/navigation.js` - ANN13 selection/navigation state surface that connector eligibility should consume.
- `paperforge/plugin/src/canvas/render.js` - Card/source DOM hooks, exact/page-level/unresolved anchors, selected states, and safe DOM rendering.
- `paperforge/plugin/src/canvas/anchors.js` - Exact/page-level/unresolved anchor status contracts; ANN14 must not recompute precision.
- `paperforge/plugin/src/canvas/view-model.js` - Card identity, anchor metadata, lane placement inputs, and read-only card models.
- `paperforge/plugin/src/canvas/index.js` - Canvas module export surface.
- `paperforge/plugin/styles.css` - Reading Canvas card, anchor, selected/focus/fallback styling namespace.
- `paperforge/plugin/tests/canvas-navigation.test.mjs` - Selection and lifecycle contracts that connector eligibility should respect.
- `paperforge/plugin/tests/canvas-render.test.mjs` and `paperforge/plugin/tests/canvas-card-dom.test.mjs` - DOM hook, selected-state, and forbidden-scope regression tests to extend for connectors.
- `paperforge/plugin/tests/canvas-main-runtime.test.mjs` - Runtime integration tests for selection, focus, refresh, teardown, and explicit fallback behavior.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- ANN13 adds focusable card and anchor DOM hooks such as `data-card-id`, `data-anchor-id`, `aria-selected`, and selected classes. ANN14 should measure these existing DOM endpoints instead of inventing a parallel identity layer.
- `paperforge/plugin/src/canvas/anchors.js` already classifies anchors as exact/page-level/unresolved. Connector eligibility should consume this status directly.
- `PaperForgeReadingCanvasView` in `main.js` already handles click/keyboard selection, refresh, teardown, and `scrollIntoView` coordination. Connector lifecycle should attach to the same session lifecycle rather than creating a separate global listener model.
- Existing overlay/popover code in `main.js` already uses `getBoundingClientRect()` for local DOM placement; ANN14 can reuse the pattern but should keep connector measurement scoped to Reading Canvas endpoints.

### Established Patterns
- Canvas modules are CommonJS under `paperforge/plugin/src/canvas/` and exported through `index.js`.
- User-facing text and card/source content use safe text APIs; connector rendering should not use annotation text as HTML.
- Missing, unsupported, stale, or unsafe states should be explicit and conservative, usually hidden or status-only rather than guessed.
- v0.3 remains read-only and session-local; no connector state should persist to settings, localStorage, vault notes, Zotero, or `annotations.db`.
- Focused Vitest/jsdom tests are the primary automated confidence source; live native PDF harness claims remain out of scope until ANN15.

### Integration Points
- A likely pure helper can compute connector eligibility from selected/hovered state plus card/anchor metadata.
- A DOM measurement helper can turn two endpoint elements plus canvas bounds into a connector path, or return hidden with a reason.
- `render.js` can render a namespaced SVG connector layer within the Reading Canvas shell, or expose a stable container for `main.js` to update.
- `main.js` should coordinate scroll/resize/refresh/teardown invalidation and call measurement/render helpers.
- `styles.css` should define restrained connector classes under `.paperforge-reading-canvas-view`, with no heavy graph or relationship-web styling.

</code_context>

<specifics>
## Specific Ideas

- First connector layer should feel like a quiet reading aid, not a graph system.
- Thin solid low-opacity lines are preferred; selected can be slightly stronger than hover.
- No arrowheads, endpoint dots, annotation-color-following connector palette, or animated connector paths in ANN14.
- Page-level and unresolved anchors should be visually honest by not receiving connector lines.
- When in doubt, hide the connector and preserve ANN13 selection/focus state.

</specifics>

<deferred>
## Deferred Ideas

- Page-level weak/dashed connector hints are deferred; ANN14 explicitly does not draw them.
- Offscreen edge indicators, cropped/faded continuation lines, and direction badges are deferred.
- Annotation-color-following connector palettes, endpoint dots, arrowheads, animations, and richer relationship polish are deferred.
- Full live native-PDF harness validation remains ANN15 scope.
- Persistent layout, local annotation editing, Zotero write-back, AI-generated cards, and multi-paper boards remain future scope.

</deferred>

---

*Phase: ANN14-focused-connector-layer-and-visual-polish*
*Context gathered: 2026-07-06*

