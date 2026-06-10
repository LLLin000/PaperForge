from __future__ import annotations

import re

_HEADING_NUMBER_PATTERN = re.compile(
    r"^\d+(?:\.\d+)*\.?\s+[A-Z]",
)

_FIGURE_PREFIX_PATTERN = re.compile(
    r"^(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+\d+",
    flags=re.IGNORECASE,
)

_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+\d+",
    flags=re.IGNORECASE,
)

_PREPROOF_MARKER = re.compile(
    r"^(?:journal\s+)?pre-?proof\b",
    re.IGNORECASE,
)

_ROMAN_SECTION_PATTERN = re.compile(
    r"^(?:[IVXLCDM]+)\.\s+[A-Z][A-Z0-9 ,;:\-/()]+$",
    re.IGNORECASE,
)

_ALPHA_SUBSECTION_PATTERN = re.compile(
    r"^[A-Z]\.\s+[A-Z][A-Za-z0-9 ,;:\-/()]+$",
)

_REFERENCE_PATTERN = re.compile(
    r"^\s*(?:\d+\.\s|[A-Z][A-Za-z'’\-]+\s+et al\.\s*\(\d{4}[a-z]?\)|\([A-Z][A-Za-z'’\-]+\s+et al\.,\s*\d{4}[a-z]?\))",
)

_REFERENCE_NUMERIC_BRACKET_PATTERN = re.compile(r"^\s*\[(\d+)\]")
_REFERENCE_NUMERIC_DOT_PATTERN = re.compile(r"^\s*(\d+)\.?\s")
_REFERENCE_NUMERIC_PAREN_PATTERN = re.compile(r"^\s*(?:\((\d+)\)|(\d+)\))\s")

_PANEL_LABEL_PATTERN = re.compile(
    r"^\(?[A-Z]\)?[\.:]?$",
)

_CITATION_LINE_PATTERN = re.compile(
    r"^[A-Z][a-z]+\'?[a-z]* [A-Z](?:\.[, ]|[A-Z]\.?,|[,\s])",
)

_AUTHOR_AFFILIATION_MARKER = re.compile(r"\$\s*\^\{")

_COMMON_SECTION_HEADINGS = {
    "introduction",
    "materials and methods",
    "methods",
    "results",
    "results and discussion",
    "discussion",
    "conclusion",
    "conclusions",
}


def _bucket_number(value: float | int | None, step: float = 1.0) -> float | None:
    if value is None:
        return None
    return round(round(float(value) / step) * step, 2)


def _detect_marker_type(text: str) -> str:
    if not text:
        return "empty"
    stripped = text.strip()
    if _PREPROOF_MARKER.match(stripped):
        return "preproof_marker"
    if _PANEL_LABEL_PATTERN.match(stripped):
        return "panel_label"
    if _ROMAN_SECTION_PATTERN.match(stripped):
        return "heading_roman"
    if _REFERENCE_NUMERIC_BRACKET_PATTERN.match(stripped):
        return "reference_numeric_bracket"
    if _REFERENCE_NUMERIC_DOT_PATTERN.match(stripped):
        return "reference_numeric_dot"
    if _REFERENCE_NUMERIC_PAREN_PATTERN.match(stripped):
        return "reference_numeric_parenthesis"
    if _HEADING_NUMBER_PATTERN.match(stripped):
        return "heading_numbered"
    if _ALPHA_SUBSECTION_PATTERN.match(stripped):
        return "heading_alpha"
    if stripped.lower().lstrip("*•·-–—") in _COMMON_SECTION_HEADINGS:
        return "canonical_section_name"
    if _FIGURE_PREFIX_PATTERN.match(stripped):
        return "figure_number"
    if _TABLE_PREFIX_PATTERN.match(stripped):
        return "table_number"
    if _REFERENCE_PATTERN.match(stripped):
        return "reference_pattern"
    if _CITATION_LINE_PATTERN.match(stripped):
        return "citation_line"
    if _AUTHOR_AFFILIATION_MARKER.match(stripped):
        return "affiliation_marker"
    if len(stripped) < 20:
        return "short_fragment"
    return "none"


def _extract_marker_signature(text: str) -> dict:
    marker_type = _detect_marker_type(text)
    stripped = text.strip()
    result = {
        "type": marker_type,
        "raw_marker": None,
        "number": None,
        "kind": None,
        "normalized_text": stripped,
    }

    if marker_type == "heading_roman":
        roman = stripped.split(".", 1)[0].strip()
        result["raw_marker"] = roman
        result["kind"] = "heading"
    elif marker_type == "heading_numbered":
        number_part = stripped.split(maxsplit=1)[0].rstrip(".")
        result["raw_marker"] = number_part
        result["number"] = number_part
        result["kind"] = "heading"
    elif marker_type == "heading_alpha":
        alpha = stripped.split(".", 1)[0].strip()
        result["raw_marker"] = alpha
        result["kind"] = "heading"
    elif marker_type == "canonical_section_name":
        result["raw_marker"] = stripped
        result["kind"] = "heading"
    elif marker_type == "figure_number":
        _FIG_NUM_RE = re.compile(
            r"(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
            r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+(\d+)",
            re.IGNORECASE,
        )
        match = _FIG_NUM_RE.search(stripped)
        if match:
            result["number"] = int(match.group(1))
            result["raw_marker"] = match.group(0)
        result["kind"] = "figure"
    elif marker_type == "table_number":
        match = re.search(r"(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(\d+)", stripped, re.IGNORECASE)
        if match:
            result["number"] = int(match.group(1))
            result["raw_marker"] = match.group(0)
        result["kind"] = "table"
    elif marker_type in {
        "reference_numeric_bracket",
        "reference_numeric_dot",
        "reference_numeric_parenthesis",
        "reference_pattern",
    }:
        bracket = _REFERENCE_NUMERIC_BRACKET_PATTERN.match(stripped)
        numeric_dot = _REFERENCE_NUMERIC_DOT_PATTERN.match(stripped)
        numeric_paren = _REFERENCE_NUMERIC_PAREN_PATTERN.match(stripped)
        if bracket:
            result["kind"] = "reference"
            result["type"] = "reference_numeric_bracket"
            result["number"] = int(bracket.group(1))
            result["raw_marker"] = bracket.group(0).strip()
        elif numeric_dot:
            result["kind"] = "reference"
            result["type"] = "reference_numeric_dot"
            result["number"] = int(numeric_dot.group(1))
            result["raw_marker"] = numeric_dot.group(0).strip()
        elif numeric_paren:
            num = numeric_paren.group(1) or numeric_paren.group(2)
            result["kind"] = "reference"
            result["type"] = "reference_numeric_parenthesis"
            result["number"] = int(num) if num is not None else None
            result["raw_marker"] = numeric_paren.group(0).strip()
        else:
            result["kind"] = "reference"
            result["type"] = "reference_pattern"
            result["raw_marker"] = stripped[:40]
    elif marker_type == "none":
        result["kind"] = "generic_text"
    elif marker_type in {"preproof_marker", "panel_label", "citation_line", "affiliation_marker", "short_fragment"}:
        result["raw_marker"] = stripped
        result["kind"] = marker_type

    return result


def _extract_span_signature(span_metadata: dict | list | None) -> dict:
    if not span_metadata:
        return {
            "font_size": None,
            "font_size_median": None,
            "font_size_bucket": None,
            "font_family_norm": None,
            "bold": False,
            "italic": False,
            "span_count": 0,
        }

    if isinstance(span_metadata, dict):
        size = span_metadata.get("size") or span_metadata.get("font_size")
        font_family = span_metadata.get("font") or span_metadata.get("font_family")
        flags_raw = span_metadata.get("flags", "")
        bold: bool
        italic: bool
        if isinstance(flags_raw, str):
            bold = "bold" in flags_raw.lower()
            italic = "italic" in flags_raw.lower()
        else:
            bold = bool(flags_raw & 16) if isinstance(flags_raw, int) else False
            italic = bool(flags_raw & 4) if isinstance(flags_raw, int) else False
        if "bold" in span_metadata:
            bold = bool(span_metadata["bold"])
        return {
            "font_size": float(size) if size is not None else None,
            "font_size_median": float(size) if size is not None else None,
            "font_size_bucket": _bucket_number(size, step=0.5),
            "font_family_norm": str(font_family).strip() if font_family else None,
            "bold": bold,
            "italic": italic,
            "span_count": 1,
        }

    if isinstance(span_metadata, list):
        sizes = [s.get("size") for s in span_metadata if s.get("size") is not None]
        mean_size = sum(sizes) / len(sizes) if sizes else None
        sorted_sizes = sorted(sizes)
        n = len(sorted_sizes)
        if n % 2 == 1:
            median_size = float(sorted_sizes[n // 2])
        elif n > 0:
            median_size = (sorted_sizes[n // 2 - 1] + sorted_sizes[n // 2]) / 2.0
        else:
            median_size = None
        families = [
            str(s.get("font") or s.get("font_family")).strip()
            for s in span_metadata
            if s.get("font") or s.get("font_family")
        ]
        flags_combined = 0
        for s in span_metadata:
            f = s.get("flags", 0)
            if isinstance(f, int):
                flags_combined |= f
        return {
            "font_size": round(mean_size, 2) if mean_size is not None else None,
            "font_size_median": round(median_size, 2) if median_size is not None else None,
            "font_size_bucket": _bucket_number(mean_size, step=0.5),
            "font_family_norm": families[0] if families else None,
            "bold": bool(flags_combined & 16),
            "italic": bool(flags_combined & 4),
            "span_count": len(span_metadata),
        }

    return {
        "font_size": None,
        "font_size_median": None,
        "font_size_bucket": None,
        "font_family_norm": None,
        "bold": False,
        "italic": False,
        "span_count": 0,
    }


def _extract_layout_signature(
    bbox: list | None,
    page_width: float | int | None = None,
    page_height: float | int | None = None,
) -> dict:
    if not bbox or len(bbox) < 4:
        return {
            "width": 0,
            "width_bucket": 0,
            "height": 0,
            "left": 0,
            "top": 0,
            "right": 0,
            "bottom": 0,
            "x_center": 0,
            "x_center_bucket": 0,
            "y_center": 0,
            "x_ratio": 0.0,
            "y_ratio": 0.0,
            "width_ratio": 0.0,
            "height_ratio": 0.0,
            "line_count": 1,
        }
    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
    width = x2 - x1
    height = y2 - y1
    x_center = round((x1 + x2) / 2, 2)
    y_center = round((y1 + y2) / 2, 2)
    width_base = float(page_width or 0) or None
    height_base = float(page_height or 0) or None
    return {
        "width": width,
        "width_bucket": _bucket_number(width, step=25),
        "height": height,
        "left": x1,
        "top": y1,
        "right": x2,
        "bottom": y2,
        "x_center": x_center,
        "x_center_bucket": _bucket_number(x_center, step=25),
        "y_center": y_center,
        "x_ratio": round(x_center / width_base, 4) if width_base else 0.0,
        "y_ratio": round(y_center / height_base, 4) if height_base else 0.0,
        "width_ratio": round(width / width_base, 4) if width_base else 0.0,
        "height_ratio": round(height / height_base, 4) if height_base else 0.0,
        "line_count": 1,
    }


def build_block_signatures(block: dict) -> dict:
    text = str(block.get("text", "") or block.get("block_content", "") or "")
    bbox = block.get("bbox") or block.get("block_bbox")
    span_metadata = block.get("span_metadata")
    page_width = block.get("page_width")
    page_height = block.get("page_height")

    marker_sig = _extract_marker_signature(text)
    layout_sig = _extract_layout_signature(bbox, page_width=page_width, page_height=page_height)
    span_sig = _extract_span_signature(span_metadata)

    return {
        "block_id": block.get("block_id", ""),
        "page": block.get("page", 1),
        "raw_label": block.get("raw_label", block.get("block_label", "unknown")),
        "text": text,
        "bbox": bbox,
        "page_width": page_width,
        "page_height": page_height,
        "raw_observation": {
            "block_id": block.get("block_id", ""),
            "page": block.get("page", 1),
            "raw_label": block.get("raw_label", block.get("block_label", "unknown")),
            "text": text,
            "bbox": bbox,
            "page_width": page_width,
            "page_height": page_height,
        },
        "role": "unassigned",
        "marker_signature": marker_sig,
        "layout_signature": layout_sig,
        "span_signature": span_sig,
    }
