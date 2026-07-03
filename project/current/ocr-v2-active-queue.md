# OCR-v2 Active Queue
> Status: ACTIVE QUEUE — OCR pairing framework branch is merge-ready after merge-unblock verification. 357 targeted tests pass.
> Last updated: 2026-07-03
> Scope: pairing framework integration / post-merge follow-up

## Current Priorities
1. **Merge `feat/ocr-pairing-framework`** back to `master`
2. **Monitor production OCR** after pairing-core unification (figure + table on shared framework)
3. **Archive stale `project/current/` files**
4. **Compatibility naming cleanup** (`figure_no` / `legend` / `FigurePipelineState`) — deferred

## Completed This Session (cumulative)
- **Pairing framework extraction**:
  - Shared `ocr_pairing_types.py`, `ocr_pairing_state.py`, `ocr_pairing_framework.py`
  - Figure pipeline migrated onto shared core without changing public seam
- **Table pipeline migration**:
  - Added `ocr_table_domain.py` + ordered `ocr_table_passes.py`
  - `build_table_inventory(...)` now routes to table vnext on shared core
- **Merge-unblock hardening**:
  - Generic-state figure rotation enrichment moved behind figure-only `_match_pre_enricher`
  - Table semantic parity validation upgraded across 6 runnable real-paper fixtures
  - Added runnable `tests/fixtures/ocr_vnext_real_papers/37LK5T97/blocks.structured.jsonl`
  - Touched-file `ruff check` / `ruff format --check` green
- **Verification**:
  - `tests/test_ocr_figures.py`
  - `tests/test_ocr_rebuild.py`
  - `tests/test_ocr_tables.py`
  - `tests/test_ocr_pairing_framework.py`
  - `tests/test_ocr_table_pairing_framework.py`
  - Result: **357 passed, 0 failed**
