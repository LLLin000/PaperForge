# Global Distance Clustering Figure Merge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task. Steps use checkbox syntax.

**Goal:** Replace greedy region-growing figure merge with global pairwise distance clustering + caption band partition + group-aware fallback.

**Architecture:** Three new functions (`_filter_figure_assets`, `_cluster_page_assets`, `_has_text_separator`) replace `_grow_region_from_seed` + `_validate_grown_region` + gap helpers. `_build_candidate_figure_groups_from_assets` rewritten to produce one group per asset. `_score_legend_to_group` gets `distance_cluster` branch. Sequential fallback becomes group-aware.

**Tech Stack:** Python 3.12+ (same as paperforge), union-find (stdlib only), no new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-21-global-distance-clustering-figure-merge.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `paperforge/worker/ocr_figures.py` | All figure inventory logic: asset filtering, clustering, scoring, fallback |
| `tests/test_ocr_figures.py` | Unit tests for clustering, text separator, scoring |
| `tests/test_ocr_real_paper_regressions.py` | Production replay tests for regression check |

### Functions in scope

| Function | Action |
|----------|--------|
| `_build_candidate_figure_groups_from_assets` | REWRITE: replace body with clustering |
| `_grow_region_from_seed` | DELETE |
| `_validate_grown_region` | DELETE |
| `_asset_gap_left` | DELETE |
| `_asset_gap_above` | DELETE |
| `_media_clusters` | KEEP (used elsewhere, don't touch) |
| `_candidate_group_entry` | KEEP |
| `_cluster_bbox` | KEEP |
| `_expand_matched_assets_locally` | KEEP (same-page only, legend-required) |
| `_partition_assets_by_caption_bands` | KEEP and REUSE |
| `_score_legend_to_group` | MODIFY: add distance_cluster branch |
| NEW `_filter_figure_assets` | ADD: extract from current inline filter |
| NEW `_cluster_page_assets` | ADD: main clustering logic |
| NEW `_has_text_separator` | ADD: text-block-in-gap detection |
| NEW `_rect_intersection_area` | ADD: helper for text separator |

---

### Task 1: Add `_rect_intersection_area` and `_has_text_separator`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — add two new functions after `_asset_gap_below`

- [ ] **Step 1: Add `_rect_intersection_area` helper**

Add after `_asset_gap_below` (line ~358):

```python
def _rect_intersection_area(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)
```

- [ ] **Step 2: Add `_has_text_separator`**

Add after `_rect_intersection_area`:

```python
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
        gap_rect = [min(a_x2, b_x2), max(a_y1, b_y1), max(a_x1, b_x1), min(a_y2, b_y2)]
    elif h_overlap > 0 and v_gap > 0:
        gap_rect = [max(a_x1, b_x1), min(a_y2, b_y2), min(a_x2, b_x2), max(a_y1, b_y1)]
    else:
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

- [ ] **Step 3: Write unit tests for both functions**

Add to `tests/test_ocr_figures.py`:

```python
def test_rect_intersection_area():
    from paperforge.worker.ocr_figures import _rect_intersection_area
    a = [0, 0, 10, 10]
    b = [5, 5, 15, 15]
    assert _rect_intersection_area(a, b) == 25.0
    assert _rect_intersection_area(a, [20, 20, 30, 30]) == 0.0

def test_has_text_separator_detects_body_between_stacked_assets():
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 50], "page": 1}
    b = {"bbox": [0, 150, 100, 200], "page": 1}
    body = {"bbox": [10, 70, 90, 130], "page": 1, "role": "body_paragraph", "text": "some body text here"}
    assert _has_text_separator(a, b, [body]) is True

def test_has_text_separator_no_block_returns_false():
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 50], "page": 1}
    b = {"bbox": [0, 150, 100, 200], "page": 1}
    assert _has_text_separator(a, b, []) is False

def test_has_text_separator_side_by_side_body_between():
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 200], "page": 1}
    b = {"bbox": [300, 0, 400, 200], "page": 1}
    body = {"bbox": [130, 50, 270, 150], "page": 1, "role": "body_paragraph", "text": "column text separator"}
    assert _has_text_separator(a, b, [body]) is True

def test_has_text_separator_short_text_ignored():
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 50], "page": 1}
    b = {"bbox": [0, 150, 100, 200], "page": 1}
    short = {"bbox": [10, 70, 90, 130], "page": 1, "role": "body_paragraph", "text": "short"}
    assert _has_text_separator(a, b, [short]) is False

def test_has_text_separator_diagonal_no_false_positive():
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 100], "page": 1}
    b = {"bbox": [300, 300, 400, 400], "page": 1}
    assert _has_text_separator(a, b, []) is False
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_ocr_figures.py::test_rect_intersection_area tests/test_ocr_figures.py::test_has_text_separator_detects_body_between_stacked_assets tests/test_ocr_figures.py::test_has_text_separator_no_block_returns_false tests/test_ocr_figures.py::test_has_text_separator_side_by_side_body_between tests/test_ocr_figures.py::test_has_text_separator_short_text_ignored tests/test_ocr_figures.py::test_has_text_separator_diagonal_no_false_positive -v
```
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "feat: add _has_text_separator and _rect_intersection_area for distance clustering"
```

---

### Task 2: Add `_filter_figure_assets` helper

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — add new function

- [ ] **Step 1: Add `_filter_figure_assets`**

Add after `_media_clusters` (after line ~458):

```python
def _filter_figure_assets(assets: list[dict]) -> list[dict]:
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

- [ ] **Step 2: Write unit test**

```python
def test_filter_figure_assets():
    from paperforge.worker.ocr_figures import _filter_figure_assets
    assets = [
        {"block_id": "fig", "role": "figure_asset", "raw_label": "image"},
        {"block_id": "chart", "role": "media_asset", "raw_label": "chart"},
        {"block_id": "empty_label", "role": "media_asset", "raw_label": ""},
        {"block_id": "table_img", "role": "media_asset", "raw_label": "table", "text": "<img src='x.png'>"},
        {"block_id": "table_plain", "role": "media_asset", "raw_label": "table", "text": "plain table"},
        {"block_id": "noise", "role": "noise", "raw_label": "image"},
        {"block_id": "nonbody", "role": "media_asset", "raw_label": "image", "_non_body_media": True},
    ]
    result = _filter_figure_assets(assets)
    assert [a["block_id"] for a in result] == ["fig", "chart", "empty_label", "table_img"]
```

- [ ] **Step 3: Run test**

```bash
pytest tests/test_ocr_figures.py::test_filter_figure_assets -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "feat: add _filter_figure_assets helper for backward-compatible asset filtering"
```

---

### Task 3: Add `_cluster_page_assets`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — add new function

- [ ] **Step 1: Add `_cluster_page_assets`**

Add after `_has_text_separator`:

```python
def _cluster_page_assets(
    page_assets: list[dict],
    all_blocks: list[dict],
    n_legends: int,
    page_width: float,
    page_height: float,
) -> list[list[dict]]:
    if not page_assets:
        return []
    if len(page_assets) == 1:
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

- [ ] **Step 2: Write unit tests**

```python
def test_cluster_page_assets_2x2_grid():
    assets = [
        {"bbox": [0, 0, 100, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [120, 0, 220, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [0, 120, 100, 220], "page": 1, "role": "figure_asset"},
        {"bbox": [120, 120, 220, 220], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 1, 1000, 1000)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4

def test_cluster_page_assets_wide_separation_no_irregular():
    assets = [
        {"bbox": [0, 0, 100, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [500, 0, 600, 100], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 1, 1000, 1000)
    # gap=400 > 250 (25% of 1000), even with y-overlap
    assert len(clusters) == 2

def test_cluster_page_assets_text_separator_splits():
    assets = [
        {"bbox": [0, 0, 100, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [0, 200, 100, 300], "page": 1, "role": "figure_asset"},
    ]
    body = {"bbox": [10, 120, 90, 180], "page": 1, "role": "body_paragraph", "text": "some body text here between figures"}
    clusters = _cluster_page_assets(assets, [body], 1, 1000, 1000)
    assert len(clusters) == 2

def test_cluster_page_assets_irregular_merge():
    assets = [
        {"bbox": [0, 0, 100, 300], "page": 1, "role": "figure_asset"},
        {"bbox": [200, 0, 300, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [200, 120, 300, 220], "page": 1, "role": "figure_asset"},
        {"bbox": [200, 240, 300, 340], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 1, 1000, 1000)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4

def test_cluster_page_assets_no_irregular_when_multi_legend():
    assets = [
        {"bbox": [0, 0, 100, 300], "page": 1, "role": "figure_asset"},
        {"bbox": [300, 0, 400, 100], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 2, 1000, 1000)
    assert len(clusters) == 2
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_ocr_figures.py::test_cluster_page_assets_2x2_grid tests/test_ocr_figures.py::test_cluster_page_assets_wide_separation_no_irregular tests/test_ocr_figures.py::test_cluster_page_assets_text_separator_splits tests/test_ocr_figures.py::test_cluster_page_assets_irregular_merge tests/test_ocr_figures.py::test_cluster_page_assets_no_irregular_when_multi_legend -v
```
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "feat: add _cluster_page_assets with distance-based union-find clustering"
```

---

### Task 4: Rewrite `_build_candidate_figure_groups_from_assets`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — replace entire function body

- [ ] **Step 1: Replace function body**

Replace the current `_build_candidate_figure_groups_from_assets` (starts at line ~487) with:

```python
def _build_candidate_figure_groups_from_assets(
    assets: list[dict],
    all_blocks: list[dict],
    legends: list[dict],
    page_width: float = 1200,
) -> list[dict]:
    media = _filter_figure_assets(assets)
    groups: list[dict] = []
    next_id = 1

    def _estimate_page_height(page_blocks: list[dict]) -> float:
        explicit = [float(b["page_height"]) for b in page_blocks if b.get("page_height")]
        if explicit:
            return max(explicit)
        bottoms = [
            float((b.get("bbox") or [0, 0, 0, 0])[3])
            for b in page_blocks if len(b.get("bbox") or []) >= 4
        ]
        return max(bottoms, default=1600.0)

    by_page: dict[int, list[dict]] = {}
    for block in media:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_media in by_page.items():
        page_blocks = [b for b in all_blocks if int(b.get("page", 0) or 0) == page]
        page_height = _estimate_page_height(page_blocks)

        page_legends = [l for l in legends if l.get("page") == page]
        n_legends = len(page_legends)

        # Multi-legend: partition by caption bands first
        if n_legends >= 2:
            band_map = _partition_assets_by_caption_bands(page_legends, page_media, page_height)
            partitions: list[tuple[str | None, list[dict]]] = [
                (band_id, list(assets)) for band_id, assets in band_map.items() if assets
            ]
            assigned_ids = {id(a) for _, p in partitions for a in p}
            free = [a for a in page_media if id(a) not in assigned_ids]
            if free:
                partitions.append((None, free))
        else:
            partitions = [(None, list(page_media))]

        # Cluster each partition
        page_groups: list[dict] = []
        for band_id, partition in partitions:
            if not partition:
                continue
            clusters = _cluster_page_assets(partition, page_blocks, n_legends, page_width, page_height)
            for cluster in clusters:
                gt = "distance_cluster" if len(cluster) >= 2 else "single_asset"
                entry = _candidate_group_entry(
                    f"group_{next_id:04d}", page, cluster, gt,
                    ["same_page", "distance_clustered" if gt == "distance_cluster" else "single_asset"],
                )
                entry["caption_band_id"] = band_id
                entry["page_legend_count"] = n_legends
                entry["safe_auto_match"] = False
                page_groups.append(entry)
                next_id += 1

        page_group_count = len(page_groups)
        page_distance_cluster_count = sum(1 for g in page_groups if g["group_type"] == "distance_cluster")
        for g in page_groups:
            g["page_group_count"] = page_group_count
            g["page_distance_cluster_count"] = page_distance_cluster_count
            g["safe_auto_match"] = (
                n_legends == 1
                and page_group_count == 1
                and g["group_type"] == "distance_cluster"
                and len(g.get("media_blocks", [])) >= 2
            )

        groups.extend(page_groups)

    return groups
```

- [ ] **Step 2: Update call site in `build_figure_inventory`**

Find the call (around line ~1790):

```python
candidate_groups = _build_candidate_figure_groups_from_assets(assets, page_width=page_width)
```

Replace with:

```python
candidate_groups = _build_candidate_figure_groups_from_assets(
    assets, structured_blocks, ordered_legends, page_width=page_width,
)
```

- [ ] **Step 3: Run existing figure tests to check for regressions**

```bash
pytest tests/test_ocr_figures.py -v --tb=short
```
Expected: existing tests pass (new tests from Tasks 1-3 also pass).

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py
git commit -m "refactor: replace greedy region-growing with distance clustering in _build_candidate_figure_groups_from_assets"
```

---

### Task 5: Modify `_score_legend_to_group`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — add distance_cluster branch

- [ ] **Step 1: Add distance_cluster branch to `_score_legend_to_group`**

Find `_score_legend_to_group` (line ~608). Add this BEFORE the existing `if gt == "page_assets":` check:

```python
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
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_ocr_figures.py -v --tb=short
```
Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr_figures.py
git commit -m "feat: add distance_cluster scoring branch with safe_auto_match"
```

---

### Task 6: Add group-aware sequential fallback

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — modify `build_figure_inventory` sequential fallback section

Insert point: AFTER preproof legend-bundling fallback, BEFORE the existing "Sequential fallback: match unmatched captions to remaining assets" block.

- [ ] **Step 1: Add `used_group_ids` tracking**

Near the top of `build_figure_inventory`, after initialization:

```python
used_group_ids: set[str] = set()
```

In the per-page matching loop (same-page match success path), after a group is matched:

```python
if best_group:
    used_group_ids.add(str(best_group.get("group_id", "")))
```

Add in both the close-tie branch and the normal branch.

- [ ] **Step 2: Add group-aware sequential fallback**

In `build_figure_inventory`, AFTER the preproof legend-bundling block and BEFORE the existing sequential fallback:

```python
    # === Group-aware sequential fallback ===
    # Consume unmatched distance_clusters that no same-page legend claimed.
    # Inserted AFTER preproof fallback, BEFORE old single-asset sequential fallback.
    local_asset_by_page_id: dict[tuple[int, str], dict] = {}
    for block in _filter_figure_assets(assets):
        local_asset_by_page_id[(int(block.get("page", 0) or 0), str(block.get("block_id", "")))] = block

    unmatched_groups = [
        g for g in candidate_groups
        if str(g.get("group_id", "")) not in used_group_ids
        and g.get("group_type") == "distance_cluster"
        and not any(
            (int(g.get("page", 0) or 0), str(bid)) in used_asset_page_ids
            for bid in g.get("asset_block_ids", [])
            if bid is not None
        )
    ]
    unmatched_groups.sort(key=lambda g: (
        int(g.get("page", 0) or 0),
        (g.get("cluster_bbox") or [0, 0, 0, 0])[1],
    ))

    for legend in list(unmatched_legends):
        lg_page = int(legend.get("page", 0) or 0)
        cap_text = str(legend.get("text", "") or "")
        fn = _extract_figure_number(cap_text)
        if fn is None:
            continue
        cap_ns = _extract_figure_namespace(cap_text)
        fig_id = _format_figure_id(cap_ns, fn)

        # Collect candidate groups: prefer same-page, then next-page, then previous-page
        same_page = [g for g in unmatched_groups if g["page"] == lg_page]
        next_page = [g for g in unmatched_groups if g["page"] == lg_page + 1]
        prev_page = [g for g in unmatched_groups if g["page"] == lg_page - 1]

        best_group = None
        if same_page:
            # Same-page group must re-pass scoring to avoid forcing unrelated clusters
            for sg in same_page:
                sg_score = _score_legend_to_group(
                    legend, sg,
                    caption_score=score_figure_caption(
                        legend, nearby_media=True, caption_style_match=False,
                        body_prose_likelihood=False,
                    ),
                    page_width=page_width,
                )
                if sg_score.get("decision") == "matched" and sg_score.get("score", 0.0) >= 0.5:
                    best_group = sg
                    break
        if best_group is None and next_page:
            best_group = next_page[0]
        if best_group is None and prev_page:
            first_bid = str(prev_page[0]["asset_block_ids"][0]) if prev_page[0]["asset_block_ids"] else ""
            first_asset = local_asset_by_page_id.get((prev_page[0]["page"], first_bid))
            if first_asset and _allow_previous_page_sequential_match(legend, first_asset):
                best_group = prev_page[0]

        if best_group is None:
            continue

        group_page = int(best_group.get("page", 0) or 0)
        caption_score = score_figure_caption(
            legend, nearby_media=True, caption_style_match=False,
            body_prose_likelihood=False,
        )

        group_assets = []
        for bid in best_group.get("asset_block_ids", []):
            if bid is None:
                continue
            asset = local_asset_by_page_id.get((group_page, str(bid)))
            if asset:
                group_assets.append(asset)
                used_asset_page_ids.add((group_page, str(bid)))

        if not group_assets:
            continue

        matched_figures.append({
            "figure_id": fig_id,
            "figure_namespace": cap_ns,
            "legend_block_id": legend.get("block_id", ""),
            "page": group_page,
            "text": cap_text,
            "figure_number": fn,
            "matched_assets": [
                {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])}
                for a in group_assets
            ],
            "asset_block_ids": [str(a.get("block_id", "")) for a in group_assets],
            "bridge_block_ids": [],
            "group_type": best_group.get("group_type", ""),
            "group_evidence": best_group.get("group_evidence", []) + ["group_sequential_fallback"],
            "cluster_bbox": best_group.get("cluster_bbox", [0, 0, 0, 0]),
            "confidence": 0.45,
            "match_score": {
                "score": 0.45,
                "decision": "matched",
                "evidence": ["group_sequential_fallback"],
            },
            "flags": ["group_sequential_match"],
            "caption_score": caption_score,
        })

        used_group_ids.add(str(best_group.get("group_id", "")))
        unmatched_legends.remove(legend)
        ambiguous_figures[:] = [
            af for af in ambiguous_figures
            if str(af.get("legend_block_id", "")) != str(legend.get("block_id", ""))
        ]

    # === End group-aware fallback ===
```

---

### Task 7: Delete obsolete functions

**Files:**
- Modify: `paperforge/worker/ocr_figures.py` — remove `_grow_region_from_seed`, `_validate_grown_region`, `_asset_gap_left`, `_asset_gap_above`

- [ ] **Step 1: Delete the obsolete functions**

Remove:
- `_grow_region_from_seed` (line ~361-389)
- `_validate_grown_region` (line ~392-413)
- `_asset_gap_left` (line ~new, added in previous fix)
- `_asset_gap_above` (line ~new, added in previous fix)

- [ ] **Step 2: Verify `_media_clusters` still exists and is unchanged**

`_media_clusters` at line ~416 should still be there. If it was accidentally removed during Task 4 edits, restore it.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_ocr_figures.py -v --tb=short
```
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py
git commit -m "refactor: remove obsolete _grow_region_from_seed, _validate_grown_region, gap helpers"
```

---

### Task 8: Add production replay regression tests

**Files:**
- Modify: `tests/test_ocr_real_paper_regressions.py` — add tests for SAN9AYVR, 2GN9LMCW, DWQQK2YB, 3FDT9652

- [ ] **Step 1: Add SAN9AYVR Figure 23 merge test**

```python
def test_san9ayvr_figure_23_all_panels_merged(tmp_path: Path) -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory
    result = replay_production_pipeline("SAN9AYVR", tmp_path)
    inventory = result["figure_inventory"]

    fig23 = [f for f in inventory["matched_figures"] if f.get("figure_number") == 23]
    assert len(fig23) == 1, "Figure 23 should be a single matched figure"
    assert len(fig23[0].get("matched_assets", [])) >= 8, "Figure 23 should have 8+ sub-panels"
    assert fig23[0].get("group_type") == "distance_cluster", (
        f"Figure 23 should be distance_clustered, got {fig23[0].get('group_type')}"
    )
```

- [ ] **Step 2: Add 2GN9LMCW Figure 4 merge test**

```python
def test_2gn9lmcw_figure_4_six_assets_merged(tmp_path: Path) -> None:
    result = replay_production_pipeline("2GN9LMCW", tmp_path)
    inventory = result["figure_inventory"]

    fig4 = [f for f in inventory["matched_figures"] if f.get("figure_number") == 4]
    assert len(fig4) == 1, "Figure 4 should be matched"
    assert len(fig4[0].get("matched_assets", [])) >= 6, "Figure 4 should have 6+ assets"
    assert fig4[0].get("group_type") == "distance_cluster"
```

- [ ] **Step 3: Add DWQQK2YB Figure 2 regression test**

```python
def test_dwqqk2yb_figure_2_on_correct_page(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    inventory = result["figure_inventory"]

    fig2 = [f for f in inventory["matched_figures"] if f.get("figure_number") == 2]
    assert len(fig2) == 1, "Figure 2 should be matched"
    assert fig2[0]["page"] == 38, f"Figure 2 should be on page 38, got page {fig2[0]['page']}"
    assert len(fig2[0].get("matched_assets", [])) >= 18, (
        f"Figure 2 should have 18+ assets, got {len(fig2[0].get('matched_assets', []))}"
    )
```

- [ ] **Step 4: Add 3FDT9652 multi-column regression test**

```python
def test_3fdt9652_multi_column_figures_not_merged(tmp_path: Path) -> None:
    result = replay_production_pipeline("3FDT9652", tmp_path)
    inventory = result["figure_inventory"]
    unmatched = inventory.get("unmatched_legends", [])

    # 3FDT9652 page 3 should have Figure 2 and Figure 3 as separate matched figures
    fig2 = [f for f in inventory["matched_figures"] if f.get("figure_number") == 2]
    fig3 = [f for f in inventory["matched_figures"] if f.get("figure_number") == 3]

    assert len(fig2) == 1, "Figure 2 should be matched"
    assert len(fig3) == 1, "Figure 3 should be matched"

    # They should NOT share any asset block
    fig2_assets = {str(a.get("block_id", "")) for a in fig2[0].get("matched_assets", [])}
    fig3_assets = {str(a.get("block_id", "")) for a in fig3[0].get("matched_assets", [])}
    assert fig2_assets.isdisjoint(fig3_assets), (
        f"Fig 2 and Fig 3 share assets: {fig2_assets & fig3_assets}"
    )

    # Each should have different legend_block_id
    assert fig2[0].get("legend_block_id") != fig3[0].get("legend_block_id"), (
        "Fig 2 and Fig 3 share the same legend_block_id"
    )
```

- [ ] **Step 5: Run production replay tests**

```bash
pytest tests/test_ocr_real_paper_regressions.py -v --tb=short -k "figure|merge|cluster"
```
Expected: all PASS (or skip if fixture data unavailable).

- [ ] **Step 6: Commit**

```bash
git add tests/test_ocr_real_paper_regressions.py
git commit -m "test: add production replay tests for distance clustering merge"
```

---

### Task 9: Full regression run

**Files:** None (run test suite)

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py -v --tb=short
```
Expected: all PASS.

- [ ] **Step 2: Run full paperforge test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: no regressions introduced.

- [ ] **Step 3: Final commit (if any fixes needed)**

```bash
git add -A
git commit -m "chore: final fixes after full regression run"
```

---

## Summary of all commits

| Task | Commit message | Files |
|------|---------------|-------|
| 1 | `feat: add _has_text_separator and _rect_intersection_area` | `ocr_figures.py`, `test_ocr_figures.py` |
| 2 | `feat: add _filter_figure_assets helper` | `ocr_figures.py`, `test_ocr_figures.py` |
| 3 | `feat: add _cluster_page_assets with union-find` | `ocr_figures.py`, `test_ocr_figures.py` |
| 4 | `refactor: replace region-growing with distance clustering` | `ocr_figures.py` |
| 5 | `feat: add distance_cluster scoring branch` | `ocr_figures.py` |
| 6 | `feat: add group-aware sequential fallback` | `ocr_figures.py` |
| 7 | `refactor: remove obsolete grow/validate helpers` | `ocr_figures.py` |
| 8 | `test: add production replay regression tests` | `test_ocr_real_paper_regressions.py` |
| 9 | `chore: final regression fixes` | Various |

## Post-implementation verification

After all tasks are done, verify against acceptance criteria:

1. ✅ SAN9AYVR Figure 23: all expected sub-panels matched (production test)
2. ✅ 2GN9LMCW Figure 4: 6+ assets merged (production test)
3. ✅ DWQQK2YB Figure 2: page 38, 10+ assets (production test)
4. ✅ 3FDT9652: no cross-figure asset overlap (production test)
5. ✅ Unit tests: 2x2 cluster, text separator, irregular merge, multi-legend partition
6. ✅ No page-swallow regression (existing test suite)
