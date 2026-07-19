---
phase: 05-workflow-hardening-and-optional-plugin-shell
plan: '02'
subsystem: testing
tags: [pytest, smoke-test, fixture, tmp_path, end-to-end]

# Dependency graph
requires: []
provides:
  - Fixture vault factory (fixture_vault) reusable across all test files
  - Fixture library records with frontmatter matching real records
  - Better BibTeX JSON fixture with 3 paper entries
  - Fixture with real temporary PDF for PDF-resolver tests
  - 13 end-to-end smoke tests covering full pipeline
affects:
  - REL-02 smoke test requirement

# Tech tracking
tech-stack:
  added: [pytest fixtures, pathlib.Path, tmp_path]
  patterns:
    - Fixture factory pattern for isolated test vault creation
    - tmp_path fixture isolation for all tests
    - Mocked network calls via unittest.mock.patch for OCR diagnostics

key-files:
  created:
    - tests/conftest.py - Shared pytest fixtures (fixture_vault, fixture_library_records, fixture_bbt_json, fixture_with_pdf)
    - tests/test_smoke.py - 13 end-to-end smoke tests

patterns-established:
  - "Fixture factory: Creates complete vault structure with paperforge.json in tmp_path"
  - "Test isolation: Every test gets a fresh tmp_path fixture vault"
  - "Mocked I/O: OCR diagnostics network calls patched to avoid live API calls"

requirements-completed: [REL-02]

# Metrics
duration: 3min
completed: 2026-04-23
---

# Phase 5 Plan 2: Smoke Test Fixture + Suite Summary

**Fixture-based smoke tests for full pipeline — doctor, selection-sync, index-refresh, OCR doctor, deep-reading queue, and CLI entry points**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-23T10:43:14Z
- **Completed:** 2026-04-23T10:46:40Z
- **Tasks:** 2 (both completed)
- **Files modified:** 2 created

## Accomplishments

- Created reusable `fixture_vault` factory that builds complete vault structure with paperforge.json in tmp_path
- Created 3 mock library records with realistic frontmatter (zotero_key, domain, title, year, ocr_status, analyze, do_ocr)
- Created Better BibTeX JSON export fixture matching library records (TESTKEY001/002/003)
- Created `fixture_with_pdf` that generates a real minimal PDF file on disk
- Implemented 13 end-to-end smoke tests covering setup validation, selection sync, index refresh, OCR doctor, deep-reading queue, and CLI entry points

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Fixture Vault Factory in conftest.py** - `1704395` (test)
2. **Task 2: Create Smoke Test Suite** - `405fc3f` (test)

**Plan metadata:** no additional commits (files already captured in task commits)

## Files Created/Modified

- `tests/conftest.py` - Shared pytest fixtures: fixture_vault, fixture_library_records, fixture_bbt_json, fixture_with_pdf, _write_minimal_pdf helper
- `tests/test_smoke.py` - 13 smoke tests across 6 categories: doctor setup validation, selection sync, index refresh, OCR doctor (L1-L3 mocked), deep-reading queue, CLI main entry

## Decisions Made

- Used `tmp_path` pytest fixture as the vault root — provides automatic isolated temp directory per test
- Used `unittest.mock.patch` to mock `requests.get`/`requests.post` in OCR doctor tests — avoids live API calls while testing the full diagnostic flow
- Created real minimal PDF using `b"%PDF-1.4\n..."` bytes for `fixture_with_pdf` — enables PDF-resolver tests that need actual file I/O

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- REL-02 smoke test requirement satisfied with 13 passing tests
- fixtures are reusable for future REL-01 test coverage expansion

---
*Phase: 05-workflow-hardening-and-optional-plugin-shell*
*Completed: 2026-04-23*
