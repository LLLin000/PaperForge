---
phase: annotation-06-annotation-sidebar-and-list-view
plan: 03
subsystem: plugin-runtime
tags: [annotation-list, paper-mode, obsidian-plugin, dom-rendering, view-model]
requires:
  - phase: annotation-06-01
    provides: Phase 5 bridge stubs (getAnnotationState, loadAnnotationsForCurrentPaper) in main.js
  - phase: annotation-06-02
    provides: View-model helper functions (buildAnnotationListViewModel, mergeAnnotationRefreshResult, etc.)
provides:
  - Embedded annotation list section in PaperForgeStatusView paper-mode runtime
  - Section-local controls (search, grouping, type/color filter) with session-only UI state
  - Manual refresh via loadAnnotationsForCurrentPaper('manual') with stale-data banner
  - Distinct rendering for loading, ready, empty, missing-db, missing-paper, cli-error, invalid-json states
  - Forbidden-scope guard tests: no PDF jump, overlay, edit/delete, write-back, DB mutation, concept-card controls
affects: annotation-06-04 (sidebar integration)
tech-stack:
  added: []
  patterns:
    - "Section-local _rerenderAnnotationSection using container.empty() + rebuild"
    - "Session-only UI state fields (_annotationUiState) reset with view instance"
    - "Recursive createEl in DOM mocks for test reliability"
key-files:
  created:
    - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  modified:
    - paperforge/plugin/main.js
key-decisions:
  - "Inlined Plan 02 view-model helpers directly in main.js instead of importing from a shared module to avoid Node-only test module dependencies in the Obsidian bundle"
  - "Used section.empty() + full rebuild for rerender to preserve DOM ordering guarantees"
  - "Session-only _annotationUiState with query, groupMode, typeColorFilter, expandedIds fields — never persisted"
  - "Recursive createEl in test DOM mocks so createEl returns elements that also have createEl"
requirements-completed:
  - LIST-01
  - LIST-02
  - LIST-03
  - LIST-04
  - LIST-05
duration: 22min
completed: 2026-06-20
---

# Phase 06: Annotation Sidebar & List View — Plan 03 Summary

**Embedded annotation list section in PaperForgeStatusView paper-mode runtime with section-local controls, manual refresh, stale-data handling, and 28 runtime tests enforcing Phase 6 forbidden-scope boundaries**

## Performance

- **Duration:** 22 min
- **Started:** 2026-06-20T00:30:00Z
- **Completed:** 2026-06-20T00:52:00Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 2

## Accomplishments
- Inserted `_renderAnnotationSection(view, this.getAnnotationState(), entry)` call in `_renderPaperMode()` immediately after `_renderPaperOverviewCard` and before the Next Step / Complete branch — locked insertion point per D-01 and D-02
- Added `_renderAnnotationSection()`, `_renderAnnotationControls()`, `_renderAnnotationRows()`, `_rerenderAnnotationSection()`, `_handleAnnotationRefresh()` methods to `PaperForgeStatusView` with full rendering, controls, stale banner, and distinct states
- Inlined Phase 6 Plan 02 view-model helpers (`buildAnnotationListViewModel`, `buildAnnotationFilterOptions`, `mergeAnnotationRefreshResult`, `getAnnotationIdentity`, `toggleAnnotationExpansion`, etc.) into `main.js` after the annotation bridge section
- Added session-local UI state fields (`_annotationUiState`, `_annotationSectionEl`, `_lastRenderableAnnotationState`) that reset with view instance
- Created 28 runtime tests covering Task 1 (test hook, DOM insertion point, section placement, controls, `getAnnotationState` consumption) and Task 2 (controls update session state, distinct states, refresh calls `loadAnnotationsForCurrentPaper('manual')`, stale banner, row rendering with text content, forbidden controls absent)
- All verification passes: syntax check, 78 view-model tests, 28 runtime tests

## Task Commits

1. **Task 1 + Task 2 (TDD): Add runtime tests and paper-mode insertion point; implement controls, section-local refresh, stale banner, and forbidden-scope guards** — `a63237f` (feat)

**Plan metadata:** (included in task commit)

_Note: TDD tasks committed together since implementation required both tasks to be coherent._

## Files Created/Modified
- `paperforge/plugin/main.js` — Modified: Added ~700 lines for annotation section rendering, controls, refresh handling, and inlined view-model helpers in `PaperForgeStatusView`
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` — Created: 640 lines, 28 tests covering Task 1 and Task 2

## Decisions Made
- **Inlined Plan 02 helpers in main.js:** Avoided importing from Node-only test modules in the Obsidian bundle. Helpers are pure functions (no DOM, no node APIs) so they compile cleanly into the plugin bundle
- **section.empty() + rebuild for rerender:** Simpler and more reliable than DOM replacement. The annotation section is leaf-level (no children to preserve state), so clearing and rebuilding is safe
- **Session-only UI state:** `_annotationUiState` fields (`query`, `groupMode`, `typeColorFilter`, `expandedIds`) live only on the view instance and are never persisted to settings, localStorage, or files
- **Recursive createEl in test mocks:** `createObsidianEl` and `addCreateEl` now chain — elements created via `createEl()` also have `createEl()` themselves, matching Obsidian's real DOM API behavior

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `addCreateEl` to return recursive elements with `createEl`**
- **Found during:** Task 1 (Test execution — all 28 tests failed with `view.createEl is not a function`)
- **Issue:** The test DOM helper `addCreateEl` patched `createEl` onto elements but the returned child elements did not have `createEl` attached. When `_renderPaperMode` created a `.paperforge-paper-view` div via `this._contentEl.createEl(...)`, and then passed it to `_renderAnnotationSection(container, ...)`, the container had no `createEl` method, causing cascading failures
- **Fix:** Made `createEl` recursive: `return addCreateEl(child)` so every element created via `createEl` also gets the `createEl`, `empty`, `setText`, `addClass`, `removeClass` methods
- **Files modified:** `paperforge/plugin/tests/annotation-main-runtime.test.mjs`
- **Verification:** All 28 tests pass
- **Committed in:** a63237f (part of task commit)

**2. [Rule 1 - Bug] Fixed `missing-paper` state test passing `paperKey: null`**
- **Found during:** Task 2 (Test execution — "renders distinct missing-paper message" failed: `expected null to be truthy`)
- **Issue:** The test passed `paperKey: null` to `makeRuntimeView` for the `missing-paper` state. In `_renderPaperMode()`, the `if (!key) { this._renderEmptyState(...); return; }` guard at line 2307 returned early before creating the annotation section. A `missing-paper` annotation state means the paper key **exists** but the PDF/content is missing from storage, so the view's `paperKey` should be a valid value
- **Fix:** Changed the test to use `paperKey: 'PAPER_A'` for all state types (both the annotation state and the view), since the annotation state's load state already encodes the difference between states
- **Files modified:** `paperforge/plugin/tests/annotation-main-runtime.test.mjs`
- **Verification:** All 28 tests pass
- **Committed in:** a63237f (part of task commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug)
**Impact on plan:** Both fixes were necessary for test correctness. No scope creep.

## Issues Encountered
- **Test DOM mock recursion:** `addCreateEl` initially returned raw `document.createElement(tag)` elements without the `createEl` proxy. This caused `view.createEl is not a function` in all 28 tests because the paper-view div (created by `_contentEl.createEl`) was used as the container for `_renderAnnotationSection`. Fixed by making `createEl` recursive.
- **`missing-paper` test semantics:** The test incorrectly conflated "missing paper" (PDF file missing from storage) with "no paper key" (no paper selected). Fixed by using a valid paper key and relying on the annotation state's load state to communicate the distinction.

## Next Phase Readiness
- All runtime rendering for the annotation list section is complete and tested
- Plan 04 (sidebar integration) can now build on the `_renderAnnotationSection` insertion point
- No blockers — the annotation section is embedded, expanded by default, and strictly scoped per Phase 6 constraints

---

*Phase: annotation-06-annotation-sidebar-and-list-view*
*Completed: 2026-06-20*

## Self-Check

- [x] All tasks executed — 2 TDD tasks (Task 1 + Task 2 combined in single commit)
- [x] Task committed with proper format — `feat(annotation-06-03)` at `a63237f`
- [x] All deviations documented — 2 auto-fixed bugs
- [x] Authentication gates — None encountered
- [x] SUMMARY.md created with substantive content ✓
- [x] STATE.md updated — progression, metrics, decisions, session recorded
- [x] ROADMAP.md updated with plan progress ✓
- [x] REQUIREMENTS.md updated — LIST-01 through LIST-05 marked complete
- [x] Final metadata commit made — `158fa32` via gsd-tools
- [x] Completion format returned below

**Self-Check: PASSED**
