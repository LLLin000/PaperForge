# Figure Number Inference from Sequence Gaps

**Date:** 2026-06-26
**Status:** Draft (Revised 2026-06-26, round 2)
**Motivation:** PaddleOCR sometimes fails to extract "Figure N." text when the label is rendered inside a figure image or in a narrow visual gap. In N6XCZD25, Figure 1's "Figure 1." text was lost, producing `figure_unknown_005` in the matched inventory while Figures 2-6 were correctly numbered.

## Problem

`figure_inventory.json` > `matched_figures` may contain items with `figure_number: null` even when the legend has been correctly matched to an asset. The renderer falls back to `figure_unknown_{N}.md` for these, producing a dead embed in the fulltext — visually placed but no cross-reference number.

## Proposal

Add `_infer_missing_main_figure_numbers()`, called inside `build_figure_inventory()` in `ocr_figures.py`, **after** `inventory` is assembled and after `_promote_sequence_matches()`, but **before** `compute_figure_legend_completeness()`.

### Terminology

| Term | Meaning |
|------|---------|
| `_infer_missing_main_figure_numbers()` | New function: infers missing main-sequence figure numbers for matched_figures entries with `figure_number: None` |
| `_promote_sequence_matches()` | **Existing** logic: promotes ambiguous figures to matched based on adjacent numbering (they already have a number of their own) |
| sequence number inference | **New**: matched figures without a number get one from gap analysis |

These are distinct concerns — *sequence_match* promotes match status, *inference* fills a missing number.

### Eligibility

Candidate must satisfy **all**:

```text
bucket == matched_figures
figure_number is None
legend_block_id exists and len > 0
asset_block_ids non-empty
settlement_type in {"same_page", "group_sequential", "cross_page_forward",
                    "cross_page_backward", "composite_parent"}
namespace == main  (see namespace isolation below)
NOT vetoed by frontmatter visual keywords (see below)
legend_bbox resolvable (see order contract)
```

Non-candidates (never inferred):
- `held_figures`, `ambiguous_figures`, `unmatched_legends`, `rejected_legends`, `unresolved_clusters`
- Asset-matched legends that turn out to be frontmatter images, graphical abstracts, TOC images, publisher previews

### Frontmatter Visual Veto

```python
_FRONTMATTER_VISUAL_VETO = (
    "graphical abstract",
    "toc",
    "table of contents",
    "highlights",
    "available with this article",
    "supplementary data",
    "supporting information",
    "video abstract",
    "visual abstract",
)
```

A candidate is vetoed if its `text`, its corresponding legend block text, or nearby container text contains any of these keywords (case-insensitive, substring match).

### First Release Scope

**Only one scenario: leading Figure 1 gap.**

```text
known main figures:  [2, 3, 4, ...]   (min == 2)
eligible unknown:    exactly 1
order check:         unknown.figure_order_key < first_known.figure_order_key
noise check:         no other unnumbered matched/ambiguous/held legend
                     intervenes between unknown and first_known
```

Scenarios explicitly deferred:
- Middle gaps (`known=[1,3,4]`, unknown=`[2]`)
- Multiple leading gaps (`known=[3,4]`, unknown=`[1,2]`)
- End gaps (`known=[1,2,3]`, unknown=`[4]`)

### Order Contract

`figure_order_key` is a tuple `(page, legend_page, y, x)` used to sort matched figures for gap detection.

**Do NOT assume `legend_bbox` is present on the matched_figures item.** Lookup order:

```python
def _resolve_legend_bbox(matched_item, structured_blocks, inventory) -> list[float] | None:
    # 1. Prefer direct field
    if matched_item.get("legend_bbox"):
        return matched_item["legend_bbox"]
    # 2. Look up legend block by (legend_page, legend_block_id) in structured_blocks
    legend_block = _find_legend_block(matched_item, structured_blocks)
    if legend_block and legend_block.get("bbox"):
        return legend_block["bbox"]
    # 3. Look up corresponding item in inventory["figure_legends"]
    for fl in inventory.get("figure_legends", []):
        if fl.get("block_id") == matched_item.get("legend_block_id"):
            if fl.get("bbox"):
                return fl["bbox"]
    # 4. Not resolvable → skip inference for this item
    return None
```

If `legend_bbox` is not resolvable after all three fallbacks, the item is **not eligible** for inference.

```python
figure_order_key = (
    min(matched_item.get("asset_pages") or [matched_item.get("page", 1)]),
    matched_item.get("legend_page") or matched_item.get("page", 1),
    legend_bbox[1],  # y0 (top-to-bottom)
    legend_bbox[0],  # x0 (left-to-right)
)
```

For leading gap: `unknown.order_key < first_known.order_key`

### Namespace Isolation

`_extract_figure_marker()` returns a structured dict:

```python
_extract_figure_marker(text: str) -> dict:
    return {
        "namespace": "main" | "supplementary" | "extended_data",
        "number": int | None,            # parsed digit, excluding S prefix
        "raw_prefix": str,               # e.g. "Figure", "Fig.", "Figs."
        "has_s_prefix": bool,            # "Fig. S1" → True
        "marker_text": str,              # the matched portion
    }
```

Heuristic:
- Text containing `supplementary`, `supporting`, `additional file`, `appendix` → namespace=supplementary
- Text containing `extended data`, `extended figure` → namespace=extended_data
- `Fig. S1` / `Figure S1` / `Figure S1C` (capital `S` immediately before digit) → namespace=supplementary, has_s_prefix=True
- Everything else → namespace=main

Only `namespace == "main" and not has_s_prefix` entries participate in inference.

This parser REPLACES the old `_extract_figure_number()` for building the known-number set. The old function strips `S` and returns a bare int — it must not be used for this pass.

### Skip Reasons

The function writes a metadata block to inventory for every invocation, even on no-op:

```python
inventory["figure_number_inference"] = {
    "status": "skipped" | "accepted",
    "method": "leading_gap",
    "reason": "no_eligible_unknowns" | "known_min_not_2"
             | "multiple_eligible_unknowns" | "unknown_not_before_first_known"
             | "namespace_not_main" | "frontmatter_visual_veto"
             | "missing_legend_bbox" | "accepted",
    "eligible_unknown_count": int,
    "known_main_numbers": list[int],
    "inferred_figure_number": int | None,
}
```

Reason catalog:

| reason | meaning |
|--------|---------|
| `no_eligible_unknowns` | No matched_figures items with figure_number=None |
| `known_min_not_2` | known_main empty or min != 2 |
| `multiple_eligible_unknowns` | >1 eligible unknown before first_known |
| `unknown_not_before_first_known` | Eligible unknown but order_key >= first_known |
| `namespace_not_main` | Eligible unknown but namespace != main |
| `frontmatter_visual_veto` | Eligible unknown but vetoed by keyword |
| `missing_legend_bbox` | Eligible unknown but legend_bbox not resolvable |
| `accepted` | Inferred successfully |

### Mutation Contract

**Do not mutate `marker_signature`.** It is observed evidence. Instead:

```python
# On matched_figures item:
matched_item["figure_number"] = 1
matched_item["figure_id"] = "figure_001"
matched_item["figure_namespace"] = "main"
matched_item["number_inference"] = {
    "status": "accepted",
    "method": "leading_gap",
    "inferred_number": 1,
    "known_numbers": [2, 3, 4, 5, 6],
}

# On corresponding figure_legends item:
legend["inferred_figure_number"] = 1
legend["figure_number_source"] = "sequence_gap_inference"
```

Reader-facing output reads `figure_number` / `figure_id` from the matched item, which is already the canonical source — no additional reader changes needed.

### Integration Point

In `ocr_figures.py`, `build_figure_inventory()` — the existing matching loop builds `matched_figures` incrementally, and `inventory` is assembled after the loop. The correct insertion point is:

```python
# 1. Assemble inventory (existing code, already after full matching loop)
inventory = {
    "figure_legends": figure_legends,
    "matched_figures": matched_figures,
    "held_figures": held_figures,
    "ambiguous_figures": ambiguous_figures,
    "unmatched_legends": unmatched_legends,
    ...
}

# 2. Existing sequence promotion
inventory = _promote_sequence_matches(inventory, structured_blocks)

# 3. NEW: infer missing main figure numbers
inventory = _infer_missing_main_figure_numbers(inventory, structured_blocks)

# 4. Existing completeness check
inventory["figure_legend_completeness"] = compute_figure_legend_completeness(
    structured_blocks, inventory,
)

return inventory
```

Do NOT place inference before the main matching loop. At that point `matched_figures` does not exist yet.

### Algorithm

```
_infer_missing_main_figure_numbers(inventory, structured_blocks) -> inventory

1. Build known set:
   - matched_figures with integer figure_number
   - namespace == main (via _extract_figure_marker on their text)
   - not has_s_prefix
   - unique numbers only

2. Build eligible unknown set:
   - matched_figures with figure_number is None
   - namespace == main
   - legend_block_id exists
   - asset_block_ids non-empty
   - settlement_type in accepted set
   - not vetoed by frontmatter keywords
   - legend_bbox resolvable

3. If len(eligible_unknowns) == 0:
   → write "no_eligible_unknowns" skip reason, return

4. If len(known_main) == 0 or min(known_main) != 2:
   → write appropriate skip reason, return

5. Eligible unknown count check:
   - exactly 1 eligible unknown → OK
   - > 1 → write "multiple_eligible_unknowns", return

6. Order check:
   - compute order_key for unknown and first_known
   - if unknown.order_key >= first_known.order_key:
     → write "unknown_not_before_first_known", return

7. Noise check:
   - scan matched_figures, held_figures, ambiguous_figures between
     unknown and first_known by order_key
   - if any exists → skip (first release conservatism)

8. Infer:
   - update matched_figures item with number_inference metadata
   - update corresponding figure_legends item
   - write "accepted" status
```

### Verification

1. **N6XCZD25 regression**:
   - `matched_figures[i]` for Figure 1 has `figure_number == 1`, `figure_id == "figure_001"`
   - No `figure_unknown_*` in matched_figures
   - `inventory["figure_number_inference"]["status"] == "accepted"`
   - Reader produces `reader_figure_id == "figure_001_reader"` for that asset
   - Reader `figure_number == 1`
   - Reader `strict_source == "matched_figures"`
   - Fulltext render does not contain `figure_unknown`
   - Fulltext render does not contain unresolved `visual_group_{page}_{asset}_reader` for that asset

2. **Frontmatter veto**:
   - known=[2,3,4], two unnumbered — one is graphical abstract (text contains "graphical abstract")
   - Only the non-vetoed eligible matched figure gets number 1
   - Vetoed item unchanged

3. **Supplementary isolation A**:
   - known supplementary=[1], known main=[2,3], eligible main unknown=1 before Figure 2
   - → infer main Figure 1; S1 does not enter known main set

4. **Supplementary isolation B**:
   - known supplementary=[1], known main=[2,3], eligible main unknown=0
   - → no-op; supplementary S1 does not affect main sequence

5. **Mid-gap deferral**:
   - known=[1,3,4], one unnumbered between 1 and 3
   - First release: skip, reason `known_min_not_2`

6. **legend_bbox fallback**:
   - matched item without `legend_bbox` → lookup succeeds via structured_blocks → inference proceeds
   - matched item where all 3 lookups fail → skip, reason `missing_legend_bbox`

7. **Strict/reader consistency**:
   - `matched_figures.figure_number`, `matched_figures.figure_id`, reader `figure_number`, `reader_figure_id` all reflect inferred number
   - Fulltext embed no longer shows `figure_unknown`

### Implementation Notes

- `_infer_missing_main_figure_numbers(inventory, structured_blocks) -> dict` — returns updated inventory
- No new dependencies
- `_extract_figure_marker()` can be adapted from existing `_FIGURE_NUMBER_PATTERN`, but must NOT strip `S` prefix silently
- `_resolve_legend_bbox()` is a new helper that tries 3 fallbacks
- `_FRONTMATTER_VISUAL_VETO` is a module-level tuple for easy extension

### Changes vs Original Spec

| Original | Revised |
|----------|---------|
| Integration: after inventory write | Integration: inside `build_figure_inventory()`, after `_promote_sequence_matches()`, before `compute_figure_legend_completeness()` |
| Mutation: write into `marker_signature.number` | Mutation: add `figure_number` + `number_inference` metadata, leave `marker_signature` untouched |
| Gap: any gap, any position | Gap: leading `[1]` only |
| Candidate: any unnumbered legend | Candidate: `matched_figures` only, with asset+legend block IDs, no frontmatter veto |
| Supplementary: brief note | Supplementary: explicit `_extract_figure_marker()` returning structured dict with `has_s_prefix` |
| Order: assumed `legend_bbox` on item | Order: 3-tier lookup via structured_blocks/figure_legends, skip if unresolvable |
| Name: sequential gap-fill fallback | Name: `_infer_missing_main_figure_numbers()` (no collision with `_promote_sequence_matches`) |
| No skip logging | `inventory["figure_number_inference"]` with status+reason for every invocation |
