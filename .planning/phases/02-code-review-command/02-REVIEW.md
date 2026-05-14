---
phase: 02-code-review
reviewed: 2026-05-14T12:00:00Z
depth: deep
files_reviewed: 1
files_reviewed_list:
  - paperforge/memory/schema.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-14T12:00:00Z
**Depth:** deep
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed Task 1 implementation: addition of `CREATE_READING_LOG` and `CREATE_PROJECT_LOG` SQL table definitions to `paperforge/memory/schema.py`. The implementation faithfully follows the plan specification with correct SQL syntax, proper registration in `ensure_schema()`, correct `ALL_TABLES` inclusion, and `CURRENT_SCHEMA_VERSION` bumped from 1 to 2. All 5 existing schema unit tests pass. No critical defects were introduced.

However, three warnings were identified: (1) the foreign key from `reading_log` to `papers` will create a deletion-ordering conflict in `builder.py` once the table is populated (future Task 6 concern), (2) the column name `date` in `project_log` shadows a SQLite built-in function name, and (3) the foreign key column `reading_log.paper_id` lacks an index, which will cause full table scans on lookup queries.

## Warnings

### WR-01: Foreign Key Will Block `DELETE FROM papers` During Rebuild

**File:** `paperforge/memory/schema.py:153` (FK definition), `paperforge/memory/builder.py:84` (DELETE caller)

**Issue:** The `reading_log` table defines `FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)` without `ON DELETE CASCADE`. During non-schema-change rebuilds in `builder.py`, the code executes `DELETE FROM papers` (line 84) WITHOUT first clearing `reading_log`. Once Task 6 populates `reading_log` from JSONL, this DELETE will fail with an `IntegrityError` because SQLite enforces foreign key constraints on DML operations when `PRAGMA foreign_keys=ON` (which `db.py:34` explicitly enables).

Currently latent because `reading_log` is never populated (Task 6 has not been implemented). Will surface during the Task 6 rebuild flow.

**Fix:**

In `builder.py`, clear `reading_log` (and `project_log`) before deleting `papers`:

```python
# In builder.py, before the DELETE FROM papers (line 84), add:
conn.execute("DELETE FROM reading_log;")
conn.execute("DELETE FROM project_log;")
```

Alternatively, add `ON DELETE CASCADE` to the foreign key definition in `schema.py`:
```python
FOREIGN KEY (paper_id) REFERENCES papers(zotero_key) ON DELETE CASCADE
```

The first approach (explicit DELETE) is preferred because it makes the rebuild flow explicit and doesn't silently cascade deletions that could surprise maintainers.

---

### WR-02: Column Name `date` Shadows SQLite Built-in Function

**File:** `paperforge/memory/schema.py:161`

**Issue:** The `project_log` table uses `date` as a column name (line 161: `date TEXT NOT NULL`). While syntactically valid in SQLite (which allows function names as unquoted identifiers), `date` is a built-in SQL function. This creates ambiguity when reading queries — `SELECT date FROM project_log` works but `SELECT date(created_at) FROM project_log` is ambiguous. More importantly, if this schema is ever ported to another SQL dialect (PostgreSQL, MySQL), `date` is a reserved word and will require quoting.

**Fix:**

Rename the column to `log_date`, `entry_date`, or `recorded_date`:

```sql
-- In CREATE_PROJECT_LOG:
log_date  TEXT NOT NULL,
```

Note: This would also require updating the plan's Task 2 (`permanent.py`) and Task 6 (`builder.py`) where the column is referenced. If changing the schema column name is too invasive for this phase, consider adding a comment noting the potential ambiguity.

---

### WR-03: Missing Index on Foreign Key Column `reading_log.paper_id`

**File:** `paperforge/memory/schema.py:142`

**Issue:** The `reading_log` table has a foreign key on `paper_id` (line 142), but no index is created for this column. All queries filtering by `paper_id` (e.g., `get_reading_notes_for_paper()` in `permanent.py`, paper-context lookup) will require full table scans. As the reading log grows, this will degrade query performance.

**Fix:**

Add an index alongside the existing `EVENT_INDEX_SQL` block (following the established pattern in the file):

```python
# After EVENT_INDEX_SQL (line 137), add:
READING_LOG_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_reading_log_paper ON reading_log(paper_id);",
    "CREATE INDEX IF NOT EXISTS idx_reading_log_project ON reading_log(project);",
    "CREATE INDEX IF NOT EXISTS idx_reading_log_created ON reading_log(created_at);",
]
```

And register in `ensure_schema()` after the `EVENT_INDEX_SQL` loop:

```python
for idx_sql in READING_LOG_INDEX_SQL:
    conn.execute(idx_sql)
```

Also add a project-level index for `project_log`:

```python
PROJECT_LOG_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_project_log_project ON project_log(project);",
    "CREATE INDEX IF NOT EXISTS idx_project_log_created ON project_log(created_at);",
]
```

---

## Info

### IN-01: Test Hardcodes Stale Schema Version

**File:** `tests/unit/memory/test_schema.py:73`

**Issue:** The test `test_get_schema_version_returns_stored_value` inserts `schema_version = '1'` and asserts the returned value equals 1. Since `CURRENT_SCHEMA_VERSION` was bumped to 2, the hardcoded '1' no longer matches the current version. While the test is verifying read-back behavior (not version equality), the stale value could confuse future maintainers who assume the test reflects the current schema version.

**Fix:**

Either update to a version-independent test or clarify with a comment:

```python
# Test uses arbitrary version '1' for read-back verification (not tied to CURRENT_SCHEMA_VERSION)
conn.execute(
    "INSERT INTO meta (key, value) VALUES ('schema_version', '1')"
)
conn.commit()
assert get_schema_version(conn) == 1
```

---

### IN-02: `ALL_TABLES` Ordering — Child Tables After Parent (Latent DDL Risk)

**File:** `paperforge/memory/schema.py:175`

**Issue:** The `ALL_TABLES` list orders `papers` (index 1) before its child tables `paper_assets`, `paper_aliases`, `paper_events`, and now `reading_log` (indices 2-7). In `drop_all_tables()`, SQLite with `PRAGMA foreign_keys=ON` will reject `DROP TABLE papers` if any child table contains rows referencing papers. This is currently benign because `drop_all_tables()` is only called when schema versions mismatch — at which point the new `reading_log` table hasn't been populated yet. However, if `drop_all_tables` is ever called on a populated database, the ordering would cause a failure.

**Fix (if desired — pre-existing, not introduced by this change):**

Reorder `ALL_TABLES` so child tables (FK-referencing) appear before parent tables (FK-referenced):

```python
ALL_TABLES = ["paper_fts", "reading_log", "project_log", "paper_events", "paper_aliases", "paper_assets", "papers", "meta"]
```

Note: `paper_fts` is a virtual table and cannot have FK constraints, so its position is flexible.

---

_Reviewed: 2026-05-14T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
