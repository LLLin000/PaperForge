# Phase 37: Frontmatter Rationalization — Summary

**Status:** Complete ✅
**Requirements:** FM-01 through FM-07 — all verified

## One-Liner
Slimmed formal note frontmatter from 28 to 16 fields, created per-workspace paper-meta.json for internal state, removed library_record_markdown().

## Key Deliverables
- `frontmatter_note()` produces 16-field frontmatter: identity (title/year/journal/first_author/zotero_key/domain/doi/pmid/collection_path/impact_factor/abstract/tags) + workflow (has_pdf/do_ocr/analyze/ocr_status/deep_reading_status) + pdf_path
- `paper_meta.py` — new module writing per-workspace paper-meta.json with OCR jobs, health, maturity, paperforge_version
- `_build_entry()` enhanced with do_ocr/analyze/first_author/impact_factor fields
- `library_record_markdown()` removed — no new library-record .md files generated
- `run_selection_sync()` no longer creates library-records

## Verification
- 188 tests pass (asset_index, migration, e2e, base_views, etc.)
- `grep "library_record_markdown" paperforge/` returns zero results
