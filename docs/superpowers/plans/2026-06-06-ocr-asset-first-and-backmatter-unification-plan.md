# OCR Asset-First Figure Pipeline And Backmatter Unification Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the proven figure/panel asset handling from `master`, keep the clearer structured matching flow from the new OCR pipeline, and unify backmatter parsing after the body/tail boundary so mixed journal layouts stop producing unstable tail sections.

**Architecture:** The plan separates figure handling into `asset-first clustering -> legend validation -> matching`, and separates tail handling into `boundary detection -> unified backmatter family -> references zone`. It intentionally avoids paper-specific body-text patches and instead generalizes by layout behavior.

**Tech Stack:** Python, PyMuPDF-derived OCR span metadata, existing `paperforge.worker.ocr*` modules, pytest.

---

## Why This Plan

Current regressions show two distinct problems:

1. **Figure pipeline regression**
   - `master` had stronger image/chart clustering, composite-region handling, and figure-internal text rejection.
   - the new pipeline has cleaner separation of concepts, but lost the strong `asset-first` step.
   - result: multi-panel figures can degrade into `one panel matched + the rest orphaned`.

2. **Backmatter instability after boundary**
   - current tail logic can find the boundary, but after entering backmatter it still allows mixed role families:
     - `section_heading`
     - `subsection_heading`
     - `backmatter_boundary_heading`
     - `backmatter_heading`
     - `body_paragraph`
     - `frontmatter_noise`
   - result: child declarations drift, bodies disappear, and ordering becomes unstable.

The right fix is not more local patching. It is:

- **retain `master`'s useful asset-first logic**
- **keep current structured matching because its separation is clearer**
- **collapse backmatter to one role family after the boundary**

---

## Design Contract

### Figure contract

Figure handling is split into four layers:

1. **Asset clustering layer**
   - merge adjacent image/chart blocks into figure candidate regions
   - includes multi-panel and composite-region handling
   - excludes figure-internal text from participating as candidate legend text

2. **Legend validation layer**
   - determine whether a text block is a formal legend, candidate legend, or rejected inner text

3. **Matching layer**
   - match validated legends to candidate regions
   - do not let low-confidence legend fallback create bogus formal figure objects

4. **Degradation layer**
   - if no valid legend exists, keep unresolved candidate regions as non-formal assets
   - do not fabricate `Figure N` from inner labels

### Backmatter contract

Backmatter handling is split into three layers:

1. **Boundary detection**
   - determine:
     - `body_end`
     - `backmatter_start`
     - `references_start`

2. **Backmatter role unification**
   - once inside backmatter:
     - all non-reference headings become `backmatter_heading`
     - all owned content becomes `backmatter_body`
     - `References` becomes `reference_heading`
     - bibliography items become `reference_item`

3. **Local page/spread ordering**
   - use geometry and zone ownership only inside the backmatter region
   - references are a dedicated zone
   - no re-entry into ordinary body-heading logic

This means:

- `backmatter_boundary_heading` remains only a boundary aid
- it is not a long-lived internal family that competes with child sections

---

## What To Reuse From `master`

### Keep / adapt

These parts from `paperforge/worker/ocr.py` in `master` are valuable and should be adapted into the new structured pipeline rather than discarded:

- `media_clusters()`
  - adjacent image/chart cluster formation
  - overlap-aware and side-by-side panel handling

- `_cluster_bbox()`
  - cluster region bbox calculation

- `_precaption_media_region()`
  - media region above a caption
  - useful for whole-figure composite detection

- `compute_precaption_composite_regions()`
  - identifies composite figure regions spanning multiple panels/media blocks

- `is_embedded_figure_text_block()`
  - rejects inner chart labels / panel-local text / embedded figure text

- `is_numbered_figure_caption()`
  - protects against prose references like `Figure 3 shows ...`

### Do not copy forward unchanged

These aspects of `master` should remain improved in the new system:

- direct inline rendering-driven caption/media coupling
- single-file OCR orchestration coupling
- old rendering-time figure decisions mixed into markdown emission

So the migration rule is:

- **reuse the geometry / clustering / rejection heuristics**
- **do not re-couple them to inline rendering**

---

## What To Keep From The New Pipeline

The current split across modules is an improvement and should remain:

- `ocr_blocks.py`
- `ocr_roles.py`
- `ocr_figures.py`
- `ocr_tables.py`
- `ocr_objects.py`
- `ocr_render.py`
- `ocr_health.py`
- `ocr_index.py`

Also keep the clearer conceptual split:

- structured roles
- figure inventory
- object emission
- final render

The old `master` logic is only a source of asset-first heuristics, not a source of architecture.

---

## Implementation Tasks

### Task 1: Restore `master` asset-first figure clustering inside the new pipeline

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_figures.py`
- Reference only: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\paperforge\worker\ocr.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_figures.py`

- [ ] **Step 1: Add failing tests for multi-panel candidate clustering**

Add tests that require:

- adjacent panel charts on one page become one candidate figure region
- composite regions above caption are preserved
- cluster bbox union matches all relevant panels

The tests must cover:

- side-by-side panels
- stacked panels
- composite page with 2xN chart layout

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "multi_panel or composite_region" -q
```

Expected:

- FAIL because current inventory does not produce unified candidate regions.

- [ ] **Step 3: Port `master` clustering heuristics into structured figure preprocessing**

Implement reusable helpers in `ocr_figures.py` based on `master` logic:

- media clustering
- cluster bbox union
- precaption composite-region building

Do not render anything here. Output candidate figure regions only.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "multi_panel or composite_region" -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "fix: restore asset-first figure clustering"
```

### Task 2: Keep figure-internal text rejection from `master`

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_roles.py`
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_figures.py`
- Reference only: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\paperforge\worker\ocr.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_figures.py`

- [ ] **Step 1: Add failing tests for inner chart labels not becoming formal legends**

Cover:

- axis-title text
- panel-local labels
- chart-internal annotations
- prose `Figure N shows...` rejection

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "inner_label or formal_legend" -q
```

Expected:

- FAIL because ambiguous `figure_title` still creates formal objects.

- [ ] **Step 3: Implement legend rejection and candidate demotion**

Use `master`'s rejection ideas:

- `is_numbered_figure_caption()`
- embedded figure-text rejection
- caption-width / placement sanity

Rules:

- low-confidence `figure_title` may remain `rejected_legend`
- it must not create a formal `matched_figure`
- unresolved candidate regions should remain unresolved/orphan clusters

- [ ] **Step 4: Run the tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "inner_label or formal_legend" -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "fix: reject figure-internal text from formal legends"
```

### Task 3: Make matching consume candidate regions, not raw single assets

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_figures.py`
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_objects.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_figures.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_objects.py`

- [ ] **Step 1: Add failing tests for unresolved cluster degradation**

Cover:

- multi-panel figure with no validated legend does not become bogus `Figure 4`
- object generation does not create a misleading figure note from a rejected legend

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_objects.py -k "unresolved or orphan_cluster or figure_4" -q
```

Expected:

- FAIL

- [ ] **Step 3: Update figure inventory and object emission**

Implement:

- candidate region inventory entries
- formal match only from validated legends
- unresolved cluster output path
- object generation must consume matched candidate regions, not arbitrary first assets

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_objects.py -k "unresolved or orphan_cluster or figure_4" -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_objects.py tests/test_ocr_figures.py tests/test_ocr_objects.py
git commit -m "fix: match figures against clustered candidates"
```

### Task 4: Unify backmatter family after the boundary

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_roles.py`
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_render.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_rendering.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_render_stabilization.py`

- [ ] **Step 1: Add failing tests for container-backmatter normalization**

Cover:

- once `backmatter_start` is entered, all non-reference headings become `backmatter_heading`
- child sections do not remain `section_heading` / `subsection_heading`
- bodies inside backmatter do not fall back to `frontmatter_noise`

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -k "backmatter_container or declarations or author_contributions" -q
```

Expected:

- FAIL

- [ ] **Step 3: Normalize roles after boundary**

Implement:

- after `backmatter_start`, non-reference headings normalize to `backmatter_heading`
- `backmatter_boundary_heading` remains only a boundary aid, not a competing long-lived family
- child bodies become `backmatter_body`
- `reference_heading` and `reference_item` remain distinct

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -k "backmatter_container or declarations or author_contributions" -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_render.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py
git commit -m "fix: unify backmatter roles after boundary"
```

### Task 5: Keep local page/spread ordering simple and zone-driven

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_render.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_rendering.py`

- [ ] **Step 1: Add failing tests for backmatter local ordering**

Cover:

- backmatter child sections on a page/spread keep heading-body ownership
- references zone remains terminal
- no mixed ordering from old role families survives

- [ ] **Step 2: Run the failing tests**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py -k "tail_spread or references_zone or backmatter_order" -q
```

Expected:

- FAIL

- [ ] **Step 3: Simplify ordering to local zone ownership**

Implement ordering using:

- body/backmatter/references boundaries
- backmatter heading/body grouping
- references zone grouping

Avoid adding new complex fallback layers. After role unification, ordering should become simpler.

- [ ] **Step 4: Run tests**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py -k "tail_spread or references_zone or backmatter_order" -q
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_rendering.py
git commit -m "fix: simplify backmatter ordering by zones"
```

### Task 6: End-to-end regression validation on both layout families

**Files:**
- Verify only:
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD\fulltext.md`
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\2GN9LMCW\fulltext.md`
  - corresponding `meta.json`, `figure_inventory.json`, `health/ocr_health.json`
- Test:
  - `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_figures.py`
  - `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_rendering.py`
  - `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_render_stabilization.py`
  - `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_objects.py`

- [ ] **Step 1: Rebuild `7C8829BD` and `2GN9LMCW`**

Run:

```bash
@'
from pathlib import Path
from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys, backfill_from_result
vault = Path(r'D:\L\OB\Literature-hub')
print(run_derived_rebuild_for_keys(vault, ['7C8829BD']))
print(backfill_from_result(vault, '2GN9LMCW'))
'@ | python -
```

Expected:

- both complete without exceptions

- [ ] **Step 2: Run focused OCR suites**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_roles.py tests/test_ocr_rebuild.py -q
```

Expected:

- PASS

- [ ] **Step 3: Manual artifact audit**

Verify:

- `7C8829BD`
  - funding continuation remains correct
  - references zone remains clean
- `2GN9LMCW`
  - Figure 4 is either correctly unresolved or correctly matched as a whole figure, not a single wrong panel
  - declarations section ordering is stable
  - `Grant Disclosures`, `Author Contributions`, `Data Availability`, `Supplemental Information` each keep their body

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_roles.py paperforge/worker/ocr_render.py paperforge/worker/ocr_objects.py tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_roles.py tests/test_ocr_rebuild.py
git commit -m "fix: generalize figure clustering and backmatter parsing"
```

---

## Coverage Checklist

- [ ] `master` asset-first clustering behavior is preserved
- [ ] `master` embedded-figure-text rejection behavior is preserved
- [ ] current structured matching architecture is preserved
- [ ] low-confidence legends no longer fabricate formal figure objects
- [ ] multi-panel figure pages are analyzed as clustered figure candidates before legend matching
- [ ] backmatter boundary remains a boundary aid, not a competing internal family
- [ ] after backmatter start, all non-reference headings normalize into one backmatter family
- [ ] references remain a dedicated terminal zone
- [ ] `7C8829BD` stays correct
- [ ] `2GN9LMCW` stops producing broken Figure 4 and unstable declaration ordering

---

Plan complete and saved to `docs/superpowers/plans/2026-06-06-ocr-asset-first-and-backmatter-unification-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
