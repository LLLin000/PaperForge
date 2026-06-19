---
phase: annotation-06-annotation-sidebar-and-list-view
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-06-02
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
autonomous: true
requirements:
  - LIST-01
  - LIST-02
  - LIST-03
  - LIST-04
  - LIST-05

must_haves:
  truths:
    - "D-01: The annotation list is embedded in existing `PaperForgeStatusView` paper mode, not a separate sidebar/view."
    - "D-02: The annotation section renders after `_renderPaperOverviewCard(view, entry)` and before the Complete/Next Step branch."
    - "D-03: The annotation section is expanded by default."
    - "D-18: The annotation section has its own refresh button in the section header."
    - "D-19: Section refresh calls Phase 5 `loadAnnotationsForCurrentPaper('manual')` and does not refresh the whole dashboard unless an existing infrastructure limitation is documented."
    - "D-20: Refresh failure after a previous successful load preserves the last successful list and shows a stale-data error banner."
    - "D-21: Empty/failure states distinguish `empty`, `missing-db`, `missing-paper`, `cli-error`, and `invalid-json`."
    - "D-22: Empty/failure states suggest appropriate next actions."
    - "D-23: Loading is local to the annotation section and does not block the rest of the paper panel."
    - "D-24: Phase 6 may add expand/collapse only; it does not add PDF jump/open-at-page actions."
    - "D-25: Phase 6 does not add overlay rendering, PDF viewer popovers, local annotation editing, Zotero write-back, database mutation, or concept-card evidence wiring."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Embedded annotation section in `PaperForgeStatusView` paper mode"
      contains: "_renderAnnotationSection"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Runtime tests for placement, controls, refresh, stale state, distinct states, and forbidden controls"
  key_links:
    - from: "PaperForgeStatusView._renderPaperMode"
      to: "PaperForgeStatusView._renderAnnotationSection"
      via: "direct call after overview and before Next Step"
      pattern: "_renderPaperOverviewCard[\\s\\S]*_renderAnnotationSection[\\s\\S]*(Complete state|Next Step)"
    - from: "PaperForgeStatusView._renderAnnotationSection"
      to: "PaperForgeStatusView.loadAnnotationsForCurrentPaper"
      via: "section refresh button"
      pattern: "loadAnnotationsForCurrentPaper\\(['\"]manual['\"]\\)"
---

<objective>
Integrate the annotation list section into the real Obsidian plugin paper-mode runtime.

Purpose: Make active-paper annotations visible and refreshable in the existing PaperForge paper panel while preserving Phase 6 scope boundaries.
Output: `main.js` runtime rendering plus tests against the real `PaperForgeStatusView` path.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-RESEARCH.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-01-SUMMARY.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-02-SUMMARY.md
@paperforge/plugin/main.js
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/runtime.test.mjs
@paperforge/plugin/tests/annotation-list-viewmodel.test.mjs
@paperforge/plugin/package.json

Narrow-read `paperforge/plugin/main.js` around these known integration points only:
- `class PaperForgeStatusView`
- constructor fields for `_currentMode`, `_currentPaperKey`, `_currentPaperEntry`, `_currentFilePath`
- `_renderPaperMode()`
- `_renderPaperOverviewCard(container, entry)`
- `_renderNextStepCard(container, entry, key)`
- `_refreshCurrentMode()`
- `_renderEmptyState(container, message)`
- `_showMessage(msg, cls)`
- `module.exports`
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Add runtime tests and paper-mode insertion point</name>
  <files>
    paperforge/plugin/main.js
    paperforge/plugin/tests/annotation-main-runtime.test.mjs
  </files>
  <behavior>
    - Test 1: The real `PaperForgeStatusView` path renders a `.paperforge-annotations-section` inside `.paperforge-paper-view` after `.paperforge-paper-overview` and before `.paperforge-next-step-card` or `.paperforge-complete-row` per D-01 and D-02.
    - Test 2: The section is expanded by default per D-03 and renders a title, count, refresh button, search control, grouping control, and type/color filter when bridge state is renderable.
    - Test 3: The runtime consumes `getAnnotationState()` from the Phase 5 bridge state and does not parse CLI stdout or raw PFResult JSON in the list renderer.
    - Test 4: The runtime test fails if `PaperForgeStatusView` cannot be accessed through `module.exports.__test` or an equivalent test hook.
  </behavior>
  <action>
    Create or extend `paperforge/plugin/tests/annotation-main-runtime.test.mjs` so it tests `paperforge/plugin/main.js`, not only `src/testable.js`. Use jsdom or the existing Obsidian-style DOM mocks to instantiate a minimal `PaperForgeStatusView` object with `containerEl`, `_contentEl`, `_currentPaperKey`, `_currentPaperEntry`, `getAnnotationState()`, and no-op app methods needed by `_renderPaperMode()`.

    If `main.js` still exports only the plugin class, refactor the export to preserve the default plugin export while adding a side-effect-free test hook such as `module.exports.__test = { PaperForgeStatusView }`. Then insert `_renderAnnotationSection(view, this.getAnnotationState(), entry)` immediately after `this._renderPaperOverviewCard(view, entry)` and before the Complete/Next Step branch. Do not move the paper overview, Next Step, recent discussion, or technical details sections.

    Mirror or inline the Plan 02 view-model helper behavior into `main.js` only as needed for the Obsidian runtime bundle. Do not import Node-only test modules into `main.js`. Do not implement Phase 5 bridge methods here; if `getAnnotationState()` or `loadAnnotationsForCurrentPaper()` is missing, stop and report the Phase 5 prerequisite failure from Plan 01.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs</automated>
  </verify>
  <done>The paper-mode runtime renders an expanded annotation section in the locked location and tests exercise the real `PaperForgeStatusView` method path.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Implement controls, section-local refresh, stale banner, and forbidden-scope guards</name>
  <files>
    paperforge/plugin/main.js
    paperforge/plugin/tests/annotation-main-runtime.test.mjs
  </files>
  <behavior>
    - Test 1: Clicking the annotation refresh button calls `loadAnnotationsForCurrentPaper('manual')`, sets section-local loading state, and rerenders the annotation section without invoking PDF open/navigation APIs per D-18, D-19, and D-23.
    - Test 2: A failed manual refresh after a previous ready/empty state keeps stale rows visible and renders a stale-data banner per D-20.
    - Test 3: `empty`, `missing-db`, `missing-paper`, `cli-error`, and `invalid-json` render distinct messages and next-action hints per D-21 and D-22.
    - Test 4: Controls update session-local `_annotationUiState` only and do not write plugin settings, localStorage, files, or database state per D-17.
    - Test 5: Rendered rows do not contain PDF jump/open-at-page buttons, overlay hooks, edit/delete buttons, write-back commands, DB mutation calls, or concept evidence controls per D-24 and D-25.
  </behavior>
  <action>
    Extend `PaperForgeStatusView` with UI-only fields such as `_annotationUiState`, `_annotationSectionEl`, and `_lastRenderableAnnotationState`. Keep these fields session-local and reset naturally with the view instance; do not persist them through `saveData`, settings, localStorage, or files.

    Implement `_renderAnnotationSection(container, annotationState, entry)`, `_renderAnnotationControls(section, viewModel)`, `_renderAnnotationRows(listEl, viewModel)`, `_rerenderAnnotationSection()`, and `_handleAnnotationRefresh()` or equivalent names. The refresh handler must call Phase 5 `loadAnnotationsForCurrentPaper('manual')`, show section-local loading UI, merge failures with the last successful renderable list, and rerender only the annotation section when possible.

    Rows should render page, swatch/type, selected text preview, and comment preview or icon. Inline expansion may reveal provenance/read-only/source/attachment/timestamps/debug-safe details, but default rows must stay compact. All selected text and comment content must be inserted as text, never `innerHTML`. Do not add row click behavior for opening PDFs, PDF page navigation, overlay rendering, editing, delete, write-back, database mutation, or concept-card evidence.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs</automated>
  </verify>
  <done>The annotation section supports controls, local refresh, stale-data behavior, distinct load states, and strict non-navigation/non-editing/non-mutating scope in the real runtime.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 5 state -> Obsidian DOM | Annotation text/comment and provenance are rendered in the plugin panel. |
| User controls -> runtime state | Search, grouping, filter, expansion, and refresh mutate only view-local UI state. |
| Runtime refresh -> Phase 5 loader | Manual refresh invokes the existing active-paper annotation loader. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-06-06 | Information Disclosure | annotation row rendering | mitigate | Render selected text/comment with text nodes, not `innerHTML`; raw tracebacks remain out of display messages. |
| T-annotation-06-07 | Tampering | refresh/list runtime | mitigate | Refresh calls only Phase 5 loader and does not query or mutate `annotations.db`; tests assert forbidden controls are absent. |
| T-annotation-06-08 | Elevation of Privilege | row affordances | mitigate | No PDF jump, overlay, edit/delete, write-back, or evidence controls in Phase 6 per D-24 and D-25. |
| T-annotation-06-09 | Denial of Service | manual refresh | mitigate | Use section-local loading and rerender so the rest of the paper panel remains usable. |
| T-annotation-06-SC | Tampering | npm installs | accept | This plan uses existing plugin test dependencies and adds no packages. |
</threat_model>

<verification>
- `node --check paperforge/plugin/main.js`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs`
</verification>

<success_criteria>
- [ ] Annotation section renders inside existing paper mode after overview and before Next Step/complete.
- [ ] Section is expanded by default and shows count, refresh, search, grouping, and type/color filter controls.
- [ ] Manual refresh is local to the section and calls `loadAnnotationsForCurrentPaper('manual')`.
- [ ] Stale banner appears while preserving previous rows after failed refresh.
- [ ] Empty, missing-db, missing-paper, cli-error, invalid-json, ready, and loading states render distinctly.
- [ ] UI state is session-only and not persisted.
- [ ] No jump/open-at-page, overlay, edit/delete, write-back, DB mutation, or concept evidence controls are added.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-03-SUMMARY.md`.
</output>
