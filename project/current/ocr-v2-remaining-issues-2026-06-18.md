# OCR-v2 Remaining Issues & Root Cause Analysis

> Date: 2026-06-19
> Status: historical readiness-cycle residuals
> Readiness gates: complete
> Active queue: `project/current/ocr-v2-active-queue.md`

This file records the residual state at the end of the readiness-gate cycle.
It is not the active rebuild-hardening queue.

## Active Readiness Residuals

1. **Gate 1 completeness-check layer** -- DONE (page/region/rendered-gap signals implemented)
2. **Gate 2 figure ownership** -- DONE on the tracked DW and generic figure-suite coverage after narrowing the previous-page fallback with local layout cross-checks
3. **Gate 3 ordering/boundary authority** -- DONE (`_enforce_reference_boundary_from_structure` upstream)
4. **Gate 4 layout coverage** -- DONE (taxonomy in `audit/coverage_ledger.json`, contract tests enforce named representatives)
5. **Backmatter heading taxonomy remains partially conservative by design**; only promote it if Gate 3 boundary evidence requires it
6. **Gate 5 unseen-paper blind audit** — DONE: 5 papers, all PASS, no new failure families

## Post-Blind-Audit Known Residuals (Low Severity)

- ~40 blocks across corpus with stale audit truth (pipeline correct, truth wrong)
- ~50 blocks across corpus: genuine edge cases (backmatter boundary, caption promotion, non-body insert)
- PZ8B59K4: 34 sidebar blocks with no zone (publisher table-number sidebar); 1 figure_unknown
- GU9R8EPE: backmatter disclaimer bleeds into rendered fulltext
- All are known patterns — no new failure families from blind audit

## Gate 5 Blind-Audit Entry Criteria

OCR-v2 is ready for blind audit only when:
- Gates 1-4 complete and verified
- No active P0 trust risk in known fixtures
- Project truth files aligned
- Blind audit sample selected before execution

## Priority Summary

| # | Issue | Priority | Type | Status |
|---|-------|----------|------|--------|
| 1 | Completeness check | P1 | Readiness gate | DONE |
| 2 | Figure ownership matcher stability | P0 | Trust / ownership gap | DONE on current tracked suites |
| 3 | Ordering authority | P1 | Structural authority gap | DONE |
| 4 | Layout coverage ledger + taxonomy | P1 | Test / evidence gap | DONE |
| 5 | Backmatter heading taxonomy | P3 | Conservative by design | Deferred |
| 6 | Unseen-paper blind audit | P0 | Validation gate | DONE — 5 papers, all PASS |
| 7 | Stale audit truth blocks | P3 | Cleanup | ~40 blocks (pipeline correct, truth wrong) |
| 8 | Edge-case misclassifications | P3 | Boundary | ~50 blocks, low severity |
