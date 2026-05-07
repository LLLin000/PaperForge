---
phase: 25-surface-convergence-doctor-repair
plan: 01
subsystem: status, doctor
tags: canonical-index, lifecycle, health, maturity, doctor, brownfield

# Dependency graph
requires:
  - phase: 24-derived-lifecycle-health-maturity
    provides: lifecycle, health, maturity, next_step derived fields in canonical index entries
provides:
  - summarize_index() helper in asset_index.py for lifecycle/health/maturity aggregates
  - run_status() reads from canonical index instead of filesystem scanning
  - status --json outputs lifecycle_level_counts, health_aggregate, maturity_distribution
  - status text output shows index section with lifecycle and health counts
  - run_doctor() Index Health section with PDF/OCR/Note/Asset Health per-dimension counts
  - Brownfield migration detection (legacy schema, old Base columns, partial OCR)
affects: phase 25-02 (plugin dashboard), phase 25-03 (Base views, repair)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Index-backed status display as canonical data source with filesystem fallback
    - Doctor check anti-corruption layer (info status tag handling)
    - Aggregate helper pattern (summarize_index returns None for missing/legacy)

key-files:
  created:
    - tests/test_status.py: 6 tests for index-backed status and doctor Index Health
  modified:
    - paperforge/worker/asset_index.py: added summarize_index() function
    - paperforge/worker/status.py: refactored run_status() + added Index Health to run_doctor()

key-decisions:
  - "D-04 preserved: summarize_index() returns None when index unavailable, caller (status.py) handles filesystem fallback"
  - "Doctor Index Health section placed after Agent checks, before print section"
  - "Existing status --json fields preserved for backward compatibility; lifecycle/health/maturity fields default to None"
  - "status_tag mapping fixed to support 'info' status (pre-existing bug)"
  - "Task 1 and Tasks 2+3 committed separately as permitted by atomic commit per task"

patterns-established: []

requirements-completed:
  - SURF-01
  - SURF-02
  - MIG-01
  - MIG-03

# Metrics
duration: 5 min
completed: 2026-05-04
---

# Phase 25 Plan 01: Surface Convergence — status --json source migration + doctor Index Health

**status --json reads lifecycle/health/maturity from canonical index; doctor shows Index Health section with per-dimension health counts and brownfield detection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-04T11:21:31Z
- **Completed:** 2026-05-04T11:27:07Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `summarize_index()` helper added to `asset_index.py` — reads canonical index and returns lifecycle, health, and maturity aggregates; returns None when index is missing or in legacy format
- `run_status()` refactored to call `summarize_index()` and use index data when available, with filesystem fallback when index is unavailable
- JSON output now includes `lifecycle_level_counts`, `health_aggregate` (4 dimensions with healthy/unhealthy), and `maturity_distribution` (levels 1-6)
- Text output shows index section with lifecycle and health counts when index is present
- `run_doctor()` now includes "Index Health" section with PDF/OCR/Note/Asset Health per-dimension status and brownfield migration detection (legacy schema v<2, legacy Base columns, partial OCR assets)
- Fixed pre-existing bug in doctor status tag mapping: `info` status was missing from the tag dict, causing KeyError on schema_version info messages

## Task Commits

Each task was committed atomically:

1. **Task 1: Add summarize_index() helper to asset_index.py** — `a431632` (feat)
2. **Task 2+3: Refactor run_status() + add doctor Index Health** — `a8eece8` (feat)

**Plan metadata:** (pending)

## Files Created/Modified
- `paperforge/worker/asset_index.py` - Added `summarize_index()` function after `refresh_index_entry()`
- `paperforge/worker/status.py` - Refactored `run_status()` to read from canonical index; added Index Health section to `run_doctor()`; fixed status_tag mapping for `info` status
- `tests/test_asset_index.py` - Added 4 tests for `summarize_index()` (aggregates, missing, legacy, empty)
- `tests/test_status.py` - Created with 6 tests for index-backed status and doctor Index Health

## Decisions Made
- `summarize_index()` returns None when index is missing or in legacy bare-list format; the caller (status.py) handles fallback per D-04
- Doctor Index Health section placed after Agent checks and before the final print loop
- Existing JSON fields preserved for backward compatibility; lifecycle/health/maturity fields default to None when index is unavailable
- status_tag mapping uses `.get()` to support `info` status without crashing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed KeyError on 'info' status tag in doctor output**
- **Found during:** Task 3 (doctor Index Health implementation)
- **Issue:** `run_doctor()` already used `"info"` status in Config Migration section checks, but the status_tag dict `{"pass": "[PASS]", "fail": "[FAIL]", "warn": "[WARN]"}` didn't include `"info"`. Calling `add_check("Index Health", "info", ...)` would crash with KeyError. The same bug existed for the pre-existing Config Migration info message at schema_version < 2.
- **Fix:** Changed status_tag from direct dict key access to `.get(status, "[INFO]")` with `"info"` added to the dict.
- **Files modified:** `paperforge/worker/status.py`
- **Verification:** `pytest tests/test_status.py` passes, manual doctor run with missing index shows "Index Health -- No canonical index" as [INFO] tag
- **Committed in:** `a8eece8` (Task 2+3 commit)

**2. [Rule 3 - Blocking] Python scope conflict with lazy import of pipeline_paths inside run_doctor()**
- **Found during:** Task 3 implementation
- **Issue:** Inside run_doctor(), a lazy `from paperforge.worker._utils import pipeline_paths` inside the Index Health section created a local variable that shadowed the module-level import used at the top of the function. Python scoping rules made `pipeline_paths` at the top of the function appear unassigned, causing UnboundLocalError.
- **Fix:** Replaced with direct access to the existing `paths` variable already in scope (defined at the top of `run_doctor()`).
- **Files modified:** `paperforge/worker/status.py`
- **Verification:** All tests pass, manual doctor run works
- **Committed in:** `a8eece8` (Task 2+3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both were necessary for correct functionality. No scope creep.

## Issues Encountered
None

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 25 foundation complete: status --json and doctor now consume canonical index semantics
- Ready for Phase 25-02: Plugin dashboard direct JSON read + doctor/repair Quick Actions
- Ready for Phase 25-03: Base views lifecycle columns + repair source-first rebuild pattern
- Brownfield detection for legacy schema, old Base templates, and partial OCR already wired into doctor

---

## Self-Check: PASSED

All created files exist on disk. All commits found in git history.

---

*Phase: 25-surface-convergence-doctor-repair*
*Completed: 2026-05-04*
