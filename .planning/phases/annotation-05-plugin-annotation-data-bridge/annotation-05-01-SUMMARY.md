---
phase: annotation-05-plugin-annotation-data-bridge
plan: 01
subsystem: plugin
tags: [vitest, annotation-bridge, pfbridge, testable-js, cli-contract, state-machine]
requires:
  - phase: annotation-04-verification-gate
    provides: CLI PFResult contract verification, annotation status/export JSON shapes
  - phase: annotation-03-cli-json-contracts
    provides: annotation export --json and status --json command behavior
provides:
  - Node-testable annotation bridge helpers in testable.js
  - Export-row normalization with display/provenance/pdfLocation/raw sections
  - 8-state annotation load state machine (idle/loading/ready/empty/missing-paper/missing-db/cli-error/invalid-json)
  - Async loadAnnotationsForPaper with two-step status-then-export pattern
  - CLI arg builders for annotation status --json and annotation export --paper KEY --json
  - Representative PFResult fixtures for plugin-side testing
affects: [annotation-06-annotation-sidebar-and-list-view]

tech-stack:
  added: []
  patterns:
    - "Injected runSubprocessFn for deterministic CLI fixture testing"
    - "Two-step loader: status preflight (DB check) then export (data fetch)"
    - "Normalized row sections: display, provenance, pdfLocation, raw"

key-files:
  created:
    - paperforge/plugin/tests/annotation-bridge.test.mjs
  modified:
    - paperforge/plugin/src/testable.js

key-decisions:
  - "Loader uses annotation status --json first to detect DB availability before calling export"
  - "Non-zero subprocess exit code is classified as cli-error before JSON parsing (prevents invalid-json misclassification)"
  - "PFResult with ok:false provides the error code from the JSON envelope, even when exitCode is non-zero"
  - "Empty subprocess results: exitCode 0 with invalid JSON → invalid-json; exitCode non-zero → cli-error"
  - "runSubprocessFn injection at the function level (not individual spawn level) for cleaner test fixtures"

patterns-established:
  - "Helper functions receive injected subprocess runner (runSubprocessFn) that returns Promise<{stdout, stderr, exitCode}>"
  - "State factory makeAnnotationState produces consistent objects across all 8 states"
  - "PFResult fixtures in tests mirror Python CLI contract shapes from test_annotation_json_contracts.py"

requirements-completed: [BRDG-01, BRDG-02, BRDG-03, BRDG-04]

duration: 18min
completed: 2026-06-19
---

# Phase 5 Plan 01: Plugin Annotation Data Bridge Summary

**Node-testable annotation bridge helpers — CLI arg builders, PFResult JSON parser, 8-state load classifier, and export-row normalizer — for the Obsidian plugin**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-19T11:13:00Z
- **Completed:** 2026-06-19T11:31:00Z
- **Tasks:** 2 (both TDD: RED+GREEN)
- **Files modified:** 2

## Accomplishments

- Created `normalizeAnnotationExportRow(row)` that maps export rows into `{display, provenance, pdfLocation, raw}` sections preserving the original row object reference under `raw`
- Defined 8 stable annotation load state names in `ANNOTATION_LOAD_STATES` constant map
- Implemented `makeAnnotationState(stateName, opts)` factory producing consistent typed state objects with `state`, `paperKey`, `annotations`, `message`, `errorCode`, and `raw` fields
- Built `buildAnnotationStatusArgs(extraArgs)` and `buildAnnotationExportArgs(paperKey, extraArgs)` CLI arg builders following the `-m paperforge annotation` module pattern
- Implemented `loadAnnotationsForPaper(options)` async loader with two-step flow (status preflight → export fetch), comprehensive failure classification, and injected `runSubprocessFn` support for deterministic testing
- All 40 tests pass, covering success, empty, missing-paper, missing-db, cli-error, and invalid-json states
- Representative PFResult fixtures based on Python CLI contract tests (`test_annotation_json_contracts.py`) for plugin-side coverage

## Task Commits

Each task was committed atomically using TDD discipline:

1. **Task 1+2 (RED): Add annotation bridge tests** — `92b46bd` (test)
2. **Task 1+2 (GREEN): Implement helpers** — `6a25497` (feat)

_Note: Both tasks share the same files (test file + testable.js) so RED and GREEN commits cover both tasks._

## Files Created/Modified

- `paperforge/plugin/tests/annotation-bridge.test.mjs` — 40 Vitest tests covering all bridge functions and load states with PFResult fixtures
- `paperforge/plugin/src/testable.js` — 6 new exported symbols: `ANNOTATION_LOAD_STATES`, `normalizeAnnotationExportRow`, `makeAnnotationState`, `buildAnnotationStatusArgs`, `buildAnnotationExportArgs`, `loadAnnotationsForPaper`

## Decisions Made

- **Loader architecture:** Two-step flow (status first, then export) prevents misinterpretation of missing DB as empty paper. Status PFResult `data.db_available` is the discriminator.
- **Error classification priority:** Subprocess errors (throws) → cli-error. Exit code non-zero → cli-error (after trying to parse PFResult for richer error code). Exit code zero + invalid JSON → invalid-json. Exit code zero + PFResult ok:false → cli-error with error code from PFResult.
- **Injection pattern:** `loadAnnotationsForPaper` accepts `runSubprocessFn` as a function matching the return shape of `runSubprocess`. This is cleaner than injecting at the individual spawn level and matches existing patterns.
- **State factory:** `makeAnnotationState` normalizes all state fields with sensible defaults (empty arrays, null for missing values), making state consumers simpler.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- **Mock subprocess complexity:** Initial complex event-emitter mock (`makeMockSubprocess`) was fragile and incompatible with sequential status+export calls. Replaced with `mockSubprocessSequence` pattern using simple pre-resolved Promises via `mockResolvedValueOnce`, which is cleaner and deterministic.
- **Error classification ordering:** Initial implementation checked `exitCode !== 0` before JSON parsing, which masked PFResult error codes when the CLI returned a valid JSON error with a non-zero exit code. Fixed by parsing JSON first and using the PFResult error code when available, falling back to `CLI_ERROR` generic code only when JSON parsing fails.

## TDD Gate Compliance

- ✅ RED commit (`test(...)`) exists — `92b46bd`
- ✅ GREEN commit (`feat(...)`) exists after RED — `6a25497`
- No REFACTOR commit needed (code was clean on first pass)

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Bridge helpers are fully implemented and testable for Phase 6 (annotation sidebar/list view)
- Phase 6 can consume `loadAnnotationsForPaper` output to render list, empty, and error states without reparsing CLI output
- `normalizeAnnotationExportRow` output is ready for direct rendering in Obsidian UI
- Pre-existing baseline test failures (3 tests in errors.test.mjs and runtime.test.mjs) are unrelated and pre-date this plan

---

*Phase: annotation-05-plugin-annotation-data-bridge*
*Completed: 2026-06-19*
