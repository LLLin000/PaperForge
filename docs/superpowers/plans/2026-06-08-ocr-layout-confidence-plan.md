# OCR Layout Confidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add layout confidence so low-confidence column detection cannot drive strong reading-order or tail reorder behavior.

**Architecture:** Extend `PageLayoutProfile` with confidence/evidence and build profiles from eligible body-like blocks. Document structure and health should expose confidence; render/order code should treat low confidence as a guard.

**Tech Stack:** Python dataclasses, pytest, OCR document structure JSON.

---

## File Structure

- Modify: `paperforge/worker/ocr_document.py` — profile dataclass, eligible block filtering, confidence scoring, low-confidence guards.
- Modify: `paperforge/worker/ocr_health.py` — layout confidence distribution.
- Test: `tests/test_ocr_document.py` — profile behavior and serialization.
- Test: `tests/test_ocr_health.py` — health metrics.

---

### Task 1: Extend PageLayoutProfile Contract

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `paperforge/worker/ocr_document.py`

- [ ] **Step 1: Write failing profile contract test**

Add to `tests/test_ocr_document.py`:

```python
def test_page_layout_profile_includes_confidence_and_evidence() -> None:
    from paperforge.worker.ocr_document import _build_page_layout_profiles

    blocks = [
        {"role": "body_paragraph", "page": 1, "bbox": [100, 100, 500, 160], "page_width": 1200, "page_height": 1700},
        {"role": "body_paragraph", "page": 1, "bbox": [700, 100, 1100, 160], "page_width": 1200, "page_height": 1700},
    ]

    profile = _build_page_layout_profiles(blocks)[1]

    assert hasattr(profile, "confidence")
    assert hasattr(profile, "evidence")
    assert profile.confidence >= 0.5
    assert "eligible_body_blocks" in profile.evidence
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_document.py -k page_layout_profile_includes_confidence -v --tb=short
```

Expected: FAIL because `PageLayoutProfile` lacks `confidence` and `evidence`.

- [ ] **Step 3: Extend the dataclass**

In `paperforge/worker/ocr_document.py`, update `PageLayoutProfile`:

```python
@dataclass
class PageLayoutProfile:
    column_count: int = 1
    column_boundaries: list[float] = field(default_factory=list)
    layout_type: str = "single_column"
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Update `_classify_page_layout()` returns**

Every `PageLayoutProfile(...)` return should set confidence/evidence. Use these defaults:

```python
PageLayoutProfile(column_count=1, column_boundaries=centers, layout_type="single_column", confidence=0.7, evidence=["eligible_body_blocks"])
```

For mixed or uncertain layouts, use confidence between `0.4` and `0.6` with evidence such as `"wide_dispersion"` or `"two_center_clusters"`.

- [ ] **Step 5: Run focused profile test**

Run:

```bash
python -m pytest tests/test_ocr_document.py -k page_layout_profile_includes_confidence -q --tb=short
```

Expected: PASS.

---

### Task 2: Filter Layout Inputs to Body-Like Blocks

**Files:**
- Modify: `tests/test_ocr_document.py`
- Modify: `paperforge/worker/ocr_document.py`

- [ ] **Step 1: Write failing wide-heading pollution test**

Add:

```python
def test_layout_profiles_ignore_wide_headings_and_media() -> None:
    from paperforge.worker.ocr_document import _build_page_layout_profiles

    blocks = [
        {"role": "section_heading", "page": 1, "bbox": [50, 50, 1150, 90], "page_width": 1200, "page_height": 1700},
        {"role": "figure_asset", "page": 1, "bbox": [400, 120, 800, 500], "page_width": 1200, "page_height": 1700},
        {"role": "body_paragraph", "page": 1, "bbox": [100, 600, 500, 660], "page_width": 1200, "page_height": 1700},
        {"role": "body_paragraph", "page": 1, "bbox": [700, 600, 1100, 660], "page_width": 1200, "page_height": 1700},
    ]

    profile = _build_page_layout_profiles(blocks)[1]

    assert profile.column_count == 2
    assert "excluded_non_body_blocks" in profile.evidence
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_document.py -k ignore_wide_headings -v --tb=short
```

Expected: FAIL if non-body blocks still pollute layout classification.

- [ ] **Step 3: Add eligible layout filter**

In `ocr_document.py`, add:

```python
_LAYOUT_ELIGIBLE_ROLES = {"body_paragraph", "list_item", "tail_candidate_body", "reference_item", "backmatter_body"}


def _is_layout_eligible_block(block: dict) -> bool:
    role = block.get("role", "")
    if role not in _LAYOUT_ELIGIBLE_ROLES:
        return False
    bbox = block.get("bbox") or block.get("block_bbox") or []
    page_width = float(block.get("page_width") or 1200)
    if len(bbox) >= 4 and (bbox[2] - bbox[0]) > page_width * 0.85:
        return False
    return True
```

- [ ] **Step 4: Use the filter in `_build_page_layout_profiles()`**

Before calling `_classify_page_layout()`, build `eligible_blocks`:

```python
eligible_blocks = [block for block in page_blocks if _is_layout_eligible_block(block)]
excluded_count = len(page_blocks) - len(eligible_blocks)
profile = _classify_page_layout(eligible_blocks, page_width, page_height)
if excluded_count:
    profile.evidence.append("excluded_non_body_blocks")
if len(eligible_blocks) < 2:
    profile.confidence = min(profile.confidence, 0.35)
    profile.evidence.append("few_eligible_blocks")
```

- [ ] **Step 5: Run focused layout tests**

Run:

```bash
python -m pytest tests/test_ocr_document.py -k "page_layout_profile_includes_confidence or ignore_wide_headings" -q --tb=short
```

Expected: PASS.

---

### Task 3: Add Health Layout Confidence Distribution

**Files:**
- Modify: `tests/test_ocr_health.py`
- Modify: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Write failing health test**

Add:

```python
def test_ocr_health_reports_layout_confidence_distribution() -> None:
    from paperforge.worker.ocr_document import DocumentStructure, PageLayoutProfile
    from paperforge.worker.ocr_health import build_ocr_health

    doc = DocumentStructure(page_layouts={
        1: PageLayoutProfile(confidence=0.8),
        2: PageLayoutProfile(confidence=0.5),
        3: PageLayoutProfile(confidence=0.2),
    })

    report = build_ocr_health(
        page_count=3,
        raw_blocks_count=3,
        structured_blocks=[{"role": "abstract_body"}, {"role": "reference_item"}, {"role": "section_heading"}, {"role": "section_heading"}],
        figure_inventory={},
        table_inventory={},
        doc_structure=doc,
    )

    assert report["layout_confidence_distribution"] == {"high": 1, "medium": 1, "low": 1}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k layout_confidence_distribution -v --tb=short
```

Expected: FAIL with missing key.

- [ ] **Step 3: Add distribution to health**

In `build_ocr_health()`, after `report` creation, add:

```python
layout_confidences = []
if doc_structure is not None and getattr(doc_structure, "page_layouts", None):
    layout_confidences = [float(p.confidence) for p in doc_structure.page_layouts.values()]
report["layout_confidence_distribution"] = _score_distribution(layout_confidences)
```

Move `_score_distribution()` above this use if it is currently defined later in the function.

- [ ] **Step 4: Run health test**

Run:

```bash
python -m pytest tests/test_ocr_health.py -k layout_confidence_distribution -q --tb=short
```

Expected: PASS.

---

### Task 4: Guard Tail Reorder With Layout and Tail Confidence

**Files:**
- Modify: `tests/test_ocr_rendering.py`
- Modify: `paperforge/worker/ocr_render.py`

- [ ] **Step 1: Write failing low-confidence tail render test**

Add to `tests/test_ocr_rendering.py`:

```python
def test_render_skips_segment_tail_reorder_when_tail_confidence_is_low() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_render import render_fulltext

    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "First tail block", "page": 3, "bbox": [700, 100, 1100, 150]},
        {"block_id": "b2", "role": "body_paragraph", "text": "Second tail block", "page": 3, "bbox": [100, 100, 500, 150]},
    ]
    doc = DocumentStructure(spread_start=3, spread_end=3)
    doc.tail_boundary_score = {"score": 0.2}
    doc.tail_reading_order = [
        {"page": 3, "column_index": 0, "y_top": 100, "y_bottom": 150, "block_indices": [1]},
        {"page": 3, "column_index": 1, "y_top": 100, "y_bottom": 150, "block_indices": [0]},
    ]

    markdown = render_fulltext(blocks, document_structure=doc)

    assert markdown.index("First tail block") < markdown.index("Second tail block")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py -k skips_segment_tail_reorder -v --tb=short
```

Expected: FAIL if renderer still applies `tail_reading_order` when `tail_boundary_score.score < 0.4`.

- [ ] **Step 3: Add confidence guard helper**

In `paperforge/worker/ocr_render.py`, add near `_has_tail_role()`:

```python
def _can_apply_tail_segment_reorder(document_structure: DocumentStructure | None) -> bool:
    if document_structure is None:
        return False
    if not document_structure.tail_reading_order or document_structure.spread_start is None:
        return False
    tail_score = getattr(document_structure, "tail_boundary_score", {}) or {}
    if float(tail_score.get("score", 1.0)) < 0.4:
        return False
    page_layouts = getattr(document_structure, "page_layouts", None) or {}
    for page in range(document_structure.spread_start, (document_structure.spread_end or document_structure.spread_start) + 1):
        profile = page_layouts.get(page)
        if profile is not None and float(getattr(profile, "confidence", 1.0)) < 0.4:
            return False
    return True
```

- [ ] **Step 4: Use the guard in render ordering**

Replace this condition in `render_fulltext()`:

```python
if document_structure and document_structure.tail_reading_order and document_structure.spread_start is not None:
```

with:

```python
if _can_apply_tail_segment_reorder(document_structure):
```

- [ ] **Step 5: Run focused render test**

Run:

```bash
python -m pytest tests/test_ocr_rendering.py -k skips_segment_tail_reorder -q --tb=short
```

Expected: PASS.

---

## Verification

Run after all tasks:

```bash
python -m pytest tests/test_ocr_document.py tests/test_ocr_health.py tests/test_ocr_rendering.py -q --tb=short
```

Expected: PASS.

Do not commit unless the user explicitly requests a commit.
