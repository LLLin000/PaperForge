# OCR Insert Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace direct structured insert promotion with score, evidence, candidate states, and conservative fallbacks.

**Architecture:** Add a structured insert scorer in `ocr_scores.py` and make `ocr_document.py` consume it during region prepass and promotion. Visual container, page-1 keywords, and continuation become evidence instead of direct conclusions.

**Tech Stack:** Python, pytest, OCR decision log metadata.

---

## File Structure

- Modify: `paperforge/worker/ocr_scores.py` — add `score_structured_insert()`.
- Modify: `paperforge/worker/ocr_document.py` — score insert candidates and avoid low-score promotion.
- Modify: `paperforge/worker/ocr_health.py` — count low-confidence and forced insert candidates.
- Test: `tests/test_ocr_scores.py` — scorer unit tests.
- Test: `tests/test_ocr_document.py` — role mutation behavior tests.
- Test: `tests/test_ocr_health.py` — health counts.

---

### Task 1: Add Structured Insert Scorer

**Files:**
- Modify: `tests/test_ocr_scores.py`
- Modify: `paperforge/worker/ocr_scores.py`

- [ ] **Step 1: Write failing scorer tests**

Add to `tests/test_ocr_scores.py`:

```python
def test_structured_insert_score_uses_multiple_evidence_terms() -> None:
    from paperforge.worker.ocr_scores import score_structured_insert

    block = {"text": "Box 1. Key points", "role": "body_paragraph", "_in_visual_container": True, "bbox": [50, 100, 400, 180], "page_width": 1200}

    result = score_structured_insert(block, body_spine_match=False, cluster_coherent=True)

    assert result["decision"] == "structured_insert"
    assert result["score"] >= 0.7
    assert "visual_container" in result["evidence"]
    assert "box_or_summary_keyword" in result["evidence"]


def test_structured_insert_score_keeps_visual_container_alone_as_candidate() -> None:
    from paperforge.worker.ocr_scores import score_structured_insert

    block = {"text": "Ordinary paragraph text", "role": "body_paragraph", "_in_visual_container": True, "bbox": [100, 100, 900, 180], "page_width": 1200}

    result = score_structured_insert(block, body_spine_match=True, cluster_coherent=False)

    assert result["decision"] != "structured_insert"
    assert result["score"] < 0.7
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_scores.py -k structured_insert_score -v --tb=short
```

Expected: FAIL with missing `score_structured_insert`.

- [ ] **Step 3: Implement scorer**

Add to `paperforge/worker/ocr_scores.py`:

```python
def score_structured_insert(
    block: dict,
    *,
    body_spine_match: bool = False,
    cluster_coherent: bool = False,
) -> dict:
    text = str(block.get("text") or block.get("block_content") or "").strip().lower()
    bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
    page_width = float(block.get("page_width") or 1200)
    score = 0.0
    evidence: list[str] = []

    if block.get("_in_visual_container"):
        score += 0.3
        evidence.append("visual_container")
    if re.match(r"^box\s*\.?\s*\d+\b", text) or "key point" in text or text in {"sections", "highlights"}:
        score += 0.3
        evidence.append("box_or_summary_keyword")
    if len(bbox) >= 4 and (bbox[2] - bbox[0]) < page_width * 0.45:
        score += 0.15
        evidence.append("narrow_width")
    if cluster_coherent:
        score += 0.15
        evidence.append("cluster_coherent")
    if body_spine_match:
        score -= 0.25
        evidence.append("body_spine_match")

    score = max(0.0, min(1.0, score))
    if score >= 0.7:
        decision = "structured_insert"
    elif score >= 0.4:
        decision = "structured_insert_candidate"
    else:
        decision = "body"
    return {"score": score, "decision": decision, "evidence": evidence}
```

- [ ] **Step 4: Run scorer tests**

Run:

```bash
python -m pytest tests/test_ocr_scores.py -k structured_insert_score -q --tb=short
```

Expected: PASS.

---

### Task 2: Make Region Prepass Use Insert Score

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `paperforge/worker/ocr_document.py`

- [ ] **Step 1: Write failing visual-container-alone test**

Add to `tests/test_ocr_document.py`:

```python
def test_visual_container_alone_does_not_force_structured_insert() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "Ordinary paragraph", "page": 2, "bbox": [100, 100, 900, 160], "page_width": 1200, "_in_visual_container": True, "_container_bbox": [90, 90, 910, 170]},
    ]

    _doc, normalized = normalize_document_structure(blocks)

    assert normalized[0]["role"] != "structured_insert"
    assert normalized[0].get("insert_score", {}).get("decision") in {"structured_insert_candidate", "body"}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_document.py -k visual_container_alone -v --tb=short
```

Expected: FAIL because region prepass currently treats visual container as strong insert evidence.

- [ ] **Step 3: Import scorer**

In `paperforge/worker/ocr_document.py`, add:

```python
from paperforge.worker.ocr_scores import score_structured_insert
```

- [ ] **Step 4: Store insert score in `_build_region_prepass()`**

Inside `_build_region_prepass()`, before final region assignment, compute:

```python
insert_score = score_structured_insert(block, body_spine_match=False, cluster_coherent=last_insert_on_page)
block["insert_score"] = insert_score
```

Replace direct `region = "structured_insert"` assignments with:

```python
if insert_score["decision"] == "structured_insert":
    region = "structured_insert"
    confidence = insert_score["score"]
elif insert_score["decision"] == "structured_insert_candidate":
    region = "body"
    confidence = insert_score["score"]
```

Keep frontmatter logic unchanged.

- [ ] **Step 5: Run focused document test**

Run:

```bash
python -m pytest tests/test_ocr_document.py -k visual_container_alone -q --tb=short
```

Expected: PASS.

---

### Task 3: Add Insert Health Counts

**Files:**
- Modify: `tests/test_ocr_health.py`
- Modify: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Write failing health test**

Add:

```python
def test_ocr_health_counts_low_confidence_insert_candidates() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=2,
        structured_blocks=[
            {"role": "structured_insert_candidate", "insert_score": {"score": 0.45, "decision": "structured_insert_candidate"}},
            {"role": "structured_insert", "insert_score": {"score": 0.35, "decision": "body"}},
            {"role": "abstract_body"}, {"role": "reference_item"}, {"role": "section_heading"}, {"role": "section_heading"},
        ],
        figure_inventory={},
        table_inventory={},
    )

    assert report["low_confidence_insert_candidate_count"] == 1
    assert report["candidate_forced_count"] == 1
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k low_confidence_insert_candidates -v --tb=short
```

Expected: FAIL with missing metrics.

- [ ] **Step 3: Add health metrics**

In `build_ocr_health()`, add:

```python
low_confidence_insert_candidate_count = sum(
    1 for b in structured_blocks
    if b.get("role") == "structured_insert_candidate" and float(b.get("insert_score", {}).get("score", 0.0)) < 0.7
)
candidate_forced_count = sum(
    1 for b in structured_blocks
    if b.get("role") == "structured_insert" and float(b.get("insert_score", {}).get("score", 1.0)) < 0.7
)
```

Add both values to `report`.

- [ ] **Step 4: Run health test**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k low_confidence_insert_candidates -q --tb=short
```

Expected: PASS.

---

## Verification

Run after all tasks:

```bash
python -m pytest tests/test_ocr_scores.py tests/test_ocr_document.py tests/test_ocr_health.py -q --tb=short
```

Expected: PASS.

Do not commit unless the user explicitly requests a commit.
