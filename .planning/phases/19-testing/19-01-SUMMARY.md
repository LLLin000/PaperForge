---
phase: 19-testing
plan: 01
subsystem: testing, utils
tags:
  - TEST-04
  - unit-tests
  - json
  - yaml
  - slugify
  - journal
dependency_graph:
  requires:
    - "14-shared-utilities-extraction (_utils.py)"
  provides:
    - "tests/test_utils_json.py"
    - "tests/test_utils_yaml.py"
    - "tests/test_utils_slugify.py"
    - "tests/test_utils_journal.py"
  affects:
    - "paperforge/worker/_utils.py (yaml_list bugfix)"
tech-stack:
  added:
    - "pytest + tmp_path for 71 unit tests"
  patterns:
    - "reset _JOURNAL_DB global cache between test classes"
---

## Summary

**Duration:** ~8 minutes
**Plan:** 19-testing-01 (4 tasks, 1 wave, sequential)

**Tasks:**
1. `tests/test_utils_json.py` — 21 tests covering read_json, write_json, read_jsonl, write_jsonl
2. `tests/test_utils_yaml.py` — 22 tests covering yaml_quote, yaml_block, yaml_list (incl. bugfix)
3. `tests/test_utils_slugify.py` — 20 tests covering slugify_filename, _extract_year
4. `tests/test_utils_journal.py` — 8 tests covering load_journal_db, lookup_impact_factor

**Verification:**
- `pytest tests/test_utils_json.py -x -q` — PASS (21 tests)
- `pytest tests/test_utils_yaml.py -x -q` — PASS (22 tests, incl. yaml_list None fix)
- `pytest tests/test_utils_slugify.py -x -q` — PASS (20 tests)
- `pytest tests/test_utils_journal.py -x -q` — PASS (8 tests)
- `pytest tests/ -x -q` — 274 passed, 2 skipped (71 new, 0 regressions)

**Bugfix discovered:** `yaml_list()` filter in `_utils.py:110` — `str(None)` yielded `"None"` (truthy) instead of being filtered out. Added explicit `value is not None` guard.

**Commits (from subagent tasks):**
- TBD from subagent commits

## Success Criteria Met

- [x] `tests/test_utils_json.py` — read/write JSON + JSONL round-trips, file not found, invalid JSON
- [x] `tests/test_utils_yaml.py` — yaml_quote edge cases, yaml_block empty/long text, yaml_list None/empty/mixed
- [x] `tests/test_utils_slugify.py` — slugify empty/special/unicode/long, _extract_year regex edge cases
- [x] `tests/test_utils_journal.py` — journal DB cache, lookup IF from DB and extra field
- [x] 0 regressions in existing tests
