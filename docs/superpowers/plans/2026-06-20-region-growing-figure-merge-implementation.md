# Region-Growing Figure Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fragile row-first figure grouping with seed-based region growth plus validation, without reintroducing page-swallow behavior.

**Architecture:** Keep the current safe `page_assets` guardrails and add a separate candidate-group growth model: seed from the earliest plausible asset, grow by local adjacency, record merge evidence, then validate the grown group before strict ownership. If validation fails, demote or split instead of forcing a match.

**Tech Stack:** Python 3.14, `paperforge.worker.ocr_figures`, pytest, existing real-paper regressions, rebuild verification on residual and unseen figure-heavy papers.

---

## File Structure

- Modify: `paperforge/worker/ocr_figures.py`
  - Owns seed selection, local adjacency growth, candidate-group evidence, and post-growth validation.
- Modify: `tests/test_ocr_figures.py`
  - Unit coverage for region growth and false-merge rejection.
- Modify: `tests/test_ocr_real_paper_regressions.py`
  - Real-paper protection against page swallow and irregular-layout regressions.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record the completed figure-merge slice and remaining ownership residuals.

---

### Task 1: Add Region-Growth Candidate Data Structures

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add a failing test for local right-neighbor growth**

Append to `tests/test_ocr_figures.py`:

```python
def test_region_growth_absorbs_adjacent_right_neighbor() -> None:
    from paperforge.worker.ocr_figures import _grow_region_from_seed

    seed = {"block_id": "a1", "bbox": [100, 100, 300, 260], "page": 5}
    others = [
        {"block_id": "a2", "bbox": [315, 105, 520, 258], "page": 5},
        {"block_id": "a3", "bbox": [700, 100, 920, 260], "page": 5},
    ]

    group = _grow_region_from_seed(seed, others, page_width=1000)

    assert group["asset_block_ids"] == ["a1", "a2"]
    assert any(step["reason"] == "adjacent_right" for step in group["growth_steps"])
```

- [ ] **Step 2: Add a failing test for stacked growth**

Append to `tests/test_ocr_figures.py`:

```python
def test_region_growth_absorbs_adjacent_below_neighbor() -> None:
    from paperforge.worker.ocr_figures import _grow_region_from_seed

    seed = {"block_id": "a1", "bbox": [100, 100, 320, 250], "page": 6}
    others = [
        {"block_id": "a2", "bbox": [98, 265, 325, 420], "page": 6},
    ]

    group = _grow_region_from_seed(seed, others, page_width=1000)

    assert group["asset_block_ids"] == ["a1", "a2"]
    assert any(step["reason"] == "adjacent_below" for step in group["growth_steps"])
```

- [ ] **Step 3: Run the red tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "region_growth_absorbs" -v`

Expected: FAIL because region-growing helpers do not exist yet.

- [ ] **Step 4: Implement seed-based growth helpers in `ocr_figures.py`**

Add helper functions:

```python
def _asset_gap_right(a: dict, b: dict) -> float:
    ab = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    return max(0.0, bb[0] - ab[2])


def _asset_gap_below(a: dict, b: dict) -> float:
    ab = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    return max(0.0, bb[1] - ab[3])


def _grow_region_from_seed(seed: dict, others: list[dict], page_width: float) -> dict:
    group = [seed]
    growth_steps: list[dict] = []
    remaining = list(others)
    changed = True
    while changed:
        changed = False
        group_bbox = _cluster_bbox([g.get("bbox", [0, 0, 0, 0]) for g in group])
        next_remaining = []
        for candidate in remaining:
            reason = None
            cb = candidate.get("bbox") or [0, 0, 0, 0]
            if cb[0] >= group_bbox[2] and _asset_gap_right({"bbox": group_bbox}, candidate) <= page_width * 0.03:
                reason = "adjacent_right"
            elif cb[1] >= group_bbox[3] and _asset_gap_below({"bbox": group_bbox}, candidate) <= page_width * 0.03:
                reason = "adjacent_below"
            if reason:
                group.append(candidate)
                growth_steps.append({"added_block_id": candidate.get("block_id", ""), "reason": reason})
                changed = True
            else:
                next_remaining.append(candidate)
        remaining = next_remaining
    return {
        "seed_asset_block_id": seed.get("block_id", ""),
        "asset_block_ids": [g.get("block_id", "") for g in group if g.get("block_id")],
        "growth_steps": growth_steps,
        "group_bbox": _cluster_bbox([g.get("bbox", [0, 0, 0, 0]) for g in group]),
    }
```

- [ ] **Step 5: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "region_growth_absorbs" -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "feat: add seed-based region growth for figure groups"
```

---

### Task 2: Add Validation And False-Merge Rejection

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add a failing test for suspicious large-gap merge rejection**

Append to `tests/test_ocr_figures.py`:

```python
def test_region_growth_validation_rejects_large_gap_without_support() -> None:
    from paperforge.worker.ocr_figures import _validate_grown_region

    group = {
        "asset_block_ids": ["a1", "a2"],
        "group_bbox": [100, 100, 800, 260],
        "growth_steps": [{"added_block_id": "a2", "reason": "adjacent_right"}],
    }
    assets = [
        {"block_id": "a1", "bbox": [100, 100, 260, 260], "page": 5},
        {"block_id": "a2", "bbox": [620, 100, 800, 260], "page": 5},
    ]

    verdict = _validate_grown_region(group, assets)
    assert verdict["validation_status"] == "split_required"
```

- [ ] **Step 2: Add a failing test for grouped-evidence demotion when another caption control zone is crossed**

Append to `tests/test_ocr_figures.py`:

```python
def test_region_growth_validation_demotes_group_when_crossing_other_caption_zone() -> None:
    from paperforge.worker.ocr_figures import _validate_grown_region

    group = {
        "asset_block_ids": ["a1", "a2"],
        "group_bbox": [100, 100, 520, 260],
        "growth_steps": [{"added_block_id": "a2", "reason": "adjacent_right"}],
    }
    assets = [
        {"block_id": "a1", "bbox": [100, 100, 300, 260], "page": 5},
        {"block_id": "a2", "bbox": [320, 100, 520, 260], "page": 5},
    ]
    other_caption_bbox = [340, 270, 520, 300]

    verdict = _validate_grown_region(group, assets, competing_caption_bboxes=[other_caption_bbox])
    assert verdict["validation_status"] == "grouped_evidence_only"
```

- [ ] **Step 3: Run the red tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "validation_rejects_large_gap or validation_demotes_group" -v`

Expected: FAIL because validation helpers do not exist yet.

- [ ] **Step 4: Implement post-growth validation helpers**

Add:

```python
def _validate_grown_region(group: dict, assets: list[dict], competing_caption_bboxes: list[list[float]] | None = None) -> dict:
    competing_caption_bboxes = competing_caption_bboxes or []
    asset_map = {str(a.get("block_id", "")): a for a in assets}
    group_assets = [asset_map[bid] for bid in group.get("asset_block_ids", []) if bid in asset_map]
    if len(group_assets) <= 1:
        return {"validation_status": "strict_match_ok", "validation_reason": "single_asset"}

    ordered = sorted(group_assets, key=lambda a: (a.get("bbox") or [0, 0, 0, 0])[0])
    max_gap = 0.0
    for left, right in zip(ordered, ordered[1:], strict=False):
        lb = left.get("bbox") or [0, 0, 0, 0]
        rb = right.get("bbox") or [0, 0, 0, 0]
        max_gap = max(max_gap, max(0.0, rb[0] - lb[2]))
    if max_gap > 250.0:
        return {"validation_status": "split_required", "validation_reason": "gap_too_large"}

    gb = group.get("group_bbox") or [0, 0, 0, 0]
    for cb in competing_caption_bboxes:
        if len(gb) >= 4 and len(cb) >= 4 and cb[0] < gb[2] and gb[0] < cb[2]:
            return {"validation_status": "grouped_evidence_only", "validation_reason": "crosses_competing_caption_zone"}

    return {"validation_status": "strict_match_ok", "validation_reason": "local_growth_validated"}
```

- [ ] **Step 5: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "validation_rejects_large_gap or validation_demotes_group" -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "fix: validate grown figure groups before strict ownership"
```

---

### Task 3: Integrate Region Growth Into Candidate Group Construction

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add a failing integration test for region-grown groups reaching the inventory surface**

Append to `tests/test_ocr_figures.py`:

```python
def test_build_figure_inventory_uses_region_grown_group_for_irregular_pair() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 5, "block_id": "a1", "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 300, 260], "text": ""},
        {"page": 5, "block_id": "a2", "role": "figure_asset", "raw_label": "image", "bbox": [315, 110, 525, 270], "text": ""},
        {"page": 5, "block_id": "c1", "role": "figure_caption", "text": "Figure 1. Irregular pair.", "bbox": [100, 290, 520, 330], "zone": "display_zone", "style_family": "legend_like"},
    ]

    inventory = build_figure_inventory(structured_blocks)
    match = inventory["matched_figures"][0]
    assert len(match["matched_assets"]) == 2
```

- [ ] **Step 2: Run the red test**

Run: `python -m pytest tests/test_ocr_figures.py -k "region_grown_group_for_irregular_pair" -v`

Expected: FAIL until growth candidates are integrated into inventory construction.

- [ ] **Step 3: Integrate region growth into `_build_candidate_figure_groups_from_assets`**

After single-asset group creation, add a region-growth pass per page:

```python
    for page, page_media in by_page.items():
        ...
        sorted_page_media = sorted(page_media, key=lambda b: ((b.get("bbox") or [0, 0, 0, 0])[1], (b.get("bbox") or [0, 0, 0, 0])[0]))
        seen_growth_ids: set[str] = set()
        for seed in sorted_page_media:
            seed_id = str(seed.get("block_id", ""))
            if seed_id in seen_growth_ids:
                continue
            grown = _grow_region_from_seed(seed, [b for b in sorted_page_media if b is not seed], page_width)
            if len(grown.get("asset_block_ids", [])) <= 1:
                continue
            seen_growth_ids.update(grown.get("asset_block_ids", []))
            entry = _candidate_group_entry(
                f"group_{next_id:03d}",
                page,
                [b for b in sorted_page_media if str(b.get("block_id", "")) in set(grown.get("asset_block_ids", []))],
                "region_grown_group",
                ["same_page", "region_growth"],
            )
            entry["growth_steps"] = grown.get("growth_steps", [])
            groups.append(entry)
            next_id += 1
```

- [ ] **Step 4: Re-run the targeted test**

Run: `python -m pytest tests/test_ocr_figures.py -k "region_grown_group_for_irregular_pair" -v`

Expected: PASS.

- [ ] **Step 5: Run the full figure suite and page-swallow regression**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -v --tb=short
python -m pytest tests/test_ocr_real_paper_regressions.py -k "mega_merges_same_page_assets" -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py
git commit -m "feat: integrate region-grown figure groups into inventory"
```

---

### Task 4: Validate On Residual And Unseen Figure-Heavy Papers, Then Record The Slice

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Rebuild a figure-heavy validation sample after the merge changes**

Run:

```bash
python -m paperforge --vault "D:\L\OB\Literature-hub" ocr rebuild --clear-checkpoint
python -m paperforge --vault "D:\L\OB\Literature-hub" ocr rebuild A8E7SRVS SAN9AYVR 4PFR9M5N 7I4YGKFG DWQQK2YB VZMMSJBS X3NTXX4M
```

Expected: rebuild completes without reviving page-swallow behavior.

- [ ] **Step 2: Verify residual metrics and no new failure family**

Check generated artifacts for:

- improved grouped asset recall on irregular layouts,
- no return of unrestricted `page_assets` behavior,
- no blockquote or truth-surface regressions introduced indirectly,
- no new failure family on unseen papers.

- [ ] **Step 3: Update `PROJECT-MANAGEMENT.md`**

Append:

```md
### 11.5 Region-Growing Figure Merge Slice (2026-06-20)

**Problem:** Row-first pair/triple grouping had become safe after `page_assets` gating, but still under-modeled irregular multi-panel figures and left figure ownership recall on the table.

**Root cause:** Candidate groups were still built around neat-layout assumptions and lacked a seed-growth model plus post-growth validation.

**Fix:** Added seed-based local region growth, retained merge evidence per absorbed asset, validated grown groups before strict ownership, and demoted or split suspicious merges rather than forcing them.

**Result:** Figure grouping is less dependent on tidy layouts while preserving the no-page-swallow guardrail.

**Validation:** Rebuilt residual and unseen figure-heavy papers after the change; no new failure family introduced.
```

- [ ] **Step 4: Commit**

```bash
git add PROJECT-MANAGEMENT.md
git commit -m "docs: record region-growing figure merge slice"
```

---

## Self-Review Notes

- Spec coverage: this plan covers seed selection, local adjacency growth, merge evidence, post-growth validation, integration into inventory, and residual/unseen-paper validation.
- Scope discipline: table-note and table ambiguity work remains in the separate design thread.
