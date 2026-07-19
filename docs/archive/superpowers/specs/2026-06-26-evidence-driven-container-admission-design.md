# Evidence-Driven Visual Container Admission

**Date:** 2026-06-26 (Revised 2026-06-26, round 3)
**Status:** Draft
**Motivation:** Current `_extract_visual_container_rects()` gates on `width >= 100 and height >= 50` before checking fill/border. In three-column academic layouts, real callout boxes (e.g., "Available With This Article") are one-column wide (~180pt) and can be short (~43pt). The size gate falsely excludes them. Conversely, size gates do not effectively exclude the false positives they were meant to block (page frames, decoration rects, grid lines), which need their own targeted vetoes.

## Problem

Two-way failure:

| Direction | Example | Root cause |
|-----------|---------|------------|
| False negative | Blue sidebar box (156x43pt) | `height=43 < 50` gate |
| False positive | Page frame rect (full page) | No page-sized veto after gate |
| False positive | 0.5pt dark-gray decor rect | No line-like / gray-detect veto after gate |

## Proposal

Replace size-first admission with **evidence-driven admission**:

```
Extract drawings → compute per-rect features →
1. Reject standalone line-like rects as containers
   (but keep them for component grouping)
2. Reject page-sized / crop-like rects
3. Component grouping (vertical merge same-x-range rects with strong overlap)
4. Check text evidence inside candidate (PDF text + OCR raw blocks)
5. Accept if visual_signal AND text_evidence AND not page_sized
```

**No absolute width/height gate.** No no-text fallback in first release.

---

## P0 Fixes (from review)

### Return type: keep list[fitz.Rect]

`_extract_visual_container_rects()` returns `list[fitz.Rect]` because downstream code uses `.x0/.x1/.y0/.y1` properties on raw fitz rect objects. Feature dicts are internal only. Plan: extract features internally → return `[r["rect"] for r in accepted]`.

### Line-like: reject standalone, keep for grouping

```python
if feature["line_like"] and not feature["component_grouped"]:
    continue  # not a standalone container
```

All features are preserved through grouping even when line_like. Only standalone admission is blocked.

### PDF text char_count

```python
char_count += len(str(block[4] or "")) if len(block) > 4 else 0
```

Not `block[4]` directly (block[4] is string text, not int). Types: `pdf_blocks: Sequence[Any] | None` (`page.get_text("blocks")` returns tuple-like).

### Fill alpha safety

```python
def _has_visible_fill(fill) -> bool:
    rgb = _normalize_rgb(fill)
    if rgb is None:
        return False
    if len(fill) >= 4 and float(fill[3]) <= 0:
        return False
    return _brightness(rgb) < 0.95  # non-white fill
```

Never access `fill[3]` without checking length.

### Black border: not killed by gray_border

```python
is_low_contrast_gray_border = (
    not is_filled
    and has_border
    and stroke_width <= 1.0
    and stroke_rgb is not None
    and _is_gray(stroke_rgb)
    and 0.02 < _brightness(stroke_rgb) < 0.85
)
```

Pure black (brightness ~0) passes as visual_signal even with thin border. Only mid-gray low-contrast thin borders are excluded.

### Call site must pass blocks

```python
raw_blocks_by_page = defaultdict(list)
for block in raw_blocks:
    raw_blocks_by_page[block.get("page", 1) - 1].append(block)

pdf_blocks = pdf_page.get_text("blocks")

by_page_containers[page_num] = _extract_visual_container_rects(
    pdf_page,
    raw_blocks_for_page=raw_blocks_by_page.get(page_num, []),
    pdf_blocks=pdf_blocks,
)
```

### Overlap ratio: overlap / text_block_area

```python
def _bbox_overlap_ratio(container_bbox, block_bbox) -> float:
    return overlap_area / block_area
```

Not `overlap / candidate_area`. Consistent with current `_in_visual_container` semantics.

---

## Algorithm

### Step 1: Feature extraction per drawing

```python
{
    "rect": fitz.Rect(x0, y0, x1, y1),      # PDF coordinate space
    "width": x1 - x0,
    "height": y1 - y0,
    "area": width * height,
    "page_area_ratio": area / (page_width * page_height),
    "fill_rgb": _normalize_rgb(fill),
    "stroke_rgb": _normalize_rgb(color) if stroke else None,
    "stroke_width": stroke_width or 0,
    "is_filled": _has_visible_fill(fill),
    "has_border": stroke and stroke_width > 0,
    "is_low_contrast_gray_border": bool(...from P0 black-border rule...),
    "line_like": height <= 3.0 or width <= 3.0,
    "near_page_edges": all edges within margin,
}
```

### Step 2: Feature loop — page-sized excluded completely, line-like excluded from standalone

```python
for drawing in drawings:
    feat = _extract_rect_features(drawing, pw, ph)

    # page-sized / crop-like: completely excluded (not even grouping_pool)
    if feat["page_area_ratio"] >= 0.60 and feat["near_page_edges"]:
        continue
    if feat["width"] >= 0.90 * pw and feat["height"] >= 0.90 * ph:
        continue

    grouping_pool.append(feat)

    if feat["line_like"]:
        continue  # grouping_pool only, no standalone admission

    candidates.append(feat)
```

Page-sized features are excluded from **both** standalone admission and grouping because they never represent genuine callout boxes. Line-like features are excluded from standalone admission but kept in `grouping_pool` for component merging (a thin border line + colored header can form a valid container).

### Step 4: Component grouping

```python
def _merge_vertical_components(features: list[dict]) -> list[dict]:
    # Sort by x0, then y0
    # Merge if:
    #   x_overlap_ratio >= 0.8
    #   -2.0 <= vertical_gap <= 5.0
    #   component_compatible(a, b):
    #     one has visible fill, other has fill or border
```

Groups produce a merged feature with unioned bbox, evidence list, and `component_grouped=True`.

**Child removal:** Merged candidates that overlap a standalone candidate's rect area replace that child candidate (not additive). After merge, any candidate whose rect is ≥50% covered by a merged rect is removed from `candidates`. This prevents thin header rects from winning overlap contests against the larger merged container bbox.

**Sort by area:** Final accepted rects sorted by `get_area()` descending so block-level overlap scores prioritize the largest container first.

### Step 5: Visual signal check

```python
visual_signal = (
    is_filled
    or (has_border and not is_low_contrast_gray_border)
)
```

### Step 6: Text evidence check

```python
def _has_container_text(
    rect: fitz.Rect,
    *,
    pdf_page: Any,
    pdf_blocks: Sequence[Any] | None,
    raw_blocks_for_page: list[dict] | None,
) -> bool:
    char_count = 0
    if pdf_blocks:
        for block in pdf_blocks:
            block_rect = fitz.Rect(block[:4])
            if _bbox_overlap_ratio(rect, block_rect) >= 0.30:
                char_count += len(str(block[4] or "")) if len(block) > 4 else 0
    if raw_blocks_for_page:
        for block in raw_blocks_for_page:
            block_bbox = block.get("bbox") or [0, 0, 0, 0]
            pw = block.get("page_width") or block.get("ocr_width") or pdf_page.rect.width
            ph = block.get("page_height") or block.get("ocr_height") or pdf_page.rect.height
            pdf_rect = _map_ocr_bbox_to_pdf_rect(block_bbox, pw, ph, pdf_page)
            if _bbox_overlap_ratio(rect, pdf_rect) >= 0.30:
                char_count += len(str(block.get("text", "")))
    return char_count >= 10

def _bbox_overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    overlap = a & b  # fitz.Intersection
    area_b = b.width * b.height
    if area_b <= 0:
        return 0.0
    if overlap.is_empty:
        return 0.0
    return (overlap.width * overlap.height) / area_b
```

### Step 7: Admission

```python
if visual_signal and _has_container_text(...) and not page_sized:
    accepted.append(feature["rect"])  # return fitz.Rect
```

---

## Call site: per-page three-phase loop

Replace the existing lazy-cache approach. Group raw blocks by page, then for each page execute three phases inside one loop:

1. **Phase A — Clear:** Pop stale flags (`_in_visual_container`, `_container_bbox`, `_container_text`) from all blocks on this page.
2. **Phase B — Compute:** Call `_extract_visual_container_rects()` with `raw_blocks_for_page` and `pdf_blocks`.
3. **Phase C — Mark:** For each block, compute `_bbox_overlap_ratio(container_rect, block_rect)`. If ≥0.3, set `_in_visual_container=True` and `_container_bbox = list(container_rect)`. Break on first match so largest container (sorted by area descending from Step 7) wins.

```python
raw_blocks_by_page: dict[int, list[dict]] = defaultdict(list)
for block in raw_blocks:
    raw_blocks_by_page[block.get("page", 1) - 1].append(block)

for pageno, page_blocks in raw_blocks_by_page.items():
    # Phase A: clear stale flags
    for block in page_blocks:
        block.pop("_in_visual_container", None)
        block.pop("_container_bbox", None)
        block.pop("_container_text", None)

    # Phase B: compute containers
    pdf_page = doc[pageno]
    pdf_blocks = pdf_page.get_text("blocks")
    containers = _extract_visual_container_rects(
        pdf_page,
        raw_blocks_for_page=page_blocks,
        pdf_blocks=pdf_blocks,
    )

    # Phase C: mark blocks
    for block in page_blocks:
        block_rect = _block_bbox_to_fitz_rect(block)
        for c in containers:
            if _bbox_overlap_ratio(c, block_rect) >= 0.3:
                block["_in_visual_container"] = True
                block["_container_bbox"] = list(c)
                break
```

---

## Thresholds

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Line-like veto | `height <= 3.0 or width <= 3.0` | All separator lines |
| Page area ratio veto | `>= 0.60` | Frame/clipping rects |
| Near-edge margin | `<= 10pt` each edge | Page-level rect |
| Near-full-page veto | `>= 0.90 * page_wh` | Crop-like rects off edges |
| Component x_overlap_ratio | `>= 0.80` | Same column |
| Component vertical gap | `-2.0 <= gap <= 5.0` | Touching rects |
| Text char threshold | `>= 10` | Avoid bullet/icon |
| Block overlap for text | `>= 0.30` (over block area) | Same as current overlap gate |
| Fill brightness signal | `< 0.95` | Reject near-white fills |
| Gray detection delta | `max - min < 0.05` | 0–1 space |
| Low-contrast border brightness | `0.02 < brightness < 0.85` | Mid-gray, not pure black |

---

## Reference: Task List

For execution order and full detail see the implementation plan at `docs/superpowers/plans/2026-06-26-evidence-driven-container-admission-implementation.md`.

Summary:

| Task | Description | File |
|------|-------------|------|
| 1 | Color normalization helpers (4 funcs) | `ocr_pdf_spans.py` |
| 2 | Rect feature extraction (`_extract_rect_features`) | `ocr_pdf_spans.py` |
| 3 | Line-like + page-sized veto loop | `ocr_pdf_spans.py` |
| 4 | Component grouping (`_merge_vertical_components` + child removal + area sort) | `ocr_pdf_spans.py` |
| 5 | Text evidence (`_has_container_text` with `pdf_page` param, `_bbox_overlap_ratio`) | `ocr_pdf_spans.py` |
| 6 | Rewrite call site as per-page three-phase loop | `ocr_pdf_spans.py` (caller) |
| 7 | Update function signature | `ocr_pdf_spans.py` |
| 8 | Tests (11 cases) | `test_ocr_pdf_spans.py` |

---

## Tests

| # | Test | Assert |
|---|------|--------|
| 1 | `test_small_sidebar_container_with_text_is_admitted` | 156x43 filled+text component → accepted |
| 2 | `test_horizontal_separator_line_is_rejected` | w=400, h=1 → rejected (AND→OR fix) |
| 3 | `test_vertical_separator_line_is_rejected` | w=1, h=600 → rejected |
| 4 | `test_page_frame_rect_is_rejected` | area_ratio>=0.6 + near edges → rejected |
| 5 | `test_white_fill_is_not_visual_signal` | fill=(1,1,1) or (0.98,0.98,0.98) → rejected unless border |
| 6 | `test_component_merge_requires_strong_x_overlap` | overlap_ratio<0.8 → not merged |
| 7 | `test_raw_block_outside_container_no_flag` | Block outside → `_in_visual_container` is False |
| 8 | `test_raw_block_inside_container_flagged` | Block inside sidebar → flag is True |
| 9 | `test_line_like_components_can_participate_in_grouping` | Blue header + thin-line border → merged covers body |
 | 10 | `test_admission_with_ocr_blocks_when_no_pdf_text` | No PDF text, OCR block inside → admitted |
 | 11 | `test_admission_maps_ocr_bbox_to_pdf_space` | PDF 600×800, OCR 1200×1600, container in PDF space, OCR bbox scaled → overlap → admitted |

**Test 11 note:** This verifies `_map_ocr_bbox_to_pdf_rect()` is actually called with correct arguments. Tests 1-10 may mock it as identity; test 11 uses a real 2:1 scaling delta.

**Yellow flag:** Pure black thin border (≤1pt) passing as visual signal may cause false positives on plot frames / chart borders with axis labels. Monitor post-deployment; not blocking this release.
