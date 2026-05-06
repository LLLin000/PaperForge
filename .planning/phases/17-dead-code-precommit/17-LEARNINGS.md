---
phase: 17
phase_name: "Dead Code Precommit"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 9
  lessons: 4
  patterns: 4
  surprises: 3
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

## Decisions

### [tool.ruff] added targeting Python 3.10+ with E/F/I/UP/B/SIM rules

Standard rule set selected: pycodestyle (E), pyflakes (F), isort (I), pyupgrade (UP), flake8-bugbear (B), flake8-simplify (SIM). Line-length set to 120 to match project conventions.

**Source:** 17-01-PLAN.md (task 1, lines 154-165), 17-01-SUMMARY.md

---

### B904 (raise-within-try) globally ignored

Existing code intentionally uses bare `raise` in try/except blocks for read_json/write_json error paths. This is a deliberate pattern, not a bug.

**Source:** 17-01-PLAN.md (task 1, line 161), 17-01-SUMMARY.md (decisions)

---

### Pre-commit hooks NOT auto-installed (DX-04 deferred to Phase 18)

The .pre-commit-config.yaml is created and documented in CONTRIBUTING.md, but hook installation (pre-commit install) is left as a manual step for Phase 18.

**Source:** 17-01-PLAN.md (task 1, line 197), 17-01-SUMMARY.md (decisions)

---

### Check 5 uses ast module for robust duplicate utility detection

Rather than regex-based detection, Check 5 uses ast.parse to walk FunctionDef nodes and compare function names against the known _utils.py export list.

**Source:** 17-01-PLAN.md (task 1, lines 203-215), 17-01-SUMMARY.md

---

### per-file-ignores for pre-existing code quality issues not in scope

106 pre-existing violations across tests/, scripts/, skills/, and some paperforge modules were suppressed via targeted per-file-ignores rather than fixing them in this phase.

**Source:** 17-01-SUMMARY.md (Deviations from Plan, item 3)

---

### load_vault_config delegation wrappers replaced with direct top-level imports

All 7 worker modules: remove the 8-line delegation wrapper function, add `from paperforge.config import load_vault_config, paperforge_paths` at module level, and update intra-function import references.

**Source:** 17-01-PLAN.md (task 2, lines 316-353), 17-01-SUMMARY.md

---

### pipeline_paths function PRESERVED in each worker module

Only the load_vault_config delegation wrapper was removed. The pipeline_paths function stays in each module because it extends the base paths with worker-only keys (17 extra keys).

**Source:** 17-01-PLAN.md (task 2, lines 337-338), 17-01-SUMMARY.md

---

### library_record field added to OCR error meta.json

Both poll and upload error handlers now include `meta['library_record'] = key` to provide zotero_key context in error messages. Added to 4 error branches total.

**Source:** 17-01-PLAN.md (task 1, lines 217-232), 17-01-SUMMARY.md

---

### Dead system_dir/resources_dir/control_dir extraction removed from pipeline_paths

ruff F841 flagged these expression-only statements (unused variables from old monolithic script) as dead code. Removed from all 7 worker modules along with the now-unused `cfg = load_vault_config(vault)` call inside pipeline_paths.

**Source:** 17-01-SUMMARY.md (Deviations from Plan, item 1)

---

## Lessons

### ruff auto-fix can uncover dead code beyond just unused imports

Beyond removing ~350 unused imports, ruff's F841 rule caught expression-only statements (dead system_dir/resources_dir/control_dir variable extractions) that were invisible to manual review.

**Context:** These were remnants of the old monolithic script pattern that persisted through multiple refactoring phases. Only automated analysis flagged them.

**Source:** 17-01-SUMMARY.md (Deviations - Rule 2, item 1)

---

### Removing re-export wrappers cascades to dependent modules

When _resolve_formal_note_path was removed from deep_reading.py's re-exports, repair.py broke because it imported the symbol through deep_reading.py rather than directly. The fix required changing repair.py's import to point directly to _utils.py.

**Context:** This shows that even backward-compatible re-exports create implicit dependency chains that break when the re-export is removed.

**Source:** 17-01-SUMMARY.md (Deviations - Rule 2, item 2)

---

### per-file-ignores are necessary when doing targeted cleanup

106 pre-existing violations across tests/, scripts/, skills/, and some paperforge modules were not in scope for this phase. Targeted per-file-ignores avoided scope creep while keeping ruff check clean.

**Context:** These violations ranged from line-length issues to simplification suggestions in pre-existing test code that would have required disproportionate effort to fix.

**Source:** 17-01-SUMMARY.md (Deviations - Rule 2, item 3)

---

### Dead code accumulates silently across refactoring phases

~450 total fixes (353 imports + 58 unsafe + 38 format + additional manual removals) were needed. Code that was "working" contained significant dead weight that had accumulated across multiple phases without detection.

**Context:** The 7 worker modules, having been refactored multiple times (Phases 12, 14, 15, 16), accumulated unused imports from removed feature code, renamed APIs, and refactored utility functions.

**Source:** 17-01-SUMMARY.md

---

## Patterns

### Pre-Commit Hooks as Safety Net

Automated enforcement (ruff lint, ruff format, consistency audit) prevents code quality regressions at commit time rather than relying on manual review.

**Source:** 17-01-PLAN.md (task 1), 17-01-SUMMARY.md

---

### AST-Based Code Analysis for Structural Checks

Using ast.parse rather than regex for Check 5's duplicate utility detection provides accurate function boundary detection without false positives from comments or strings.

**Source:** 17-01-PLAN.md (task 1, lines 203-215), 17-01-SUMMARY.md

---

### Direct Import Replacing Delegation Wrapper

Remove the function hop by replacing `def load_vault_config(vault): from paperforge.config import load_vault_config as _shared; return _shared(vault)` with `from paperforge.config import load_vault_config` at module level. Same name binding, zero indirection.

**Source:** 17-01-PLAN.md (task 2), 17-01-SUMMARY.md

---

### Error Context Enrichment

Adding a single field (`library_record` with zotero_key) to existing error data structures provides actionable debugging context without restructuring error handling paths.

**Source:** 17-01-PLAN.md (task 1), 17-01-SUMMARY.md

---

## Surprises

### 353 issues auto-fixed by ruff -- far more unused imports than anticipated

The initial ruff check found 353 issues automatable by --fix, plus 58 more via --unsafe-fixes. This vastly exceeded the expected number of dead imports.

**Impact:** Required significantly more verification effort (module import testing, test suite) than planned.

**Source:** 17-01-SUMMARY.md

---

### Dead system_dir/resources_dir/control_dir extraction found by ruff via F841

Expression-only statements dating from the old monolithic script pattern were silently present in all 7 worker modules. Only ruff's F841 (unused-variable) rule flagged them.

**Impact:** Required manual removal from all 7 worker modules plus adjusting pipeline_paths to no longer call load_vault_config (which was only needed for those dead extractions).

**Source:** 17-01-SUMMARY.md (Deviations - Rule 2, item 1)

---

### repair.py imported _resolve_formal_note_path through deep_reading.py's re-export, not directly

When deep_reading.py's re-export of _resolve_formal_note_path was removed, repair.py broke. The implicit dependency via deep_reading.py was not documented and was invisible until import test failed.

**Impact:** Required fixing repair.py to import directly from _utils.py. Highlighted the fragility of chained re-exports.

**Source:** 17-01-SUMMARY.md (Deviations - Rule 2, item 2)
