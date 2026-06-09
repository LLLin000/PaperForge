from __future__ import annotations

from collections import Counter, defaultdict
import re
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

_REFERENCE_MARKER_TYPES = {
    "reference_numeric_bracket",
    "reference_numeric_dot",
    "reference_numeric_parenthesis",
    "reference_pattern",
    "citation_line",
}

_REFERENCE_HEADING_TEXTS = {"references", "bibliography"}
_HEADING_MARKER_TYPES = {"canonical_section_name"}
_SUPPORT_ZONE_HINTS = ("support", "insert", "frontmatter", "margin", "sidebar")


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


def discover_reference_family_anchor(blocks: list[dict], page_count: int | None = None) -> dict[str, Any]:
    """Discover a reference-family anchor from marker/style/tail evidence."""
    resolved_page_count = max(page_count or 0, max((int(b.get("page", 0) or 0) for b in blocks), default=0))
    reference_candidates = [block for block in blocks if _is_reference_family_candidate(block)]
    if not reference_candidates:
        return {
            "status": "HOLD",
            "family_name": "reference_family",
            "reason": "no_reference_marker_candidates",
            "item_count": 0,
        }

    family_counts: Counter[tuple[Any, ...]] = Counter()
    family_pages: dict[tuple[Any, ...], set[int]] = defaultdict(set)
    family_marker_counts: Counter[tuple[Any, ...]] = Counter()
    for block in reference_candidates:
        key = _reference_family_key(block)
        if key is None:
            continue
        family_counts[key] += 1
        family_pages[key].add(int(block.get("page", 0) or 0))
        family_marker_counts[key] += 1

    if not family_counts:
        return {
            "status": "HOLD",
            "family_name": "reference_family",
            "reason": "no_reference_family_signature",
            "item_count": len(reference_candidates),
            "marker_count": 0,
        }

    ranked_candidates = sorted(
        family_counts.items(),
        key=lambda item: (
            -_reference_candidate_rank_score(
                family_pages=sorted(family_pages[item[0]]),
                item_count=item[1],
                marker_count=family_marker_counts[item[0]],
                page_count=resolved_page_count,
            ),
            -max(family_pages[item[0]]),
            -len(family_pages[item[0]]),
            -item[1],
            str(item[0]),
        ),
    )

    best_hold: dict[str, Any] | None = None
    for family_key, item_count in ranked_candidates:
        family_candidate = _build_reference_family_candidate(
            blocks=blocks,
            family_key=family_key,
            item_count=item_count,
            family_pages=sorted(family_pages[family_key]),
            marker_count=family_marker_counts[family_key],
            page_count=resolved_page_count,
        )
        if family_candidate["status"] == "ACCEPT":
            return family_candidate
        if best_hold is None:
            best_hold = family_candidate

    return best_hold or {
        "status": "HOLD",
        "family_name": "reference_family",
        "reason": "insufficient_reference_family_evidence",
        "item_count": 0,
        "marker_count": 0,
        "sample_pages": [],
        "tail_continuity": 0.0,
        "heading_binding": False,
    }


def partition_zone_families(
    blocks: list[dict],
    anchors: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Assign in-zone style/layout family artifacts without resolving final roles."""
    anchors = anchors or {}
    body_anchor = anchors.get("body_family_anchor") or {}
    reference_anchor = anchors.get("reference_family_anchor") or {}

    partitioned: dict[str, dict[str, Any]] = {}
    for index, block in enumerate(blocks):
        block_id = str(block.get("block_id") or f"block_{index}")
        style_family, authority = _classify_style_family(block, body_anchor, reference_anchor)
        block["style_family"] = style_family
        block["style_family_authority"] = authority
        partitioned[block_id] = {
            "style_family": style_family,
            "authority": authority,
            "zone": block.get("zone"),
        }
    return partitioned


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


def _classify_style_family(
    block: dict,
    body_anchor: dict[str, Any],
    reference_anchor: dict[str, Any],
) -> tuple[str, str]:
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    text = str(block.get("text") or block.get("block_content") or "").strip()
    zone = str(block.get("zone") or "")
    text_lower = text.lower()

    if _reference_anchor_matches_block(reference_anchor, block):
        return "reference_like", "reference_family_anchor"
    if marker_type in _REFERENCE_MARKER_TYPES:
        return "reference_like", "reference_marker"
    if marker_type == "table_number" or text_lower.startswith("table "):
        return "table_caption_like", "table_marker"
    if marker_type in {"figure_number", "panel_label"} or text_lower.startswith("figure "):
        return "legend_like", "figure_marker"
    if marker_type in _HEADING_MARKER_TYPES:
        return "heading_like", "heading_marker"
    if _anchor_matches_block(body_anchor, block, _body_family_key):
        return "body_like", "body_family_anchor"
    if zone == "frontmatter_side_zone":
        return "support_like", "frontmatter_side_zone"
    if body_anchor.get("status") == "ACCEPT" and zone == "body_zone" and _is_body_zone_body_like(block):
        return "body_like", "body_zone_with_anchor"
    if zone == "body_zone" and _is_body_family_candidate(block):
        return "body_like", "body_zone_candidate"
    if any(hint in zone for hint in _SUPPORT_ZONE_HINTS):
        return "support_like", "zone_context"
    return "unknown_like", "fallback"


def _anchor_matches_block(
    anchor: dict[str, Any],
    block: dict,
    key_builder: Any,
) -> bool:
    if anchor.get("status") != "ACCEPT":
        return False
    anchor_key = (
        anchor.get("font_family_norm"),
        anchor.get("font_size_bucket"),
        anchor.get("width_bucket"),
        anchor.get("x_center_bucket"),
    )
    if any(value is not None for value in anchor_key):
        return key_builder(block) == anchor_key
    return False


def _reference_anchor_matches_block(anchor: dict[str, Any], block: dict) -> bool:
    if not _anchor_matches_block(anchor, block, _reference_family_key):
        return False
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    if marker_type in _REFERENCE_MARKER_TYPES:
        return True

    zone = str(block.get("zone") or "")
    if zone == "reference_zone":
        return True
    if zone == "body_zone":
        return False
    if _has_reference_text_structure(block):
        return True
    if zone:
        return False

    sample_pages = [int(page) for page in anchor.get("sample_pages") or [] if page is not None]
    page = int(block.get("page", 0) or 0)
    if sample_pages and page > 0:
        if page >= min(sample_pages) - 1:
            return _has_reference_text_structure(block)
    return False


def _has_reference_text_structure(block: dict) -> bool:
    text = str(block.get("text") or block.get("block_content") or "").strip()
    if not text:
        return False

    if re.match(r"^\[\d+\]", text):
        return True
    if re.match(r"^\d+[\.)]", text):
        return True

    citation_years = re.findall(r"\b(?:19|20)\d{2}[a-z]?\b", text)
    if len(citation_years) >= 2:
        return True

    if text.count(";") >= 2 and text.count(",") >= 3:
        return True

    return False


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


def _is_body_zone_body_like(block: dict) -> bool:
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    if marker_type in _STRONG_MARKER_TYPES | {"panel_label"}:
        return False
    span_signature = block.get("span_signature") or {}
    layout_signature = block.get("layout_signature") or {}
    return bool(
        span_signature.get("font_family_norm")
        and (span_signature.get("font_size_median") is not None or span_signature.get("font_size_bucket") is not None)
        and layout_signature.get("width")
    )


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


def _is_reference_family_candidate(block: dict) -> bool:
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    if marker_type not in _REFERENCE_MARKER_TYPES:
        return False
    span_signature = block.get("span_signature") or {}
    layout_signature = block.get("layout_signature") or {}
    if span_signature.get("font_size_median") is None and span_signature.get("font_size_bucket") is None:
        return False
    if not layout_signature.get("width"):
        return False
    return True


def _reference_family_key(block: dict) -> tuple[Any, ...] | None:
    span_signature = block.get("span_signature") or {}
    layout_signature = block.get("layout_signature") or {}
    font_family = span_signature.get("font_family_norm") or "unknown"
    font_size_bucket = span_signature.get("font_size_bucket")
    if font_size_bucket is None:
        font_size_bucket = _bucket_number(span_signature.get("font_size_median"), step=0.5)
    width_bucket = layout_signature.get("width_bucket")
    if width_bucket is None:
        width_bucket = _bucket_number(layout_signature.get("width"), step=25)
    x_center_bucket = layout_signature.get("x_center_bucket")
    if x_center_bucket is None:
        x_center_bucket = _bucket_number(layout_signature.get("x_center"), step=25)
    if font_size_bucket is None or width_bucket is None or x_center_bucket is None:
        return None
    return (
        font_family,
        font_size_bucket,
        width_bucket,
        x_center_bucket,
    )


def _reference_tail_continuity_score(reference_pages: list[int], page_count: int) -> float:
    if not reference_pages:
        return 0.0
    if page_count <= 0:
        return 1.0
    last_page = max(reference_pages)
    tail_gap = max(0, page_count - last_page)
    if tail_gap > 1:
        return 0.0
    if len(reference_pages) == 1:
        return 1.0 if tail_gap <= 1 else 0.0
    contiguous_span = 1
    for idx in range(len(reference_pages) - 1, 0, -1):
        if reference_pages[idx] - reference_pages[idx - 1] == 1:
            contiguous_span += 1
        else:
            break
    if contiguous_span != len(reference_pages):
        return 0.0
    expected_span = max(2, min(len(reference_pages), 3))
    continuity = contiguous_span / expected_span
    if tail_gap == 1:
        continuity = min(continuity, 1.0)
    return continuity


def _reference_candidate_rank_score(
    family_pages: list[int],
    item_count: int,
    marker_count: int,
    page_count: int,
) -> float:
    tail_score = _reference_tail_continuity_score(family_pages, page_count)
    last_page = max(family_pages) if family_pages else 0
    return (
        tail_score * 1000
        + last_page * 10
        + min(item_count, 10) * 3
        + min(marker_count, 10)
    )


def _has_reference_heading_near_family(blocks: list[dict], family_pages: list[int]) -> bool:
    if not family_pages:
        return False
    target_pages = set(family_pages)
    target_pages.add(max(1, family_pages[0] - 1))
    for block in blocks:
        page = int(block.get("page", 0) or 0)
        if page not in target_pages:
            continue
        marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
        text = str(block.get("text") or block.get("block_content") or "").strip().lower()
        if marker_type in {"canonical_section_name", "short_fragment", "none"} and text in _REFERENCE_HEADING_TEXTS:
            return True
    return False


def _build_reference_family_candidate(
    blocks: list[dict],
    family_key: tuple[Any, ...],
    item_count: int,
    family_pages: list[int],
    marker_count: int,
    page_count: int,
) -> dict[str, Any]:
    tail_continuity = _reference_tail_continuity_score(family_pages, page_count)
    heading_present = _has_reference_heading_near_family(blocks, family_pages)
    font_family, font_size_bucket, width_bucket, x_center_bucket = family_key
    strong_tail = tail_continuity >= 1.0
    strong_marker_family = item_count >= 2 and marker_count >= 2
    heading_supported_singleton = heading_present and item_count >= 1 and marker_count >= 1
    can_accept = strong_tail and (strong_marker_family or heading_supported_singleton)
    reason = "reference_markers_with_tail_continuity"
    if heading_present:
        reason = f"{reason}_and_heading_binding"
    if can_accept:
        return {
            "status": "ACCEPT",
            "family_name": "reference_family",
            "reason": reason,
            "item_count": item_count,
            "marker_count": marker_count,
            "sample_pages": family_pages,
            "tail_continuity": tail_continuity,
            "heading_binding": heading_present,
            "font_family_norm": font_family,
            "font_size_bucket": font_size_bucket,
            "width_bucket": width_bucket,
            "x_center_bucket": x_center_bucket,
        }
    return {
        "status": "HOLD",
        "family_name": "reference_family",
        "reason": "insufficient_reference_family_evidence",
        "item_count": item_count,
        "marker_count": marker_count,
        "sample_pages": family_pages,
        "tail_continuity": tail_continuity,
        "heading_binding": heading_present,
        "font_family_norm": font_family,
        "font_size_bucket": font_size_bucket,
        "width_bucket": width_bucket,
        "x_center_bucket": x_center_bucket,
    }


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
