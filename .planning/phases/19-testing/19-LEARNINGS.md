---
phase: 19
phase_name: "Testing"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 7
  lessons: 3
  patterns: 3
  surprises: 2
missing_artifacts:
  - "UAT.md"
---

## Decisions

### Test file per function group
Created 4 dedicated unit test files covering all `paperforge/worker/_utils.py` functions, plus `test_e2e_pipeline.py` and `test_setup_wizard.py`. Each test file covers one logical module/function group.

**Rationale/Context:** Close TEST-04 (last testing gap in v1.4 code health phase) and TEST-01/TEST-02 (E2E and setup wizard coverage). Isolated test files make failures easier to diagnose and maintain.

**Source:** 19-01-PLAN.md, 19-02-PLAN.md, 19-03-PLAN.md

---

### Cache reset pattern for journal DB tests
Journal DB tests must reset `_utils._JOURNAL_DB = None` between test scenarios to account for the module-level global cache.

**Rationale/Context:** `_utils.py` caches `_JOURNAL_DB` globally across calls within the same process. Without explicit cache reset, tests that check loading behavior would get stale cached results.

**Source:** 19-01-PLAN.md Task 4

---

### E2E tests run against existing fixture vault
Rather than deleting and recreating records, E2E tests run selection-sync on the existing `test_vault` fixture and verify the updated records match expected values.

**Rationale/Context:** The `test_vault` fixture already creates library records and formal notes. Running sync on the existing vault verifies deduplication behavior and updates, which is more realistic than testing from scratch.

**Source:** 19-02-PLAN.md Task 1

---

### State-based OCR validation
OCR pipeline behavior is validated via meta.json state files only, not by calling `run_ocr()`.

**Rationale/Context:** `run_ocr()` requires network access to PaddleOCR API. State-based validation (`ocr_status: done/pending/nopdf`) avoids external dependencies and is faster.

**Source:** 19-02-PLAN.md Task 1, 19-02-SUMMARY.md

---

### sys.path insertion for setup_wizard tests
Test files for `setup_wizard.py` insert repo root into `sys.path` to make the module importable.

**Rationale/Context:** Same pattern as `test_smoke.py`. The repo root is not in the default Python path, so explicit insertion is needed for imports to work.

**Source:** 19-03-PLAN.md Task 1

---

### No Textual UI testing
Tests focus on standalone functions and classes (`AGENT_CONFIGS`, `EnvChecker`, `CheckResult`, `_find_vault`) — the `SetupWizardApp` Textual App class is excluded.

**Rationale/Context:** Textual-based App and StepScreen classes require a running terminal. Focusing on standalone detection/validation logic allows testing without terminal dependencies.

**Source:** 19-03-PLAN.md

---

### 3-stage pipeline consistency check
E2E tests validate consistency across selection-sync, index-refresh, formal notes, and OCR states in a single test method.

**Rationale/Context:** A `test_full_pipeline_consistency()` test runs all stages sequentially and cross-validates outputs (matching titles, consistent ocr_status, correct wikilinks), ensuring the pipeline produces coherent state end-to-end.

**Source:** 19-02-PLAN.md, 19-02-SUMMARY.md

---

## Lessons

### yaml_list() None filter bug discovered during test writing
`yaml_list()` filter in `_utils.py:110` — `str(None)` yielded `"None"` (truthy) instead of being filtered out.

**Context:** While writing unit tests for `yaml_list`, it was discovered that `None` values in list items were not properly filtered because `str(None)` produces the string `"None"` which is truthy. Fixed with explicit `value is not None` guard.

**Source:** 19-01-SUMMARY.md

---

### High test count growth from utility tests
Starting from ~205 existing tests, adding 71 new tests across 4 utility test files resulted in 317 total tests.

**Context:** The 4 unit test files added 71 tests (21+22+20+8), plus E2E and setup wizard tests adding 13+30 = 43 more, for a total of 114 new tests reaching 317 passed, 2 skipped.

**Source:** 19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md

---

### Zero regression consistently achieved
All 3 sub-phases added 0 regressions to the existing test suite.

**Context:** Each of the 3 test sub-plans explicitly verified zero regressions. The full suite passed with 317 tests (2 skipped) at the end of the phase.

**Source:** 19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md

---

## Patterns

### tmp_path for isolated vault creation
All tests use pytest's `tmp_path` fixture for temporary directory creation instead of heavyweight vault fixtures.

**When to use:** For unit tests that need temporary files or directories but don't need a full vault structure with paperforge.json and exports.

**Source:** 19-01-PLAN.md, 19-02-PLAN.md, 19-03-PLAN.md

---

### conftest fixtures for E2E tests
`test_vault` fixture provides a full vault with paperforge.json, exports, OCR fixtures, and library records.

**When to use:** For integration tests that need the complete vault structure including paperforge.json configuration, Zotero exports, OCR state files, and library records.

**Source:** 19-02-PLAN.md

---

### monkeypatch/patch for platform-dependent tests
`unittest.mock.patch` and monkeypatch used for import simulation, path override, and platform-dependent behavior.

**When to use:** When testing code that depends on environment state (Zotero installation, Python version, current working directory).

**Source:** 19-03-PLAN.md, 19-03-SUMMARY.md

---

## Surprises

### Fast execution speed
71 new tests created across 3 sub-plans in ~16 minutes total (8+4+4 min).

**Impact:** The testing phase was completed much faster than expected, demonstrating that well-specified test plans with detailed code snippets speed implementation significantly.

**Source:** 19-01-SUMMARY.md, 19-02-SUMMARY.md, 19-03-SUMMARY.md

---

### Bug found while writing tests, not in production
The yaml_list None filter bug was discovered during test creation rather than in production usage.

**Impact:** The test-driven approach caught a latent bug that would have caused incorrect YAML output when None values appeared in list data. Proves the value of comprehensive unit test coverage.

**Source:** 19-01-SUMMARY.md
