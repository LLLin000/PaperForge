---
phase: 50-repair-blind-spots
plan: 001
subsystem: worker
tags: [repair, divergence-detection, logging, dead-code, paperforge]
requires: []
provides:
  - "Condition 4 detects note_ocr_status=pending vs meta=done/failed as three-way divergence"
  - "All 5 bare except:pass blocks replaced with logger.warning() calls"
  - "--fix mode prints [WARNING] for unhandled divergence types"
  - "Dead load_domain_config import, call, and orphaned dict comprehension removed"
affects: [49-module-hardening]

tech-stack:
  added: []
  patterns:
    - "logger.warning() for error logging (established pattern from Phase 49)"
    - "Combined guard condition: not (note_ocr_status == 'pending' and meta_validated_status == 'pending')"

key-files:
  created: []
  modified:
    - "paperforge/worker/repair.py"
    - "tests/test_repair.py"

key-decisions:
  - "REPAIR-01: Replaced note_ocr_status != 'pending' guard with not (pending AND pending) — catches pending-vs-done/failed while preserving false negatives for consistent-pending states"
  - "REPAIR-02: Added else clause printing [WARNING] with zotero_key and div_reason for unhandled --fix types instead of silently skipping"
  - "REPAIR-03: Changed 4 plan-specified + 1 auto-detected bare except Exception: pass to logger.warning() with descriptive message including zotero_key and exception"

patterns-established:
  - "Exception swallowing replaced with logger.warning() — follows discussion.py pattern from Phase 49"

requirements-completed:
  - REPAIR-01
  - REPAIR-02
  - REPAIR-03
  - REPAIR-04

duration: 4min
completed: 2026-05-07
---

# Phase 50: Repair Blind Spots — Plan 001 Summary

**Four repair worker blind spots closed: condition 4 divergence detection, --fix mode coverage, silent exception logging, and dead code removal**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-07T20:15:09Z
- **Completed:** 2026-05-07T20:19:10Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- **REPAIR-01:** Condition 4 three-way divergence detection now catches `note_ocr_status == "pending"` vs `meta_ocr_status in ("done", "failed")` — the previous `note_ocr_status != "pending"` guard silently skipped this entire category
- **REPAIR-04:** Dead `load_domain_config` import (from `_domain`), orphaned `load_domain_config(paths)` call, and unused dict comprehension removed — zero dead code in `repair.py`
- **REPAIR-03:** All 5 bare `except Exception: pass` blocks replaced with `logger.warning()` calls including zotero_key and exception message — index load failures, index write failures, and meta write failures are now visible in logs
- **REPAIR-02:** `--fix` mode gained an `else` clause that prints `[WARNING] No --fix handler for <key>: <reason>` for any divergence type without an explicit fix handler — no silently skipped conditions

## Task Commits

Each task was committed atomically:

1. **Task 1: Dead code removal + Condition 4 fix (REPAIR-04, REPAIR-01)** — `8c75871` (fix)
2. **Task 2: Exception logging + Fix coverage (REPAIR-03, REPAIR-02)** — `989f994` (fix)

## Files Created/Modified

- `paperforge/worker/repair.py` — All 4 fixes applied (412 -> 414 lines, zero dead code, zero bare except:pass, condition 4 expanded, else clause added)
- `tests/test_repair.py` — 37 tests (up from 27), 10 new tests covering all 4 requirements

## Decisions Made

- **Condition 4 guard redesign:** Used `not (note_ocr_status == "pending" and meta_validated_status == "pending")` instead of a simple `note_ocr_status != "pending"` removal. This precisely catches the missing case (note lags behind meta) while keeping consistent-pending states benign.
- **Rule 2 deviation for line 315:** Auto-detected and fixed one additional bare `except Exception: pass` at the meta write in the first `--fix` branch (line 315) that was not listed in the plan's 4 blocks. Silent exception swallowing is a critical issue following the same pattern.
- **TDD flow:** Tests written before fixes for both tasks, confirming RED (fail before fix) and GREEN (pass after fix) transitions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed bare except:pass at line 315 (first --fix branch meta write)**
- **Found during:** Task 2 (Exception logging)
- **Issue:** Plan specified 4 bare except:pass blocks (lines 223, 306, 347, 355) but missed the identical pattern at line 315 (meta write in first --fix branch)
- **Fix:** Replaced `except Exception: pass` with `logger.warning("Failed to reset meta ocr_status for %s: %s", zotero_key, e)`
- **Files modified:** paperforge/worker/repair.py
- **Verification:** All 37 tests pass, grep confirms zero bare `except Exception: pass` patterns
- **Committed in:** 989f994 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary for completeness — REPAIR-03 scope covers all bare except:pass blocks, not just 4 of 5. No scope creep.

## Issues Encountered

None — both tasks executed cleanly with TDD flow.

## User Setup Required

None — all changes are to internal worker code. No external service configuration required.

## Next Phase Readiness

- All 4 REPAIR requirements satisfied and verified by 37 passing tests
- Phase 50 is the v1.11 milestone's final phase — milestone ready for closure
- All 27 v1.11 requirements now complete across phases 46-50

---

## Self-Check: PASSED

All claims verified:
- [x] `paperforge/worker/repair.py` exists (414 lines)
- [x] `tests/test_repair.py` exists (37 tests)
- [x] Commit `8c75871` found in git log (Task 1)
- [x] Commit `989f994` found in git log (Task 2)
- [x] Zero bare `except Exception: pass` patterns in repair.py (grep confirms)
- [x] Zero `load_domain_config` references in repair.py (grep confirms)
- [x] 37/37 tests pass

*Phase: 50-repair-blind-spots*
*Completed: 2026-05-07*
