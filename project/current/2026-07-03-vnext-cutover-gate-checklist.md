# VNext Cutover Gate Checklist — 2026-07-03

## Gate 1 — Contract Compatibility
- [x] `build_figure_inventory(structured_blocks, page_width=1200) -> dict` preserved
- [x] All 8 core fields present: `matched_figures`, `unmatched_legends`, `unmatched_assets`, `unresolved_clusters`, `rejected_legends`, `held_figures`, `ambiguous_figures`, `local_pairing_hypotheses`
- [x] Legacy-only keys are additive (present in legacy output, not required by downstream)
- [x] VNext-only keys are additive (present in vnext output, not consumed by legacy downstream)

## Gate 2 — Regression Suite
- [x] `test_ocr_figure_vnext_*.py`: **59 passed**
- [x] `test_ocr_figures.py + test_ocr_render.py`: **290 passed**
- [x] Total: **349 passed, 0 failed**
- [x] Legacy path unchanged (wrapper still calls legacy)

## Gate 3 — Real-Paper Diff Review
- [x] **5-paper corpus** covering all 9 spec §8.3 categories
- [x] **0 regressions** — consumed block IDs identical across all 5 papers
- [x] **Verdicts:** improvement=2, equivalent=2, parity=1
- [x] No previously confident figure disappears without explanation
- [x] No owned asset appears in unresolved clusters
- [x] No figure card consumes the same asset twice
- [x] Diff review documented: `project/current/2026-07-03-vnext-cutover-diff-review.md`

## Gate 4 — Diagnostics Superiority
- [x] Claim journal: `OwnershipLedger.snapshot()` via `state.ledger._journal`
- [x] Ownership conflict explanation: `PassReport.conflicts` array
- [x] Pass-level invariants: `FinalAccountingPass.invariant_errors` + `PassReport.invariant_errors`
- [x] Completeness accounting trace: `state.completeness` with per-legend status in `details`
- [x] Pass reports per-pipeline-run: `pass_reports` in output dict

## Overall Cutover Decision
- [x] All 4 gates pass
- [x] **Ready for wrapper switch**
