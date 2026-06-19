---
phase: annotation-05-plugin-annotation-data-bridge
plan: 02
subsystem: plugin
tags: [obsidian-plugin, annotation-bridge, runtime-state, vitest, paperforge-status-view]
requires:
  - phase: annotation-05-plugin-annotation-data-bridge
    provides: Node-testable annotation bridge helpers, normalized rows, and annotation load states from Plan 01
provides:
  - PaperForgeStatusView annotation state initialized to idle
  - Active-paper annotation loader method for Phase 6 manual refresh
  - Runtime stale-result guard for active paper changes
  - Runtime test hook for PaperForgeStatusView
  - Vitest runtime harness for main.js annotation wiring
affects: [annotation-06-annotation-sidebar-and-list-view]
tech-stack:
  added: []
  patterns:
    - "Runtime helper logic mirrors src/testable.js because the bundled Obsidian plugin cannot require local source modules"
    - "PaperForgeStatusView exposes state through getAnnotationState() and loadAnnotationsForCurrentPaper(reason)"
    - "Runtime tests stub Obsidian and inject _annotationLoader to avoid Python subprocess execution"
key-files:
  created:
    - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  modified:
    - paperforge/plugin/main.js
    - .planning/ROADMAP.md
    - .planning/STATE.md
key-decisions:
  - "Use existing _currentPaperKey as the only runtime paper identity for annotation loading."
  - "Expose _annotationLoader as a test-only instance injection point while production continues to use loadAnnotationsForPaper."
  - "Keep Phase 5 invisible: no list UI, refresh button, PDF jump, overlay, editing, write-back, or database mutation."
patterns-established:
  - "Runtime state starts as idle, moves to missing-paper without subprocess when no active paper exists, and stores full bridge states for later UI rendering."
  - "Monotonic _annotationLoadSeq prevents stale async results from overwriting a newer active paper."
  - "main.js __test hook exposes PaperForgeStatusView without changing the plugin's default export."
requirements-completed: [BRDG-01, BRDG-02, BRDG-03, BRDG-04]
duration: 35min
completed: 2026-06-19
---

# Phase 5 Plan 02: Plugin Annotation Runtime Integration Summary

**Active-paper annotation bridge state wired into PaperForgeStatusView with stale-load protection and runtime coverage**

## Performance

- **Duration:** 35 min
- **Started:** 2026-06-19T22:35:00+08:00
- **Completed:** 2026-06-19T23:09:29+08:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `PaperForgeStatusView` runtime annotation state initialized to `idle`.
- Added `getAnnotationState()` and `loadAnnotationsForCurrentPaper(reason)` for Phase 6 to consume.
- Reused `_currentPaperKey` as the only paper identity and set `missing-paper` without calling the bridge when no paper is active.
- Added `_annotationLoadSeq` stale-result protection so older async loads cannot overwrite a newer active paper state.
- Hooked annotation loading into active paper detection and current-mode refresh.
- Added `annotation-main-runtime.test.mjs`, which exercises the real `main.js` `PaperForgeStatusView` path with an Obsidian stub and injected loader.

## Task Commits

1. **Task 1+2: Runtime bridge wiring and harness** - `0aa0302` (feat/test)

Earlier Plan 02 foundation already existed in history:

- `1c58fd7` - inline annotation bridge helpers and lifecycle controller

## Files Created/Modified

- `paperforge/plugin/main.js` - Stores annotation state, exposes loader/state methods, loads on active-paper changes, and exposes a non-rendering `__test` hook.
- `paperforge/plugin/tests/annotation-main-runtime.test.mjs` - Runtime tests for current key loading, missing-paper skip, stale-result guard, stored state access, `_detectAndSwitch()`, and `_refreshCurrentMode()`.
- `.planning/ROADMAP.md` - Marks Annotation Phase 5 as executed.
- `.planning/STATE.md` - Records Phase 5 completion and keeps Annotation Phase 6 as the next planned work.

## Decisions Made

- Kept the production loader path unchanged by default: `loadAnnotationsForCurrentPaper()` calls `loadAnnotationsForPaper()` unless a test injects `_annotationLoader`.
- Kept Phase 5 UI-invisible. Visible annotation list, refresh controls, grouping, filtering, and styling remain Phase 6 work.
- Did not add TypeScript/JavaScript database access; plugin runtime still uses the v0.1 CLI bridge.

## Deviations from Plan

None in product scope. The runtime test harness required a local Obsidian module stub because the `obsidian` npm package is type-definition-only and cannot be required directly at runtime.

## Issues Encountered

- Sandbox Vitest run failed with `Access is denied` while esbuild loaded `vitest.config.ts`. Running the same `npm.cmd test ...` commands outside the sandbox succeeded.
- Full plugin suite still has 3 pre-existing baseline failures unrelated to annotation runtime wiring:
  - `tests/errors.test.mjs`: 2 `buildRuntimeInstallCommand` expectation failures.
  - `tests/runtime.test.mjs`: 1 Windows `resolvePythonExecutable` `py -3` expectation failure.

## Verification

- `node --check paperforge/plugin/main.js` - passed.
- `npm.cmd test -- tests/annotation-bridge.test.mjs` - passed, 40 tests.
- `npm.cmd test -- tests/annotation-lifecycle.test.mjs` - passed, 15 tests.
- `npm.cmd test -- tests/annotation-main-runtime.test.mjs` - passed, 6 tests.
- `npm.cmd test` - ran 102 tests total: 99 passed, 3 failed due to the known unrelated baseline failures listed above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Annotation Phase 6 can now consume `PaperForgeStatusView.getAnnotationState()` and `loadAnnotationsForCurrentPaper('manual')` instead of reparsing raw CLI output. Phase 6 should keep its preflight gate, but the Phase 5 runtime bridge is now present for list UI work.

---

*Phase: annotation-05-plugin-annotation-data-bridge*
*Completed: 2026-06-19*
