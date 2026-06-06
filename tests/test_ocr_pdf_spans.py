"""Tests for PDF font span extraction."""

from __future__ import annotations


def test_extract_pdf_spans_for_block_returns_spans() -> None:
    """Extract spans from a known PDF block position."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(50, 100), "Hello World",
                     fontname="helv", fontsize=14, color=(0, 0, 0))

    spans = extract_pdf_spans_for_block(doc, 0, [40, 80, 200, 120])
    assert spans is not None
    assert len(spans) >= 1
    sizes = [s["size"] for s in spans]
    assert any(abs(s - 14) < 1 for s in sizes)
    fonts = [s["font"] for s in spans if s.get("font")]
    assert any("Helv" in f or "helv" in f.lower() for f in fonts)


def test_extract_pdf_spans_empty_bbox() -> None:
    """Empty bbox should return None."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 0, [0, 0, 0, 0])
    assert spans is None


def test_extract_pdf_spans_outside_page() -> None:
    """Outside-page bbox should return None."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 0, [-100, -100, -50, -50])
    assert spans is None or spans == []


def test_extract_pdf_spans_invalid_page() -> None:
    """Invalid page number should return None gracefully."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 99, [0, 0, 100, 100])
    assert spans is None


def test_extract_pdf_spans_invalid_doc() -> None:
    """Closed doc should return None gracefully."""
    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block
    import fitz

    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.close()

    spans = extract_pdf_spans_for_block(doc, 0, [0, 0, 100, 100])
    assert spans is None


def test_backfill_span_metadata_no_pdf() -> None:
    """Missing PDF path should leave blocks unchanged."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    blocks = [{"page": 1, "bbox": [0, 0, 100, 50], "text": "test"}]
    result = backfill_span_metadata_from_pdf(blocks, None)
    result[0].get("span_metadata") is None


def test_backfill_span_metadata_bad_path() -> None:
    """Non-existent PDF path should leave blocks unchanged."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    blocks = [{"page": 1, "bbox": [0, 0, 100, 50], "text": "test"}]
    result = backfill_span_metadata_from_pdf(blocks, "/nonexistent/pdf.pdf")
    result[0].get("span_metadata") is None


def test_backfill_span_metadata_with_real_pdf() -> None:
    """Real PDF should produce span_metadata on blocks."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf
    import fitz
    import tempfile
    from pathlib import Path

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(50, 100), "Test Title",
                     fontname="helv", fontsize=16, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 200), "Body text here",
                     fontname="helv", fontsize=10, color=(0, 0, 0))

    tmp = Path(tempfile.mktemp(suffix=".pdf"))
    doc.save(str(tmp))
    doc.close()

    blocks = [
        {"page": 1, "bbox": [40, 80, 200, 120], "text": "Test Title"},
        {"page": 1, "bbox": [40, 180, 250, 220], "text": "Body text here"},
        {"page": 1, "bbox": [0, 0, 10, 10], "text": "empty"},
    ]
    try:
        result = backfill_span_metadata_from_pdf(blocks, tmp)
        assert result[0].get("span_metadata") is not None
        assert result[1].get("span_metadata") is not None
        assert result[2].get("span_metadata") is None
    finally:
        tmp.unlink(missing_ok=True)
