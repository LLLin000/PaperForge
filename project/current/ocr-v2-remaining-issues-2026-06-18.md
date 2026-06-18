# OCR-v2 Remaining Issues & Root Cause Analysis

> Date: 2026-06-18
> Baseline: After 9.7 close-out, ahead of DW repair phase

## Active Residuals After 9.7

1. **DWQQK2YB first-surviving-page support blocks still route inconsistently** (`frontmatter_support` vs `frontmatter_noise` / body fallback)
2. **DWQQK2YB figure ownership still over-claims or stays ambiguous** on mixed post-reference figure pages
3. **Backmatter heading taxonomy remains partially conservative by design**; only fix if verified zone semantics require it
4. **Completeness-check layer is specified and pending implementation**

## Priority Summary

| # | Issue | Priority | Type | Status |
|---|-------|----------|------|--------|
| 1 | DW support routing | P0 | Routing gap | Active |
| 2 | DW figure ownership | P0 | Ownership gap | Active |
| 3 | Backmatter heading | P3 | Conservative by design | Deferred |
| 4 | Completeness check | P1 | Feature gap | Planned next slice |
