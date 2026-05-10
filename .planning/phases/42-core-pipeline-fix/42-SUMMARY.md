# Phase 42: Core Pipeline Fix - Summary

**Status:** Complete ✅
**Tests:** 181 passed, 2 skipped, 1 pre-existing failure
**Date:** 2026-05-07

## Changes

### `sync.py`
- `load_control_actions()` rewritten to scan Literature/ formal note frontmatter (not library-records)
- `run_selection_sync()` no longer creates empty library-records domain directories
- Orphan cleanup targets Literature/ directory (not library-records)

### `ocr.py`
- `auto_analyze_after_ocr` writes `analyze: true` to formal note frontmatter (not library-record)

### `status.py`
- `run_status()` counts do_ocr, path errors, and records from formal notes + canonical index
- Doctor checks (`check_pdf_paths`, `check_wikilink_format`) sample from formal notes

### Tests
- `conftest.py` updated: formal note fixtures now carry workflow frontmatter fields
