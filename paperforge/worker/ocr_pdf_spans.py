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
            page_num = block.get("page", 1) - 1
            bbox = block.get("bbox", [])
            if not bbox or len(bbox) < 4:
                continue
            spans = extract_pdf_spans_for_block(doc, page_num, bbox)
            if spans:
                block["span_metadata"] = spans
    finally:
        doc.close()

    return raw_blocks
