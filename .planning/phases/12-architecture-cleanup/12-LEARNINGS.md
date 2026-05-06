---
phase: 12
phase_name: "Architecture Cleanup"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 6
  lessons: 4
  patterns: 3
  surprises: 1
missing_artifacts:
  - "12-VERIFICATION.md"
  - "12-UAT.md"
---

## Decisions

### Extract 4041-line monolithic file into 7 focused worker modules
`paperforge/worker/` now contains 7 modules: sync.py, ocr.py, repair.py, status.py, deep_reading.py, update.py, base_views.py — each responsible for a single functional area.

**Rationale/Context:** The original `literature_pipeline.py` (4041 lines) was a God module with no separation of concerns. Extraction improves maintainability, testability, and developer onboarding.

**Source:** 12-SUMMARY.md (Files Created)

---

### Relocate skills/ to paperforge/skills/ with backward-compatible fallback
`skills/literature-qa/` moved to `paperforge/skills/literature-qa/`. `setup_wizard.py` checks the new location first, then falls back to the old location during the transition period.

**Rationale/Context:** Skills are part of the paperforge package, not an independent top-level directory. A fallback mechanism prevents breakage for users who haven't updated their installation.

**Source:** 12-SUMMARY.md (Skills Migration, Decisions Made)

---

### Duplicated utilities acceptable for test compatibility
Each worker module received a full copy of utility functions from the original monolithic file header during migration.

**Rationale/Context:** Slightly wasteful, but ensures each module is self-contained during the migration without needing to rewrite all internal function calls. A planned refactoring pass in a future phase can extract shared utilities.

**Source:** 12-SUMMARY.md (Decisions Made)

---

### Module-reference imports for patchable cross-module calls
`ocr.py` uses `from paperforge.worker import sync as _sync` with `_sync.run_selection_sync()` instead of direct `from paperforge.worker.sync import run_selection_sync`.

**Rationale/Context:** Direct imports create module-level references that are not affected by monkey-patching. Module-reference imports allow tests to patch `paperforge.worker.sync.run_selection_sync` and have the patch apply to calls within `ocr.py`.

**Source:** 12-SUMMARY.md (Decisions Made)

---

### Function-level imports to avoid circular imports
`sync.py` uses function-level imports inside `run_selection_sync` and `run_index_refresh` for cross-module dependencies (`ensure_base_views` from `base_views.py`, `validate_ocr_meta` from `ocr.py`).

**Rationale/Context:** `sync.py` and `ocr.py` have mutual dependencies. Top-level imports in both directions would create circular import errors at module load time. Function-level imports defer the resolution until invocation.

**Source:** 12-SUMMARY.md (Deviation 4)

---

### Delete old directories only after test confirmation
`pipeline/` and `skills/` directories were removed only after all 203 tests passed with zero failures.

**Rationale/Context:** Premature deletion could have hidden issues. Keeping old directories until test verification provides a rollback path and ensures the new module structure is fully functional.

**Source:** 12-SUMMARY.md (Decisions Made)

---

## Lessons

### OCR test patches must target the correct module namespace
After extracting `run_ocr` to `paperforge/worker/ocr.py`, tests that patched `paperforge.worker.sync.write_json` no longer caught writes because `ocr.py` had its own copy of the utility function.

**Rationale/Context:** Module extraction changes function ownership. Tests must update their patch targets to reflect the new module structure. This was discovered only when tests failed after the migration.

**Source:** 12-SUMMARY.md (Deviation 1)

---

### Direct imports break mock patching for cross-module calls
`run_ocr` called `run_selection_sync` via `from paperforge.worker.sync import run_selection_sync`, creating a module-level reference that was not affected by patches on `sync.run_selection_sync`.

**Rationale/Context:** Python's `from X import Y` creates a new reference in the importing module's namespace. `unittest.mock.patch` targets are ineffective on these direct imports. The fix was to use module-reference imports (`import sync as _sync` + `_sync.run_selection_sync()`).

**Source:** 12-SUMMARY.md (Deviation 2)

---

### Dynamic module loading tests break when source files are deleted
`test_legacy_worker_compat.py` dynamically loaded the now-deleted `literature_pipeline.py` at import time, causing the test module itself to fail before any test could execute.

**Rationale/Context:** Tests that dynamically load source files are tightly coupled to file paths. When those files are moved or deleted, the test module cannot even be imported. Tests should import from the package interface, not from specific file paths.

**Source:** 12-SUMMARY.md (Deviation 3)

---

### 203 tests passed after full migration
The complete architecture cleanup resulted in 203 passed, 0 failed, 2 skipped — meeting the target of 203+ passed.

**Rationale/Context:** This validates that the extraction was functionally correct. All existing behavior was preserved despite the significant structural reorganization.

**Source:** 12-SUMMARY.md (Test Results)

---

## Patterns

### Wave strategy with per-wave verification
Each wave (Package Structure + Sync/OCR, Repair/Status/Deep, Base Views + Skills, Import Cleanup, Docs) was verified individually before proceeding to the next, preventing regression accumulation.

**Rationale/Context:** Architecture cleanup is inherently risky (many interdependent changes). Verifying each wave independently ensures problems are caught early and the rollback scope is minimized.

**Source:** 12-PLAN.md (Wave Strategy)

---

### Backward-compatible fallback in setup_wizard
The setup wizard checks the new directory location first, then falls back to the old location for the transition period.

**Rationale/Context:** Users may have outdated installations or manual configurations. A graceful fallback prevents breakage during the migration window.

**Source:** 12-SUMMARY.md (Decisions Made)

---

### git mv for preserving file history
The plan explicitly recommended using `git mv` for file moves to preserve git history across the extraction.

**Rationale/Context:** Without `git mv`, renamed files lose their commit history, making future `git blame` investigations harder. Preserving history aids debugging and attribution.

**Source:** 12-PLAN.md (Risk Mitigation)

---

## Surprises

### Circular import issues between sync.py and ocr.py
`sym.py` needs functions from `base_views.py` and `ocr.py`, while `ocr.py` also needs `run_selection_sync` from `sync.py`. This mutual dependency created circular import errors that were not anticipated.

**Rationale/Context:** In a monolithic 4041-line file, circular imports don't exist because everything is in the same module. Splitting by functional area revealed hidden coupling between sync and OCR logic that required function-level imports to break the cycle.

**Source:** 12-SUMMARY.md (Deviation 4)
