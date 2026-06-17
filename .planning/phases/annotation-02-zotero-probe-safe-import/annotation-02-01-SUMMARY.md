---
phase: annotation-02-zotero-probe-safe-import
plan: 01
type: execute
wave: 1
subsystem: annotation
tags:
  - zotero-probe
  - safe-import
  - tdd
  - sqlite-snapshot
requires:
  - paperforge/annotation/db.py (Phase 1 — connection patterns)
  - paperforge/annotation/schema.py (Phase 1 — annotations schema)
provides:
  - paperforge/annotation/errors.py (structured domain errors)
  - paperforge/annotation/zotero_probe.py (snapshot/probe/fetch helpers)
affects:
  - Plan 02 — will consume probe helpers for normalization
  - Plan 03 — will consume probe helpers for scoped import
tech-stack:
  added:
    - sqlite3 URI mode=ro for read-only connections
    - tempfile + shutil.copy2 for atomic snapshot
  patterns:
    - contextlib.contextmanager for snapshot lifecycle
    - sqlite3.Row row factory for dict-like row access
key-files:
  created:
    - paperforge/annotation/errors.py
    - paperforge/annotation/zotero_probe.py
    - tests/unit/annotation/test_zotero_probe.py
decisions:
  - D-04: Zotero access defaults to temp-copy mode (enforced)
  - D-05: Zotero DB path from explicit input, never hardcoded (enforced)
  - D-08: Probe failures use structured domain errors (enforced)
  - SAFE-04: No function writes to Zotero SQLite (verified)
metrics:
  duration_minutes: 8
  completed_date: "2026-06-18"
  tests_total: 10
  tests_passed: 10
  tests_failed: 0
  files_created: 3
  files_modified: 0
commits:
  - dcb83ef: test(annotation-02-01): add failing Zotero probe tests
  - 8c122dc: feat(annotation-02-01): implement structured errors and Zotero probe helpers
---

# Phase annotation-02 Zotero Probe & Safe Import Plan 1: Zotero Probe Foundation

**One-liner:** Created the safe Zotero SQLite snapshot/probe foundation — temp-copy context manager, read-only opener via SQLite URI mode=ro, schema validator against required Zotero annotation tables, and a narrow raw fetch helper — with 10 passing TDD tests covering safety, errors, and schema discovery.

## Results

| Metric | Value |
|--------|-------|
| Tests total | 10 |
| Tests passed | 10 |
| Tests failed | 0 |
| Files created | 3 |
| TDD compliance | RED→GREEN gate verified (dcb83ef = failing import, 8c122dc = all pass) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Robustness] Windows PermissionError on snapshot cleanup**

- **Found during:** Task 2 (GREEN verification)
- **Issue:** When `probe_zotero_annotation_schema` raises `ZoteroSchemaError`, the exception propagates while the `sqlite3.Connection` (`conn2`) still holds a file lock on the snapshot. On Windows, `zotero_snapshot`'s `finally: snapshot_path.unlink()` fails with `PermissionError` because the file is still open.
- **Fix:** Restructured `test_missing_table_raises_zotero_schema_error` and `test_missing_column_raises_zotero_schema_error` to close `conn2` **before** the `zotero_snapshot` context manager's cleanup runs. Used `pytest.raises` as an inner context inside `zotero_snapshot`, not wrapping it, so the connection close happens before the outer `with` block exits.
- **Files modified:** `tests/unit/annotation/test_zotero_probe.py`
- **Commit:** `8c122dc`

**2. [Rule 2 - Correctness] `test_missing_table_raises_zotero_schema_error` fixture had incomplete `items` table**

- **Found during:** Task 2 (GREEN verification)
- **Issue:** The test's `items` table only had `itemID` and `key`, but the probe's `REQUIRED_ZOTERO_TABLES` also expects `dateModified`. This caused `probe_zotero_annotation_schema` to raise a **column**-missing error instead of the expected **table**-missing error.
- **Fix:** Added `dateModified` column to the `items` CREATE TABLE in the test fixture, so the table-level check is cleanly tripped by the missing `itemAnnotations` table.
- **Files modified:** `tests/unit/annotation/test_zotero_probe.py`
- **Commit:** `8c122dc`

**3. [Rule 2 - Correctness] `test_missing_column_raises_zotero_schema_error` had SQLite syntax error**

- **Found during:** Task 2 (GREEN verification)
- **Issue:** The CREATE TABLE contained a `--` SQL comment inside a multi-line string, which SQLite rejected as `incomplete input`.
- **Fix:** Removed the inline comment.
- **Files modified:** `tests/unit/annotation/test_zotero_probe.py`
- **Commit:** `8c122dc`

## Verification

- `python -m pytest tests/unit/annotation/test_zotero_probe.py -q` → 10 passed
- `python -m compileall paperforge/annotation` → no errors
- Full annotation test suite: `28 passed, 1 skipped` (pre-existing skip, unchanged)

## Success Criteria

| Criterion | Status |
|-----------|--------|
| Missing/unreadable Zotero DB paths produce structured errors | ✓ `ZoteroDatabaseError` raised by `zotero_snapshot()` and `open_zotero_readonly()` |
| Unknown/missing annotation schema produces structured errors | ✓ `ZoteroSchemaError` raised by `probe_zotero_annotation_schema()` with table/column details |
| Zotero DB access copies to a temporary snapshot by default | ✓ `zotero_snapshot()` copies via `shutil.copy2` |
| Snapshot is opened read-only and cleaned up | ✓ URI mode=ro+immutable; `unlink()` in finally block |
| No Zotero write-back or live SQLite mutation path | ✓ Verified: no INSERT/UPDATE/DELETE/DROP against source Zotero DB |

## Key Decisions Made

1. **REQUIRED_ZOTERO_TABLES as minimum schema** — The probe validates a minimal set of tables/columns needed for annotation import. Extra columns in the live DB are ignored (not required, not forbidden). This matches Zotero 6/7 internal schema while allowing forward/backward compatibility.

2. **`open_zotero_readonly` adds `&immutable=1`** — Beyond `mode=ro`, also set `immutable=1` in the SQLite URI to prevent any shared-cache locks on what is already a temp snapshot.

3. **Error classes carry structured fields** — `ZoteroDatabaseError` has `db_path` and `original_error`; `ZoteroSchemaError` has `table_name` and `column_name`. This gives CLI code enough context to produce stable JSON and Chinese messages without re-parsing the message string.

## Threat Flags

None. The implementation is read-only probe/snapshot code with no network endpoints, auth paths, file access beyond the explicit `db_path` argument, or schema mutations.

## Self-Check: PASSED

```
FOUND: paperforge/annotation/errors.py
FOUND: paperforge/annotation/zotero_probe.py
FOUND: tests/unit/annotation/test_zotero_probe.py
FOUND: dcb83ef
FOUND: 8c122dc
```

All created files exist on disk. Both commit hashes are present in git log.
