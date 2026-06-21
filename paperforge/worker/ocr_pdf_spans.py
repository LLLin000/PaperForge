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


def _extract_visual_container_rects(page: Any) -> list:
    """Extract visible rectangle regions (filled or bordered) from a PDF page.

    Uses PyMuPDF's ``get_drawings()`` to find rectangles with:
    - noticeable fill color (not white/transparent), OR
    - visible border/outline

    Returns list of fitz.Rect objects for each detected container.
    """

    rects: list = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return rects

    for drawing in drawings:
        fill = drawing.get("fill")
        color = drawing.get("color")
        stroke_width = drawing.get("width", 0) or 0
        rect = drawing.get("rect")
        if not rect:
            continue

        if rect.width < 100 or rect.height < 50:
            continue

        is_filled = False
        if fill and len(fill) >= 3:
            r, g, b = fill[0], fill[1], fill[2]
            brightness = (r + g + b) / 3
            is_filled = brightness < 0.95

        has_border = bool(color) and (isinstance(color, (list, tuple))) and stroke_width > 0

        if is_filled or has_border:
            rects.append(rect)

    return rects


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
        by_page_containers: dict[int, list] = {}
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

        import fitz
        for block in raw_blocks:
            page_num = block.get("page", 1) - 1
            bbox = block.get("bbox", [])
            if not bbox or len(bbox) < 4:
                continue
            if page_num not in by_page_containers:
                try:
                    pdf_page = doc[page_num]
                    by_page_containers[page_num] = _extract_visual_container_rects(pdf_page)
                except Exception:
                    by_page_containers[page_num] = []
            containers = by_page_containers[page_num]
            if not containers:
                continue
            pw = block.get("page_width") or block.get("ocr_width") or 0
            ph = block.get("page_height") or block.get("ocr_height") or 0
            if pw <= 0 or ph <= 0:
                try:
                    pdf_rect = doc[page_num].rect
                    pw = int(pdf_rect.width * 2) if pdf_rect.width > 0 else 1200
                    ph = int(pdf_rect.height * 2) if pdf_rect.height > 0 else 1700
                except Exception:
                    pw, ph = 1200, 1700
            if pw > 0 and ph > 0:
                try:
                    pdf_page = doc[page_num]
                    block_rect = _map_ocr_bbox_to_pdf_rect(bbox, pw, ph, pdf_page)
                except Exception:
                    continue
            else:
                block_rect = fitz.Rect(*bbox)
            for container_rect in containers:
                if block_rect.x0 > container_rect.x1 or block_rect.x1 < container_rect.x0:
                    continue
                if block_rect.y0 > container_rect.y1 or block_rect.y1 < container_rect.y0:
                    continue
                overlap_w = min(block_rect.x1, container_rect.x1) - max(block_rect.x0, container_rect.x0)
                overlap_h = min(block_rect.y1, container_rect.y1) - max(block_rect.y0, container_rect.y0)
                if overlap_w > 0 and overlap_h > 0:
                    block_w = block_rect.x1 - block_rect.x0
                    block_h = block_rect.y1 - block_rect.y0
                    overlap_area = overlap_w * overlap_h
                    block_area = block_w * block_h if block_w > 0 and block_h > 0 else 0
                    if block_area > 0 and overlap_area / block_area >= 0.3:
                        block["_in_visual_container"] = True
                        container_overlap_ratio = overlap_area / block_area
                        pw = block.get("page_width") or 0
                        ph = block.get("page_height") or 0
                        pdf_page_rect = doc[page_num].rect
                        scale_x = pw / pdf_page_rect.width if (pw and pdf_page_rect.width) else 1
                        scale_y = ph / pdf_page_rect.height if (ph and pdf_page_rect.height) else 1
                        block["_container_bbox"] = [
                            container_rect.x0 * scale_x,
                            container_rect.y0 * scale_y,
                            container_rect.x1 * scale_x,
                            container_rect.y1 * scale_y,
                        ]

                        in_container_parts: list[str] = []
                        pdf_page_for_text = doc[page_num]
                        block_pdf_rect = _map_ocr_bbox_to_pdf_rect(bbox, pw, ph, pdf_page_for_text) if pw and ph else None
                        for tblock in pdf_page_for_text.get_text("blocks"):
                            tx0, ty0, tx1, ty1, ttext, *_ = tblock
                            ttext = (ttext or "").strip()
                            if not ttext:
                                continue
                            in_container = (
                                max(tx0, container_rect.x0) < min(tx1, container_rect.x1)
                                and max(ty0, container_rect.y0) < min(ty1, container_rect.y1)
                            )
                            if not in_container:
                                continue
                            if block_pdf_rect:
                                in_block = (
                                    max(tx0, block_pdf_rect.x0) < min(tx1, block_pdf_rect.x1)
                                    and max(ty0, block_pdf_rect.y0) < min(ty1, block_pdf_rect.y1)
                                )
                                if not in_block:
                                    continue
                            in_container_parts.append(ttext)
                        if in_container_parts and container_overlap_ratio > 0.7:
                            container_text = "\n".join(in_container_parts)
                            block_text = str(block.get("text") or "")
                            if container_text and len(container_text) < len(block_text) * 0.8:
                                block["_container_text"] = container_text
                        break
    finally:
        doc.close()

    return raw_blocks


def _words_to_text(words: list[tuple]) -> str:
    """Convert fitz word tuples to reading-order text with line breaks.

    Each word tuple is (x0, y0, x1, y1, text, block_no, line_no, word_no).
    Groups words by y-position into lines, sorts within lines by x.
    """
    if not words:
        return ""

    # Sort by y-bucket then x
    words = sorted(words, key=lambda w: (round(w[1] / 3), w[0]))

    lines: list[str] = []
    current_words: list[tuple[float, str]] = []
    current_y: float | None = None

    for w in words:
        x0, y0, text = w[0], w[1], str(w[4]).strip()
        if not text:
            continue

        if current_y is None or abs(y0 - current_y) <= 3:
            current_words.append((x0, text))
            current_y = y0 if current_y is None else current_y
        else:
            if current_words:
                lines.append(" ".join(t for _, t in sorted(current_words)))
            current_words = [(x0, text)]
            current_y = y0

    if current_words:
        lines.append(" ".join(t for _, t in sorted(current_words)))

    return "\n".join(line.strip() for line in lines if line.strip()).strip()


TEXT_LIKE_RAW_LABELS = frozenset({"text"})


def backfill_missing_text_from_pdf(
    raw_blocks: list[dict],
    pdf_path: str | Path | None,
) -> list[dict]:
    """Fill empty-text blocks from source PDF embedded text layer.

    Trigger: raw_label == "text" AND text/block_content empty
             AND span_metadata has PDF-derived font evidence
             AND page dimensions are available for bbox mapping.

    Extracts text via words-level fitz API with clip-constrained bbox.
    Does NOT use intersecting-blocks fallback (too coarse for multi-column).

    Sets _ocr_raw_status and _ocr_raw_error_type on every processed block.
    Returns mutated blocks list.
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
        recovered = 0
        unrecovered = 0
        no_layer = 0

        for block in raw_blocks:
            raw_label = str(block.get("raw_label") or "")
            if raw_label not in TEXT_LIKE_RAW_LABELS:
                continue

            current_text = str(
                block.get("text")
                or block.get("block_content")
                or ""
            ).strip()
            # Ponytail: "text" field may be JSON list [] from raw block format,
            # not a string. str([]) → "[]" which is truthy but has no real text.
            # Detect and treat as empty.
            if current_text and current_text not in ("[]", "[ ]"):
                continue

            # Guard: must have span_metadata as PDF evidence
            spans = block.get("span_metadata")
            if not spans or not isinstance(spans, list) or len(spans) == 0:
                continue

            page_index = int(block.get("page", 1)) - 1
            if page_index < 0 or page_index >= len(doc):
                block["_ocr_raw_status"] = "missing_text_unrecovered"
                block["_ocr_raw_error_type"] = "invalid_page_index"
                unrecovered += 1
                continue

            bbox = block.get("bbox") or block.get("block_bbox")
            if not bbox or len(bbox) < 4:
                block["_ocr_raw_status"] = "missing_text_unrecovered"
                block["_ocr_raw_error_type"] = "missing_bbox"
                unrecovered += 1
                continue

            page_width = float(block.get("page_width") or 0)
            page_height = float(block.get("page_height") or 0)
            if page_width <= 0 or page_height <= 0:
                block["_ocr_raw_status"] = "missing_text_unrecovered"
                block["_ocr_raw_error_type"] = "missing_page_dimensions"
                unrecovered += 1
                continue

            pdf_page = doc[page_index]

            try:
                rect = _map_ocr_bbox_to_pdf_rect(
                    bbox, page_width, page_height, pdf_page
                )
            except Exception:
                block["_ocr_raw_status"] = "missing_text_unrecovered"
                block["_ocr_raw_error_type"] = "bbox_mapping_failed"
                unrecovered += 1
                continue

            if rect.is_empty or rect.width <= 0 or rect.height <= 0:
                block["_ocr_raw_status"] = "missing_text_unrecovered"
                block["_ocr_raw_error_type"] = "empty_rect"
                unrecovered += 1
                continue

            # Expand rect slightly to account for OCR-PDF alignment drift
            pad_x = max(1.0, rect.width * 0.01)
            pad_y = max(1.0, rect.height * 0.05)
            expanded = fitz.Rect(
                rect.x0 - pad_x,
                rect.y0 - pad_y,
                rect.x1 + pad_x,
                rect.y1 + pad_y,
            ) & pdf_page.rect

            try:
                words = pdf_page.get_text("words", clip=expanded)
            except Exception:
                words = []

            text = _words_to_text(words)

            if text:
                block["_original_ocr_text"] = ""
                block["text"] = text
                block["block_content"] = text
                block["_text_source"] = "pdf_text_layer_fallback"
                block["_ocr_raw_status"] = "missing_text_recovered"
                block["_ocr_raw_error_type"] = "empty_text_with_pdf_evidence"
                block["role"] = "body_paragraph"
                recovered += 1
            else:
                try:
                    page_text = pdf_page.get_text("text").strip()
                except Exception:
                    page_text = ""
                if not page_text:
                    block["_ocr_raw_status"] = "missing_text_unrecovered"
                    block["_ocr_raw_error_type"] = "no_pdf_text_layer"
                    no_layer += 1
                else:
                    block["_ocr_raw_status"] = "missing_text_unrecovered"
                    block["_ocr_raw_error_type"] = "empty_text_with_pdf_evidence"
                    block["_text_error"] = "pdf_words_empty"
                unrecovered += 1

    finally:
        doc.close()

    return raw_blocks
