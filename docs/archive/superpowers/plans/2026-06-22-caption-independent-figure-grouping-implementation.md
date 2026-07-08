# Caption-Independent Figure Grouping — Stage 1A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` or `executing-plans`.

**Goal:** Introduce caption-independent semantic grouping truth and prevent caption-band-local groups from entering the main ownership input stream. This is **Stage 1A** only. It does **not** implement or rewrite the full ledger / reservation / cross-page matching layer if those helpers are absent or unstable.

**Primary Spec:** `docs/superpowers/specs/2026-06-22-caption-independent-figure-grouping-design.md`

**Downstream Matching Spec Preserved:** `docs/superpowers/specs/2026-06-22-group-first-cross-page-figure-caption-matching-design.md`

---

## 1. Stage Boundary

This plan is intentionally narrower than the matching plan.

It should be read as:

```text
Stage 1A:
1. introduce semantic_groups
2. introduce band_assist_by_group_id
3. make the main candidate group input caption-independent
4. ensure any existing ledger/reservation input surface consumes semantic_groups
5. do not deeply rewrite same-page / cross-page matcher behavior here
```

It is **not**:

```text
full matcher rewrite
```

If ledger / reservation / cross-page helpers are not already present in the current code branch, this plan does not invent them. That remains the downstream matching plan.

---

## 2. Non-Negotiable Constraints

- Do not let caption-band-local groups enter `candidate_groups` / ledger truth input.
- Do not let caption count (`n_legends`) alter semantic group topology.
- Do not remove neutral separator behavior from caption/text blocks.
- Do not substantially rewrite `_score_legend_to_group()` in this plan unless a targeted failing test requires it.
- Do not rewrite `build_figure_inventory()` end-to-end.
- Do not expand this plan into full reservation / cross-page implementation work.

---

## 3. Compatibility Rule

For minimal surgery, `build_figure_inventory()` may continue to use the variable name `candidate_groups`, but its value must come from caption-independent semantic grouping.

Required interpretation:

```text
candidate_groups = semantic_groups
```

Band-local groups must not be appended to that list.

---

## 4. File Map

| File | Responsibility |
|------|---------------|
| `paperforge/worker/ocr_figures.py` | Main work: semantic grouping helper, assist helper, input rewiring |
| `paperforge/worker/ocr.py` | No expected semantic change; keep render-only same-page gate unchanged |
| `paperforge/worker/ocr_objects.py` | Verify no reader/crop regressions if group payload shape changes |
| `tests/test_ocr_figures.py` | Main test coverage |

---

## 5. Implementation Tasks

### Task 1: Freeze Semantic Group Topology Contract

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add topology comparison helper**

Add a tiny helper used by tests or test seams:

```python
def _semantic_group_topology(groups: list[dict]) -> set[frozenset[str]]:
    return {frozenset(str(bid) for bid in g.get("asset_block_ids", [])) for g in groups}
```

Hard rule:

```text
tests compare topology by asset_block_ids, not by generated group_id values
```

- [ ] **Step 2: Add contract comment near grouping helpers**

Document:

```text
semantic_groups are caption-independent
caption/text may act as neutral separators only
caption count may not change topology
```

---

### Task 2: Introduce Caption-Independent Semantic Group Builder

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add new helper**

Add:

```python
def _build_semantic_figure_groups_from_assets(
    assets: list[dict],
    all_blocks: list[dict],
    *,
    page_width: float = 1200,
) -> list[dict]:
    ...
```

Required behavior:

1. group from the full page asset set
2. do not call `_partition_assets_by_caption_bands()`
3. do not pass `n_legends` into topology-changing behavior
4. may use `_has_text_separator(...)` as a neutral barrier
5. must return stable `asset_block_ids`, `page`, `cluster_bbox`, `group_type`

- [ ] **Step 2: Define executable clustering contract**

Semantic clustering should:

1. group page assets by connected components or equivalent visual continuity logic
2. consider horizontal/vertical gap thresholds independent of caption count
3. use `_has_text_separator()` as neutral barrier
4. never create `caption_band_id`
5. never depend on ownership band identity

Pseudocode target:

```python
def _cluster_semantic_page_assets(page_assets, page_blocks, page_width, page_height):
    parent = union_find(len(page_assets))
    for each pair a, b:
        if visual_gap_too_large:
            continue
        if _has_text_separator(a, b, page_blocks):
            continue
        if same_row_or_column_continuity(a, b):
            union(a, b)
    return components
```

- [ ] **Step 3: Do not reuse caption-contaminated topology mode**

If `_cluster_page_assets(...)` is reused, it must be wrapped or refactored so semantic mode does not consult `n_legends`.

Allowed:

```python
_cluster_page_assets(..., grouping_mode="semantic")
```

Forbidden:

```python
_cluster_page_assets(..., n_legends=<live caption count>)
```

---

### Task 3: Preserve Caption-Band Logic As Assist Only

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Keep `_partition_assets_by_caption_bands()` but demote its role**

It may remain for same-page assist only.

- [ ] **Step 2: Add assist builder**

Add:

```python
def _build_caption_band_group_assist(...):
    ...
```

or equivalent inline seam.

Recommended output:

```python
band_assist_by_group_id = {
    group_id: {
        "best_caption_band_id": str | None,
        "overlap_ratio": float,
        "evidence": list[str],
    }
}
```

- [ ] **Step 3: Stage 1A restraint**

In this plan, `band_assist_by_group_id` may be attached as metadata only.
Do not substantially rewrite `_score_legend_to_group()` unless a targeted failing test requires it.

---

### Task 4: Replace Main Group Input With Semantic Groups

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Make `build_figure_inventory()` derive main group input from semantic grouping**

Minimal-surgery path:

```python
semantic_groups = _build_semantic_figure_groups_from_assets(...)
candidate_groups = semantic_groups
```

- [ ] **Step 2: Ensure band-local groups do not enter that list**

Hard rule:

```text
band-local groups may exist,
but must not be appended to candidate_groups
```

- [ ] **Step 3: If ledger/reservation helpers already exist, keep them on this input only**

If `_build_page_ledger()`, `_build_residual_ledger()`, or reservation helpers are already present in the branch, they must consume `candidate_groups == semantic_groups`.

If they are not present, do not invent them in this plan.

---

### Task 5: Add Red/Green Tests For The Old Bug And New Invariant

**Files:**
- Modify: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add semantic invariant test**

Required passing test:

```python
new_one_caption = _build_semantic_figure_groups_from_assets(...)
new_two_captions = _build_semantic_figure_groups_from_assets(...)
assert topology(new_one_caption) == topology(new_two_captions)
```

- [ ] **Step 2: Add ordinary same-page multi-figure safety test**

Required passing test:

```text
two visually separated same-page figures do not collapse into one semantic group
```

- [ ] **Step 3: Add neutral separator test**

Required passing test:

```text
caption/text barrier can keep clusters separate without pre-assigning ownership
```

- [ ] **Step 4: Add optional illustrative old-bug test**

If stable enough, add a test showing that old caption-conditioned grouping changes topology when caption count changes.

This may be:

1. an explicit failing old helper comparison, or
2. a comment-backed regression fixture documenting the prior behavior

Do not make this test brittle if the old helper is being removed during refactor.

---

## 6. Required Tests Matrix

- [ ] same visual assets + caption count changes -> same semantic topology
- [ ] topology comparison uses `asset_block_ids`, not `group_id`
- [ ] caption/text barrier may split continuity without assigning ownership
- [ ] band assist exists but does not enter ledger truth
- [ ] ordinary same-page two-figure layout still yields two semantic groups or two settleable groups
- [ ] if ledger/reservation exists, it consumes semantic groups rather than caption-conditioned groups

---

## 7. Verification Commands

```bash
python -m pytest tests/test_ocr_figures.py -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short
```

Optional after Stage 1B exists or branch already includes matching helpers:

```bash
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2HEUD5P9
```

---

## 8. Exit Criteria

This Stage 1A plan is complete only when:

1. `semantic_groups` exist as caption-independent grouping truth
2. `candidate_groups` in the main flow come from `semantic_groups`
3. `band_assist_by_group_id` exists only as assist metadata
4. caption count / caption identity changes alone do not change semantic topology
5. neutral separator behavior is preserved
6. the plan has not silently expanded into a full matcher rewrite
