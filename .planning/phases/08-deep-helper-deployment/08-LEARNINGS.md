---
phase: 08
phase_name: "Deep Helper Deployment"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 4
  lessons: 4
  patterns: 5
  surprises: 4
missing_artifacts:
  - "UAT.md"
---

## Decisions

### D-01: Use `importlib.util.spec_from_file_location` with sys.modules pre-registration for Python 3.14
When importing `ld_deep.py` from tests, pre-register the module in `sys.modules` before `exec_module` to work around Python 3.14 dataclass compatibility issues with `from __future__ import annotations`.

**Rationale/Context:** Python 3.14 pre-release has a dataclass regression where `dataclasses` accesses `sys.modules[cls.__module__].__dict__` before the module is registered.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 2)

### D-02: Generate deterministic OCR fixtures once and commit, never regenerate in CI
The `tests/sandbox/ocr-complete/TSTONE001/` fixtures (fulltext, figure-map, chart-type-map, meta) were generated once and committed to git.

**Rationale/Context:** Deterministic fixtures ensure tests are repeatable. Regenerating in CI would introduce variability or require live API calls.  
**Source:** 08-PLAN.md (Task 2) / 08-SUMMARY.md (Decisions Made)

### D-03: Rollback deletes partial files and restores original note text
`prepare_deep_reading()` rollback tracks files written during the current run and, on failure, deletes created files and restores the original formal note from a saved copy.

**Rationale/Context:** Not a full filesystem snapshot — only tracks artifacts created during this single prepare call. Sufficient for the partial-failure scenario.  
**Source:** 08-PLAN.md (Task 5) / 08-SUMMARY.md (Decisions Made)

### D-04: `_import_ld_deep()` helper for non-package imports
Created a helper function using `importlib.util.spec_from_file_location` to import `ld_deep.py` from outside the package tree, since `skills/` has no `__init__.py`.

**Rationale/Context:** `from skills.literature_qa.scripts.ld_deep import ...` fails because `skills/` directory is not a Python package.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 3)

---

## Lessons

### L-01: Python 3.14 pre-release has a dataclass regression with `from __future__ import annotations`
`dataclasses.dataclass` accesses `sys.modules[cls.__module__].__dict__` before the module is registered in `sys.modules`, causing import failures when using `importlib.util.spec_from_file_location`.

**Rationale/Context:** Only affects the pre-release Python 3.14.0. Workaround is to pre-register the module before `exec_module`.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 2) / 08-VERIFICATION.md

### L-02: Doctor was checking directory existence, not actual importability
The doctor's "Agent script" check only verified that the script directory existed, not that the script could actually be imported and executed.

**Rationale/Context:** Directory existence ≠ importability. A file can exist but fail to import due to syntax errors, missing dependencies, or module resolution issues.  
**Source:** 08-PLAN.md (Task 1b)

### L-03: `skills/` is not a Python package — direct import fails
Because `skills/` has no `__init__.py`, `from skills.literature_qa.scripts.ld_deep import ...` raises `ModuleNotFoundError`.

**Rationale/Context:** The `skills/` directory is designed for deployment to Agent vaults, not as a Python package in the repo. An import helper is needed for tests.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 3)

### L-04: zotero_key regex captured surrounding quotes causing queue filter mismatch
The regex extracting `zotero_key` from JSON captured quotation marks (`"TSTONE001"` instead of `TSTONE001`), causing the queue filter to not match records and OCR path lookup to fail.

**Rationale/Context:** Fixed by adding `.strip('"').strip("'")` to the extracted key value. Found during test execution of `test_queue_shows_ready_paper`.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 1)

---

## Patterns

### P-01: Rollback-on-failure in prepare operations
Track files written during a prepare operation. On any exception, delete created files and restore original content from a saved copy.

**When to use:** Any multi-step write operation where partial completion would leave the system in an inconsistent state.  
**Source:** 08-PLAN.md (Task 5) / 08-SUMMARY.md

### P-02: Deterministic fixtures committed to git
Generate test fixtures once via a script, verify correctness, and commit them. Never regenerate in CI.

**When to use:** When tests depend on specific data that's expensive or non-deterministic to generate at test time.  
**Source:** 08-PLAN.md (Task 2) / 08-SUMMARY.md

### P-03: Regression test per reported issue
Each regression test is named with a regression ID and covers one specific issue from prior audit findings.

**When to use:** When tracking regression from an audit or known-issue list. One test per issue = clear pass/fail per finding.  
**Source:** 08-PLAN.md (Task 3d) / 08-SUMMARY.md (patterns-established)

### P-04: Import helper for non-package modules
Use `importlib.util.spec_from_file_location` with a helper function to import modules that live outside the package tree.

**When to use:** When code is deployed to a non-standard location (e.g., an Agent vault's skills directory) and tests need to import it.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 3)

### P-05: Doc-as-executable validation
Extract command snippets from markdown documentation, execute them against a test fixture, and assert they run without error.

**When to use:** When documentation contains runnable commands that must stay in sync with actual CLI behavior.  
**Source:** 08-PLAN.md (Task 4)

---

## Surprises

### S-01: zotero_key quote stripping bug discovered during test execution
The regex capturing `zotero_key` from JSON included surrounding quotation marks. This wasn't caught by existing tests because no test exercised the queue with actual JSON-sourced keys.

**Impact:** Medium — queue filter silently failed to match records, causing false "nothing ready" output. Caught and fixed during Phase 8 testing.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 1)

### S-02: Python 3.14 dataclass import workaround needed
Python 3.14 pre-release broke the standard `importlib.util` pattern for importing modules with dataclasses. Required pre-registration in `sys.modules`.

**Impact:** Low — workaround exists. Affects only pre-release Python 3.14.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 2)

### S-03: Import from `skills/` fails because it's not a Python package
`skills/` has no `__init__.py`, so direct imports from it fail. Required creating an `_import_ld_deep()` helper.

**Impact:** Medium — test imports would fail without the workaround. Not a production issue but a test infrastructure concern.  
**Source:** 08-SUMMARY.md (Deviations — Auto-fixed Issue 3)

### S-04: Test vault fixture cleanup caused transient state issues
Reusing the same test vault across tests caused state leaks (files from one test affecting another). Resolved by creating a fresh vault per test.

**Impact:** Low — transient test failures during development. Resolved with per-test isolation.  
**Source:** 08-SUMMARY.md (Issues Encountered)
