# Figure-Containment & Reference-Boundary Backmatter Design

**Date:** 2026-06-27
**Status:** Figure containment → P1 plan-ready; Backmatter → not implemented from this file
**Authorization:** This spec authorizes implementation of **Figure containment only** (§3).
Backmatter sections (§4, §2) are diagnostic notes only and must not be implemented from this file.
**Review verdict (2026-06-27):**

```
Figure containment: direction correct.  §3.2 and §3.3 below are already updated to §3.7.
Backmatter redesign:   not ready.  Multi-page refs, same-page body+ref, and
                       reference_zone extent remain unsolved.  Needs separate spec.
```

**Audit evidence:** 25K5KZAQ, YGH7VEX6, XD2BPCMG, NC66N4Q3

---

## Table of Contents

1. [Problem: Figure-Containment Gap](#1-problem-figure-containment-gap)
2. [Problem: Reference-Boundary Backmatter](#2-problem-reference-boundary-backmatter)
3. [Design: Figure-Containment Render Pass](#3-design-figure-containment-render-pass)
4. [Design: Reference-Boundary Backmatter Redesign](#4-design-reference-boundary-backmatter-redesign)
5. [Implementation Order & Dependencies](#5-implementation-order--dependencies)
6. [Risk & Verification](#6-risk--verification)

---

## 1. Problem: Figure-Containment Gap

### 1.1 Evidence (XD2BPCMG)

Cartilage review, 26 pages. Pages 3 and 16 contain large composite multi-panel figures (Figure 1 and Figure 6). 21 text blocks on page 3 are spatially inside Figure 1's bounding region. None are classified as `figure_inner_text`:

- `vision_footnote` → `footnote` (16 blocks on p3, 17 on p16)
- `paragraph_title` → `subsection_heading` (panel headings like "(c) Cartilage Function")
- `figure_title` → `non_body_insert` ("(a) Cartilage distribution")

### 1.2 Root cause

Three converging gaps:

**Gap A: No spatial containment check.** The pipeline has zero code that answers "does this text block's bbox fall inside a figure's bounding region?" The existing `_bbox_contains()` (ocr.py:833) exists for footnotes/media dedup, but is never used for figure-inner-text detection. The 2026-06-13 `v1-real-paper-audit-report.md` explicitly chose proximity over containment because "panel labels sit outside asset bboxes" — but for XD2BPCMG's composite figures, the labels are INSIDE.

**Gap B: Legend detection gated by `raw_label`.** The `_looks_like_figure_inner_label()` function only fires for `raw_label == "text"`. All figure-internal text on XD2BPCMG pages 3/16 has `raw_label` in `{vision_footnote, paragraph_title, figure_title, footer}` — none reach the inner-label check.

**Gap C: Figure 1 caption demoted.** Figure 1's legend was demoted from `figure_caption_candidate` to `body_paragraph` (reason: "figure mention with narrative prose in body spine"). Without a matched figure entry, no `cluster_bbox` exists, so even if containment logic existed, there'd be no reference region to check against.

### 1.3 Scope of impact

| Paper | Pages affected | Blocks misclassified | Effect |
|-------|---------------|---------------------|--------|
| XD2BPCMG | 3, 16 | 33+ | Figure labels → `footnote` in fulltext |
| Any paper with composite figures | ~21.5% of vault | Varies | Same pattern |

---

## 2. Problem: Reference-Boundary Backmatter

### 2.1 Evidence (25K5KZAQ, NC66N4Q3)

**25K5KZAQ (Bioactive Materials, 11p):**
- CRediT/Ethics headings at y=422-802 → classified as `subsection_heading`
- "Declaration of competing interest" at y=829 → correctly `backmatter_heading`
- Result: CRediT text appears as body prose above Discussion, not as backmatter

**NC66N4Q3 (Radiographic Atlas, 56p):**
- Page 56: two-column layout, left=Discussion, right=References
- `body_end_page=None`, `ref_start=None` — boundary detection fails because body+ref share final page
- `is_clean_separated = False` → tail spread logic enters degraded mode

### 2.2 Root cause

Three converging failures:

**A: Backmatter heading pattern too narrow.** `_is_backmatter_boundary_heading()` checks only `{ADDITIONAL, DECLARATION, INFORMATION}` as container words. "CRediT authorship contribution statement" and "Ethics approval and consent to participate" contain none of these. Combined with font_size 7.97pt < 11pt visual-heading threshold, the function returns False.

**B: Normalization skips subsection_heading.** `_normalize_backmatter_roles_after_boundary()` line 2062 unconditionally skips any block with role in `{section_heading, subsection_heading, sub_subsection_heading}`. Even a block that SHOULD be a backmatter boundary (but was classified as subsection_heading due to font size) never gets promoted.

**C: Body-end detection breaks on same-page body+ref.** When body and references share a page (especially two-column: left=body, right=ref), the forward scan's per-column check finds the left column has body without tail → `any_body_without_tail = True` → scan continues past the actual body end. `body_end_page` stays at the last pure-body page, leaving the mixed page as a no-man's-land.

### 2.3 Scope of impact

| Paper | Effect | Frequency |
|-------|--------|-----------|
| 25K5KZAQ | CRediT/Ethics in body flow, not backmatter | ~30-50% of papers with CRediT |
| NC66N4Q3 | body_end_page=None, boundary degraded | ≤5% (same-page body+ref is rare) |
| Any with unknown boundary headings | Backmatter heading → subsection_heading | Unknown but likely >5% |

---

## 3. Design: Figure-Containment Render Pass

### 3.1 Strategy

**Not a legend-matching fix.** The containment check is a **render-hygiene pass** that runs AFTER `build_figure_inventory` has completed. It does not affect asset assignment or legend selection — it only prevents figure-internal text from appearing as body prose in the rendered fulltext.

Rationale: The containment fix must handle the case where Figure 1 has NO matched_figures entry (demoted caption). In that case, we compute a composite bbox from same-page `figure_asset` blocks directly.

### 3.2 Algorithm (authoritative — matches §3.7 contracts)

```
def _tag_figure_contained_text(blocks: list[dict], matched_figures: list[dict]) -> None:
    for page in set(b.get("page") for b in blocks):
        page_blocks = [b for b in blocks if b.get("page") == page]
        figure_regions, covered_asset_ids = [], set()

        # Source 1: matched_figures cluster_bbox
        for mf in matched_figures:
            if mf.get("page") == page:
                cb = mf.get("cluster_bbox") or mf.get("asset_bbox")
                if cb:
                    figure_regions.append(("matched", cb))
                    for aid in mf.get("asset_block_ids", []):
                        covered_asset_ids.add(aid)

        # Source 2: uncovered figure-like assets (when caption is demoted — no matched entry)
        fallback_assets = [
            b for b in page_blocks
            if b.get("block_id") not in covered_asset_ids
            and b.get("role") in {"figure_asset", "media_asset"}
            and not b.get("_table_owned")
            and (b.get("asset_family_hint") == "figure_like"
                 or str(b.get("raw_label") or "") in {"image", "chart", "figure_title"})
        ]
        fallback_regions = _cluster_bboxes_by_proximity(
            [b["bbox"] for b in fallback_assets], margin=40
        )
        for fr in fallback_regions:
            if not _highly_overlaps_any_matched_region(fr, figure_regions):
                figure_regions.append(("fallback", fr))

        # Tag contained text blocks
        for block in page_blocks:
            if block.get("role") in {"figure_asset", "media_asset", "noise",
                                     "figure_caption", "figure_caption_candidate"}:
                continue
            block_bbox = block.get("bbox")
            if not block_bbox or len(block_bbox) < 4:
                continue
            for _, fr in figure_regions:
                if _is_contained(block_bbox, fr):
                    block["_figure_contained"] = True
                    if block.get("role") in {"body_paragraph", "subsection_heading",
                                             "footnote", "non_body_insert", "frontmatter_noise"}:
                        block["role"] = "figure_inner_text"
                    break


def _is_contained(block_bbox, region_bbox):
    """Contract E: center-inside + overlap/block_area >= 0.85 + width guard."""
    bw = block_bbox[2] - block_bbox[0]
    rw = region_bbox[2] - region_bbox[0]
    if bw > rw * 0.95:
        return False
    cx = (block_bbox[0] + block_bbox[2]) / 2
    cy = (block_bbox[1] + block_bbox[3]) / 2
    if not (region_bbox[0] <= cx <= region_bbox[2] and region_bbox[1] <= cy <= region_bbox[3]):
        return False
    ix1, iy1 = max(block_bbox[0], region_bbox[0]), max(block_bbox[1], region_bbox[1])
    ix2, iy2 = min(block_bbox[2], region_bbox[2]), min(block_bbox[3], region_bbox[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return False
    overlap_area = (ix2 - ix1) * (iy2 - iy1)
    block_area = bw * (block_bbox[3] - block_bbox[1])
    return overlap_area / block_area >= 0.85


def _highly_overlaps_any_matched_region(fallback_bbox, figure_regions):
    for tag, matched_bbox in figure_regions:
        if tag != "matched":
            continue
        ix1 = max(fallback_bbox[0], matched_bbox[0])
        iy1 = max(fallback_bbox[1], matched_bbox[1])
        ix2 = min(fallback_bbox[2], matched_bbox[2])
        iy2 = min(fallback_bbox[3], matched_bbox[3])
        if ix2 > ix1 and iy2 > iy1:
            overlap = (ix2 - ix1) * (iy2 - iy1)
            fb_area = (fallback_bbox[2] - fallback_bbox[0]) * (fallback_bbox[3] - fallback_bbox[1])
            if fb_area > 0 and overlap / fb_area >= 0.5:
                return True
    return False
```

### 3.3 Cluster bbox aggregation (proximity-based, Contract D)

When no `matched_figures` entry exists for a page's figure assets (demoted caption case),
use proximity clustering — composite figures have gaps between panels that strict overlap misses.

```python
def _cluster_bboxes_by_proximity(bboxes: list[list[int]], margin: int = 40) -> list[list[int]]:
    """Union-Find on inflated bboxes.  Two bboxes merge when their inflated
    (by margin) versions overlap.  Returns union of original (non-inflated) bboxes."""
    if not bboxes:
        return []
    n = len(bboxes)
    parent = list(range(n))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    for i in range(n):
        for j in range(i + 1, n):
            b1, b2 = bboxes[i], bboxes[j]
            if (b1[2] + margin > b2[0] - margin and b2[2] + margin > b1[0] - margin
                    and b1[3] + margin > b2[1] - margin and b2[3] + margin > b1[1] - margin):
                union(i, j)
    components = {}
    for i in range(n):
        root = find(i)
        components.setdefault(root, []).append(bboxes[i])
    return [
        [min(b[0] for b in group), min(b[1] for b in group),
         max(b[2] for b in group), max(b[3] for b in group)]
        for group in components.values()
    ]
```

This replaces the earlier `_cluster_bboxes_by_overlap` sketch.

### 3.4 Protection: DO NOT touch render_default

Critical constraint from P0 Fix 5: `figure_inner_text` assignment must NOT change `render_default` or `index_default`. The original block's participation in figure matching is unaffected — only its rendered role changes.

Standard blocks that appear inside a figure region:
- Already rendered: not touched (render_default already false in some cases)
- Previously body_paragraph: role changed to figure_inner_text. The renderer must already handle `figure_inner_text` skipping (confirmed: ocr_render.py already excludes figure_inner_text from body flow).

### 3.5 Affected code locations

| File | Change |
|------|--------|
| `ocr.py` (or `ocr_figures.py`) | New function `_tag_figure_contained_text()`, called in `postprocess_ocr_result()` AFTER `build_figure_inventory(blocks)` and BEFORE `render_fulltext_markdown(blocks)` — NOT inside `normalize_document_structure` |
| `ocr.py` or `ocr_figures.py` | Helper `_cluster_bboxes_by_proximity()` (can live in same file) |
| `ocr_render.py` | Verify figure_inner_text is already excluded from body flow (confirmed) — no change expected |

### 3.6 Test strategy

| Test case | What it verifies |
|-----------|-----------------|
| Block fully inside figure_asset bbox → role becomes figure_inner_text | Core containment |
| Block partially inside (margin-adjacent) → NOT tagged | Margin boundary |
| Block inside cluster_bbox from matched_figures → tagged | Cluster path |
| Block inside cluster_bbox from unmatched assets → tagged | Demoted caption path |
| render_default unchanged after role change | Render hygiene |
| XD2BPCMG page 3 regression | 33 footnote blocks → figure_inner_text |

### 3.7 Implementation contracts (from review)

**Contract A — Call site: after build_figure_inventory, before render.**
NOT inside `normalize_document_structure()` — it runs before figure inventory.
Correct placement: `postprocess_ocr_result()`, between `build_figure_inventory(blocks)` and `render_fulltext_markdown(blocks)`.

**Contract B — Fallback asset eligibility: include `media_asset` with figure-like family.**
Fallback clustering must use the same asset eligibility as `build_figure_inventory`:
```python
role in {"figure_asset", "media_asset"} and not table_owned
and (asset_family_hint == "figure_like" or raw_label in {"image", "chart", "figure_title"})
```

**Contract C — Fallback assets must exclude those already covered by matched_figures.**
```python
covered_asset_ids = set()
for mf in matched_figures:
    for aid in mf.get("asset_block_ids", []):
        covered_asset_ids.add((mf.get("page"), aid))
# Fallback clustering only uses assets NOT in covered_asset_ids.
# If fallback region is contained by / highly overlaps a matched region, drop it.
```

**Contract D — Proximity clustering, not overlap clustering.**
Multi-panel composite figures have gaps between panels — strict overlap misses them.
```python
def _cluster_bboxes_by_proximity(bboxes, margin=40):
    # inflate each bbox by margin, union overlapping inflated bboxes, return original-bbox unions
```

**Contract E — Containment test: center-inside + overlap ratio, not raw bbox_contains.**
```python
def _is_contained(block_bbox, region_bbox):
    cx = (block_bbox[0] + block_bbox[2]) / 2
    cy = (block_bbox[1] + block_bbox[3]) / 2
    center_inside = (region_bbox[0] <= cx <= region_bbox[2] and region_bbox[1] <= cy <= region_bbox[3])
    overlap = intersection_area(block_bbox, region_bbox) / block_area(block_bbox)
    return center_inside and overlap >= 0.85 and block_width <= region_width * 0.95
```

**Out of scope (first release):** `render_default`/`index_default` unchanged. Renderer skips `figure_inner_text` by role (confirmed). Indexing behavior is out of scope unless indexer does not respect role — document this in the function docstring.

---

## 4. Superseded Backmatter Sketch — DO NOT IMPLEMENT

> **WARNING:** This section (§4.1–§4.7) documents a rejected design that was reviewed
> and found to have 3 unresolved blockers. It is preserved here as diagnostic reference
> material only. **Do not implement anything from §4.1–§4.7.**
>
> The current spec for backmatter redesign starts at §4.8 (review verdict).
> A future separate spec must resolve §4.8's blockers before any implementation.

### 4.1 Core principle (superseded)

**References are the dividing line.** Everything after the first `reference_heading` is backmatter. This replaces the current forward/backward scan approach.

**Why this simplifies:** Because reference headings are detected by the structural gate with high confidence (line text matches "References" / "Bibliography" etc.), and reference items have strong typographic signatures (reference-like family anchor). Using ref as the anchor eliminates the dependency on body-end detection + backmatter heading recognition.

### 4.2 Tail zone redefinition (superseded)

| Current | Proposed (rejected) |
|---------|----------|
| `body_zone` up to inferred body_end_page | Body flows until first reference_heading |
| `tail_nonref_hold_zone` before ref | Merged into body_zone or post-ref-zone |
| `post_reference_backmatter_zone` after ref | `backmatter_zone`: everything after first reference_heading |
| `reference_zone` | Unchanged |

### 4.3 Algorithm (superseded — see §4.8 for blockers)

```
1. Find the canonical reference_heading:
   - Scan ALL pages for blocks with role == "reference_heading"
   - Select the first one (minimum page number, then minimum y)
   
2. Partition blocks:
   - Page < ref_heading_page: body_zone (no change)
   - Page == ref_heading_page AND y < ref_heading_y: body_zone
   - Page == ref_heading_page AND y >= ref_heading_y AND role != reference_*: 
     → backmatter_zone, normalize to backmatter_body
   - Page > ref_heading_page: backmatter_zone
   
3. Normalize backmatter blocks:
   - heading roles → backmatter_heading (regardless of font size / container words)
   - body_paragraph → backmatter_body
   - non_body_insert → backmatter_body (if text content exists)
```

### 4.4 Fix for 25K5KZAQ (superseded — incomplete without pre-ref handling)

With the ref-boundary approach, page 10 would be partitioned as:

```
y < 1400 (References heading): body_zone — Discussion, CRediT, Ethics, Declaration
y >= 1400: reference_zone + backmatter_zone
```

Wait — this means CRediT/Ethics would still be in `body_zone` because they're ABOVE the References heading. The ref-boundary approach alone doesn't fix the CRediT classification — we still need to handle pre-ref backmatter.

**Revised: Pre-ref backmatter detection via known heading patterns.**

```
1. Run ref-boundary partition (as above)
2. In pre-ref body_zone, scan for known backmatter section headings:
   - "CRediT authorship contribution statement"
   - "Ethics approval and consent to participate" 
   - "Declaration of competing interest"
   - "Supplementary materials"
   - "Data availability"
   - "Acknowledgements" / "Acknowledgments"
   - "Funding"
   - "Author contributions" / "CRediT"
   - Any heading matching _BACKMATTER_TITLE_DENY_LIST patterns
3. First matched heading → pre-ref backmatter start
   - Blocks between first matched heading and next body heading → backmatter_zone
   - Blocks after first matched heading AND before reference_heading → backmatter_zone
```

This combines the ref-boundary anchor with a known-heading table for pre-ref backmatter. The heading table is an explicit, curated list (not heuristic) — low false-positive risk because these are standardized section names.

### 4.5 Known heading table (superseded — gate too loose for substring safety)

```python
_PRE_REF_BACKMATTER_HEADINGS = {
    "credit authorship contribution statement",
    "ethics approval and consent to participate",
    "ethics statement",
    "declaration of competing interest",
    "competing interests",
    "conflict of interest",
    "data availability",
    "data availability statement",
    "supplementary materials",
    "supplementary data",
    "supplementary information",
    "appendix a",
    "appendix",
    "acknowledgements",
    "acknowledgments",
    "funding",
    "author contributions",
    "credit",
}
```

### 4.6 Fix for NC66N4Q3 (superseded — column-aware partition unresolved)

The two-column same-page body+ref case (page 56: left=Discussion, right=References):

```
1. Detect candidate ref blocks per-column via marker_signature + reference_zone
2. If ref blocks exist on a page WITHOUT a reference_heading,
   check if a reference_heading exists on the immediately previous page
3. If yes, this is a continuation page — treat remaining body as body_flow,
   not as pre-ref-backmatter
```

This is a refinement of the ref-boundary approach: the ref-heading's page becomes the partition boundary, not the ref-blocks' page.

### 4.7 Affected code locations (superseded — call graph not yet traced)

| File | Change |
|------|--------|
| `ocr_roles.py` | `_is_backmatter_boundary_heading()` — add known-heading table OR defer to document-context pass |
| `ocr_document.py` | `_reconcile_tail_spread()` — replace forward/backward scan with ref-boundary scan |
| `ocr_document.py` | `_normalize_backmatter_roles_after_boundary()` — remove subsection_heading skip, add body_paragraph→backmatter_body conversion |
| `ocr_document.py` | `_promote_tail_body_candidates()` — allow same-page promotion below backmatter anchor |
| `ocr_document.py` | `infer_zones()` — simplify zone boundary using ref partition |
| `ocr_families.py` | May need reference anchor tuning |

### 4.8 Review verdict: NOT ready for implementation

The review identified **3 unresolved blockers** and **3 structural weaknesses** that must be resolved before a new backmatter spec can be written.

#### Blocker 1: `reference_heading` ≠ `reference_zone` extent

The algorithm's `Page > ref_heading_page → backmatter_zone` breaks on multi-page references. Most papers' reference sections span 2+ pages. The boundary is not `reference_heading` but `reference_zone.end`.

Correct model:
```
1. Detect verified reference_zone (heading + item range + page/y extent)
2. Blocks before reference_zone.start → body or pre-ref backmatter
3. Blocks inside reference_zone → preserve reference_heading/reference_item
4. Blocks after reference_zone.end → post-ref backmatter
```

#### Blocker 2: Same-page body+ref must be column-aware

NC66N4Q3 page 56: left=Discussion, right=References. Cannot partition by page or y alone.
```
If body and reference blocks share a page:
  reference column / x-range → reference_zone
  body column outside reference x-range → body_flow
```
Current code has tail/backmatter ownership in `_promote_tail_body_candidates()`,
`_assign_tail_spread_ownership()`, and renderer `_reorder_tail_run()` — any redesign
must update all three consistently.

#### Blocker 3: Pre-ref known-heading table needs stronger gate

The `_PRE_REF_BACKMATTER_HEADINGS` set is directionally correct but risks false positives if using substring matching on generic words like `"funding"`, `"credit"`, `"appendix"`.

Required gates:
- Normalized exact match OR anchored regex only — no substring matching except explicitly listed aliases
- Only trigger if reference_zone exists, heading is before reference_zone.start,
  document progress >= 0.50 (or page >= max(2, total_pages - 3)),
  heading role is heading-like OR bold/short block,
  AND no later numbered body section heading appears before References

#### Structural weaknesses

1. **Corpus audit needed first.** Before writing a new spec, audit the full vault for:
   - Papers with CRediT/Ethics/Declaration backmatter (count, patterns, font sizes, column layouts)
   - Papers with multi-page reference sections + post-ref backmatter
   - Papers with same-page body+ref on final page
   This data determines whether the new design generalizes or remains paper-specific.

2. **Verification target `body_end_page=3` is wrong.** NC66N4Q3 page 56 has Discussion in left column — body_end_page should not be 3. Replace with:
   ```
   NC66N4Q3: page 56 right-column ref items remain reference_zone,
             page 56 left-column Discussion remains body_flow,
             tail spread does NOT enter degraded no-boundary mode
   ```

3. **Affected code locations are still speculative.** Current tail/backmatter path includes
   `_reconcile_tail_spread`, `infer_zones`, `_normalize_backmatter_roles_after_boundary`,
   `_promote_tail_body_candidates`, `_assign_tail_spread_ownership`, `_reorder_tail_run`.
   Before redesign, trace and document the full call graph.

### 4.9 Recommended approach for new spec

Write a new spec in this order:
```
Phase A: Audit corpus for backmatter patterns (CRediT, font sizes, column layouts, ref spans)
Phase B: Trace and document full tail/backmatter call graph
Phase C: Define reference_zone.start/end model (not reference_heading alone)
Phase D: Define same-page column-aware partition for body+ref
Phase E: Define pre-ref backmatter known-heading table with exact-match gate
Phase F: Update role normalization (remove subsection_heading skip)
Phase G: Update renderer _reorder_tail_run consistently
Phase H: Real-paper regression (min 20 papers with diverse backmatter)
```

### 4.10 Test strategy (for the future spec)

| Test case | What it verifies |
|-----------|-----------------|
| 25K5KZAQ: CRediT/Ethics → backmatter_body | Known heading detection |
| NC66N4Q3: ref items remain reference_zone, Discussion remains body_flow, no degraded mode | Same-page body+ref box partition |
| Standard paper: no pre-ref backmatter → no change | Non-regression |
| Paper with multi-page ref section + post-ref backmatter → all refs preserved | reference_zone.end model |
| Paper with appendix after ref → appendix in post-ref backmatter | Post-ref boundary |
| Paper with no references → fallback to old algorithm | Degraded mode |
| font_size < 11pt bold heading on tail page → backmatter_heading | Font-independent promotion |

---

## 5. Implementation Order

### Phase 1: Figure containment (only)

- Independent of P0 changes. Can be implemented and tested standalone.
- Implementation-plan ready once §3.2/§3.3 are confirmed to match §3.7 contracts.
- **Estimated scope:** ~50–80 lines new code + imports + unit tests.

**Backmatter redesign:** No implementation in this spec. Next action is corpus audit + call graph trace + new spec (see §4.9 for full roadmap).

---

## 6. Risk & Verification

### 6.1 Containment risks

| Risk | Mitigation |
|------|-----------|
| False positives: body text inside figure bounding box | Use center-inside + overlap/block_area >= 0.85 + block_width <= region_width * 0.95 (Contract E). Only reassign roles in {body_paragraph, footnote, subsection_heading, non_body_insert, frontmatter_noise}. |
| Full-width text blocks that span past figure region | Width check (Contract E): block_width > region_width * 0.95 → not tagged |
| Matched figure region and fallback region double-count | covered_asset_ids + _highly_overlaps_any_matched_region guard (Contract C) |
| Performance: per-page bbox comparison O(n*m) | n < 200 blocks/page, m < 20 regions/page — negligible |

### 6.2 Backmatter — not yet implementation-ready

This section is preserved as reference material for the future redesign. The following blockers (§4.8) must be resolved before any implementation:

1. Multi-page reference sections broken by `ref_heading → backmatter` model
2. Same-page body+ref requires column-aware partition (not page/y-only)
3. Pre-ref known-heading table needs stronger gate (exact match, document-progress guard)

### 6.3 Verification checklist (Figure containment only)

- [ ] All P0 tests still pass (regression)
- [ ] Containment: XD2BPCMG fulltext no longer contains footnote-inside-figure blocks
- [ ] Containment: render_default/index_default unchanged for tagged blocks
- [ ] Containment: matched_figures cluster_bbox path works (standard papers)
- [ ] Containment: fallback asset clustering path works (demoted-caption papers)
- [ ] Containment: covered_asset_ids exclusion prevents double-region
- [ ] 9TW98JH8 (already correct): unchanged
