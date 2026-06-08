# OCR Health Hard Rule Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OCR health expose remaining hard-rule decisions and uncertainty counts across figures, tables, layout, inserts, and renderer-facing unresolved states.

**Architecture:** Keep health as the aggregation layer. It should summarize signals that already exist in inventories, document structure, decision logs, and audit docs; it should not perform new OCR classification.

**Tech Stack:** Python, pytest, OCR health JSON.

---

## File Structure

- Modify: `paperforge/worker/ocr_health.py` — add summary metrics.
- Modify: `tests/test_ocr_health.py` — health aggregation tests.
- Read: `docs/ocr/high-risk-rule-audit.md` — baseline count source if present.

---

### Task 1: Add Health Summary Metrics Test

**Files:**
- Modify: `tests/test_ocr_health.py`
- Modify: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Write failing uncertainty summary test**

Add to `tests/test_ocr_health.py`:

```python
def test_ocr_health_reports_hard_rule_and_uncertainty_summary() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, PageLayoutProfile
    from paperforge.worker.ocr_health import build_ocr_health

    doc = DocumentStructure(page_layouts={1: PageLayoutProfile(confidence=0.25)})
    doc.tail_boundary_score = {"score": 0.35}

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=6,
        structured_blocks=[
            {"role": "structured_insert", "insert_score": {"score": 0.35}},
            {"role": "abstract_body"}, {"role": "reference_item"}, {"role": "section_heading"}, {"role": "section_heading"},
        ],
        figure_inventory={
            "matched_figures": [{"caption_score": {"score": 0.3}}],
            "ambiguous_figures": [{"legend_block_id": "cap1"}],
            "unresolved_clusters": [{"cluster_id": "unresolved_cluster_001"}],
        },
        table_inventory={"tables": [{"match_status": "ambiguous", "match_score": {"score": 0.5}, "has_asset": False, "is_continuation": False}]},
        doc_structure=doc,
    )

    assert report["low_score_but_matched_count"] >= 1
    assert report["ambiguous_match_count"] >= 2
    assert report["unresolved_cluster_count"] == 1
    assert report["candidate_forced_count"] >= 1
    assert report["low_tail_boundary_confidence"] is True
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k hard_rule_and_uncertainty_summary -v --tb=short
```

Expected: FAIL with missing keys.

---

### Task 2: Implement Aggregation Metrics

**Files:**
- Modify: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Add figure uncertainty counts**

In `build_ocr_health()`, after figure score collection, add:

```python
ambiguous_figure_match_count = len(figure_inventory.get("ambiguous_figures", []))
unresolved_cluster_count = len(figure_inventory.get("unresolved_clusters", []))
low_score_matched_figures = sum(
    1 for mf in figure_inventory.get("matched_figures", [])
    if float(mf.get("caption_score", {}).get("score", 1.0)) < 0.4
)
```

- [ ] **Step 2: Add table uncertainty counts**

Add:

```python
ambiguous_table_match_count = sum(1 for t in tables if t.get("match_status") == "ambiguous")
low_score_matched_tables = sum(
    1 for t in tables
    if t.get("has_asset") and float(t.get("match_score", {}).get("score", 1.0)) < 0.4
)
```

- [ ] **Step 3: Add insert and tail counts**

Add:

```python
candidate_forced_count = sum(
    1 for b in structured_blocks
    if b.get("role") == "structured_insert" and float(b.get("insert_score", {}).get("score", 1.0)) < 0.7
)
low_tail_boundary_confidence = tail_score.get("score", 1.0) < 0.4
```

- [ ] **Step 4: Add values to `report`**

Add:

```python
"low_score_but_matched_count": low_score_matched_figures + low_score_matched_tables,
"ambiguous_match_count": ambiguous_figure_match_count + ambiguous_table_match_count,
"ambiguous_figure_match_count": ambiguous_figure_match_count,
"ambiguous_table_match_count": ambiguous_table_match_count,
"unresolved_cluster_count": unresolved_cluster_count,
"candidate_forced_count": candidate_forced_count,
"low_tail_boundary_confidence": low_tail_boundary_confidence,
```

- [ ] **Step 5: Run focused health test**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k hard_rule_and_uncertainty_summary -q --tb=short
```

Expected: PASS.

---

### Task 3: Add Audit Baseline Count Fallback

**Files:**
- Modify: `tests/test_ocr_health.py`
- Modify: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Write deterministic default test**

Add:

```python
def test_ocr_health_has_hard_rule_decision_count_key() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[{"role": "abstract_body"}, {"role": "reference_item"}, {"role": "section_heading"}, {"role": "section_heading"}],
        figure_inventory={},
        table_inventory={},
    )

    assert "hard_rule_decision_count" in report
    assert isinstance(report["hard_rule_decision_count"], int)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k hard_rule_decision_count_key -v --tb=short
```

Expected: FAIL with missing key.

- [ ] **Step 3: Add a safe default count**

In `build_ocr_health()`, add:

```python
hard_rule_decision_count = 0
```

Add to `report`:

```python
"hard_rule_decision_count": hard_rule_decision_count,
```

Do not make health parse Markdown in this step. If the audit count needs to become dynamic, add a later small parser with tests.

- [ ] **Step 4: Run health tests**

Run:

```bash
python -m pytest tests/test_ocr_health.py -q --tb=short
```

Expected: PASS.

---

## Verification

Run after all tasks:

```bash
python -m pytest tests/test_ocr_health.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_document.py -q --tb=short
```

Expected: PASS.

Do not commit unless the user explicitly requests a commit.
