# OCR-v2 Active Queue
> Status: ACTIVE QUEUE — Four-layer release readiness. Layer 2 delivered. 1278 tests green on `master`.
> Last updated: 2026-07-05
> Scope: UI polish → downstream tools

## Current Priorities
1. ✅ **Workstream X: Layout-category truth audit** — 11 papers, 6 bug patterns. Report in `docs/superpowers/analysis/2026-07-05-layout-truth-audit-findings.md`
2. ✅ **Layer 2: OCR Quality Report + Readiness Policy** — `build_quality_indicators()`, `evaluate_readiness()`, human feedback sidecar. Contract polished at commit `96fd9771`.
3. 🟡 **Plugin UI polish** — dashboard cleanliness, maintenance display
4. 🟡 **Downstream tooling** — section-aware vector chunking, figure/table separate handling

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
  - Result: **105 passed, 0 failed**
- **Layer 2: OCR Quality Report + Readiness Policy**:
  - Added `paperforge/worker/ocr_quality.py` — `build_quality_indicators()` with 5 normalizers
  - Added `paperforge/worker/ocr_quality_feedback.py` — human feedback sidecar (per-mark hash, stale detection)
  - Added `paperforge/policies/ocr_readiness_v1.yaml` — default readiness policy (weights, hard-red, use-case gates)
  - Added `evaluate_readiness()` — policy evaluator with deep-merge, user override bypass
  - Contract polish: `status/gates/reasons` output shape, hash validation, non-mutating append
  - 22 new tests (17 quality + 5 feedback), 1278 total green
  - Master commit: `96fd9771`

## Immediate Next Checks
- [ ] Send 6 bug patterns to GPT for solution design
- [ ] Fix 37LK5T97 two-column figure 1 bug (Round 2 RED)
- [ ] Archive stale queue docs from pairing-framework phase
