# OCR-v2 PR3 Ownership & Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the two highest-blast-radius residual fixes in the safest possible way: reject dangerous cross-column `page_assets` groups at the acceptance gate, then add conservative post-hoc figure/table asset arbitration.

**Architecture:** Do not start with clustering redesign or figure-first ordering. For Issue 5, tighten `_is_safe_page_assets_group(...)` so unsafe cross-column groups never become valid figure candidates. For Issue 6, keep both local inventories intact, then arbitrate only after both exist and before writeback/render. Preserve the existing `ownership_conflicts` audit surface.

**Tech Stack:** Python 3.x, pytest, OCR worker modules under `paperforge/worker/`

## Global Constraints

- PR3 scope is fixed: **Issue 5 → Issue 6**.
- Do **not** refactor `_cluster_semantic_page_assets(...)` first.
- Do **not** add full column-layout inference.
- Do **not** use figure-first ordering.
- Do **not** remove `ownership_conflicts`; unresolved overlaps must remain visible.
- Arbitration may resolve only clear asymmetric cases; weak/weak conflicts stay surfaced.
- Place arbitration in pipeline wiring after both inventories exist.

---

## File Map

- `paperforge/worker/ocr_figures.py` — safe-group gate, conflict resolution helper, conflict audit
- `paperforge/worker/ocr.py` — main OCR pipeline wiring
- `paperforge/worker/ocr_rebuild.py` — rebuild pipeline wiring
- `tests/test_ocr_figures.py` — page-assets gate tests and ownership arbitration tests

---

### Task 1: Reject cross-column `page_assets` groups at `_is_safe_page_assets_group`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

**Interfaces:**
- Consumes: `_is_safe_page_assets_group(group, legend, page_blocks, page_numbered_legend_count, page_width, page_height) -> tuple[bool, list[str]]`
- Produces:
  - `_column_band_id(bbox, page_width) -> int | None`
  - new rejection evidence: `cross_column_media`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_figures.py`:

```python
def test_page_assets_group_rejects_cross_column_media_assets():
    from paperforge.worker.ocr_figures import _is_safe_page_assets_group

    media_blocks = [
        {"block_id": "L1", "page": 1, "bbox": [0, 0, 280, 200], "raw_label": "image", "text": ""},
        {"block_id": "L2", "page": 1, "bbox": [0, 220, 280, 420], "raw_label": "image", "text": ""},
        {"block_id": "R1", "page": 1, "bbox": [310, 0, 590, 200], "raw_label": "image", "text": ""},
    ]
    group = {"media_blocks": media_blocks, "cluster_bbox": [0, 0, 590, 420]}
    legend = {"text": "Figure 1. Example.", "page": 1}

    safe, evidence = _is_safe_page_assets_group(
        group,
        legend,
        page_blocks=list(media_blocks),
        page_numbered_legend_count=1,
        page_width=600,
        page_height=1000,
    )

    assert safe is False
    assert "cross_column_media" in evidence


def test_same_column_stacked_assets_still_pass_gate():
    from paperforge.worker.ocr_figures import _is_safe_page_assets_group

    media_blocks = [
        {"block_id": "A", "page": 1, "bbox": [0, 0, 280, 200], "raw_label": "image", "text": ""},
        {"block_id": "B", "page": 1, "bbox": [0, 220, 280, 420], "raw_label": "image", "text": ""},
        {"block_id": "C", "page": 1, "bbox": [0, 440, 280, 640], "raw_label": "image", "text": ""},
    ]
    group = {"media_blocks": media_blocks, "cluster_bbox": [0, 0, 280, 640]}
    legend = {"text": "Figure 1. Example.", "page": 1}

    safe, evidence = _is_safe_page_assets_group(
        group,
        legend,
        page_blocks=list(media_blocks),
        page_numbered_legend_count=1,
        page_width=600,
        page_height=1000,
    )

    assert safe is True
    assert evidence == []


def test_full_width_group_can_span_columns_without_rejection():
    from paperforge.worker.ocr_figures import _is_safe_page_assets_group

    media_blocks = [
        {"block_id": "A", "page": 1, "bbox": [20, 100, 580, 280], "raw_label": "image", "text": ""},
        {"block_id": "B", "page": 1, "bbox": [20, 300, 580, 480], "raw_label": "image", "text": ""},
        {"block_id": "C", "page": 1, "bbox": [20, 500, 580, 680], "raw_label": "image", "text": ""},
    ]
    group = {"media_blocks": media_blocks, "cluster_bbox": [20, 100, 580, 680]}
    legend = {"text": "Figure 1. Full-width figure.", "page": 1}

    safe, evidence = _is_safe_page_assets_group(
        group,
        legend,
        page_blocks=list(media_blocks),
        page_numbered_legend_count=1,
        page_width=600,
        page_height=1000,
    )

    assert safe is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_figures.py::test_page_assets_group_rejects_cross_column_media_assets \
  tests/test_ocr_figures.py::test_same_column_stacked_assets_still_pass_gate \
  tests/test_ocr_figures.py::test_full_width_group_can_span_columns_without_rejection -q
```

Expected: FAIL because the current gate is column-agnostic.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_figures.py`, add:

```python
def _column_band_id(bbox: list[float], page_width: float) -> int | None:
    if not bbox or len(bbox) < 4 or page_width <= 0:
        return None
    center_x = (bbox[0] + bbox[2]) / 2.0
    if center_x < page_width * 0.45:
        return 0
    if center_x > page_width * 0.55:
        return 1
    return None
```

Then add a final gate in `_is_safe_page_assets_group(...)` before `return True, evidence`:

```python
full_width_group = cw >= page_width * 0.65 and page_numbered_legend_count == 1
if not full_width_group:
    bands = {
        _column_band_id(mb.get("bbox") or [0, 0, 0, 0], page_width)
        for mb in media_blocks
    }
    bands.discard(None)
    if len(bands) > 1:
        return False, ["cross_column_media"]
```

This is intentionally a **rejection gate only**. Do not alter clustering.

- [ ] **Step 4: Run tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py
git commit -m "fix: reject cross-column safe page-assets groups"
```

---

### Task 2: Add conservative post-hoc figure/table arbitration

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

**Interfaces:**
- Produces:
  - `_table_ownership_strength(table: dict) -> tuple[int, int]`
  - `_figure_ownership_strength(fig: dict) -> tuple[int, int]`
  - `resolve_media_asset_conflicts(figure_inventory: dict, table_inventory: dict) -> list[dict]`
  - `figure_inventory["ownership_resolutions"]`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ocr_figures.py`:

```python
def test_resolve_media_asset_conflicts_prefers_explicit_table_over_weak_figure():
    from paperforge.worker.ocr_figures import resolve_media_asset_conflicts, _build_ownership_conflicts

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "legend_block_id": "figcap",
                "text": "Figure 1. Example.",
                "match_score": {"score": 0.51, "decision": "matched", "evidence": ["fallback"]},
                "asset_block_ids": ["asset"],
                "page": 1,
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "caption_block_id": "tabcap",
                "caption_text": "Table 1. Example.",
                "match_status": "matched",
                "has_asset": True,
                "asset_block_id": "asset",
                "page": 1,
            }
        ]
    }

    resolutions = resolve_media_asset_conflicts(figure_inventory, table_inventory)
    conflicts = _build_ownership_conflicts(figure_inventory, table_inventory)

    assert resolutions[0]["winner"] == "table"
    assert figure_inventory["matched_figures"] == []
    assert conflicts == []


def test_resolve_media_asset_conflicts_prefers_explicit_figure_over_weak_table():
    from paperforge.worker.ocr_figures import resolve_media_asset_conflicts, _build_ownership_conflicts

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "legend_block_id": "figcap",
                "text": "Figure 1. Example.",
                "match_score": {"score": 0.92, "decision": "matched", "evidence": ["same_page", "x_overlap"]},
                "asset_block_ids": ["asset"],
                "page": 1,
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "caption_block_id": "tabcap",
                "caption_text": "Table 1",
                "match_status": "matched_low_confidence",
                "has_asset": True,
                "asset_block_id": "asset",
                "page": 1,
            }
        ]
    }

    resolutions = resolve_media_asset_conflicts(figure_inventory, table_inventory)
    conflicts = _build_ownership_conflicts(figure_inventory, table_inventory)

    assert resolutions[0]["winner"] == "figure"
    assert table_inventory["tables"][0]["has_asset"] is False
    assert conflicts == []


def test_resolve_media_asset_conflicts_leaves_weak_weak_case_unresolved():
    from paperforge.worker.ocr_figures import resolve_media_asset_conflicts, _build_ownership_conflicts

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "legend_block_id": "figcap",
                "text": "Figure 1.",
                "match_score": {"score": 0.52, "decision": "matched_low_confidence", "evidence": ["fallback"]},
                "asset_block_ids": ["asset"],
                "page": 1,
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "caption_block_id": "tabcap",
                "caption_text": "Table 1",
                "match_status": "matched_low_confidence",
                "has_asset": True,
                "asset_block_id": "asset",
                "page": 1,
            }
        ]
    }

    resolutions = resolve_media_asset_conflicts(figure_inventory, table_inventory)
    conflicts = _build_ownership_conflicts(figure_inventory, table_inventory)

    assert resolutions == []
    assert len(conflicts) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_prefers_explicit_table_over_weak_figure \
  tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_prefers_explicit_figure_over_weak_table \
  tests/test_ocr_figures.py::test_resolve_media_asset_conflicts_leaves_weak_weak_case_unresolved -q
```

Expected: FAIL because `resolve_media_asset_conflicts` does not exist.

- [ ] **Step 3: Write minimal implementation**

In `paperforge/worker/ocr_figures.py`, add:

```python
def _table_ownership_strength(table: dict) -> tuple[int, int]:
    explicit = 1 if str(table.get("caption_text") or "").lower().startswith("table") else 0
    strong = 1 if str(table.get("match_status") or "") == "matched" else 0
    return (explicit, strong)


def _figure_ownership_strength(fig: dict) -> tuple[int, int]:
    text = str(fig.get("text") or "")
    explicit = 1 if text.lower().startswith(("figure", "fig.")) else 0
    strong = 1 if float((fig.get("match_score") or {}).get("score", 0.0) or 0.0) >= 0.70 else 0
    return (explicit, strong)


def resolve_media_asset_conflicts(figure_inventory: dict, table_inventory: dict) -> list[dict]:
    resolutions: list[dict] = []
    tables_by_asset = {
        (int(t.get("page", 0) or 0), str(t.get("asset_block_id", ""))): t
        for t in table_inventory.get("tables", [])
        if t.get("has_asset") and t.get("asset_block_id")
    }

    kept_figures = []
    for fig in figure_inventory.get("matched_figures", []):
        asset_ids = [
            (int(fig.get("page", 0) or 0), str(bid))
            for bid in fig.get("asset_block_ids", [])
            if bid is not None
        ]
        conflict_id = next((aid for aid in asset_ids if aid in tables_by_asset), None)
        if conflict_id is None:
            kept_figures.append(fig)
            continue

        table = tables_by_asset[conflict_id]
        table_strength = _table_ownership_strength(table)
        figure_strength = _figure_ownership_strength(fig)

        if table_strength > figure_strength:
            resolutions.append({"page": conflict_id[0], "block_id": conflict_id[1], "winner": "table"})
            continue
        if figure_strength > table_strength:
            resolutions.append({"page": conflict_id[0], "block_id": conflict_id[1], "winner": "figure"})
            table["has_asset"] = False
            table["asset_block_id"] = None
            kept_figures.append(fig)
            continue

        kept_figures.append(fig)

    figure_inventory["matched_figures"] = kept_figures
    figure_inventory["ownership_resolutions"] = resolutions
    return resolutions
```

Do **not** auto-resolve equal-strength weak/weak cases.

- [ ] **Step 4: Run tests to verify they pass**

Run the same command from Step 2.

Expected: PASS.

---

### Task 3: Wire arbitration into the two OCR pipelines

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_figures.py`

**Interfaces:**
- Consumes: `resolve_media_asset_conflicts(...)`, `attach_ownership_conflicts(...)`
- Produces: pipeline order
  1. build figure inventory
  2. build table inventory
  3. resolve ownership conflicts
  4. attach remaining ownership conflicts
  5. writebacks / render

- [ ] **Step 1: Add a small integration test**

Add to `tests/test_ocr_figures.py`:

```python
def test_attach_ownership_conflicts_runs_after_resolution():
    from paperforge.worker.ocr_figures import resolve_media_asset_conflicts, attach_ownership_conflicts

    figure_inventory = {
        "matched_figures": [{
            "figure_id": "figure_001",
            "legend_block_id": "figcap",
            "text": "Figure 1. Example.",
            "match_score": {"score": 0.51, "decision": "matched", "evidence": ["fallback"]},
            "asset_block_ids": ["asset"],
            "page": 1,
        }]
    }
    table_inventory = {
        "tables": [{
            "table_id": "table_001",
            "caption_block_id": "tabcap",
            "caption_text": "Table 1. Example.",
            "match_status": "matched",
            "has_asset": True,
            "asset_block_id": "asset",
            "page": 1,
        }]
    }

    resolve_media_asset_conflicts(figure_inventory, table_inventory)
    attach_ownership_conflicts(figure_inventory, table_inventory)

    assert figure_inventory.get("ownership_conflicts") == []
    assert figure_inventory.get("ownership_resolutions")[0]["winner"] == "table"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_attach_ownership_conflicts_runs_after_resolution -q
```

Expected: FAIL until resolution logic and wiring exist together.

- [ ] **Step 3: Update pipeline wiring**

In both `paperforge/worker/ocr.py` and `paperforge/worker/ocr_rebuild.py`, replace:

```python
from paperforge.worker.ocr_figures import attach_ownership_conflicts
attach_ownership_conflicts(figure_inventory, table_inventory)
```

with:

```python
from paperforge.worker.ocr_figures import attach_ownership_conflicts, resolve_media_asset_conflicts
resolve_media_asset_conflicts(figure_inventory, table_inventory)
attach_ownership_conflicts(figure_inventory, table_inventory)
```

Keep this order **before** writebacks.

- [ ] **Step 4: Run focused regression bundle**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr.py paperforge/worker/ocr_rebuild.py tests/test_ocr_figures.py
git commit -m "fix: add conservative figure-table asset arbitration"
```

---

## Self-Review

### 1. Spec coverage
- Issue 5 cross-column page-assets acceptance → Task 1
- Issue 6 post-hoc arbitration + preserved audit surface → Tasks 2-3

### 2. Placeholder scan
- No TODO/TBD text remains
- Every task includes exact files, tests, commands, and code snippets

### 3. Type consistency
- Issue 5 is a gate-only change in `ocr_figures.py`
- Issue 6 adds one helper plus wiring calls; no signature churn outside explicit new helper

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-01-ocr-v2-pr3-ownership-boundary-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
