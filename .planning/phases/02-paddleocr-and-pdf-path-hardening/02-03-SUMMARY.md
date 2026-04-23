---
phase: 02-paddleocr-and-pdf-path-hardening
plan: 03
subsystem: ocr
tags: [paddleocr, diagnostics, cli, pytest, requests]

requires:
  - phase: 01-config-and-command-foundation
    provides: CLI parser structure and vault config loading

provides:
  - ocr_doctor() function with tiered L1-L4 diagnostics
  - `paperforge ocr doctor` CLI subcommand
  - `paperforge ocr doctor --live` for L4 live PDF round-trip
  - Mocked unit tests for all diagnostic levels
  - User-facing documentation for OCR doctor

affects:
  - 02-paddleocr-and-pdf-path-hardening (future PDF preflight plans)

tech-stack:
  added: []
  patterns:
    - "Tiered diagnostic levels with early-exit on failure"
    - "Mocked HTTP testing with unittest.mock.patch"
    - "Sub-subcommand CLI pattern with argparse"

key-files:
  created:
    - paperforge_lite/ocr_diagnostics.py
    - tests/test_ocr_doctor.py
    - tests/fixtures/blank.pdf
  modified:
    - paperforge_lite/cli.py
    - tests/test_cli_worker_dispatch.py
    - command/lp-ocr.md

key-decisions:
  - "Used required=False on ocr subparser to preserve backward compatibility of `paperforge ocr` alias"
  - "L4 live test polls up to 10 times with 5s sleep, cancelling test job immediately after L3"

patterns-established:
  - "Diagnostic functions return structured dict with level/passed/error/fix keys"
  - "CLI commands import diagnostics lazily to avoid import-time side effects"

requirements-completed:
  - OCR-01

duration: 18min
completed: 2026-04-23
---

# Phase 02 Plan 03: OCR Doctor Command Summary

**Tiered `paperforge ocr doctor` diagnostic command with L1-L4 checks, mocked test coverage, and user documentation**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-23T12:50:00Z
- **Completed:** 2026-04-23T13:08:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Implemented `ocr_doctor(config, live=False)` with L1 token, L2 URL, L3 schema, and L4 live PDF checks
- Added `paperforge ocr doctor` and `paperforge ocr doctor --live` CLI subcommands
- Created 7 mocked unit tests covering all diagnostic levels and edge cases
- Updated user documentation with diagnostic levels table and exit codes

## Task Commits

1. **Task 1: Implement ocr_doctor() with L1-L4 diagnostics** - `3bd1c5e` (feat)
2. **Task 2: Add CLI dispatch, tests, and documentation** - `2a3295e` (feat)

## Files Created/Modified
- `paperforge_lite/ocr_diagnostics.py` - Core diagnostic function with tiered L1-L4 checks
- `tests/test_ocr_doctor.py` - 7 mocked unit tests for L1-L4 scenarios
- `tests/fixtures/blank.pdf` - Minimal blank PDF fixture for L4 live test
- `paperforge_lite/cli.py` - Sub-subcommand parser for `ocr run` and `ocr doctor`, dispatch logic
- `tests/test_cli_worker_dispatch.py` - Added doctor dispatch test
- `command/lp-ocr.md` - User documentation for `paperforge ocr doctor`

## Decisions Made
- Preserved backward compatibility of `paperforge ocr` alias by using `required=False` on the ocr subparser and defaulting missing `ocr_action` to `"run"`
- L3 test job is immediately cancelled via DELETE after obtaining jobId to avoid wasting OCR provider resources

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed L4 test mock setup for multiple `requests.get` calls**
- **Found during:** Task 1 (test_l4_live_success / test_l4_live_failure)
- **Issue:** Patching `requests.get` with a single `return_value` caused L4 polling to receive the L2 mock response instead of the poll mock, resulting in timeout failures
- **Fix:** Changed `patch` to use `side_effect=[get_resp] + [poll_resp] * 10` so the first GET returns the L2 response and subsequent GETs return the poll response
- **Files modified:** `tests/test_ocr_doctor.py`
- **Verification:** All 7 tests pass
- **Committed in:** `3bd1c5e` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor test-level fix. No scope creep.

## Issues Encountered
- None beyond the mocked L4 test fix above

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- OCR doctor command is fully functional and tested
- Ready for Plan 02-04 (Selection Sync PDF Reporting) or other OCR hardening work
- No blockers

---
*Phase: 02-paddleocr-and-pdf-path-hardening*
*Completed: 2026-04-23*
