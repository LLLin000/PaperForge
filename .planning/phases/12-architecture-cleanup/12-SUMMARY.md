# Phase 12 Plan 12: Architecture Cleanup Summary

**One-liner:** Migrated 4041-line monolithic `literature_pipeline.py` into 7 focused worker modules under `paperforge/worker/` and relocated `skills/literature-qa/` to `paperforge/skills/literature-qa/`.

---

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | Create `paperforge/worker/` package structure | Done |
| 2 | Migrate sync functions from literature_pipeline.py | Done |
| 3 | Migrate OCR functions | Done |
| 4 | Migrate repair functions | Done |
| 5 | Migrate status/doctor functions | Done |
| 6 | Migrate deep-reading functions | Done |
| 7 | Extract base_views module | Done |
| 8 | Migrate skills/ to paperforge/skills/ | Done |
| 9 | Update all import paths | Done |
| 10 | Verify tests and consistency audit | Done |
| 11 | Update documentation (implicit in AGENTS.md paths) | Done |

---

## Files Created

### Worker Modules (`paperforge/worker/`)
- `paperforge/worker/__init__.py` — Package init with re-exports
- `paperforge/worker/sync.py` — sync utilities + selection-sync + index-refresh (~1440 lines)
- `paperforge/worker/ocr.py` — OCR queue + post-processing (~1377 lines)
- `paperforge/worker/repair.py` — Repair scan + fix mode (~540 lines)
- `paperforge/worker/status.py` — Doctor + status commands (~626 lines)
- `paperforge/worker/deep_reading.py` — Deep reading queue (~120 lines)
- `paperforge/worker/update.py` — Update/rollback logic (~398 lines)
- `paperforge/worker/base_views.py` — Base view generation (~516 lines)

### Skills Migration (`paperforge/skills/`)
- `paperforge/skills/__init__.py`
- `paperforge/skills/literature-qa/scripts/ld_deep.py`
- `paperforge/skills/literature-qa/prompt_deep_subagent.md`
- `paperforge/skills/literature-qa/chart-reading/*.md` (20 chart reading guides)

---

## Files Modified

### Command Layer
- `paperforge/commands/sync.py` — Import from `paperforge.worker.sync`
- `paperforge/commands/ocr.py` — Import from `paperforge.worker.ocr`
- `paperforge/commands/repair.py` — Import from `paperforge.worker.repair`
- `paperforge/commands/status.py` — Import from `paperforge.worker.status`
- `paperforge/commands/deep.py` — Import from `paperforge.worker.deep_reading`

### CLI & Config
- `paperforge/cli.py` — `_import_worker_functions()` now imports from `paperforge.worker.*`
- `paperforge/config.py` — `ld_deep_script` resolution checks `paperforge/skills/` first, then falls back to old `skills/` location

### Setup
- `setup_wizard.py` — Updated to copy worker modules from `paperforge/worker/` and skills from `paperforge/skills/`, with backward-compatible fallbacks

### Tests (14 files)
- `tests/test_pdf_resolver.py`
- `tests/test_path_normalization.py`
- `tests/test_selection_sync_pdf.py`
- `tests/test_base_views.py`
- `tests/test_base_preservation.py`
- `tests/test_doctor.py`
- `tests/test_repair.py`
- `tests/test_ocr_preflight.py`
- `tests/test_ocr_state_machine.py`
- `tests/test_smoke.py`
- `tests/test_ld_deep_config.py`
- `tests/test_prepare_rollback.py`
- `tests/test_legacy_worker_compat.py`
- `tests/conftest.py`

---

## Files Deleted

- `pipeline/worker/scripts/literature_pipeline.py` (4041 lines)
- `pipeline/__init__.py`
- `pipeline/worker/__init__.py`
- `pipeline/worker/scripts/__init__.py`
- Entire `skills/literature-qa/` directory (moved to `paperforge/skills/literature-qa/`)

---

## Test Results

```
pytest tests/ -v --tb=short
========================= 203 passed, 2 skipped in 5.48s ========================
```

Target met: 203+ passed, 0 failed.

---

## Consistency Audit

```
=== Consistency Audit Results ===
[PASS] Check 1: No old command names
[PASS] Check 2: No paperforge_lite in Python
[PASS] Check 3: No dead links
[PASS] Check 4: Command docs structure
Passed: 4/4
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] OCR test patches targeting wrong module namespace**
- **Found during:** Task 6 (OCR test verification)
- **Issue:** After extracting `run_ocr` to `paperforge/worker/ocr.py`, tests that patched `paperforge.worker.sync.write_json` no longer caught writes because `ocr.py` had its own copy of `write_json` from the duplicated header utilities. Similarly, direct imports like `from paperforge.worker.sync import load_export_rows` created module-level references that were unaffected by patches on `sync`.
- **Fix:** Updated `test_ocr_preflight.py` and `test_ocr_state_machine.py` patch targets from `paperforge.worker.sync.*` to `paperforge.worker.ocr.*` for functions used internally by `ocr.py`. Also changed `ocr.py` to use `_sync.run_selection_sync()` module reference instead of direct import so patches on `sync.run_selection_sync` continue to work.
- **Files modified:** `paperforge/worker/ocr.py`, `tests/test_ocr_preflight.py`, `tests/test_ocr_state_machine.py`
- **Commit:** `f54fe8a`

**2. [Rule 1 - Bug] `run_ocr` calling `run_selection_sync` caused KeyError in tests**
- **Found during:** Task 6 (OCR test verification)
- **Issue:** `run_ocr` calls `run_selection_sync(vault)` at the end. Tests patched `run_selection_sync` but because `ocr.py` imported it directly with `from paperforge.worker.sync import run_selection_sync`, the patch didn't affect `ocr.py`'s reference.
- **Fix:** Changed `ocr.py` to use `from paperforge.worker import sync as _sync` and call `_sync.run_selection_sync(vault)`, making the patch effective.
- **Files modified:** `paperforge/worker/ocr.py`
- **Commit:** `498a9ed`

**3. [Rule 1 - Bug] `test_legacy_worker_compat.py` module loading failure**
- **Found during:** Task 10 (final verification)
- **Issue:** The test dynamically loaded `pipeline/worker/scripts/literature_pipeline.py` at import time. After deleting the file, the test module couldn't even be imported.
- **Fix:** Rewrote the test to import directly from `paperforge.worker.sync` and `paperforge.config`, and updated the subprocess test to use `python -m paperforge` CLI instead of invoking the deleted script.
- **Files modified:** `tests/test_legacy_worker_compat.py`
- **Commit:** `f54fe8a`

**4. [Rule 2 - Missing functionality] Function-level imports for circular import breaking**
- **Found during:** Task 2 (sync module creation)
- **Issue:** `sync.py` needs `ensure_base_views` (from `base_views.py`) and `validate_ocr_meta` (from `ocr.py`), but `ocr.py` also needs `run_selection_sync` from `sync.py`. Top-level imports in both directions would create a circular import.
- **Fix:** Used function-level imports inside `run_selection_sync` and `run_index_refresh` for cross-module dependencies.
- **Files modified:** `paperforge/worker/sync.py`
- **Commit:** `498a9ed`

---

## Known Stubs

None. All functions are fully implemented from the original monolithic file.

---

## Decisions Made

1. **Duplicated utilities acceptable for test compatibility**: Each worker module initially received a full copy of the utility functions from the original file header. This is slightly wasteful but ensures each module is self-contained and avoids needing to rewrite all internal function calls during the migration.

2. **Module-reference imports for patchable cross-module calls**: `ocr.py` uses `from paperforge.worker import sync as _sync` and calls `_sync.run_selection_sync()` so that tests can patch `paperforge.worker.sync.run_selection_sync` and have the patch affect `ocr.py`.

3. **Backward compatibility in setup_wizard.py**: The wizard checks `paperforge/skills/` first, then falls back to `skills/` for the transition period, matching the plan's requirement.

4. **Old directories deleted after test confirmation**: `pipeline/` and `skills/` were removed only after all 203 tests passed with zero failures.

---

## Self-Check: PASSED

- [x] All new worker modules exist and are importable
- [x] `paperforge/worker/__init__.py` exports all required functions
- [x] `paperforge/skills/literature-qa/` contains all migrated files
- [x] No `pipeline.worker.scripts` imports remain in codebase
- [x] No `skills/literature-qa` imports remain in codebase (except backward-compat fallback in setup_wizard.py)
- [x] All tests pass (203 passed, 2 skipped)
- [x] Consistency audit passes (4/4)
- [x] Commits exist for all major changes

---

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `498a9ed` | feat(phase-12): extract worker modules from literature_pipeline.py | 16 files changed, 5329 insertions(+) |
| `ba8a08b` | feat(phase-12): migrate skills/literature-qa to paperforge/skills/ | 22 files changed, 3156 insertions(+) |
| `f54fe8a` | test(phase-12): update test imports for new worker module structure | 14 files changed, 139 insertions(+), 163 deletions(-) |
| `87251db` | chore(phase-12): remove old pipeline/ and skills/ directories | 26 files changed, 7350 deletions(-) |
