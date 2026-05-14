---
phase: permanent-jsonl-review
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - paperforge/memory/permanent.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase permanent-jsonl-review: Code Review Report

**Reviewed:** 2026-05-14
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `paperforge/memory/permanent.py` — a new 154-line JSONL permanent storage module implementing two append-only logs (`reading-log.jsonl` and `project-log.jsonl`) with 10 functions for append, read-all, and filtered-read operations. The file correctly uses `secrets.token_hex` for collision-resistant ID generation, handles write-side OSError, and gracefully skips malformed JSON lines on read.

Four WARNING-level issues were found, primarily around schema inconsistency with the corresponding SQL tables defined in `paperforge/memory/schema.py` (added in the immediately prior commit 5493e28). The JSONL field names for `project_log` diverge from the SQL column names (`entry_type` vs `type`, `content` vs `title`), the `reading_log` is missing the `verified` field present in SQL, and `append_project_entry` lacks input validation. The module also has no tests and no consumers — it is not imported anywhere in the codebase.

No BLOCKER issues were found: the code is free of crashes, data loss, and security vulnerabilities.

## Warnings

### WR-01: Schema field name mismatch — project_log JSONL vs SQL

**File:** `paperforge/memory/permanent.py:114-133`
**Issue:** The JSONL `append_project_entry` records use field names that differ from the SQL `project_log` table defined in `paperforge/memory/schema.py` (lines 158-173):

| JSONL (permanent.py) | SQL (schema.py) |
|-----------------------|-----------------|
| `entry_type`          | `type`          |
| `content`             | `title`         |
| *(none)*              | `date` (NOT NULL) |

`append_project_entry` also lacks a `date` field entirely — the SQL schema requires `date TEXT NOT NULL`. The `reading_log` tables match more closely but still diverge in one column (see WR-02).

These two commits (5493e28 for the SQL tables, 0d1ca3a for JSONL) appear related. Inconsistent field names will cause confusion and potential data corruption when any bridge/migration code is written between the two storage backends.

**Fix:** Align the JSONL field names with the SQL schema. Either:
1. Rename JSONL fields to match SQL (`entry_type` → `type`, `content` → `title`, add `date` field), or
2. Rename the SQL columns to match JSONL (if the SQL schema has not yet been deployed).

Example aligned implementation for `append_project_entry`:
```python
record: dict[str, object] = {
    "id": entry_id,
    "created_at": now,
    "project": entry.get("project", ""),
    "date": date_str,                    # ADDED — matches SQL NOT NULL
    "type": entry.get("type", ""),       # RENAMED from entry_type
    "title": entry.get("title", ""),     # RENAMED from content
    "content": entry.get("content", ""), # KEEP for backward compat, or remove
    "status": entry.get("status", ""),
    ...
}
```

### WR-02: Missing `verified` field in reading_log JSONL entries

**File:** `paperforge/memory/permanent.py:32-76`
**Issue:** The SQL `reading_log` table (schema.py line 140-155) includes a `verified INTEGER DEFAULT 0` column, but the JSONL `append_reading_note` function (lines 53-65) never emits this field. If data is ever migrated between JSONL and SQL, verification status will be silently dropped.

**Fix:** Add `verified` to the entry dict with a default of `0` (or make it a parameter):
```python
entry: dict[str, object] = {
    ...
    "verified": 0,    # ADDED — matches SQL schema
}
```

### WR-03: Missing input validation on `append_project_entry`

**File:** `paperforge/memory/permanent.py:114-144`
**Issue:** `append_reading_note` validates that `paper_id` and `excerpt` are non-empty before writing (lines 44-47). However, `append_project_entry` performs zero validation — it accepts an empty dict, producing a record where all fields default to empty strings/lists. By contrast, the parallel SQL `project_log` table enforces `NOT NULL` constraints on `project`, `date`, `type`, and `title`.

This inconsistency means the JSONL can accumulate garbage rows that would be rejected by the SQL backend. It also silently swallows caller errors where a required field was omitted.

**Fix:** Add validation for the fields that are semantically required:
```python
def append_project_entry(vault: Path, entry: dict) -> dict:
    project = entry.get("project", "")
    entry_type = entry.get("entry_type", "")
    if not project:
        return {"ok": False, "error": "project is required"}
    if not entry_type:
        return {"ok": False, "error": "entry_type is required"}
    # ... rest of function
```

### WR-04: No tests for the new module

**File:** `paperforge/memory/permanent.py` (entire file)
**Issue:** Zero tests exist for this module. The `tests/unit/memory/` directory has 6 test files (test_builder.py, test_context.py, test_query.py, test_refresh.py, test_schema.py, __init__.py) but none cover `permanent.py`. No entry in the integration or chaos test suites either.

With 10 functions covering two distinct log types, validation logic, error handling, and JSONL line format, the absence of tests means:
- ID uniqueness (`secrets.token_hex`) is untested
- Unicode handling (`ensure_ascii=False`) is untested
- Malformed JSON skipping is untested
- Empty-string validation is untested
- OSError recovery on write is untested
- Filtering (`get_reading_notes_for_paper`, `get_project_entries`) correctness is untested

**Fix:** Create `tests/unit/memory/test_permanent.py` covering at minimum:
- `append_reading_note` / `append_project_entry` happy path
- Validation rejection (empty paper_id, empty excerpt)
- Round-trip: append then read-all
- Filtered reads (`get_reading_notes_for_paper`, `get_project_entries`)
- Malformed JSONL line skipping
- Unicode content preservation

## Info

### IN-01: Inline filepath construction bypasses `get_*_log_path` helpers

**File:** `paperforge/memory/permanent.py:68, 136`
**Issue:** Both `append_reading_note` and `append_project_entry` construct the filepath inline (`log_dir / "reading-log.jsonl"`) instead of calling `get_reading_log_path(vault)` and `get_project_log_path(vault)` which are defined directly above them. This duplicates the path logic and creates a risk of divergence if the path is ever changed in only one place.

**Fix:** Replace:
```python
log_dir = _ensure_logs_dir(vault)
filepath = log_dir / "reading-log.jsonl"
```
with:
```python
filepath = _ensure_logs_dir(vault) / "reading-log.jsonl"
```
Or preferably, use the dedicated helpers:
```python
filepath = get_reading_log_path(vault)
_ensure_logs_dir(vault)  # ensure directory exists
```

### IN-02: No module-level docstring

**File:** `paperforge/memory/permanent.py:1-11`
**Issue:** The file lacks a module docstring. Other modules in the `paperforge/memory/` package describe their purpose and usage. A docstring would help future developers understand that this is a JSONL append-only log (not a queryable database) and why it exists alongside the SQL tables.

**Fix:** Add a module docstring:
```python
"""Permanent JSONL storage layer for reading-log and project-log.

Provides append-only JSONL persistence as an append-only archival backend
alongside the query-oriented SQL tables.  Each log entry is written as a
single JSON line with a unique, collision-resistant ID generated via
``secrets.token_hex``.

All write functions return ``{"ok": True/False, ...}`` dicts.
Read functions return ``list[dict]`` with malformed lines silently skipped.
"""
```

### IN-03: `append_reading_note` does not validate `section` for emptiness

**File:** `paperforge/memory/permanent.py:32-76`
**Issue:** `paper_id` and `excerpt` are validated as non-empty (lines 44-47), but `section` — a required positional parameter with no default — is not validated. The SQL `reading_log` schema also marks `section` as `TEXT NOT NULL` without a default. An empty `section` value would pass through silently and create an entry that's difficult to query or filter by section.

**Fix:** Add a validation check:
```python
if not section:
    return {"ok": False, "error": "section is required"}
```

### IN-04: Module not exported from `paperforge/memory/__init__.py`

**File:** `paperforge/memory/__init__.py`
**Issue:** The package `__init__.py` exports `get_connection`, `get_memory_db_path`, `ensure_schema`, and `drop_all_tables` — all SQL/db-related. The new `permanent` module is not re-exported, and no other module in the codebase imports it (`grep` returned zero results for `from paperforge.memory.*permanent`). This means the 154 lines of code are dead code until a consumer is wired in.

**Fix:** Add the key functions to the package's public API, or document in a follow-up task which command/worker will consume this module.

---

_Reviewed: 2026-05-14_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
