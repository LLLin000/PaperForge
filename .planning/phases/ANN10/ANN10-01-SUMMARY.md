---
phase: ANN10
plan: "01"
subsystem: canvas
tags: [canvas, dom-render, annotation-loader, stale-guard, lifecycle-controller, read-only, vitest, commonjs]

# Dependency graph
requires:
  - phase: ANN09
    provides: v0.2 annotation contracts (loadAnnotationsForPaper, makeAnnotationState, ANNOTATION_LOAD_STATES)
  - phase: RESEARCH
    provides: architecture recommendations (src/canvas/* module seams, ItemView pattern)
provides:
  - canvas context resolution (buildCanvasContextFromEntry / buildMissingCanvasContext)
  - thin annotation wrapper over v0.2 loader contracts (createCanvasAnnotationLoader)
  - canvas session controller with fixed paper identity, stale-guarded refresh, teardown (createCanvasSessionController)
  - Phase ANN10 shell DOM render dispatch covering 10 states (renderCanvasView)
  - paper identity header and stale banner overlay rendering
  - 82 focused Vitest tests proving explicit paper identity, v0.2 contract reuse, stale-result safety, read-only rendering
affects: [ANN10-02, ANN11, ANN12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Canvas modules under src/canvas/ exported via CommonJS index.js"
    - "Canvas annotation loader wraps v0.2 loadAnnotationsForPaper — no new CLI contract"
    - "Session controller owns fixed paperKey via construction, never reads global _currentPaperKey"
    - "Stale-guard pattern: monotonic load sequence discards superseded async results"
    - "Shell render dispatch: switch on vm.state with separate render* functions"
    - "All user-facing text via textContent — never innerHTML for annotation data"

key-files:
  created:
    - "paperforge/plugin/src/canvas/context.js"
    - "paperforge/plugin/src/canvas/annotations.js"
    - "paperforge/plugin/src/canvas/controller.js"
    - "paperforge/plugin/src/canvas/render.js"
    - "paperforge/plugin/tests/canvas-context.test.mjs"
    - "paperforge/plugin/tests/canvas-controller.test.mjs"
    - "paperforge/plugin/tests/canvas-render.test.mjs"
  modified:
    - "paperforge/plugin/src/canvas/index.js"

key-decisions:
  - "Controller test helpers use makeV02Loader() + createCanvasAnnotationLoader wrapper instead of raw { loadForPaper: fn } mocks — aligns with annotations.js wrapper contract"
  - "'database' excluded from render test's FORBIDDEN_WORDS text-level check because status messages legitimately describe annotation database state; still checked at button level"
  - "Render dispatch explicitly lists all handled states; default renders idle placeholder"

patterns-established:
  - "Canvas module test files: canvas-{module}.test.mjs pattern"
  - "Render forbidden-controls assertion: check innerHTML + button textContent"
  - "Controller stale-guard test pattern: controlled-promise resolution via v0.2 loader mock"

requirements-completed: [CANVAS-02]

# Metrics
duration: ~45min
completed: 2026-07-05
---

# Phase ANN10 — Plan 01: Canvas Data Contract Foundation Summary

**Fixed-paper-identity context resolution, v0.2 annotation contract wrapper, lifecycle controller with stale-guarded async refresh, and read-only shell DOM render dispatch covering 10 states — all under 82 Vitest tests**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-07-05
- **Completed:** 2026-07-05
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Canvas context resolution (`buildCanvasContextFromEntry`, `buildMissingCanvasContext`) with `entry.key` authoritative for paper identity and explicit fail-closed result objects
- Thin annotation wrapper (`createCanvasAnnotationLoader`) delegating to v0.2 `loadAnnotationsForPaper` — no new DB, Zotero, or subprocess API
- Session controller (`createCanvasSessionController`) with fixed paperKey, stale-guarded monotonic load sequence, refresh coordination, and safe teardown
- Shell render dispatch (`renderCanvasView`) switching on 10 states: idle, loading, ready, empty, missing-paper, missing-db, cli-error, invalid-json, missing-source, unsupported; plus paper identity header and stale banner
- All user-facing text via `textContent` — no `innerHTML` for annotation data — tested with XSS payload encoding
- No card, anchor, connector, persistent layout, or editing controls introduced (Phase 11+ scope)
- CommonJS export surface through `canvas/index.js`

## Task Commits

Each task was committed atomically:

1. **Task 1: Canvas context and annotation contract modules** — `994e318` (feat)
2. **Task 2: Canvas controller lifecycle and shell renderer** — `019e633` (feat)

## Files Created/Modified

- `paperforge/plugin/src/canvas/context.js` — `buildCanvasContextFromEntry(entry)`, `buildMissingCanvasContext(reason)`. Returns `{ ok, paperKey, entry, reason }` objects. `entry.key` is authoritative.
- `paperforge/plugin/src/canvas/annotations.js` — `createCanvasAnnotationLoader({ loadAnnotationsForPaper })`, `ANNOTATION_LOAD_STATES`. Thin wrapper over v0.2 contracts; no new CLI/subprocess code.
- `paperforge/plugin/src/canvas/controller.js` — `createCanvasSessionController({ paperKey, annotationLoader })`. Fixed paperKey, stale-guarded async refresh via monotonic sequence, teardown disposes controller.
- `paperforge/plugin/src/canvas/render.js` — `renderCanvasView(contentEl, vm)`, 10 render helpers. Shell states only. textContent-safe. No edit/write controls.
- `paperforge/plugin/src/canvas/index.js` — CommonJS re-export of all canvas modules.
- `paperforge/plugin/tests/canvas-context.test.mjs` — 27 tests: entry resolution, missing/invalid entries, key authority, annotation wrapper delegation with explicit paperKey.
- `paperforge/plugin/tests/canvas-controller.test.mjs` — 20 tests: lifecycle (fixed paperKey, getState tracking, stale discard, monotonic sequence, refresh coordination, teardown).
- `paperforge/plugin/tests/canvas-render.test.mjs` — 35 tests: shell states (all 10), paper identity header, stale banner, safe text (XSS encoding), forbidden-control absence, no Phase 11+ class leakage.

## Decisions Made

- **Controller tests use v0.2 wrapper pattern**: Helpers `makeV02Loader()`, `makeMockLoader(v02Mock)`, `makeFailV02Loader()`, `makeSlowV02Loader(delayMs)` create v0.2-compatible functions wrapped by `createCanvasAnnotationLoader`. This avoids the raw `{ loadForPaper: fn }` mock pattern which bypasses the annotations.js wrapper contract.
- **"database" excluded from FORBIDDEN_WORDS text-level check**: Status message "Annotation database is not available" legitimately describes DB state. The word is still checked at button level. `evidence` and `concept card` remain in the full check as they never appear in status messages.
- **Render dispatch explicit-state list**: All handled states listed explicitly in the switch; `default` renders idle placeholder. This makes it easy to audit which states are supported and catches unsupported states at test time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Controller test mocks bypassed annotations.js wrapper contract**
- **Found during:** Task 2 (Controller lifecycle tests)
- **Issue:** Tests used raw `{ loadForPaper: vi.fn(async ({ paperKey }) => ...) }` mocks. The controller calls `annotationLoader.loadForPaper(paperKey, loadOptions)` with string args, but the mock destructured `{ paperKey }` from the first arg (expecting an object). This caused `paperKey` to be `undefined` in tests.
- **Fix:** Replaced all raw loader mocks with `createCanvasAnnotationLoader` wrapping v0.2-compatible functions created by `makeV02Loader()`, `makeSlowV02Loader()`, `makeFailV02Loader()`. Test helpers ensure correct signature delegation.
- **Files modified:** `paperforge/plugin/tests/canvas-controller.test.mjs`
- **Verification:** All 20 controller tests pass. Stale-guard monotonic sequence test uses controlled-promise resolution pattern.
- **Committed in:** 019e633 (Task 2 commit)

**2. [Rule 2 - Missing Critical] FORBIDDEN_WORDS included "database" causing false positive in missing-db state test**
- **Found during:** Task 2 (Render tests)
- **Issue:** `assertNoForbiddenControls` checked `innerHTML` for "database" — the `missing-db` state message "Annotation database is not available" failed this check. The word "database" in a status message describing DB state is a valid description, not a control keyword.
- **Fix:** Removed "database" from the FORBIDDEN_WORDS text-level check. Added inline comment explaining why. The button-level check still covers all words including "database".
- **Files modified:** `paperforge/plugin/tests/canvas-render.test.mjs`
- **Verification:** All 35 render tests pass including missing-db state test.
- **Committed in:** 019e633 (Task 2 commit)

**3. [Rule 2 - Missing Critical] Render dispatch missing `missing-source` and `unsupported` cases**
- **Found during:** Initial test run
- **Issue:** `renderCanvasView` switch did not handle `missing-source` or `unsupported` states — they fell through to `default` (rendering idle placeholder). Test expectations for `.paperforge-canvas-missing-source` and `.paperforge-canvas-unsupported` elements failed.
- **Fix:** Added `case 'missing-source'` (→ `renderCanvasMissingSource`) and `case 'unsupported'` (→ `renderCanvasUnsupported`) to the switch statement. Render helper functions already existed.
- **Files modified:** `paperforge/plugin/src/canvas/render.js`
- **Verification:** All render tests pass, including missing-source and unsupported state tests.
- **Committed in:** 019e633 (Task 2 commit)

**Total deviations:** 3 auto-fixed (2 missing critical, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness and test reliability. No scope creep.

## Issues Encountered

- The annotations.js wrapper contract (v0.2) was introduced in the original source but the controller tests bypassed it with raw mocks. Once all tests used the proper `createCanvasAnnotationLoader` wrapping pattern, all controller tests passed.
- The `render.js` switch dispatch had redundant SSR `typeof` guards that were removed during planning; the jsdom test environment handles `document.createElement` natively.

## Next Phase Readiness

- **Ready for ANN10-02 (Obsidian view registration):** Canvas context resolution, annotation wrapper, controller lifecycle, and render shell are all tested and exportable via CommonJS `index.js`. `main.js` can require `src/canvas/` modules and register the canvas view.
- **For ANN11 (Card layout):** The render dispatch switch is extensible — adding a `case 'ready'` that renders card lanes is the next step. The paper identity header and stale banner are already handled.
- **Test frameworks verified:** 82 tests across 3 focused files all pass in jsdom environment. The annotation-bridge, annotation-main-runtime, and annotation-section-dom test files remain independently passable.

---
*Phase: ANN10 — Plan 01*
*Completed: 2026-07-05*
