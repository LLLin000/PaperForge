# Plan 02-03 Execution Summary

## Status: COMPLETED

## Files Created
- `paperforge/ocr_diagnostics.py` — `ocr_doctor()` with tiered L1-L4 checks
- `tests/test_ocr_doctor.py` — 7 tests for L1-L4 diagnostics

## Files Modified
- `paperforge/cli.py` — Added `ocr` sub-subcommands (`run`, `doctor`), `_cmd_ocr_doctor()`, dispatch logic
- `tests/test_cli_worker_dispatch.py` — Added `test_ocr_doctor_dispatch`
- `command/lp-ocr.md` — Added `paperforge ocr doctor` documentation with diagnostic level table

## Diagnostic Levels
| Level | Check | Failure Meaning |
|-------|-------|-----------------|
| L1 | API token presence | `PADDLEOCR_API_TOKEN` missing |
| L2 | URL reachability | Cannot connect to service |
| L3 | API schema validation | Response format unexpected |
| L4 | Live PDF round-trip | Full submission fails (requires `--live`) |

## Test Results
- `tests/test_ocr_doctor.py`: 7 passed
- `tests/test_cli_worker_dispatch.py::test_ocr_doctor_dispatch`: passed

## Notes
- L3 submits a minimal payload and immediately cancels the test job to avoid wasting resources
- L4 polls for result up to 10 attempts with 5s delay
- Exit code 0 = pass, 1 = fail (any level)
