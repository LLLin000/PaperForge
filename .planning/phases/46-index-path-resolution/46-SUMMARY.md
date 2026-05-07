---
phase: 46-index-path-resolution
plan: 001+002
subsystem: core-config
tags:
  - asset_index
  - config
  - env-var
  - path-resolution
  - base_views
  - discussion
dependency-graph:
  requires: []
  provides:
    - "Config-resolved literature_dir in 5 canonical index workspace fields"
    - "PAPERFORGE_LITERATURE_DIR env var used globally"
    - "library_records path matches docstring"
    - "CONFIG_PATH_KEYS covers skill_dir + command_dir"
  affects: "11 downstream consumers: plugin dashboard, context command, discussion.py, ld_deep.py, status.py, repair.py, sync.py"
tech-stack:
  added: []
  patterns:
    - "path.relative_to(vault) for config-resolved vault-relative paths"
    - "pathlib.Path for cross-platform path construction"
key-files:
  created: []
  modified:
    - paperforge/worker/asset_index.py
    - paperforge/config.py
    - tests/test_config.py
    - paperforge/worker/base_views.py
    - paperforge/worker/discussion.py
    - tests/test_base_views.py
    - tests/test_migration.py
decisions:
  - "Used workspace_dir.relative_to(vault) + forward-slash normalization for all 5 workspace path fields"
  - "Removed LIBRARY_RECORDS substitution entirely (no .base templates reference it)"
  - "Simplified discussion.py path construction to vault_path / ai_path_str (pathlib handles cross-platform)"
metrics:
  duration: "5 min"
  completed_date: "2026-05-07"
  tasks_total: 4
  tasks_completed: 4
  requirements: "PATH-01 through PATH-06"
---

# Phase 46: Index Path Resolution — Execution Summary

**One-liner:** Replaced 5 hardcoded `"Literature/"` paths in the canonical index builder with config-resolved relative paths, fixed the `PAPERFORGERATURE_DIR` env var typo (missing `LI`), aligned `library_records` path with its docstring, extended `CONFIG_PATH_KEYS` for migration coverage, removed orphan `${LIBRARY_RECORDS}` placeholder substitution, and eliminated unnecessary Windows backslash replacement in discussion.py.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Updated tests affected by changes**
- **Found during:** Test execution (post-task verification)
- **Issue:** 3 tests failed due to our changes: `test_base_views.py` had 2 tests referencing the removed `${LIBRARY_RECORDS}` substitution; `test_migration.py` had a hardcoded `"Literature/"` expected path that no longer matches the config-resolved output.
- **Fix:** Updated `test_base_views.py` to test `${LITERATURE}` and `${CONTROL_DIR}` placeholders instead; updated `test_migration.py` to derive the expected root from `paths["literature"].relative_to(vault)`.
- **Files modified:** `tests/test_base_views.py`, `tests/test_migration.py`
- **Commit:** `4e30c51`

### Out-of-scope Issues Logged

**2. [Pre-existing] OCR state machine test failures (2 tests)**
- **Tests:** `test_retry_exhaustion_becomes_error` (expects `error` but gets `blocked`), `test_full_cycle_from_pending_to_done` (expects `done` but gets `queued`)
- **Root cause:** OCR state machine status values changed — unrelated to Phase 46 changes
- **Documented in:** `.planning/phases/46-index-path-resolution/46-deferred-items.md`

## Asset Inventory

### Files Created
None.

### Files Modified

| File | Changes |
|------|---------|
| `paperforge/worker/asset_index.py` | 5 workspace-path fields now use `workspace_dir.relative_to(vault)` instead of hardcoded `f"Literature/..."` |
| `paperforge/config.py` | (1) Env var: `paperforgeRATURE_DIR` -> `PAPERFORGE_LITERATURE_DIR` (2) library_records: `control` -> `control / "library-records"` (3) CONFIG_PATH_KEYS: added `skill_dir`, `command_dir` |
| `tests/test_config.py` | Updated assertion from `paperforgeRATURE_DIR` to `PAPERFORGE_LITERATURE_DIR` |
| `paperforge/worker/base_views.py` | Removed orphan `${LIBRARY_RECORDS}` placeholder substitution |
| `paperforge/worker/discussion.py` | Simplified `ai_dir = vault_path / ai_path_str` (removed `os.name` conditional and backslash replace) |
| `tests/test_base_views.py` | Updated placeholder tests to use `${LITERATURE}` and `${CONTROL_DIR}` |
| `tests/test_migration.py` | Updated path expectations to use config-resolved `lit_rel` |

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `b4da56a` | `fix(46-index-path-resolution): replace 5 hardcoded Literature/ paths with config-resolved relative paths (PATH-01)` | asset_index.py |
| `5b037ef` | `fix(46-index-path-resolution): fix config env var typo, library_records path, and CONFIG_PATH_KEYS (PATH-02, PATH-03, PATH-04)` | config.py, test_config.py |
| `6c66bf4` | `fix(46-index-path-resolution): remove orphan LIBRARY_RECORDS placeholder from base_views.py (PATH-05)` | base_views.py |
| `b6cb7e6` | `fix(46-index-path-resolution): remove unnecessary Windows backslash replace in discussion.py (PATH-06)` | discussion.py |
| `4e30c51` | `fix(46-index-path-resolution): update tests for removed LIBRARY_RECORDS and config-resolved paths` | test_base_views.py, test_migration.py |

## Test Results

- **Total:** 480 tests (478 pass, 2 fail, 2 skip)
- **Failures:** 2 pre-existing OCR state machine tests (`test_retry_exhaustion_becomes_error`, `test_full_cycle_from_pending_to_done`) — not caused by Phase 46 changes
- **All Phase 46-related tests pass:** ENV_KEYS coverage, path resolution smoke test, placeholder substitution, workspace path assertions

## Verification Summary

| Requirement | Status | Notes |
|-------------|--------|-------|
| PATH-01 | PASS | 5 workspace fields use config-resolved `literature_dir` via `workspace_dir.relative_to(vault)` |
| PATH-02 | PASS | `library_records` returns `control / "library-records"` matching docstring |
| PATH-03 | PASS | `PAPERFORGE_LITERATURE_DIR` env var correct; no `paperforgeRATURE_DIR` remnants |
| PATH-04 | PASS | `CONFIG_PATH_KEYS` includes `skill_dir` and `command_dir` |
| PATH-05 | PASS | `${LIBRARY_RECORDS}` placeholder substitution removed from `base_views.py` |
| PATH-06 | PASS | Unnecessary `ai_path_str.replace("/", "\\")` removed from `discussion.py` |

## Known Stubs

None. All changes are production-ready path resolution logic. No empty values, placeholder text, or disconnected components introduced.

## Self-Check

- [x] All 5 workspace-path fields in canonical index entries use config-resolved paths
- [x] `PAPERFORGE_LITERATURE_DIR` env var correctly overrides `literature_dir`
- [x] `paperforge_paths()["library_records"]` returns `<control>/library-records`
- [x] `CONFIG_PATH_KEYS` includes `skill_dir` and `command_dir`
- [x] `rg '\$\{LIBRARY_RECORDS\}'` returns zero matches in paperforge/worker/
- [x] `rg 'replace.*/.*\\'` returns zero matches in discussion.py path construction
- [x] All modified files pass Python syntax validation
- [x] library_records path key preserved in config.py (not removed)
- [x] Test suite: 478 passed, 2 pre-existing OCR failures documented as deferred
