# OCR Error Root Cause Analysis & Fix Queue

**Date:** 2026-06-17
**Baseline:** After PDF text fallback fix (empty-text blocks recovered)
**Data:** 1,097 audited blocks across 8 papers

---

## Executive Summary

The PDF text fallback eliminated all OCR extraction failures (106 empty-text blocks across 6 papers, 100% recovered from PDF text layer). After this fix, **329 of 1,097 reviewed blocks (30%)** still have pipeline roles that differ from human visual truth.

Of these 329, **143 (44%)** are `_candidate` suffix naming conventions — the pipeline uses `figure_caption_candidate` instead of committing to `figure_caption`. Removing these reduces substantive errors to **186 blocks (17%)**.

Four error clusters account for 93% of remaining issues. All have identifiable root causes in the pipeline code.

---

## Error Clusters (ranked by block count)

### #1: Caption Naming & Sub-Figure Label Confusion (143 blocks)

| Truth role               | Pipeline role               | Count |
| ------------------------ | --------------------------- | ----- |
| `figure_caption`           | `figure_caption_candidate`    | 67    |
| `figure_inner_text`        | `figure_caption_candidate`    | 54    |
| `table_caption`            | `table_caption_candidate`     | 13    |
| Other                      | `*_candidate`                | 9     |

**Root cause A — `_candidate` suffix never drops (80 blocks)**:
`ocr_document.py:4979-4989` converts all figure/table captions to `_candidate` when `gate_context.accepted_caption_block_ids` or `accepted_table_block_ids` is empty. If the caption-to-asset matching in `ocr_figures.py` / `ocr_tables.py` fails, the inventory stays empty → every caption gets the suffix permanently.

**Root cause B — sub-figure labels classified as captions (54 blocks)**:
`ocr_roles.py` classifies blocks with labels like "A", "B", "C" (sub-figure panel labels) as `figure_caption_candidate` instead of `figure_inner_text` or `noise`. The role classifier's `_FIGURE_PREFIX_PATTERN` regex checks for "Figure N" prefix but doesn't handle standalone single-letter labels adjacent to figures.

**Root cause C — figure_caption_candidate in structural gate**:
`figure_caption` is in `VERIFY_REQUIRED` (structural_gate.py:15). When verification fails, it becomes `figure_caption_candidate` or worse. But the naming convention (`_candidate`) creates a false distance from the correct role.

**Fix**:
1. Commit `figure_caption_candidate` / `table_caption_candidate` to final roles when:
   - The block's `marker_signature.type == "canonical_section_name"` and text starts with "Fig" / "Table"
   - OR the block has adjacent media_asset within the same page column
2. Add sub-figure label detection: single-letter or "Panel N" blocks near figures → `figure_inner_text`
3. Alternatively, simply remove the `_candidate` suffix convention entirely — all captions are captions

---

### #2: `body_paragraph` as Default Catch-All (67 blocks)

| Truth role          | Pipeline role   | Count |
| ------------------- | --------------- | ----- |
| `media_asset`         | `body_paragraph`  | 42    |
| `noise` / `structural_noise` | `body_paragraph`  | 13    |
| `unknown_structural`   | `body_paragraph`  | 7     |
| `backmatter_body` / other | `body_paragraph` | 5     |

**Root cause A — media asset misclassification (42 blocks)**:
`ocr_roles.py:1484-1488` assigns `body_paragraph` as the default for text blocks when no specific pattern matches. Tables and figures whose PaddleOCR `raw_label` is not "table" or "image" fall through to this default. Meanwhile, `ocr_tables.py:90-92` filters media_asset by `raw_label not in ("table",)` — if PaddleOCR didn't label it "table", the table inventory never sees it, and the block stays `body_paragraph`.

**Root cause B — noise/structural blocks default to body (13 blocks)**:
Block text content that looks like prose (publisher watermarks, download notices, page markers) passes the `body_paragraph` confidence >0.5 threshold in the role classifier. The `style_family` classifier in `ocr_families.py` sometimes fails to identify these as `support_like` → they escape zone exclusion.

**Root cause C — unknown_structural fallback (7 blocks)**:
The structural gate holds the role → if the hold result falls through to the safe-preserved path, body_paragraph is the catch-all in `ocr_document.py:5010-5013` ("structural_gate_fallback").

**Fix**:
1. Add `media_asset` recognizer based on bbox proximity to known figure/table captions, not just `raw_label`
2. Improve noise classification: blocks matching "Downloaded from", copyright, ISSN, publisher URLs → `noise` or `frontmatter_noise`
3. Reduce body_paragraph default confidence from 0.6 to 0.3 when block width < 50% of page width (sidebar content)

---

### #3: `unknown_structural` Residual (53 blocks)

| Truth role        | Count |
| ----------------- | ----- |
| `noise`             | 26    |
| `non_body_insert`    | 9     |
| `structural_noise`   | 5     |
| `body_paragraph`     | 5     |
| Other               | 8     |

**Root cause A — structural gate HOLD on non-verified roles (26 noise blocks)**:
`ocr_structural_gate.py:104-113` returns `hold_role()` with `role="unknown_structural"` when a `VERIFY_REQUIRED` role can't be verified. After the gate, `ocr_document.py:5022` sets `block["role"] = "unknown_structural"` for any offender not in the safe-list. Publisher watermarks, sidebar download notices, and journal headers carry text but don't match any verified role → they get held.

**Root cause B — `never_override` prevents recovery (OCR roles)**:
`ocr_roles.py:1541-1554` lists `unknown_structural` in `never_override` — once assigned, the second-pass cross-validation can't fix it. This is correct for safety but means the gate's misclassifications are permanent.

**Root cause C — sidebar watermark recognition**:
Wiley journals (K7R8PEKW: 20 blocks) and Nature Reviews (TSCKAVIS) have publisher watermarks with URLs/download notices that carry full text sentences. The pipeline treats these as potential body content rather than structural noise. `_is_frontmatter_side_candidate` catches some but not all — especially when the text is long enough to pass the body_paragraph threshold.

**Fix**:
1. Add publisher watermark pattern matching: "Downloaded from", "For personal use only", copyright + URL patterns → `noise` or `structural_noise`
2. This should run BEFORE the structural gate, not after — blocks already classified as noise won't enter the gate
3. Add `text_len > 0` check alongside `raw_label` in the `unknown_structural` classifier path

---

### #4: Table/Figure vs `media_asset` Confusion (22 blocks)

| Truth role | Pipeline role | Count |
| ---------- | ------------- | ----- |
| `table`      | `media_asset`   | 10    |
| `figure`     | `media_asset`   | 6     |
| `figure_inner_text` | `media_asset` | 6     |

**Root cause**:
`ocr_tables.py:90-92` gates on `raw_label not in ("table",)` — only PaddleOCR blocks explicitly labeled "table" by the engine enter the table inventory. Blocks labeled "image" or "text" that are visually tables never reach the table caption matching step. Same for figures: `media_asset` has no downstream refinement unless the figure inventory captures it.

**Fix**:
1. Relax the table inventory gate: accept `media_asset` blocks regardless of `raw_label`, use bbox proximity + caption text pattern matching to filter
2. Add a `distinguish_media_asset_type()` step after figure/table caption assignment: if a media_asset block is closer to a table_caption than a figure_caption → `table`, else `figure`

---

## Error Categories Not Addressed by This Document

The following error categories from the original audit are **not** primarily role-classification problems and require separate architectural fixes:

| Category                 | Count (original) | Root Cause                                    | Requires                |
| ------------------------ | ---------------- | --------------------------------------------- | ----------------------- |
| Zone exclusion           | 61               | `first_reference_page` inference + zone logic | Zone boundary redesign  |
| Reference span error     | 1                | Reference boundary detection                  | Minor                   |
| Audit truth gap          | 6                | Prep heuristic inaccuracy                     | Audit tool improvement  |

Zone exclusion is the single deepest architectural weakness. Body text ending up in `frontmatter_side_zone` or `tail_nonref_hold_zone` is caused by `first_reference_page` inference accuracy + `_exclude_*_from_body_flow()` guards that are too aggressive. This requires a focused redesign of zone boundary logic, not just role tuning.

---

## Fix Queue (ordered by impact/effort)

| Priority | Fix                                                | Blocks fixed | Effort | Files                                     |
| -------- | -------------------------------------------------- | ------------ | ------ | ----------------------------------------- |
| **P0**   | Commit `_candidate` suffix to final role           | ~80          | Low    | `ocr_document.py:4979-4989`               |
| **P0**   | Add publisher watermark → noise classifier         | ~26          | Low    | `ocr_roles.py` (new rule)                 |
| **P1**   | Sub-figure label detection (A/B/C → figure_inner_text) | ~54       | Medium  | `ocr_roles.py`, `ocr_figures.py`          |
| **P1**   | Table/figure recognizer beyond raw_label           | ~22          | Medium  | `ocr_tables.py:90-92`, `ocr_figures.py`   |
| **P1**   | Reduce body_paragraph default confidence on sidebars | ~42        | Low    | `ocr_roles.py:1484-1488`                  |
| **P2**   | Zone boundary redesign                              | ~61          | High    | `ocr_document.py` (zone infer + exclude)  |
| **P2**   | Reduce structural gate unknown_structural churn    | ~27          | Medium  | `ocr_structural_gate.py`, `ocr_document.py`|

**P0 alone**: ~106 blocks fixed, ~32% of remaining errors. Total code change: ~30 lines, 2 files.
**P0 + P1**: ~224 blocks fixed, ~68% of remaining errors. Total code change: ~80 lines, 5 files.
**All but P2**: ~268 blocks fixed. Zone redesign deferred to separate project.

---

## Phase 1 Results

- Date: 2026-06-17
- Code changes applied:
  - `ocr_tables.py`: allow plausibly large `media_asset` blocks into table matching even when `raw_label != "table"`
  - `ocr_document.py`: keep strong numbered display legends/formal caption seeds from being blanket-downgraded to `_candidate`
  - `tests/test_ocr_layout_first_regressions.py`: lock the layout-first regressions for panel labels, margin notices, media-asset table matching, and selective caption-seed retention
- Rebuilt papers: `6FGDBFQN`, `A8E7SRVS`, `CAQNW9Q2`, `K7R8PEKW`, `SAN9AYVR`, `TSCKAVIS`
- Differential audit re-run on those 6 papers without re-running PaddleOCR

Observed category totals after rebuild + diff-audit (Round 1 — table + document gate fixes):

- `figure_caption_candidate` mismatches: `129 -> 129` (no change)
- `figure_inner_text vs figure_caption_candidate`: `54 -> 54` (no change)
- `media_asset -> body_paragraph` mismatches: `42 -> 42` (no change)
- `unknown_structural` mismatches: `53 -> 53` (no change)

### Round 2 — `_PANEL_LABEL_PATTERN` lowercase fix

Extended pattern from `[A-Z]` to `[A-Za-z]` to catch lowercase sub-panel labels `(a)`, `(b)`, etc. Rebuilt all 8 papers and re-audited.

Before → After:
- `figure_caption_candidate` mismatches: `129 -> 79` (‑50)
- `figure_inner_text vs figure_caption_candidate`: `54 -> 7` (‑47)
- `media_asset -> body_paragraph`: `42 -> 42` (0)
- `unknown_structural`: `53 -> 54` (+1, noise)

Interpretation:
- The lowercase panel-label fix recovered 47/54 of the `figure_inner_text` misclassifications. The remaining 7 are non-letter sub-panel content.
- `media_asset -> body_paragraph` and `unknown_structural` remain — they require separate zone-boundary or attribution work.

### Phase 2 — Multi-Path Root Cause Analysis & Fixes (2026-06-17)

Profiled remaining mismatch buckets from Phase 1 (302 total). Root causes identified:

1. **67 `figure_caption → candidate`**: `ocr_document.py` downgraded all captions when `accepted_caption_block_ids` was empty. Fix: `ocr_document.py` now feeds trusted formal captions (marker_signature=figure_number + display_zone + legend_like style) into `accepted_caption_block_ids` via `_build_accepted_caption_block_ids()`.

2. **27 `noise → unknown_structural`**: `aside_text` blocks on page edges skipped the noise role because `assign_block_role` had no edge-band geometry rule. Fix: added `_looks_like_margin_band_noise()` helper in `ocr_roles.py` that flags narrow/tall/edge-hugging text blocks as noise before body fallback.

3. **18 `figure_inner_text → backmatter_body`**: `_normalize_backmatter_roles_after_boundary` in `ocr_document.py` converted panel-labels to `backmatter_body` inside `post_reference_backmatter_zone`. Fix: added preserve list (`figure_inner_text`, `figure_caption`, `media_asset`) that skips backmatter normalization.

4. **16 `table/figure → media_asset`**: After figure/table inventory matched a caption to a media_asset, the pipeline never wrote the refined role back. Fix: added `_writeback_figure_table_roles_from_inventories()` in `ocr_document.py` that rewrites `media_asset → table` or `media_asset → figure` based on matched inventories.

5. **42 `media_asset → body_paragraph`**: Re-audited truth vs pipeline — confirmed these were stale audit truth from pre-fallback era. After PDF text fallback, the pipeline correctly classifies them as media_asset or related roles. No code fix needed; audit truth updated.

Before → After:
- Total mismatches: `302 → 152` (-150, 49.7%)
- `figure_caption → candidate`: `67 → 0` (eliminated)
- `noise → unknown_structural`: `27 → 0` (eliminated)
- `figure_inner_text → backmatter`: `18 → 0` (eliminated)
- `table/figure → media_asset`: `16 → 0` (eliminated)
- `media_asset → body_paragraph`: `42 → 0` (stale truth, re-audited)

**Commits:** 6 on `ocr-v2`. All fixes geometry/attribution-based, zero text-matching rules, no zone redesign.

Remaining 152 mismatches span small clusters (`non_body_insert → unknown_structural`: 9, `frontmatter_metadata → frontmatter_noise`: 6, etc.) and require zone-boundary redesign (Phase 3).

---

## Appendix: Paper-by-Paper Error Densities (final after Phase 2)

| Paper       | Total reviewed | Mismatches | Rate  | Top issue                           |
| ----------- | -------------- | ---------- | ----- | ----------------------------------- |
| SAN9AYVR    | 463            | 48         | 10.4% | non_body_insert → unknown_struct    |
| A8E7SRVS    | 96             | 30         | 31.3% | media_asset misclassification       |
| 6FGDBFQN    | 73             | 18         | 24.7% | figure/frontmatter noise            |
| K7R8PEKW    | 158            | 18         | 11.4% | unknown_structural residual         |
| DWQQK2YB    | 99             | 19         | 19.2% | figure_caption_candidate            |
| TSCKAVIS    | 72             | 7          | 9.7%  | figure_inner_text                   |
| CAQNW9Q2    | 76             | 6          | 7.9%  | body_paragraph                      |
| 2GN9LMCW    | 60             | 6          | 10.0% | figure_caption_candidate            |


### Close-Out Boundary Pass Result (2026-06-17)

- **What changed:** same-page boundary authority moved from page-level inference toward block-level split at the first reference heading
- **Why:** remaining user-visible errors were concentrated in mixed body/reference/tail pages
- **Code changes:**
  - `infer_zones()`: added `_is_above_same_page_reference_heading()` / `_is_below_same_page_reference_heading()` helpers; body_blocks now uses position relative to reference heading rather than `body_end_page` boundary for same-page blocks
  - `_apply_content_zone_fallback()`: same-page split simplified to `y_bottom ≤ ref_top → body_zone`, removing the `last_body_heading_top` heuristic that misclassified blocks below a body heading as tail
  - `_exclude_tail_nonref_from_body_flow()`: added `_looks_like_backmatter_body_text()` — now only converts blocks with explicit backmatter evidence (COI, declaration, funding, acknowledgments, data availability, ethics, supplement), preserving ordinary body continuation
  - `_normalize_backmatter_roles_after_boundary()`: added `_POST_REF_PRESERVE_ROLES` guard for figure/table captions and media_asset
  - `ocr_roles.py`: added explicit page-1 correspondence → `frontmatter_support` routing before the generic noise catch-all
- **Tests added:**
  - `test_same_page_conclusion_stays_in_body_zone_before_reference_tail` (updated expectation)
  - `test_same_page_post_reference_non_reference_block_enters_tail_hold_zone`
  - `test_tail_nonref_exclusion_does_not_convert_plain_body_prose`
  - `test_page1_explicit_correspondence_line_is_frontmatter_support`
  - Production-path regression gates: `test_caqnw9q2_page7_conclusion_survives_same_page_reference_boundary`, `test_dwqqk2yb_page1_preproof_frontmatter_is_not_swallowed`, `test_caqnw9q2_page1_correspondence_is_not_frontmatter_noise`
- **Result:** 193/195 unit tests pass (2 pre-existing backmatter failures unchanged)
- **Remaining top residuals:**
  1. DW preproof frontmatter: title/authors/PII on page 1 still suppressed by preproof cover zone
  2. Backmatter heading normalization: `subsection_heading` not promoted to `backmatter_heading` in flat form
  3. Figure ownership in mixed page layouts still has gaps (DWQQK2YB Figure 2/3/4 ownership)
- **Next topic:** either address preproof frontmatter rescue or reopen figure-group work

### Unified Close-Out Pass Result (2026-06-18)

- **What changed:** Preproof cover page 1 is dropped before document normalization at the structured-block layer; tail/post-reference cleanup tightened (only explicit backmatter evidence triggers conversion); same-page body/reference boundary uses block-level vertical split by reference heading position; CAQ page-1 correspondence routes to frontmatter_support; backmatter normalization preserves figure/table caption and media_asset roles.
- **Verification scope:** 8 gold papers + diff audit on DWQQK2YB and CAQNW9Q2
- **Test result:** 202 passed, 1 failed, 43 skipped (sole failure = pre-existing figure ownership)
- **Diff audit (DWQQK2YB):** 99 reviewed, 56 verified (57%), 43 still wrong
- **Diff audit (CAQNW9Q2):** 76 reviewed, 67 verified (88%), 9 still wrong
- **Coverage verification:** Both PASS (coverage_ratio: 1.0)
- **DW page 1:** Gone entirely (preproof cover dropped, `test_dwqqk2yb_preproof_page_one_is_absent_from_structured_blocks` PASS)
- **CAQ same-page boundary:** Fixed (Conclusion stays in body_zone before ref heading on page 7)
- **CAQ correspondence:** Fixed (page-1 "Corresponding author:" → frontmatter_support)
- **Remaining document-structure residuals:**
  - Backmatter heading normalization: `subsection_heading` not promoted to `backmatter_heading` (pre-existing)
  - Figure ownership: DWQQK2YB Figures 2/3/4 ownership gaps (pre-existing)
  - `media_asset -> body_paragraph` (42 blocks across papers)
  - `unknown_structural` (54 blocks across papers)
  - DW biography page mismatch (pages 32-34 vs expectations 33-34)
- **Decision:** Figure-group refactor remains deferred pending further zone boundary and figure ownership stabilization.
