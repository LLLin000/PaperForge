# Weak Cluster Rejection for Column Detection

**Date:** 2026-06-22
**Status:** draft
**Scope:** `paperforge/worker/ocr_document.py` — `_cluster_page_columns()`, `_classify_page_layout()`

---

## Problem

A single-column page with a short left-offset body line (e.g. "Informed Consent Statement: Not applicable.", bbox `[328,832,704,854]`, x_center=516) creates a false second x-center cluster. The gap between its x_center (516) and the main body x_center (~724) exceeds the 15% page-width threshold, causing the page to be misclassified as `two_column`. Subsequent column-sort in `_order_tail_blocks()` breaks reading order by emitting all left-column blocks before all right-column blocks.

**Affected paper:** `2E4EPHN2` (Mendes et al. 2022, Antioxidants), page 12.

**Root cause:** `_cluster_page_columns()` uses only x-center positions for gap-based clustering. A single short line with offset x_center can split into its own cluster, creating a false `column_count == 2`.

---

## Design

### Core principle

Before accepting a cluster as a real column, require evidence: at least 2 blocks, or sufficient vertical coverage, or sufficient text mass. A cluster with count=1, minimal y_coverage, and few words is a "weak isolated cluster" and should be ignored.

### Implementation contract

#### 1. New function: `_cluster_page_column_groups(page_blocks, page_width) -> list[dict]`

Replace the x-center-only clustering with a function that returns cluster metadata.

**Return value:** List of cluster dicts, sorted by `center` ascending. Each dict:

```
center: float          — mean x_center of blocks in this cluster
count: int             — number of blocks
x_min: float           — minimum x_center
x_max: float           — maximum x_center
y_min: float           — minimum y_top of blocks' bboxes
y_max: float           — maximum y_bottom of blocks' bboxes
y_coverage: float      — y_max - y_min (vertical span in px)
word_count: int        — total word count across all blocks
width_median: float    — median block width
block_ids: list[str|int] — block identifiers
blocks: list[dict]     — the full block dicts
```

**Algorithm:** Same gap-based clustering as `_cluster_page_columns()` (gap > `page_width * 0.15` splits into new cluster), but tracks full block objects instead of just x_centers.

**Edge cases:**
- No blocks or all blocks filtered (width <= 50px, no bbox): return single cluster dict with `center = page_width / 2`, count=0, empty values.
- Single block: return single cluster dict.

#### 2. Compatibility wrapper: `_cluster_page_columns(page_blocks, page_width) -> list[float]`

```python
return [c["center"] for c in _cluster_page_column_groups(page_blocks, page_width)]
```

All existing callers continue to work unchanged.

#### 3. New function: `_is_weak_isolated_column_cluster(cluster: dict, page_height: float) -> bool`

Determines if a cluster lacks sufficient evidence to be considered a real column.

```python
def _is_weak_isolated_column_cluster(cluster: dict, page_height: float) -> bool:
    # Not weak if ANY evidence of being a real column
    if cluster["count"] >= 2:
        return False
    if cluster["y_coverage"] >= page_height * 0.10:
        return False
    if cluster["word_count"] >= 25:
        return False
    return True  # All three checks fail
```

**Rationale for thresholds:**
- `count >= 2`: A real column in a two-column paper will have multiple blocks per page.
- `y_coverage >= page_height * 0.10`: ~160px on a 1600px page. A single large paragraph block covers this easily.
- `word_count >= 25`: ~3 lines of text. Short backmatter lines (e.g. "Informed Consent Statement: Not applicable.") are ~5 words.

A cluster is weak only when ALL three conditions fail.

**For the bug case:** count=1, y_coverage=22px, word_count≈5 → weak → ignored.

#### 4. Modified: `_classify_page_layout(page_blocks, page_width, page_height) -> PageLayoutProfile`

**New flow:**

```python
def _classify_page_layout(page_blocks, page_width, page_height):
    clusters = _cluster_page_column_groups(page_blocks, page_width)

    # Filter weak isolated clusters before computing column_count
    real_clusters = [
        c for c in clusters
        if not _is_weak_isolated_column_cluster(c, page_height)
    ]

    # All clusters are weak: low-confidence single_column
    if not real_clusters:
        return PageLayoutProfile(
            column_count=1,
            column_boundaries=[page_width / 2],
            layout_type="single_column",
            confidence=0.35,
            evidence=["eligible_body_blocks", "all_column_clusters_weak"],
        )

    evidence_extra = []
    if len(real_clusters) < len(clusters):
        evidence_extra.append("weak_isolated_column_cluster_ignored")

    centers = [c["center"] for c in real_clusters]
    column_count = len(real_clusters)

    # --- single column ---
    if column_count == 1:
        return PageLayoutProfile(
            column_count=1,
            column_boundaries=[real_clusters[0]["center"]],
            layout_type="single_column",
            confidence=0.55 if evidence_extra else 0.7,
            evidence=["eligible_body_blocks"] + evidence_extra,
        )

    # --- two real columns: role distribution via cluster membership ---
    if column_count == 2:
        col_blocks: dict[int, list[str]] = {0: [], 1: []}
        for i in (0, 1):
            for block in real_clusters[i]["blocks"]:
                col_blocks[i].append(block.get("role", ""))

        body_roles = {
            "body_paragraph", "section_heading",
            "subsection_heading", "sub_subsection_heading",
        }
        col_has_body = {}
        col_has_tail = {}
        for col_idx, roles in col_blocks.items():
            col_has_body[col_idx] = bool(set(roles) & body_roles)
            col_has_tail[col_idx] = bool(set(roles) & _TAIL_ROLES)

        one_side_body = col_has_body[0] and not col_has_tail[0]
        other_side_tail = not col_has_body[1] and col_has_tail[1]
        swapped = col_has_body[1] and not col_has_tail[1]
        swapped_tail = not col_has_body[0] and col_has_tail[0]

        if (one_side_body and other_side_tail) or (swapped and swapped_tail):
            return PageLayoutProfile(
                column_count=2,
                column_boundaries=centers,
                layout_type="mixed_tail",
                confidence=0.6,
                evidence=["eligible_body_blocks", "two_center_clusters"] + evidence_extra,
            )
        return PageLayoutProfile(
            column_count=2,
            column_boundaries=centers,
            layout_type="two_column",
            confidence=0.7,
            evidence=["eligible_body_blocks"] + evidence_extra,
        )

    # --- three or more real columns ---
    return PageLayoutProfile(
        column_count=column_count,
        column_boundaries=centers,
        layout_type="two_column",
        confidence=0.5,
        evidence=["eligible_body_blocks", "wide_dispersion"] + evidence_extra,
    )
```

**Key changes from current code:**
1. `real_clusters` filter applied BEFORE `column_count` decision — covers 2+ and 3+ cluster cases.
2. `single_column` boundary uses `real_clusters[0]["center"]` — not averaged with weak cluster centers.
3. `two_column` role distribution uses `real_clusters[i]["blocks"]` (cluster membership) — NOT `page_width / 2` midpoint.

#### 5. Evidence naming

| Evidence string | Meaning |
|-----------------|---------|
| `weak_isolated_column_cluster_ignored` | One or more weak clusters were filtered out before deciding layout |
| `all_column_clusters_weak` | ALL clusters were weak; fallback to single_column with low confidence |

---

## What is NOT changed

- `_LAYOUT_ELIGIBLE_ROLES` — unchanged
- `_is_layout_eligible_block()` — unchanged
- `_sort_blocks_by_column()` — still uses `page_width / 2` midpoint; tracked separately
- `_build_page_layout_profiles()` — unchanged
- No new backmatter heading detection
- No block-level signal guards in layout eligibility

---

## Regression analysis

| Scenario | Expected | Why safe |
|----------|----------|---------|
| True two-column body page (multi-block per column) | `two_column` | Both clusters: count >= 2 |
| True two-column reference page | `two_column` | Reference items have sufficient count |
| Mixed tail page (body + backmatter) | `mixed_tail` | Both columns have sufficient y_coverage |
| Single-column page (1 cluster) | `single_column` | Does not enter weak check |
| Single-column + 1 short offset line (this bug) | `single_column` | Weak cluster ignored |
| Single-column + 2 short offset lines (3 raw clusters) | `single_column` | 2 weak filtered, 1 real remains |
| All clusters weak (rare) | `single_column` low confidence | Fallback, does not preserve false two_column |
| One large block per true column | `two_column` | count=1 but y_coverage or word_count sufficient |

---

## Tests

### Required (4)

1. **test_short_isolated_body_line_does_not_create_two_column_layout**
   Replicates page 12: 6 full-width body blocks + 1 short offset line. Expect `single_column` + `weak_isolated_column_cluster_ignored`.

2. **test_balanced_two_column_layout_still_detected**
   2 blocks left column, 2 blocks right column. Expect `two_column`.

3. **test_single_large_block_per_column_still_two_column**
   1 large body block per column (count=1 but large y_coverage and word_count). Expect `two_column`.

4. **test_multiple_weak_offset_lines_do_not_create_wide_dispersion**
   3 raw clusters (2 weak, 1 real). Expect `single_column` + `weak_isolated_column_cluster_ignored`.

### Optional (1)

5. **test_all_clusters_weak_fallback_to_single_column**
   All clusters fail the weak check. Expect `single_column` with confidence <= 0.35 and evidence `all_column_clusters_weak`.

---

## Rollback plan

If this change introduces regressions on real two-column papers:
1. Check if the affected page's weak cluster has `y_coverage` or `word_count` just below the thresholds — the thresholds can be lowered.
2. Check if `_is_weak_isolated_column_cluster` is being too aggressive — the function can be adjusted independently of the rest of the pipeline.
3. The `_cluster_page_columns()` compatibility wrapper ensures all other callers are unaffected.
