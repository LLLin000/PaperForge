# P1 Implementation Plan: Figure Containment Render Hygiene

> **Based on:** `2026-06-27-figure-containment-and-backmatter-boundary-design.md` §3
> **Spec contracts:** §3.7 A–E (codified in §3.2 algorithm)
> **Verification:** XD2BPCMG (composite figures with demoted caption), YGH7VEX6 (standard composite)
> **Audit evidence:** XD2BPCMG p3/p16 (33 blocks inside Figure 1 bbox → `footnote`/`subsection_heading`)

---

## Overview

Add a render-hygiene pass after `build_table_inventory()` and `write_back_table_roles()`
that checks text blocks for spatial containment inside figure bounding regions.
Contained text blocks are reclassified as `figure_inner_text`, preventing them
from leaking into the fulltext as body prose / headings / footnotes.

**Does NOT affect:**
- Figure legend matching or asset ownership
- `render_default` / `index_default` flags
- Any P0 logic (these are independent)

---

## Helper: `_cluster_bboxes_by_proximity()`

**File:** `paperforge/worker/ocr_figures.py`

```python
def _cluster_bboxes_by_proximity(
    bboxes: list[list[int]], margin: int = 40
) -> list[list[int]]:
    """Union-Find proximity clustering.

    Two bboxes merge when their *inflated* versions overlap.  Returns union of
    original (non-inflated) bboxes.  Needed because composite multi-panel figures
    have visible gaps between sub-panels — strict overlap misses them.
    """
    if not bboxes:
        return []
    n = len(bboxes)
    parent = list(range(n))

    def _find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def _union(i: int, j: int) -> None:
        ri, rj = _find(i), _find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        b1 = bboxes[i]
        for j in range(i + 1, n):
            b2 = bboxes[j]
            if (b1[2] + margin > b2[0] - margin
                    and b2[2] + margin > b1[0] - margin
                    and b1[3] + margin > b2[1] - margin
                    and b2[3] + margin > b1[1] - margin):
                _union(i, j)

    components: dict[int, list[list[int]]] = {}
    for i in range(n):
        root = _find(i)
        components.setdefault(root, []).append(bboxes[i])

    return [
        [min(b[0] for b in group), min(b[1] for b in group),
         max(b[2] for b in group), max(b[3] for b in group)]
        for group in components.values()
    ]
```

---

## Helper: `_is_contained()` — containment test (Contract E)

```python
def _is_contained(block_bbox: list[int], region_bbox: list[int]) -> bool:
    """Check if a text block is visually inside a figure region.

    Three tests, all must pass:
    1. Width guard: block not wider than 95% of region (catches full-width body text)
    2. Center-inside: block centroid falls within region
    3. Overlap ratio: >= 85% of block area overlaps with region
    """
    bw = block_bbox[2] - block_bbox[0]
    bh = block_bbox[3] - block_bbox[1]
    rw = region_bbox[2] - region_bbox[0]

    if bw > rw * 0.95:
        return False

    cx = (block_bbox[0] + block_bbox[2]) / 2
    cy = (block_bbox[1] + block_bbox[3]) / 2
    if not (region_bbox[0] <= cx <= region_bbox[2]
            and region_bbox[1] <= cy <= region_bbox[3]):
        return False

    ix1 = max(block_bbox[0], region_bbox[0])
    iy1 = max(block_bbox[1], region_bbox[1])
    ix2 = min(block_bbox[2], region_bbox[2])
    iy2 = min(block_bbox[3], region_bbox[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return False

    overlap_area = (ix2 - ix1) * (iy2 - iy1)
    block_area = bw * bh
    return block_area > 0 and overlap_area / block_area >= 0.85
```

---

## Helper: `_highly_overlaps_any_matched_region()` — dedup guard (Contract C)

```python
def _highly_overlaps_any_matched_region(
    fallback_bbox: list[int],
    figure_regions: list[tuple[str, list[int]]],
) -> bool:
    """Drop fallback region if >50% of its area overlaps any matched region."""
    for tag, matched_bbox in figure_regions:
        if tag != "matched":
            continue
        ix1 = max(fallback_bbox[0], matched_bbox[0])
        iy1 = max(fallback_bbox[1], matched_bbox[1])
        ix2 = min(fallback_bbox[2], matched_bbox[2])
        iy2 = min(fallback_bbox[3], matched_bbox[3])
        if ix2 > ix1 and iy2 > iy1:
            overlap = (ix2 - ix1) * (iy2 - iy1)
            fb_area = ((fallback_bbox[2] - fallback_bbox[0])
                       * (fallback_bbox[3] - fallback_bbox[1]))
            if fb_area > 0 and overlap / fb_area >= 0.5:
                return True
    return False
```

---

## Helper: `_figure_region_bbox()` — region resolver

Matched figures may carry region info in different fields. Resolve in order:

```python
def _figure_region_bbox(mf: dict) -> list[float] | None:
    """Resolve a figure's bounding region from available fields.

    Resolution order:
    1. cluster_bbox (composite figure's full extent)
    2. asset_bbox (single-asset figure)
    3. union of matched_assets[].bbox (sequential fallback / legacy entries)
    """
    cb = mf.get("cluster_bbox")
    if cb and len(cb) >= 4:
        return cb

    ab = mf.get("asset_bbox")
    if ab and len(ab) >= 4:
        return ab

    asset_bboxes = [
        a.get("bbox")
        for a in mf.get("matched_assets", []) or []
        if a.get("bbox") and len(a.get("bbox")) >= 4
    ]
    if asset_bboxes:
        return [
            min(b[0] for b in asset_bboxes),
            min(b[1] for b in asset_bboxes),
            max(b[2] for b in asset_bboxes),
            max(b[3] for b in asset_bboxes),
        ]

    return None
```

---

## Helper: `_matched_asset_keys()` — page-qualified asset exclusion

Both `matched_assets` and `asset_block_ids` must be checked, because different
match paths populate different fields. Keys are `(page, block_id)` to prevent
same-id-on-different-page collisions.

```python
def _matched_asset_keys(mf: dict) -> set[tuple[int, str]]:
    """Collect page-qualified asset identifiers from a matched figure.

    Reads from both matched_assets and asset_block_ids, then unions.
    """
    keys: set[tuple[int, str]] = set()
    page = int(mf.get("page", 0) or 0)

    for asset in mf.get("matched_assets", []) or []:
        bid = asset.get("block_id")
        ap = int(asset.get("page", page) or page)
        if bid:
            keys.add((ap, str(bid)))

    for bid in mf.get("asset_block_ids", []) or []:
        if bid:
            keys.add((page, str(bid)))

    return keys
```

---

## Main entry point: `tag_figure_contained_text()`

**Location:** `paperforge/worker/ocr_figures.py` (same file as the helpers, exported)

```python
def tag_figure_contained_text(
    blocks: list[dict],
    matched_figures: list[dict],
) -> None:
    """Render-hygiene pass: tag text blocks spatially inside figure regions.

    Does NOT mutate render_default/index_default.  Renderer skips
    figure_inner_text by role.  Indexing behavior out of scope.

    ponytail: containment is center-inside + 85% overlap heuristic.
    Upgrade to pixel-exact polygon if false positives confirmed.
    """
    _LEAK_ROLES = {
        "body_paragraph", "section_heading", "subsection_heading",
        "sub_subsection_heading", "backmatter_heading", "backmatter_body",
        "tail_candidate_body", "footnote", "structured_insert",
        "non_body_insert", "frontmatter_noise",
    }

    pages = {b.get("page") for b in blocks if b.get("page") is not None}
    matched_by_page: dict[int, list[dict]] = {}
    for mf in matched_figures:
        p = mf.get("page")
        if p is not None:
            matched_by_page.setdefault(p, []).append(mf)

    for page in sorted(pages):
        page_blocks = [b for b in blocks if b.get("page") == page]
        figure_regions: list[tuple[str, list[int]]] = []
        covered_asset_keys: set[tuple[int, str]] = set()

        # --- Source 1: matched_figures cluster_bbox ---
        for mf in matched_by_page.get(page, []):
            region = _figure_region_bbox(mf)
            if region:
                figure_regions.append(("matched", region))
                covered_asset_keys |= _matched_asset_keys(mf)

        # --- Source 2: uncovered figure-like assets (demoted-caption fallback) ---
        fallback_assets = [
            b for b in page_blocks
            if (int(b.get("page", 0) or 0), str(b.get("block_id", ""))) not in covered_asset_keys
            and b.get("role") in {"figure_asset", "media_asset"}
            and b.get("role") not in {"table_html", "table_asset"}
            and (
                b.get("asset_family_hint") == "figure_like"
                or str(b.get("raw_label", "") or "") in {"image", "chart", "figure_title", "figure"}
            )
        ]
        if fallback_assets:
            fallback_bboxes = [b["bbox"] for b in fallback_assets if len(b.get("bbox") or []) >= 4]
            for fr in _cluster_bboxes_by_proximity(fallback_bboxes, margin=40):
                if not _highly_overlaps_any_matched_region(fr, figure_regions):
                    figure_regions.append(("fallback", fr))

        if not figure_regions:
            continue

        # --- Tag contained text blocks ---
        for block in page_blocks:
            role = str(block.get("role") or "")
            if role in {"figure_asset", "media_asset", "noise",
                        "figure_caption", "figure_caption_candidate",
                        "table_html", "table_asset",
                        "figure_inner_text"}:
                continue
            bbox = block.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            for _, fr in figure_regions:
                if _is_contained(bbox, fr):
                    block["_figure_contained"] = True
                    if role in _LEAK_ROLES:
                        block["role"] = "figure_inner_text"
                    break
```

---

## Call site in `postprocess_ocr_result()`

**File:** `paperforge/worker/ocr.py`

Find the `postprocess_ocr_result()` function. The real pipeline order is:

```
build_figure_inventory(structured)
write_back_figure_roles(figure_inventory, structured)
synthesize_reader_figures(...)

build_table_inventory(structured)
attach_ownership_conflicts(figure_inventory, table_inventory)
write_figure_inventory(...)
write_back_table_roles(table_inventory, structured)
write_table_inventory(...)

==== INSERT HERE ====
tag_figure_contained_text(structured, figure_inventory.get("matched_figures", []))
=====================

write_structured_blocks_jsonl(...)
render_fulltext_markdown(...)
```

Insert `tag_figure_contained_text()` after `write_back_table_roles()` and before
`write_structured_blocks_jsonl()`. This ensures:
- Table assets are already writeback'd to `table_html`, so fallback won't include them
- All figure role writeback is complete
- The structured blocks snapshot is still mutable before persist+render

Also add the import at the top of `ocr.py`:
```python
from paperforge.worker.ocr_figures import tag_figure_contained_text
```

---

## Tests

**File:** New `tests/unit/worker/test_figure_containment.py`

### Tests from plan (10 cases)

| Test | What it verifies |
|------|-----------------|
| `test_block_fully_inside_matched_region` | Block inside matched region → figure_inner_text |
| `test_block_inside_fallback_region` | Block inside fallback-clustered assets → figure_inner_text |
| `test_block_not_tagged_when_outside` | Block outside all regions → unchanged |
| `test_block_not_tagged_when_mostly_outside` | Overlap < 85% → unchanged |
| `test_full_width_block_not_tagged` | Block wider than 95% of region → unchanged |
| `test_figure_asset_never_tagged` | role=figure_asset → unchanged |
| `test_render_default_unchanged` | render_default/index_default not mutated |
| `test_covered_asset_exclusion` | Asset in matched_figures → excluded from fallback |
| `test_fallback_dropped_when_overlaps_matched` | Fallback region >50% overlap matched → dropped |
| `test_proximity_clustering_merges_gapped_panels` | Two disjoint bboxes 30px apart → merged |

### Additional tests (from review, 4 cases)

| Test | What it verifies |
|------|-----------------|
| `test_matched_assets_only_entry` | matched figure with `matched_assets` but no `asset_block_ids/cluster_bbox` → region resolved from asset bbox union |
| `test_page_qualified_exclusion` | Same block_id on page 1 and page 2 → only page-1 asset excluded from fallback |
| `test_table_html_not_in_fallback` | Table writeback to `table_html` role → excluded from fallback region |
| `test_structured_insert_inside_figure` | `structured_insert` inside figure → `figure_inner_text` (prevents callout leakage) |

---

## Verification

**Audit paper: XD2BPCMG** (cartilage review, composite Figure 1 on p3):
- Before: 33 blocks inside Figure 1 bbox → `footnote`/`subsection_heading`
- After: same blocks → `figure_inner_text`
- Render: no `## (b) Type of cartilage` in fulltext
- Structured inserts inside figure also tagged

**Regression (no change expected):**
- 9TW98JH8 (5p, clean mixed-tail, 20/20 correct)
- YGH7VEX6 (8p, Springer — standard figures, no containment issue)
- `python -m pytest tests/unit/ tests/cli/ -v --tb=short`
- `ruff check --fix paperforge/ && ruff format paperforge/`

---

## Total diff

~140 lines new code (5 helpers + 1 main entry + 1 import + call site)
~110 lines new tests
