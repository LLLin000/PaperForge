# OCR Table Score Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make table asset selection use `score_table_match()` instead of vertical-nearest selection.

**Architecture:** Keep `ocr_tables.py` as the table inventory owner. Expand candidate pages to previous/current/next, score all candidates, choose only when top score and score separation are safe, and expose match status for health/render consumers.

**Tech Stack:** Python, pytest, PaperForge table inventory JSON.

---

## File Structure

- Modify: `paperforge/worker/ocr_tables.py` — replace `_pick_best_asset()` with score-based selection.
- Modify: `paperforge/worker/ocr_scores.py` — extend `score_table_match()` if previous-page or caption-below evidence is missing.
- Modify: `paperforge/worker/ocr_health.py` — count low-confidence and ambiguous table matches.
- Test: `tests/test_ocr_tables.py` — score-based table selection tests.
- Test: `tests/test_ocr_scores.py` — table score evidence tests.

---

### Task 1: Add Previous-Page and Ambiguous Table Tests

**Files:**
- Modify: `tests/test_ocr_tables.py`

- [ ] **Step 1: Write failing previous-page match test**

Add to `tests/test_ocr_tables.py`:

```python
def test_table_inventory_considers_previous_page_assets() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    blocks = [
        {"block_id": "asset1", "role": "table_asset", "page": 1, "bbox": [100, 900, 700, 1200]},
        {"block_id": "cap1", "role": "table_caption", "page": 2, "text": "Table 1. Baseline characteristics", "bbox": [100, 80, 700, 120]},
    ]

    inventory = build_table_inventory(blocks)

    table = inventory["tables"][0]
    assert table["asset_block_id"] == "asset1"
    assert table["match_status"] in {"matched", "matched_low_confidence"}
```

- [ ] **Step 2: Write failing ambiguous candidate test**

Add:

```python
def test_table_inventory_marks_close_scores_ambiguous() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    blocks = [
        {"block_id": "cap1", "role": "table_caption", "page": 1, "text": "Table 1. Baseline characteristics", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset1", "role": "table_asset", "page": 1, "bbox": [100, 160, 700, 400]},
        {"block_id": "asset2", "role": "table_asset", "page": 1, "bbox": [105, 165, 705, 405]},
    ]

    inventory = build_table_inventory(blocks)
    table = inventory["tables"][0]
    assert table["match_status"] == "ambiguous"
    assert table["has_asset"] is False
    assert len(table["candidate_assets"]) == 2
```

- [ ] **Step 3: Run table tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_tables.py -k "previous_page_assets or close_scores" -v --tb=short
```

Expected: FAIL because current candidate pages exclude previous page and `_pick_best_asset()` chooses one nearest asset.

---

### Task 2: Replace `_pick_best_asset()` With Score-Based Selection

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`

- [ ] **Step 1: Add a score-based helper**

Replace `_compute_asset_score()` and `_pick_best_asset()` with:

```python
def _score_candidate_assets(
    page_assets: list[tuple[int, dict]],
    caption: dict,
    *,
    is_continuation: bool,
) -> list[tuple[int, dict, dict]]:
    scored = [
        (i, asset, score_table_match(caption, asset, is_continuation=is_continuation))
        for i, asset in page_assets
    ]
    scored.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
    return scored
```

- [ ] **Step 2: Expand candidate pages**

In `build_table_inventory()`, replace:

```python
candidate_pages = [caption_page] if is_cont else [caption_page, caption_page + 1]
```

with:

```python
candidate_pages = [caption_page - 1, caption_page, caption_page + 1]
if is_cont:
    candidate_pages = [caption_page - 1, caption_page, caption_page + 1]
```

- [ ] **Step 3: Select by score and separation**

Replace the loop that calls `_pick_best_asset()` with:

```python
all_candidates: list[tuple[int, dict, dict]] = []
for page in candidate_pages:
    if page < 1:
        continue
    page_assets = [
        (i, asset)
        for i, asset in enumerate(assets)
        if i not in used_asset_indices and asset.get("page", 0) == page
    ]
    all_candidates.extend(_score_candidate_assets(page_assets, caption, is_continuation=is_cont))

all_candidates.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
match_status = "unmatched_caption"
candidate_assets = [
    {"asset_block_id": asset.get("block_id", ""), "match_score": score}
    for _, asset, score in all_candidates[:3]
]

if all_candidates:
    top_idx, top_asset, top_score = all_candidates[0]
    second_score = all_candidates[1][2].get("score", 0.0) if len(all_candidates) > 1 else -1.0
    if top_score.get("score", 0.0) < 0.4:
        matched_asset = None
        match_status = "unmatched_caption"
    elif top_score.get("score", 0.0) - second_score < 0.15:
        matched_asset = None
        match_status = "ambiguous"
    else:
        matched_asset = top_asset
        used_asset_indices.add(top_idx)
        match_status = "matched" if top_score.get("score", 0.0) >= 0.6 else "matched_low_confidence"
```

- [ ] **Step 4: Add status and candidates to table entries**

In the table dict, add:

```python
"match_status": match_status,
"candidate_assets": candidate_assets,
```

Set `match_score` to the selected top score when matched, or the first candidate score when ambiguous/unmatched:

```python
"match_score": (
    score_table_match(caption, matched_asset, is_continuation=is_cont)
    if matched_asset
    else (all_candidates[0][2] if all_candidates else {"score": 0.0, "matched_asset_id": "", "decision": "ambiguous", "evidence": []})
),
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
python -m pytest tests/test_ocr_tables.py -k "previous_page_assets or close_scores" -q --tb=short
```

Expected: PASS.

---

### Task 3: Add Health Counts for Table Match Status

**Files:**
- Modify: `tests/test_ocr_health.py`
- Modify: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Write failing health test**

Add to `tests/test_ocr_health.py`:

```python
def test_ocr_health_counts_ambiguous_and_low_confidence_tables() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[{"role": "abstract_body"}, {"role": "reference_item"}, {"role": "section_heading"}, {"role": "section_heading"}],
        figure_inventory={},
        table_inventory={"tables": [
            {"has_asset": False, "is_continuation": False, "match_status": "ambiguous", "match_score": {"score": 0.5}},
            {"has_asset": True, "is_continuation": False, "match_status": "matched_low_confidence", "match_score": {"score": 0.45}},
        ]},
    )

    assert report["ambiguous_table_match_count"] == 1
    assert report["low_confidence_table_match_count"] == 1
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k ambiguous_and_low_confidence_tables -v --tb=short
```

Expected: FAIL with missing keys.

- [ ] **Step 3: Add health metrics**

In `build_ocr_health()`, after `tables = table_inventory.get("tables", [])`, add:

```python
ambiguous_table_match_count = sum(1 for t in tables if t.get("match_status") == "ambiguous")
low_confidence_table_match_count = sum(1 for t in tables if t.get("match_status") == "matched_low_confidence")
```

Add to `report`:

```python
"ambiguous_table_match_count": ambiguous_table_match_count,
"low_confidence_table_match_count": low_confidence_table_match_count,
```

- [ ] **Step 4: Run health test**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k ambiguous_and_low_confidence_tables -q --tb=short
```

Expected: PASS.

---

## Verification

Run after all tasks:

```bash
python -m pytest tests/test_ocr_scores.py tests/test_ocr_tables.py tests/test_ocr_health.py -q --tb=short
```

Expected: PASS.

Do not commit unless the user explicitly requests a commit.
