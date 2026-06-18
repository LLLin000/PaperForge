# Plan 03-03 Summary: Annotation List/Status/Export JSON Contracts

**Date:** 2026-06-18
**Status:** ✓ Complete

## Objective

Implement read-only annotation CLI commands: `list`, `status`, and `export` — all backed by real `annotations.db` queries.

## Deliverables

| Artifact | Status |
|----------|--------|
| `paperforge/commands/annotation.py` — `_cmd_list`, `_cmd_status`, `_cmd_export` with real DB queries | ✓ Done |
| `tests/cli/test_annotation_read_json.py` — 8 contract tests | ✓ Done (8 pass) |

## Test Results

```
tests/cli/test_annotation_read_json.py ........ [100%] 8 passed
tests/cli/test_annotation_import_json.py ...... [100%] 8 passed
tests/cli/test_annotation_command_shape.py .... [100%] 7 passed
Total: 23 annotation CLI tests pass
```

## Implementation Details

### `status --json`
- Opens `annotations.db` read-only via `get_annotations_connection(read_only=True)`.
- Returns: `db_path`, `schema_version`, `total_annotations`, `source_counts`, `readonly_count`, `deleted_count`, `db_available`, `total_papers_with_annotations`.
- Absent DB → returns `db_available: false` with zero counts (not an error).
- SQL: `COUNT(*)`, `GROUP BY source`, `COUNT(DISTINCT paper_id)`.

### `list --paper KEY --json`
- Requires `--paper`; returns `VALIDATION_ERROR` if missing.
- Queries non-deleted rows (`deleted_at IS NULL`) for the paper.
- Order: `page_index`, `sort_index`, `id`.
- Returns lightweight scan fields: `id, type, page, page_label, selected_text, comment, color, source, is_readonly`.
- Absent DB → returns empty annotation list (not an error).

### `export --paper KEY --json`
- Requires `--paper`; returns `VALIDATION_ERROR` if missing.
- Queries ALL rows (including soft-deleted) for the paper.
- Returns full payload: all columns, plus `format_version: "1.0"`.
- Absent DB → returns empty export (not an error).

### DB Helpers Extracted
- `_open_annotations_db(args)` — opens read-only connection or returns None.
- `_require_paper(args, command)` — validates `--paper` param, returns JSON error if missing.
- `_rows_to_list(rows)` — lightweight format.
- `_rows_to_export(rows)` — full field format.

### Error Handling
- All `--json` failures use `PFResult` envelope with stable `ErrorCode`.
- Non-JSON text mode is minimal but never tracebacks.
- DB absence is handled gracefully (empty state, not a crash).

## Commit

`<pending>`
