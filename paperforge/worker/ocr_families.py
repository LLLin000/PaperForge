from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


_STRONG_MARKER_TYPES = {
    "figure_number",
    "table_number",
    "reference_numeric_bracket",
    "reference_numeric_dot",
    "reference_numeric_parenthesis",
    "reference_pattern",
    "citation_line",
}

_FRONTMATTER_MARKER_TYPES = {
    "affiliation_marker",
    "preproof_marker",
}


def discover_body_family_anchor(blocks: list[dict], page_count: int | None = None) -> dict[str, Any]:
    """Discover a document-level body family anchor from middle-page evidence."""
    resolved_page_count = max(page_count or 0, max((int(b.get("page", 0) or 0) for b in blocks), default=0))
    sample_pages = _select_middle_sample_pages(blocks, resolved_page_count)
    if not sample_pages:
        return {
            "status": "HOLD",
            "family_name": "body_family",
            "reason": "no_eligible_middle_pages",
            "sample_pages": [],
            "candidate_count": 0,
        }

    family_pages: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    family_counts: Counter[tuple[Any, ...]] = Counter()

    for block in blocks:
        page = int(block.get("page", 0) or 0)
        if page not in sample_pages:
            continue
        if not _is_body_family_candidate(block):
            continue
        key = _body_family_key(block)
        if key is None:
            continue
        family_counts[key] += 1
        family_pages[key].add(page)

    repeated_candidates = [
        (key, family_counts[key], sorted(family_pages[key]))
        for key in family_counts
        if len(family_pages[key]) >= 2
    ]
    if not repeated_candidates:
        return {
            "status": "HOLD",
            "family_name": "body_family",
            "reason": "no_repeated_family_across_sample_pages",
            "sample_pages": sorted(sample_pages),
            "candidate_count": sum(family_counts.values()),
        }

    repeated_candidates.sort(key=lambda item: (-len(item[2]), -item[1], item[2][0], str(item[0])))
    winning_key, winning_count, winning_pages = repeated_candidates[0]
    font_family, font_size_bucket, width_bucket, x_center_bucket = winning_key
    return {
        "status": "ACCEPT",
        "family_name": "body_family",
        "reason": "dominant_repeated_middle_page_family",
        "sample_pages": winning_pages,
        "candidate_count": winning_count,
        "font_family_norm": font_family,
        "font_size_bucket": font_size_bucket,
        "width_bucket": width_bucket,
        "x_center_bucket": x_center_bucket,
    }


def _select_middle_sample_pages(blocks: list[dict], page_count: int) -> set[int]:
    if page_count <= 0:
        return set()

    pages = {int(block.get("page", 0) or 0) for block in blocks if int(block.get("page", 0) or 0) > 0}
    if not pages:
        return set()

    if page_count >= 4:
        tail_page_count = max(1, round(page_count * 0.2))
        tail_cutoff = max(1, page_count - tail_page_count)
        start_page = max(2, int(page_count * 0.25))
        end_page = min(int(page_count * 0.7), tail_cutoff)
        if end_page < start_page:
            start_page = 2
            end_page = tail_cutoff

        selected = {
            page for page in pages
            if page != 1 and page <= tail_cutoff and start_page <= page <= end_page
        }
        if not selected:
            selected = {
                page for page in pages
                if page != 1 and page <= tail_cutoff
            }
        if len(selected) < 2:
            selected = {page for page in pages if page != 1}
    else:
        selected = {page for page in pages if page != 1}

    stable_pages: set[int] = set()
    for page in selected:
        page_blocks = [block for block in blocks if int(block.get("page", 0) or 0) == page]
        if _page_is_contaminated(page_blocks):
            continue
        stable_pages.add(page)
    return stable_pages


def _page_is_contaminated(page_blocks: list[dict]) -> bool:
    if not page_blocks:
        return True
    media_like = 0
    short_like = 0
    media_area_ratio = 0.0
    reference_like = 0
    frontmatter_like = 0
    total = len(page_blocks)
    for block in page_blocks:
        marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
        if marker_type in _STRONG_MARKER_TYPES | {"figure_number", "table_number", "panel_label"}:
            media_like += 1
            media_area_ratio += _block_area_ratio(block)
        if marker_type in {
            "reference_numeric_bracket",
            "reference_numeric_dot",
            "reference_numeric_parenthesis",
            "reference_pattern",
            "citation_line",
        }:
            reference_like += 1
        if marker_type in _FRONTMATTER_MARKER_TYPES:
            frontmatter_like += 1
        if _word_count(block) < 12:
            short_like += 1
    if media_like / total > 0.5:
        return True
    if media_area_ratio > 0.33:
        return True
    if short_like / total > 0.75:
        return True
    if reference_like / total >= 0.5:
        return True
    if frontmatter_like / total >= 0.5:
        return True
    return False


def _is_body_family_candidate(block: dict) -> bool:
    if _word_count(block) < 25:
        return False
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    if marker_type in _STRONG_MARKER_TYPES:
        return False
    span_signature = block.get("span_signature") or {}
    if not span_signature.get("font_family_norm"):
        return False
    if span_signature.get("font_size_median") is None and span_signature.get("font_size_bucket") is None:
        return False
    layout_signature = block.get("layout_signature") or {}
    if not layout_signature.get("width"):
        return False
    return True


def _body_family_key(block: dict) -> tuple[Any, ...] | None:
    span_signature = block.get("span_signature") or {}
    layout_signature = block.get("layout_signature") or {}
    font_family = span_signature.get("font_family_norm")
    font_size_bucket = span_signature.get("font_size_bucket")
    if font_size_bucket is None:
        font_size_bucket = _bucket_number(span_signature.get("font_size_median"), step=0.5)
    width_bucket = layout_signature.get("width_bucket")
    if width_bucket is None:
        width_bucket = _bucket_number(layout_signature.get("width"), step=25)
    x_center_bucket = layout_signature.get("x_center_bucket")
    if x_center_bucket is None:
        x_center_bucket = _bucket_number(layout_signature.get("x_center"), step=25)
    if font_family is None or font_size_bucket is None or width_bucket is None or x_center_bucket is None:
        return None
    return (
        font_family,
        font_size_bucket,
        width_bucket,
        x_center_bucket,
    )


def _word_count(block: dict) -> int:
    text = str(block.get("text") or block.get("block_content") or "")
    return len([token for token in text.split() if token])


def _bucket_number(value: Any, step: float) -> float | None:
    if value is None:
        return None
    return round(round(float(value) / step) * step, 2)


def _block_area_ratio(block: dict) -> float:
    bbox = block.get("bbox") or block.get("block_bbox") or []
    if len(bbox) >= 4:
        width = max(0.0, float(bbox[2]) - float(bbox[0]))
        height = max(0.0, float(bbox[3]) - float(bbox[1]))
    else:
        layout_signature = block.get("layout_signature") or {}
        width = max(0.0, float(layout_signature.get("width") or 0.0))
        height = max(0.0, float(layout_signature.get("height") or 0.0))
    page_width = float(block.get("page_width") or 0.0)
    page_height = float(block.get("page_height") or 0.0)
    if page_width <= 0 or page_height <= 0:
        return 0.0
    return (width * height) / (page_width * page_height)
