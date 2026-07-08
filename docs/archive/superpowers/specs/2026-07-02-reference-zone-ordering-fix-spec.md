# Reference Zone Fix — Specification v2

> **Status:** Spec complete — root causes validated, implementation contract hardened  
> **Problem rate:** 14/50 papers (28%) have ref ordering/leakage anomalies  
> **Approach:** 5 commits, each independently verifiable

---

## Commit 1: P0 — Table Consumed Key Page Collision

### Root Cause

`ocr_render.py:1010-1015` builds a flat `block_page_by_id` dict keyed by per-page `block_id` (not globally unique). Last-write-wins overwrites earlier pages' entries. Then at line 1017-1022, `consumed_table_block_keys` uses this dict to resolve each table's `consumed_block_ids` to a page — resolving to the wrong page when the same `block_id` exists on a later page. The render loop at line 1438-1442 then silently skips ref blocks whose `(page, block_id)` matches the consumed key.

### Fix Contract

**Do NOT** simply swap to `table.get("page")`. Build consumed keys with **explicit per-block page** from table inventory fields, not from a flat dict.

```python
def _add_consumed_key(
    keys: set[tuple[int | None, str | int]],
    page: int | None,
    block_id: str | int,
) -> None:
    """Add (page, block_id) and (page, str(block_id)) to consumed keys."""
    if block_id is None or block_id == "":
        return
    keys.add((page, block_id))
    keys.add((page, str(block_id)))
```

Then in the table loop:

```python
consumed_table_block_keys: set[tuple[int | None, str | int]] = set()
for table in table_inventory.get("tables", []):
    table_page = table.get("page")

    # Caption block — always on table's page
    _add_consumed_key(consumed_table_block_keys, table_page, table.get("caption_block_id"))

    # Asset segments — each has its own page (caption ±1)
    for seg in table.get("segments", []):
        _add_consumed_key(consumed_table_block_keys, seg.get("page"), seg.get("asset_block_id"))

    # Note blocks on same page
    for bid in table.get("note_block_ids", []):
        _add_consumed_key(consumed_table_block_keys, table_page, bid)

    # Bridge/continuation blocks — same page as caption
    for bid in table.get("bridge_block_ids", []):
        _add_consumed_key(consumed_table_block_keys, table_page, bid)

    # Legacy fallback: consumed_block_ids table.page (no global lookup)
    for bid in table.get("consumed_block_ids", []):
        _add_consumed_key(consumed_table_block_keys, table_page, bid)
```

**Long-term contract:** `ocr_tables.py` should directly produce `consumed_block_keys: [{"page": ..., "block_id": ...}]`. Render should only consume this page-keyed output, never re-derive page from flat dict.

### Verification

```
test_table_consumed_block_ids_do_not_drop_same_id_reference_on_later_page  → P0 fix
test_table_caption_still_consumed                                            → regression
```

**Papers to re-verify:** 37LK5T97 (refs 100-101), B43QSAJP (17-18), 62LTMCI8 (139-143), 4KCHGV2Z (3-5, 7-8), 58UFL9UN (120-121), JQMRCEXY (16-20)

---

## Commit 2: P1 — `skip_section_grouping` Ordering

### Root Cause

When `skip_section_grouping=True` (pages with `reference_item` blocks but no `reference_heading`), the code emits `non_ref + refs + backmatter + fnotes`. This places `body_paragraph` blocks in `zone=tail_nonref_hold_zone` ("Address correspondence to:", "E-mail:", "Received/Accepted") before refs on the same page.

### Fix Contract

1. **`backmatter_roles`** must include `backmatter_boundary_heading`:

```python
backmatter_roles = frozenset({
    "backmatter_body",
    "backmatter_heading",
    "backmatter_boundary_heading",
})
```

2. **Ordering**: `ordinary_non_ref + refs + backmatter + tail_backmatter + fnotes`

3. **Tail backmatter detection**: Use `zone=tail_nonref_hold_zone` as primary signal, pattern match as weak fallback:

```python
_TAIL_BACKMATTER_CONTINUATION_PATTERN = re.compile(
    r"^(?:address correspondence|correspondence|e-?mail|email|"
    r"received|accepted|published|available online|"
    r"author contributions?|conflicts? of interest|funding|"
    r"acknowledg(?:e)?ments?)\b",
    re.IGNORECASE,
)

def _is_tail_backmatter_continuation(block: dict) -> bool:
    zone = str(block.get("zone") or "")
    if zone == "tail_nonref_hold_zone":
        return True
    text = str(block.get("text") or block.get("block_content") or "").strip()
    return bool(_TAIL_BACKMATTER_CONTINUATION_PATTERN.match(text))
```

4. **Modify skip branch:**

```python
if skip_section_grouping:
    ref_roles = frozenset({"reference_heading", "reference_item", "reference_body"})
    backmatter_roles = frozenset({...})

    non_ref_all = [b for b in tail_blocks if b.get("role") not in ref_roles
                   and b.get("role") not in backmatter_roles and b.get("role") != "footnote"]
    refs = sorted([b for b in tail_blocks if b.get("role") in ref_roles], key=_ref_number_sort_key)
    backmatter = [b for b in tail_blocks if b.get("role") in backmatter_roles]
    fnotes = [b for b in tail_blocks if b.get("role") == "footnote"]

    tail_backmatter = [b for b in non_ref_all if _is_tail_backmatter_continuation(b)]
    ordinary_non_ref = [b for b in non_ref_all if not _is_tail_backmatter_continuation(b)]

    return (ordinary_non_ref + refs + backmatter + tail_backmatter + fnotes,
            carried_ref, carried_backmatter)
```

### Verification

```
test_skip_section_grouping_places_tail_nonref_after_refs           → positive test
test_skip_section_grouping_keeps_ordinary_nonref_before_refs       → negative test
test_real_backmatter_heading_still_attaches_its_own_body           → funding/ack not orphaned
```

---

## Commit 3: P2 — Phase 4b Tail Nonref Guard (non-skip path)

### Root Cause

In the non-skip path, `body_pool` blocks that fail `_find_owning_heading()` can fall through to `ref_section["bodies"]`. This is the same symptom as P1 but via a different code path.

### Fix Contract

Guard must be placed **after** `_find_owning_heading()` (not before it), so that real backmatter bodies (Funding, Acknowledgments) still attach to their own heading:

```python
tail_backmatter_blocks: list[dict] = []

for body in body_pool:
    idx = _find_owning_heading(body, backmatter_sections, page_width)
    if idx is not None:
        backmatter_sections[idx]["bodies"].append(body)
        continue

    if _is_tail_backmatter_continuation(body):
        tail_backmatter_blocks.append(body)   # NOT orphan_blocks
        continue

    # Original carried_backmatter / ref_section / orphan logic remains
    ...
```

**Emit order** (Phase 5):

```python
result.extend(sec_order_blocks)           # backmatter sections
result.extend(ref_section_blocks)          # references
result.extend(tail_backmatter_blocks)      # ← inserted here, before footnotes
result.extend(footnote_blocks)
result.extend(orphan_blocks)
```

This ensures backmatter continuation appears after refs, not before them.

### Verification

```
test_phase_4b_does_not_swallow_tail_nonref_into_ref_section   → positive
test_funding_body_still_attaches_to_funding_heading            → anti-regression
```

---

## Commit 4: P3 — Page Continuation Marker False Reference

### Root Cause

"X of Y" page markers (61px wide, e.g. "13 of 18", "13. of 18") match `reference_like` style family through three entry points with no exclusion gate.

### Fix Contract

Regex must cover variants seen in real data: `13 of 18`, `13. of 18`, `Page 13 of 18`, `13/18`:

```python
_PAGE_CONTINUATION_MARKER_PATTERN = re.compile(
    r"^(?:page\s*)?\d{1,4}\s*(?:[\.\-–—]?\s+of\s+|/)\s*\d{1,4}$",
    re.IGNORECASE,
)
```

Helper with width gate:

```python
def _looks_like_page_continuation_marker(block: dict) -> bool:
    text = str(block.get("text") or block.get("block_content") or "").strip()
    if not _PAGE_CONTINUATION_MARKER_PATTERN.match(text):
        return False

    bbox = block.get("bbox") or block.get("block_bbox") or []
    width = float(bbox[2]) - float(bbox[0]) if len(bbox) >= 4 else None
    layout_sig = block.get("layout_signature") or {}
    if layout_sig.get("width") is not None:
        width = float(layout_sig["width"])

    if width is not None:
        return width < 180
    return len(text.split()) <= 3
```

Gate at three entry points in `ocr_families.py`:

```python
# In _is_reference_family_candidate()
if _looks_like_page_continuation_marker(block):
    return False

# In _reference_anchor_matches_block()
if _looks_like_page_continuation_marker(block):
    return False

# In _has_reference_text_structure()
if _looks_like_page_continuation_marker(block):
    return False
```

### Verification

```
test_page_continuation_marker_is_not_reference  → "13 of 18", "13. of 18", "Page 13 of 18", "13/18"
test_real_reference_is_still_reference           → "13. Smith J, Wang L. Cartilage repair in 2018."
```

**Papers to re-verify:** 62LTMCI8, TXMVULD7, JQMRCEXY — fake refs gone.

---

## Commit 5: P4 — Same-Page Ref Blocks Before Reference Heading

### Root Cause

`_order_tail_blocks` (via `_sort_blocks_by_column`) can place some `reference_item` blocks ABOVE the `reference_heading` on the same page — but only for pages that pass the tail-page gate (`_body_count <= _tail_count`). Pages that fail the gate keep original reading order, which may also place refs before the heading if the PDF's internal order does so.

### Fix Contract

**Do NOT** only fix column-sort. Use a unified helper applied to **all page block lists** that have a `reference_heading`:

```python
def _force_reference_heading_before_same_page_refs(page_blocks: list[dict]) -> list[dict]:
    """Reorder page blocks so reference_item/reference_body always follow
    the first reference_heading on the same page. Non-ref blocks are unchanged."""
    headings = [b for b in page_blocks if b.get("role") == "reference_heading"]
    if not headings:
        return page_blocks

    ref_roles = {"reference_item", "reference_body"}
    refs = [b for b in page_blocks if b.get("role") in ref_roles]
    if not refs:
        return page_blocks

    first_heading = headings[0]
    others = [b for b in page_blocks if b is not first_heading and b.get("role") not in ref_roles]

    # Insert all refs immediately after the heading
    out: list[dict] = []
    inserted = False
    for b in others:
        out.append(b)
        if b is first_heading:
            inserted = True
            out.extend(sorted(refs, key=_ref_number_sort_key))

    if not inserted:
        # Fallback: heading wasn't in `others` (unlikely), find original position
        heading_idx = page_blocks.index(first_heading)
        before = [b for b in page_blocks[:heading_idx] if b.get("role") not in ref_roles]
        after = [b for b in page_blocks[heading_idx:] if b.get("role") not in ref_roles and b is not first_heading]
        return before + [first_heading] + sorted(refs, key=_ref_number_sort_key) + after

    return out
```

Apply in `_order_tail_blocks` AFTER column-sort, before passing to `_reorder_tail_run`:

```python
if page in tail_pages:
    pw = page_widths.get(page, 1200)
    sorted_blocks = _sort_blocks_by_column(page_blocks, pw)
    sorted_blocks = _force_reference_heading_before_same_page_refs(sorted_blocks)
    ordered, carried_ref, carried_backmatter = _reorder_tail_run(
        sorted_blocks, ...
    )
    result.extend(ordered)
```

### Verification

```
test_refs_on_heading_page_are_rendered_after_heading  → positive
test_non_ref_blocks_not_moved_by_guard                 → negative
```

**Papers to re-verify:** 95FDVE4W (ref 2), WV2FF4NV (ref 9), 58UFL9UN (refs 9, 30, 31)

---

## Regression Testing: Final Paper Checklist

| Paper | Current State | Expected After All Fixes |
|-------|--------------|-------------------------|
| 37LK5T97 | missing 100, 101; backmatter intrudes | 118 refs in section, continuous; backmatter after refs |
| B43QSAJP | missing 17, 18 | 54 refs, continuous |
| 62LTMCI8 | missing 139-143; 6 fake "X of 18" | 152 refs, no fake refs |
| 4KCHGV2Z | missing 3-5, 7-8, 20-22 | 25 refs, continuous |
| 58UFL9UN | missing 9,30,31,115,116,120,121 | 132 refs, continuous |
| TXMVULD7 | missing 39; 5 fake "X of 16" | 73 refs, no fake refs |
| JQMRCEXY | missing 16-20; 2 fake refs | 21 refs, no fake refs |
| 95FDVE4W | ref 2 before heading | 24 refs in section |
| WV2FF4NV | ref 9 before heading | 77 refs in section |

### Unit Tests

```
test_table_consumed_block_ids_do_not_drop_same_id_reference_on_later_page  → P0
test_table_caption_still_consumed                                           → P0 regression
test_skip_section_grouping_places_tail_nonref_after_refs                    → P1
test_skip_section_grouping_keeps_ordinary_nonref_before_refs                → P1
test_real_backmatter_heading_still_attaches_its_own_body                    → P1 regression
test_phase_4b_does_not_swallow_tail_nonref_into_ref_section                → P2
test_funding_body_still_attaches_to_funding_heading                        → P2 regression
test_page_continuation_marker_is_not_reference                              → P3
test_real_reference_is_still_reference                                      → P3 regression
test_refs_on_heading_page_are_rendered_after_heading                       → P4
test_non_ref_blocks_not_moved_by_guard                                      → P4 regression
```

## Appendix: Full Scan Results (50 papers)

| Verdict | Count | Key |
|---------|-------|-----|
| ✅ Clean | 36 | Various |
| ⚠️ P0 (block_page_by_id) | 6 | 37LK5T97, B43QSAJP, 62LTMCI8, 4KCHGV2Z, 58UFL9UN, JQMRCEXY |
| ⚠️ P1 (skip_section_grouping) | 1 | 37LK5T97 |
| ⚠️ P3 (page marker) | 3 | 62LTMCI8, TXMVULD7, JQMRCEXY |
| ⚠️ P4 (ref before heading) | 3 | 95FDVE4W, WV2FF4NV, 58UFL9UN |
| Uses `[N]` format (audit false positive) | 5 | 53B47JM8, 49NUE2G7, 24A2QUAH, X6PQAH4V, PP76T2EY | 
