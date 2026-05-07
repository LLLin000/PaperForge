---
phase: 23-canonical-asset-index-safe-rebuilds
plan: 03
subsystem: asset-index
tags: incremental, refresh, ocr, deep-reading, repair, integration-tests

# Dependency graph
requires:
  - phase: 23-02
    provides: refresh_index_entry() in asset_index.py
provides:
  - Post-OCR incremental index refresh by completed key (ocr.py)
  - Post-deep-reading incremental index refresh for all records (deep_reading.py)
  - Post-repair incremental index refresh for path and divergence fixes (repair.py)
  - run_index_refresh() docstring explaining full-rebuild convention (sync.py)
  - Integration tests covering incremental refresh behavior, worker call sites, and workspace paths
affects:
  - Phase 24 (Derived Lifecycle, Health & Maturity)
  - Phase 25 (Surface Convergence, Doctor & Repair)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Incremental refresh by zotero_key for single-paper changes
    - Full rebuild as safe default for sync (multi-paper changes)
    - ImportError fallback for pre-migration compatibility
    - Fail-soft logging for refresh failures

key-files:
  created:
    - tests/test_asset_index_integration.py
  modified:
    - paperforge/worker/ocr.py
    - paperforge/worker/deep_reading.py
    - paperforge/worker/repair.py
    - paperforge/worker/sync.py

key-decisions:
  - "OCR captures done keys before queue filter to pass to incremental refresh"
  - "Deep-reading refreshes ALL records (not just synced ones) because formal note content changes affect the index even when status didn't change"
  - "Repair triggers refresh for both path fixes (BBT export re-resolution + PDF resolver) and divergence fixes (three-way state repair)"
  - "run_index_refresh keeps full-rebuild default; incremental is opt-in from single-paper workers"

patterns-established:
  - "Worker modules that modify individual paper state import refresh_index_entry and call it after each relevant modification"
  - "Integration tests for asset_index use _minimal_vault + BBT export fixture setup, matching test_asset_index.py patterns"

requirements-completed:
  - ASSET-03
  - ASSET-04
  - MIG-02

# Metrics
duration: 8 min
completed: 2026-05-04
---

# Phase 23 Plan 03: Incremental Refresh Wiring & Integration Tests

**Wire incremental index refresh into OCR, deep-reading, and repair workers; document sync.py default convention; add integration tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-04T00:48:00Z
- **Completed:** 2026-05-04T00:56:00Z
- **Tasks:** 4
- **Files modified:** 5

## Accomplishments

- OCR post-processing calls `refresh_index_entry(vault, key)` per completed key instead of full rebuild, with ImportError fallback
- Deep-reading status sync triggers incremental index refresh for all records after the queue report is written
- Repair triggers incremental refresh for per-paper path fixes (BBT export + PDF resolver) and three-way state divergence fixes
- `run_index_refresh()` in sync.py has docstring explaining the full-rebuild default convention vs incremental refresh by key
- 9 integration tests covering: incremental refresh preserves unrelated entries, appends new keys, legacy format fallback, unknown key handling, structural call-site verification for all 3 workers, and workspace path field consistency

## Task Commits

Each task was committed atomically:

1. **Task 1: OCR incremental refresh** - `3557476` (feat)
2. **Task 2: Deep-reading incremental refresh** - `3ec6753` (feat)
3. **Task 3: Repair incremental refresh + sync.py docstring** - `a190c94` (feat)
4. **Task 4: Integration tests** - `c8561fd` (feat)

## Files Created/Modified

- `paperforge/worker/ocr.py` - Post-OCR block: capture done keys, call `refresh_index_entry` per key, fallback to full rebuild on ImportError
- `paperforge/worker/deep_reading.py` - After status sync report, call `refresh_index_entry` for every record with fail-soft logging
- `paperforge/worker/repair.py` - Three call sites: BBT export path fix, PDF resolver path fix, divergence state fix
- `paperforge/worker/sync.py` - Docstring on `run_index_refresh` explaining convention
- `tests/test_asset_index_integration.py` - 9 tests across 3 test classes

## Decisions Made

- **OCR key capture timing**: Done keys must be captured before the queue filter removes them (line 1809). This avoids double-scanning the queue.
- **Deep-reading refreshes ALL records**: Even when `synced == 0`, formal note content changes (e.g., `deep_reading_md_path` field) affect the index, so every record is refreshed.
- **Repair has 3 call sites**: Path fixes can come from BBT export re-resolution or PDF resolver fallback; divergence fixes happen via `run_repair()`. All three need refresh.
- **Fail-soft pattern**: All refresh calls are wrapped in try/except that logs a warning and continues. The index being stale is preferable to a worker crash.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed indentation error in repair.py after edit**
- **Found during:** Task 4 (integration tests running)
- **Issue:** The `if resolved:` block in `repair_pdf_paths()` lost proper indentation during the edit, causing a SyntaxError
- **Fix:** Restored correct 4-space indentation levels for `if resolved:` and `else:` blocks
- **Files modified:** paperforge/worker/repair.py
- **Verification:** pytest passes 9/9 integration tests, 14/14 existing tests
- **Committed in:** c8561fd (Task 4 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor — necessary fix, no scope creep.

## Issues Encountered

- Indentation error in repair.py after initial edit (fixed in Task 4 commit per Rule 1)
- OCR queue uses `zotero_key` field but plan example referenced `key` — used correct field name in implementation

## User Setup Required

None - all changes are internal to Python worker code and tests.

## Next Phase Readiness

- All three worker operations (OCR, deep-reading, repair) now use incremental index refresh
- Integration tests verify behavior and provide safety net for future changes
- Phase 23 plan sequence complete (3/3 plans) — ready for Phase 24 (Derived Lifecycle, Health & Maturity)
- `run_index_refresh` convention is documented for future developers

## Self-Check: PASSED

- [x] Created file: `tests/test_asset_index_integration.py` — FOUND
- [x] Commits all present: `3557476`, `3ec6753`, `a190c94`, `c8561fd` — FOUND
- [x] Module importable: `from paperforge.worker.asset_index import refresh_index_entry` — OK
- [x] Integration tests pass: 9/9 passed
- [x] Existing tests pass: 14/14 passed

---

*Phase: 23-canonical-asset-index-safe-rebuilds*
*Completed: 2026-05-04*
