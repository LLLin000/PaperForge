# Annotation Phase 8: PDF Overlay Rendering Spike and Implementation - Context

**Gathered:** 2026-06-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 8 makes imported PaperForge/Zotero PDF annotations visible directly on top of the native Obsidian PDF viewer when the current viewer DOM and hooks make that possible.

In plain terms: after Phase 7 can jump from an annotation row to the correct PDF/page, Phase 8 tries to show the annotation marks in the PDF page itself. The overlay is an enhancement, not a dependency for reading. If Obsidian PDF viewer internals are unavailable, changed, or unsafe to attach to, PaperForge must keep the sidebar/list and page-jump workflow usable.

This phase does not create or edit annotations, write to Zotero, mutate `annotations.db`, create concept-card evidence links, replace the existing sidebar/list, or guarantee overlay support across every future Obsidian PDF viewer implementation.

</domain>

<decisions>
## Implementation Decisions

### Overlay Activation and Risk Gate
- **D-01:** The plugin should automatically try to enable PDF overlay for the active paper/PDF when the PDF viewer can be identified safely.
- **D-02:** Overlay activation is fail-closed. If the viewer DOM, PDF page layer, annotation position data, or active PDF identity cannot be confirmed, the overlay does not render.
- **D-03:** Failure to render overlay must degrade to the existing annotation sidebar/list and Phase 7 page-jump behavior. It must not break the paper panel, loaded annotations, filters, grouping, or navigation.
- **D-04:** Overlay availability should be represented as a small internal/runtime state, not as a new primary workflow. User-facing notices should be concise and should not expose raw DOM errors, raw JSON, stack traces, or shell output.

### Visual Mark Style
- **D-05:** Default overlay marks are lightweight semi-transparent highlights over the corresponding PDF text area.
- **D-06:** Highlight color should use the annotation's original color when available. If no usable color exists, use a restrained default yellow.
- **D-07:** Marks should preserve text readability. Avoid heavy fills, large decorative markers, or UI that visually competes with the PDF text.
- **D-08:** Border-only or pin-only markers are not the Phase 8 default. They may be useful fallbacks only if precise rectangle fill is unreliable.

### Positioning and Scope
- **D-09:** Overlay positioning should use preserved annotation location fields from `pdfLocation`, especially `pageIndex`, `positionJson`, and `selectorJson`.
- **D-10:** `pageIndex` remains the authoritative machine page location. `pageLabel` is display text and should not drive positioning arithmetic.
- **D-11:** Render overlay marks only for annotations whose active PDF identity and page can be matched confidently to the currently open PDF. Supplemental-PDF annotations must not appear on the main article PDF by guesswork.
- **D-12:** If a row has no usable position/selector data, keep it in the sidebar/list and jump workflow, but do not invent a page-area overlay.
- **D-13:** Coordinate conversion should be isolated behind testable helpers where possible, because PDF coordinate systems, viewer scaling, page rotation, and DOM transforms are the risky part of this phase.

### Overlay Interaction
- **D-14:** Clicking or focusing an overlay highlight should open a lightweight PDF-local popover/detail surface.
- **D-15:** The popover should show selected text, comment, page label/page number, source/read-only provenance, and enough identity to trust where the annotation came from.
- **D-16:** Sidebar/list synchronization is optional for Phase 8. The main path is a PDF-local interaction loop; locating/expanding the matching sidebar row can be deferred unless it is cheap and low-risk.
- **D-17:** Popovers must be read-only. They must not add edit/delete/create controls.

### Lifecycle, Refresh, and Teardown
- **D-18:** Overlay marks must be scoped to the active PDF/paper and must be torn down when the active file, pane, paper identity, PDF page DOM, or annotation state changes.
- **D-19:** Refreshing annotation data should refresh overlay marks only after the new state is confirmed. Failed refresh should leave the sidebar/list usable and avoid stale overlay marks.
- **D-20:** Overlay should not poll continuously. Prefer event-driven attachment/refresh tied to active file changes, paper-mode render, annotation load/refresh, and observable PDF viewer DOM changes.

### Verification and Spike Boundary
- **D-21:** Phase 8 should start with a spike that documents the currently observable Obsidian PDF viewer DOM/hooks and identifies the safest attachment point.
- **D-22:** The implementation should include automated tests for helper logic, overlay state transitions, fallback behavior, DOM creation/teardown, and popover content where these can be tested outside live Obsidian.
- **D-23:** A small manual Obsidian verification note is acceptable for the parts that depend on real PDF viewer internals.
- **D-24:** If the spike cannot find a reliable viewer attachment point, Phase 8 should still land a documented disabled/fallback path rather than forcing a brittle overlay.

### the agent's Discretion
The user delegated remaining Phase 8 decisions to the agent's judgment after selecting the recommended direction. The planner may choose exact helper names, CSS class names, event hooks, and whether the spike and implementation are split into separate plans, as long as the decisions above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/ROADMAP.md` - Annotation Phase 8 goal, dependency, requirements, and success criteria.
- `.planning/REQUIREMENTS.md` - OVLY-02 through OVLY-05 and SAFE/TEST boundaries.
- `.planning/PROJECT.md` - Annotation v0.2 framing, local-first behavior, thin-shell plugin direction, and risk-gated overlay decision.
- `.planning/STATE.md` - Current v0.2 status, Phase 7 completion, and known baseline failures.

### Prior Annotation Phases
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md` - Normalized annotation row shape, preserved `pdfLocation.positionJson`, `selectorJson`, attachment identity, and raw row preservation.
- `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md` - Sidebar/list fallback, row display, session-only annotation UI state, and no editing/write-back boundaries.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` - Source PDF resolution, page-index semantics, attachment identity safety, page-badge navigation, and read-only/fallback behavior.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md` - Final page-badge affordance, styling, and DOM regression surface that Phase 8 must coexist with.
- `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-04-SUMMARY.md` - Phase 7 verification gate and 142-test baseline.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - Obsidian runtime shell, annotation bridge state, `_renderAnnotationSection`, `_renderAnnotationRows`, `_openAnnotationPdf`, active paper entry, and existing PDF open behavior.
- `paperforge/plugin/src/testable.js` - Pure annotation helpers, normalized row contracts, sorting/grouping helpers, and PDF target resolution helpers.
- `paperforge/plugin/styles.css` - Existing annotation section and page-badge styles; overlay CSS should extend this without disrupting list layout.
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` - Runtime harness for annotation bridge, list rendering, and PDF navigation behavior.
- `paperforge/plugin/tests/annotation-section-dom.test.mjs` - DOM regression surface for annotation rows, page badge, expand behavior, and styling-sensitive markup.
- `paperforge/plugin/tests/annotation-navigation.test.mjs` - Pure PDF target resolution and page navigation helper contracts.
- `paperforge/plugin/tests/annotation-bridge.test.mjs` - Preserved `pdfLocation`, source attachment identity, position/selector fields, and normalized row contract.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `normalizeAnnotationExportRow()` already preserves `display`, `provenance`, `pdfLocation`, and `raw`; Phase 8 should consume these fields rather than reparsing CLI JSON.
- `pdfLocation.positionJson` and `pdfLocation.selectorJson` are already preserved for overlay positioning.
- `resolveAnnotationPdfTarget()` and Phase 7 navigation helpers provide the safety pattern for matching an annotation to the correct source PDF.
- `_renderAnnotationSection()` and `_renderAnnotationRows()` provide the current list surface and row identity model.
- `_openAnnotationPdf(row)` proves the current PDF/page navigation path and should remain independent from overlay rendering.

### Established Patterns
- Plugin UI is built with Obsidian `createEl()` and explicit event listeners, not a component framework.
- Helper logic that needs deterministic tests should live in or be mirrored through `paperforge/plugin/src/testable.js`, while `main.js` remains the Obsidian runtime shell.
- Annotation UI state is session-local and read-only; overlay state should follow the same pattern.
- User-facing failures are friendly notices/states, never raw stack traces or raw CLI output.
- The sidebar/list remains the fallback and should not be removed, hidden, or made dependent on overlay success.

### Integration Points
- Active paper/PDF identity comes from `PaperForgeStatusView` state, `_currentPaperKey`, `_currentPaperEntry`, and current Obsidian file context.
- Overlay attachment should connect near the PDF viewer DOM/runtime, while list rendering remains in the PaperForge paper panel.
- Overlay refresh should connect to annotation load/refresh and active-file changes rather than polling.
- Tests should extend the existing Vitest harnesses and add a focused manual Obsidian check only for real viewer internals.

</code_context>

<specifics>
## Specific Ideas

- Use automatic overlay probing with safe fallback rather than a manual user toggle as the Phase 8 default.
- Use semi-transparent highlights as the default mark style.
- Use a lightweight popover for selected text/comment/source details.
- Treat overlay as an enhancement layered on top of the already working list and page-jump flow.

</specifics>

<deferred>
## Deferred Ideas

- Sidebar/list row auto-expansion or bidirectional synchronization from overlay click is optional and may be deferred if it increases risk.
- Local annotation creation/editing/deletion remains a future editing phase.
- Zotero write-back remains out of scope.
- Concept-card evidence integration remains a future requirement after annotation display/navigation/overlay are stable.

</deferred>

---

*Phase: annotation-08-pdf-overlay-rendering-spike-and-implementation*
*Context gathered: 2026-06-28*
