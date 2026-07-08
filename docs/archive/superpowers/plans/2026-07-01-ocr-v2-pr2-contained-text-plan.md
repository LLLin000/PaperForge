# OCR-v2 PR2 Figure Contained-Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix demoted-caption figure inner-text leakage by adding validated `_container_bbox` regions to `tag_figure_contained_text`, without changing figure ownership or creating new matched figures.

**Architecture:** Keep this PR containment-only. The only production file is `ocr_figures.py`. `_container_bbox` is already produced upstream and passed through structured blocks; this PR only teaches the containment pass to use it safely as an additional region source. Do not touch figure matching, role assignment, render, or pipeline wiring.

**Tech Stack:** Python 3.x, pytest, OCR worker modules under `paperforge/worker/`

## Global Constraints

- PR2 scope is fixed: **Issue 2 only**.
- Root cause is **demoted-caption cascade / missing reliable figure region**, not generic asset-gap blindness.
- Do **not** use padding to widen `cluster_bbox`.
- Do **not** create new `matched_figure` entries.
- Do **not** consume assets or mutate figure ownership.
- Only allowed behavior change: contained leak blocks may get `_figure_contained=True` and `role="figure_inner_text"`.
- Prefer additive helpers inside `ocr_figures.py`.

---

## File Map

- `paperforge/worker/ocr_figures.py` — containment region construction and tagging
- `tests/unit/worker/test_figure_containment.py` — containment tests

---

### Task 1: Add failing containment tests for `_container_bbox` demoted-caption cases

**Files:**
- Test: `tests/unit/worker/test_figure_containment.py`

**Interfaces:**
- Consumes: existing `tag_figure_contained_text(blocks, matched_figures) -> None`
- Produces: failing tests that describe the desired containment-only behavior

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/worker/test_figure_containment.py`:

```python
def test_container_bbox_tags_vision_footnote_inside_demoted_figure(self):
    blocks = [
        self._block(
            "inner",
            1,
            120,
            120,
            180,
            140,
            role="footnote",
            text="Single outlet",
            _container_bbox=[90, 90, 320, 220],
            page_width=1000,
            page_height=1600,
        ),
        self._block(
            "asset1",
            1,
            100,
            100,
            200,
            200,
            role="media_asset",
            raw_label="table",
            asset_family_hint="ambiguous",
            page_width=1000,
            page_height=1600,
        ),
        self._block(
            "asset2",
            1,
            210,
            100,
            310,
            200,
            role="media_asset",
            raw_label="table",
            asset_family_hint="ambiguous",
            page_width=1000,
            page_height=1600,
        ),
    ]

    tag_figure_contained_text(blocks, [])

    assert blocks[0]["role"] == "figure_inner_text"
    assert blocks[0]["_figure_contained"] is True


def test_container_bbox_does_not_consume_body_paragraph_next_to_figure(self):
    blocks = [
        self._block(
            "body",
            1,
            350,
            100,
            700,
            130,
            role="body_paragraph",
            text="Nearby body text",
            _container_bbox=[90, 90, 320, 220],
            page_width=1000,
            page_height=1600,
        ),
        self._block(
            "asset1",
            1,
            100,
            100,
            200,
            200,
            role="media_asset",
            raw_label="image",
            asset_family_hint="figure_like",
            page_width=1000,
            page_height=1600,
        ),
    ]

    tag_figure_contained_text(blocks, [])

    assert blocks[0]["role"] == "body_paragraph"
    assert not blocks[0].get("_figure_contained")


def test_huge_container_bbox_is_rejected_by_area_gate(self):
    blocks = [
        self._block(
            "body",
            1,
            100,
            100,
            300,
            130,
            role="body_paragraph",
            text="Nearby body text",
            _container_bbox=[0, 0, 1000, 1600],
            page_width=1000,
            page_height=1600,
        ),
        self._block(
            "asset",
            1,
            100,
            500,
            300,
            700,
            role="media_asset",
            raw_label="image",
            asset_family_hint="figure_like",
            page_width=1000,
            page_height=1600,
        ),
    ]

    tag_figure_contained_text(blocks, [])

    assert blocks[0]["role"] == "body_paragraph"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/worker/test_figure_containment.py -q
```

Expected: FAIL because `_container_bbox` is currently ignored.

---

### Task 2: Add validated `_container_bbox` region helpers in `ocr_figures.py`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/unit/worker/test_figure_containment.py`

**Interfaces:**
- Produces:
  - `_container_area_ok(container_bbox, page_width, page_height) -> bool`
  - `_container_has_media_asset(container_bbox, page_blocks) -> bool`
  - `_validated_container_regions(page_blocks, page_width, page_height) -> list[list[float]]`

- [ ] **Step 1: Write helper-level tests**

Add to `tests/unit/worker/test_figure_containment.py`:

```python
def test_validated_container_regions_reject_missing_media_assets(self):
    blocks = [
        self._block("body", 1, 100, 100, 300, 130, role="body_paragraph", text="x", _container_bbox=[90, 90, 320, 220], page_width=1000, page_height=1600),
    ]
    regions = _validated_container_regions(blocks, 1000, 1600)
    assert regions == []


def test_validated_container_regions_accept_reasonable_container_with_media(self):
    blocks = [
        self._block("body", 1, 120, 120, 180, 140, role="footnote", text="x", _container_bbox=[90, 90, 320, 220], page_width=1000, page_height=1600),
        self._block("asset", 1, 100, 100, 200, 200, role="media_asset", raw_label="image", asset_family_hint="figure_like", page_width=1000, page_height=1600),
    ]
    regions = _validated_container_regions(blocks, 1000, 1600)
    assert regions == [[90, 90, 320, 220]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/worker/test_figure_containment.py -q
```

Expected: FAIL because helper(s) do not exist.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_figures.py`, add:

```python
def _container_area_ok(container_bbox: list[float], page_width: float, page_height: float) -> bool:
    if len(container_bbox) < 4 or page_width <= 0 or page_height <= 0:
        return False
    cw = container_bbox[2] - container_bbox[0]
    ch = container_bbox[3] - container_bbox[1]
    page_area = max(1.0, page_width * page_height)
    container_area = max(1.0, cw * ch)
    if container_area >= page_area * 0.65:
        return False
    if cw >= page_width * 0.98 and ch >= page_height * 0.45:
        return False
    return True


def _container_has_media_asset(container_bbox: list[float], page_blocks: list[dict]) -> bool:
    for block in page_blocks:
        if block.get("role") not in {"figure_asset", "media_asset"}:
            continue
        bbox = block.get("bbox") or [0, 0, 0, 0]
        if len(bbox) < 4:
            continue
        if _is_contained(bbox, container_bbox):
            return True
    return False


def _validated_container_regions(page_blocks: list[dict], page_width: float, page_height: float) -> list[list[float]]:
    regions: list[list[float]] = []
    seen: set[tuple[float, float, float, float]] = set()
    for block in page_blocks:
        bbox = block.get("_container_bbox")
        if not bbox or len(bbox) < 4:
            continue
        tup = tuple(float(x) for x in bbox)
        if tup in seen:
            continue
        seen.add(tup)
        if not _container_area_ok(list(tup), page_width, page_height):
            continue
        if not _container_has_media_asset(list(tup), page_blocks):
            continue
        regions.append(list(tup))
    return regions
```

- [ ] **Step 4: Run tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 3: Wire `_container_bbox` regions into `tag_figure_contained_text`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/unit/worker/test_figure_containment.py`

**Interfaces:**
- Consumes: `tag_figure_contained_text(blocks, matched_figures)`
- Produces: region source priority
  1. matched figure bbox
  2. validated `_container_bbox`
  3. fallback asset cluster bbox

- [ ] **Step 1: Update the integration tests if needed**

If the helper-only tests passed but integration tests still do not cover ordering, add:

```python
def test_matched_cluster_bbox_takes_precedence_over_container_bbox(self):
    mf = self._matched_fig(1, [80, 80, 220, 220], matched_assets=[{"block_id": "a1", "bbox": [90, 90, 200, 200]}])
    blocks = [
        self._block("inner", 1, 120, 120, 180, 140, role="footnote", text="x", _container_bbox=[0, 0, 1000, 1600], page_width=1000, page_height=1600),
        self._block("a1", 1, 90, 90, 200, 200, role="figure_asset", raw_label="image", asset_family_hint="figure_like", page_width=1000, page_height=1600),
    ]
    tag_figure_contained_text(blocks, [mf])
    assert blocks[0]["role"] == "figure_inner_text"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/unit/worker/test_figure_containment.py -q
```

Expected: FAIL on the new integration coverage if `_container_bbox` regions are still unused.

- [ ] **Step 3: Write minimal implementation**

Inside `tag_figure_contained_text(...)`, after matched figure regions and before fallback asset regions, add:

```python
page_width = max((float(b.get("page_width") or 0.0) for b in page_blocks), default=0.0)
page_height = max((float(b.get("page_height") or 0.0) for b in page_blocks), default=0.0)

for cr in _validated_container_regions(page_blocks, page_width, page_height):
    if not _highly_overlaps_any_matched_region(cr, figure_regions):
        figure_regions.append(("container", cr))
```

Keep the existing skip rules for roles and the existing `_LEAK_ROLES` behavior. Do **not** create inventory entries. Do **not** alter `matched_figures`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/worker/test_figure_containment.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/unit/worker/test_figure_containment.py
git commit -m "fix: add validated container regions for figure contained text"
```

---

## Self-Review

### 1. Spec coverage
- Demoted-caption region gap → covered
- `_container_bbox` safety gates → covered
- Containment-only scope → covered
- Rejected approaches (padding, ownership mutation) → honored

### 2. Placeholder scan
- No TODO/TBD text remains
- Every task includes exact files, tests, commands, and code snippets

### 3. Type consistency
- Only additive helpers and local integration inside `ocr_figures.py`
- No pipeline wiring changes in PR2

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-01-ocr-v2-pr2-contained-text-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
