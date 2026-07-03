# Annotation Phase 10: Canvas Data Contract and View Registration - Context

**Gathered:** 2026-07-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 10 establishes the Visual Reading Canvas foundation. It adds a PaperForge-owned Obsidian `ItemView`, explicit paper identity, a minimal open path, canvas module seams, and a shell-level render lifecycle that can load or represent annotation state through the existing v0.2 contracts.

In plain terms: this phase makes it possible to open a read-only Reading Canvas for one known paper and prove that the view, context, annotation bridge, stale guards, and shell states are wired correctly.

This phase does not implement annotation cards, source anchors, bidirectional navigation, connector lines, full visual polish, local annotation editing, Zotero write-back, persistent layout state, Obsidian `.canvas` files, or native PDF overlay reliability.

</domain>

<decisions>
## Implementation Decisions

### Canvas Entry Points
- **D-01:** The primary user entry point is a PaperForge paper panel button near the current paper context, labelled along the lines of `Open Reading Canvas`.
- **D-02:** The secondary entry point is a command palette command, labelled along the lines of `PaperForge: Open Reading Canvas for active paper`.
- **D-03:** Phase 10 should not add a global canvas browser, global paper picker, or sidebar-level canvas navigation. Those would introduce a separate paper-selection workflow outside this phase.
- **D-04:** The paper panel button opens the canvas for the exact paper represented by the current panel entry; it must not re-guess paper identity from the active file.
- **D-05:** The command palette entry may use the existing active-paper resolution path. If no active paper can be resolved, it should show a concise Notice asking the user to open a recognized paper note or PDF first.

### Paper Identity and View State
- **D-06:** A Reading Canvas view is bound to one explicit `paperKey`.
- **D-07:** When opened from paper mode, the canvas uses the current panel `entry.key` as the authoritative paper identity.
- **D-08:** The canvas `ItemView` stores its own explicit `paperKey`/context state and does not rely on live global `_currentPaperKey` drift after opening.
- **D-09:** If the active paper changes elsewhere in Obsidian, an already-open canvas does not automatically switch to the new paper.
- **D-10:** To view a different paper, the user opens or activates a canvas from that paper's own panel or command context.
- **D-11:** All canvas annotation loading, refresh, stale-result checks, and teardown behavior must key off the canvas-owned paper identity.

### Module Boundaries
- **D-12:** Add a new `paperforge/plugin/src/canvas/` module area for Phase 10 canvas code.
- **D-13:** Phase 10 should create the minimal module set: `context.js`, `annotations.js`, `controller.js`, `render.js`, and `index.js`.
- **D-14:** `context.js` owns open/context resolution and returns explicit objects such as `{ ok, paperKey, entry, reason }`.
- **D-15:** `annotations.js` is a thin wrapper around existing v0.2 annotation loader/state contracts. It must not add direct SQLite reads, direct Zotero access, or new Python subprocess APIs.
- **D-16:** `controller.js` owns the canvas session lifecycle, fixed paper identity, stale guards, refresh coordination, and teardown.
- **D-17:** `render.js` owns only shell-level DOM for Phase 10: loading, empty, missing-paper, command-failure, missing-source, and unsupported states. Card lanes, source anchors, navigation, and connectors are later phases.
- **D-18:** `index.js` provides a narrow CommonJS export surface for the canvas module.
- **D-19:** `main.js` should remain a thin Obsidian runtime integration layer: view type constant, `ItemView` class, command registration, paper panel button, and minimal delegation into `src/canvas/*`.
- **D-20:** If the shipped Obsidian runtime cannot reliably require `src/canvas/*`, Phase 10 may temporarily inline canvas helper code in `main.js`, but the plan must record this as debt and add parity/runtime tests to prevent helper drift.

### Test and Completion Standard
- **D-21:** Pure helper tests should cover `context.js` paperKey/entry resolution, missing paper, invalid entry, and user-facing reason messages.
- **D-22:** Pure helper tests should prove `annotations.js` wraps existing v0.2 annotation contracts and does not introduce new DB/API/subprocess contracts.
- **D-23:** Controller tests should cover fixed `paperKey`, stale result discard, refresh coordination, and teardown.
- **D-24:** Render tests should cover canvas shell/loading/empty/error/unsupported states and assert no edit, delete, save, import, apply, or write-back controls appear.
- **D-25:** Runtime/DOM tests should cover registration of `VIEW_TYPE_PAPERFORGE_READING_CANVAS`, command availability, paper panel button availability, and the canvas `ItemView` rendering with explicit `paperKey`.
- **D-26:** Phase 10 verification should run `node --check main.js` and the focused v0.2 annotation test gate to prove list/jump/overlay fallback behavior remains intact.
- **D-27:** Phase 10 does not require annotation card rendering, source anchors, connector geometry, full visual styling, or a successful live native PDF overlay harness.
- **D-28:** Phase 10 docs/plans must keep the v0.2 live native PDF overlay harness pending status explicit so canvas confidence is not confused with native overlay confidence.

### the agent's Discretion
The user approved the recommended choices for entry points, paper identity, module boundaries, and test gates. The planner may choose exact function names, class names, CSS class names, command IDs, and test file names as long as the decisions above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` - Current annotation v0.3 goal, target features, read-only scope, and previous v0.2 harness caveat.
- `.planning/REQUIREMENTS.md` - CANVAS-01, CANVAS-02, SAFE, and TEST requirements that define Phase 10 boundaries.
- `.planning/ROADMAP.md` - Annotation Phase 10 goal, dependencies, requirements, success criteria, and research flags.
- `.planning/STATE.md` - Current milestone position and known blockers/concerns.

### v0.3 Research
- `.planning/research/SUMMARY.md` - Research synthesis recommending a PaperForge-owned `ItemView`, CommonJS `src/canvas/*`, plain DOM/SVG, and no new framework/API for MVP.
- `.planning/research/ARCHITECTURE.md` - Canvas module seam recommendation and warning against native PDF DOM dependency.
- `.planning/research/PITFALLS.md` - Risks around duplicate annotation runtime, helper drift, stale async renders, and read-only boundary breaches.
- `.planning/research/STACK.md` - Stack additions/non-additions; confirms existing Obsidian/CommonJS/Vitest stack is sufficient.

### Prior Annotation Decisions
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md` - Annotation bridge source-of-truth, load states, normalized row shape, and CLI JSON contract.
- `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md` - Read-only annotation list, session-only UI state, fallback behavior, and no edit/write-back boundary.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` - Source PDF resolution, page navigation fallback, attachment identity safety, and read-only navigation behavior.
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md` - Risk-gated overlay decisions, strict source identity, and v0.2 fallback preservation.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - Automated v0.2 verification status and pending live Obsidian overlay harness note.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - Existing Obsidian plugin runtime, `PaperForgeStatusView`, annotation state, paper mode rendering, command registration, and overlay lifecycle.
- `paperforge/plugin/src/testable.js` - Existing testable annotation loader/state/list/navigation/overlay helpers and CommonJS export style.
- `paperforge/plugin/styles.css` - Existing PaperForge plugin CSS namespace and annotation section styling.
- `paperforge/plugin/tests/annotation-bridge.test.mjs` - Annotation bridge contract tests.
- `paperforge/plugin/tests/annotation-navigation.test.mjs` - Annotation PDF target and navigation fallback tests.
- `paperforge/plugin/tests/annotation-overlay.test.mjs` - Overlay helper tests that Phase 10 must not regress.
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` - Runtime wiring tests for main.js annotation behavior.
- `paperforge/plugin/tests/annotation-section-dom.test.mjs` - DOM tests for annotation section, forbidden controls, and runtime fallback behavior.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `loadAnnotationsForPaper()` and `makeAnnotationState()` in `paperforge/plugin/src/testable.js` provide the v0.2 annotation source-of-truth that `src/canvas/annotations.js` should wrap.
- `createAnnotationLifecycleController()` and `_annotationLoadSeq` patterns already model active-paper stale guards; Phase 10 should adapt the idea to a canvas-owned fixed `paperKey`.
- `resolveAnnotationPdfTarget()` and `_openAnnotationPdf()` remain fallback/navigation assets for later phases, but Phase 10 should not depend on them for canvas shell registration.
- Existing annotation section DOM tests include forbidden-control assertions that can be mirrored for canvas shell safety.

### Established Patterns
- The plugin is CommonJS and Obsidian desktop-only; new plugin modules should use `require()`/`module.exports`.
- `main.js` is the shipped Obsidian entrypoint, while `src/testable.js` contains pure helper contracts for Vitest. Phase 10 must avoid growing untested helper drift between these surfaces.
- Plugin UI helpers return stable state objects or `{ ok, reason }` results instead of throwing for ordinary user-facing invalid states.
- User-facing annotation display is read-only. Any edit/delete/create/write-back verbs in Phase 10 canvas UI are a regression.

### Integration Points
- `PaperForgePlugin.onload()` is where the new view type and command should be registered.
- `PaperForgeStatusView._renderPaperMode()` or its paper header/annotation area is the likely location for the paper panel button.
- A new `PaperForgeReadingCanvasView` should extend Obsidian `ItemView` and own its session context.
- Existing focused v0.2 annotation tests should remain the regression gate after Phase 10 implementation.

</code_context>

<specifics>
## Specific Ideas

- The desired product direction is the user-provided reference UI: dark reading canvas, central reading content, side annotation cards, and colored relationship lines. Phase 10 only lays the view/data foundation for that direction.
- The first visible canvas can be plain and shell-level, but it should already feel like a distinct PaperForge Reading Canvas rather than another sidebar list.
- A canvas is treated as a paper reading workspace, not as a live mirror of whatever paper is currently active elsewhere.

</specifics>

<deferred>
## Deferred Ideas

- Annotation card layout belongs to Annotation Phase 11.
- Source anchors belong to Annotation Phase 12.
- Bidirectional card/source navigation belongs to Annotation Phase 13.
- Connector lines and visual polish belong to Annotation Phase 14.
- Final canvas verification and live harness record belong to Annotation Phase 15.
- Global canvas browser, paper picker, persistent draggable layout, Obsidian `.canvas` persistence, local annotation editing, Zotero write-back, AI cards, and multi-paper boards remain future scope.

</deferred>

---

*Phase: annotation-10-canvas-data-contract-and-view-registration*
*Context gathered: 2026-07-03*
