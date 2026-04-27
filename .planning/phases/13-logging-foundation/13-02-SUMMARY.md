---
phase: 13-logging-foundation
plan: 02
subsystem: logging
tags: [logging, python, print-migration, refactoring]

requires:
  - phase: 13-logging-foundation
    plan: 01
    provides: logging_config.py with configure_logging(), global --verbose flag in cli.py
provides:
  - Module-level logger instances in all 12 worker and command modules
  - All diagnostic print() calls migrated to logging module
  - update.py _log() function eliminated in favor of logger.*()
affects:
  - Phase 14: Shared Utils Extraction (loggers already in place for new _utils.py)
  - Phase 15: OCR Worker Retry/Backoff (logging pattern established)
  - Phase 16: Progress Bars (stdout/stderr boundary already enforced)

tech-stack:
  added: []
  patterns:
    - "Each module has `import logging; logger = logging.getLogger(__name__)` at module level"
    - "Diagnostic output uses printf-style %%s/%%d formatting for lazy evaluation"
    - "stdout reserved for user-facing output; stderr via logging for diagnostics (OBS-02)"

key-files:
  created: []
  modified:
    - paperforge/worker/repair.py
    - paperforge/worker/deep_reading.py
    - paperforge/worker/ocr.py
    - paperforge/worker/sync.py
    - paperforge/worker/status.py
    - paperforge/worker/base_views.py
    - paperforge/worker/update.py
    - paperforge/commands/ocr.py
    - paperforge/commands/repair.py
    - paperforge/commands/deep.py
    - paperforge/commands/sync.py
    - paperforge/commands/status.py

key-decisions:
  - "printf-style format strings (%%s, %%d) used instead of f-strings for all logger calls — enables lazy evaluation"
  - "stdout print() calls at run_repair() exit points preserved as user-facing summary (lines 530-541)"
  - "commands/ocr.py _diagnose() function's print() calls preserved as user-facing diagnostic report"
  - "update.py input() prompt converted from colored to plain text since _color() function removed"
  - "paperforge/update.py (standalone) does not exist on disk — only paperforge/worker/update.py exists"

patterns-established:
  - "Logger pattern: import logging at top of module, logger = logging.getLogger(__name__) after last import"
  - "Diagnostic migration: all `print(f'[tag] ...')` calls replaced with logger.info/warning/error(...)"
  - "User-facing stdout contract: summary print() calls at function exit points remain as print()"

requirements-completed: [OBS-01, OBS-02]

metrics:
  duration: 12min
  completed: 2026-04-27
---

# Phase 13: Logging Foundation — Plan 02 Summary

**Module-level loggers added to 12 worker/command modules; 50 diagnostic print() calls migrated to logging in repair.py, commands/ocr.py, and worker/update.py**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-27T15:00:00+08:00
- **Completed:** 2026-04-27T15:12:22+08:00
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- Added `import logging; logger = logging.getLogger(__name__)` to all 7 worker modules and all 5 command modules
- Migrated 10 `[repair]`-tagged `print()` calls in `worker/repair.py` to `logger.*()` with printf-style formatting
- Migrated 4 `[INFO]`/`[WARN]` `print()` calls in `commands/ocr.py` to `logger.*()`
- Removed `_log()` and `_color()` functions from `worker/update.py`; migrated all 36 `_log()` call sites to `logger.*()`
- All user-facing stdout `print()` calls preserved intact

## Task Commits

Each task was committed atomically:

1. **Task 1: Add module-level logger to all 12 worker and command modules** - `e0dbfec` (feat)
2. **Task 2: Migrate diagnostic print() calls to logger.*() in repair.py, commands/ocr.py, and update.py** - `492c4c2` (feat)

## Files Created/Modified
- `paperforge/worker/repair.py` - Added module-level logger; migrated 10 diagnostic prints to logger.*(); 4 user-facing stdout prints preserved
- `paperforge/worker/deep_reading.py` - Added module-level logger
- `paperforge/worker/ocr.py` - Added module-level logger
- `paperforge/worker/sync.py` - Added module-level logger
- `paperforge/worker/status.py` - Added module-level logger
- `paperforge/worker/base_views.py` - Added module-level logger
- `paperforge/worker/update.py` - Added module-level logger; removed _log() and _color() functions; migrated 36 _log() call sites to logger.*()
- `paperforge/commands/ocr.py` - Added module-level logger; migrated 4 diagnostic prints to logger.*()
- `paperforge/commands/repair.py` - Added module-level logger
- `paperforge/commands/deep.py` - Added module-level logger
- `paperforge/commands/sync.py` - Added module-level logger
- `paperforge/commands/status.py` - Added module-level logger

## Decisions Made
- Used printf-style `%s`/`%d` formatting for all logger calls instead of f-strings — enables lazy evaluation when logging level suppresses the message
- Kept `input()` prompt in `worker/update.py` as plaintext (removed `_color()` wrapper) since CLI coloring is a user-experience concern handled by the terminal, not the logging system
- Preserved `commands/ocr.py _diagnose()` function's `print()` calls — these are user-facing diagnostic report on stdout, not diagnostic trace output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] paperforge/update.py does not exist on disk**
- **Found during:** Task 1 (Adding module-level loggers)
- **Issue:** The plan lists `paperforge/update.py` as one of the 13 target files, but this file does not exist. The actual file containing the `_log()` function referenced in Task 2 is `paperforge/worker/update.py`, which was already in the file list.
- **Fix:** Skipped the non-existent file. The remaining 12 files cover all 7 worker modules and 5 command modules as intended.
- **Files modified:** None (skipped)
- **Verification:** 12 of 12 files processed successfully; all import tests pass
- **Committed in:** e0dbfec (Task 1 commit)

**2. [Rule 2 - Missing Critical] input() prompt in update.py still referenced removed _color() function**
- **Found during:** Task 2 (Migrating update.py _log() calls)
- **Issue:** Line 417 contained `input(_color("确认更新? [y/N]: ", "y"))` which references the now-removed `_color()` function. This would cause a NameError at runtime.
- **Fix:** Replaced with plain `input("确认更新? [y/N]: ")`. The prompt text goes to stdout naturally via `input()` and the color formatting was cosmetic only.
- **Files modified:** paperforge/worker/update.py
- **Verification:** No remaining `_color(` references in update.py
- **Committed in:** 492c4c2 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- None — execution was straightforward. The plan accurately identified all target files and migration mappings.

## Next Phase Readiness
- All 12 worker and command modules now have module-level logger instances
- All diagnostic print() calls migrated to logging module
- Stdout/stderr boundary (OBS-02) is established: stdout = user-facing, stderr = diagnostics
- Ready for Phase 13 Plan 03: PAUSED for Agent prioritization

---

*Phase: 13-logging-foundation*
*Completed: 2026-04-27*
