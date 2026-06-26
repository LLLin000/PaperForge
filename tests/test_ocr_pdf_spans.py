"""Tests for PDF font span extraction."""

from __future__ import annotations


def test_extract_pdf_spans_for_block_returns_spans() -> None:
    """Extract spans from a known PDF block position."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(50, 100), "Hello World", fontname="helv", fontsize=14, color=(0, 0, 0))

    spans = extract_pdf_spans_for_block(doc, 0, [40, 80, 200, 120])
    assert spans is not None
    assert len(spans) >= 1
    sizes = [s["size"] for s in spans]
    assert any(abs(s - 14) < 1 for s in sizes)
    fonts = [s["font"] for s in spans if s.get("font")]
    assert any("Helv" in f or "helv" in f.lower() for f in fonts)


def test_extract_pdf_spans_empty_bbox() -> None:
    """Empty bbox should return None."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 0, [0, 0, 0, 0])
    assert spans is None


def test_extract_pdf_spans_outside_page() -> None:
    """Outside-page bbox should return None."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 0, [-100, -100, -50, -50])
    assert spans is None or spans == []


def test_extract_pdf_spans_invalid_page() -> None:
    """Invalid page number should return None gracefully."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    doc.new_page(width=612, height=792)

    spans = extract_pdf_spans_for_block(doc, 99, [0, 0, 100, 100])
    assert spans is None


def test_extract_pdf_spans_invalid_doc() -> None:
    """Closed doc should return None gracefully."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.close()

    spans = extract_pdf_spans_for_block(doc, 0, [0, 0, 100, 100])
    assert spans is None


def test_extract_pdf_spans_mapped_coordinates() -> None:
    """OCR bbox at 2x scale should be correctly mapped to PDF coords."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 100), "Mapped Text", fontname="helv", fontsize=14)

    # OCR bbox at 2x scale (OCR dims: 1190x1684, PDF dims: 595x842)
    ocr_bbox = [100, 200, 300, 250]

    spans = extract_pdf_spans_for_block(doc, 0, ocr_bbox, page_width=1190, page_height=1684)
    assert spans is not None
    assert len(spans) >= 1


def test_extract_pdf_spans_mapped_coordinates_fallback() -> None:
    """Without page_width/page_height, use direct bbox (backward compat)."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import extract_pdf_spans_for_block

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(50, 100), "Direct", fontname="helv", fontsize=14)

    spans = extract_pdf_spans_for_block(doc, 0, [40, 80, 120, 120])
    assert spans is not None


def test_backfill_span_metadata_no_pdf() -> None:
    """Missing PDF path should leave blocks unchanged."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    blocks = [{"page": 1, "bbox": [0, 0, 100, 50], "text": "test"}]
    result = backfill_span_metadata_from_pdf(blocks, None)
    assert result[0].get("span_metadata") is None


def test_backfill_span_metadata_bad_path() -> None:
    """Non-existent PDF path should leave blocks unchanged."""
    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    blocks = [{"page": 1, "bbox": [0, 0, 100, 50], "text": "test"}]
    result = backfill_span_metadata_from_pdf(blocks, "/nonexistent/pdf.pdf")
    assert result[0].get("span_metadata") is None


def test_extract_visual_container_detects_filled_box() -> None:
    """A small filled blue box should be detected as a container."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import _extract_visual_container_rects

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Draw a filled blue rectangle (simulating "Available With This Article" box)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(400, 600, 550, 650))
    shape.finish(fill=(0, 0.35, 0.6), color=None, width=0)
    shape.commit()

    rects = _extract_visual_container_rects(page)
    doc.close()

    assert len(rects) == 1
    assert rects[0].x0 == 400
    assert rects[0].y0 == 600


def test_extract_visual_container_skips_thin_large_decoration() -> None:
    """A thin 0.5pt border covering >50% of page (page decoration) should NOT be detected."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import _extract_visual_container_rects

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Draw a thin 0.5pt border rectangle covering most of the page
    # (simulating the N6XCZD25 false positive)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(50, 70, 543, 738))
    shape.finish(fill=None, color=(0.13, 0.12, 0.12), width=0.5)
    shape.commit()

    rects = _extract_visual_container_rects(page)
    doc.close()

    assert len(rects) == 0, f"Expected 0, got {len(rects)}: page decoration should be filtered"


def test_extract_visual_container_detects_thick_border_box() -> None:
    """A thick-border unfilled rectangle should still be detected."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import _extract_visual_container_rects

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Draw a thick 3pt border rectangle (real callout box)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(400, 600, 550, 650))
    shape.finish(fill=None, color=(0, 0, 0), width=3.0)
    shape.commit()

    rects = _extract_visual_container_rects(page)
    doc.close()

    assert len(rects) == 1, "Thick border box should be detected"


def test_extract_visual_container_skips_small_thin_border() -> None:
    """A small thin-border rectangle below min size should be skipped."""
    import fitz

    from paperforge.worker.ocr_pdf_spans import _extract_visual_container_rects

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(100, 100, 150, 130))  # 50x30 < 100x50 minimum
    shape.finish(fill=(1, 0, 0), color=None, width=0)
    shape.commit()

    rects = _extract_visual_container_rects(page)
    doc.close()

    assert len(rects) == 0, "Sub-minimum rect should be skipped"


def test_backfill_span_metadata_with_real_pdf() -> None:
    """Real PDF should produce span_metadata on blocks."""
    import tempfile
    from pathlib import Path

    import fitz

    from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(fitz.Point(50, 100), "Test Title", fontname="helv", fontsize=16, color=(0, 0, 0))
    page.insert_text(fitz.Point(50, 200), "Body text here", fontname="helv", fontsize=10, color=(0, 0, 0))

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
