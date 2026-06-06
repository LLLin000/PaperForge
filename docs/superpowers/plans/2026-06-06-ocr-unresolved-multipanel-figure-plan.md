# OCR Unresolved Multi-Panel Figure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When OCR detects a multi-panel figure region but cannot validate a formal legend, preserve it as one unresolved figure candidate instead of degrading into multiple orphan assets.

**Architecture:** Keep the current `asset-first clustering -> legend validation -> matching` pipeline. The missing piece is to promote clustered-but-unmatched multi-panel regions into first-class inventory objects, then let object/render layers consume them. Do not reintroduce false `Figure N` objects from low-confidence legend text.

**Tech Stack:** Python, existing `paperforge.worker.ocr_figures`, `ocr_objects`, `ocr_render`, pytest.

---

## Problem Summary

Current behavior on `2GN9LMCW` page 9:

- `_compute_candidate_figure_regions()` already finds one correct multi-panel region:
  - bbox roughly `[363, 237, 1075, 1016]`
  - media block ids `[2,3,4,5,6,7]`
- the suspicious text `Days post culture in osteogenic differentiation supplemented medium` is correctly rejected from formal legend matching
- but because the candidate region never becomes a first-class inventory object:
  - no `Figure 4` note is emitted
  - the six panels degrade into six `orphan_XXX` objects

So the clustering layer is already doing useful work, but its output is being thrown away.

---

## Root Cause

The pipeline currently has a gap between:

1. **candidate region discovery**
2. **formal matched figure emission**

Today the inventory contract only persists:

- `matched_figures`
- `unmatched_assets`
- `rejected_legends`

It does **not** persist:

- clustered unresolved figure candidates

As a result:

- if formal legend validation succeeds -> good `figure_XXX.md`
- if formal legend validation fails -> region collapses into individual orphans

That is the wrong degradation behavior for multi-panel figures.

---

## Desired Behavior

For a page like `2GN9LMCW` page 9:

1. cluster six chart panels into one figure candidate region
2. reject the axis-title-like `figure_title` block as a formal legend
3. preserve the region as:
   - `unresolved_multi_panel`
   - or `orphan_cluster`
4. emit one object note for the whole region
5. optionally surface it in `fulltext.md` as a warning/candidate figure link
6. do **not** fabricate a fake formal `Figure 4`

This means the system remains conservative about legend truth, while still preserving the useful visual grouping.

---

## Data Contract Change

Extend `figure_inventory.json` with one new section:

```json
{
  "unresolved_clusters": [
    {
      "cluster_id": "cluster_004",
      "page": 9,
      "bbox": [363, 237, 1075, 1016],
      "media_block_ids": [2, 3, 4, 5, 6, 7],
      "matched_legend_block_id": null,
      "status": "unresolved_multi_panel",
      "confidence": 0.45,
      "flags": ["legend_rejected", "multi_panel_cluster"]
    }
  ]
}
```

Rules:

- `matched_figures` remains only for formal figure objects
- `unresolved_clusters` is for asset-first clusters with no validated formal legend
- `unmatched_assets` remains only for truly ungrouped residual assets

---

## Rendering/Object Contract

### Object layer

`ocr_objects.py` should emit:

- `render/figures/figure_XXX.md` for `matched_figures`
- `render/figures/orphan_cluster_XXX.md` (or `candidate_figure_XXX.md`) for `unresolved_clusters`
- single-asset orphans only for truly ungrouped unmatched assets

The unresolved cluster object should contain:

- a cropped image of the whole cluster bbox
- page number
- warning text like:
  - `Multi-panel figure candidate detected`
  - `No reliable formal legend matched`

It must **not** contain a fabricated `Figure 4` title.

### Render layer

`ocr_render.py` should decide whether unresolved cluster notes appear in `fulltext.md`.

Recommended behavior:

- do not mix them with formal `Figure N`
- if surfaced, use a warning-style unresolved figure entry

Example:

```md
>[!figure]- Unresolved figure candidate
> ![[render/figures/orphan_cluster_001.md]]
> [!warning] Multi-panel figure detected but no reliable formal legend matched.
```

If you want to keep `fulltext.md` cleaner, this can instead be omitted from body render and shown only in object/doctor outputs. But one explicit decision must be made.

---

## Implementation Tasks

### Task 1: Add failing tests for unresolved multi-panel clusters

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_figures.py`
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_objects.py`

- [ ] **Step 1: Add figure inventory regression**

Add a test that builds:

- six panel chart assets on one page
- one rejected low-confidence legend-like text

Assert:

- `matched_figures` stays empty for this region
- `rejected_legends` contains the bad legend
- `unresolved_clusters` contains one cluster with six media block ids
- `unmatched_assets` does not contain six separate residual panel assets

- [ ] **Step 2: Add object emission regression**

Assert:

- unresolved cluster produces exactly one object note
- that note is not titled `Figure 4`
- it points to a whole-cluster crop, not a single panel crop

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_objects.py -k "unresolved_cluster or multipanel" -q
```

Expected:

- FAIL

### Task 2: Persist unresolved cluster inventory

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_figures.py`

- [ ] **Step 1: Promote candidate regions into inventory entries**

When a candidate region:

- contains multiple media blocks
- has no validated formal legend

write it into `unresolved_clusters`.

- [ ] **Step 2: Consume cluster membership before orphan expansion**

Panel assets that belong to an unresolved cluster must not also spill into plain `unmatched_assets`.

- [ ] **Step 3: Run focused tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "unresolved_cluster or multipanel" -q
```

Expected:

- PASS

### Task 3: Emit unresolved cluster objects

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_objects.py`

- [ ] **Step 1: Add unresolved cluster object emission**

For each `unresolved_cluster`:

- crop the cluster bbox as one image
- write one markdown object note
- use a neutral title such as:
  - `Unresolved Figure Candidate`
  - or `Orphan Figure Cluster`

- [ ] **Step 2: Keep single-asset orphan behavior only for true residuals**

Do not emit per-panel orphan notes for assets already consumed by an unresolved cluster.

- [ ] **Step 3: Run focused tests**

Run:

```bash
python -m pytest tests/test_ocr_objects.py -k "unresolved_cluster or multipanel" -q
```

Expected:

- PASS

### Task 4: Decide render visibility

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_render.py`
- Modify tests if needed:
  - `tests/test_ocr_rendering.py`

- [ ] **Step 1: Choose one policy**

Pick one and implement it consistently:

- Option A: unresolved cluster notes are referenced in `fulltext.md`
- Option B: unresolved cluster notes stay out of `fulltext.md` but remain in render objects and doctor outputs

Recommended default:

- Option A for visibility, but clearly labeled as unresolved

- [ ] **Step 2: Add regression**

Assert the chosen behavior explicitly so it does not silently change later.

- [ ] **Step 3: Run focused tests**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py -k "unresolved_cluster or multipanel" -q
```

Expected:

- PASS

### Task 5: Real-paper validation on `2GN9LMCW`

**Files:**
- Verify:
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\2GN9LMCW\structure\figure_inventory.json`
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\2GN9LMCW\render\figures\`
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\2GN9LMCW\fulltext.md`

- [ ] **Step 1: Rebuild**

Run:

```bash
@'
from pathlib import Path
from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys
vault = Path(r'D:\L\OB\Literature-hub')
print(run_derived_rebuild_for_keys(vault, ['2GN9LMCW']))
'@ | python -
```

- [ ] **Step 2: Verify**

Expected:

- no fake `figure_004.md`
- one unresolved cluster object exists for page 9
- no six separate panel orphans for that same cluster
- no formal `Figure 4` emitted unless a real formal legend is found

---

## Acceptance Checklist

- [ ] candidate figure regions are persisted into inventory
- [ ] low-confidence legend text no longer creates a formal figure object
- [ ] multi-panel unresolved figure becomes one object, not six orphan panel notes
- [ ] `2GN9LMCW` page 9 no longer degrades into single-panel fake Figure 4
- [ ] the chosen unresolved-cluster render policy is explicit and tested

