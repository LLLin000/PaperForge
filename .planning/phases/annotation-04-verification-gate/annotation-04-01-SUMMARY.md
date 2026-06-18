---
phase: annotation-04-verification-gate
plan: 01
type: summary
status: complete
completed: 2026-06-18
commit: 12b8e35
wave: 1
---

# Plan 01 — Generated Fixture and Service Verification Foundation

## What Was Done

### Fixture Consolidation (`conftest.py` — new file)

Created `tests/unit/annotation/conftest.py` with runtime-generated Zotero SQLite fixture helpers, satisfying TEST-01 coverage requirements:

- **`build_zotero_two_paper`** — Two papers (A + B), each with PDF attachments and annotations including tags and position JSON. Used by flow tests.
- **`build_zotero_unknown_schema`** — SQLite file with no Zotero annotation tables. Used for schema-error tests.
- **`build_zotero_fixture_full`** — Multiple papers, libraries, and attachments. Used by importer tests.
- **`build_zotero_fixture_reduced`** — Same as `full` but missing one annotation row. Used for stale-detection tests.
- **`open_ann()`** — Shared helper for opening `annotations.db` with `sqlite3.Row` factory.
- **Temp-file fixtures** — `zotero_two_paper_path`, `zotero_unknown_schema_path`, `zotero_full_path`, `zotero_reduced_path`, `ann_db_path`.

### Refactored `test_importer.py`

Removed ~240 lines of duplicated fixture builders (`_create_zotero_fixture_full`, `_create_zotero_fixture_reduced`, `_open_ann`, inline fixture definitions) that now live in `conftest.py`. All imports redirected to `from .conftest import open_ann`.

### Fixed `test_zotero_import_flow.py`

- Added missing `import pytest`
- Fixed `_open_ann()` → `open_ann()` (wrong function name)
- Fixed `_PAPER_A_*` → `PAPER_A_*` (wrong constant prefix)
- These bugs caused `NameError` exceptions that were masked by Windows `PermissionError` during snapshot cleanup

### Service Contract Tests (`test_service_contracts.py` — new file)

17 tests covering lower-level read behavior behind `annotation list/status/export`:

| Area | Tests | Coverage |
|------|-------|----------|
| Paper filtering | 3 | List/export return only requested paper; no intersection between papers |
| Ordering stability | 2 | Results ordered by page_index, sort_index, id for both list and export |
| Deleted-row behaviour | 3 | List excludes deleted; export includes deleted; status counts deleted |
| Provenance fields | 2 | Export includes all provenance; list scan omits detail fields |
| Row helper contract | 3 | _rows_to_list/_rows_to_export produce correct keys; is_readonly boolean |
| Source counts | 3 | GROUP BY source, readonly count, distinct paper count |

## Verification

- `python -m pytest tests/unit/annotation/ -q` → **88 passed, 1 skipped** (skipped test is pre-existing FTS5 availability check)
- Python compile check: clean

## Success Criteria

- [x] Generated SQLite fixtures satisfy parent paper, PDF attachment, and multiple annotation row coverage
- [x] Fixture helpers are shared enough to avoid obvious drift (conftest.py is the single source)
- [x] Service/list/export/status behavior is covered below the CLI layer
- [x] Paper-scoped stale deletion regression is explicit (test name: `test_flow_reimport_does_not_stale_other_paper`)
