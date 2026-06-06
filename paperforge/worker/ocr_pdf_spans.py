"""PDF font span extraction using PyMuPDF.

Extracts per-character font metadata (size, font family, bold/italic flags,
color) from the source PDF at each block's bounding box position.

This is the single source of truth for span_metadata — NOT the OCR engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _map_ocr_bbox_to_pdf_rect(
    bbox: list[float],
    page_width: float,
    page_height: float,
    pdf_page: Any,
) -> Any:
    """Scale OCR-space bbox to PDF-space fitz.Rect.

    OCR bboxes come from rendered page images; PDF coordinates may
    differ.  Scales by the ratio of PDF page dimensions to OCR image
    dimensions.
    """
    import fitz

    pdf_rect = pdf_page.rect
    scale_x = pdf_rect.width / page_width if page_width else 1.0
    scale_y = pdf_rect.height / page_height if page_height else 1.0
    return fitz.Rect(
        bbox[0] * scale_x,
        bbox[1] * scale_y,
        bbox[2] * scale_x,
        bbox[3] * scale_y,
    )


def extract_pdf_spans_for_block(
    pdf_doc: Any,
    page_num: int,
    bbox: list[float],
    page_width: float | None = None,
    page_height: float | None = None,
) -> list[dict] | None:
    """Extract per-character span metadata from a PDF at a given bbox.

    Args:
        pdf_doc: An open fitz.Document.
        page_num: 0-indexed page number.
        bbox: [x1, y1, x2, y2] in OCR (or PDF) coordinates.
        page_width: OCR image width for scaling to PDF space.
        page_height: OCR image height for scaling to PDF space.

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
        if page_width and page_height and page_width > 0 and page_height > 0:
            rect = _map_ocr_bbox_to_pdf_rect(bbox, page_width, page_height, page)
        else:
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
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                size = span.get("size")
                if size is None:
                    continue
                flags = span.get("flags", 0)
                if not isinstance(flags, int):
                    flags = 0
                spans.append(
                    {
                        "size": float(size),
                        "font": str(span.get("font", "")),
                        "flags": flags,
                        "color": int(span.get("color", 0)),
                    }
                )

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
            page_num = block.get("page", 1) - 1
            bbox = block.get("bbox", [])
            if not bbox or len(bbox) < 4:
                continue
            spans = extract_pdf_spans_for_block(
                doc,
                page_num,
                bbox,
                page_width=block.get("page_width"),
                page_height=block.get("page_height"),
            )
            if spans:
                block["span_metadata"] = spans
    finally:
        doc.close()

    return raw_blocks
