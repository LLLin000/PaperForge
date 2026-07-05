"""PDF font span extraction using PyMuPDF.

Extracts per-character font metadata (size, font family, bold/italic flags,
color) from the source PDF at each block's bounding box position.

This is the single source of truth for span_metadata — NOT the OCR engine.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import fitz

import os as _os
from contextlib import redirect_stderr as _redirect_stderr


def _fitz_quiet_open(path: str):
    with _redirect_stderr(_os.devnull):
        return fitz.open(path)


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

def _rect_from_bbox(bbox) -> fitz.Rect | None:
    """Convert a 4-element bbox to fitz.Rect, returning None for invalid input."""
    if not bbox or len(bbox) < 4:
        return None
    try:
        rect = fitz.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except Exception:
        return None
    if rect.is_empty or rect.width <= 0 or rect.height <= 0:
        return None
    return rect


def _char_center_hits_rect(char: dict, rect: fitz.Rect, tol: float = 0.75) -> bool:
    """Check if a character's center falls within a rect (with tolerance)."""
    cb = _rect_from_bbox(char.get("bbox"))
    if cb is None:
        return False
    cx = (cb.x0 + cb.x1) / 2
    cy = (cb.y0 + cb.y1) / 2
    return (
        rect.x0 - tol <= cx <= rect.x1 + tol
        and rect.y0 - tol <= cy <= rect.y1 + tol
    )


def _span_hits_rect(span: dict, rect: fitz.Rect) -> bool:
    """Check if a span's characters (or span bbox fallback) overlap a rect."""
    chars = span.get("chars") or []
    if chars:
        return any(_char_center_hits_rect(ch, rect) for ch in chars)
    # Fallback for unexpected rawdict shape.
    sb = _rect_from_bbox(span.get("bbox"))
    if sb is None:
        return False
    inter = sb & rect
    return (not inter.is_empty) and inter.width > 0 and inter.height > 0


def _spans_from_rawdict(
    rawdict: dict,
    rect: fitz.Rect | None = None,
) -> list[dict] | None:
    """Extract flat span metadata list from a rawdict page dict, optionally filtered by rect."""
    spans: list[dict] = []

    for block in rawdict.get("blocks", []):
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):
            line_dir = line.get("dir")
            if isinstance(line_dir, (list, tuple)) and len(line_dir) == 2:
                line_dir = (float(line_dir[0]), float(line_dir[1]))
            else:
                line_dir = None

            line_wmode = line.get("wmode")
            if not isinstance(line_wmode, int):
                line_wmode = 0

            for span in line.get("spans", []):
                if rect is not None and not _span_hits_rect(span, rect):
                    continue

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
                        "dir": line_dir,
                        "wmode": line_wmode,
                    }
                )

    return spans if spans else None


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

    return _spans_from_rawdict(tp)


def _normalize_rgb(color) -> tuple[float, float, float] | None:
    if color is None:
        return None
    if not isinstance(color, (list, tuple)):
        return None
    if len(color) < 3:
        return None
    r, g, b = float(color[0]), float(color[1]), float(color[2])
    if max(r, g, b) > 1.0:
        r /= 255.0
        g /= 255.0
        b /= 255.0
    return (r, g, b)


def _is_gray(rgb: tuple[float, float, float], threshold: float = 0.05) -> bool:
    return max(rgb) - min(rgb) < threshold


def _brightness(rgb: tuple[float, float, float]) -> float:
    return (rgb[0] + rgb[1] + rgb[2]) / 3.0


def _has_visible_fill(fill) -> bool:
    rgb = _normalize_rgb(fill)
    if rgb is None:
        return False
    if isinstance(fill, (list, tuple)) and len(fill) >= 4 and float(fill[3]) <= 0:
        return False
    return _brightness(rgb) < 0.95


def _extract_rect_features(
    drawing: dict,
    page_width: float,
    page_height: float,
    margin: float = 10.0,
) -> dict:
    """Extract structured features from a PyMuPDF drawing for container admission."""
    import fitz

    fill = drawing.get("fill")
    color = drawing.get("color")
    stroke_width = drawing.get("width", 0) or 0
    raw_rect = drawing.get("rect")
    if not raw_rect:
        return {"rect": fitz.Rect(0, 0, 0, 0), "width": 0, "height": 0, "area": 0,
                "page_area_ratio": 0, "fill_rgb": None, "stroke_rgb": None,
                "stroke_width": 0, "is_filled": False, "has_border": False,
                "is_low_contrast_gray_border": False, "line_like": False, "near_page_edges": False}

    rect = fitz.Rect(raw_rect)
    w = rect.width
    h = rect.height
    area = w * h
    page_area = page_width * page_height
    page_area_ratio = area / page_area if page_area > 0 else 0

    fill_rgb = _normalize_rgb(fill)
    stroke_rgb = _normalize_rgb(color) if color else None
    has_border = stroke_rgb is not None and stroke_width > 0
    is_filled = _has_visible_fill(fill)

    is_low_contrast_gray_border = (
        not is_filled
        and has_border
        and stroke_width <= 1.0
        and stroke_rgb is not None
        and _is_gray(stroke_rgb)
        and 0.02 < _brightness(stroke_rgb) < 0.85
    )

    line_like = h <= 3.0 or w <= 3.0
    near_page_edges = (
        rect.x0 <= margin
        and rect.y0 <= margin
        and rect.x1 >= page_width - margin
        and rect.y1 >= page_height - margin
    )

    return {
        "rect": rect,
        "width": w,
        "height": h,
        "area": area,
        "page_area_ratio": page_area_ratio,
        "fill_rgb": fill_rgb,
        "stroke_rgb": stroke_rgb,
        "stroke_width": stroke_width,
        "is_filled": is_filled,
        "has_border": has_border,
        "is_low_contrast_gray_border": is_low_contrast_gray_border,
        "line_like": line_like,
        "near_page_edges": near_page_edges,
    }


def _component_compatible(a: dict, b: dict) -> bool:
    """One has visible fill, other has fill or border."""
    return (a["is_filled"] and (b["is_filled"] or b["has_border"])) or (
        b["is_filled"] and (a["is_filled"] or a["has_border"])
    )


def _merge_vertical_components(features: list[dict], pw: float = 0, ph: float = 0) -> list[dict]:
    """Group features by x-range overlap >=0.8 and vertical gap -2..5pt.
    Returns merged feature dicts with component_grouped=True."""
    import fitz

    if not features:
        return []
    sorted_feats = sorted(features, key=lambda f: (f["rect"].x0, f["rect"].y0))
    merged: list[dict] = []
    used = [False] * len(sorted_feats)

    for i, a in enumerate(sorted_feats):
        if used[i]:
            continue
        union_rect = fitz.Rect(a["rect"])
        for j in range(i + 1, len(sorted_feats)):
            if used[j]:
                continue
            b = sorted_feats[j]
            x_overlap = min(union_rect.x1, b["rect"].x1) - max(union_rect.x0, b["rect"].x0)
            if x_overlap <= 0:
                continue
            x_overlap_ratio = x_overlap / min(union_rect.width, b["rect"].width)
            if x_overlap_ratio < 0.8:
                continue
            gap = b["rect"].y0 - union_rect.y1
            if gap < -2.0 or gap > 5.0:
                continue
            if not _component_compatible(a, b):
                continue
            union_rect = fitz.Rect(
                min(union_rect.x0, b["rect"].x0),
                min(union_rect.y0, b["rect"].y0),
                max(union_rect.x1, b["rect"].x1),
                max(union_rect.y1, b["rect"].y1),
            )
            used[j] = True
        used[i] = True
        merged.append({
            "rect": union_rect,
            "is_filled": a["is_filled"],
            "has_border": a["has_border"],
            "is_low_contrast_gray_border": a["is_low_contrast_gray_border"],
            "component_grouped": True,
            "page_area_ratio": (union_rect.width * union_rect.height) / (pw * ph) if pw and ph else 0,
        })

    return merged


def _bbox_overlap_ratio(container_rect: Any, block_rect: Any) -> float:
    """Return overlap / block_area. Returns 0.0 if block_area <= 0 or intersection empty."""
    area_b = block_rect.width * block_rect.height
    if area_b <= 0:
        return 0.0
    overlap = container_rect & block_rect
    if overlap.is_empty:
        return 0.0
    return (overlap.width * overlap.height) / area_b


def _word_center_inside_rect(word_bbox, block_rect) -> bool:
    x0, y0, x1, y1 = word_bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    return block_rect.x0 <= cx <= block_rect.x1 and block_rect.y0 <= cy <= block_rect.y1


def _word_belongs_to_block(word_bbox, block_rect) -> bool:
    word_rect = fitz.Rect(*word_bbox)
    return (
        _word_center_inside_rect(word_bbox, block_rect)
        or _bbox_overlap_ratio(word_rect, block_rect) >= 0.30
    )


def _has_container_text(
    rect: Any,
    *,
    pdf_page: Any,
    pdf_blocks: list[Any] | None = None,
    raw_blocks_for_page: list[dict] | None = None,
) -> bool:
    """Count chars from PDF text blocks + OCR raw blocks inside rect.
    Threshold: >= 10 chars total.
    OCR raw block bbox must be mapped to PDF space."""
    import fitz

    char_count = 0
    if pdf_blocks:
        for block in pdf_blocks:
            pdf_rect = fitz.Rect(block[:4])
            if _bbox_overlap_ratio(rect, pdf_rect) >= 0.30:
                char_count += len(str(block[4] or "")) if len(block) > 4 else 0

    if raw_blocks_for_page:
        for block in raw_blocks_for_page:
            block_bbox = block.get("bbox") or [0, 0, 0, 0]
            pw = block.get("page_width") or block.get("ocr_width") or pdf_page.rect.width
            ph = block.get("page_height") or block.get("ocr_height") or pdf_page.rect.height
            try:
                block_rect = _map_ocr_bbox_to_pdf_rect(block_bbox, pw, ph, pdf_page)
            except Exception:
                block_rect = fitz.Rect(*block_bbox)
            if _bbox_overlap_ratio(rect, block_rect) >= 0.30:
                char_count += len(str(block.get("text", "")))

    return char_count >= 10


def _extract_visual_container_rects(
    page: Any,
    raw_blocks_for_page: list[dict] | None = None,
    pdf_blocks: Sequence[Any] | None = None,
) -> list[fitz.Rect]:
    """Extract visible rectangle regions (filled or bordered) from a PDF page.

    Args:
        page: PyMuPDF page object.
        raw_blocks_for_page: OCR raw blocks for this page, used for text evidence check.
        pdf_blocks: PDF text blocks for this page, used for text evidence check.
    """

    try:
        drawings = page.get_drawings()
    except Exception:
        return []

    page_rect = page.rect
    pw, ph = page_rect.width, page_rect.height

    grouping_pool: list[dict] = []
    candidates: list[dict] = []

    for drawing in drawings:
        feat = _extract_rect_features(drawing, pw, ph)

        # page-sized/crop-like: completely excluded from everything
        if feat["page_area_ratio"] >= 0.60 and feat["near_page_edges"]:
            continue
        if feat["width"] >= 0.90 * pw and feat["height"] >= 0.90 * ph:
            continue

        grouping_pool.append(feat)

        if feat["line_like"]:
            continue  # not standalone, but in grouping_pool

        candidates.append(feat)

    # --- Task 4: Component grouping ---
    merged = _merge_vertical_components(grouping_pool, pw, ph)
    overlapping_merged: list[dict] = []
    for m in merged:
        if any((m["rect"] & c["rect"]).get_area() > 0 for c in candidates):
            overlapping_merged.append(m)

    # Remove child candidates covered by merged rects
    child_ids: set[int] = set()
    for m in overlapping_merged:
        for c in candidates:
            cid = id(c["rect"])
            if cid in child_ids:
                continue
            overlap = (m["rect"] & c["rect"]).get_area()
            if overlap > 0 and overlap >= c["rect"].get_area() * 0.5:
                child_ids.add(cid)
    candidates = [c for c in candidates if id(c["rect"]) not in child_ids]
    candidates.extend(overlapping_merged)

    # --- Task 5: Text evidence admission ---
    accepted: list[fitz.Rect] = []
    for feat in candidates:
        vs = feat["is_filled"] or (feat["has_border"] and not feat["is_low_contrast_gray_border"])
        if not vs:
            continue
        if not _has_container_text(
            feat["rect"], pdf_page=page, pdf_blocks=pdf_blocks, raw_blocks_for_page=raw_blocks_for_page
        ):
            continue
        accepted.append(feat["rect"])

    accepted.sort(key=lambda r: r.get_area(), reverse=True)
    return accepted


def backfill_span_metadata_from_pdf(
    raw_blocks: list[dict],
    pdf_path: str | Path | None,
) -> list[dict]:
    """Backfill span_metadata for raw blocks from the source PDF.

    Optimized: groups raw_blocks by page, calls page.get_text("rawdict")
    once per page (not once per block), then filters spans per block
    using character bbox center overlap.

    Returns the modified blocks list (mutated in-place for efficiency).
    Gracefully handles missing PDFs, invalid bboxes, and extraction failures.
    """
    if not pdf_path:
        return raw_blocks
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return raw_blocks

    try:
        doc = _fitz_quiet_open(str(pdf_path))
    except Exception:
        return raw_blocks

    try:
        from collections import defaultdict

        # Group blocks by 0-indexed page number
        raw_blocks_by_page: dict[int, list[dict]] = defaultdict(list)
        for block in raw_blocks:
            try:
                pageno = int(block.get("page", 1)) - 1
            except Exception:
                pageno = 0
            raw_blocks_by_page[pageno].append(block)

        # Phase 0: span metadata backfill — one get_text("rawdict") per page
        #           Skips pages where all blocks already have span_metadata.
        for pageno, page_blocks in raw_blocks_by_page.items():
            if pageno < 0 or pageno >= len(doc):
                continue

            # Only process blocks that still need span_metadata
            need = [b for b in page_blocks if not b.get("span_metadata")]
            if not need:
                continue  # entire page already done, skip get_text("rawdict")

            try:
                page = doc[pageno]
                page_rawdict = page.get_text("rawdict")
            except Exception:
                continue

            for block in need:
                bbox = block.get("bbox", [])
                if not bbox or len(bbox) < 4:
                    continue

                try:
                    pw = block.get("page_width")
                    ph = block.get("page_height")
                    if pw and ph and pw > 0 and ph > 0:
                        rect = _map_ocr_bbox_to_pdf_rect(bbox, pw, ph, page)
                    else:
                        rect = fitz.Rect(*bbox)
                except Exception:
                    continue

                if rect.is_empty or rect.width <= 0 or rect.height <= 0:
                    continue

                spans = _spans_from_rawdict(page_rawdict, rect)
                if spans:
                    block["span_metadata"] = spans

        # Phase A+B+C: per-page container detection
        for pageno, page_blocks in raw_blocks_by_page.items():
            # Phase A: clear stale flags
            for block in page_blocks:
                block.pop("_in_visual_container", None)
                block.pop("_container_bbox", None)
                block.pop("_container_text", None)

            # Phase B: compute containers with text evidence
            try:
                pdf_page = doc[pageno]
                pdf_blocks = pdf_page.get_text("blocks")
                containers = _extract_visual_container_rects(
                    pdf_page,
                    raw_blocks_for_page=page_blocks,
                    pdf_blocks=pdf_blocks,
                )
            except Exception:
                continue

            if not containers:
                continue

            # Phase C: mark blocks that overlap containers
            for block in page_blocks:
                bbox = block.get("bbox", [])
                if not bbox or len(bbox) < 4:
                    continue
                pw = block.get("page_width") or block.get("ocr_width") or 0
                ph = block.get("page_height") or block.get("ocr_height") or 0
                if pw <= 0 or ph <= 0:
                    try:
                        pdf_rect = doc[pageno].rect
                        pw = int(pdf_rect.width * 2) if pdf_rect.width > 0 else 1200
                        ph = int(pdf_rect.height * 2) if pdf_rect.height > 0 else 1700
                    except Exception:
                        pw, ph = 1200, 1700
                if pw > 0 and ph > 0:
                    try:
                        block_rect = _map_ocr_bbox_to_pdf_rect(bbox, pw, ph, doc[pageno])
                    except Exception:
                        continue
                else:
                    block_rect = fitz.Rect(*bbox)

                for container_rect in containers:
                    overlap_ratio = _bbox_overlap_ratio(container_rect, block_rect)
                    if overlap_ratio >= 0.3:
                        block["_in_visual_container"] = True
                        scale_x = pw / doc[pageno].rect.width if pw and doc[pageno].rect.width else 1
                        scale_y = ph / doc[pageno].rect.height if ph and doc[pageno].rect.height else 1
                        block["_container_bbox"] = [
                            container_rect.x0 * scale_x,
                            container_rect.y0 * scale_y,
                            container_rect.x1 * scale_x,
                            container_rect.y1 * scale_y,
                        ]
                        block["_container_text"] = block.get("text", "") or ""
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

_LIGATURE_MAP = {
    "\ufb01": "fi", "\ufb02": "fl", "\ufb00": "ff",
    "\ufb03": "ffi", "\ufb04": "ffl",
    "\u2013": "-", "\u2014": "-", "\u2015": "-",
}


def _strip_for_comparison(s: str) -> str:
    """Normalize text for overlap detection: drop formatting, citations, LaTeX, ligatures."""
    import re

    for src, dst in _LIGATURE_MAP.items():
        s = s.replace(src, dst)
    s = re.sub(r'\$\$?[^$]+\$\$?', '', s)
    s = re.sub(r'\$?\^?\{?\[?\d+[\d,\-]*\]?\}?\$?', '', s)
    s = re.sub(r'[\s\W_]+', '', s)
    return s.lower()


def _backfill_coverage_in_existing(backfill_text: str, existing_text: str) -> float:
    """Fraction of backfill_text n-grams present in existing_text, after stripping.

    Uses 5-gram overlap (not exact character sequence) to be robust against:
    - Prefix fragments (e.g. "cific" vs "specific" at column boundary)
    - PDF text layer encoding artifacts (ligature→normal)
    - Hyphenation and spacing differences.
    """
    a = _strip_for_comparison(backfill_text)
    b = _strip_for_comparison(existing_text)
    if len(a) < 40:
        return 0.0

    n = 5
    if len(a) < n or len(b) < n:
        return 0.0

    a_grams = {a[i : i + n] for i in range(len(a) - n + 1)}
    b_grams = {b[i : i + n] for i in range(len(b) - n + 1)}
    if not a_grams:
        return 0.0

    return len(a_grams & b_grams) / len(a_grams)


_BACKFILL_OVERLAP_REJECT_THRESHOLD = 0.8


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

    try:
        doc = _fitz_quiet_open(str(pdf_path))
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

            words = [
                w for w in words
                if len(w) >= 4 and _word_belongs_to_block(tuple(w[:4]), rect)
            ]

            text = _words_to_text(words)

            if text:
                same_page_existing = [
                    other for other in raw_blocks
                    if other is not block
                    and other.get("page") == block.get("page")
                    and str(other.get("text") or other.get("block_content") or "").strip()
                ]
                overlaps = any(
                    _backfill_coverage_in_existing(text, str(other.get("text") or other.get("block_content") or ""))
                    >= _BACKFILL_OVERLAP_REJECT_THRESHOLD
                    for other in same_page_existing
                )
                if overlaps:
                    block["_ocr_raw_status"] = "missing_text_rejected"
                    block["_ocr_raw_error_type"] = "backfill_overlaps_existing_text_block"
                    block["_text_source"] = "pdf_text_layer_fallback_rejected"
                    unrecovered += 1
                else:
                    block["_original_ocr_text"] = ""
                    block["text"] = text
                    block["block_content"] = text
                    block["_text_source"] = "pdf_text_layer_fallback"
                    block["_ocr_raw_status"] = "missing_text_recovered"
                    block["_ocr_raw_error_type"] = "empty_text_with_pdf_evidence"
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
def extract_pdf_lines_normalized(pdf_path: str | Path) -> dict[int, list[dict]]:
    """Extract PDF rawdict text lines per page, normalized to OCR coordinates.

    Each returned line dict:
        page (int): 1-indexed page number
        text (str): line text
        bbox (list[float]): normalized OCR coordinates [x1, y1, x2, y2]
        source_bbox_pdf (list[float]): original PDF coordinates
        dir (tuple[float, float]): writing direction (dx, dy)
        source (str): "pdf_rawdict_line"

    Returns dict mapping 1-indexed page number -> list of line dicts.
    Empty dict on error.
    """
    if not pdf_path:
        return {}
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        return {}
    try:
        doc = _fitz_quiet_open(str(pdf_path))
    except Exception:
        return {}
    try:
        result: dict[int, list[dict]] = {}
        for page_num in range(len(doc)):
            try:
                pdf_page = doc[page_num]
                pdf_rect = pdf_page.rect
                ocr_width = int(pdf_rect.width * 2) if pdf_rect.width > 0 else 1200
                ocr_height = int(pdf_rect.height * 2) if pdf_rect.height > 0 else 1700
                raw_dict = pdf_page.get_text("dict")
                page_lines: list[dict] = []
                for block in raw_dict.get("blocks", []):
                    if block.get("type") != 0:  # text block
                        continue
                    for line in block.get("lines", []):
                        bbox_pdf = line.get("bbox", [0, 0, 0, 0])
                        if len(bbox_pdf) < 4:
                            continue
                        text_parts = []
                        for span in line.get("spans", []):
                            text_parts.append(str(span.get("text", "")))
                        text = "".join(text_parts).strip()
                        if not text:
                            continue
                        # Normalize PDF coords to OCR/render coords
                        scale_x = ocr_width / pdf_rect.width if pdf_rect.width > 0 else 2.0
                        scale_y = ocr_height / pdf_rect.height if pdf_rect.height > 0 else 2.0
                        bbox_ocr = [
                            bbox_pdf[0] * scale_x,
                            bbox_pdf[1] * scale_y,
                            bbox_pdf[2] * scale_x,
                            bbox_pdf[3] * scale_y,
                        ]
                        direction = tuple(line.get("dir", (1.0, 0.0)))
                        page_lines.append({
                            "page": page_num + 1,
                            "text": text,
                            "bbox": bbox_ocr,
                            "source_bbox_pdf": bbox_pdf,
                            "dir": direction,
                            "source": "pdf_rawdict_line",
                        })
                result[page_num + 1] = page_lines
            except Exception:
                continue
        return result
    finally:
        doc.close()
