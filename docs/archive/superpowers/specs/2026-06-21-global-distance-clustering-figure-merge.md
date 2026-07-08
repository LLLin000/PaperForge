# Global Distance Clustering for Figure Merge

> **Date:** 2026-06-21
> **Status:** v3 — revised after 2nd GPT review
> **Scope:** Replace greedy region-growing figure merge with caption-band-constrained pairwise distance clustering + group-aware sequential fallback
> **Supersedes:** `2026-06-20-region-growing-figure-merge-design.md`

---

## 1. Why region-growing failed

The 2026-06-20 spec introduced `_grow_region_from_seed`: greedy seed expansion in 2→4 directions. Still fails because:

| Problem | Why | Consequence |
|---------|-----|-------------|
| **First seed wins** | Assets sorted y-x; top-left seed absorbs everything reachable | Remaining seeds get fewer assets → partial merges |
| **No backtracking** | Absorbed asset is `seen_growth_ids`, can't rejoin | Wrong merges persist |
| **Overlapping candidates** | One asset in single_asset + same_row + region_grown simultaneously | Groups compete by scoring; closest wins, merged loses |
| **Local greed** | Each seed only sees neighbors, not whole page | 2x2 grids, irregular layouts fail |

---

## 2. Design: global distance clustering + caption band partition + group-aware fallback

### Core principle

1. **Global pairwise clustering** replaces greedy seed-growth. Union-find on all pairwise distances within a caption band produces globally optimal clusters.
2. **Caption bands partition the page BEFORE clustering** on multi-legend pages. Assets in different bands can NEVER be in the same cluster.
3. **One candidate group per asset** — no overlapping candidates, no competition between single_asset and merged group.
4. **Group-aware sequential fallback** allows unmatched distance_clusters to be consumed as whole groups, not asset-by-asset.

### Implementation contract

```text
1. Extract _filter_figure_assets() from current compatible asset filtering:
   figure_asset: accept.
   media_asset: accept if raw_label in {image, chart, figure},
                or raw_label empty,
                or raw_label == "table" AND "<img" in text.lower().

2. Replace _build_candidate_figure_groups_from_assets() candidate generation:
   remove: page_assets, same_row_pair/triple, region_grown_group.
   produce exactly ONE candidate group per asset (cluster or singleton).

3. For each page:
   page_legends = deduped ordered_legends from build_figure_inventory.
   if len(page_legends) >= 2:
       partition assets using _partition_assets_by_caption_bands().
       cluster independently inside each band.
   else:
       cluster all page assets together.

4. _cluster_page_assets():
   pairwise union by h_gap/v_gap/no_text_separator.
   irregular merge across clusters only when ALL of:
       n_legends <= 1
       y_overlap / shorter_h >= 0.5
       horizontal_gap <= page_width * 0.25
       no text separator between clusters.

5. Group type:
   len(cluster) >= 2 => distance_cluster
   len(cluster) == 1 => single_asset
   Each group entry carries:
       caption_band_id: which caption band it belongs to (or None)
       page_legend_count: total legends on this page
       page_cluster_count: total groups of all types on this page
       safe_auto_match: len(page_legends)==1 AND page_cluster_count==1 AND len(cluster)>=2

6. _score_legend_to_group():
   single_asset: current score_figure_match (unchanged).
   distance_cluster:
       if group.safe_auto_match: return {"score": 0.85, "decision": "matched"}
       else: score_figure_match(cluster_bbox) + 0.15 bounded multi-asset bonus.

7. Fallback:
   Keep _expand_matched_assets_locally unchanged (same-page only, legend-required).
   Add GROUP-AWARE sequential fallback:
       - unmatched_candidate_groups includes distance_clusters not consumed by any same-page legend.
       - Sequential fallback takes the next available group (all its assets together),
         not individual assets.
       - Old single-asset sequential fallback remains as last resort.
   Track used_group_ids so each group is consumed at most once.
```

---

## 3. Algorithm details

### 3.1 Asset filter (`_filter_figure_assets`)

```python
def _filter_figure_assets(assets: list[dict]) -> list[dict]:
    """Extract figure-like media blocks with backward compatibility."""
    result = []
    for b in assets:
        if b.get("_non_body_media"):
            continue
        role = b.get("role", "")
        if role == "figure_asset":
            result.append(b)
        elif role == "media_asset":
            rl = str(b.get("raw_label", "") or "")
            if rl in {"image", "chart", "figure"}:
                result.append(b)
            elif not rl.strip():
                result.append(b)
            elif rl == "table" and "<img" in str(b.get("text", "") or "").lower():
                result.append(b)
    return result
```

### 3.2 Caption band partition

Use existing `_partition_assets_by_caption_bands()` when `n_legends >= 2`.

Current code already has this function. It uses caption y-boundaries (midpoints between adjacent captions) and assigns assets by center-y. It handles narrow sidecar captions, captions above vs below assets, and free-floating margin.

```python
if n_legends >= 2:
    band_map = _partition_assets_by_caption_bands(page_legends, page_assets, page_height)
    partitions = list(band_map.values())
    unaffiliated = [a for a in page_assets if id(a) not in {id(x) for p in partitions for x in p}]
    if unaffiliated:
        partitions.append(unaffiliated)  # cluster unaffiliated separately
```

### 3.3 Distance clustering

```python
def _cluster_page_assets(
    page_assets: list[dict],
    all_blocks: list[dict],
    n_legends: int,
    page_width: float,
    page_height: float,
) -> list[list[dict]]:
    if len(page_assets) <= 1:
        return [list(page_assets)]

    h_threshold = max(page_width * 0.12, 40.0)
    v_threshold = max(min(page_width, page_height) * 0.08, 40.0)
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
                # Irregular layout: allow wider x-gap if y-overlap is significant
                if n_legends <= 1:
                    a_y1, a_y2 = ab[1], ab[3]
                    b_y1, b_y2 = bb[1], bb[3]
                    y_overlap = max(0, min(a_y2, b_y2) - max(a_y1, b_y1))
                    shorter_h = min(a_y2 - a_y1, b_y2 - b_y1)
                    if shorter_h > 0 and y_overlap / shorter_h >= 0.5:
                        if h_gap > page_width * 0.25:
                            continue
                    else:
                        continue
                else:
                    continue

            if v_gap > v_threshold:
                continue

            if _has_text_separator(a, b, all_blocks):
                continue

            union(i, j)

    clusters: dict[int, list[dict]] = {}
    for i, block in enumerate(page_assets):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(block)

    return list(clusters.values())
```

### 3.4 Text separator (control flow fixed)

```python
def _rect_intersection_area(a, b) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _has_text_separator(a: dict, b: dict, page_blocks: list[dict]) -> bool:
    ab = a.get("bbox", [0, 0, 0, 0])
    bb = b.get("bbox", [0, 0, 0, 0])
    a_page = a.get("page")

    a_y1, a_y2 = ab[1], ab[3]
    b_y1, b_y2 = bb[1], bb[3]
    a_x1, a_x2 = ab[0], ab[2]
    b_x1, b_x2 = bb[0], bb[2]

    v_overlap = max(0.0, min(a_y2, b_y2) - max(a_y1, b_y1))
    h_gap = max(0.0, b_x1 - a_x2, a_x1 - b_x2)
    h_overlap = max(0.0, min(a_x2, b_x2) - max(a_x1, b_x1))
    v_gap = max(0.0, b_y1 - a_y2, a_y1 - b_y2)

    if v_overlap > 0 and h_gap > 0:
        # Side-by-side: check vertical strip between them
        gap_rect = [min(a_x2, b_x2), max(a_y1, b_y1), max(a_x1, b_x1), min(a_y2, b_y2)]
    elif h_overlap > 0 and v_gap > 0:
        # Stacked: check horizontal strip between them
        gap_rect = [max(a_x1, b_x1), min(a_y2, b_y2), min(a_x2, b_x2), max(a_y1, b_y1)]
    else:
        # Diagonal: use bounding rect of both, subtract asset areas
        gap_rect = [min(a_x1, b_x1), min(a_y1, b_y1), max(a_x2, b_x2), max(a_y2, b_y2)]

    for block in page_blocks:
        if block.get("page") != a_page:
            continue
        role = block.get("role", "")
        if role not in ("body_paragraph", "section_heading", "subsection_heading",
                        "backmatter_heading", "backmatter_body"):
            continue
        txt = str(block.get("text", "") or "").strip()
        if not txt or len(txt) < 10:
            continue
        cb = block.get("bbox", [0, 0, 0, 0])
        block_area = max(1.0, (cb[2] - cb[0]) * (cb[3] - cb[1]))
        if _rect_intersection_area(gap_rect, cb) / block_area >= 0.3:
            return True
    return False
```

### 3.5 Scoring

```python
def _score_legend_to_group(
    legend: dict, group: dict, *,
    caption_score: dict, page_width: float = 1200,
    anchor_supported: bool = False, caption_text_supported: bool = False,
    family_supported: bool = False, zone_supported: bool = False,
) -> dict:
    gt = group.get("group_type", "")

    if gt == "distance_cluster":
        num_assets = len(group.get("media_blocks", []))
        if group.get("safe_auto_match") and num_assets >= 2:
            return {"score": 0.85, "decision": "matched",
                    "evidence": ["same_page", "distance_clustered", "safe_auto_match"]}

        cluster_bbox = group.get("cluster_bbox", [0, 0, 0, 0])
        match_score = score_figure_match(
            legend,
            {"bbox": cluster_bbox, "page": group.get("page", 0)},
            caption_score=caption_score,
            anchor_supported=anchor_supported,
            caption_text_supported=caption_text_supported,
            family_supported=family_supported,
            zone_supported=zone_supported,
        )
        if num_assets >= 2 and match_score.get("score", 0) > 0:
            match_score = dict(match_score)
            match_score["score"] = min(1.0, match_score["score"] + 0.15)
            match_score.setdefault("evidence", []).append("multi_asset_coherence_bonus")
            if match_score["score"] >= 0.5 and match_score.get("decision") in ("candidate", "ambiguous"):
                match_score["decision"] = "matched"
        return match_score

    if gt == "single_asset":
        asset = group["media_blocks"][0]
        return score_figure_match(
            legend, asset,
            caption_score=caption_score,
            anchor_supported=anchor_supported,
            caption_text_supported=caption_text_supported,
            family_supported=family_supported,
            zone_supported=zone_supported,
        )

    # Keep existing handling for page_assets and same_row groups
    # (will be removed when those group types are eliminated in a follow-up)
    ...
```

### 3.6 Group-aware sequential fallback

In `build_figure_inventory`, after per-page matching:

```python
# Track used groups across the entire paper
used_group_ids: set[str] = set()
# ... (existing per-page matching loop marks used_group_ids) ...

# Build unmatched candidate groups for sequential fallback
unmatched_groups = [
    g for g in candidate_groups
    if g["group_id"] not in used_group_ids
    and not any(
        (g["page"], bid) in used_asset_page_ids
        for bid in g["asset_block_ids"]
    )
]
unmatched_groups.sort(key=lambda g: (g["page"], g["cluster_bbox"][1] if g.get("cluster_bbox") else 0))

# Sequential fallback: try group-aware first
for legend in unmatched_legends:
    lg_page = legend.get("page")
    # Find best unmatched group (prefer same-page cluster, then adjacent page cluster)
    candidates = [g for g in unmatched_groups
                  if g["page"] in (lg_page - 1, lg_page, lg_page + 1)
                  and g["group_id"] not in used_group_ids]
    if not candidates:
        continue  # fall through to existing single-asset fallback
    best = candidates[0]  # nearest page, then reading order
    # Claim all assets in the group
    for bid in best["asset_block_ids"]:
        for asset in assets:
            if str(asset.get("block_id", "")) == str(bid):
                matched_assets.append(asset)
                used_asset_page_ids.add((best["page"], bid))
    used_group_ids.add(best["group_id"])
    # Create figure entry with all matched assets
    ...

# Existing single-asset sequential fallback for any remaining unmatched legends
# (unchanged, as last resort)
```

---

## 4. Edge-case matrix

| # | Scenario | Detection | Handling | Fallback |
|---|----------|-----------|----------|----------|
| 1 | One page, 2+ separate figures | n_legends >= 2 | Caption bands partition BEFORE clustering | single_asset per band, score_figure_match |
| 2 | Cross-page figure | n_legends == 0 on page | Orphan cluster → group-aware sequential fallback | Old single-asset fallback |
| 3 | Dense old-journal layout | Text separator | Don't merge across | Distance threshold + no separator → allow |
| 4 | Irregular layout (1 tall + 3 small) | y_overlap >= 50%, x_gap <= 25% pw, n_legends <= 1 | Force merge | Over-merge prevented by caption bands |
| 5 | Embedded caption in figure | Caption is not an asset | Ignored by clustering | N/A |
| 6 | Figure + table on same page | Type filter splits | Cluster separately | Position-only fallback |
| 7 | Multi-col figures same y-band | n_legends >= 2 | Caption bands prevent cross-band union | single_asset per band |
| 8 | Orphan single-panel figure | Cluster size 1 | single_asset → score_figure_match | N/A |
| 9 | Text-separated figures | Text separator exists | Don't merge across | No separator → allow distance merge |
| 10 | Very large multi-panel | Many assets, single legend | Cluster merges all within thresholds | Group-aware sequential fallback |
| 11 | Single legend + multiple unrelated clusters | n_legends==1, n_clusters>1 | Highest-scoring cluster wins, rest unmatched | Sequential group fallback |

---

## 5. Files to change

| File | Action |
|------|--------|
| `paperforge/worker/ocr_figures.py` | Add `_filter_figure_assets`; replace `_build_candidate_figure_groups_from_assets`; add `_cluster_page_assets`, `_has_text_separator`; delete `_grow_region_from_seed`, `_validate_grown_region`, `_asset_gap_left`, `_asset_gap_above`; modify `_score_legend_to_group`; add group-aware sequential fallback; update `build_figure_inventory` call site |
| `tests/test_ocr_figures.py` | Unit tests: 2x2 cluster, text separator, multi-caption bands, irregular layout, scoring |
| `tests/test_ocr_real_paper_regressions.py` | Production replay: SAN9AYVR Fig 23, 2GN9LMCW Fig 4, DWQQK2YB Fig 2, 3FDT9652 |

---

## 6. What to keep vs delete

| Code | Action |
|------|--------|
| `_media_clusters` | KEEP (used by other paths) |
| `_candidate_group_entry` | KEEP (unchanged) |
| `_cluster_bbox` | KEEP (unchanged) |
| `_expand_matched_assets_locally` | KEEP (unchanged, same-page only) |
| `_partition_assets_by_caption_bands` | KEEP and REUSE for multi-legend pages |
| `_grow_region_from_seed` | DELETE |
| `_validate_grown_region` | DELETE |
| `_asset_gap_left`, `_asset_gap_above` | DELETE |
| Existing sequential fallback (single-asset) | KEEP as last resort |

---

## 7. Acceptance criteria

1. SAN9AYVR Figure 23: expected panel block_ids all in matched_assets.
2. 2GN9LMCW Figure 4: 6 assets merged.
3. DWQQK2YB Figure 2: page 38, 19 assets (no regression).
4. 3FDT9652: multi-col figures NOT merged.
5. 2GN9LMCW Figures 1-3: single-panel independent (cluster size 1).
6. Single legend + multiple figures (K7R8PEKW): best cluster wins, group-aware fallback consumes rest.
7. No page-swallow regression.
