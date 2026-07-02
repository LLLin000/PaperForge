# Page Number Tracing Through PaperForge Pipeline

## 1. Raw OCR Result → `all_results`

**Entry point:** `paperforge/worker/ocr.py` lines 2357-2361 (`run_ocr`)
```
PaddleOCR API returns NDJSON per-line. Each line parsed as JSON["result"] = one page payload.
→ all_results: list[dict], each element = per-page result from PaddleOCR API.
```

The API response structure is stored verbatim at `result.json` (ocr.py line 1801):
```python
write_json(json_dir / "result.json", all_results)
```

**Backfill path** (`ocr_rebuild.py` lines 515-522): reads `result.json` and normalizes:
- If dict → `raw.get("pages", [])` (legacy format)
- If list → use directly

---

## 2. `build_raw_blocks_for_result_lines()` — Page Number Origin

**File:** `paperforge/worker/ocr_blocks.py` lines 465-472

```python
def build_raw_blocks_for_result_lines(paper_id: str, all_results: list[dict]) -> list[dict[str, Any]]:
    rows = []
    page_num = 0
    for payload in all_results:
        for res in payload.get("layoutParsingResults", []):
            page_num += 1
            rows.extend(build_raw_blocks_for_page(paper_id, page_num, res))
    return rows
```

**Key observations:**
- `page_num` starts at **0** and increments **after** the first entry → **first page = 1** (1-indexed)
- **Nested loop**: For each API page payload, it iterates ALL `layoutParsingResults`. If a single page returns >1 result entry, page counting inflates. (In normal PaddleOCR operation, each page produces exactly one `layoutParsingResults` entry.)
- Each result entry gets its own page number, and all blocks from that entry share that page number.

---

## 3. `build_raw_blocks_for_page()` — Direct Page Assignment

**File:** `paperforge/worker/ocr_blocks.py` lines 441-462

```python
def build_raw_blocks_for_page(paper_id: str, page: int, result: dict) -> list[dict[str, Any]]:
    pruned = result.get("prunedResult", {})
    width = pruned.get("width", 0)
    height = pruned.get("height", 0)
    blocks = pruned.get("parsing_res_list", [])
    rows = []
    for i, block in enumerate(blocks):
        rows.append({
            "paper_id": paper_id,
            "page": page,                                            # ← PAGE NUMBER SET HERE
            "block_id": block.get("block_id", f"p{page}_b{i}"),
            "raw_label": block.get("block_label", "unknown"),
            "raw_order": block.get("block_order", i),
            "bbox": block.get("block_bbox", [0, 0, 0, 0]),
            "text": block.get("block_content", "") or "",
            "page_width": width,
            "page_height": height,
            "source": "ocr_raw",
        })
    return rows
```

- `page` parameter is used **verbatim** as the block's page number.
- No offset, no transformation.

---

## 4. `postprocess_ocr_result()` — Parallel Page Counting

**File:** `paperforge/worker/ocr.py` lines 1777-1796

```python
page_num = 0
for page_payload in all_results:
    for res in page_payload.get("layoutParsingResults", []):
        page_num += 1
        render_page_blocks(vault, page_num, res, ...)
```

This is the **SAME** counting logic as `build_raw_blocks_for_result_lines`. Both iterate `all_results` → `layoutParsingResults` in lockstep. `page_num` at the end = total number of `layoutParsingResults` entries = `meta["page_count"]`.

Then sets `meta["page_count"] = page_num` at ocr.py line 2413:
```python
meta["page_count"] = page_num
```

---

## 5. `build_structured_blocks()` — Cover Page Drop (CRITICAL)

**File:** `paperforge/worker/ocr_blocks.py` lines 189-302

**Step 1: Group by page** (lines 200-205):
```python
by_page: dict[int, list[dict]] = {}
for block in raw_blocks:
    page = block.get("page", 1)
    by_page.setdefault(page, []).append(block)

total_pages = max(by_page.keys()) if by_page else 1  # ← original max page (e.g. N)
```

**Step 2: Cover page detection and removal** (lines 297-302):
```python
if _has_preproof_cover_page_one(rows):
    rows = [row for row in rows if (row.get("page", 0) or 0) != 1]
elif _has_nonpreproof_cover_page_one(rows):
    rows = [row for row in rows if (row.get("page", 0) or 0) != 1]
```

**⚠️ OFFSET ROOT CAUSE:** After this drop:
- Blocks with page==1 are **removed entirely**
- Remaining blocks still have their **original page values** (2, 3, ..., N)
- **No re-indexing / renumbering** occurs
- `meta["page_count"]` is still N (set before this function runs)
- `total_pages` was computed from `by_page` (line 205) **before** the drop, so it's still N
- `discover_body_family_anchor(rows, page_count=total_pages)` at line 304 receives the original N

**Detection functions** (lines 129-175):
- `_has_preproof_cover_page_one()` — checks for preproof markers on page 1
- `_has_nonpreproof_cover_page_one()` — checks for cover text markers ("just accepted", etc.) on page 1 without real content

---

## 6. `infer_zones()` — Page-Based Zone Computation

**File:** `paperforge/worker/ocr_document.py` lines 1300-1713

**First surviving page** (line 1430):
```python
first_surviving_page = _first_surviving_page(blocks)
```
Where `_first_surviving_page()` (line 628-630):
```python
def _first_surviving_page(blocks: list[dict]) -> int | None:
    pages = sorted({int(block.get("page", 0) or 0) for block in blocks if int(block.get("page", 0) or 0) > 0})
    return pages[0] if pages else None
```

After cover page drop, this returns **2** (the first remaining page). This is used throughout the zone inference.

**Anchor page selection** (line 1435):
```python
anchor_page = first_surviving_page if first_surviving_page is not None and first_surviving_page <= 2 else 1
```
This correctly handles both cases: uses first_surviving_page when it's 1 or 2 (normal or after cover drop), falls back to 1 for blocksets starting on page 3+.

**Body end page** (line 1536):
```python
body_end_page = first_reference_page - 1 if first_reference_page is not None else max_page
```
A simple page arithmetic: no off-by-one here, but values depend on block page values (which may be shifted after cover drop).

**Frontmatter side zone** (line 1490):
```python
int(block.get("page", 0) or 0) >= first_reference_page - 1
```
Uses `first_reference_page` (from block page values) — consistent within the shifted numbering.

**`page1_candidates`** (lines 1437-1444): Selects blocks whose page matches `anchor_page`. After cover drop, `anchor_page` = first surviving page (e.g., 2), so it processes blocks on that page as "page 1 candidates." The role assignment functions (in `ocr_roles.py`) reference these by checking `page_num == 1` or `page == anchor_page` — this is handled via the `anchor_page` variable, not hardcoded `== 1`.

---

## 7. Page-Based Role Assignment in `ocr_roles.py`

**File:** `paperforge/worker/ocr_roles.py`

Role assignment functions **read `page` from block data directly**:

- **`assign_block_role()`** (line 865+) — receives `block` dict with `"page"` from `build_structured_blocks` pass-through. Checks `block.get("page") or 1` and `page_num == 1` patterns.

- **Hardcoded `page_num == 1` checks** — These fire correctly when page 1 exists, but after cover page drop, they **never fire** because page 1 blocks are gone. Instead, the zone-based logic in `infer_zones()` drives frontmatter handling via `anchor_page`.

- **`_is_backmatter_boundary_heading()`** line 369: uses `page_num` and `total_pages` — works within shifted numbering.

**Evidence strings** contain phrases like `"page-1 article-type label"` (line 906), `"page-1 zone title_zone"` (line 1027), etc. These are metadata labels only; not used for computation.

---

## 8. Role Index — Verbatim Page Propagation

**File:** `paperforge/worker/ocr_index.py` lines 27-35

```python
for block in structured_blocks:
    role = block.get("role", "")
    entry = {
        "paper_id": block.get("paper_id", ""),
        "page": block.get("page", 0),    # ← VERBATIM from block
        ...
    }
```

No transformation. If a block has `page: 5`, it goes into the role index as `page: 5`.

Metadata entries artificially get `"page": 0` (line 54).

---

## 9. Render — Page Marker Generation

**File:** `paperforge/worker/ocr_render.py`

**During body block iteration** (lines 1635-1664):
```python
if block_page != current_page:
    for p in range(first_new_page, block_page):
        lines.append(f"<!-- page {p} -->")
    ...
    lines.append(f"<!-- page {block_page} -->")
```
Emits page markers based on block page values.

**Post-body sweep** (lines 1891-1908):
```python
effective_count = page_count if page_count is not None else max_page
for p in range(1, effective_count + 1):
    if p in emitted_pages:
        continue
    if p > (current_page or 0):
        lines.append(f"<!-- page {p} -->")
```
This iterates from 1 to `page_count` (original N). After cover page drop:
- **Page 1** gets an empty `<!-- page 1 -->` marker (no blocks, no objects)
- Page 2..N get their content (blocks that exist)
- `emitted_pages` count will be N (= page_count), so `validate_ocr_meta` passes

**⚠️ Note:** The render generates `page_count` markers regardless of whether page 1 blocks exist. This is correct for `validate_ocr_meta` (which counts markers), but produces an empty `<!-- page 1 -->` in the markdown output when a cover page was dropped.

---

## 10. `normalize_document_structure()` — Page Usage

**File:** `paperforge/worker/ocr_document.py` lines 5494-6203

- Builds `page_layouts` from `_build_page_layout_profiles()` → uses `int(block.get("page", 0) or 0)` (line 525+)
- Calls `infer_zones()` with block.page values
- Calls `discover_body_family_anchor(blocks)` → uses `page_count` from `total_pages` (original N)
- All page comparisons are within the block's page numbering system (which may be shifted if cover was dropped)
- **No page renumbering or offset correction anywhere**

---

## 11. `_select_middle_sample_pages()` — Page Selection for Body Anchor

**File:** `paperforge/worker/ocr_families.py` lines 225-262

```python
def _select_middle_sample_pages(blocks: list[dict], page_count: int) -> set[int]:
    pages = {int(block.get("page", 0) or 0) for block in blocks if int(block.get("page", 0) or 0) > 0}
    if page_count >= 4:
        start_page = max(2, int(page_count * 0.25))
        end_page = min(int(page_count * 0.7), ...)
        selected = {page for page in pages if page != 1 and ...}
    else:
        selected = {page for page in pages if page != 1}
```

**After cover page drop:**
- `page_count` = original N (e.g., 10)
- `pages` = {2, 3, ..., N} (e.g., {2, ..., 10})
- `start_page = max(2, int(10*0.25)) = 3`
- `end_page = min(7, 8) = 7`
- Selected: {3, 4, 5, 6, 7} — these are real block pages, fine

The `page != 1` guard was designed before cover page drop existed. It's redundant after the drop (page 1 blocks don't exist), but harmless.

**After cover page drop with 3-page paper:**
- `page_count` = 3, `pages` = {2, 3}
- `page_count < 4` → `selected = {2, 3}` (correct)

---

## 12. `validate_ocr_meta()` — Page Count Consistency Check

**File:** `paperforge/worker/ocr.py` lines 174-204

```python
rendered_pages = fulltext_path.read_text(encoding="utf-8").count("<!-- page ")
if rendered_pages != page_count:
    return ("done_incomplete", f"OCR page marker mismatch: meta={page_count}, rendered={rendered_pages}")
```

Since the render generates `<!-- page N -->` for every page from 1 to `page_count`, this check passes even with an empty page 1 marker. **No actual content presence check.**

---

## 13. Off-by-One Analysis Summary

### Confirmed: Cover Page Drop Creates Page Number Shift

| Scenario | Block pages | `meta["page_count"]` | Render generates | Issue |
|----------|------------|----------------------|-----------------|-------|
| Normal 10-page paper | 1..10 | 10 | `<!-- page 1 -->` through `<!-- page 10 -->` | No issue |
| 10-page + cover (page 1 dropped) | 2..10 | **10** (not 9) | `<!-- page 1 -->` (empty) through `<!-- page 10 -->` | Page values shifted by 1 vs. content page count |
| After cover drop, 9 real content pages | max=10, min=2 | **10** (original) | 10 markers, 1 empty | Content pages are 2..10 but conceptually 1..9 |

### Potential Off-by-One Locations

| Location | File:Line | Risk | Explanation |
|----------|-----------|------|-------------|
| `build_raw_blocks_for_result_lines` | `ocr_blocks.py:469` | **Medium** | `for res in payload.get("layoutParsingResults", [])` — if a page has >1 result entry, page counting inflates |
| `postprocess_ocr_result` | `ocr.py:1795` | **Medium** | Same loop as above — duplicate counting if multi-result page |
| Cover page drop (no re-index) | `ocr_blocks.py:297-302` | **HIGH** | Block pages 2..N, `meta["page_count"]` = N, `total_pages` = N. Functions get `page_count=N` but first content page is 2. |
| `_first_surviving_page()` | `ocr_document.py:628-630` | None | Returns correct first page from remaining blocks (e.g., 2). Used correctly by `infer_zones()`. |
| `body_end_page = first_reference_page - 1` | `ocr_document.py:1536` | None internally | Arithmetic is consistent within the shifted numbering. But the VALUE is offset by 1 from conceptual page count. |
| `render_fulltext_markdown` | `ocr_render.py:1891-1893` | None | `for p in range(1, page_count + 1)` correctly covers all pages. Page 1 just has no content blocks. |
| `validate_ocr_meta` | `ocr.py:203` | Medium | `rendered_pages == page_count` passes always, even with empty page 1. Does not detect that page 1 has no content. |
| `_select_middle_sample_pages` | `ocr_families.py:233-237` | Low | Uses original `page_count` (N) for proportion math. After cover drop, proportion is off: N=10 suggests 10 pages but only 9 have content. `start_page=int(10*0.25)=3` vs conceptual `int(9*0.25)=2` — minor and unlikely to affect correctness. |

### No Offset Found In

- **`ocr_blocks.py` lines 200-203**: `block.get("page", 1)` — safe default
- **`ocr_index.py` line 31**: `block.get("page", 0)` — verbatim pass-through
- **`ocr_families.py` line 71**: `max(page_count, max_block_page)` — correctly takes the larger value
- **`ocr_families.py` line 229**: `page != 1` guard — redundant after cover drop, not harmful
- **`ocr_document.py` line 1435**: `anchor_page = first_surviving_page if ... <= 2 else 1` — handles cover-drop case explicitly

### Root Cause of the +1 Offset

**There is no +1 bug in the numeric sense.** The pipeline does not add or subtract 1 from page numbers during propagation. The issue is:

1. `meta["page_count"]` reflects the **original PDF page count** (number of `layoutParsingResults` entries), NOT the number of content pages after cover removal
2. Block page values are the **original 1-indexed PDF page numbers**, not renumbered after cover page drop
3. This creates a **systematic +1 shift** when cover page 1 is removed: all downstream consumers see `page: 2` for what is conceptually the first content page

The design trades off conceptual cleanliness for traceability (block page == original PDF page number). If a consumer expects contiguous 1..N page numbering (e.g., for paginated display), behavior will be wrong after cover page drop.
