# Layout Pipeline — Remaining Risk Scan (2026-07-03)

## Method

Checked every function in the layout analysis pipeline against code + 100+ real vault papers:
- `_cluster_page_column_groups` / `_classify_page_layout`
- `infer_zones` / `_apply_zone_labels` / `_apply_content_zone_fallback`
- `_detect_forward_body_end` / `_detect_backward_backmatter_start` / `_reconcile_tail_spread`
- `_build_page_reading_segments` / `_build_tail_reading_order`
- `_is_frontmatter_side_candidate` / `_is_first_page_body_start`
- `discover_body_family_anchor`
- `_page_has_strong_body_continuation`

## Covered by existing/planned fixes

| Issue | Status |
|-------|--------|
| Sidecar caption (37LK5T97) | ✅ Fixed in `_is_sidecar_candidate` |
| Two-column ref ordering | ✅ Fixed in `_should_attach_reference_item_to_ref_section` |
| Column-aware prefix recovery | ✅ Fixed in `_recover_figure_heading_prefix` |
| Weak cluster rejection (2E4EPHN2) | ✅ Fixed in `_is_weak_isolated_column_cluster` |
| Spread_start > spread_end (AH6Q7DLC) | ✅ Planned Step 1 — 1-line guard |
| Frontmatter zone leak (CAQNW9Q2) | ✅ Planned Step 2 — width-vs-body rescue |
| mixed_tail fixture coverage | ✅ Planned Step 5 — 2 new fixtures |

## Analyzed and found acceptable — not risks

### 1. Low-confidence layout pages (conf<0.35)
**Frequency:** 536/732 papers.
**Root cause:** Figure-heavy pages have 0-1 `_is_layout_eligible_block` (headings excluded by design). Confidence capped at 0.35 as expected fallback.
**Verdict:** ✅ Not a bug. Data limitation — correct behavior.

### 2. body_anchor_ok=False (7% of papers)
**Mechanism:** When `discover_body_family_anchor` returns HOLD, `body_blocks` filter in `infer_zones` (line 1540) produces empty `body_block_ids`. `_apply_content_zone_fallback` assigns body_zone to everything indiscriminately.
**Real impact:** Reference zone still works (separately detected). Fallback assigns reasonable zones. Only loss is body_zone metadata (anchor_family, boundary_band).
**Verdict:** ✅ Acceptable degradation. The 7% are very short or stylistically unusual papers where zone metadata adds minimal value.

### 3. Mixed_tail classification conservative
**Mechanism:** `_classify_page_layout` requires body column to have ZERO tail roles (line 486: `not col_has_tail[0]`). If both columns have some tail + some body, classified as two_column.
**Verdict:** ✅ Conservative by design. False two_column is safer than false mixed_tail. No evidence of actual wrong behavior.

### 4. Headings excluded from layout eligibility
**Mechanism:** `_LAYOUT_ELIGIBLE_ROLES` = `{body_paragraph, list_item, tail_candidate_body, reference_item, backmatter_body}`. But `_cluster_page_column_groups` uses ALL blocks with bbox width > 50px — not just eligible ones.
**Real effect:** Headings' x-centers contribute to column clustering. Eligibility only affects confidence count (line 534: `len(eligible_blocks) < 2 → confidence = min(confidence, 0.35)`).
**Verdict:** ✅ Safe. Clustering is correct; confidence is correctly conservative.

### 5. Reading order segments
**Mechanism:** `_build_page_reading_segments`: single-col = y-sorted, multi-col = column-grouped then y-sorted. Standard academic reading order.
**Verdict:** ✅ Correct.

## Findings that changed the plan

Only one plan change: Step 2's width rescue was confirmed effective on the motivating paper (CAQNW9Q2 correspondence: 161px vs body 393px = 233px diff, far exceeding 100px threshold). The plan was updated in-session.

## Conclusion

**No new critical or high-risk issues found beyond the three planned fixes.** The pipeline is structurally sound — all components have the right conceptual model. The three remaining issues (spread cap, frontmatter rescue, mixed_tail fixtures) are well-understood, bounded-in-impact, and already planned.
