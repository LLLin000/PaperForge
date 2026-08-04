# Phase ANN13: Bidirectional Navigation and Fallback Paths - Context

**Gathered:** 2026-07-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase ANN13 makes the PaperForge Reading Canvas navigable after ANN12's source surface and anchor rendering work.

In plain terms: users can move from an annotation card to its supported source anchor, move from a source anchor back to the corresponding card, keep a clear selected state while reading, and use a safe v0.2 PDF page fallback when canvas source navigation cannot honestly locate the source.

This phase does not implement connector lines, connector geometry, SVG relationship paths, local annotation editing, Zotero write-back, persistent layout, native PDF DOM anchoring as the canvas foundation, fuzzy source matching, or new import/apply flows.

</domain>

<decisions>
## Implementation Decisions

### Card to Source Navigation
- **D-01:** Selecting an annotation card with an `exact` anchor should scroll the central source surface to the inline exact highlight.
- **D-02:** Selecting an annotation card with a `page-level` anchor should scroll the central source surface to the page/block marker, not to a guessed sentence or paragraph.
- **D-03:** Selecting an annotation card with an `unresolved` anchor should not scroll the source surface. It should show the unresolved reason and, when eligible, a PDF fallback entry.
- **D-04:** After card-to-source navigation, selected state should remain visible until the user selects another card/source anchor or presses Escape.
- **D-05:** If the target source anchor is not currently present in the DOM, ANN13 must not guess, jump to an approximate location, or auto-fallback to PDF. It should keep the card selected, show a temporary unable-to-locate explanation, and offer fallback entry when eligible.
- **D-06:** Card-triggered source scrolling happens only in response to explicit user card selection. Refreshes, stale renders, and re-renders must not automatically steal the user's scroll position.

### Source to Card Focus
- **D-07:** Selecting a source anchor should focus the corresponding annotation card, scroll the relevant card lane enough to make the card visible, and mark both source and card as selected.
- **D-08:** Page-level markers that correspond to multiple cards should select a page-level group, not pretend the marker maps to one exact card. Related cards may be highlighted or listed as a group.
- **D-09:** Source-to-card selection should move real DOM focus to the target card when a single card is selected. Cards must therefore be focusable elements.
- **D-10:** If the corresponding card is unavailable because of refresh, stale load, paper change, or teardown, ANN13 should not keep a dangling selection. It should show that the card is temporarily unavailable and clear selection.

### Selection Lifecycle
- **D-11:** Paper changes and canvas teardown must immediately clear all card, source, group, and focus selection state. Selections must not be restored across papers.
- **D-12:** After a successful refresh, if the same card/anchor still exists, selected state may be preserved, but the canvas must not auto-scroll or steal the user's current reading position.
- **D-13:** After refresh, if the previously selected card/anchor no longer exists, selection should be cleared and a one-time status message should explain that the previous selection is unavailable.
- **D-14:** Pressing Escape should clear card/source/group selection and temporary navigation status messages without changing scroll position.

### PDF Page Fallback
- **D-15:** PDF fallback action should appear only when canvas source navigation is unavailable and the annotation has a trustworthy v0.2 PDF/page navigation target.
- **D-16:** PDF fallback must be triggered only by an explicit user click on a fallback button. ANN13 must never auto-jump from the canvas to the PDF.
- **D-17:** Fallback button copy should be explicit: "Open PDF page" and its localized equivalent. It must not be labeled as generic "source" navigation.
- **D-18:** PDF fallback must be hidden when there is no trustworthy PDF path, no valid `pageIndex`, a `sourceAttachmentKey` mismatch against the resolved PDF, or a paper identity mismatch.
- **D-19:** Fallback should reuse v0.2 PDF page navigation safety rules and attachment identity checks rather than introducing a new PDF navigation contract.

### Keyboard and Accessibility
- **D-20:** Annotation cards, exact source anchors, page-level markers, and fallback buttons should be reachable through Tab. Unresolved status text should not be tabbable because it has no action.
- **D-21:** Enter and Space should activate the currently focused card, source anchor, page-level marker, or fallback button. Escape should clear selection as described in D-14.
- **D-22:** Selected card/source states should be represented with `aria-selected` in addition to visual selected classes.
- **D-23:** Fallback actions should use real `button` elements with clear `aria-label` values.
- **D-24:** ANN13 should use stable natural DOM tab order for source anchors and card lanes. It should not add a full roving tabindex, listbox pattern, or arrow-key navigation system.

### Scope and Safety Boundaries
- **D-25:** ANN13 must preserve ANN12's read-only boundary: no create, edit, delete, save, import, apply, write-back, evidence mutation, or concept-card mutation controls.
- **D-26:** ANN13 must not introduce connector classes, connector geometry, SVG connector paths, hover/selected line drawing, or final visual relationship polish; those belong to ANN14.
- **D-27:** ANN13 must not depend on native Obsidian PDF viewer DOM internals for canvas navigation. PDF fallback may use the existing v0.2 `openLinkText` page-navigation path after safety checks.

### the agent's Discretion
The planner may choose exact helper/module names, event wiring structure, selected CSS class names, status message wording, and test filenames as long as the locked navigation, lifecycle, fallback, accessibility, and safety decisions above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` - Current annotation v0.3 target, read-only canvas direction, and v0.2 live harness caveat.
- `.planning/REQUIREMENTS.md` - NAV-01, NAV-02, NAV-03, SAFE, and TEST requirements for ANN13.
- `.planning/ROADMAP.md` - ANN13 goal, dependency on ANN12, and success criteria.
- `.planning/STATE.md` - Current milestone state showing ANN12 complete and ANN13 as the next phase.

### Prior Canvas Phases
- `.planning/phases/ANN12/ANN12-CONTEXT.md` - Source anchor precision levels, source surface rules, and the explicit deferral of navigation to ANN13.
- `.planning/phases/ANN12/ANN12-01-PLAN.md` - Pure source surface and anchor resolver contracts that ANN13 navigation should consume.
- `.planning/phases/ANN12/ANN12-02-PLAN.md` - Runtime source loading, source DOM rendering, anchor visual states, CSS, i18n, and safety gates.
- `.planning/phases/ANN12/ANN12-VALIDATION.md` - Exact/page-level/unresolved validation matrix and forbidden-scope scan.
- `.planning/phases/ANN11/ANN11-CONTEXT.md` - Card model, lane placement, read-only card boundary, and deferred navigation work.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` - Existing v0.2 PDF page navigation fallback and attachment identity safety.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - v0.2 automated gate status and pending live native-PDF harness note.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - Reading Canvas runtime, v0.2 PDF `openLinkText` fallback path, paper/session identity, and source loading integration.
- `paperforge/plugin/src/canvas/anchors.js` - ANN12 anchor statuses, diagnostics, source/page metadata, and exact/page-level/unresolved contracts.
- `paperforge/plugin/src/canvas/render.js` - ANN12 source surface, exact highlight, page-level marker, unresolved status, and safe DOM rendering.
- `paperforge/plugin/src/canvas/view-model.js` - Card view-models, anchor attachment, selected card identities, and lane inputs.
- `paperforge/plugin/src/canvas/index.js` - Canvas module export surface for planner/executor integration.
- `paperforge/plugin/src/canvas/controller.js` - Session lifecycle and stale-load guard patterns.
- `paperforge/plugin/src/testable.js` - Existing v0.2 PDF target resolution, attachment matching, page navigation, and annotation row contracts.
- `paperforge/plugin/tests/annotation-navigation.test.mjs` - Existing v0.2 PDF page target and fallback safety tests.
- `paperforge/plugin/tests/canvas-source-anchor.test.mjs` - Anchor model safety tests, including no scroll/focus fields before ANN13.
- `paperforge/plugin/tests/canvas-render.test.mjs`, `canvas-card-dom.test.mjs`, and `canvas-main-runtime.test.mjs` - DOM/source/card rendering safety and runtime regression tests to extend for ANN13.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- ANN12 adds `paperforge/plugin/src/canvas/anchors.js` with exact/page-level/unresolved anchor status and diagnostics that ANN13 should consume rather than recompute.
- ANN12 adds source DOM helpers in `paperforge/plugin/src/canvas/render.js`, including exact highlight and page-level marker classes that can become navigation targets.
- ANN11/ANN12 card view-models already preserve card identity, source/provenance identity, page metadata, anchor status, and lane assignment.
- v0.2 navigation helpers in `paperforge/plugin/src/testable.js` already resolve PDF candidates, attachment identity, and page links for safe `openLinkText` fallback.
- `PaperForgeReadingCanvasView` already owns fixed paper context and stale-load/session identity guards in `main.js`; ANN13 should extend those guards for navigation state.

### Established Patterns
- Canvas modules are CommonJS under `paperforge/plugin/src/canvas/` and exported through `index.js`.
- Ordinary missing/unsupported states should be explicit state objects or visible status messages, not thrown exceptions.
- User-facing source/card text must use safe DOM text APIs, not `innerHTML`.
- v0.3 remains read-only and must not mutate Zotero, `annotations.db`, vault notes, settings, localStorage, or persistent layout state.
- Focused Vitest/jsdom tests are the primary automated confidence source; live native PDF overlay reliability remains a separate pending harness.

### Integration Points
- A likely ANN13 model helper can own selection state transitions: selected card, selected anchor, selected page-level group, temporary status, and fallback eligibility.
- `render.js` should add focusable card/anchor/fallback DOM wiring or render metadata required for runtime event binding.
- `main.js` should remain a thin runtime coordinator for DOM events, `scrollIntoView`, focus, Escape handling, and v0.2 PDF fallback invocation.
- `styles.css` should add selected/focus classes without adding connector or relationship-line classes.
- `i18n.js` should receive visible navigation/fallback/status copy such as unable-to-locate, card unavailable, previous selection unavailable, and Open PDF page.

</code_context>

<specifics>
## Specific Ideas

- Navigation should feel useful but honest: exact anchors can behave like precise source targets; page-level anchors can move to page/block markers; unresolved anchors explain limits and offer fallback only when the PDF/page target is safe.
- Selection is persistent enough for reading, but refresh/re-render must not hijack scroll position.
- Source-to-card focus should be real focus, not just a visual class.
- Page-level group selection is preferred over pretending one page marker maps to one exact card.
- PDF fallback is deliberately explicit: users click "Open PDF page" and know they are leaving canvas source navigation.

</specifics>

<deferred>
## Deferred Ideas

- Connector lines, connector geometry, hover/selected relationship drawing, SVG connector paths, and final visual relationship polish belong to ANN14.
- Full canvas verification and live harness recording belong to ANN15.
- Native PDF DOM anchoring, bundled PDF.js rendering, local annotation editing, Zotero write-back, persistent layout, AI cards, and multi-paper boards remain future scope.

</deferred>

---

*Phase: ANN13-bidirectional-navigation-and-fallback-paths*
*Context gathered: 2026-07-06*
