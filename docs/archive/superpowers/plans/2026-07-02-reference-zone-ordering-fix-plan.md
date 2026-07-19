# Implementation Plan: Reference Zone Fixes

> **Based on:** `docs/superpowers/specs/2026-07-02-reference-zone-ordering-fix-spec.md`  
> **Commits:** 5 sequential, independently verifiable  
> **Target:** 9 papers verified clean after all commits  
> **Tests:** 12 unit tests (8 positive + 4 anti-regression)

---

## Commit 1: P0 — Table Consumed Key Page Collision

### Files
- `paperforge/worker/ocr_render.py` — consumed_table_block_keys construction (lines ~1010-1022)

### Changes

**1.1 — Add `_add_consumed_key` helper** before `render_fulltext_markdown` or as module-level function:

```python
def _add_consumed_key(
    keys: set[tuple[int | None, str | int]],
    page: int | None,
    block_id: str | int,
) -> None:
    if block_id is None or block_id == "":
        return
    keys.add((page, block_id))
    keys.add((page, str(block_id)))
```

**1.2 — Rewrite consumed_table_block_keys construction** in `render_fulltext_markdown()`.

Remove lines that build `block_page_by_id` (the flat dict). Replace the table-consumption loop with:

```python
consumed_table_block_keys: set[tuple[int | None, str | int]] = set()

def _add_and_remember(page, block_id):
    if block_id is None or block_id == "":
        return
    _add_consumed_key(consumed_table_block_keys, page, block_id)
    keyed_bid_strs.add(str(block_id))

for table in table_inventory.get("tables", []):
    table_page = table.get("page")
    keyed_bid_strs: set[str] = set()

    # Caption block — always on table's page
    _add_and_remember(table_page, table.get("caption_block_id"))

    # Asset segments — each has its own page (caption ±1)
    for seg in table.get("segments", []):
        _add_and_remember(seg.get("page"), seg.get("asset_block_id"))

    # Note blocks on same page
    for bid in table.get("note_block_ids", []):
        _add_and_remember(table_page, bid)

    # Bridge/continuation blocks — same page as caption
    for bid in table.get("bridge_block_ids", []):
        _add_and_remember(table_page, bid)

    # Legacy fallback: only ids NOT already page-keyed
    for bid in table.get("consumed_block_ids", []):
        if bid is None or bid == "":
            continue
        if str(bid) in keyed_bid_strs:
            continue
        _add_consumed_key(consumed_table_block_keys, table_page, bid)
```

**1.3 — Cleanup:** If `block_page_by_id` is no longer used elsewhere in the function, remove its construction loop. If still used (e.g. for `_block_page_map` or `_block_text_by_bid`), keep it but do NOT use it for consumed key resolution.

### Verification

```bash
# 1. Parse check
python -c "import ast; ast.parse(open('paperforge/worker/ocr_render.py').read()); print('OK')"

# 2. Unit test
python -m pytest tests/test_ocr_render.py::test_table_consumed_block_ids_do_not_drop_same_id_reference_on_later_page -v
python -m pytest tests/test_ocr_render.py::test_cross_page_table_asset_id_does_not_consume_same_id_on_caption_page -v

# 3. Paper regression: rebuild 37LK5T97, check refs 100-101 appear
python scripts/dev/ocr_rebuild_paper.py 37LK5T97
grep "100\. Lin" /path/to/ocr/37LK5T97/fulltext.md

# 4. Repeat for B43QSAJP (refs 17-18), 62LTMCI8 (139-143), 4KCHGV2Z (3-5,7-8),
#    58UFL9UN (120-121), JQMRCEXY (16-20)
```

---

## Commit 2: P1 — `skip_section_grouping` Ordering

### Files
- `paperforge/worker/ocr_render.py` — `_reorder_tail_run()` skip_section_grouping branch (lines ~524-532)

### Changes

**2.1 — Add `_is_tail_backmatter_continuation` helper** in `ocr_render.py`:

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

**2.2 — Rewrite `skip_section_grouping` branch:**

```python
if skip_section_grouping:
    ref_roles = frozenset({"reference_heading", "reference_item", "reference_body"})
    backmatter_roles = frozenset({
        "backmatter_body",
        "backmatter_heading",
        "backmatter_boundary_heading",
    })

    non_ref_all = [
        b for b in tail_blocks
        if b.get("role") not in ref_roles
        and b.get("role") not in backmatter_roles
        and b.get("role") != "footnote"
    ]

    refs = [b for b in tail_blocks if b.get("role") in ref_roles]
    refs.sort(key=_ref_number_sort_key)

    backmatter = [b for b in tail_blocks if b.get("role") in backmatter_roles]
    fnotes = [b for b in tail_blocks if b.get("role") == "footnote"]

    tail_backmatter = [b for b in non_ref_all if _is_tail_backmatter_continuation(b)]
    ordinary_non_ref = [b for b in non_ref_all if not _is_tail_backmatter_continuation(b)]

    return (ordinary_non_ref + refs + backmatter + tail_backmatter + fnotes,
            carried_ref, carried_backmatter)
```

### Verification

```bash
# Unit tests
python -m pytest tests/test_ocr_render.py::test_skip_section_grouping_places_tail_nonref_after_refs -v
python -m pytest tests/test_ocr_render.py::test_skip_section_grouping_keeps_ordinary_nonref_before_refs -v
python -m pytest tests/test_ocr_render.py::test_real_backmatter_heading_still_attaches_its_own_body -v

# Paper: 37LK5T97 page 20 — "Address correspondence" must appear after refs 100-118
python scripts/dev/ocr_rebuild_paper.py 37LK5T97
# Check that refs 100-118 appear before "Address correspondence" in fulltext
```
```python
tail_backmatter_blocks: list[dict] = []

# Phase 4b — geometric body attachment
for body in body_pool:
    idx = _find_owning_heading(body, backmatter_sections, page_width)
    if idx is not None:
        backmatter_sections[idx]["bodies"].append(body)
        continue

    if _is_tail_backmatter_continuation(body):
        tail_backmatter_blocks.append(body)
        continue

    if carried_backmatter is not None:
        bbox = body.get("bbox") or body.get("block_bbox")
        if bbox and len(bbox) >= 4:
            body_top = bbox[1]
            if (first_local_anchor_top is None or body_top < first_local_anchor_top) and (
                not ref_heading or body_top < ref_bottom
            ):
                carried_bodies.append(body)
                continue

    if ref_section is not None and not _needs_synthetic_ref:
        if ref_section is carried_ref:
            ref_section["bodies"].append(body)
            orphan_blocks.append(body)
        else:
            ref_section["bodies"].append(body)
    else:
        orphan_blocks.append(body)
```
        tail_backmatter_blocks.append(body)
        continue


**3.2 — Update emit order** (Phase 5, after `ref_section` emission):

```python
result.extend(non_tail_pass)
result.extend(carried_bodies)
# ... backmatter sections ...
# ... ref section ...
result.extend(tail_backmatter_blocks)   # ← NEW: between refs and footnotes
result.extend(footnote_blocks)
result.extend(orphan_blocks)
```

## Commit 3: P2 — Phase 4b Tail Nonref Guard

### Files
- `paperforge/worker/ocr_render.py` — `_reorder_tail_run()` Phase 4b body_pool loop (lines ~633-653)

### Changes

(see code block above — guard after `_find_owning_heading()`, `tail_backmatter_blocks`, emit between refs and footnotes)


### Verification

```bash
# Unit tests
python -m pytest tests/test_ocr_render.py::test_phase_4b_does_not_swallow_tail_nonref_into_ref_section -v
python -m pytest tests/test_ocr_render.py::test_funding_body_still_attaches_to_funding_heading -v

# Regression: 37LK5T97 still clean after commit 2 + commit 3
```

---

## Commit 4: P3 — Page Continuation Marker

### Files
- `paperforge/worker/ocr_families.py` — 3 entry points

### Changes

**4.1 — Add helper** at module level in `ocr_families.py`:

```python
_PAGE_CONTINUATION_MARKER_PATTERN = re.compile(
    r"^(?:page\s*)?\d{1,4}\s*(?:[\.\-–—]?\s+of\s+|/)\s*\d{1,4}$",
    re.IGNORECASE,
)

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

**4.2 — Gate at three entry points:**

```python
# In _is_reference_family_candidate(), early return:
if _looks_like_page_continuation_marker(block):
    return False

# In _reference_anchor_matches_block(), early return:
if _looks_like_page_continuation_marker(block):
    return False

# In _has_reference_text_structure(), early return:
if _looks_like_page_continuation_marker(block):
    return False
```

### Verification

```bash
# Unit tests
python -m pytest tests/test_ocr_families.py::test_page_continuation_marker_is_not_reference -v
python -m pytest tests/test_ocr_families.py::test_real_reference_is_still_reference -v

# Paper rebuild
python scripts/dev/ocr_rebuild_paper.py 62LTMCI8
# Check "13 of 18" blocks no longer have role=reference_item

# Also check TXMVULD7, JQMRCEXY
```

---

## Commit 5: P4 — Same-Page Ref Blocks Before Reference Heading

### Files
- `paperforge/worker/ocr_render.py` — `_order_tail_blocks()` AND non-tail page path

### Changes

**5.1 — Add helper** in `ocr_render.py`:

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
    heading_idx = page_blocks.index(first_heading)

    before = [b for b in page_blocks[:heading_idx] if b.get("role") not in ref_roles]
    after = [b for b in page_blocks[heading_idx + 1:] if b.get("role") not in ref_roles]

    return before + [first_heading] + sorted(refs, key=_ref_number_sort_key) + after
```

**5.2 — Fix early return in `_order_tail_blocks()`** for non-tail pages with ref heading:

Current code returns early when no tail pages detected, skipping pages with `reference_heading` + `reference_item` that don't qualify as tail pages. The fix replaces the early return:

```python
# Before:
if not tail_pages:
    return blocks

# After:
if not tail_pages:
    result: list[dict] = []
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is None:
            result.append(block)
        else:
            by_page.setdefault(p, []).append(block)
    for page in sorted(by_page):
        result.extend(_force_reference_heading_before_same_page_refs(by_page[page]))
    return result
```

**5.3 — Apply helper in tail page path:**

```python
if page in tail_pages:
    pw = page_widths.get(page, 1200)
    sorted_blocks = _sort_blocks_by_column(page_blocks, pw)
    sorted_blocks = _force_reference_heading_before_same_page_refs(sorted_blocks)  # ← NEW
    ...
```

**5.4 — Update `_page_has_ref_items`** to also check `reference_body`:

```python
# Before:
_page_has_ref_items = any(b.get("role") == "reference_item" for b in sorted_blocks)

# After:
_page_has_ref_items = any(b.get("role") in {"reference_item", "reference_body"} for b in sorted_blocks)
```


### Verification

```bash
# Unit tests
python -m pytest tests/test_ocr_render.py::test_refs_on_heading_page_are_rendered_after_heading -v
python -m pytest tests/test_ocr_render.py::test_non_ref_blocks_not_moved_by_guard -v

# Paper rebuild
python scripts/dev/ocr_rebuild_paper.py 95FDVE4W
grep "2\. Bedi" /path/to/ocr/95FDVE4W/fulltext.md
# Ref 2 must appear after "## References" heading

# Also verify WV2FF4NV (ref 9), 58UFL9UN (refs 9, 30, 31)
```

---

## Full Regression

After all 5 commits, run:

```bash
# 1. All unit tests
python -m pytest tests/ -q

# 2. All 9 regression papers
for key in 37LK5T97 B43QSAJP 62LTMCI8 4KCHGV2Z 58UFL9UN JQMRCEXY TXMVULD7 95FDVE4W WV2FF4NV; do
    python scripts/dev/ocr_rebuild_paper.py $key
done

# 3. Run reference-zone audit
python scripts/dev/ocr_reference_zone_audit.py --limit=50
# Expect: 0 papers with ref ordering issues
```

**Unit test checklist (12 total):**

| # | Test | Commit |
|---|------|--------|
| 1 | `test_table_consumed_block_ids_do_not_drop_same_id_reference_on_later_page` | P0 |
| 2 | `test_cross_page_table_asset_id_does_not_consume_same_id_on_caption_page` | P0 anti-regression |
| 3 | `test_table_caption_still_consumed` | P0 regression |
| 4 | `test_skip_section_grouping_places_tail_nonref_after_refs` | P1 |
| 5 | `test_skip_section_grouping_keeps_ordinary_nonref_before_refs` | P1 |
| 6 | `test_real_backmatter_heading_still_attaches_its_own_body` | P1 regression |
| 7 | `test_phase_4b_does_not_swallow_tail_nonref_into_ref_section` | P2 |
| 8 | `test_funding_body_still_attaches_to_funding_heading` | P2 regression |
| 9 | `test_page_continuation_marker_is_not_reference` | P3 |
| 10 | `test_real_reference_is_still_reference` | P3 regression |
| 11 | `test_refs_on_heading_page_are_rendered_after_heading` | P4 |
| 12 | `test_non_ref_blocks_not_moved_by_guard` | P4 regression |

---

## Effort Estimate

| Commit | Files | Lines Changed | Complexity | Risk |
|--------|-------|--------------|------------|------|
| 1 (P0) | `ocr_render.py` | ~20 add, ~10 remove | Medium | Table note consumption regression |
| 2 (P1) | `ocr_render.py` | ~15 add, ~5 remove | Low | backmatter_roles change is additive |
| 3 (P2) | `ocr_render.py` | ~10 add | Low | Guard after _find_owning_heading is safe |
| 4 (P3) | `ocr_families.py` | ~30 add, ~3 insert | Low | Regex + width gate, covered by tests |
| 5 (P4) | `ocr_render.py` | ~40 add, ~3 insert | Medium | Only moves refs, never deletes |

**Total:** ~100-120 lines changed, 12 new tests, full regression on 9 papers.
