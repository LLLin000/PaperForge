# OCR-v2 Remaining Issues & Root Cause Analysis

> Date: 2026-06-18
> Baseline: readiness-gates transition after 9.9 DW repair phase

## Active Readiness Residuals

1. **Gate 1 completeness-check layer is specified but not implemented** in the structured-block and rendered-coverage paths
2. **Gate 2 figure ownership still carries a trust gap** on mixed post-reference and multi-panel pages; current hard case still tolerates ambiguity in practice
3. **Gate 3 ordering/boundary authority is not fully upstream**; renderer-side repair remains part of the correctness story
4. **Gate 4 layout coverage is under-formalized**; old fixture-ledger assumptions are stale, and the readiness ledger needs to live against the real audit-paper corpus instead
5. **Backmatter heading taxonomy remains partially conservative by design**; only promote it if Gate 3 boundary evidence requires it
6. **Gate 5 unseen-paper blind audit is intentionally deferred** until Gates 1-4 are complete

## Priority Summary

| # | Issue | Priority | Type | Status |
|---|-------|----------|------|--------|
| 1 | Completeness check | P1 | Readiness gate | Active next slice |
| 2 | Figure ownership | P0 | Trust / ownership gap | Active after Gate 1 |
| 3 | Ordering authority | P1 | Structural authority gap | Active after Gate 2 |
| 4 | Layout coverage ledger + taxonomy | P1 | Test / evidence gap | Active after Gate 3 |
| 5 | Backmatter heading taxonomy | P3 | Conservative by design | Deferred unless Gate 3 needs it |
| 6 | Unseen-paper blind audit | Next stage | Validation gate | Deferred by design |
