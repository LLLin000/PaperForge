# OCR Span Metadata Integration Plan (Revised)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build persistent span_metadata pipeline extracted from source PDF, used for cross-validation role refinement.

**Architecture:** Span metadata is extracted from the source PDF using each block's bbox position (PyMuPDF `fitz`), not from the OCR engine. Pipeline: PaddleOCR bbox → PDF font extraction → raw blocks → structured blocks → role profiles → cross-validation. Existing OCR outputs are retroactively backfillable.

**Tech Stack:** Python 3.x, PyMuPDF (fitz), PaddleOCR block JSON structure, existing PaperForge worker pipeline (`ocr_blocks.py`, `ocr_roles.py`, `ocr_render.py`, `ocr_rebuild.py`)

**Spec:** `docs/superpowers/specs/2026-06-06-ocr-unified-span-metadata-design.md`

**Status:** Tasks 2-6 are already implemented and committed. Only Task 1 (PDF font extraction) is new. Tasks 7-8 are future work.

---

### Task 1: PDF Font Extraction Module

**Files:**
- Create: `paperforge/worker/ocr_pdf_spans.py`
- Modify: `paperforge/worker/ocr_blocks.py` (revert Paddle passthrough, keep structured carry-through)
- Modify: `paperforge/worker/ocr_rebuild.py` (wire PDF extraction into rebuild pipeline)
- Modify: `paperforge/worker/ocr.py` (wire PDF extraction into OCR pipeline)
- Modify: `tests/test_ocr_blocks.py` (replace Paddle passthrough test with PDF extraction test)

This task replaces the old assumption that `span_metadata` comes from PaddleOCR. Instead, a new module extracts font information from the PDF using each block's bbox.

- [ ] **Step 1: Revert Paddle passthrough in `build_raw_blocks_for_page`**

Remove `"span_metadata": block.get("span_metadata")` from `build_raw_blocks_for_page` (currently line 93 of `ocr_blocks.py`). Raw blocks should NOT carry span_metadata from PaddleOCR — that field is often absent and architecturally wrong.

Also remove the test `test_build_raw_blocks_preserves_span_metadata` from `test_ocr_blocks.py` — it tests the wrong source.

- [ ] **Step 2: Write failing test for PDF span extraction**

Create `tests/test_ocr_pdf_spans.py`:

```python
"""Tests for PDF font span extraction."""

from __future__ import annotations


def test_extract_pdf_spans_for_block_returns_spans() -> None:
    """Extract spans from a known PDF block position."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    # Create a minimal in-memory PDF with known text
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(50, 100), "Hello World",
                     fontname="helv", fontsize=14, color=(0, 0, 0))

    spans = extract_pdf_spans_for_block(doc, 0, [40, 80, 200, 120])
    assert spans is not None
    assert len(spans) >= 1
    # At least one span should have the expected properties
    sizes = [s["size"] for s in spans]
    assert any(abs(s - 14) < 1 for s in sizes)
    # Flags should indicate at least bold-relevant bits (helv is not bold)
    # The font name should be extractable
    fonts = [s["font"] for s in spans if s.get("font")]
    assert any("Helv" in f or "helv" in f.lower() for f in fonts)


def test_extract_pdf_spans_outside_page() -> None:
    """Outside-page bbox should return None gracefully."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 0, [-100, -100, -50, -50])
    assert spans is None or spans == []


def test_extract_pdf_spans_invalid_page() -> None:
    """Invalid page number should return None."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 99, [0, 0, 100, 100])
    assert spans is None


def test_backfill_span_metadata_no_pdf() -> None:
    """Missing PDF path should leave blocks unchanged."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    blocks = [{"page": 1, "bbox": [0, 0, 100, 50], "text": "test"}]
    result = backfill_span_metadata_from_pdf(blocks, None)
    assert result == blocks
    assert result[0].get("span_metadata") is None


def test_backfill_span_metadata_bad_path() -> None:
    """Non-existent PDF path should leave blocks unchanged."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    blocks = [{"page": 1, "bbox": [0, 0, 100, 50], "text": "test"}]
    result = backfill_span_metadata_from_pdf(blocks, "/nonexistent/pdf.pdf")
    assert result == blocks
    assert result[0].get("span_metadata") is None
```

Run: `pytest tests/test_ocr_pdf_spans.py -v`
Expected: 5 FAILED

- [ ] **Step 3: Implement `extract_pdf_spans_for_block`**

Create `paperforge/worker/ocr_pdf_spans.py`:

```python
"""PDF font span extraction using PyMuPDF.

Extracts per-character font metadata (size, font family, bold/italic flags,
color) from the source PDF at each block's bounding box position.

This is the single source of truth for span_metadata — NOT the OCR engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_pdf_spans_for_block(
    pdf_doc: Any,
    page_num: int,
    bbox: list[float],
) -> list[dict] | None:
    """Extract per-character span metadata from a PDF at a given bbox.

    Args:
        pdf_doc: An open fitz.Document.
        page_num: 0-indexed page number.
        bbox: [x1, y1, x2, y2] in PDF coordinates.

    Returns:
        List of per-character span dicts, or None if extraction fails.
        Each span: {"size": float, "font": str, "flags": int, "color": int}
    """
    import fitz

    try:
        if page_num < 0 or page_num >= len(pdf_doc):
            return None
        page = pdf_doc[page_num]
    except Exception:
        return None

    if not bbox or len(bbox) < 4:
        return None

    try:
        rect = fitz.Rect(*bbox)
    except Exception:
        return None

    if rect.is_empty or rect.width <= 0 or rect.height <= 0:
        return None

    try:
        tp = page.get_text("rawdict", clip=rect)
    except Exception:
        return None

    spans: list[dict] = []
    for block in tp.get("blocks", []):
        if block.get("type") != 0:  # 0 = text block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size")
                if size is None:
                    continue
                flags = span.get("flags", 0)
                if not isinstance(flags, int):
                    flags = 0
                # Normalize flags: existing extract_block_span_profile
                # checks flags & 16 for bold (fitz: bit 4 = bold, same value)
                # and flags & 4 for italic (fitz: bit 1 = italic, different bit)
                # We keep fitz flags as-is — extract_block_span_profile handles
                # the interpretation differently per format
                spans.append({
                    "size": float(size),
                    "font": str(span.get("font", "")),
                    "flags": flags,
                    "color": int(span.get("color", 0)),
                })

    return spans if spans else None


def backfill_span_metadata_from_pdf(
    raw_blocks: list[dict],
    pdf_path: str | Path | None,
) -> list[dict]:
    """Backfill span_metadata for raw blocks from the source PDF.

    Iterates all blocks, extracts per-character font info from the PDF
    at each block's bbox, and writes it as span_metadata.

    Returns the modified blocks list (mutated in-place for efficiency).
    Gracefully handles missing PDFs, invalid bboxes, and extraction failures.
    """
    if not pdf_path:
        return raw_blocks

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return raw_blocks

    import fitz

    try:
        doc = fitz.open(str(pdf_path))
    except Exception:
        return raw_blocks

    try:
        for block in raw_blocks:
            page_num = block.get("page", 1) - 1  # Convert 1-indexed to 0-indexed
            bbox = block.get("bbox", [])
            if not bbox or len(bbox) < 4:
                continue
            spans = extract_pdf_spans_for_block(doc, page_num, bbox)
            if spans:
                block["span_metadata"] = spans
    finally:
        doc.close()

    return raw_blocks
```

- [ ] **Step 4: Run PDF extraction tests to verify pass**

Run: `pytest tests/test_ocr_pdf_spans.py -v`
Expected: 5 PASSED

- [ ] **Step 5: Update pipeline wiring — `build_structured_blocks` keeps carry-through**

Keep `"span_metadata": block.get("span_metadata")` in `build_structured_blocks` (already present at line 59). The structured blocks still carry span_metadata — the source has just moved from PaddleOCR to PDF extraction.

- [ ] **Step 6: Wire PDF extraction into `postprocess_ocr_result` in `ocr.py`**

In `postprocess_ocr_result` (around line 1754-1756), after `write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)` and BEFORE `build_structured_blocks`, add PDF extraction:

```python
    # Backfill span_metadata from source PDF (not from OCR engine)
    resolved_pdf = resolve_pdf_path(source_meta, vault)
    if resolved_pdf:
        from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf
        backfill_span_metadata_from_pdf(all_raw_blocks, resolved_pdf)
        # Re-write raw blocks with span_metadata
        write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)
```

The `resolve_pdf_path` function already exists in the pipeline — it resolves the `source_pdf` path from storage.

- [ ] **Step 7: Wire PDF extraction into `run_derived_rebuild_for_keys` in `ocr_rebuild.py`**

In `run_derived_rebuild_for_keys` (around line 56-62), after reading raw blocks and BEFORE `build_structured_blocks`:

```python
    # Backfill span_metadata from source PDF
    source_meta_path = artifacts.source_metadata
    if source_meta_path.exists():
        source_meta = read_json(source_meta_path)
        pdf_path = resolve_source_pdf(source_meta, paper_root)
        if pdf_path:
            from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf
            backfill_span_metadata_from_pdf(all_raw_blocks, pdf_path)
            # Re-write raw blocks with span_metadata
            write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)
```

- [ ] **Step 8: Update span_metadata test in structured blocks**

Keep `test_build_structured_blocks_carries_span_metadata` — it verifies structured blocks carry through whatever span_metadata they receive, regardless of source.

Update the test to explicitly pass span_metadata in raw blocks (since raw now gets it from PDF extraction, not PaddleOCR passthrough):

```python
def test_build_structured_blocks_carries_span_metadata() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks
    span_data = [{"size": 14.0, "font": "Times-Bold", "flags": 16, "color": 0}]
    raw_blocks = [{
        "paper_id": "KEY001", "page": 1, "block_id": "p1_b1",
        "raw_label": "paragraph_title", "raw_order": 0,
        "bbox": [1,2,3,4], "text": "Methods", "page_width": 1200, "page_height": 1600,
        "source": "ocr_raw", "span_metadata": span_data,
    }]
    rows = build_structured_blocks(raw_blocks)
    assert rows[0]["span_metadata"] == span_data
```

- [ ] **Step 9: Run full test suite**

Run: `python -m pytest tests/test_ocr_pdf_spans.py tests/test_ocr_blocks.py tests/test_ocr_profiles.py -v --tb=short`
Expected: all pass

Run: `python -m pytest tests/unit/ tests/cli/ -v --tb=short -x`
Expected: all pass

- [ ] **Step 10: Commit**

```bash
git add paperforge/worker/ocr_pdf_spans.py tests/test_ocr_pdf_spans.py paperforge/worker/ocr_blocks.py tests/test_ocr_blocks.py paperforge/worker/ocr.py paperforge/worker/ocr_rebuild.py
git commit -m "feat: extract span_metadata from source PDF using PyMuPDF, revert PaddleOCR passthrough"
```

---

### Task 2: span_metadata Carry-Through (Already Implemented)

**Commit:** `ef08912`

`build_structured_blocks` in `ocr_blocks.py` carries `span_metadata` from raw blocks to structured output. No changes needed — the pass-through is correct regardless of source.

---

### Task 3: Profile Infrastructure (Already Implemented)

**Commit:** `24f3e31`, `fc600fa`

`paperforge/worker/ocr_profiles.py` with:
- `extract_block_span_profile` — handles both list format (from PDF) and dict format (legacy test data)
- `build_role_span_profiles` — aggregates per-role style profiles
- `compare_against_role_family` — block vs. family comparison
- `cross_validate_with_span` — confidence adjustment
- `write_role_span_profiles` — persistence

---

### Task 4: Profile Persistence (Already Implemented)

**Commit:** `0ab9f7d`

`role_span_profiles.json` is written in both `ocr.py:postprocess_ocr_result` and `ocr_rebuild.py:run_derived_rebuild_for_keys`.

---

### Task 5: Dynamic Heading Family Discovery (Already Implemented)

**Commit:** `f6b7f8b`, `976a073`

Hardcoded font-size thresholds removed from `_infer_heading_level`, `_is_backmatter_boundary_heading`, heading fallback. Profile-based matching using `compare_against_role_family`.

---

### Task 6: Second-Pass Cross-Validation (Already Implemented)

**Commit:** `fbc5de6`

`second_pass_cross_validate` function in `ocr_roles.py`. Two-pass approach in `build_structured_blocks`.

---

### Task 7: Frontmatter Noise Zone+Style Refactor (Future)

Not yet implemented. Key changes:
- Zone gate: restrict phrase-only frontmatter matches to page 1 or page margins
- Use `compare_against_role_family` vs body profile to validate font size difference
- Remove hardcoded phrase matching outside page 1

---

### Spec Coverage

| Requirement | Task |
|---|---|
| span_metadata extracted from PDF (not OCR) | Task 1 |
| span_metadata preserved through structured layer | Task 2 |
| `role_span_profiles.json` with profile quality | Task 4 |
| heading families discovered dynamically | Task 5 |
| unnumbered heading uses family matching | Task 5 |
| backmatter boundary no longer depends on absolute page | Task 5 |
| second-pass cross-validation for low-confidence blocks | Task 6 |
| zero span data → near-zero behavior change | Task 1 (None return) |
| retroactive backfill for existing papers | Task 1 (rebuild wiring) |
| reference_item family consistency | (future — deeper revalidate) |
| frontmatter_noise zone+style driven | Task 7 (future) |
