# Annotation Phase 6: Annotation Sidebar and List View - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 6 turns the active-paper annotation state from Phase 5 into a visible, paper-scoped annotation list inside the existing PaperForge Obsidian UI.

In plain terms: when the user is looking at a recognized paper in the PaperForge paper panel, they should be able to see the paper's imported Zotero/PaperForge annotations without opening raw JSON. The list should be compact enough for scanning, support page/type/color organization, provide a local refresh action, and show clear empty/error/loading states.

This phase does not implement jump-to-PDF/page behavior, PDF overlay rendering, local annotation editing, Zotero write-back, concept-card evidence integration, or a separate annotation-only pane. Those remain scoped to later phases or future requirements.

</domain>

<decisions>
## Implementation Decisions

### Entry and Placement
- **D-01:** The annotation list should be embedded in the existing `PaperForgeStatusView` paper mode rather than creating a separate sidebar/view.
- **D-02:** The annotation section should be rendered after the paper overview card and before the Next Step card.
- **D-03:** The annotation section should be expanded by default so imported annotations are immediately visible.
- **D-04:** The implementation should keep the section bounded for long annotation lists, using internal list height/scroll behavior rather than letting many annotations consume the whole paper panel.

### Row Display
- **D-05:** Annotation rows should use a compact row-list layout, not large cards.
- **D-06:** The default row preview should show selected text up to 2 lines and comment up to 1 line.
- **D-07:** Long selected text or comments should be expandable inline.
- **D-08:** Each row should always show page, color/type, selected text preview, and comment icon or comment summary.
- **D-09:** Provenance details such as source, read-only state, attachment key, annotation key, timestamps, and raw/debug fields should live in row expansion details, not clutter the default row.
- **D-10:** Color/type should be represented as a small color swatch plus type label so the UI does not depend on color alone.

### Ordering, Grouping, and Filtering
- **D-11:** Default ordering should follow PDF reading order: page number ascending, then source sort/index within page.
- **D-12:** The list should provide a grouping control with three modes: no grouping, group by page, and group by type/color.
- **D-13:** The default grouping mode is no grouping while preserving PDF reading-order sorting.
- **D-14:** The list should provide type/color filtering.
- **D-15:** The list should provide a search box over selected text and comment.
- **D-16:** Search should not search raw JSON or provenance fields in Phase 6; those are debugging/details data, not the primary reading surface.
- **D-17:** Filter and grouping settings should be remembered only for the current panel session, not persisted globally or per paper.

### Refresh, Loading, and Failure States
- **D-18:** The annotation section should have its own refresh button in the section header.
- **D-19:** The section refresh should refresh only annotations by calling the Phase 5 reusable loader; it should not refresh the whole dashboard unless required by existing infrastructure.
- **D-20:** When refresh fails after a previous successful load, the UI should preserve the last successful list and show a clear error banner stating that the displayed data is stale.
- **D-21:** Empty and failure states must distinguish at least `empty`, `missing-db`, `missing-paper`, `cli-error`, and `invalid-json` instead of showing a generic "no annotations" message.
- **D-22:** Empty/failure states should suggest the next action appropriate to the state, such as importing annotations, initializing/repairing annotation data, or opening a recognized paper note/PDF.
- **D-23:** Loading should be local to the annotation section, using section-level loading text or skeleton UI; annotation loading should not block the rest of the paper panel.

### Scope Boundaries
- **D-24:** Phase 6 may add non-navigating row affordances such as expand/collapse, but it must not add PDF jump/open-at-page actions. That is Annotation Phase 7.
- **D-25:** Phase 6 must not add PDF overlay rendering, popovers on the PDF viewer, local annotation editing, Zotero write-back, database mutation, or concept-card evidence wiring.

### the agent's Discretion
- The planner may choose exact CSS class names and DOM structure as long as they fit the existing PaperForge panel style and remain testable.
- The planner may choose whether the grouping control is a segmented control, select menu, or compact button group, as long as it supports the three locked grouping modes.
- The planner may choose the exact bounded-list behavior, such as max-height with internal scroll, as long as the section does not dominate the full paper panel for long lists.
- The planner may choose concise English UI labels consistent with existing plugin language until a broader localization pass is planned.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/ROADMAP.md` - Annotation Phase 6 goal, dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` - LIST-01 through LIST-05 and v0.2 scope boundaries.
- `.planning/STATE.md` - Current milestone state, phase numbering decision, and known baseline failures.
- `.planning/PROJECT.md` - Annotation v0.2 framing and key decisions.

### Direct Dependency
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md` - Phase 5 annotation state, row shape, lifecycle, and bridge boundaries.
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-01-PLAN.md` - Planned helper/state normalization contract that Phase 6 consumes.
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-02-PLAN.md` - Planned runtime `PaperForgeStatusView` annotation state and loader integration.

### Plugin Code
- `paperforge/plugin/main.js` - Existing `PaperForgeStatusView`, paper mode rendering, refresh button, empty/error utilities, and mode lifecycle.
- `paperforge/plugin/src/testable.js` - Existing Node-testable helper pattern and planned annotation helper exports.
- `paperforge/plugin/tests/` - Existing Vitest tests and planned Phase 5 annotation bridge/runtime tests.
- `paperforge/plugin/package.json` - Plugin-side test script.

### Annotation CLI and Contracts
- `paperforge/commands/annotation.py` - Annotation CLI JSON behavior and export/list/status payloads.
- `paperforge/annotation/` - Annotation storage and schema modules.
- `tests/cli/test_annotation_json_contracts.py` - Cross-command PFResult contract tests.
- `tests/cli/test_annotation_read_json.py` - Existing annotation list/status/export JSON read tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PaperForgeStatusView._renderPaperMode()` already renders paper-scoped UI and is the correct surface for the annotation list.
- `PaperForgeStatusView._renderPaperOverviewCard()` currently appears before Next Step rendering; Phase 6 should insert the annotation section after this call.
- `PaperForgeStatusView._renderEmptyState(container, message)` provides a reusable empty-state pattern.
- `PaperForgeStatusView._showMessage(msg, cls)` and section-level status classes demonstrate existing friendly message handling.
- Existing contextual buttons such as `.paperforge-contextual-btn` and header refresh controls provide a pattern for the annotation section refresh button.

### Established Patterns
- The plugin uses DOM `createEl()` construction rather than framework components.
- The PaperForge panel is mode-based: global, paper, and collection rendering are switched by `PaperForgeStatusView._switchMode()` and refreshed by `_refreshCurrentMode()`.
- User-facing errors should be friendly and should not expose raw Python tracebacks or shell noise.
- Helper logic that needs deterministic tests should live in or be mirrored through `paperforge/plugin/src/testable.js`, while `main.js` remains the Obsidian runtime shell.
- Existing code has some mojibake in labels; Phase 6 should avoid adding new corrupted strings and should prefer clean labels.

### Integration Points
- Phase 6 should consume Phase 5's stored annotation bridge state through `getAnnotationState()` and refresh through `loadAnnotationsForCurrentPaper(reason)`.
- The annotation section should rerender safely when active paper changes, annotation state changes, or the user clicks the section refresh button.
- Tests should cover loaded rows, empty state, missing DB, missing paper, CLI error, invalid JSON, filtering, grouping, search, row expansion, and stale-list-on-refresh-failure behavior.

</code_context>

<specifics>
## Specific Ideas

- Section title can be "Annotations" with count and a refresh icon/button on the right.
- Default list should be compact: page badge, color swatch, type label, selected text preview, and comment preview/icon.
- Expanded row details can show source/read-only/provenance fields for trust and debugging without overwhelming the main list.
- Grouping options should be no grouping, by page, and by type/color.
- Search should target only selected text and comments in Phase 6.
- Refresh failure should keep the previous list visible with a stale/error banner.

</specifics>

<deferred>
## Deferred Ideas

- Jumping from an annotation row to the source PDF/page belongs to Annotation Phase 7.
- PDF overlay rendering, viewer popovers, and overlay fallback behavior belong to Annotation Phase 8.
- Display-layer verification across list, jump, overlay, and known baseline failures belongs to Annotation Phase 9.
- Local annotation creation/editing/deletion, Zotero write-back, and concept-card evidence integration remain future requirements outside annotation v0.2 Phase 6.

</deferred>

---

*Phase: annotation-06-annotation-sidebar-and-list-view*
*Context gathered: 2026-06-19*
