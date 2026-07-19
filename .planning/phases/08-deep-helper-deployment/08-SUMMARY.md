---
phase: 08-deep-helper-deployment
plan: 08
subsystem: testing
tags: [pytest, fixtures, rollback, regression-testing, smoke-tests]

requires:
  - phase: 07-sandbox-onboarding
    provides: test infrastructure, sandbox vault, paperforge CLI
provides:
  - Deterministic OCR-complete fixtures (TSTONE001)
  - 14 smoke tests covering importability, prepare, queue, regressions
  - 3 rollback tests for prepare_deep_reading failure paths
  - Enhanced doctor with importability and per-domain export checks
  - Fixed zotero_key quote stripping in scan_deep_reading_queue
affects:
  - 09-verification
  - 10-release

tech-stack:
  added: [pytest fixtures, importlib.util, unittest.mock.patch]
  patterns: [rollback-on-failure, deterministic fixtures, regression test suite]

key-files:
  created:
    - tests/conftest.py - Test vault fixture with TSTONE001 setup
    - tests/test_smoke.py - 14 smoke and regression tests
    - tests/test_prepare_rollback.py - 3 rollback behavior tests
    - tests/sandbox/exports/骨科.json - Synthetic BBT export fixture
    - tests/sandbox/generate_ocr_fixture.py - Fixture generation script
    - tests/sandbox/ocr-complete/TSTONE001/fulltext.md - Synthetic OCR fulltext
    - tests/sandbox/ocr-complete/TSTONE001/figure-map.json - Generated figure map
    - tests/sandbox/ocr-complete/TSTONE001/chart-type-map.json - Generated chart types
    - tests/sandbox/ocr-complete/TSTONE001/meta.json - OCR metadata fixture
  modified:
    - pipeline/worker/scripts/literature_pipeline.py - Doctor importability, env var, export checks
    - skills/literature-qa/scripts/ld_deep.py - Rollback, zotero_key quote stripping
    - .gitignore - Removed blanket tests/ exclusion

key-decisions:
  - "Use importlib.util.spec_from_file_location with Python 3.14 workaround (pre-add to sys.modules) for dataclass compatibility"
  - "Generate deterministic fixtures once and commit, never regenerate in CI"
  - "Rollback deletes partial files and restores original note text, not a full filesystem snapshot"

patterns-established:
  - "Rollback pattern: track written files, save original state, clean up on exception"
  - "Fixture pattern: synthetic data + generation script for reproducibility"
  - "Regression test pattern: one test per reported issue, named with regression ID"

requirements-completed: [DEEP-04, DEEP-06, REG-01, REG-02, REG-03, D-13, D-14, D-15]

duration: 45min
completed: 2026-04-24
---

# Phase 8: Deep Helper Deployment And Sandbox Regression Gate Summary

**Deterministic OCR fixtures, 17 regression/smoke tests, rollback on prepare failure, and doctor importability checks**

## Performance

- **Duration:** 45 min
- **Started:** 2026-04-24T12:50:00Z
- **Completed:** 2026-04-24T13:35:00Z
- **Tasks:** 5
- **Files modified:** 11

## Accomplishments
- Enhanced doctor command checks actual importability (not just directory existence)
- Doctor validates per-domain JSON exports and checks canonical PADDLEOCR_API_TOKEN env var
- Created deterministic OCR-complete fixture (TSTONE001) with synthetic fulltext, figure-map, chart-type-map
- 14 smoke tests covering setup wizard, doctor, ld_deep import, prepare, queue, docs, metadata, PDF paths
- 3 rollback tests verifying cleanup on figure-map failure and scaffold failure
- Added rollback-on-failure to prepare_deep_reading with original note restoration
- Fixed zotero_key quote stripping bug in scan_deep_reading_queue

## Task Commits

1. **Task 1: Fix ld_deep.py Importability** - `fa51cf7` (fix)
2. **Task 2: Create OCR-Complete Fixture** - `afa19eb` (feat)
3. **Task 3 & 4: Extend Smoke Tests + Doc Verification** - `802d34b` (test)
4. **Task 5: Add Rollback to prepare_deep_reading** - `766ed1e` (feat)

**Plan metadata:** `pending` (docs commit after summary)

## Files Created/Modified
- `pipeline/worker/scripts/literature_pipeline.py` - Doctor importability, env var, per-domain export checks
- `skills/literature-qa/scripts/ld_deep.py` - Rollback logic, zotero_key quote stripping
- `tests/conftest.py` - test_vault fixture with full vault setup
- `tests/test_smoke.py` - 14 smoke/regression tests
- `tests/test_prepare_rollback.py` - 3 rollback tests
- `tests/sandbox/exports/骨科.json` - BBT export fixture
- `tests/sandbox/generate_ocr_fixture.py` - Fixture generation script
- `tests/sandbox/ocr-complete/TSTONE001/*` - OCR fixture files (fulltext, figure-map, chart-type-map, meta)
- `.gitignore` - Removed blanket tests/ exclusion

## Decisions Made
- Used `importlib.util.spec_from_file_location` with pre-registration in `sys.modules` as Python 3.14 dataclass workaround
- Generated fixtures once and committed; generation script available for reproducibility but not run in CI
- Rollback tracks only files written during the current prepare run, not full filesystem snapshot

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed zotero_key quote stripping in scan_deep_reading_queue**
- **Found during:** Task 3 (test_queue_shows_ready_paper)
- **Issue:** zotero_key regex captured quotes (`"TSTONE001"`), causing queue filter mismatch and wrong OCR path lookup
- **Fix:** Added `.strip('"').strip("'")` to zotero_key extraction
- **Files modified:** skills/literature-qa/scripts/ld_deep.py
- **Verification:** test_queue_shows_ready_paper passes, queue returns correct ocr_status
- **Committed in:** 766ed1e (Task 5 commit)

**2. [Rule 2 - Missing Critical] Added Python 3.14 dataclass import workaround**
- **Found during:** Task 3 (test_ld_deep_import_from_deployed)
- **Issue:** Python 3.14 fails to import ld_deep.py via importlib.util because dataclasses accesses `sys.modules[cls.__module__].__dict__` before module is registered
- **Fix:** Pre-register module in sys.modules before exec_module; skip test gracefully if bug persists
- **Files modified:** tests/test_smoke.py, tests/test_prepare_rollback.py
- **Verification:** All import-based tests pass on Python 3.14
- **Committed in:** 802d34b (Task 3 commit)

**3. [Rule 3 - Blocking] Fixed test imports (skills is not a package)**
- **Found during:** Task 3 (test execution)
- **Issue:** `from skills.literature_qa.scripts.ld_deep import ...` fails because `skills/` has no `__init__.py`
- **Fix:** Created `_import_ld_deep()` helper using `importlib.util.spec_from_file_location`
- **Files modified:** tests/test_smoke.py, tests/test_prepare_rollback.py
- **Verification:** All ld_deep imports work
- **Committed in:** 802d34b (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 1 missing critical, 1 blocking)
**Impact on plan:** All auto-fixes necessary for correctness and testability. No scope creep.

## Issues Encountered
- Python 3.14.0 pre-release dataclass regression with `from __future__ import annotations` required workaround in test imports
- Test vault fixture cleanup between tests caused transient state issues; resolved by using fresh vault per test

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 17 tests pass
- Sandbox fixtures committed and deterministic
- Rollback behavior tested for both figure-map and scaffold failures
- Doctor validates importability, env names, and per-domain exports
- Ready for Phase 9 (verification) or Phase 10 (release)

---
*Phase: 08-deep-helper-deployment*
*Completed: 2026-04-24*
