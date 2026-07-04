# Phase ANN11: Annotation Card View-Models and Layout - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase ANN11 turns existing paper-scoped annotation state into safe, deterministic side-lane card models for the PaperForge Reading Canvas.

In plain terms: this phase makes the canvas show read-only annotation cards in left/right lanes around the central reading surface, with enough metadata and source identity preserved for later anchor, navigation, and connector phases.

This phase does not implement source anchors, card-to-source navigation, source-to-card navigation, connector lines, draggable/freeform layout, persistent layout state, local annotation editing, Zotero write-back, AI cards, or new annotation import/apply flows.

</domain>

<decisions>
## Implementation Decisions

### Card Information Density
- **D-01:** Annotation cards should always show the selected text preview, comment preview, page, color/type, source/provenance line, and read-only status.
- **D-02:** The card should feel compact enough to sit beside a central reading surface, but it must not hide the core evidence fields needed to recognize the annotation.
- **D-03:** Phase ANN11 should not add expandable details, drawers, popovers, editable forms, or local card mutation flows. A later phase may add richer interaction after card/source navigation exists.
- **D-04:** Missing selected text or missing comment values should render as explicit, quiet placeholders rather than disappearing or collapsing the card.

### Deterministic Side-Lane Placement
- **D-05:** Cards are sorted by stable reading/source order before lane assignment.
- **D-06:** Within the same page or source group, original source/order metadata should be preserved when available; otherwise the implementation may fall back to stable normalized annotation identity/order.
- **D-07:** Lane assignment should alternate cards between left and right lanes after sorting, producing a balanced reference-UI-like reading canvas without storing layout state.
- **D-08:** Phase ANN11 must not introduce draggable cards, random layout, user-persisted lane choices, localStorage/settings persistence, or Obsidian `.canvas` persistence.
- **D-09:** The planner may choose exact tie-breakers, but the result must be deterministic for the same annotation input.

### Explicit Canvas States
- **D-10:** The canvas shell keeps a central status/surface area while side lanes render card content only when annotation data is loaded and usable.
- **D-11:** Loaded, empty, missing paper, missing annotation database, missing source, command failure, refresh, and stale-result states must be explicit view-model states.
- **D-12:** Error and stale states should never masquerade as an empty annotation list.
- **D-13:** During refresh, existing cards may remain visible only if clearly marked as refreshing/stale-safe; otherwise the renderer should show a clear refreshing state.
- **D-14:** Missing source or unsupported future anchoring should preserve card visibility when annotation metadata is otherwise valid, but the card must expose source/provenance limitations for later phases.

### Long Text, CJK, and Layout Resilience
- **D-15:** Selected text and comment previews should use bounded line counts, safe wrapping, and maximum card height so long content cannot stretch lanes or resize the canvas unexpectedly.
- **D-16:** CJK-heavy content must wrap naturally and avoid overlap, clipped controls, negative spacing tricks, or viewport-scaled font behavior.
- **D-17:** Cards should use stable dimensions and CSS constraints that keep hover/focus/read-only/status elements from shifting the lane layout.
- **D-18:** Phase ANN11 should test long selected text, long comments, missing values, and CJK-heavy values at the view-model and DOM level.

### Read-Only and Provenance Signals
- **D-19:** Cards must visibly communicate read-only status in a restrained way, such as a small badge or metadata chip.
- **D-20:** Cards should preserve source, attachment/provenance, page, type, and color metadata needed by later evidence workflows.
- **D-21:** Card interactions may support selection/focus styling as a future navigation affordance, but Phase ANN11 must not expose create, edit, delete, save, import, apply, or write-back controls.
- **D-22:** Tests should assert forbidden controls/verbs are absent from card rendering and interactions, mirroring the v0.2 annotation list safety gate.

### the agent's Discretion
The user approved the recommended choices for card density, lane placement, state handling, long/CJK text behavior, and read-only/provenance signaling. The planner may choose exact function names, CSS class names, DOM structure, placeholder copy, tie-breaker order, and focused test filenames as long as the decisions above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` - Current annotation v0.3 goal, target features, read-only scope, and previous v0.2 harness caveat.
- `.planning/REQUIREMENTS.md` - CANVAS-03, CANVAS-04, CARD-01, CARD-02, CARD-03, CARD-04, SAFE, and TEST requirements that define Phase ANN11 boundaries.
- `.planning/ROADMAP.md` - Phase ANN11 goal, dependencies, requirements, success criteria, and deferred later phases.
- `.planning/STATE.md` - Current milestone position and known blockers/concerns.

### v0.3 Research
- `.planning/research/SUMMARY.md` - Research synthesis recommending deterministic left/right card lanes, read-only cards, provenance preservation, and no persistent layout state.
- `.planning/research/ARCHITECTURE.md` - Canvas module seam recommendation including future `view-model.js` and `layout.js`.
- `.planning/research/PITFALLS.md` - Risks around duplicate annotation runtime, wrong-paper stale renders, read-only boundary breaches, and misleading evidence claims.
- `.planning/research/STACK.md` - Confirms existing Obsidian/CommonJS/Vitest stack and plain DOM/CSS are sufficient for card rendering.

### Prior Annotation Decisions
- `.planning/phases/ANN10/annotation-10-CONTEXT.md` - Canvas entry point, explicit paper identity, `src/canvas/*` module boundaries, shell states, and ANN11 deferral.
- `.planning/phases/ANN10/ANN10-01-PLAN.md` - Planned canvas contract modules and pure tests that ANN11 should build on after ANN10 execution.
- `.planning/phases/ANN10/ANN10-02-PLAN.md` - Planned runtime ItemView/button/shell wiring that ANN11 should not duplicate.
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md` - Annotation bridge source-of-truth, load states, normalized row shape, and CLI JSON contract.
- `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md` - Read-only annotation list, session-only UI state, fallback behavior, and no edit/write-back boundary.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` - Source PDF resolution, page navigation fallback, attachment identity safety, and read-only navigation behavior.
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md` - Strict source identity and v0.2 fallback preservation.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - Automated v0.2 verification status and pending live Obsidian overlay harness note.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - Existing Obsidian plugin runtime and, after ANN10, expected Reading Canvas runtime integration point.
- `paperforge/plugin/src/testable.js` - Existing normalized annotation helpers, list view-model, UI state, navigation, and overlay testable contracts.
- `paperforge/plugin/src/canvas/*` - Expected ANN10 canvas module area; ANN11 should extend this area rather than duplicate logic in `main.js`.
- `paperforge/plugin/styles.css` - Existing PaperForge plugin CSS namespace and annotation section styling; ANN11 should add namespaced canvas/card styles.
- `paperforge/plugin/tests/annotation-bridge.test.mjs` - Annotation bridge contract tests.
- `paperforge/plugin/tests/annotation-list-viewmodel.test.mjs` - Existing list view-model and edge-case text/state coverage to reuse as a model.
- `paperforge/plugin/tests/annotation-section-dom.test.mjs` - Existing DOM tests for annotation rows, long/CJK text, and forbidden controls.
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` - Runtime wiring tests for annotation UI behavior that should remain unregressed.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `normalizeAnnotationExportRow()` in `paperforge/plugin/src/testable.js` defines the normalized annotation row shape that card models should consume indirectly through existing contracts.
- `buildAnnotationListViewModel()` and `createDefaultAnnotationListUiState()` already encode many v0.2 loaded/empty/error/read-only list display decisions; ANN11 should reuse the lessons without turning canvas cards into another sidebar list.
- Existing annotation DOM tests assert `.paperforge-annotation-selected-text`, `.paperforge-annotation-comment`, long text behavior, and forbidden controls. ANN11 should mirror those safety ideas for `.paperforge-reading-canvas-*` / `.paperforge-canvas-*` classes.
- ANN10 is expected to provide canvas-owned context, annotation wrapping, controller, and render shell modules. ANN11 should add/extend card view-model and layout seams there.

### Established Patterns
- The plugin is CommonJS and Obsidian desktop-only; new modules should use `require()`/`module.exports`.
- Existing UI helpers prefer explicit state objects or `{ ok, reason }` results for ordinary invalid/missing user states.
- PaperForge annotation display is read-only. Any edit/delete/create/write-back affordance in Phase ANN11 is a regression.
- Focused v0.2 annotation gates remain the regression baseline; ANN11 tests should be additive.

### Integration Points
- `paperforge/plugin/src/canvas/view-model.js` is the likely home for card models and explicit canvas/card state projection.
- `paperforge/plugin/src/canvas/layout.js` is the likely home for deterministic side-lane assignment.
- `paperforge/plugin/src/canvas/render.js` should render card lanes once ANN10 shell rendering exists.
- `paperforge/plugin/styles.css` should receive bounded, namespaced styles for card lanes, card previews, metadata rows, read-only badges, and CJK/long-text wrapping.

</code_context>

<specifics>
## Specific Ideas

- The target UI direction remains the user-provided dark reading canvas: central reading content, left/right annotation cards, and eventually colored evidence relationships.
- For ANN11, the visual step toward that target is side-lane cards around the central canvas, not connectors or exact text anchors.
- The user approved a compact card model with visible evidence fields, deterministic left/right reading-order alternation, explicit status handling, CJK-safe bounded previews, and restrained read-only/provenance badges.

</specifics>

<deferred>
## Deferred Ideas

- Source anchors belong to Annotation Phase ANN12.
- Bidirectional card/source navigation belongs to Annotation Phase ANN13.
- Connector lines and final visual polish belong to Annotation Phase ANN14.
- Final canvas verification and live harness record belong to Annotation Phase ANN15.
- Expandable details, draggable/freeform card layout, persistent lane choices, local annotation editing, Zotero write-back, AI-generated cards, multi-paper boards, and Obsidian `.canvas` persistence remain future scope.

</deferred>

---

*Phase: ANN11-annotation-card-view-models-and-layout*
*Context gathered: 2026-07-04*
