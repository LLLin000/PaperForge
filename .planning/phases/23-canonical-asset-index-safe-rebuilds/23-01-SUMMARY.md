---
phase: 23-canonical-asset-index-safe-rebuilds
plan: 01
subsystem: worker
tags: filelock, atomic-write, asset-index, canonical-index, sync-refactor

# Dependency graph
requires:
  - phase: 22-configuration-truth-compatibility
    provides: paperforge_paths resolver, schema_version handling
provides:
  - asset_index.py module with build_index, get_index_path, atomic_write_index
  - Versioned envelope format for formal-library.json (schema_version, generated_at, paper_count)
  - Atomic writes via tempfile.NamedTemporaryFile + os.replace
  - Cross-process locking via filelock.FileLock (10s timeout)
  - Delegation: run_index_refresh calls asset_index.build_index
  - Tests (14) covering envelope, atomic write, locking, and empty-exports edge case
affects:
  - 23-02 canonical asset index incremental refresh
  - 23-03 canonical asset index workspace paths

# Tech tracking
tech-stack:
  added:
    - filelock>=3.13.0 (cross-process file locking)
  patterns:
    - Index writes use tempfile + os.replace for atomicity
    - Index writes use filelock for cross-process safety
    - Lazy imports inside build_index to avoid circular deps

key-files:
  created:
    - paperforge/worker/asset_index.py (index module)
    - tests/test_asset_index.py (14 tests)
  modified:
    - paperforge/worker/sync.py (run_index_refresh delegates to build_index)
    - pyproject.toml (filelock dependency — committed in prior session)

key-decisions:
  - "Index envelope uses CURRENT_SCHEMA_VERSION = '2' matching config.py schema_version"
  - "Lazy imports inside build_index avoid circular import between sync.py and asset_index.py"
  - "Orphaned-record cleanup stays in sync.py; only the core build loop moves to asset_index"
  - "atomic_write_index uses path.with_suffix('.json.lock') as lock file, creating lock alongside index"

patterns-established:
  - "New modules that import from sync.py use lazy imports to avoid circular deps"
  - "Atomic writes: tempfile in same directory + os.replace + filelock"
  - "Index envelope format: {schema_version, generated_at, paper_count, items}"

requirements-completed:
  - ASSET-01
  - ASSET-02
  - ASSET-04
  - MIG-02

# Metrics
duration: 7 min
completed: 2026-05-04
---

# Phase 23 Plan 01: Canonical Asset Index & Safe Rebuilds Summary

**Extracted index generation from sync.py into asset_index.py with versioned envelope format, atomic writes (tempfile + os.replace + filelock), and 14 passing tests**

## Performance

- **Duration:** 7 min (Tasks 2-3 in current session; Task 1 committed in prior session)
- **Started:** 2026-05-04T00:29:08+08:00 (Task 1 from prior session)
- **Completed:** 2026-05-04T00:36:44Z
- **Tasks:** 3 (1 prior, 2 current)
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- Created `paperforge/worker/asset_index.py` — the single canonical home for asset index generation
  - `get_index_path(vault)` — resolves the index file location
  - `build_envelope(items)` — wraps items in versioned envelope (schema_version="2", generated_at, paper_count)
  - `atomic_write_index(path, data)` — writes atomically via tempfile + os.replace + filelock (10s timeout)
  - `build_index(vault, verbose)` — full rebuild extracted from sync.py's run_index_refresh loop
- Modified `sync.py` `run_index_refresh()` to delegate to `asset_index.build_index()` — orphaned-record cleanup stays in sync.py
- Created `tests/test_asset_index.py` with 14 tests covering envelope format, atomic writes, lock timeout, empty-exports edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Add filelock dependency** — `a2c6c8b` (chore) — *committed in prior session*
2. **Task 2: Create asset_index.py module** — `87437cf` (feat)
3. **Task 3: Write tests for asset_index.py** — `ccd7903` (test)

**Plan metadata:** *(committed below)*

## Files Created/Modified

- `paperforge/worker/asset_index.py` (269 lines) — Canonical index module with envelope, atomic writes, locking, and build_index
- `paperforge/worker/sync.py` (modified) — `run_index_refresh()` delegates to `asset_index.build_index()`
- `tests/test_asset_index.py` (261 lines) — 14 tests for core functionality
- `pyproject.toml` — `filelock>=3.13.0` added (Task 1, committed in prior session)

## Decisions Made

- **Lazy imports in build_index:** Functions imported from `sync.py` (collection_fields, frontmatter_note, etc.) are imported inside `build_index()` via lazy imports to avoid circular dependency — `sync.py` imports `asset_index` at module level.
- **Orphaned cleanup stays in sync.py:** The orphaned-record cleanup logic (lines 1689-1733 of the modified file) remains in `run_index_refresh()` because it's tightly coupled to the `exports` dict and domain resolution that happens before the build_index call.
- **Lock file naming:** `atomic_write_index` uses `path.with_suffix('.json.lock')` as the lock file path, creating it as a sibling to the target index file.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `datetime.utcnow()` in `build_envelope()` triggers a Python 3.14 deprecation warning (prefer `datetime.now(datetime.UTC)`). This is cosmetic — functionality is correct. Deferred to a future cleanup pass as it's not part of the current task scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for Plan 23-02 (incremental refresh with key-based update)
- `asset_index.py` now exists as a stable module to extend with `refresh_index_entry()`
- All 14 tests pass, verifying envelope format, atomic writes, and lock behavior

---

*Phase: 23-canonical-asset-index-safe-rebuilds*
*Completed: 2026-05-04*

## Self-Check: PASSED

- [x] `paperforge/worker/asset_index.py` exists
- [x] `tests/test_asset_index.py` exists
- [x] Commit `a2c6c8b` — Task 1: filelock dependency
- [x] Commit `87437cf` — Task 2: asset_index.py module
- [x] Commit `ccd7903` — Task 3: tests
