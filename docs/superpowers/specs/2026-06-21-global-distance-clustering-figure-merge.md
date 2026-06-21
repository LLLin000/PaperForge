# Global Distance Clustering for Figure Merge

> **Date:** 2026-06-21
> **Status:** draft for review
> **Scope:** Replace greedy region-growing figure merge with global distance-based clustering + caption-as-boundary fallback
> **Supersedes:** `2026-06-20-region-growing-figure-merge-design.md`

---

## 1. Why region-growing failed

The 2026-06-20 spec introduced `_grow_region_from_seed`: starting from one asset, greedily absorb neighbors right and down. It was extended to 4 directions (left, up, right, down) but the core problem remains:

| Problem | Why | Consequence |
|---------|-----|-------------|
| **First seed wins** | Assets are sorted y-x; the top-left seed absorbs everything it can reach | Remaining seeds get fewer assets → partial merges |
| **No backtracking** | Once absorbed, an asset is `seen_growth_ids` and can't join another group | Wrong merges persist |
| **Overlapping candidates** | An asset exists in single_asset + same_row + region_grown groups simultaneously | Groups compete via scoring; the closest asset wins, merged group loses |
| **Local greed, not global view** | Each seed only sees immediate neighbors, not the whole page layout | 2x2 grids, irregular layouts, and cross-column figures all fail |

**Concrete failure (SAN9AYVR Figure 23, page 50):**
A large multi-panel figure with panels a-h spanning the page. Region growth from the top-left seed absorbs some panels, eats across the page, but misses panels in the lower-right because they're more than one "gap" away from any grown boundary. Those missed panels become unmatched assets.

---

## 2. Design: distance-based clustering

### Core principle

On a given page, ASSETS THAT ARE CLOSE TOGETHER WITH NO TEXT SEPARATOR BETWEEN THEM FORM ONE FIGURE.

This is how human vision works: global spatial proximity + text boundaries = perceptual groups.

### Algorithm (8 steps)

```
Step 1 — Collect figure assets on the page
  input: all blocks on a page
  filter: role=figure_asset OR (role=media_asset AND raw_label∈{image,chart,figure})
  exclude: _non_body_media, table assets, non_body_insert

Step 2 — Remove single_asset from candidate generation
  Assets that belong to a cluster must NOT also exist as standalone candidates.
  Only unclustered single assets get standalone groups.

Step 3 — Pairwise distance clustering
  For each pair of assets (A, B) on the same page:
    - horizontal_gap = max(0, left_b - right_a)  [right edge of leftmost to left edge of rightmost]
    - vertical_gap = max(0, top_b - bottom_a)     [bottom of upper to top of lower]
    - candidate_for_merge = true IF:
        horizontal_gap <= max(page_width * 0.12, 40)
        AND vertical_gap <= max(page_height * 0.08, 40)
    - BUT: if a text block (body_paragraph, section_heading, subsection_heading)
      with non-empty text exists in the bounding rectangle between A and B,
      candidate_for_merge = false (text separator)

  Union-find: connect all candidate pairs into clusters.

Step 4 — Irregular layout merge
  For each pair of clusters (C1, C2):
    y_overlap = overlap of C1's y-range and C2's y-range
    shorter_height = min(height of C1, height of C2)
    if y_overlap >= shorter_height * 0.5:
      merge C1 and C2 even if horizontal_gap exceeds threshold
    (Rationale: 1 tall left panel + 3 small right panels form one figure)

Step 5 — Generate candidate groups
  Each cluster → ONE candidate group entry
  cluster_bbox = union of all asset bboxes in the cluster
  group_type = "distance_cluster"
  evidence = ["same_page", "distance_clustered"]

Step 6 — Count legends on the page
  legends = blocks with role=figure_caption on this page
  n_legends = len(legends)

Step 7 — Match legends to clusters
  Case n_legends == 0:
    → orphan clusters, pass to _expand_matched_assets_locally (existing cross-page fallback)
  Case n_legends == 1:
    → auto-match legend to cluster. score = 0.85. decision = "matched"
    No scoring competition.
  Case n_legends >= 2:
    → split: sort legends by y-position. Sort clusters by y-position.
      Assign each cluster to the nearest legend.
      If multiple clusters map to the same legend → merge them.
    If any legend has no cluster → pass to single_asset fallback.

Step 8 — Single assets not in any cluster
  → treated as individual candidate groups (backward compatible)
  → matched via existing score_figure_match
```

### Threshold rationale

The gap thresholds (12% page width, 8% page height, min 40px) match the existing thresholds used in `same_row_pair` and `_grow_region_from_seed`. They've been tested on 37 normal papers without false page-swallow. No new threshold tuning needed.

The min 40px floor prevents over-merging on small figures in dense layouts.

### Text separator detection

```python
def _has_text_separator(a: dict, b: dict, all_blocks: list[dict]) -> bool:
    """Check if any text block exists in the bounding rect between assets a and b."""
    ax1, ay1, ax2, ay2 = a["bbox"]
    bx1, by1, bx2, by2 = b["bbox"]
    # bounding rect of both assets
    rect = [min(ax1, bx1), min(ay1, by1), max(ax2, bx2), max(ay2, by2)]
    for block in all_blocks:
        role = block.get("role", "")
        if role not in ("body_paragraph", "section_heading", "subsection_heading"):
            continue
        txt = str(block.get("text", "") or "").strip()
        if not txt:
            continue
        bx1, by1, bx2, by2 = block["bbox"]
        # text block INSIDE the bounding rect AND BETWEEN the two assets vertically
        if (bx1 > rect[0] and bx2 < rect[2] and
            by1 > min(ay2, by2) and by2 < max(ay1, by1)):
            return True
    return False
```

---

## 3. Edge-case matrix with fallbacks

All 10 scenarios from the PROJECT-MANAGEMENT analysis, with concrete handling:

| # | Scenario | Detection | Handling | Fallback |
|---|----------|-----------|----------|----------|
| 1 | One page, 2+ separate figures | n_legends >= 2 | Split by y-proximity | Per-asset single_agent scoring |
| 2 | Cross-page figure | n_legends == 0 after per-page clustering | Move to `_expand_matched_assets_locally` | Existing sequential fallback |
| 3 | Dense old-journal layout | Text separator in gap | Don't merge across separator | Tight spacing with no text → distance threshold allows merge |
| 4 | Irregular layout (1 tall + 3 small) | y_overlap >= 50 | Force merge across x-gap | If over-merged, caption-as-boundary splits |
| 5 | Embedded caption inside figure | Caption is not an asset | Ignored by clustering | N/A |
| 6 | Figure + table on same page | Split by type (figure_asset vs table_asset) | Cluster separately | Type-independent position fallback |
| 7 | Multi-column figures same y | n_legends >= 2 | Caption-as-boundary split | Single_asset fallback |
| 8 | Orphan single-panel figure | Cluster of size 1 | Standalone candidate | Existing score_figure_match |
| 9 | Text-separated figures | Text separator exists | Don't merge across | Distance threshold without separator |
| 10 | Very large multi-panel (>10 panels) | Many assets, single legend | Cluster merges all; sequential expansion collects stragglers | Existing `_expand_matched_assets_locally` |

---

## 4. Files to change

### `paperforge/worker/ocr_figures.py`

| Function | Lines | Change |
|----------|-------|--------|
| `_build_candidate_figure_groups_from_assets` | 487-603 | Replace entire body. Remove single_asset, same_row, page_assets, region_growth. Add clustering. |
| `_grow_region_from_seed` | 361-389 | DELETE (replaced by clustering) |
| `_validate_grown_region` | 392-413 | DELETE (validation moves into clustering) |
| `_asset_gap_left` | (new) | DELETE (added in previous fix, no longer needed) |
| `_asset_gap_above` | (new) | DELETE (no longer needed) |
| `_score_legend_to_group` | 608-662 | MODIFY: add `"distance_cluster"` case returning score=0.85, `decision="matched"` when n_legends==1 |
| `_expand_matched_assets_locally` | 665-? | No change (cross-page fallback stays) |
| NEW `_cluster_page_assets` | (new) | ADD: main clustering function |
| NEW `_has_text_separator` | (new) | ADD: text separator detection |

### `paperforge/worker/ocr_figures.py` — detailed function changes

**`_build_candidate_figure_groups_from_assets()`** — replacement:

```python
def _build_candidate_figure_groups_from_assets(
    assets: list[dict], blocks: list[dict],
    legends: list[dict], page_width: float = 1200
) -> list[dict]:
    media = _filter_figure_assets(assets)
    groups: list[dict] = []
    next_id = 1

    by_page: dict[int, list[dict]] = {}
    for block in media:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_media in by_page.items():
        if len(page_media) == 0:
            continue

        # Count legends on this page
        page_legends = [l for l in legends if l.get("page") == page]

        # Cluster assets by distance
        clusters = _cluster_page_assets(page_media, blocks, page_width)

        for cluster in clusters:
            entry = _candidate_group_entry(
                f"group_{next_id:04d}", page, cluster,
                "distance_cluster",
                ["same_page", "distance_clustered"],
            )
            groups.append(entry)
            next_id += 1

        # Single assets not in any cluster → individual groups
        clustered_ids = set()
        for c in clusters:
            for bid in [b.get("block_id") for b in c]:
                clustered_ids.add(str(bid))
        for block in page_media:
            if str(block.get("block_id", "")) not in clustered_ids:
                groups.append(_candidate_group_entry(
                    f"group_{next_id:04d}", page, [block],
                    "single_asset", ["same_page", "single_asset"]
                ))
                next_id += 1

    return groups
```

**`_cluster_page_assets()`** — new function:

```python
def _cluster_page_assets(
    page_assets: list[dict],
    all_blocks: list[dict],
    page_width: float,
) -> list[list[dict]]:
    """Cluster assets by spatial proximity with text-separator awareness."""
    if len(page_assets) <= 1:
        return [list(page_assets)]

    # Get page height from first asset's bbox
    page_height = 1600.0  # default
    for b in all_blocks:
        ph = b.get("page_height")
        if ph:
            page_height = float(ph)
            break

    h_threshold = max(page_width * 0.12, 40.0)
    v_threshold = max(page_height * 0.08, 40.0)

    # Union-find
    parent = list(range(len(page_assets)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[py] = px

    for i in range(len(page_assets)):
        for j in range(i + 1, len(page_assets)):
            a, b = page_assets[i], page_assets[j]
            ab = a.get("bbox", [0, 0, 0, 0])
            bb = b.get("bbox", [0, 0, 0, 0])

            h_gap = max(0.0, bb[0] - ab[2], ab[0] - bb[2])
            v_gap = max(0.0, bb[1] - ab[3], ab[1] - bb[3])

            if h_gap > h_threshold:
                # Check y-overlap for irregular layouts
                a_y1, a_y2 = ab[1], ab[3]
                b_y1, b_y2 = bb[1], bb[3]
                y_overlap = max(0, min(a_y2, b_y2) - max(a_y1, b_y1))
                shorter_h = min(a_y2 - a_y1, b_y2 - b_y1)
                if shorter_h > 0 and y_overlap / shorter_h < 0.5:
                    continue  # no horizontal overlap and not vertically aligned → separate clusters

            if v_gap > v_threshold:
                continue  # too far apart vertically → separate clusters

            # Text separator check
            if _has_text_separator(a, b, all_blocks):
                continue

            union(i, j)

    # Build clusters
    clusters: dict[int, list[dict]] = {}
    for i, block in enumerate(page_assets):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(block)

    return list(clusters.values())
```

**`_has_text_separator()`** — new function:

```python
def _has_text_separator(a: dict, b: dict, all_blocks: list[dict]) -> bool:
    """True if body text or heading exists in the gap between assets a and b."""
    ab = a.get("bbox", [0, 0, 0, 0])
    bb = b.get("bbox", [0, 0, 0, 0])

    gap_top = min(ab[3], bb[3])
    gap_bot = max(ab[1], bb[1])
    if gap_bot <= gap_top:
        return False  # assets overlap vertically, no gap to check

    gap_left = min(ab[0], bb[0])
    gap_right = max(ab[2], bb[2])

    for block in all_blocks:
        role = block.get("role", "")
        if role not in ("body_paragraph", "section_heading", "subsection_heading"):
            continue
        txt = str(block.get("text", "") or "").strip()
        if not txt:
            continue
        cb = block.get("bbox", [0, 0, 0, 0])
        # Block must be inside the gap rectangle
        if (cb[0] >= gap_left and cb[2] <= gap_right
                and cb[1] >= gap_top and cb[3] <= gap_bot):
            return True
    return False
```

**`_score_legend_to_group()`** — modification:

```python
# Add before the `if gt == "page_assets":` block:
    if gt == "distance_cluster":
        return {
            "score": 0.85,
            "decision": "matched",
            "evidence": ["same_page", "distance_clustered"],
        }
```

This replaces the 0.55 flat score for `page_assets` with a 0.85 guaranteed match for distance-clustered groups.

---

## 5. Acceptance criteria

1. **SAN9AYVR Figure 23**: All sub-panels (a-h) merged into one figure, 0 unmatched assets on page 50.
2. **2GN9LMCW Figure 4**: All 6 assets merged (was previously partially merged).
3. **DWQQK2YB Figure 2**: Stays correctly on page 38 with 19 assets (existing fix, must not regress).
4. **3FDT9652**: No regression on multi-column figures (separate figures in different columns with their own captions must not merge).
5. **2GN9LMCW Figures 1-3**: Single-panel figures remain as independent figures (clusters of size 1).
6. **No page-swallow**: A page with 10+ assets across 3 separate figures must not merge them all (text separator + caption-as-boundary prevents this).

---

## 6. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Over-merge (2 separate figs → 1 cluster) | Medium | Medium | Caption-as-boundary split when n_legends >= 2 |
| Under-merge (single fig → 2+ clusters) | Low | Low | `_expand_matched_assets_locally` collects orphans |
| Text separator false positive (body text between sub-panels of same fig) | Low | Medium | Text inside display_zone is usually caption/figure text, not body_paragraph. Real body text between sub-panels is rare in published papers. |
| Distance threshold too tight for large figures | Low | Low | y-overlap signal merges irregular layouts. Cross-page fallback catches stragglers. |
| Performance (pairwise O(n²)) | Low | Low | Pages with > 50 assets are rare (< 1% of corpus). Union-find is O(n log n). |

---

## 7. Files summary

| File | Action |
|------|--------|
| `paperforge/worker/ocr_figures.py` | Replace `_build_candidate_figure_groups_from_assets` body; add `_cluster_page_assets` + `_has_text_separator`; delete `_grow_region_from_seed` + `_validate_grown_region`; modify `_score_legend_to_group` |
| `tests/test_ocr_figures.py` | Add tests for distance clustering, text separator, multi-legend split, irregular layout |
| `tests/test_ocr_real_paper_regressions.py` | Add SAN9AYVR regression test for Figure 23 merge |
| `PROJECT-MANAGEMENT.md` | Updated with analysis (already done) |

---

## 8. Rejected alternatives

| Alternative | Why rejected |
|-------------|-------------|
| Fix region-growth scoring (new bonus/threshold) | Doesn't solve the greedy-first-seed-wins problem |
| Add more growth directions (8-direction) | Still local, still greedy, still no backtracking |
| Machine learning for figure grouping | Over-engineering. Distance clustering is deterministic, auditable, and sufficient. |
| Per-page manual layout templates | Not generalizable to arbitrary journal formats |
