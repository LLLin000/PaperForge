## RESEARCH COMPLETE

**Phase:** Annotation Phase 6 - Annotation Sidebar and List View  
**Researched:** 2026-06-19  
**Domain:** Obsidian plugin DOM rendering, annotation list view-model logic, Vitest runtime harness  
**Confidence:** HIGH for codebase integration points; MEDIUM for jsdom test environment guidance; LOW for external Obsidian API docs because official docs were not reliably retrievable through the available search path.

### Key Findings
- The correct Phase 6 insertion point is `PaperForgeStatusView._renderPaperMode()` immediately after `this._renderPaperOverviewCard(view, entry)` and before the complete/Next Step branch. [VERIFIED: codebase rg/narrow read]
- The initial HEAD baseline inspection showed no committed annotation bridge/list helpers in `paperforge/plugin/src/testable.js`; later working-tree status showed uncommitted Phase 5 helper artifacts. Planner must preflight the actual available Phase 5 bridge before implementing Phase 6. [VERIFIED: codebase rg/narrow read] [VERIFIED: git status] [VERIFIED: annotation-05 plans]
- Pure list behavior belongs in `src/testable.js`: filtering, search, grouping, reading-order sort, preview truncation decisions, expansion state transitions, available filter options, and render-state decisions. [VERIFIED: phase context] [ASSUMED: implementation recommendation]
- Runtime tests must exercise the real `PaperForgeStatusView` path in `main.js`; helper-only tests are insufficient because `main.js` currently exports only the plugin class and has no test hook for the view. [VERIFIED: codebase rg/narrow read]
- Phase 6 must stay read-only and non-navigating: no PDF jump, overlay, editing, writeback, database mutation, or concept evidence wiring. [VERIFIED: annotation-06-CONTEXT.md] [VERIFIED: REQUIREMENTS.md]

### File Created
`.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Implementation Surface | HIGH | Confirmed by narrow reads of `main.js` around `PaperForgeStatusView`, `_renderPaperMode`, `_refreshCurrentMode`, `_renderEmptyState`, `_showMessage`, and `module.exports`. |
| Existing Patterns | HIGH | Confirmed by `main.js`, `src/testable.js`, plugin tests, and `package.json`. |
| Test Strategy | HIGH/MEDIUM | Codebase harness needs are HIGH; jsdom config detail is MEDIUM from Vitest official docs. |
| External Docs | LOW | Obsidian official API pages were not reliably retrievable; recommendations rely on local code patterns instead. |

## User Constraints

### Locked Decisions from Phase 6 Context
- Embed the annotation list in existing `PaperForgeStatusView` paper mode, not a separate sidebar/view. [VERIFIED: annotation-06-CONTEXT.md]
- Render after the paper overview card and before the Next Step card. [VERIFIED: annotation-06-CONTEXT.md]
- Expanded by default, bounded for long lists, compact row-list layout, selected text up to 2 lines, comment up to 1 line, inline expansion for long text/comments. [VERIFIED: annotation-06-CONTEXT.md]
- Default order is PDF reading order: page ascending, then source sort/index within page. [VERIFIED: annotation-06-CONTEXT.md]
- Grouping modes are none, page, and type/color; default grouping is none. [VERIFIED: annotation-06-CONTEXT.md]
- Type/color filtering and selected-text/comment search are required; search must not include raw JSON or provenance fields in Phase 6. [VERIFIED: annotation-06-CONTEXT.md]
- Filter/grouping settings are current-panel-session only, not persisted globally or per paper. [VERIFIED: annotation-06-CONTEXT.md]
- Annotation section needs its own refresh button, local loading state, stale-data banner on refresh failure after previous success, and distinct empty/error states. [VERIFIED: annotation-06-CONTEXT.md]
- Phase 6 must not add PDF jump/open-at-page actions, overlay rendering, PDF viewer popovers, local editing, Zotero write-back, DB mutation, or concept-card evidence wiring. [VERIFIED: annotation-06-CONTEXT.md]

### Phase Requirements
| ID | Description | Research Support |
|----|-------------|------------------|
| LIST-01 | User can view a paper-scoped annotation list in the PaperForge Obsidian UI. | Insert section in `_renderPaperMode()` after overview and before Next Step. [VERIFIED: codebase rg/narrow read] |
| LIST-02 | User can scan annotations by page, color/type, selected text, and comment. | Use compact row view-model fields from Phase 5 normalized `display` shape. [VERIFIED: annotation-05 plans] |
| LIST-03 | User can filter or group annotations by at least page and type/color. | Put grouping/filter/search in pure helpers before DOM rendering. [ASSUMED: implementation recommendation] |
| LIST-04 | User can refresh annotation list after import without restarting Obsidian. | Header refresh calls Phase 5 reusable loader, then rerenders only annotation section when possible. [VERIFIED: annotation-06-CONTEXT.md] |
| LIST-05 | List UI degrades gracefully for empty papers, missing PDFs, and unsupported fields. | Render decisions should consume Phase 5 states and row capability flags instead of reparsing raw CLI output. [VERIFIED: annotation-05 plans] |

## Project Constraints

- `AGENTS.md` says plugin UI text normally goes through `i18n.js` with `t('key_name')`, but Phase 6 context explicitly allows concise English labels until a broader localization pass is planned. Planner should avoid adding mojibake strings. [VERIFIED: AGENTS.md] [VERIFIED: annotation-06-CONTEXT.md]
- Existing plugin code uses Obsidian-style `createEl()` DOM construction rather than framework components; Phase 6 should follow that pattern. [VERIFIED: codebase rg/narrow read]
- Existing code avoids raw `innerHTML` in sensitive DOM construction; annotation selected text/comment must be rendered as text nodes, not HTML. [VERIFIED: codebase rg/narrow read]
- Existing plugin tests import CommonJS helpers from `src/testable.js` through Vitest ESM test files. [VERIFIED: codebase rg/narrow read]
- No new npm package is needed for Phase 6; `vitest`, `jsdom`, `obsidian`, and `obsidian-test-mocks` are already declared dev dependencies. [VERIFIED: package.json]

## Implementation Surface

### Primary Cut-In
`paperforge/plugin/main.js` has this paper-mode flow: resolve current `entry` and `key`, render the paper header and status strip, render `_renderPaperOverviewCard(view, entry)`, then render complete/Next Step, recent discussion, and technical details. [VERIFIED: codebase rg/narrow read]

Recommended insertion:

```js
this._renderPaperOverviewCard(view, entry);
this._renderAnnotationSection(view, this.getAnnotationState(), entry);

if (entry.next_step === 'ready' && entry.deep_reading_status === 'done') {
  ...
} else {
  this._renderNextStepCard(view, entry, key);
}
```

This satisfies the locked placement: overview after, Next Step before. [VERIFIED: annotation-06-CONTEXT.md]

### Runtime Fields and Methods
The constructor already tracks `_currentMode`, `_currentPaperKey`, `_currentPaperEntry`, `_currentFilePath`, cached index items, mode subscribers, and leaf debounce state. [VERIFIED: codebase rg/narrow read]

Phase 6 should add only UI-local state:
- `_annotationUiState`: `{ query, groupMode, typeColorFilter, expandedIds }`. [ASSUMED: implementation recommendation]
- `_annotationSectionEl`: current section container for local rerender. [ASSUMED: implementation recommendation]
- `_lastRenderableAnnotationState`: previous ready/empty state used to preserve stale list when refresh fails. [ASSUMED: implementation recommendation]

Runtime methods should be minimal:
- `_renderAnnotationSection(container, annotationState, entry)`
- `_renderAnnotationControls(section, viewModel)`
- `_renderAnnotationRows(listEl, viewModel)`
- `_rerenderAnnotationSection()`
- `_handleAnnotationRefresh()` calling `loadAnnotationsForCurrentPaper('manual')`

Do not add a second paper resolver; consume `_currentPaperKey` and Phase 5 state only. [VERIFIED: annotation-05 plans]

### Phase 5 Dependency Check
The inspected `main.js` baseline does not contain `loadAnnotationsForCurrentPaper` or `getAnnotationState`. The initial `src/testable.js` baseline also lacked annotation helpers, but the working tree later showed uncommitted Phase 5 helper changes. [VERIFIED: codebase rg/narrow read] [VERIFIED: git status]

Planner should add a Wave 0/preflight checkpoint before Phase 6 implementation:
- Confirm Phase 5 Plan 01/02 has been executed.
- Confirm `src/testable.js` exports annotation bridge helpers and lifecycle helpers.
- Confirm `main.js` exposes real `PaperForgeStatusView` annotation state methods.
- If absent, stop and execute Phase 5 first rather than reimplementing the bridge inside Phase 6. [ASSUMED: implementation recommendation]

## Existing Patterns

### DOM Construction
- `main.js` builds UI with `container.createEl(...)`, classes, text nodes, and event listeners. [VERIFIED: codebase rg/narrow read]
- `_renderEmptyState(container, message)` renders a reusable `.paperforge-empty-state`. [VERIFIED: codebase rg/narrow read]
- `_showMessage(msg, cls)` updates `.paperforge-message msg-${cls}`. [VERIFIED: codebase rg/narrow read]
- Existing paper-mode card styles include `.paperforge-paper-overview`, `.paperforge-next-step-card`, `.paperforge-contextual-btn`, `.paperforge-section-label`, and `.paperforge-status-strip`. [VERIFIED: codebase rg/narrow read]

### Testable Helper Pattern
- `src/testable.js` exports plain CommonJS functions and constants. [VERIFIED: codebase rg/narrow read]
- Existing tests import helpers with `await import('../src/testable.js')`. [VERIFIED: codebase rg/narrow read]
- `runSubprocess` uses dependency injection for child process spawning. [VERIFIED: codebase rg/narrow read]
- Existing plugin tests are helper-focused; there is no current runtime harness for `PaperForgeStatusView`. [VERIFIED: codebase rg/narrow read]

### Export/Test Hook Pattern Needed
`main.js` currently ends with `module.exports = class PaperForgePlugin extends Plugin { ... }`, which makes `PaperForgeStatusView` inaccessible to tests. [VERIFIED: codebase rg/narrow read]

Recommended runtime-test hook:

```js
class PaperForgePlugin extends Plugin {
  ...
}

module.exports = PaperForgePlugin;
module.exports.__test = { PaperForgeStatusView };
```

This keeps plugin export behavior intact while allowing Vitest to instantiate or `Object.create(PaperForgeStatusView.prototype)` for runtime method tests. [ASSUMED: implementation recommendation]

## Pure Functions for `src/testable.js`

Phase 6 should put these in `paperforge/plugin/src/testable.js` and duplicate/integrate only the needed render helpers in `main.js` if the plugin bundling pattern still requires it. [VERIFIED: existing helper pattern] [ASSUMED: implementation recommendation]

| Function | Purpose | Tests |
|----------|---------|-------|
| `createDefaultAnnotationListUiState()` | Session-local defaults: no group, no filter, empty query, no expanded rows. | Defaults match Phase 6 decisions. |
| `getAnnotationIdentity(row)` | Stable row ID from annotation key/id/source fields. | Falls back safely when unsupported fields are missing. |
| `getAnnotationReadingOrderKey(row)` | Page asc, then `sort_index`, then stable ID. | Handles missing page/sort without crashing. |
| `sortAnnotationsForReadingOrder(rows)` | Deterministic default ordering. | Page/sort/index order. |
| `buildAnnotationFilterOptions(rows)` | Type/color options from normalized display fields. | Dedupes and includes labels. |
| `matchesAnnotationSearch(row, query)` | Search selected text and comment only. | Does not match provenance/raw fields. |
| `matchesAnnotationTypeColorFilter(row, filter)` | Type/color filtering. | Works with missing color/type. |
| `groupAnnotationRows(rows, groupMode)` | Modes: none, page, type/color. | Group headers and order are stable. |
| `getAnnotationPreview(text, maxLinesKind)` | Preview decision for selected text/comment. | Indicates truncation/expandability without DOM measurement. |
| `toggleAnnotationExpansion(uiState, rowId)` | Inline expansion state transition. | Pure add/remove behavior. |
| `buildAnnotationListViewModel(annotationState, uiState)` | Single render model for controls, rows, groups, banners, and empty/error messages. | Covers ready, empty, missing-db, missing-paper, cli-error, invalid-json, loading. |
| `mergeAnnotationRefreshResult(previousRenderable, nextState)` | Preserve stale list on failed refresh while showing banner. | Ready -> cli-error keeps stale rows; initial cli-error does not invent rows. |

The line-count preview requirement is visual, but pure helpers can decide text length/truncation and DOM/CSS can enforce 2-line/1-line clamping. [ASSUMED: implementation recommendation]

## Runtime Integration Guidance

### Section Rendering
Render one bounded section using existing card/section patterns:
- Header: title `Annotations`, count, local refresh button.
- Controls: search box; grouping control with `none`, `page`, `type-color`; type/color filter.
- Body: bounded internal scroller for long lists.
- Rows: compact row-list, not cards.
- Expansion: inline details for provenance/read-only/source/attachment/timestamps/raw-debug-safe fields.

All annotation text/comment content should be passed as `text`, never HTML. [VERIFIED: codebase DOM pattern] [ASSUMED: security recommendation]

### Refresh
The section refresh button should:
1. Set section state to local loading and rerender the annotation section only.
2. Call `loadAnnotationsForCurrentPaper('manual')`.
3. Merge the new state with previous renderable state.
4. Rerender `_annotationSectionEl`.

Avoid `_refreshCurrentMode()` for manual annotation refresh unless there is no practical section container, because it invalidates index data and rerenders the whole mode. [VERIFIED: `_refreshCurrentMode` narrow read] [ASSUMED: implementation recommendation]

### Missing PDF and Unsupported Fields
Phase 6 does not navigate to PDFs, but list rows can show a non-actionable `PDF missing` or `source unavailable` detail when Phase 5 row data lacks attachment/PDF identity. [VERIFIED: LIST-05] [ASSUMED: implementation recommendation]

Do not add row click handlers that open PDFs or pages. That belongs to Annotation Phase 7. [VERIFIED: annotation-06-CONTEXT.md]

## Risks

| Risk | Why It Matters | Mitigation |
|------|----------------|------------|
| Phase 5 bridge absent | Current inspected files do not contain annotation bridge helpers or runtime methods. [VERIFIED: codebase rg/narrow read] | Add a preflight gate; do not reimplement CLI parsing in Phase 6. |
| Helper-only tests pass while runtime is unwired | Existing tests only import `src/testable.js`; `PaperForgeStatusView` is not test-accessible. [VERIFIED: codebase rg/narrow read] | Add `module.exports.__test = { PaperForgeStatusView }` and runtime harness tests. |
| Refresh accidentally rerenders whole dashboard | `_refreshCurrentMode()` invalidates index and rerenders current mode. [VERIFIED: codebase rg/narrow read] | Add annotation-section-only rerender path. |
| Search leaks/debug fields | Phase 6 explicitly excludes raw JSON/provenance search. [VERIFIED: annotation-06-CONTEXT.md] | Centralize search in `matchesAnnotationSearch()`. |
| New UI exceeds scope into navigation/editing | Later phases own PDF jump, overlay, editing, writeback, evidence. [VERIFIED: ROADMAP.md] | Tests assert no jump/open action is rendered in Phase 6 rows. |
| XSS/unsafe content rendering | Imported annotation text/comment originates outside the plugin UI. [VERIFIED: annotation feature domain] | Render with text nodes only; never use `innerHTML`. |
| Test command friction on Windows | `npm --version` failed in PowerShell because `npm.ps1` is blocked; `npm.cmd --version` works. [VERIFIED: environment probe] | Use `npm.cmd test` in Windows verification commands. |
| Missing dependencies | `paperforge/plugin/node_modules` is absent. [VERIFIED: environment probe] | Planner should add dependency-install/checkpoint before running plugin tests. |

## Test Strategy

### Required Test Layers
1. `annotation-list-viewmodel.test.mjs`: pure helper tests for filtering/search/group/sort/preview/expansion/render-state decisions. [ASSUMED: implementation recommendation]
2. `annotation-main-runtime.test.mjs`: instantiate the real `PaperForgeStatusView` test hook and verify insertion, refresh, stale result behavior, and state consumption. [ASSUMED: implementation recommendation]
3. `annotation-section-dom.test.mjs` or extend runtime test with jsdom: verify DOM order and row rendering states. [ASSUMED: implementation recommendation]

Vitest supports configured test environments, and `jsdom` is already declared in `package.json`; use explicit jsdom configuration or a per-file environment annotation before asserting DOM behavior. [CITED: https://vitest.dev/config/]

### Minimum Assertions
- `_renderPaperMode()` renders annotation section after `.paperforge-paper-overview` and before `.paperforge-next-step-card` or `.paperforge-complete-row`. [VERIFIED: implementation target]
- Loaded state renders rows with page, swatch, type label, selected text preview, comment preview/icon, and read-only/source detail only in expansion. [VERIFIED: annotation-06-CONTEXT.md]
- Empty, `missing-db`, `missing-paper`, `cli-error`, and `invalid-json` states render distinct messages. [VERIFIED: annotation-06-CONTEXT.md]
- Filtering/grouping/search are computed by helpers and reflected in DOM. [ASSUMED: implementation recommendation]
- Refresh calls `loadAnnotationsForCurrentPaper('manual')` and does not call PDF open/navigation APIs. [VERIFIED: annotation-06-CONTEXT.md]
- Refresh failure after previous ready state keeps stale rows and shows a stale/error banner. [VERIFIED: annotation-06-CONTEXT.md]
- Rows do not render PDF jump buttons, overlay hooks, edit/delete buttons, writeback commands, DB mutation calls, or concept evidence actions. [VERIFIED: annotation-06-CONTEXT.md]

### Commands
Use Windows-safe npm invocation:

```powershell
cd paperforge/plugin
npm.cmd test -- tests/annotation-list-viewmodel.test.mjs
npm.cmd test -- tests/annotation-main-runtime.test.mjs
npm.cmd test
```

Also keep syntax verification:

```powershell
node --check paperforge/plugin/main.js
```

`node_modules` is currently missing, so tests need dependency installation or an existing cache before execution. [VERIFIED: environment probe]

## Recommended Plan Split

### annotation-06-00: Preflight Dependency Gate
**Files:** no code changes unless Phase 5 artifacts are missing.  
**Purpose:** Confirm Phase 5 bridge exists before Phase 6 starts.

Must verify:
- `src/testable.js` has Phase 5 annotation bridge helpers.
- `main.js` has `getAnnotationState()` and `loadAnnotationsForCurrentPaper(reason)`.
- `main.js` has or can safely add a `module.exports.__test` hook for `PaperForgeStatusView`.
- Plugin dependencies are installed or install step is explicitly queued.

If any Phase 5 bridge artifact is absent, planner should route back to Annotation Phase 5 instead of smuggling bridge implementation into Phase 6. [ASSUMED: implementation recommendation]

### annotation-06-01: Pure Annotation List View-Model
**Files:**
- `paperforge/plugin/src/testable.js`
- `paperforge/plugin/tests/annotation-list-viewmodel.test.mjs`

Must implement:
- Filter/search/group/sort helpers.
- Preview/expandability decisions.
- Expansion state transitions.
- `buildAnnotationListViewModel()`.
- Stale-ready merge helper for refresh failures.

Must verify:
- Reading order sort.
- Group modes: none/page/type-color.
- Type/color filter.
- Search selected text/comment only.
- Empty/error/loading render decisions.
- No raw/provenance search.

### annotation-06-02: Runtime Section Rendering and Refresh
**Files:**
- `paperforge/plugin/main.js`
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs`

Must implement:
- Insert `_renderAnnotationSection()` after `_renderPaperOverviewCard()` and before Next Step/complete.
- Session-local UI state fields.
- Local refresh button calling Phase 5 loader.
- Section-only rerender path.
- Runtime test hook if not already present.

Must verify:
- Real `PaperForgeStatusView` renders annotation section in correct order.
- Runtime consumes `getAnnotationState()` instead of parsing CLI output.
- Refresh calls `loadAnnotationsForCurrentPaper('manual')`.
- Stale failure preserves previous list.
- Missing paper/missing db/empty/cli-error/invalid-json render distinctly.
- No PDF jump, overlay, edit/delete, writeback, DB mutation, or concept evidence controls.

### annotation-06-03: Styling, Bounded List, and Full Plugin Regression
**Files:**
- `paperforge/plugin/styles.css`
- `paperforge/plugin/main.js` only if small class hooks are needed
- `paperforge/plugin/tests/annotation-section-dom.test.mjs` or extend runtime test

Must implement:
- Compact row-list styles.
- 2-line selected text clamp and 1-line comment clamp.
- Bounded internal scroll for long lists.
- Color swatch plus type label.
- Expansion details layout.

Must verify:
- Long list does not dominate paper panel.
- Text remains readable and does not overflow row controls.
- Expanded details do not show by default.
- `node --check paperforge/plugin/main.js`.
- `npm.cmd test` for full plugin suite, noting any pre-existing unrelated failures separately.

## Do Not Hand-Roll / Do Not Cross Scope

| Problem | Do Not Build in Phase 6 | Use Instead |
|---------|--------------------------|-------------|
| Annotation data loading | New JS database reads or CLI parsing | Phase 5 `getAnnotationState()` and `loadAnnotationsForCurrentPaper()` |
| PDF navigation | Row jump/open-at-page actions | Defer to Annotation Phase 7 |
| PDF overlay | Viewer DOM hooks, marks, popovers | Defer to Annotation Phase 8 |
| Annotation editing | Create/edit/delete local annotations | Future editing requirements |
| Zotero sync-back | Zotero Web API or SQLite writes | Out of scope; v0.2 remains read-only |
| Evidence integration | Concept-card evidence anchors | Future EVID requirements |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | syntax check and plugin tests | yes | v24.16.0 | none needed |
| npm via `npm.cmd` | plugin dependency install/test | yes | 11.13.0 | use `npm.cmd`, not `npm` in PowerShell |
| plugin `node_modules` | Vitest execution | no | n/a | run dependency install/checkpoint before tests |
| Vitest/jsdom deps | DOM/runtime tests | declared, not installed | package.json declares `vitest`, `jsdom`, `obsidian`, `obsidian-test-mocks` | install existing deps; no new package needed |

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth change. |
| V3 Session Management | no | No session state. |
| V4 Access Control | yes | Do not add DB mutation, editing, writeback, or external actions. |
| V5 Input Validation | yes | Treat annotation text/comment as untrusted display text; render via text nodes. |
| V6 Cryptography | no | No crypto change. |

Known threat patterns:
- Tampering: accidental DB mutation through new JS code. Mitigation: consume Phase 5 state only; no DB access in Phase 6. [VERIFIED: SAFE requirements]
- Information disclosure: raw traceback/shell output in UI. Mitigation: render friendly bridge messages only. [VERIFIED: SAFE-04]
- XSS/UI injection: imported annotation text/comment rendered as HTML. Mitigation: `createEl({ text })` or `setText`, never `innerHTML`. [ASSUMED: security recommendation based on code pattern]

## Sources

### Primary
- `.planning/ROADMAP.md` - Phase 6 goal, dependencies, later phase boundaries. [VERIFIED: codebase read]
- `.planning/REQUIREMENTS.md` - LIST, SAFE, TEST, OVLY scope boundaries. [VERIFIED: codebase read]
- `.planning/STATE.md` - current milestone state and baseline failures. [VERIFIED: codebase read]
- `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md` - locked Phase 6 implementation decisions. [VERIFIED: codebase read]
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-CONTEXT.md` - bridge contract Phase 6 should consume. [VERIFIED: codebase read]
- `.planning/phases/annotation-05-plugin-annotation-data-bridge/annotation-05-01-PLAN.md` and `annotation-05-02-PLAN.md` - planned helper/runtime bridge shape. [VERIFIED: codebase read]
- `paperforge/plugin/main.js` - actual `PaperForgeStatusView` render and export surface. [VERIFIED: codebase rg/narrow read]
- `paperforge/plugin/src/testable.js` - current testable helper exports. [VERIFIED: codebase read]
- `paperforge/plugin/tests/runtime.test.mjs`, `commands.test.mjs`, `errors.test.mjs`, `vector-ready.test.mjs` - current Vitest patterns. [VERIFIED: codebase read]
- `paperforge/plugin/package.json` - test script and dev dependencies. [VERIFIED: codebase read]

### Secondary
- Vitest configuration docs: `https://vitest.dev/config/` - jsdom/test environment guidance. [CITED: https://vitest.dev/config/]

### Assumptions Log
| # | Claim | Risk if Wrong |
|---|-------|---------------|
| A1 | Recommended helper names and exact state shapes are implementation recommendations, not existing code. | Planner may need to adapt names to Phase 5 actual implementation. |
| A2 | Section-only rerender is preferable to `_refreshCurrentMode()` for manual annotation refresh. | If Obsidian lifecycle constraints require full rerender, implementation can still meet behavior with more invalidation. |
| A3 | A `module.exports.__test` hook is acceptable for runtime tests. | If release packaging forbids this, planner needs an alternate side-effect-free export strategy. |
| A4 | Text-node rendering is sufficient to mitigate annotation text injection in this UI. | If later rich annotation markup is supported, sanitizer policy must be added before rendering markup. |

## Open Questions (RESOLVED)

1. **Has Annotation Phase 5 actually been executed and stabilized in this branch?**
   - What we know: Phase 5 plans specify bridge helpers/runtime methods; initial baseline reads did not show them, while later working-tree status showed uncommitted Phase 5 helper artifacts. [VERIFIED: codebase rg/narrow read] [VERIFIED: git status]
   - Resolution: Treat Phase 5 as a hard prerequisite. `annotation-06-01-PLAN.md` is the dependency/preflight plan and must stop Phase 6 execution if the Phase 5 bridge helpers or runtime methods are absent or incomplete.

2. **Will Phase 6 add a dedicated Vitest jsdom config or per-file environment annotation?**
   - What we know: `jsdom` is declared but not installed locally; no config file was inspected. [VERIFIED: package.json] [VERIFIED: environment probe]
   - Resolution: Use the smallest test-environment change needed by the Phase 6 DOM/runtime tests. Prefer per-file jsdom annotations or the existing plugin Vitest config; do not add a new package.

3. **Should labels be English-only for now?**
   - What we know: Phase 6 context permits concise English labels until broader localization. [VERIFIED: annotation-06-CONTEXT.md]
   - Resolution: Use concise, non-corrupted labels consistent with the current plugin surface. Full localization is out of scope for Phase 6 unless the executor can reuse existing i18n keys without expanding scope.

### Ready for Planning
Research complete. Planner can create Phase 6 plans with a preflight dependency gate, pure helper plan, runtime integration plan, and styling/regression plan.
