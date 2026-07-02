# OCR-v2 Active Queue
> Status: ACTIVE QUEUE — Round 2 truth audit + 3 targeted bug fixes. 428 regression tests pass.
> Last updated: 2026-07-02
> Scope: post-audit cleanup

## Current Priorities
1. **Monitor production OCR** after rotated-figure prematch, asset-internal recovery, sidecar/table fixes
2. **Archive stale `project/current/` files**
3. **Group-first figure inventory refactor** (deferred)

## Completed This Session (cumulative)
- **Round 2 truth audit**: 10 new papers batch-audited via ocr_truth_audit.py (high-risk mode)
  - 5 GREEN / 4 YELLOW / 1 RED (37LK5T97 — Figure 1 broken, tables unmatched)
  - 2 vision agents dispatched for RED papers
  - Findings: `docs/superpowers/specs/2026-07-02-ocr-truth-audit-round2-findings.md`
- **37LK5T97 Figure 1 sidecar fix** (ocr_document.py)
  - Add `_is_sidecar_candidate` guard in candidate_resolution demotion
  - Sidecar caption in adjacent column no longer demoted as narrative prose
  - Figure 1 matched: `figure_001`, asset=block_id=9
- **37LK5T97 rotated table matching fix** (ocr_scores.py)
  - Add `adjacent_x` + `y_overlap_with_asset` checks in score_table_match for rotated captions
  - All 6 tables matched with has_asset=true
- **37LK5T97 rotated table render fix** (ocr_tables.py, ocr_objects.py)
  - `_table_has_rotated_content` detects dir=[0,-1], computes union render_bbox + rotation_deg=270
  - Tables 1-5 rendered at correct orientation (1908×2858 → 2858×1908)
  - Same approach as rotated figure rendering
- Git: commits `16f9403` (recovery), `59cd01a` (figure quality), `bd3f3b6` (sidecar+table match), `86e0d14` (table render)
