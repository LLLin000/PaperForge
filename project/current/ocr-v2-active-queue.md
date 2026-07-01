# OCR-v2 Active Queue
> Status: ACTIVE QUEUE — Audit fixes + rotated-figure prematch landed. 422 regression tests pass.
> Last updated: 2026-07-01
> Scope: post-audit cleanup

## Current Priorities
1. **Monitor production OCR** after rotated-figure prematch refactor
2. **Archive stale `project/current/` files**
3. **Group-first figure inventory refactor** (deferred)

## Completed This Session (cumulative)
- **4-commit audit fix plan**: 3 new commits + 1 pre-existing
  - Commit 1 (`2d40ad9`): Table Roman+S prefix across 4 files
  - Commit 2 (`21bdfd0`): vision_footnote figure description rescue
  - Commit 3 (pre-existing `4ab227e`): unmatched asset dedup
  - Commit 4 (`7670227`): bbox-only synthetic vector figure fallback
- **Orientation-aware rotated figure follow-up**
  - preserve PyMuPDF `dir/wmode` in `span_metadata`
  - move rotated-caption handling into normal figure pre-match
  - carry `rotation_correction_deg` into figure crop/render
  - U746UJ7G now matches via `same_page_rotated` instead of synthetic fallback
- **422 regression tests pass**, 0 failures


## Cross-Links
- Narrative ledger: `PROJECT-MANAGEMENT.md` (§9.18)
- Evidence source: `project/current/ocr_rebuild_audit.md`
- Architecture boundary: `project/current/ocr-v2-generalization-boundary.md`

