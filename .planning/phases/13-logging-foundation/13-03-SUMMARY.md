---
phase: 13-logging-foundation
plan: 03
subsystem: cli
tags: [logging, verbose, cli, debug]
requires:
  - phase: 13-01
    provides: logging_config.py and --verbose global flag on root parser
  - phase: 13-02
    provides: configure_logging() invoked in main() before dispatch
provides:
  - Worker function signatures accept verbose: bool = False parameter
  - Command modules (sync, ocr, status) wire args.verbose to worker calls
affects:
  - Phase 14: worker utils extraction will inherit verbose-ready signatures
tech-stack:
  added: []
  patterns:
    - verbose=getattr(args, "verbose", False) for safe argument extraction
    - Worker contract-first: accept verbose param even if not yet used internally
key-files:
  created: []
  modified:
    - paperforge/worker/sync.py
    - paperforge/worker/ocr.py
    - paperforge/worker/status.py
    - paperforge/commands/sync.py
    - paperforge/commands/ocr.py
    - paperforge/commands/status.py
key-decisions:
  - "verbose defaults to False for backward compatibility with existing call sites"
  - "getattr(args, 'verbose', False) pattern used for safe extraction (handles missing attribute in test/offline contexts)"
  - "No internal behavior changes inside workers yet — verbose param is contract-first for Phase 14+ activation"
patterns-established:
  - "verbose=getattr(args, 'verbose', False) — standard wiring pattern for all command modules"
  - "def foo(vault, verbose=False) — standard signature pattern for all worker functions"
requirements-completed:
  - OBS-03
duration: 8min
completed: 2026-04-27
---

# Phase 13: Logging Foundation — Plan 03 Summary

## All 4 primary CLI commands (sync, ocr, status, deep-reading) wire the global `--verbose`/`-v` flag from root parser through command modules to worker function signatures

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-27T15:15:20Z
- **Completed:** 2026-04-27T15:23:XXZ
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `verbose: bool = False` to 5 worker function signatures (run_selection_sync, run_index_refresh, run_ocr, run_doctor, run_status) — backward compatible due to default False
- Wired `verbose=getattr(args, "verbose", False)` through sync, ocr, and status command modules to their respective worker functions
- deep-reading and repair commands already had this wiring (confirmed unchanged)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add verbose parameter to worker function signatures** - `00692ef` (feat)
2. **Task 2: Wire verbose through command modules to worker functions** - `f70ea85` (feat)

**Plan metadata:** (pending — final commit)

## Files Created/Modified

- `paperforge/worker/sync.py` — `run_selection_sync` and `run_index_refresh` now accept `verbose: bool = False`
- `paperforge/worker/ocr.py` — `run_ocr` now accepts `verbose: bool = False`
- `paperforge/worker/status.py` — `run_doctor` and `run_status` now accept `verbose: bool = False`
- `paperforge/commands/sync.py` — passes `verbose=getattr(args, "verbose", False)` to both worker calls
- `paperforge/commands/ocr.py` — passes `verbose=getattr(args, "verbose", False)` to `run_ocr()`
- `paperforge/commands/status.py` — passes `verbose=getattr(args, "verbose", False)` to `run_status()`

## Decisions Made

- **Backward compatibility first:** Default `False` ensures all existing call sites (CLI dispatch, tests, direct imports) continue to work without modification.
- **Safe extraction pattern:** `getattr(args, "verbose", False)` guards against missing `verbose` attribute when command modules are invoked outside the CLI (e.g., tests or offline contexts).
- **Contract-first approach:** Worker functions accept `verbose` even though no internal branching on it yet. The parameter serves as a contract for Phases 14+ when logging is activated inside worker functions.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required. This is a purely internal wiring change.

## Next Phase Readiness

- All primary CLI commands propagate the global `--verbose` flag to worker functions
- deep-reading and repair were already wired (confirmed unchanged)
- Ready for Phase 14 (shared utils extraction) where `verbose` will drive actual DEBUG-level logging inside workers

## Self-Check: PASSED

- [x] All 5 worker functions accept `verbose: bool = False` with default False
- [x] sync.py has 2 verbose wirings (run_selection_sync + run_index_refresh)
- [x] ocr.py has 1 verbose wiring (run_ocr)
- [x] status.py has 1 verbose wiring (run_status)
- [x] deep.py has 1 verbose wiring (pre-existing, confirmed unchanged)
- [x] repair.py has 1 verbose wiring (pre-existing, confirmed unchanged)

---

*Phase: 13-logging-foundation*
*Completed: 2026-04-27*
