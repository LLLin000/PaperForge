# OCR Figure Score Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make figure scoring participate in asset matching so low-confidence legends and ambiguous nearest assets are not emitted as confident figures.

**Architecture:** Keep `ocr_figures.py` as the inventory owner and extend `ocr_scores.py` with a lightweight figure match scorer. `build_figure_inventory()` should score candidate assets before consuming them and should preserve ambiguous/unmatched/orphan states.

**Tech Stack:** Python, pytest, PaperForge OCR figure inventory JSON.

---

## File Structure

- Modify: `paperforge/worker/ocr_scores.py` — add `score_figure_match()`.
- Modify: `paperforge/worker/ocr_figures.py` — replace nearest-only matching with scored candidate selection.
- Modify: `paperforge/worker/ocr_health.py` — count ambiguous and low-score matched figures.
- Test: `tests/test_ocr_scores.py` — figure match score unit tests.
- Test: `tests/test_ocr_figures.py` — inventory behavior tests.
- Test: `tests/test_ocr_rendering.py` — unresolved/orphan figure visibility if renderer currently drops them.

---

### Task 1: Add Figure Match Scorer Tests

**Files:**
- Modify: `tests/test_ocr_scores.py`
- Modify: `paperforge/worker/ocr_scores.py`

- [ ] **Step 1: Write failing tests for figure match scores**

Add to `tests/test_ocr_scores.py`:

```python
def test_figure_match_score_prefers_same_page_overlap() -> None:
    from paperforge.worker.ocr_scores import score_figure_match

    legend = {"block_id": "cap1", "page": 2, "bbox": [100, 500, 700, 540]}
    asset = {"block_id": "fig1", "page": 2, "bbox": [120, 120, 680, 480]}

    result = score_figure_match(legend, asset, caption_score={"score": 0.8})

    assert result["decision"] == "matched"
    assert result["matched_asset_id"] == "fig1"
    assert result["score"] >= 0.6
    assert "same_page" in result["evidence"]
    assert "x_overlap" in result["evidence"]


def test_figure_match_score_rejects_low_caption_score() -> None:
    from paperforge.worker.ocr_scores import score_figure_match

    legend = {"block_id": "cap1", "page": 2, "bbox": [100, 500, 700, 540]}
    asset = {"block_id": "fig1", "page": 2, "bbox": [120, 120, 680, 480]}

    result = score_figure_match(legend, asset, caption_score={"score": 0.2})

    assert result["decision"] == "rejected"
    assert result["score"] < 0.4
    assert "low_caption_score" in result["evidence"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_scores.py -k figure_match -v --tb=short
```

Expected: FAIL with missing `score_figure_match`.

- [ ] **Step 3: Implement `score_figure_match()`**

Add to `paperforge/worker/ocr_scores.py`:

```python
def score_figure_match(legend: dict, asset: dict, *, caption_score: dict | None = None) -> dict:
    legend_bbox = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
    asset_bbox = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
    score = 0.0
    evidence: list[str] = []

    caption_value = float((caption_score or {}).get("score", 0.0))
    if caption_value < 0.4:
        evidence.append("low_caption_score")
        return {"score": caption_value, "matched_asset_id": asset.get("block_id", ""), "decision": "rejected", "evidence": evidence}

    if legend.get("page") == asset.get("page"):
        score += 0.3
        evidence.append("same_page")
    if _bbox_x_overlap_ratio(legend_bbox, asset_bbox) >= 0.4:
        score += 0.25
        evidence.append("x_overlap")
    if len(legend_bbox) >= 4 and len(asset_bbox) >= 4:
        vertical_gap = min(abs(legend_bbox[1] - asset_bbox[3]), abs(asset_bbox[1] - legend_bbox[3]))
        if vertical_gap <= 300:
            score += 0.2
            evidence.append("nearby_y")
        if asset_bbox[3] <= legend_bbox[1] or asset_bbox[1] >= legend_bbox[3]:
            score += 0.1
            evidence.append("caption_above_or_below")
    score += min(0.15, caption_value * 0.15)
    score = max(0.0, min(1.0, score))
    decision = "matched" if score >= 0.6 else "ambiguous" if score >= 0.4 else "rejected"
    return {"score": score, "matched_asset_id": asset.get("block_id", ""), "decision": decision, "evidence": evidence}
```

- [ ] **Step 4: Run scorer tests**

Run:

```bash
python -m pytest tests/test_ocr_scores.py -k figure_match -q --tb=short
```

Expected: PASS.

---

### Task 2: Convert Nearest Asset Choice to Scored Selection

**Files:**
- Modify: `tests/test_ocr_figures.py`
- Modify: `paperforge/worker/ocr_figures.py`

- [ ] **Step 1: Write failing ambiguous-nearest test**

Add to `tests/test_ocr_figures.py`:

```python
def test_figure_inventory_marks_close_asset_candidates_ambiguous() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "cap1", "role": "figure_caption", "page": 1, "text": "Figure 1. Assay result", "bbox": [100, 500, 700, 540]},
        {"block_id": "asset1", "role": "figure_asset", "page": 1, "bbox": [100, 100, 700, 470]},
        {"block_id": "asset2", "role": "figure_asset", "page": 1, "bbox": [110, 560, 710, 900]},
    ]

    inventory = build_figure_inventory(blocks)

    assert inventory["matched_figures"] == []
    assert len(inventory.get("ambiguous_figures", [])) == 1
    assert inventory["ambiguous_figures"][0]["legend_block_id"] == "cap1"
```

- [ ] **Step 2: Run the test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k close_asset_candidates -v --tb=short
```

Expected: FAIL because current code chooses one nearest asset.

- [ ] **Step 3: Import and use `score_figure_match()`**

In `paperforge/worker/ocr_figures.py`, update the import:

```python
from paperforge.worker.ocr_scores import score_figure_caption, score_figure_match
```

Then replace the nearest-asset loop in `build_figure_inventory()` with candidate scoring:

```python
caption_score = score_figure_caption(
    legend,
    nearby_media=any(a.get("page", 0) == legend_page for a in assets),
    caption_style_match=_caption_style_match(legend, structured_blocks),
)
candidates = []
for ai, asset in enumerate(assets):
    if ai in used_asset_indices or asset.get("page", 0) != legend_page:
        continue
    match_score = score_figure_match(legend, asset, caption_score=caption_score)
    if match_score["decision"] != "rejected":
        candidates.append((ai, asset, match_score))
candidates.sort(key=lambda item: item[2]["score"], reverse=True)
```

- [ ] **Step 4: Add selection rules**

Use these rules immediately after sorting candidates:

```python
ambiguous_figures: list[dict] = []

if candidates:
    top_score = candidates[0][2]["score"]
    close = [item for item in candidates if top_score - item[2]["score"] < 0.15]
    if top_score < 0.4:
        matched_assets = []
    elif len(close) > 1:
        ambiguous_figures.append({
            "legend_block_id": legend.get("block_id", ""),
            "page": legend_page,
            "caption_score": caption_score,
            "candidates": [
                {"asset_block_id": asset.get("block_id", ""), "match_score": score}
                for _, asset, score in close
            ],
        })
        matched_assets = []
    else:
        best_idx, best_asset, best_score = candidates[0]
        matched_assets = [best_asset]
        used_asset_indices.add(best_idx)
        region_match = {"media_blocks": [best_asset], "match_score": best_score}
```

Keep one `ambiguous_figures` list initialized near `matched_figures` and include it in the returned inventory.

- [ ] **Step 5: Run the focused figure test**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k close_asset_candidates -q --tb=short
```

Expected: PASS.

---

### Task 3: Refuse Low-Caption-Score Confident Matches

**Files:**
- Modify: `tests/test_ocr_figures.py`
- Modify: `paperforge/worker/ocr_figures.py`

- [ ] **Step 1: Write failing low-caption-score test**

Add to `tests/test_ocr_figures.py`:

```python
def test_figure_inventory_does_not_confidently_match_low_caption_score() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "cap1", "role": "figure_caption_candidate", "page": 1, "text": "Figure 1 shows that cells moved.", "bbox": [100, 500, 700, 540]},
        {"block_id": "asset1", "role": "figure_asset", "page": 1, "bbox": [100, 100, 700, 470]},
    ]

    inventory = build_figure_inventory(blocks)

    assert inventory["matched_figures"] == []
    assert len(inventory["unmatched_legends"]) == 1
```

- [ ] **Step 2: Run the test to verify failure or current behavior**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k low_caption_score -v --tb=short
```

Expected: FAIL if the candidate still becomes a confident match.

- [ ] **Step 3: Guard `matched_figures.append()`**

In `build_figure_inventory()`, append to `matched_figures` only when `matched_assets` is non-empty and `caption_score["score"] >= 0.4`. Otherwise append the legend to `unmatched_legends` and skip creating a confident figure entry.

Use this shape:

```python
if not matched_assets or caption_score.get("score", 0.0) < 0.4:
    unmatched_legends.append(legend)
    continue
```

- [ ] **Step 4: Run figure tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -q --tb=short
```

Expected: PASS.

---

## Verification

Run after all tasks:

```bash
python -m pytest tests/test_ocr_scores.py tests/test_ocr_figures.py tests/test_ocr_health.py tests/test_ocr_rendering.py -q --tb=short
```

Expected: PASS.

Do not commit unless the user explicitly requests a commit.
