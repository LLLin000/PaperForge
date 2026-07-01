# OCR-v2 Active Queue
> Status: ACTIVE QUEUE — Asset-internal figure number recovery implemented. 428 regression tests pass.
> Last updated: 2026-07-01
> Scope: post-audit cleanup

## Current Priorities
1. **Monitor production OCR** after rotated-figure prematch refactor + asset-internal recovery
2. **Archive stale `project/current/` files**
3. **Group-first figure inventory refactor** (deferred)

## Completed This Session (cumulative)
- **Asset-internal figure number recovery**
  - add `extract_pdf_lines_normalized` helper to ocr_pdf_spans.py
  - add `_recover_missing_figure_numbers_from_assets` pass + 5 gate functions + 2 pattern constants
  - broadened gate to support `figure_unknown_NNN` figures from normal prematch
  - wired in ocr_rebuild.py: build and pass `page_pdf_lines_by_page` to inventory builder
  - U746UJ7G verified: `figure_unknown_000` → `figure_002` with recovered label "Plot of Criteria Time"
  - 6 new tests, 428 regression tests pass

## Cross-Links
- Narrative ledger: `PROJECT-MANAGEMENT.md` (§9.19)
- Evidence source: `project/current/ocr_rebuild_audit.md`
- Architecture boundary: `project/current/ocr-v2-generalization-boundary.md`
