# Phase 2 Root Cause Analysis — Remaining OCR Mismatches

**Date:** 2026-06-17
**Baseline:** After Phase 1 (PDF fallback + panel label fix)
**Data:** 302 mismatches across 8 papers, 795 verified

---

## Bucket 1: `truth=media_asset pipe=body_paragraph` (42 blocks)

- ALL 42 have `raw_label = text`, `marker_signature = none`
- 41/42 in `body_zone` or `tail_nonref_hold_zone`
- 31/42 have `style_family = body_like`
- xcenter median 71.8% (right-column body text)
- Content: complete body prose, not captions, not media assets

**Root cause:** Audit truth stale. These were reviewed as `media_asset` when text was empty (pre-fallback). After PDF text fallback filled the text, the pipeline correctly classifies them as `body_paragraph`. The truth needs updating, not the code.

**Action:** Differential re-audit only. Update block_review.jsonl truth_role to `body_paragraph`. Do NOT change pipeline code.

---

## Bucket 2: `truth=noise pipe=unknown_structural` (27 blocks)

- 25/27 have `raw_label = aside_text`
- width median 18px, height median 1503px, xcenter median 97.6%
- All: publisher download/sidebar watermarks, journal running notices
- Geometry: ultra-narrow, ultra-tall, pinned to page edge
- 18/27 in `body_zone` (should never be body), 5 with no zone

**Root cause:** Geometry is the signal, but it fires too late. `aside_text` blocks with extreme edge-band geometry should be classified as noise BEFORE entering the structural gate and body-zone assignment. Currently the style_family classifier sees `body_like` because the text looks like prose; the geometry evidence (narrow + tall + edge) is not strong enough pre-gate.

**Fix:** Add an edge-band geometry rule in `ocr_roles.py` or zone prepass that fires on `raw_label in {"aside_text", "header_image"} + width < page_width * 0.03 + height > page_height * 0.5` before body-like classification. Route to `noise` with high confidence. No text-matching needed — geometry alone is sufficient.

---

## Bucket 3: `truth=figure_caption pipe=figure_caption_candidate` (67 blocks)

- 64/67 have `raw_label = figure_title`
- 63/67 have `marker_signature = figure_number`
- 60/67 in `display_zone`
- 41/67 have `style_family = legend_like`, 26/67 `support_like`
- width median 959px, xcenter median 50% — standard full-width figure captions

**Root cause:** The classifier already knows these are captions (raw_label + marker + zone + style all agree). The problem is downstream: `ocr_structural_gate.py` only ACCEPTs `figure_caption` when the block is in `accepted_caption_block_ids` (membership verified against figure inventory matched assets). If figure inventory/caption-to-asset matching fails, the gate holds the role, and it becomes `figure_caption_candidate` permanently.

The real gap is in the **figure inventory → accepted_caption_block_ids → structural gate** pipeline. Strong formal legends with `figure_number` marker, `display_zone`, and `legend_like`/`support_like` style should be admitted into `accepted_caption_block_ids` even without asset matching, or the gate should trust the accumulated evidence.

**Fix:** In `ocr_figures.py` or the `_build_accepted_caption_block_ids` path: for blocks with `marker_signature.type == "figure_number"` AND `zone == "display_zone"` AND `style_family in {"legend_like", "support_like"}`, add them to `accepted_caption_block_ids` regardless of asset matching. This is a geometry+marker evidence rule, not text matching.

---

## Bucket 4: `truth=figure_inner_text pipe=backmatter_body` (18 blocks)

- ALL 18 in DWQQK2YB only
- `raw_label = figure_title`, `marker_signature = panel_label`
- ALL in `zone = post_reference_backmatter_zone`
- `style_family = legend_like`
- width median 29.5px, height median 26px — very small panel labels
- Content: `(a)`, `(b)`, `(c)`, `(d)` etc.

**Root cause:** These panel labels are correctly classified as `figure_inner_text` by the role classifier (the panel label regex catches them). But `ocr_document.py` post-reference backmatter normalization (around line 4630+) converts all non-heading blocks in `post_reference_backmatter_zone` to `backmatter_body`. The panel label evidence is lost in this downstream normalization step.

**Fix:** In the backmatter normalization pass: preserve blocks with `marker_signature.type == "panel_label"` or `role == "figure_inner_text"` — do not convert them to `backmatter_body`. Local, single-line guard. Zero regression risk.

---

## Bucket 5: `truth=table pipe=media_asset` (10 blocks) + `truth=figure pipe=media_asset` (6 blocks)

- ALL 10 table blocks in A8E7SRVS
- `raw_label = table` (PaddleOCR labeled them correctly!)
- `zone = body_zone`
- Content contains actual `<table>...</table>` HTML

**Root cause:** PaddleOCR correctly labeled these as `table`. The table inventory likely processes them. But the **final role writeback from table inventory to structured block role** is not happening. The block stays `media_asset` even though the table inventory has a matched table entry for it.

Similarly for `figure -> media_asset`: the figure inventory may match the caption but the asset block's role is not updated.

**Fix:** In `ocr_tables.py` and `ocr_figures.py`: after table/figure inventory is built, iterate matched tables/figures and update the structured block role of each matched asset from `media_asset` to `table_html` (or `figure_asset`). This is a role writeback step, not a gate change. The previous `ocr_tables.py` gate relaxation (Phase 1) was necessary but insufficient — it only admitted blocks, it didn't write back roles.

---

## Summary: What to fix vs What to re-audit

| # | Bucket | Blocks | Type | Fix location |
|---|--------|--------|------|--------------|
| # | Bucket | Blocks | Type | Fix location | Result |
|---|--------|--------|------|--------------|--------|
| 1 | media_asset→body_paragraph | 42 | Re-audit only (stale truth) | No code change | ✅ 42→0 (re-audited) |
| 2 | noise→unknown_structural | 27 | Geometry rule | `ocr_roles.py` | ✅ 27→12 (−15, 12 residual: non-edge-band aside_text in body zone) |
| 3 | figure_caption→candidate | 67 | Accepted caption IDs | `ocr_document.py` | ✅ 67→5 (−62, 5 residual: no marker/zone/style triple match) |
| 4 | figure_inner_text→backmatter | 18 | Post-ref normalization guard | `ocr_document.py` | ✅ 18→0 (fully resolved) |
| 5 | table/figure→media_asset | 16 | Inventory role writeback + re-audit | `ocr_tables.py` + `ocr_figures.py` | ✅ 16→3 (3 residual: genuinely ambiguous inventory matches) |

**Phase 2 net:** need_reaudit 302 → 152 (−150, 49.7% reduction). 945/1097 blocks verified (86.1%).

**Residual (152):** 42 A8E7SRVS (mostly structural noise/zone issues), 30 6FGDBFQN, 23 SAN9AYVR, 22 K7R8PEKW, 16 DWQQK2YB, 9 TSCKAVIS, 5 each for 2GN9LMCW and CAQNW9Q2.
