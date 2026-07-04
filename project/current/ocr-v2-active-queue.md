# OCR-v2 Active Queue
> Status: ACTIVE QUEUE — A/B/C OCR deepening pass merged to `master`; legacy path remains default, `OCR_PIPELINE_V3` is merged but OFF by default. Focused suite + fixture-backed parity gate: 100 tests green on `master`.
> Last updated: 2026-07-04
> Scope: post-merge stabilization / v3 parity follow-up

## Current Priorities
1. **Monitor merged `master`** for any default-path OCR regressions after the A/B/C merge
2. **Broaden fixture-backed real-paper parity for `OCR_PIPELINE_V3=1`** beyond the first `DWQQK2YB` replay gate before considering any default-on change
3. **Update / archive stale `project/current/` files** that still point to pre-merge pairing-framework work
4. **Compatibility naming cleanup** (`figure_no` / `legend` / `FigurePipelineState`) — still deferred

## Completed This Session (cumulative)
- **Workstream A — object writeback seam**:
  - Added `paperforge/worker/ocr_object_writeback.py`
  - Unified figure/table asset writeback, contained text, side-adjacent text, and consumed-block ownership evidence
  - Added `tests/test_ocr_object_writeback.py`
- **Workstream B — tail settlement seam**:
  - Added `paperforge/worker/ocr_tail_settlement.py`
  - Added `TailSettlementReport` and attached it to `DocumentStructure`
  - Preserved legacy tail/body/backmatter behavior with focused regressions
- **Workstream C — v3 pre/post normalize split**:
  - Added `paperforge/worker/ocr_pre_match_normalize.py`
  - Added `paperforge/worker/ocr_post_match_normalize.py`
  - Added `OCR_PIPELINE_V3` toggle and `normalize_mode="seed_only"`
  - Updated figure/table matching to accept `role_candidate > role > seed_role`
- **Pre-merge blocker cleanup**:
  - Fixed page-qualified object writeback lookup
  - Guarded contained figure claims by page
  - Restored rescue equivalence inside `post_match_normalize()`
  - Added merge-gate regression tests for all four blockers
- **Verification**:
  - `tests/test_ocr_pipeline_v3.py`
  - `tests/test_ocr_tail_settlement.py`
  - `tests/test_ocr_object_writeback.py`
  - `tests/test_appendix_figure_numbering.py`
  - `tests/test_ocr_rendering.py`
  - Result: **100 passed, 0 failed**

## Immediate Next Checks
- [x] Merge `feat/ocr-tail-settlement` into `master`
- [x] Push merged `master`
- [x] Add first fixture-backed `OCR_PIPELINE_V3` real-paper parity gate (`DWQQK2YB`)
- [ ] Broaden fixture-backed v3 parity beyond one replay fixture
- [ ] Decide whether `post_match_normalize()` rescue equivalence is sufficient or still needs corpus proof
- [ ] Archive or rewrite stale queue docs from the pairing-framework phase
