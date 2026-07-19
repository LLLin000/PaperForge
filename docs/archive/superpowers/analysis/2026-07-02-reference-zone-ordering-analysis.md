# Reference Zone & Ordering — Root Cause Analysis

> **Date:** 2026-07-02  
> **Scope:** 50-paper scan → 14 with issues (28%) → deep-dive on all 14

---

## Summary of Findings

| # | Pattern | Root Cause | Impact | Fix |
|---|---------|-----------|--------|-----|
| P0 | **Ref blocks silently dropped from fulltext** | `block_page_by_id` flat-dict collision in `ocr_render.py:1010-1022` | ~60% of all missing refs | Use `table.get("page")` instead of cross-page lookup |
| P1 | **Backmatter intrudes into ref section** | `_reorder_tail_run` Phase 4b (line 646-651) assigns unclaimed body_pool to ref_section | Content like "Address correspondence" appears between refs | Route body_pool in `tail_nonref_hold_zone` to backmatter, not refs |
| P2 | **skip_section_grouping places non_ref before refs** | Multi-column pages without ref_heading emit `non_ref + refs + backmatter` | "Received/Accepted" appears before trailing refs on same page | Minor — page-tied non_ref content naturally precedes trailing refs |
| P3 | **Page continuation markers classified as reference_item** | Narrow blocks ("13 of 18") matched `reference_like` style family | Pollutes ref count (5-6 per paper), doesn't lose real refs | Tighten reference_like gate for width < 200 && no citation content |
| P4 | **Unexplained ref loss (3 papers)** | 95FDVE4W ref 2, WV2FF4NV ref 9, 58UFL9UN refs 9,30,31 | 5 refs lost, mechanism unknown | Needs deeper render-loop debug |

---

## P0: block_page_by_id Collision (CRITICAL)

### Location
`paperforge/worker/ocr_render.py`, lines 1010-1022 (key construction) and 1438-1442 (consumption filter).

### Root Cause
`block_page_by_id` is built as a **flat dict keyed by block_id alone** (a per-page integer, not globally unique):

```python
# Line 1010-1015 — last-write-wins collision
block_page_by_id: dict[str | int, int | None] = {}
for block in structured_blocks:
    bid = block.get("block_id")
    page = block.get("page")
    block_page_by_id[bid] = page       # OVERWRITES earlier entries
    block_page_by_id[str(bid)] = page
```

When `consumed_table_block_keys` is built (lines 1017-1022), each table's `consumed_block_ids` is paired with the **globally resolved page** from this dict — not the table's actual page:

```python
for table in table_inventory.get("tables", []):
    for block_id in table.get("consumed_block_ids", []):
        page = block_page_by_id.get(block_id, table.get("page"))  # BUG
        consumed_table_block_keys.add((page, block_id))
```

If the same integer block_id appears on a later page (e.g. a reference page), `block_page_by_id` returns the WRONG page for the table's consumed blocks. This causes the render loop's filter at line 1438-1442 to silently skip reference items whose block_id collides with a table's consumed block_id.

### Confirmed Affected Refs

| Paper | Missing Refs | Table Page | Ref Page | Colliding BlockIDs |
|-------|-------------|-----------|----------|-------------------|
| 37LK5T97 | 100, 101 | p12 (Table 4) | p20 | 2, 3 |
| B43QSAJP | 17, 18 | p5 | p22 | 5, 6 |
| 62LTMCI8 | 139-143 | p4/p5/p7/p8/p9/p11 | p18 | 2-6 |
| 4KCHGV2Z | 3-5, 7-8 | p2, p7 | p8 | 12-17 |
| 58UFL9UN | 120, 121 | p4 | p13 | 7, 8 |
| JQMRCEXY | 16-20 | p5, p6 | p9 | 4-8 |
| **Total** | **~20 refs** | | | |

### Verifiable Effect
In all cases, the missing refs **exist** in structured blocks as `reference_item`, `zone=reference_zone`, `render_default=True`, `role_verification_status=ACCEPT`. They are in the reference zone artifact (`item_block_ids`). They reach `ordered_blocks`. They are silently dropped by the `consumed_table_block_keys` filter because `(page, block_id)` matches a table's consumed entry with the wrong page.

### Fix
Replace line 1021 with the table's own page:

```python
# Before:
page = block_page_by_id.get(block_id, table.get("page"))

# After:
page = table.get("page")  # consumed blocks exist on the table's page
```

The `consumed_block_ids` for a table (caption + asset) always live on the same page as the table. The cross-page lookup is unnecessary and introduces the collision.

---

## P1: Backmatter Intrusion into Reference Zone

### Location
`paperforge/worker/ocr_render.py`, `_reorder_tail_run` Phase 4b, lines 633-653.

### Mechanism
On pages where `skip_section_grouping=True` (ref items present but no reference heading), body_pool blocks are classified. If a `body_paragraph` block doesn't match any backmatter section heading, it falls through to:

```python
elif ref_section is not None and not _needs_synthetic_ref:
    ref_section["bodies"].append(body)
```

Observed in 37LK5T97 page 20: "Address correspondence to:", "E-mail:", "Received/Accepted" are `body_paragraph` in `tail_nonref_hold_zone`. No backmatter heading on page 20 → they leak into `ref_section["bodies"]`. Since they have no numeric prefix, `_ref_number_sort_key` sorts them to the end. But on skip_section_grouping pages, `non_ref` content appears BEFORE `refs`, so the backmatter appears at the top of page 20.

### Impact
Content ordering looks wrong — "Address correspondence" appears between ref 99 (page 19) and ref 100+ (page 20). The backmatter should be after all refs.

### Fix Direction
Blocks with `zone=tail_nonref_hold_zone` should be routed to a separate backmatter section or emitted as `non_tail_pass` rather than falling into `body_pool` → `ref_section`.

---

## P2: skip_section_grouping Non-ref Ordering

### Location
`_reorder_tail_run` lines 524-532.

### Mechanism
When skip_section_grouping=True:
```python
non_ref = [b for b in tail_blocks if b.get("role") not in ref_roles ...]
refs = [b for b in tail_blocks if b.get("role") in ref_roles]
refs.sort(key=_ref_number_sort_key)
return non_ref + refs + backmatter + fnotes, carried_ref, carried_backmatter
```

The output places ALL `non_ref` blocks BEFORE `refs`. On a page with mixed content (like backmatter continuation + refs), the backmatter appears first.

### Impact
Minor — per-page ordering is technically correct for the reading flow, but when the page transition from refs (page X) to backmatter + refs (page X+1) happens, the backmatter appears to "jump in front" of the remaining refs.

---

## P3: Page Continuation Markers as reference_item

### Location
Style family assignment (`ocr_families.py`).

### Manifestation
Blocks with narrow width (38-61px) containing text like "13 of 18" are classified as `style_family=reference_like` and assigned `role=reference_item`. They have NO actual reference content — they're page numbering artifacts.

### Affected Papers
| Paper | Count | Sample |
|-------|-------|--------|
| 62LTMCI8 | 6 | "13 of 18" through "18 of 18" |
| TXMVULD7 | 5 | "12 of 16" through "16 of 16" |
| JQMRCEXY | 2 | "8 of 9", "9 of 9" |

### Impact
Inflates reference item count by 5-6 per paper. Does NOT cause missing refs or ordering issues — the narrow items sort to the end by lexicographic order and don't displace real refs.

### Fix Direction
In `ocr_families.py` or `ocr_scores.py`, add a gate: if block text matches `r"^\d+\s+of\s+\d+$"` OR bbox width < 100 AND text matches a page-marker pattern, reject `reference_like` classification.

---

## P4: Unexplained Ref Loss (3 papers)

These papers have ref blocks that exist in structured blocks with correct role but don't appear in fulltext, and the block_page_by_id collision doesn't apply (no table consumption hit).

| Paper | Missing | Block | Page | Render Default |
|-------|---------|-------|------|---------------|
| 95FDVE4W | Ref 2 | bid=11, p16 | No collision | True |
| WV2FF4NV | Ref 9 | bid=39, p19 | block_page_by_id→p20 | True |
| 58UFL9UN | Refs 9,30,31 | bid=26,47,48, p10 | bid=26 resolves→p13 | True |

WV2FF4NV and 58UFL9UN have block_page_by_id collision even without table consumption — the dict stores wrong page for that bid. This COULD affect other lookups in the render loop that use `block_page_by_id` (e.g. `consumed_caption_keys`). Needs further investigation.

---

## Cross-Cutting: Column Layout Accuracy

Analysis of tail_reading_order segments for 37LK5T97 page 20:
- **Segment 8** (col 0, left column): bid=0 (noise), refs 100-110 (bid=2-12) — correct
- **Segment 9** (col 1, right column): bid=1 (noise), refs 111-118 (bid=13-20), body_paragraph (bid=21-23) — correct

All blocks are within their correct segments. No column assignment errors found. The remaining ColumnLayoutAccuracy agent data suggests other multi-column papers (B43QSAJP, 24A2QUAH) also have accurate column assignments.

---

## Prioritized Fix List

| Priority | Fix | Files | Lines | Effort |
|----------|-----|-------|-------|--------|
| **P0** | Use `table.get("page")` instead of `block_page_by_id` lookup | `ocr_render.py` | 1021 | 1 line |
| **P1** | Route `tail_nonref_hold_zone` body_paragraph away from ref_section | `ocr_render.py` | 571-579, 646-651 | ~5 lines |
| **P2** | Add page-marker gate to `reference_like` classification | `ocr_families.py` | ~330 | ~5 lines |
| **P3** | Investigate remaining unexplained losses (P4) | debug render loop | 1384-1600 | deeper |
