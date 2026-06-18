# OCR-v2 Remaining Issues & Root Cause Analysis

> Date: 2026-06-18
> Baseline: After 9.7 close-out, ahead of DW repair phase

## Active Residuals After 9.7

1. **DWQQK2YB figure ownership still over-claims or stays ambiguous** on mixed post-reference figure pages (group-first figure inventory refactor deferred)
2. **Backmatter heading taxonomy remains partially conservative by design**; only fix if verified zone semantics require it
3. **Completeness-check layer is specified and pending implementation**

## Priority Summary

| # | Issue | Priority | Type | Status |
|---|-------|----------|------|--------|
| 1 | DW figure ownership | P0 | Ownership gap | Deferred (architectural) |
| 2 | Backmatter heading | P3 | Conservative by design | Deferred |
| 3 | Completeness check | P1 | Feature gap | Planned next slice |
