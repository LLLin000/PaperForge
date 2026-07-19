# Evidence-Driven Container Admission — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans`.
> **Primary Spec:** `docs/superpowers/specs/2026-06-26-evidence-driven-container-admission-design.md`

**Goal:** Rewrite `_extract_visual_container_rects()` in `ocr_pdf_spans.py` to use evidence-driven admission (visual signal + text evidence + vetoes) instead of size-first gates. Motivation: N6XCZD25 blue sidebar box (156×43pt) was excluded by `height<50` gate; page frame rects and thin gray decor rects were falsely admitted.

## File Map

| File | Responsibility |
|------|---------------|
| `paperforge/worker/ocr_pdf_spans.py` | All new helpers + rewritten `_extract_visual_container_rects()` |
| `paperforge/worker/ocr_pdf_spans.py` (call site) | Updated to pass `raw_blocks_for_page` and `pdf_blocks` |
| `tests/test_ocr_pdf_spans.py` | All new tests |

## Stage Boundary

This plan:
- Adds 9 new helpers: `_normalize_rgb()`, `_is_gray()`, `_brightness()`, `_has_visible_fill()`, `_has_container_text()`, `_bbox_overlap_ratio()`, `_extract_rect_features()`, `_merge_vertical_components()`, `_component_compatible()`
- Rewrites `_extract_visual_container_rects()` body (signature change: adds `raw_blocks_for_page` and `pdf_blocks` params)
- Updates caller: the by-page cache loop that calls `_extract_visual_container_rects()` — needs to pre-group raw blocks and pass them
- Adds stale flag cleanup before overlap loop
- Returns `list[fitz.Rect]` (unchanged type for downstream)

This plan does NOT:
- Change `_in_visual_container` flag logic (overlap ≥0.3 → flag)
- Change `_container_bbox` / `_container_text` setting
- Change `score_structured_insert` or render logic
- Touch any file outside `ocr_pdf_spans.py` and its test file

## Non-Negotiable Constraints

1. Return type remains `list[fitz.Rect]` — downstream uses `.x0/.x1/.y0/y1` properties
2. Line-like rects (height≤3 or width≤3) are NOT standalone containers, but ARE kept for component grouping
3. Text evidence is REQUIRED for admission — no no-text fallback in first release
4. `_map_ocr_bbox_to_pdf_rect()` must be called before any OCR block overlap check
5. `_has_visible_fill()` must handle both 3-element and 4-element color tuples safely
6. Pure black border (brightness ≤0.02) passes as visual signal; only mid-gray (0.02–0.85) thin borders are excluded
7. Stale flag cleanup and container detection must be per-page three-phase: (a) clear flags, (b) compute containers, (c) mark blocks — all inside one page loop
8. page-sized/crop-like features (area ≥ 60% page + near edges) are completely excluded — never standalone, never in grouping_pool
9. Merged candidates that overlap any standalone candidate replace their child components in accepted set; accepted rects are sorted by area descending so larger container takes priority in overlap scoring

## Implementation Tasks

### Task 1: Color normalization helpers (~8 min)

**File:** `paperforge/worker/ocr_pdf_spans.py`

Add module-level helpers:

```python
def _normalize_rgb(color) -> tuple[float, float, float] | None:
    """Normalize PyMuPDF drawing color to 0-1 float RGB.
    Accepts None, (r,g,b) in 0-1 or 0-255, or (r,g,b,a)."""

def _is_gray(rgb: tuple[float, float, float], threshold: float = 0.05) -> bool:
    """True if max(rgb) - min(rgb) < threshold."""

def _brightness(rgb: tuple[float, float, float]) -> float:
    """Return (r+g+b)/3."""

def _has_visible_fill(fill) -> bool:
    """True if fill is non-white (brightness < 0.95) and alpha > 0.
    Handles both 3- and 4-element fill tuples safely."""
```

---

### Task 2: Rect feature extraction (~10 min)

**File:** `paperforge/worker/ocr_pdf_spans.py`

```python
def _extract_rect_features(
    drawing: dict,
    page_width: float,
    page_height: float,
    margin: float = 10.0,
) -> dict:
```

Returns:
```python
{
    "rect": fitz.Rect(x0, y0, x1, y1),
    "width": float, "height": float, "area": float,
    "page_area_ratio": float,
    "fill_rgb": tuple | None, "stroke_rgb": tuple | None,
    "stroke_width": float,
    "is_filled": bool,
    "has_border": bool,
    "is_low_contrast_gray_border": bool,
    "line_like": bool,
    "near_page_edges": bool,
}
```

Use the helpers from Task 1. Compute `is_low_contrast_gray_border` per the black-border-safe rule.

---

### Task 3: Fix line-like veto and add page-sized veto (~5 min)

**File:** `paperforge/worker/ocr_pdf_spans.py`

```python
grouping_pool: list[dict] = []
candidates: list[dict] = []

for drawing in drawings:
    feat = _extract_rect_features(drawing, pw, ph)

    # page-sized / crop-like: completely excluded from everything
    if feat["page_area_ratio"] >= 0.60 and feat["near_page_edges"]:
        continue
    if feat["width"] >= 0.90 * pw and feat["height"] >= 0.90 * ph:
        continue

    grouping_pool.append(feat)

    if feat["line_like"]:
        continue  # not standalone, but in grouping_pool

    candidates.append(feat)
```

---

### Task 4: Component grouping (~10 min)

**File:** `paperforge/worker/ocr_pdf_spans.py`

```python
def _component_compatible(a: dict, b: dict) -> bool:
    """One has visible fill, other has fill or border."""

def _merge_vertical_components(features: list[dict]) -> list[dict]:
    """Group features by x-range overlap >=0.8 and vertical gap -2..5pt.
    Returns merged feature dicts with component_grouped=True."""
```

Apply merge to `grouping_pool`:

```python
merged = _merge_vertical_components(grouping_pool)
overlapping_merged: list[dict] = []
for m in merged:
    if any((m["rect"] & c["rect"]).area > 0 for c in candidates):
        m["component_grouped"] = True
        overlapping_merged.append(m)
# Remove child candidates that are covered by merged rects
child_rects = {id(c["rect"]): c for c in candidates}
covered_ids: set[int] = set()
for m in overlapping_merged:
    for c in candidates:
        if id(c["rect"]) in covered_ids:
            continue
        if c is m:
            continue
        overlap = (m["rect"] & c["rect"]).area
        if overlap > 0 and overlap >= c["rect"].get_area() * 0.5:
            covered_ids.add(id(c["rect"]))
candidates = [c for c in candidates if id(c["rect"]) not in covered_ids]
candidates.extend(overlapping_merged)
```

---

### Task 5: Text evidence admission (~15 min)

**File:** `paperforge/worker/ocr_pdf_spans.py`

```python
def _bbox_overlap_ratio(container_rect: fitz.Rect, block_rect: fitz.Rect) -> float:
    """Return overlap / block_area.
    Returns 0.0 if block_area <= 0 or intersection is empty."""

def _has_container_text(
    rect: fitz.Rect,
    *,
    pdf_page: Any,
    pdf_blocks: Sequence[Any] | None,
    raw_blocks_for_page: list[dict] | None,
) -> bool:
    """Count chars from PDF text blocks + OCR raw blocks inside rect.
    Threshold: >= 10 chars total.
    OCR raw block bbox must be mapped to PDF space via _map_ocr_bbox_to_pdf_rect().
    The mapping requires page_width/page_height from the raw block; fallback to
    pdf_page.rect.width/height if block lacks these fields."""
```

Implementation notes:
- `_bbox_overlap_ratio()`: if `block_area <= 0`, return 0.0. If `intersection.is_empty`, return 0.0.
- `_has_container_text()`: for each raw_blocks_for_page entry, map its bbox:
  ```python
  pw = block.get("page_width") or block.get("ocr_width") or pdf_page.rect.width
  ph = block.get("page_height") or block.get("ocr_height") or pdf_page.rect.height
  block_rect = _map_ocr_bbox_to_pdf_rect(block["bbox"], pw, ph, pdf_page)
  ```
- For PDF text blocks: use `fitz.Rect(b[:4])` directly (they are already in PDF space).

Wire into admission:

```python
accepted: list[fitz.Rect] = []
for feat in candidates:
    vs = feat["is_filled"] or (feat["has_border"] and not feat["is_low_contrast_gray_border"])
    if not vs:
        continue
    if not _has_container_text(feat["rect"], pdf_page=page, pdf_blocks=pdf_blocks, raw_blocks_for_page=raw_blocks_for_page):
        continue
    accepted.append(feat["rect"])

# Larger rects first so block-level overlap picks the biggest container
accepted.sort(key=lambda r: r.get_area(), reverse=True)
return accepted
```

---

### Task 6: Rewrite call site as per-page three-phase loop (~10 min)

**File:** `paperforge/worker/ocr_pdf_spans.py` (the by-page container cache + block flag loop)

Group raw blocks by page first, then for each page: (a) clear stale flags, (b) compute containers, (c) mark blocks with overlap. All three phases happen inside the same page loop to avoid cross-page contamination.

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

    # Phase C: mark blocks that overlap containers
    for block in page_blocks:
        block_rect = _block_bbox_to_fitz_rect(block)
        for c in containers:
            overlap_ratio = _bbox_overlap_ratio(c, block_rect)
            if overlap_ratio >= 0.3:
                block["_in_visual_container"] = True
                block["_container_bbox"] = list(c)
                break
```

This replaces the existing lazy-cache approach. `_block_bbox_to_fitz_rect()` is an existing helper in the same file.

---

### Task 7: Update `_extract_visual_container_rects` signature (~3 min)

```python
def _extract_visual_container_rects(
    page: fitz.Page,
    raw_blocks_for_page: list[dict] | None = None,
    pdf_blocks: Sequence[Any] | None = None,
) -> list[fitz.Rect]:
```

---

### Task 8: Tests (~28 min)

**File:** `tests/test_ocr_pdf_spans.py`

11 test functions:

| # | Function | Key assertion |
|---|----------|---------------|
| 1 | `test_small_sidebar_container_with_text_is_admitted` | 156x43, blue fill + text → admitted |
| 2 | `test_horizontal_separator_line_is_rejected` | w=400, h=1 → not in returned list |
| 3 | `test_vertical_separator_line_is_rejected` | w=1, h=600 → not returned |
| 4 | `test_page_frame_rect_is_rejected` | 0.6 area + near edges → not returned |
| 5 | `test_white_fill_is_not_visual_signal` | (1,1,1) fill → not admitted (unless border) |
| 6 | `test_component_merge_requires_strong_x_overlap` | x_overlap=0.5 → not merged |
| 7 | `test_raw_block_outside_container_no_flag` | Block outside → `_in_visual_container` False |
| 8 | `test_raw_block_inside_container_flagged` | Block inside → flag True |
| 9 | `test_line_like_components_can_participate_in_grouping` | Blue header + 4 thin lines → merged covers body |
| 10 | `test_admission_with_ocr_blocks_when_no_pdf_text` | No PDF text, OCR block inside → admitted |
| 11 | `test_admission_maps_ocr_bbox_to_pdf_space` | PDF 600x800, OCR 1200x1600, container in PDF space, OCR bbox scaled → overlap → admitted |

For tests 1-10, `_map_ocr_bbox_to_pdf_rect` can be mocked as identity. For test 11, use a real mapping delta (OCR 1200x1600 → PDF 600x800) to verify the function is called with correct arguments.

**Yellow flag:** Pure black thin border (≤1pt) passing as visual signal may cause false positives on plot frames / chart borders with axis labels. Monitor in post-deployment audit; not blocking this release.

---

## Execution Order

```
Task 1: Color normalization helpers          →  8 min
Task 2: Rect feature extraction              → 10 min
Task 3: Line-like + page-sized veto          →  5 min
Task 4: Component grouping                   → 10 min
Task 5: Text evidence admission              → 15 min
Task 6: Rewrite call site as 3-phase loop    → 10 min
Task 7: Update function signature            →  3 min
Task 8: Tests (11 cases)                     → 28 min
                                          Total: ~89 min
```

Single commit PR.
