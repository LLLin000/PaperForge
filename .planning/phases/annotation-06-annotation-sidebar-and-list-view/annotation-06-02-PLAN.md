---
phase: annotation-06-annotation-sidebar-and-list-view
plan: 02
type: execute
wave: 2
depends_on:
  - annotation-06-01
files_modified:
  - paperforge/plugin/src/testable.js
  - paperforge/plugin/tests/annotation-list-viewmodel.test.mjs
autonomous: true
requirements:
  - LIST-02
  - LIST-03
  - LIST-05

must_haves:
  truths:
    - "D-11: Default ordering follows PDF reading order: page ascending, then source sort/index within page."
    - "D-12: The view-model supports grouping modes `none`, `page`, and `type-color`."
    - "D-13: The default grouping mode is `none` while preserving reading-order sorting."
    - "D-14: The view-model supports type/color filtering."
    - "D-15: The view-model supports search over selected text and comment."
    - "D-16: Search does not match raw JSON, provenance fields, attachment keys, annotation keys, source fields, or timestamps."
    - "D-17: Group, filter, search, and expansion state are session-local UI state only and are not persisted globally or per paper."
    - "LIST-05: Empty, missing-paper, missing-db, cli-error, invalid-json, loading, and ready states produce distinct render decisions."
  artifacts:
    - path: "paperforge/plugin/src/testable.js"
      provides: "Pure annotation list view-model helpers"
      exports:
        - createDefaultAnnotationListUiState
        - sortAnnotationsForReadingOrder
        - buildAnnotationFilterOptions
        - matchesAnnotationSearch
        - groupAnnotationRows
        - toggleAnnotationExpansion
        - mergeAnnotationRefreshResult
        - buildAnnotationListViewModel
    - path: "paperforge/plugin/tests/annotation-list-viewmodel.test.mjs"
      provides: "Vitest coverage for annotation list sorting, grouping, filtering, search, preview, expansion, and state decisions"
  key_links:
    - from: "paperforge/plugin/src/testable.js"
      to: "paperforge/plugin/main.js"
      via: "Plan 03 mirrors or consumes the tested view-model behavior in the Obsidian runtime"
      pattern: "buildAnnotationListViewModel"
---

<objective>
Build pure annotation list view-model helpers and tests.

Purpose: Keep sorting, grouping, filtering, search, preview, expansion, stale-data, and state decisions deterministic before runtime DOM work.
Output: Testable helper exports in `src/testable.js` plus focused Vitest coverage.
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
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-01-PLAN.md
@.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-02-PLAN.md
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/runtime.test.mjs
@paperforge/plugin/package.json
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Define list UI state, row identity, ordering, grouping, filter, and search helpers</name>
  <files>
    paperforge/plugin/src/testable.js
    paperforge/plugin/tests/annotation-list-viewmodel.test.mjs
  </files>
  <behavior>
    - Test 1: `createDefaultAnnotationListUiState()` returns `{ query: "", groupMode: "none", typeColorFilter: "all", expandedIds: [] }` or an equivalent serializable session-local default per D-13 and D-17.
    - Test 2: `sortAnnotationsForReadingOrder(rows)` sorts by numeric page ascending, then `pdfLocation.sortIndex`, then stable row identity per D-11.
    - Test 3: `groupAnnotationRows(rows, "none"|"page"|"type-color")` returns stable group structures for all three locked grouping modes per D-12.
    - Test 4: `buildAnnotationFilterOptions(rows)` deduplicates type/color choices and produces labels that include type and color where present per D-14.
    - Test 5: `matchesAnnotationSearch(row, query)` matches selected text and comment only, and does not match `raw`, `provenance`, source, attachment, annotation key, timestamp, or debug fields per D-15 and D-16.
  </behavior>
  <action>
    Add `paperforge/plugin/tests/annotation-list-viewmodel.test.mjs` using the existing Vitest ESM import pattern for CommonJS helpers from `../src/testable.js`. Use normalized annotation rows shaped like the Phase 5 `display`, `provenance`, `pdfLocation`, and `raw` contract; do not parse CLI output in these tests.

    Extend `paperforge/plugin/src/testable.js` with pure helper exports for session-local UI defaults, stable annotation identity, reading-order sorting, type/color option construction, search matching, type/color filter matching, and grouping. Keep these helpers independent from Obsidian APIs and DOM. Do not add persistence, localStorage, global settings writes, CLI calls, database reads, PDF navigation, overlay hooks, edit/delete actions, write-back, or evidence integration.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "if (!(Test-Path 'paperforge/plugin/node_modules')) { throw 'Missing paperforge/plugin/node_modules. Run npm.cmd install in paperforge/plugin before executing tests; do not add packages.' }"</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs</automated>
  </verify>
  <done>Pure helpers correctly compute default session UI state, reading-order sorting, locked grouping modes, type/color filters, and selected-text/comment-only search.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Define preview, inline expansion, stale refresh merge, and render-state view-model</name>
  <files>
    paperforge/plugin/src/testable.js
    paperforge/plugin/tests/annotation-list-viewmodel.test.mjs
  </files>
  <behavior>
    - Test 1: preview helpers mark selected text as two-line-preview content and comment as one-line-preview content without relying on DOM measurement per D-06.
    - Test 2: `toggleAnnotationExpansion(uiState, rowId)` adds and removes IDs without mutating unrelated session-local settings per D-07 and D-17.
    - Test 3: `buildAnnotationListViewModel(annotationState, uiState)` returns distinct decisions for `loading`, `ready`, `empty`, `missing-paper`, `missing-db`, `cli-error`, and `invalid-json` per D-21 and D-23.
    - Test 4: `mergeAnnotationRefreshResult(previousRenderable, nextState)` preserves the last successful ready/empty renderable state and marks it stale when a refresh fails after previous success per D-20.
    - Test 5: unsupported/missing row fields do not crash and produce safe fallback labels for LIST-05.
  </behavior>
  <action>
    Extend the same test file and helper module with preview metadata helpers, pure expansion state transitions, a stale-refresh merge helper, and `buildAnnotationListViewModel(annotationState, uiState)`. The view-model should centralize row count, visible rows, grouped rows, control state, banners, empty/error messages, and whether stale data is being shown.

    Distinct state messages should be concise and user-facing: empty suggests importing annotations, missing-db suggests initializing or repairing annotation data, missing-paper suggests opening a recognized paper note or PDF, cli-error suggests retrying or checking PaperForge annotation status, and invalid-json suggests checking the local CLI output. Keep raw traceback/shell output in debug data only and never in display messages.
  </action>
  <verify>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs</automated>
  </verify>
  <done>The view-model can drive the Phase 6 UI for ready, loading, empty, missing-db, missing-paper, cli-error, invalid-json, filtering, grouping, search, inline expansion, and stale refresh without using DOM or CLI code.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase 5 annotation rows -> list view-model | Imported annotation text/comment and raw fields enter helper logic. |
| UI controls -> row filtering/search | User-entered query and filter values select rows for rendering. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-06-03 | Information Disclosure | `matchesAnnotationSearch` | mitigate | Search only `display.selectedText` and `display.comment`; tests assert provenance/raw fields do not match per D-16. |
| T-annotation-06-04 | Tampering | helper scope | mitigate | Helpers are pure and do not call CLI, read DB files, mutate `annotations.db`, or persist UI settings. |
| T-annotation-06-05 | Denial of Service | sorting/grouping missing fields | mitigate | Helpers tolerate missing page/type/color/comment fields and return fallback labels without throwing. |
| T-annotation-06-SC | Tampering | npm installs | accept | This plan uses existing `vitest` from `package.json`; no package installation or package changes. |
</threat_model>

<verification>
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs`
</verification>

<success_criteria>
- [ ] Reading-order sorting is deterministic and page-first.
- [ ] Grouping modes are exactly `none`, `page`, and `type-color`, with `none` as default.
- [ ] Type/color filtering works for rows with and without color/type.
- [ ] Search matches selected text and comment only, not raw/provenance/debug fields.
- [ ] UI state remains session-local helper data and is not persisted.
- [ ] Distinct state decisions exist for ready, loading, empty, missing-db, missing-paper, cli-error, and invalid-json.
- [ ] Stale refresh merge preserves prior successful rows with a stale banner after failed refresh.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-02-SUMMARY.md`.
</output>
