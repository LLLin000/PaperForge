from __future__ import annotations

import dataclasses
import re
from collections import namedtuple
from dataclasses import dataclass, field

from paperforge.worker.ocr_decisions import record_decision
from paperforge.worker.ocr_families import (
    discover_body_family_anchor,
    discover_reference_family_anchor,
    partition_zone_families,
)
from paperforge.worker.ocr_roles import (
    _BACKMATTER_TITLE_DENY_LIST,
    _is_near_figure_media,
    _looks_like_affiliation,
    _looks_like_author_list,
)
from paperforge.worker.ocr_scores import score_structured_insert

_TAIL_ROLES = frozenset(
    {
        "backmatter_boundary_heading",
        "backmatter_heading",
        "backmatter_body",
        "tail_candidate_body",
        "reference_heading",
        "reference_item",
    }
)

TailBoundary = namedtuple(
    "TailBoundary",
    [
        "body_end_page",
        "backmatter_start",
        "references_start",
        "spread_start",
        "spread_end",
        "is_clean_separated",
        "reason",
    ],
)


@dataclass
class PagePosition:
    page: int
    y: float


@dataclass
class PageLayoutProfile:
    column_count: int = 1
    column_boundaries: list[float] = field(default_factory=list)
    layout_type: str = "single_column"
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)


@dataclass
class ReadingSegment:
    page: int
    column_index: int
    y_top: float
    y_bottom: float
    block_indices: list[int]
    semantic_hint: str = ""


@dataclass
class ReferenceZone:
    page: int
    column_index: int
    y_start: float
    y_end: float
    block_indices: list[int]


@dataclass
class DocumentStructure:
    body_end_page: int | None = None
    backmatter_start: PagePosition | None = None
    references_start: PagePosition | None = None
    spread_start: int | None = None
    spread_end: int | None = None
    backmatter_form: str = "flat"
    body_family_anchor: dict | None = None
    reference_family_anchor: dict | None = None
    page_layouts: dict[int, PageLayoutProfile] | None = None
    tail_reading_order: list[dict] | None = None
    reference_zones: list[dict] | None = None
    region_bus: dict | None = None
    span_coverage: dict | None = None
    layout_audit: dict | None = None
    tail_boundary_score: dict = field(default_factory=dict)
    abstract_span: dict | None = None
    reference_zone: dict | None = None
    role_gate_summary: dict | None = None


@dataclass
class RegionPrepass:
    block_regions: dict[int, str]
    frontmatter_indices: set[int]
    structured_insert_indices: set[int]
    body_candidate_indices: set[int]
    confidence_by_index: dict[int, float]


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _next_nonempty_block_same_page(blocks: list[dict], idx: int) -> dict | None:
    """Return the next non-empty block on the same page after idx, or None."""
    page = blocks[idx].get("page")
    if page is None:
        return None
    for j in range(idx + 1, len(blocks)):
        if blocks[j].get("page") != page:
            return None
        text = _block_text(blocks[j]).strip()
        if text:
            return blocks[j]
    return None


_BACKMATTER_BODY_SIGNALS = re.compile(
    r"\b(?:declare|conflict|interest|funding|support|grant|author|contribut|"
    r"acknowledge|thank|ethic|review|approv|consent|availab|data|material|"
    r"competing|financial|disclos|report|none|no conflict|nothing to declare)\b",
    re.IGNORECASE,
)


def _looks_like_tail_body(block: dict) -> bool:
    """Return True if the block looks like short backmatter body text.

    Heuristics: short paragraphs with backmatter-related vocabulary,
    no section-heading formatting, and a word count below the body spine
    threshold.
    """
    text = _block_text(block).strip()
    if not text:
        return False
    words = text.split()
    if len(words) > 80:
        return False
    role = block.get("role", "")
    if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
        return False
    if _BACKMATTER_BODY_SIGNALS.search(text):
        return True
    if len(words) <= 25:
        return True
    return False


_BIOGRAPHY_TEXT_SIGNALS = re.compile(
    r"\b(?:received?\s+(?:her|his|their)\s+(?:PhD|Doctorate|doctoral|degree)|"
    r"is\s+a\s+(?:professor|researcher|scientist|physician|postdoc|fellow)|"
    r"currently\s+(?:a|an|at)|"
    r"(?:Department|Laboratory|Institute|University|College|School|Center|Hospital)\s+of\b|"
    r"earned?\s+(?:her|his|their)\s+(?:degree|PhD)|"
    r"completed?\s+(?:her|his|their)\s+(?:PhD|doctoral|residency|fellowship)|"
    r"works?\s+(?:in|at|on)\b|"
    r"research(?:s|ing)?\s+(?:interests?|focus|areas?|includes?|encompasses?)|"
    r"specializes?\s+in\b|"
    r"focused?\s+(?:on|in)\b|"
    r"authored?\s+(?:over|more than|\d+)|"
    r"published?\s+(?:over|more than|\d+)|"
    r"has\s+(?:published|authored|co-authored)|"
    r"(?:MD|PhD|MSc|M\.D\.|Ph\.D\.)\b)",
    re.IGNORECASE,
)


def _looks_like_biography_text(text: str) -> bool:
    """Return True if the text looks like a biography sentence cluster.

    Detects patterns like "X received PhD from...", "X is a professor at...",
    "X, MD, PhD, is a researcher in...", etc.
    """
    if not text:
        return False
    words = text.split()
    if len(words) > 80:
        return False
    if len(words) < 5:
        return False
    if _BIOGRAPHY_TEXT_SIGNALS.search(text):
        return True
    return False


def _looks_like_box_anchor(text: str) -> bool:
    normalized = text.strip().lower()
    return bool(
        re.match(r"^box\s*\.?\s*\d+\b", normalized)
        or normalized in {"key points", "highlights", "summary", "take-home messages"}
    )


def _build_region_prepass(blocks: list[dict]) -> RegionPrepass:
    block_regions: dict[int, str] = {}
    confidence_by_index: dict[int, float] = {}
    frontmatter_indices: set[int] = set()
    structured_insert_indices: set[int] = set()
    body_candidate_indices: set[int] = set()

    by_page: dict[int, list[tuple[int, dict]]] = {}
    for idx, block in enumerate(blocks):
        by_page.setdefault(int(block.get("page", 1) or 1), []).append((idx, block))

    for page, page_items in by_page.items():
        page_items.sort(key=lambda item: (item[1].get("bbox") or item[1].get("block_bbox") or [0, 0, 0, 0])[1])
        last_insert_on_page = False
        last_insert_anchor_kind = ""
        for idx, block in page_items:
            role = block.get("role", "")
            text = _block_text(block).strip().lower()
            bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
            page_height = block.get("page_height") or 1700
            page_width = block.get("page_width") or 1200
            y_top = bbox[1] if len(bbox) >= 4 else 0

            region = "body"
            confidence = 0.5

            insert_score = score_structured_insert(block, body_spine_match=False, cluster_coherent=last_insert_on_page)
            block["insert_score"] = insert_score

            if insert_score["decision"] == "structured_insert":
                region = "structured_insert"
                confidence = insert_score["score"]
                last_insert_anchor_kind = "container" if block.get("_in_visual_container") else "box"
            elif insert_score["decision"] == "structured_insert_candidate":
                region = "body"
                confidence = insert_score["score"]
            elif page == 1 and (
                role in {"paper_title", "authors", "affiliation", "frontmatter_noise"} or y_top < page_height * 0.22
            ):
                region = "frontmatter"
                confidence = 0.8
            last_insert_on_page = region == "structured_insert"
            if region != "structured_insert":
                last_insert_anchor_kind = ""

            block_regions[idx] = region
            confidence_by_index[idx] = confidence
            if region == "frontmatter":
                frontmatter_indices.add(idx)
            elif region == "structured_insert":
                structured_insert_indices.add(idx)
            else:
                body_candidate_indices.add(idx)

    return RegionPrepass(
        block_regions=block_regions,
        frontmatter_indices=frontmatter_indices,
        structured_insert_indices=structured_insert_indices,
        body_candidate_indices=body_candidate_indices,
        confidence_by_index=confidence_by_index,
    )


def _compute_span_coverage(blocks: list[dict]) -> dict:
    """Compute span metadata coverage across the document.

    Returns:
        coverage_ratio: float 0-1
        coverage_quality: str "strong" (>=0.7), "moderate" (>=0.3), "weak" (<0.3)
        blocks_with_span: int
        blocks_without_span: int
        degraded_mode_active: bool
    """
    total = len(blocks)
    if total == 0:
        return {
            "coverage_ratio": 0.0,
            "coverage_quality": "weak",
            "blocks_with_span": 0,
            "blocks_without_span": 0,
            "degraded_mode_active": True,
        }

    with_span = sum(1 for b in blocks if b.get("span_metadata"))
    ratio = with_span / total

    if ratio >= 0.7:
        quality = "strong"
    elif ratio >= 0.3:
        quality = "moderate"
    else:
        quality = "weak"

    return {
        "coverage_ratio": ratio,
        "coverage_quality": quality,
        "blocks_with_span": with_span,
        "blocks_without_span": total - with_span,
        "degraded_mode_active": quality == "weak",
    }


_LAYOUT_ELIGIBLE_ROLES = {"body_paragraph", "list_item", "tail_candidate_body", "reference_item", "backmatter_body"}


def _is_layout_eligible_block(block: dict) -> bool:
    role = block.get("role", "")
    if role not in _LAYOUT_ELIGIBLE_ROLES:
        return False
    bbox = block.get("bbox") or block.get("block_bbox") or []
    page_width = float(block.get("page_width") or 1200)
    if len(bbox) >= 4 and (bbox[2] - bbox[0]) > page_width * 0.85:
        return False
    return True


def _cluster_page_columns(page_blocks: list[dict], page_width: float) -> list[float]:
    """Cluster block x-centers by column using a gap-based approach.

    Returns one representative x-center per column cluster.
    """
    centers: list[float] = []
    for block in page_blocks:
        bbox = block.get("bbox") or block.get("block_bbox")
        if not bbox or len(bbox) < 4:
            continue
        block_width = bbox[2] - bbox[0]
        if block_width <= 50:
            continue
        x_center = (bbox[0] + bbox[2]) / 2
        centers.append(x_center)

    if not centers:
        return [page_width / 2]

    centers.sort()
    gap_threshold = page_width * 0.15
    clusters: list[list[float]] = [[centers[0]]]

    for c in centers[1:]:
        if c - clusters[-1][-1] > gap_threshold:
            clusters.append([c])
        else:
            clusters[-1].append(c)

    return [sum(cluster) / len(cluster) for cluster in clusters]


def _classify_page_layout(page_blocks: list[dict], page_width: float, page_height: float) -> PageLayoutProfile:
    """Classify a page's layout based on column clusters and role distribution."""
    centers = _cluster_page_columns(page_blocks, page_width)
    column_count = len(centers)

    if column_count == 1:
        return PageLayoutProfile(
            column_count=1,
            column_boundaries=centers,
            layout_type="single_column",
            confidence=0.7,
            evidence=["eligible_body_blocks"],
        )

    if column_count == 2:
        col_blocks: dict[int, list[str]] = {0: [], 1: []}
        for block in page_blocks:
            bbox = block.get("bbox") or block.get("block_bbox")
            if not bbox or len(bbox) < 4:
                continue
            x_center = (bbox[0] + bbox[2]) / 2
            col = 0 if x_center < page_width / 2 else 1
            col_blocks[col].append(block.get("role", ""))

        body_roles = {
            "body_paragraph",
            "section_heading",
            "subsection_heading",
            "sub_subsection_heading",
        }

        col_has_body: dict[int, bool] = {}
        col_has_tail: dict[int, bool] = {}
        for col_idx, roles in col_blocks.items():
            col_has_body[col_idx] = bool(set(roles) & body_roles)
            col_has_tail[col_idx] = bool(set(roles) & _TAIL_ROLES)

        one_side_body = col_has_body[0] and not col_has_tail[0]
        other_side_tail = not col_has_body[1] and col_has_tail[1]
        swapped = col_has_body[1] and not col_has_tail[1]
        swapped_tail = not col_has_body[0] and col_has_tail[0]

        if (one_side_body and other_side_tail) or (swapped and swapped_tail):
            return PageLayoutProfile(
                column_count=2,
                column_boundaries=centers,
                layout_type="mixed_tail",
                confidence=0.6,
                evidence=["eligible_body_blocks", "two_center_clusters"],
            )

        return PageLayoutProfile(
            column_count=2,
            column_boundaries=centers,
            layout_type="two_column",
            confidence=0.7,
            evidence=["eligible_body_blocks"],
        )

    return PageLayoutProfile(
        column_count=column_count,
        column_boundaries=centers,
        layout_type="two_column",
        confidence=0.5,
        evidence=["eligible_body_blocks", "wide_dispersion"],
    )


def _build_page_layout_profiles(blocks: list[dict]) -> dict[int, PageLayoutProfile]:
    """Build per-page layout profiles for all pages that have blocks."""
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)

    profiles: dict[int, PageLayoutProfile] = {}
    for page, page_blocks in by_page.items():
        page_width = max((b.get("page_width", 0) or 0) for b in page_blocks) or 1200
        page_height = max((b.get("page_height", 0) or 0) for b in page_blocks) or 1600
        eligible_blocks = [block for block in page_blocks if _is_layout_eligible_block(block)]
        excluded_count = len(page_blocks) - len(eligible_blocks)
        profile = _classify_page_layout(eligible_blocks, page_width, page_height)
        if excluded_count:
            profile.evidence.append("excluded_non_body_blocks")
        if len(eligible_blocks) < 2:
            profile.confidence = min(profile.confidence, 0.35)
            profile.evidence.append("few_eligible_blocks")
        profiles[page] = profile

    return profiles


def _block_bbox(block: dict) -> list[float] | None:
    bbox = block.get("bbox") or block.get("block_bbox")
    return bbox if bbox and len(bbox) >= 4 else None


def _block_y_top(block: dict) -> float:
    bbox = _block_bbox(block)
    return bbox[1] if bbox else 0.0


def _block_y_bottom(block: dict) -> float:
    bbox = _block_bbox(block)
    return bbox[3] if bbox else 0.0


_REFERENCE_ZONE_MARKER_TYPES = {
    "reference_numeric_bracket",
    "reference_numeric_dot",
    "reference_numeric_parenthesis",
    "reference_pattern",
    "citation_line",
}

_REFERENCE_ZONE_HEADING_TEXTS = {"references", "bibliography"}

_TAIL_NONREF_HEADING_DENY_TYPES = {
    "reference_numeric_bracket",
    "reference_numeric_dot",
    "reference_numeric_parenthesis",
    "reference_pattern",
    "citation_line",
    "preproof_marker",
}


def _make_zone(
    status: str,
    block_ids: list[str | int],
    *,
    composite_block_ids: list[str] | None = None,
    **extra: object,
) -> dict:
    zone = {"status": status, "block_ids": block_ids}
    if composite_block_ids is not None:
        zone["composite_block_ids"] = composite_block_ids
    zone.update(extra)
    return zone


def _canonical_section_text(block: dict) -> str:
    return _block_text(block).strip().lower()


def _strip_inline_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def _is_page1_body_start(block: dict, *, seen_title_or_author: bool) -> bool:
    """Detect when page 1 frontmatter ends and body content begins."""
    if not seen_title_or_author:
        return False
    role = block.get("role") or block.get("seed_role")
    if role == "unassigned":
        role = block.get("seed_role")
    text = str(block.get("text") or "").strip()
    words = text.split()
    if role in {"section_heading", "subsection_heading"}:
        return True
    if role == "body_paragraph" and len(words) >= 20:
        lower = text.lower()
        if not lower.startswith(("correspondence", "received", "accepted", "published", "doi")):
            return True
    return False


def _is_reference_heading_candidate(block: dict) -> bool:
    marker_type = (block.get("marker_signature") or {}).get("type") or "none"
    if _canonical_section_text(block) not in _REFERENCE_ZONE_HEADING_TEXTS:
        return False
    return marker_type in {"canonical_section_name", "short_fragment", "none"}


def _is_reference_item_candidate(block: dict) -> bool:
    marker_type = (block.get("marker_signature") or {}).get("type") or "none"
    if marker_type in _REFERENCE_ZONE_MARKER_TYPES:
        return True
    text = _block_text(block).strip()
    if text and len(text) >= 40:
        lower = text.lower()
        if (
            re.search(r"\((?:19|20)\d{2}[a-z]?\)|\b(?:19|20)\d{2}\.", text)
            and (text.count(",") >= 2 or "et al." in lower or "doi:" in lower)
        ):
            return True
    # Old-style references can miss explicit markers, but they should still
    # carry reference-family evidence rather than relying on the pre-gate role
    # alone. Without this guard, body citations can poison early pages and make
    # reference_zone swallow the document.
    if (
        block.get("role") == "reference_item"
        and str(block.get("style_family") or "") == "reference_like"
        and marker_type not in {
        "heading_arabic",
        "heading_decimal",
        "heading_roman",
        "heading_alpha",
        }
    ):
        return True
    return False


def _looks_like_short_heading_text(text: str) -> bool:
    if not text:
        return False
    words = [token for token in text.split() if token]
    if not words or len(words) > 8:
        return False
    if len(text) > 80:
        return False
    return text[:1].isupper() or text.isupper()


def _is_tail_nonref_heading_candidate(block: dict, body_anchor: dict | None = None) -> bool:
    marker_type = (block.get("marker_signature") or {}).get("type") or "none"
    if marker_type in _TAIL_NONREF_HEADING_DENY_TYPES:
        return False
    if marker_type in {"heading_numbered", "heading_arabic", "heading_decimal", "heading_roman", "heading_alpha"}:
        return False
    text = _canonical_section_text(block)
    if not text or text in _REFERENCE_ZONE_HEADING_TEXTS:
        return False

    score = 0
    if marker_type == "canonical_section_name":
        score += 2

    if _looks_like_short_heading_text(_block_text(block).strip()):
        score += 1

    span_signature = block.get("span_signature") or {}
    layout_signature = block.get("layout_signature") or {}
    font_size = span_signature.get("font_size_median")
    if font_size is not None and font_size >= 10.0:
        score += 1
    if span_signature.get("is_bold"):
        score += 1

    body_anchor = body_anchor or {}
    body_font_size = body_anchor.get("font_size_bucket")
    if body_font_size is not None and font_size is not None and font_size >= float(body_font_size) + 0.5:
        score += 1

    body_width = body_anchor.get("width_bucket")
    block_width = layout_signature.get("width")
    if body_width is not None and block_width is not None and block_width <= float(body_width) - 25:
        score += 1

    body_font_family = body_anchor.get("font_family_norm")
    block_font_family = span_signature.get("font_family_norm")
    if body_font_family and block_font_family and body_font_family != block_font_family:
        score += 1

    return score >= 2


def _infer_tail_hold_band(
    blocks: list[dict],
    body_sample_pages: list[int],
    first_reference_page: int | None,
    tail_spread: TailBoundary | None,
    body_anchor: dict | None = None,
) -> tuple[int | None, int | None]:
    if tail_spread is not None and tail_spread.spread_start is not None and tail_spread.spread_end is not None:
        start_page = tail_spread.spread_start
        end_page = tail_spread.spread_end
        if first_reference_page is not None:
            end_page = min(end_page, first_reference_page - 1)
        if end_page < start_page:
            return None, None
        return start_page, end_page

    if first_reference_page is None:
        return None, None

    body_guard_page = max(body_sample_pages) if body_sample_pages else 0
    candidate_pages = sorted(
        {
            int(block.get("page", 0) or 0)
            for block in blocks
            if body_guard_page < int(block.get("page", 0) or 0) < first_reference_page
            and _is_tail_nonref_heading_candidate(block, body_anchor=body_anchor)
        }
    )
    if not candidate_pages:
        return None, None
    return candidate_pages[0], first_reference_page - 1


def _page_band(start_page: int | None, end_page: int | None) -> dict[str, int] | None:
    if start_page is None or end_page is None:
        return None
    return {"start_page": start_page, "end_page": end_page}


def _zone_block_key(block: dict) -> str:
    page = int(block.get("page", 0) or 0)
    block_id = str(block.get("block_id") or "")
    return f"p{page}:{block_id}"


def _canonical_block_id(block: dict) -> str | int | None:
    return block.get("block_id")


def _artifact_block_id(block: dict, duplicate_block_ids: set[str]) -> str | int | None:
    block_id = _canonical_block_id(block)
    if block_id is None:
        return None
    if str(block_id) in duplicate_block_ids:
        return _zone_block_key(block)
    return block_id


def _duplicate_block_ids_from_blocks(blocks: list[dict]) -> set[str]:
    counts: dict[str, int] = {}
    for block in blocks:
        block_id = _canonical_block_id(block)
        if block_id is None:
            continue
        key = str(block_id)
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _is_frontmatter_side_candidate(block: dict, body_anchor: dict | None = None) -> bool:
    page = int(block.get("page", 0) or 0)
    if page <= 0:
        return False

    marker_type = (block.get("marker_signature") or {}).get("type") or "none"
    if marker_type == "preproof_marker" or _is_reference_item_candidate(block):
        return False

    text = str(block.get("text") or block.get("block_content") or "").strip()
    if not text:
        return False

    lower = text.lower()
    bbox = _block_bbox(block)
    page_width = float(block.get("page_width") or 0)
    page_height = float(block.get("page_height") or 0)
    block_width = (bbox[2] - bbox[0]) if bbox else 0.0
    x_center = ((bbox[0] + bbox[2]) / 2.0) if bbox else 0.0
    narrow = page_width > 0 and block_width > 0 and block_width <= page_width * 0.38
    side_column = (
        page_width > 0 and bbox is not None and (x_center <= page_width * 0.28 or x_center >= page_width * 0.72)
    )
    top_half = page_height > 0 and bbox is not None and bbox[1] <= page_height * 0.55

    furniture_phrases = (
        "correspondence",
        "corresponding author",
        "highlights",
        "received:",
        "accepted:",
        "published online",
        "copyright",
        "edited by",
        "reviewed by",
        "specialty section",
        "citation:",
        "how to cite",
        "to cite this article",
        "conflict of interest",
        "equal contribution",
        "these authors contributed equally",
        "orcid",
    )
    if any(phrase in lower for phrase in furniture_phrases):
        if page == 1:
            return True
        if (
            page <= 2
            and top_half
            and any(phrase in lower for phrase in ("correspondence", "corresponding author", "highlights"))
        ):
            return True
        return top_half and (narrow or side_column)

    body_anchor = body_anchor or {}
    body_width = body_anchor.get("width_bucket")
    body_font_family = body_anchor.get("font_family_norm")
    span_signature = block.get("span_signature") or {}
    block_font_family = span_signature.get("font_family_norm")
    if page <= 2 and top_half and (narrow or side_column):
        if body_width is not None and block_width and block_width <= float(body_width) - 100:
            return True
        if body_font_family and block_font_family and block_font_family != body_font_family:
            return True

    return False


def infer_zones(
    blocks: list[dict],
    anchors: dict[str, dict] | None,
    tail_spread: TailBoundary | None = None,
) -> dict[str, dict]:
    """Infer an explicit zone bus from anchors and coarse boundary bands."""
    anchors = anchors or {}
    body_anchor = anchors.get("body_family_anchor") or {}
    reference_anchor = anchors.get("reference_family_anchor") or {}
    block_id_counts: dict[str, int] = {}
    for block in blocks:
        block_id = _canonical_block_id(block)
        if block_id is None:
            continue
        key = str(block_id)
        block_id_counts[key] = block_id_counts.get(key, 0) + 1
    duplicate_block_ids = {key for key, count in block_id_counts.items() if count > 1}
    pages = sorted({int(block.get("page", 0) or 0) for block in blocks if int(block.get("page", 0) or 0) > 0})
    max_page = pages[-1] if pages else None

    body_sample_pages = sorted(int(page) for page in body_anchor.get("sample_pages") or [] if int(page) > 0)
    body_anchor_ok = body_anchor.get("status") == "ACCEPT" and bool(body_sample_pages)

    reference_heading_blocks = [block for block in blocks if _is_reference_heading_candidate(block)]
    reference_item_blocks = [block for block in blocks if _is_reference_item_candidate(block)]

    first_reference_page: int | None = None
    body_guard_page = max(body_sample_pages) if body_sample_pages else 0
    if reference_anchor.get("status") == "ACCEPT" and reference_item_blocks:
        heading_pages = [int(block.get("page", 0) or 0) for block in reference_heading_blocks]
        item_pages = [int(block.get("page", 0) or 0) for block in reference_item_blocks]
        eligible_heading_pages = [page for page in heading_pages if page >= body_guard_page]
        eligible_item_pages = [page for page in item_pages if page >= body_guard_page]
        if eligible_heading_pages:
            first_reference_page = min(eligible_heading_pages)
        elif eligible_item_pages:
            first_reference_page = min(eligible_item_pages)

    # HOLD-fallback: reference items exist but anchor evidence is weak.
    # Derive first_reference_page from dense tail-side item clusters instead.
    if first_reference_page is None and reference_item_blocks:
        fallback_item_pages = [
            int(block.get("page", 0) or 0)
            for block in reference_item_blocks
            if int(block.get("page", 0) or 0) > body_guard_page
        ]
        if fallback_item_pages:
            page_counts: dict[int, int] = {}
            for p in fallback_item_pages:
                page_counts[p] = page_counts.get(p, 0) + 1
            candidate_pages = sorted(p for p, c in page_counts.items() if c >= 3)
            if candidate_pages:
                first_reference_page = candidate_pages[0]

    reference_blocks = [
        block
        for block in reference_item_blocks
        if first_reference_page is not None
        and int(block.get("page", 0) or 0) >= first_reference_page
        and block.get("block_id") is not None
    ]
    reference_block_ids = [
        _artifact_block_id(block, duplicate_block_ids)
        for block in reference_blocks
    ]
    reference_composite_ids = [
        _zone_block_key(block)
        for block in reference_item_blocks
        if first_reference_page is not None
        and int(block.get("page", 0) or 0) >= first_reference_page
        and block.get("block_id") is not None
    ]

    _POST_REFERENCE_BACKMATTER_HEADINGS = {
        "biographies", "table and figure captions", "figure captions",
        "table captions", "graphical abstract",
    }
    post_ref_backmatter_start: int | None = None
    post_ref_heading_ids: list[str | int] = []
    if first_reference_page is not None:
        for block in sorted(blocks, key=lambda b: (int(b.get("page", 0) or 0), (b.get("bbox") or [0, 0, 0, 0])[1])):
            page = int(block.get("page", 0) or 0)
            if page < first_reference_page:
                continue
            text = str(block.get("text") or "").strip().lower()
            role = block.get("role") or block.get("seed_role")
            if role == "unassigned":
                role = block.get("seed_role")
            if text in _POST_REFERENCE_BACKMATTER_HEADINGS and role in {
                "section_heading", "subsection_heading", "sub_subsection_heading",
                "backmatter_heading_candidate", "reference_heading",
            }:
                post_ref_backmatter_start = page
                bid = _artifact_block_id(block, duplicate_block_ids)
                if bid is not None:
                    post_ref_heading_ids.append(bid)
                break
    if post_ref_backmatter_start is not None:
        reference_blocks = [
            b for b in reference_blocks
            if int(b.get("page", 0) or 0) < post_ref_backmatter_start
        ]
        reference_block_ids = [
            _artifact_block_id(b, duplicate_block_ids) for b in reference_blocks
        ]
        reference_composite_ids = [
            _zone_block_key(b) for b in reference_item_blocks
            if first_reference_page is not None
            and int(b.get("page", 0) or 0) >= first_reference_page
            and int(b.get("page", 0) or 0) < post_ref_backmatter_start
            and b.get("block_id") is not None
        ]

    preproof_blocks = [
        block for block in blocks if ((block.get("marker_signature") or {}).get("type") or "none") == "preproof_marker"
    ]
    preproof_pages = sorted(
        {int(block.get("page", 0) or 0) for block in preproof_blocks if int(block.get("page", 0) or 0) > 0}
    )

    display_blocks = [
        block
        for block in blocks
        if ((block.get("marker_signature") or {}).get("type") or "none")
        in {"figure_number", "table_number", "panel_label"}
        and block.get("block_id") is not None
    ]
    display_block_ids = [_artifact_block_id(block, duplicate_block_ids) for block in display_blocks]
    display_composite_ids = [_zone_block_key(block) for block in display_blocks]

    page1_candidates = [
        b for b in blocks
        if int(b.get("page", 0) or 0) == 1
        and ((b.get("marker_signature") or {}).get("type") or "none") != "preproof_marker"
        and not _is_reference_item_candidate(b)
        and block.get("block_id") is not None
    ]
    page1_candidates.sort(key=lambda b: (
        (b.get("bbox") or [0, 0, 0, 0])[1],
        (b.get("bbox") or [0, 0, 0, 0])[0],
    ))
    frontmatter_main_blocks = []
    seen_title_or_author = False
    body_started = False
    for block in page1_candidates:
        role = block.get("role") or block.get("seed_role")
        if role == "unassigned":
            role = block.get("seed_role")
        if role in {"paper_title", "authors", "frontmatter_support", "affiliation"}:
            seen_title_or_author = True
        if _is_page1_body_start(block, seen_title_or_author=seen_title_or_author):
            body_started = True
        if not body_started:
            frontmatter_main_blocks.append(block)
    frontmatter_main_ids = [_artifact_block_id(block, duplicate_block_ids) for block in frontmatter_main_blocks]
    frontmatter_main_composite_ids = [_zone_block_key(block) for block in frontmatter_main_blocks]

    frontmatter_main_id_set = set(frontmatter_main_ids)
    frontmatter_side_blocks = [
        block
        for block in blocks
        if _is_frontmatter_side_candidate(block, body_anchor=body_anchor)
        and _artifact_block_id(block, duplicate_block_ids) not in frontmatter_main_id_set
        and block.get("block_id") is not None
    ]
    frontmatter_side_ids = [_artifact_block_id(block, duplicate_block_ids) for block in frontmatter_side_blocks]
    frontmatter_side_composite_ids = [_zone_block_key(block) for block in frontmatter_side_blocks]
    frontmatter_side_id_set = set(frontmatter_side_ids)
    frontmatter_side_pages = sorted(
        {
            int(block.get("page", 0) or 0)
            for block in blocks
            if _artifact_block_id(block, duplicate_block_ids) in frontmatter_side_id_set and int(block.get("page", 0) or 0) > 0
        }
    )

    tail_hold_start, tail_hold_end = _infer_tail_hold_band(
        blocks,
        body_sample_pages=body_sample_pages,
        first_reference_page=first_reference_page,
        tail_spread=tail_spread,
        body_anchor=body_anchor,
    )

    # Veto tail start on pages with strong body continuation
    if tail_hold_start is not None:
        by_page: dict[int, list[dict]] = {}
        for b in blocks:
            page = int(b.get("page", 0) or 0)
            if page > 0:
                by_page.setdefault(page, []).append(b)
        while tail_hold_start and _page_has_strong_body_continuation(by_page.get(tail_hold_start, [])):
            tail_hold_start += 1

    body_end_page = first_reference_page - 1 if first_reference_page is not None else max_page
    if tail_hold_start is not None:
        candidate_body_end = tail_hold_start - 1
        if body_end_page is None or candidate_body_end < body_end_page:
            body_end_page = candidate_body_end

    # Find the reference heading block on the first reference page so we can
    # split same-page blocks by vertical position (above = body, below = ref/tail).
    refs_start_page = first_reference_page
    ref_heading_block = None
    ref_heading_top = 0.0
    if refs_start_page is not None:
        for block in reference_heading_blocks:
            if int(block.get("page", 0) or 0) == refs_start_page:
                ref_heading_block = block
                ref_heading_top = _block_y_top(block)
                break

    body_blocks = [
        block
        for block in blocks
        if body_anchor_ok
        and int(block.get("page", 0) or 0) > 1
        and (
            (body_end_page is None or int(block.get("page", 0) or 0) <= body_end_page)
            or (refs_start_page is not None and int(block.get("page", 0) or 0) == refs_start_page
                and ref_heading_block is not None
                and _block_y_bottom(block) <= ref_heading_top)
        )
        and not _is_reference_item_candidate(block)
        and _artifact_block_id(block, duplicate_block_ids) not in frontmatter_side_id_set
        and block.get("block_id") is not None
    ]
    body_block_ids = [_artifact_block_id(block, duplicate_block_ids) for block in body_blocks]
    body_composite_ids = [_zone_block_key(block) for block in body_blocks]

    # Blocks below the reference heading on the same page that are NOT
    # reference items go into tail_nonref_hold_zone (gratitude text, etc.).
    same_page_tail_blocks = []
    if refs_start_page is not None and ref_heading_block is not None:
        for block in blocks:
            if int(block.get("page", 0) or 0) != refs_start_page:
                continue
            if _block_y_top(block) <= ref_heading_top:
                continue
            if _is_reference_item_candidate(block):
                continue
            if _is_reference_heading_candidate(block):
                continue
            if block.get("block_id") is None:
                continue
            same_page_tail_blocks.append(block)

    tail_nonref_hold_blocks = [
        block
        for block in blocks
        if tail_hold_start is not None
        and tail_hold_end is not None
        and tail_hold_start <= int(block.get("page", 0) or 0) <= tail_hold_end
        and not _is_reference_item_candidate(block)
        and not _is_reference_heading_candidate(block)
        and block.get("block_id") is not None
    ]
    # Merge same-page tail blocks into tail_nonref_hold (deduplicate by block_id).
    seen_tail_ids = {_artifact_block_id(b, duplicate_block_ids) for b in tail_nonref_hold_blocks}
    for block in same_page_tail_blocks:
        bid = _artifact_block_id(block, duplicate_block_ids)
        if bid not in seen_tail_ids:
            tail_nonref_hold_blocks.append(block)
            seen_tail_ids.add(bid)
    tail_nonref_hold_ids = [_artifact_block_id(block, duplicate_block_ids) for block in tail_nonref_hold_blocks]
    tail_nonref_hold_composite_ids = [_zone_block_key(block) for block in tail_nonref_hold_blocks]

    reference_end_page = max(
        [int(block.get("page", 0) or 0) for block in reference_item_blocks if int(block.get("page", 0) or 0) > 0],
        default=first_reference_page,
    )

    return {
        "frontmatter_main_zone": _make_zone(
            "ACCEPT" if frontmatter_main_ids else "HOLD",
            frontmatter_main_ids,
            composite_block_ids=frontmatter_main_composite_ids,
            boundary_band=_page_band(1, 1) if frontmatter_main_ids else None,
        ),
        "frontmatter_side_zone": _make_zone(
            "ACCEPT" if frontmatter_side_ids else "HOLD",
            frontmatter_side_ids,
            composite_block_ids=frontmatter_side_composite_ids,
            boundary_band=_page_band(frontmatter_side_pages[0], frontmatter_side_pages[-1])
            if frontmatter_side_pages
            else None,
        ),
        "body_zone": _make_zone(
            "ACCEPT" if body_block_ids else "HOLD",
            body_block_ids,
            composite_block_ids=body_composite_ids,
            anchor_family="body_family_anchor" if body_anchor_ok else None,
            boundary_band=_page_band(min(body_sample_pages) if body_sample_pages else None, body_end_page),
        ),
        "reference_zone": _make_zone(
            "ACCEPT" if reference_block_ids else ("HOLD" if reference_anchor.get("status") == "ACCEPT" else "REJECT"),
            reference_block_ids,
            composite_block_ids=reference_composite_ids,
            anchor_family="reference_family_anchor" if reference_anchor.get("status") == "ACCEPT" else None,
            boundary_band=_page_band(first_reference_page, reference_end_page),
        ),
        "display_zone": _make_zone(
            "ACCEPT" if display_block_ids else "HOLD",
            display_block_ids,
            composite_block_ids=display_composite_ids,
            boundary_band=None,
        ),
        "tail_nonref_hold_zone": _make_zone(
            "ACCEPT" if tail_nonref_hold_ids else "HOLD",
            tail_nonref_hold_ids,
            composite_block_ids=tail_nonref_hold_composite_ids,
            boundary_band=_page_band(tail_hold_start, tail_hold_end),
        ),
        "post_reference_backmatter_zone": _make_zone(
            "ACCEPT" if post_ref_backmatter_start is not None and post_ref_heading_ids else "HOLD",
            post_ref_heading_ids,
            composite_block_ids=[
                _zone_block_key(b) for b in blocks
                if post_ref_backmatter_start is not None
                and int(b.get("page", 0) or 0) >= post_ref_backmatter_start
                and b.get("block_id") is not None
                and not (
                    _is_reference_item_candidate(b)
                    and int(b.get("page", 0) or 0) < post_ref_backmatter_start
                )
            ],
            boundary_band=_page_band(post_ref_backmatter_start, max_page) if post_ref_backmatter_start else None,
        ),
        "preproof_cover_zone": _make_zone(
            "ACCEPT" if preproof_pages else "HOLD",
            [_artifact_block_id(block, duplicate_block_ids) for block in preproof_blocks if block.get("block_id") is not None],
            composite_block_ids=[_zone_block_key(block) for block in preproof_blocks if block.get("block_id") is not None],
            boundary_band=_page_band(preproof_pages[0], preproof_pages[-1]) if preproof_pages else None,
        ),
    }


def _classify_segment_hint(blocks: list[dict]) -> str:
    roles = {b.get("role") for b in blocks}
    body_roles = {
        "body_paragraph",
        "section_heading",
        "subsection_heading",
        "sub_subsection_heading",
    }
    backmatter_roles = {
        "backmatter_heading",
        "backmatter_boundary_heading",
        "backmatter_body",
        "tail_candidate_body",
    }
    ref_roles = {"reference_heading", "reference_item"}
    has_body = bool(roles & body_roles)
    has_backmatter = bool(roles & backmatter_roles)
    has_ref = bool(roles & ref_roles)
    count = sum([has_body, has_backmatter, has_ref])
    if count >= 2:
        return "mixed"
    if has_body:
        return "body"
    if has_backmatter:
        return "backmatter"
    if has_ref:
        return "references"
    return ""


def _get_column_index_by_boundaries(x_center: float, boundaries: list[float]) -> int:
    if len(boundaries) <= 1:
        return 0
    midpoints = [(boundaries[i] + boundaries[i + 1]) / 2 for i in range(len(boundaries) - 1)]
    for col, mp in enumerate(midpoints):
        if x_center < mp:
            return col
    return len(boundaries) - 1


def _build_page_reading_segments(
    page_blocks: list[dict],
    page_profile: PageLayoutProfile | None,
    page_idx_offset: int,
) -> list[ReadingSegment]:
    if not page_blocks:
        return []
    page = page_blocks[0].get("page", 0) or 0
    if page_profile is None or page_profile.column_count <= 1:
        sorted_blocks = sorted(enumerate(page_blocks), key=lambda x: _block_y_top(x[1]))
        indices = [page_idx_offset + i for i, _ in sorted_blocks]
        y_top = min(_block_y_top(b) for b in page_blocks)
        y_bottom = max(_block_y_bottom(b) for b in page_blocks)
        hint = _classify_segment_hint(page_blocks)
        return [
            ReadingSegment(
                page=page,
                column_index=0,
                y_top=y_top,
                y_bottom=y_bottom,
                block_indices=indices,
                semantic_hint=hint,
            )
        ]
    boundaries = page_profile.column_boundaries
    col_blocks: dict[int, list[tuple[int, dict]]] = {}
    for i, block in enumerate(page_blocks):
        bbox = _block_bbox(block)
        if bbox:
            x_center = (bbox[0] + bbox[2]) / 2
            col = _get_column_index_by_boundaries(x_center, boundaries)
        else:
            col = 0
        col_blocks.setdefault(col, []).append((i, block))
    segments: list[ReadingSegment] = []
    for col in sorted(col_blocks):
        items = col_blocks[col]
        items.sort(key=lambda x: _block_y_top(x[1]))
        indices = [page_idx_offset + i for i, _ in items]
        col_blocks_only = [b for _, b in items]
        y_top = min(_block_y_top(b) for b in col_blocks_only)
        y_bottom = max(_block_y_bottom(b) for b in col_blocks_only)
        hint = _classify_segment_hint(col_blocks_only)
        segments.append(
            ReadingSegment(
                page=page,
                column_index=col,
                y_top=y_top,
                y_bottom=y_bottom,
                block_indices=indices,
                semantic_hint=hint,
            )
        )
    return segments


def _build_tail_reading_order(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile],
) -> list[ReadingSegment]:
    tail_pages: set[int] = set()
    for block in blocks:
        if block.get("role") in _TAIL_ROLES:
            p = block.get("page")
            if p is not None:
                tail_pages.add(p)
    if not tail_pages:
        return []
    by_page: dict[int, list[tuple[int, dict]]] = {}
    for i, block in enumerate(blocks):
        p = block.get("page")
        if p is not None and p in tail_pages:
            by_page.setdefault(p, []).append((i, block))
    segments: list[ReadingSegment] = []
    for page in sorted(by_page):
        page_items = by_page[page]
        page_items.sort(key=lambda x: x[0])
        page_idx_offset = page_items[0][0]
        page_blocks_only = [item[1] for item in page_items]
        profile = page_layouts.get(page)
        page_segments = _build_page_reading_segments(page_blocks_only, profile, page_idx_offset)
        segments.extend(page_segments)
    return segments


def _enforce_body_before_references_in_segments(
    segments: list[ReadingSegment],
    blocks: list[dict],
    spread_start: int | None,
    spread_end: int | None,
) -> list[ReadingSegment]:
    """Ensure body continuation completes before references on mixed pages.

    When a spread page contains both body-continuation blocks AND
    reference-zone blocks, body continuation must complete before
    references begin in the output order.
    """
    if spread_start is None or spread_end is None:
        return segments

    body_continuation_roles = {"tail_candidate_body", "backmatter_body", "backmatter_heading", "backmatter_boundary_heading"}
    ref_roles = {"reference_heading", "reference_item"}

    by_page: dict[int, list[ReadingSegment]] = {}
    for seg in segments:
        by_page.setdefault(seg.page, []).append(seg)

    result: list[ReadingSegment] = []
    for page in sorted(by_page):
        page_segs = by_page[page]
        if spread_start <= page <= spread_end:
            has_body = False
            has_ref = False
            for seg in page_segs:
                for bi in seg.block_indices:
                    if bi < len(blocks):
                        r = blocks[bi].get("role", "")
                        if r in body_continuation_roles:
                            has_body = True
                        if r in ref_roles:
                            has_ref = True

            if has_body and has_ref:
                body_segs: list[ReadingSegment] = []
                backmatter_segs: list[ReadingSegment] = []
                ref_segs: list[ReadingSegment] = []
                other_segs: list[ReadingSegment] = []
                for seg in page_segs:
                    roles_in_seg = {
                        blocks[bi].get("role", "")
                        for bi in seg.block_indices
                        if bi < len(blocks)
                    }
                    if roles_in_seg & ref_roles:
                        ref_segs.append(seg)
                    elif roles_in_seg & body_continuation_roles:
                        body_segs.append(seg)
                    elif any("backmatter" in (blocks[bi].get("role", "") or "") for bi in seg.block_indices if bi < len(blocks)):
                        backmatter_segs.append(seg)
                    else:
                        other_segs.append(seg)
                result.extend(body_segs + backmatter_segs + ref_segs + other_segs)
                continue

        result.extend(page_segs)

    return result


def _detect_reference_zones(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile],
) -> list[ReferenceZone]:
    """Detect local reference zones per page.

    For each page with a ``reference_heading``, creates a ``ReferenceZone``
    scoped to that heading's column.  Only blocks in the same column and
    below the heading's bottom y are included in the zone.
    """
    zones: list[ReferenceZone] = []
    for block in blocks:
        if block.get("role") != "reference_heading":
            continue
        page = block.get("page")
        if page is None:
            continue
        profile = page_layouts.get(page)
        bbox = _block_bbox(block)
        if not bbox:
            continue
        y_start = bbox[3]
        if profile is None or profile.column_count <= 1:
            column_index = 0
        else:
            x_center = (bbox[0] + bbox[2]) / 2
            column_index = _get_column_index_by_boundaries(x_center, profile.column_boundaries)
        zone_indices: list[int] = []
        max_y = y_start
        for j, b in enumerate(blocks):
            if b.get("page") != page:
                continue
            bb = _block_bbox(b)
            if not bb:
                continue
            if profile and profile.column_count > 1:
                bx_center = (bb[0] + bb[2]) / 2
                bcol = _get_column_index_by_boundaries(bx_center, profile.column_boundaries)
                if bcol != column_index:
                    continue
            if bb[1] < y_start - 1:
                continue
            zone_indices.append(j)
            if bb[3] > max_y:
                max_y = bb[3]
        zones.append(
            ReferenceZone(
                page=page,
                column_index=column_index,
                y_start=y_start,
                y_end=max_y,
                block_indices=zone_indices,
            )
        )
    return zones


def _block_in_any_reference_zone(
    block: dict,
    zones: list[ReferenceZone],
    global_index: int,
) -> bool:
    """Check if a block (by global index) falls within any reference zone."""
    return any(global_index in zone.block_indices for zone in zones)


def _detect_forward_body_end(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> int | None:
    """Scan blocks front-to-back and return the last page of stable body.

    Tracks pages with body headings (section_heading, subsection_heading)
    and body_paragraph continuity.  When a page has tail roles
    (backmatter_heading, reference_heading, etc.) and no body content,
    the body is considered to have ended on the preceding clean body page.

    With ``page_layouts``, multi-column pages are checked per-column:
    if any column has body roles without tail roles in that same column,
    body continues even if other columns have tail content.
    Returns None if no clear body/backmatter boundary is found.
    """
    if not blocks:
        return None
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)
    pages = sorted(by_page.keys())
    if not pages:
        return None

    body_roles = {"body_paragraph", "section_heading", "subsection_heading", "sub_subsection_heading"}
    last_clean_body_page: int | None = None

    for page in pages:
        page_blocks = by_page[page]
        roles = {b.get("role") for b in page_blocks}
        has_body = bool(roles & body_roles)
        has_tail = bool(roles & _TAIL_ROLES)

        if page_layouts and page in page_layouts:
            profile = page_layouts[page]
            if profile.column_count > 1:
                boundaries = profile.column_boundaries
                col_has_body: dict[int, bool] = {}
                col_has_tail: dict[int, bool] = {}
                for block in page_blocks:
                    bbox = _block_bbox(block)
                    if not bbox:
                        continue
                    x_center = (bbox[0] + bbox[2]) / 2
                    col = _get_column_index_by_boundaries(x_center, boundaries)
                    role = block.get("role", "")
                    if role in body_roles:
                        col_has_body[col] = True
                    if role in _TAIL_ROLES:
                        col_has_tail[col] = True

                any_body_without_tail = any(
                    col_has_body.get(col, False) and not col_has_tail.get(col, False)
                    for col in range(profile.column_count)
                )
                if any_body_without_tail:
                    last_clean_body_page = page
                    continue

        if has_body and not has_tail:
            last_clean_body_page = page
        elif has_tail:
            if last_clean_body_page is not None:
                return last_clean_body_page
            if not has_body:
                prev_idx = pages.index(page) - 1
                if prev_idx >= 0:
                    return pages[prev_idx]
                return None

    return last_clean_body_page


def _detect_backward_backmatter_start(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> int | None:
    """Scan blocks backward and return the page where backmatter begins.

    Starting from the last page, looks for the first reference_heading or
    backmatter_heading.  Dense reference pages (>= 4 reference_item blocks)
    are a strong signal.  Short backmatter_body blocks near headings confirm
    the backmatter zone.

    With ``page_layouts``, multi-column pages check for backmatter headings
    rather than relying on the dense-refs heuristic, which can be confused
    by reference-only columns.  Returns None if no backmatter found.
    """
    if not blocks:
        return None
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)
    pages = sorted(by_page.keys(), reverse=True)
    if not pages:
        return None

    best: int | None = None
    for page in pages:
        page_blocks = by_page[page]
        roles = {b.get("role") for b in page_blocks}
        seed_roles = {b.get("seed_role") for b in page_blocks}

        if any(r in roles for r in ("reference_heading", "backmatter_heading", "backmatter_boundary_heading")):
            best = page
            continue
        if any(r in seed_roles for r in ("reference_heading", "backmatter_heading", "backmatter_heading_candidate", "backmatter_boundary_heading")):
            best = page
            continue

        if page_layouts and page in page_layouts:
            profile = page_layouts[page]
            if profile.column_count > 1:
                continue

        dense_refs = sum(1 for b in page_blocks if b.get("role") == "reference_item")
        if dense_refs < 4:
            dense_refs += sum(1 for b in page_blocks if b.get("seed_role") == "reference_item")
        has_ref_heading = (
            "reference_heading" in roles
            or "reference_heading" in seed_roles
        )
        if dense_refs >= 4 and has_ref_heading:
            best = page
            continue

    return best


def _detect_references_start(
    blocks: list[dict],
    body_end_page: int | None,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> int | None:
    """Scan from body end page forward for the first page with a reference
    heading or reference item.

    With ``page_layouts``, uses ``_detect_reference_zones`` internally to
    find the earliest page with a local reference zone.  Falls back to
    page-level scanning when layout data is unavailable.
    Returns None if no references zone is found.
    """
    if body_end_page is None:
        return None
    if page_layouts:
        zones = _detect_reference_zones(blocks, page_layouts)
        if zones:
            earliest = min(z.page for z in zones)
            return max(earliest, body_end_page)
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)
    pages = sorted(p for p in by_page if p >= body_end_page)
    for page in pages:
        roles = {b.get("role") for b in by_page[page]}
        if "reference_heading" in roles or "reference_item" in roles:
            return page
    return None


_BACKMATTER_TITLE_DENY_LIST = frozenset({
    "generative ai statement", "acknowledgments", "acknowledgements",
    "funding", "conflict of interest", "competing interests",
    "data availability", "supplementary materials", "supplementary material",
    "author contributions", "declaration of competing interest",
    "credit authorship contribution statement", "ethical statement",
    "ethics statement", "institutional review board",
})


def _page_has_strong_body_continuation(page_blocks: list[dict]) -> bool:
    """Return True if page looks like body continuation, not tail/backmatter."""
    body_like = [
        b for b in page_blocks
        if (b.get("seed_role") in {"body_paragraph", "section_heading", "subsection_heading"}
            or b.get("role") in {"body_paragraph", "section_heading", "subsection_heading"})
    ]
    ref_like = [b for b in page_blocks if _is_reference_item_candidate(b)]
    backmatter_heading = [
        b for b in page_blocks
        if _canonical_section_text(b) in _BACKMATTER_TITLE_DENY_LIST
    ]
    return len(body_like) >= 3 and len(ref_like) < 3 and not backmatter_heading


def _veto_tail_spread_body_continuation(boundary: TailBoundary, blocks: list[dict]) -> TailBoundary:
    """Push spread_start forward past pages with strong body continuation."""
    by_page: dict[int, list[dict]] = {}
    for b in blocks:
        page = int(b.get("page", 0) or 0)
        if page > 0:
            by_page.setdefault(page, []).append(b)
    spread = boundary.spread_start
    while spread is not None and _page_has_strong_body_continuation(by_page.get(spread, [])):
        spread += 1
    return boundary._replace(spread_start=spread)


def _reconcile_tail_spread(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> TailBoundary | None:
    """Reconcile forward and backward scans into a structured TailBoundary.

    Returns a TailBoundary namedtuple or None when no tail spread exists.
    The ``reason`` field provides an explainability trace.
    ``page_layouts`` is passed to layout-aware boundary detection functions.
    """
    forward_end = _detect_forward_body_end(blocks, page_layouts)
    backward_start = _detect_backward_backmatter_start(blocks, page_layouts)
    references_start = _detect_references_start(blocks, forward_end, page_layouts)

    if forward_end is None and backward_start is None:
        max_page = max((b.get("page") for b in blocks if b.get("page")), default=0)
        if max_page > 0:
            by_page_refs: dict[int, int] = {}
            for b in blocks:
                p = b.get("page")
                if p and b.get("role") == "reference_item":
                    by_page_refs[p] = by_page_refs.get(p, 0) + 1
            if by_page_refs:
                ref_pages = sorted(by_page_refs.keys())
                first_ref = ref_pages[0]
                last_ref = ref_pages[-1]
                return _veto_tail_spread_body_continuation(TailBoundary(
                    body_end_page=max(1, first_ref - 1),
                    backmatter_start=first_ref,
                    references_start=first_ref,
                    spread_start=first_ref,
                    spread_end=last_ref,
                    is_clean_separated=False,
                    reason=f"backward reference fallback: ref items on pages {first_ref}-{last_ref}",
                ), blocks)
        return None

    max_page = 0
    for block in blocks:
        p = block.get("page")
        if p is not None and p > max_page:
            max_page = p

    if forward_end is None and backward_start is not None:
        start = max(1, backward_start - 2)
        reason = (
            f"forward body end not detected, backward backmatter start "
            f"at page {backward_start}, references start at page "
            f"{references_start or 'N/A'}"
        )
        return _veto_tail_spread_body_continuation(TailBoundary(
            body_end_page=None,
            backmatter_start=backward_start,
            references_start=references_start,
            spread_start=start,
            spread_end=max_page,
            is_clean_separated=False,
            reason=reason,
        ), blocks)

    if backward_start is None and forward_end is not None:
        if references_start is not None:
            last_ref_page = references_start
            for b in blocks:
                if b.get("role") == "reference_item":
                    p = b.get("page")
                    if p and p > last_ref_page:
                        last_ref_page = p
            return _veto_tail_spread_body_continuation(TailBoundary(
                body_end_page=forward_end,
                backmatter_start=references_start,
                references_start=references_start,
                spread_start=forward_end + 1,
                spread_end=last_ref_page,
                is_clean_separated=False,
                reason=f"backward backmatter not detected via layout, using references_start={references_start}, last_ref={last_ref_page}",
            ), blocks)
        return None

    if forward_end is not None and backward_start is not None:
        is_clean = forward_end < backward_start
        if is_clean:
            spread_start = forward_end + 1
            spread_end = max(backward_start, references_start or 0)
        else:
            spread_start = backward_start
            spread_end = forward_end
        reason = (
            f"forward body end at page {forward_end}, "
            f"backward backmatter start at page {backward_start}, "
            f"references start at page {references_start or 'N/A'}"
        )
        return _veto_tail_spread_body_continuation(TailBoundary(
            body_end_page=forward_end,
            backmatter_start=backward_start,
            references_start=references_start,
            spread_start=spread_start,
            spread_end=spread_end,
            is_clean_separated=is_clean,
            reason=reason,
        ), blocks)

    return None


_BOUNDARY_ROLES = frozenset({"backmatter_boundary_heading", "backmatter_boundary_candidate"})


def _classify_backmatter_form(tail_boundary: TailBoundary, blocks: list[dict]) -> str:
    """Return ``"container"`` (PeerJ-style boundary heading with >= 3
    child sections) or ``"flat"`` (Frontiers-style, no boundary or few
    children).
    """
    if tail_boundary.spread_start is None or tail_boundary.spread_end is None:
        return "flat"

    # Search for boundary headings from body_end_page onwards, not just
    # from spread_start, because the container boundary may lie on the
    # last body page (before backmatter begins) — e.g. ADDITIONAL
    # INFORMATION AND DECLARATIONS on page 10 when spread starts at 11.
    search_start = min(tail_boundary.spread_start, tail_boundary.body_end_page or tail_boundary.spread_start)
    boundary_page = None
    for block in blocks:
        p = block.get("page")
        if p is not None and search_start <= p <= tail_boundary.spread_end and block.get("role") in _BOUNDARY_ROLES:
            boundary_page = p
            break

    if boundary_page is None:
        return "flat"

    child_count = 0
    seen_boundary = False
    for block in blocks:
        p = block.get("page")
        if p is not None and (p < boundary_page or (p == boundary_page and not seen_boundary)):
            if block.get("role") in _BOUNDARY_ROLES and p == boundary_page:
                seen_boundary = True
            continue
        if p is not None and p > tail_boundary.spread_end:
            break
        if not seen_boundary:
            if block.get("role") in _BOUNDARY_ROLES:
                seen_boundary = True
            continue
        if block.get("role") == "reference_heading":
            break
        if block.get("role") in ("backmatter_heading", "backmatter_heading_candidate"):
            text = block.get("text", "")
            if len(text) < 40:
                child_count += 1

    return "container" if child_count >= 3 else "flat"


def _effective_tail_start(tail_boundary: TailBoundary, blocks: list[dict]) -> int:
    """Return the effective lower bound for tail analysis.

    Normally ``spread_start``, but for container-form tail spreads the
    boundary heading may lie on the last body page (before the detected
    backmatter start).  In that case the tail analysis should include
    that earlier page so child sections beneath the boundary are not
    orphaned outside the spread.
    """
    effective = tail_boundary.spread_start
    body_end = tail_boundary.body_end_page
    if body_end is not None and body_end < effective:
        for block in blocks:
            p = block.get("page")
            if p is not None and body_end <= p < effective:
                if block.get("role") in _BOUNDARY_ROLES:
                    effective = min(effective, body_end)
                    break
    return effective


def _label_backmatter_regime(tail_boundary: TailBoundary, backmatter_form: str, blocks: list[dict]) -> None:
    """Enrich tail-spread blocks with a ``_backmatter_regime`` field.

    Blocks after a ``backmatter_boundary_heading`` in container mode get
    ``_backmatter_regime = "container"``; everything else in the spread
    gets ``_backmatter_regime = "flat"``.  The enrichment is in-place.
    """
    if tail_boundary.spread_start is None:
        return

    tail_start = _effective_tail_start(tail_boundary, blocks)
    boundary_seen = False
    for block in blocks:
        p = block.get("page")
        if p is not None and p < tail_start:
            continue
        if p is not None and p > tail_boundary.spread_end:
            continue

        if block.get("role") in _TAIL_ROLES:
            if block.get("role") in _BOUNDARY_ROLES:
                boundary_seen = True
            if backmatter_form == "container" and boundary_seen:
                block["_backmatter_regime"] = "container"
            else:
                block["_backmatter_regime"] = "flat"


def _normalize_backmatter_roles_after_boundary(
    tail_boundary: TailBoundary | None,
    backmatter_form: str,
    blocks: list[dict],
) -> None:
    """Normalize mixed roles inside the backmatter region.

    Once the backmatter boundary has been entered, all non-reference headings
    should be treated as backmatter headings and all owned content should stop
    competing with body/frontmatter roles.
    """
    if tail_boundary is None or tail_boundary.spread_start is None or tail_boundary.spread_end is None:
        return

    tail_start = _effective_tail_start(tail_boundary, blocks)
    boundary_seen = False
    backmatter_started = False
    for block in blocks:
        page = block.get("page")
        if page is None or page < tail_start or page > tail_boundary.spread_end:
            continue

        role = block.get("role")
        if backmatter_form == "container":
            if role in _BOUNDARY_ROLES:
                if boundary_seen:
                    old_role = block.get("role")
                    block["role"] = "backmatter_heading"
                    if old_role != block["role"]:
                        record_decision(
                            block,
                            stage="backmatter_role_normalization",
                            old_role=old_role,
                            new_role=block["role"],
                            reason="duplicate boundary heading demoted to backmatter heading",
                        )
                else:
                    boundary_seen = True
                backmatter_started = True
                block["_backmatter_regime"] = "container"
                continue

            if not boundary_seen:
                continue
        else:
            if role in _BOUNDARY_ROLES | {"backmatter_heading"}:
                backmatter_started = True
                block["_backmatter_regime"] = "flat"
                if role in _BOUNDARY_ROLES:
                    old_role = block.get("role")
                    block["role"] = "backmatter_heading"
                    if old_role != block["role"]:
                        record_decision(
                            block,
                            stage="backmatter_role_normalization",
                            old_role=old_role,
                            new_role=block["role"],
                            reason="boundary role normalized to backmatter heading (flat form)",
                        )
                continue
            if not backmatter_started:
                continue

        if role == "reference_heading":
            break

        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            old_role = block.get("role")
            block["role"] = "backmatter_heading"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="backmatter_role_normalization",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="heading demoted to backmatter heading inside backmatter region",
                )
            block["_backmatter_regime"] = backmatter_form
            block["render_default"] = True
            continue

        if role in {"body_paragraph", "frontmatter_noise"}:
            old_role = block.get("role")
            block["role"] = "backmatter_body"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="backmatter_role_normalization",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="body/noise block assigned backmatter body role inside backmatter region",
                )
            block["_backmatter_regime"] = backmatter_form
            block["render_default"] = True
            block["index_default"] = True


def _detect_frontmatter_zone(
    block: dict,
    page_blocks: list[dict],
    page_height: float,
    page_width: float,
    style_profiles: dict | None = None,
) -> str | None:
    """Detect frontmatter zone for a block on page 1.

    Returns one of: ``title_zone``, ``author_zone``, ``affiliation_zone``,
    ``journal_furniture_zone``, ``abstract_zone``, or ``None``.
    """
    page_num = block.get("page", 1) or 1
    if page_num > 1:
        return None

    bbox = block.get("block_bbox", [0, 0, 0, 0])
    if len(bbox) < 4:
        return None

    text = str(block.get("block_content", "") or "").strip()
    if not text:
        return None

    lower_txt = text.lower()
    raw_label = str(block.get("block_label", "") or "").strip()
    x1, y1, x2 = bbox[0], bbox[1], bbox[2]

    if lower_txt.startswith("abstract") and len(text) < 30:
        return "abstract_zone"

    import re as _re

    # "received"/"published" intentionally excluded — too common in body text
    # ("she received her degree", "published works include...").
    # Only distinctive frontmatter vocabulary is used.
    furniture_signals = [
        "submitted",
        "accepted",
        "copyright",
        "\u00a9",
        "doi:",
        "https://doi.org",
        "academic editor",
        "how to cite",
        "to cite this article",
        "creative commons",
        "cc by",
        "cc license",
        "this is an open-access article",
        "reviewed by",
        "edited by",
        "present address",
    ]
    if any(_re.search(r"(?<!\w)" + _re.escape(s) + r"(?!\w)", lower_txt) for s in furniture_signals):
        return "journal_furniture_zone"

    narrow_furniture = [
        "citation:",
        "correspondence",
        "orcid",
        "these authors contributed equally",
        "equal contribution",
        "additional information",
    ]
    if any(s in lower_txt for s in narrow_furniture):
        block_width = x2 - x1
        is_narrow = page_width > 0 and block_width < page_width * 0.35
        is_top_half = page_height > 0 and y1 < page_height * 0.5
        if is_narrow or is_top_half:
            return "journal_furniture_zone"

    if page_height > 0 and y1 < page_height * 0.2:
        block_width = x2 - x1
        is_wide_enough = page_width <= 0 or block_width > page_width * 0.4
        if is_wide_enough and lower_txt not in _BACKMATTER_TITLE_DENY_LIST and not _looks_like_author_list(text):
            if raw_label in ("paragraph_title", "doc_title"):
                return "title_zone"
            if raw_label == "text" and len(text) < 80:
                return "title_zone"

    if (
        page_height > 0
        and y1 < page_height * 0.4
        and _looks_like_author_list(text)
        and not _looks_like_affiliation(text)
    ):
        return "author_zone"

    if page_height > 0 and y1 < page_height * 0.6 and _looks_like_affiliation(text):
        return "affiliation_zone"

    return None


def _page_still_frontmatter(page_blocks: list[dict], page_num: int, page_height: float) -> bool:
    """Check if page is still in frontmatter regime (no body content yet).

    Uses block labels and vertical position: if any block on a page > 1 has
    body-type labels (figure_title, chart, table) or a text block in the
    lower third, body content has started and frontmatter rules should stop.
    """
    if page_num == 1:
        return True
    for pb in page_blocks:
        label = pb.get("block_label", "")
        if label in ("figure_title", "chart", "table", "reference_content"):
            return False
        bbox = pb.get("block_bbox", [0, 0, 0, 0])
        if label == "text" and len(bbox) >= 4 and bbox[1] > page_height * 0.35:
            return False
    return True


def rescue_roles_with_document_context(
    blocks: list[dict],
    role_profiles: dict,
    document_structure: DocumentStructure | None = None,
) -> list[dict]:
    """Apply section-context-aware role rescue rules using document structure.

    Uses the previously-built role style profiles and document boundaries to
    correct common role-assignment errors:

    1. ``frontmatter_noise`` in the body section with body-like font
       → ``body_paragraph``
    2. ``body_paragraph`` in the references section with reference-like font
       → ``reference_item`` (only when confidence < 0.7)
    3. Weak heading (confidence < 0.6) with body-like font → ``body_paragraph``

    Family-level profiles are layered on top of individual-role profiles for
    broader-baseline matching:

    - Non-body insert cluster members are validated against
      ``non_body_insert_family`` vs ``body_family`` — blocks that match
      body better are reinstated.
    - Weak heading/body disambiguation uses ``heading_family`` vs
      ``body_family`` when enough heading data exists.
    - Reference rescue compares against ``reference_family``.

    Never overrides: strong formal prefixes (Figure, Table), strong numbering,
    or explicit boundary-heading logic.

    Returns a new list of blocks with corrected roles.
    """
    from paperforge.worker.ocr_profiles import (
        build_family_profiles,
        compare_against_family,
        compare_against_role_family,
        extract_block_span_profile,
    )
    from paperforge.worker.ocr_roles import _has_heading_numbering

    if document_structure is None:
        document_structure = analyze_document_structure(blocks)

    family_profiles = build_family_profiles(blocks)
    span_coverage = _compute_span_coverage(blocks)
    degraded_mode_active = span_coverage["degraded_mode_active"]

    body_end_page = document_structure.body_end_page
    refs_start = document_structure.references_start
    refs_start_page = refs_start.page if refs_start else None

    result = list(blocks)

    # Precompute pre-proof pages so the rescue loop can skip them entirely
    try:
        from paperforge.worker.ocr_roles import is_preproof_marker

        _preproof_pages = {
            int(b.get("page", 0) or 0)
            for b in result
            if is_preproof_marker(str(b.get("text", "") or b.get("block_content", "") or ""))
        }
    except Exception:
        _preproof_pages = set()

    for block in result:
        # --- Non-body insert cluster validation via family profiles ---
        if block.get("_non_body_insert"):
            bp = extract_block_span_profile(block)
            should_skip = True  # default: keep flag, skip downstream rules

            # Geometry guard: narrow blocks stay non_body_insert even if font
            # matches body_family — narrowness is structural evidence of being
            # a profile/sidebar card, not a body paragraph.
            bbox = block.get("bbox", [0, 0, 0, 0])
            block_w = (bbox[2] - bbox[0]) if len(bbox) >= 4 else 0
            page_w = block.get("page_width", 0) or 0
            # Use body_family's per-page median_width from the spine, or
            # approximate from page_width.  Blocks narrower than 60% of the
            # expected body width are structurally incompatible with the spine.
            if block_w > 0 and page_w > 0:
                expected_body_min = page_w * 0.35  # ~420px on 1200px-wide page
                if block_w < expected_body_min:
                    # Definitely a narrow insert, not a body paragraph — keep.
                    continue

            if bp and "non_body_insert_family" in family_profiles and "body_family" in family_profiles:
                ni_fam = family_profiles["non_body_insert_family"]
                ni_quality = ni_fam.get("quality", "no_data")
                # Only trust family comparison when non_body_insert_family is
                # well-established (strong quality, low dispersion).  Moderate
                # profiles are unreliable because non_body_insert blocks are
                # naturally heterogeneous (different bio fonts/sizes).
                if ni_quality == "strong":
                    ni_match = compare_against_family(bp, ni_fam)
                    body_match = compare_against_family(bp, family_profiles["body_family"])
                    if body_match["match_score"] > max(ni_match["match_score"], 0.6) and body_match["size_compatible"]:
                        old_role = block.get("role")
                        del block["_non_body_insert"]
                        block["role"] = "body_paragraph"
                        if old_role != block["role"]:
                            record_decision(
                                block,
                                stage="rescue_non_body_insert",
                                old_role=old_role,
                                new_role=block["role"],
                                reason="non_body_insert validated as body paragraph via family comparison",
                            )
                        block.setdefault("evidence", []).append("rescue_family: non_body_insert → body_paragraph")
                        should_skip = False
            if should_skip:
                continue

        # --- Rule 1: frontmatter_noise → body_paragraph (body section + body font)
        if block.get("role") == "frontmatter_noise":
            # Never rescue pre-proof page blocks — entire page is intentional suppression
            if (block.get("page", 0) or 0) in _preproof_pages:
                continue
            evidence_text = "\n".join(str(e) for e in block.get("evidence", []))
            if any(
                zone_hint in evidence_text
                for zone_hint in (
                    "journal_furniture_zone",
                    "title_zone",
                    "author_zone",
                    "affiliation_zone",
                    "abstract_zone",
                )
            ):
                continue
            page = block.get("page", 1) or 1
            bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
            page_h = block.get("page_height") or 1700
            if len(bbox) >= 4 and bbox[1] > page_h * 0.85:
                continue
            if body_end_page is not None and page <= body_end_page:
                bp = extract_block_span_profile(block)
                if bp:
                    family_rescued = False
                    if "body_family" in family_profiles:
                        body_match = compare_against_family(bp, family_profiles["body_family"])
                        if body_match["size_compatible"] and body_match["match_score"] > 0.5:
                            old_role = block.get("role")
                            block["role"] = "body_paragraph"
                            if old_role != block["role"]:
                                record_decision(
                                    block,
                                    stage="rescue_frontmatter_noise",
                                    old_role=old_role,
                                    new_role=block["role"],
                                    reason="frontmatter_noise rescued to body_paragraph via family profile match",
                                )
                            block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.1, 1.0)
                            block.setdefault("evidence", []).append("rescue_family: frontmatter_noise → body_paragraph")
                            family_rescued = True
                    if not family_rescued:
                        body_fam = role_profiles.get("body_paragraph", {})
                        if body_fam:
                            match = compare_against_role_family(bp, body_fam)
                        if match["size_compatible"] and match["match_score"] > 0.5:
                            old_role = block.get("role")
                            block["role"] = "body_paragraph"
                            if old_role != block["role"]:
                                record_decision(
                                    block,
                                    stage="rescue_frontmatter_noise",
                                    old_role=old_role,
                                    new_role=block["role"],
                                    reason="frontmatter_noise rescued to body_paragraph via role family match",
                                )
                            block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.1, 1.0)
                            block.setdefault("evidence", []).append("rescue: frontmatter_noise → body_paragraph")

        # --- Rule 2: body_paragraph → reference_item (refs section + ref font)
        role = block.get("role", "")
        if role == "body_paragraph" and block.get("role_confidence", 1.0) < 0.7:
            bp = extract_block_span_profile(block)
            if bp:
                ref_rescued = False

                # Zone-based gate (layout-aware, column-scoped)
                ref_zones = document_structure.reference_zones
                p_layouts = document_structure.page_layouts
                in_reference_zone = False

                if ref_zones:
                    block_page = block.get("page", 1) or 1
                    bbox = block.get("bbox") or [0, 0, 0, 0]
                    x_center = (bbox[0] + bbox[2]) / 2 if len(bbox) >= 4 else 0
                    y_center = (bbox[1] + bbox[3]) / 2 if len(bbox) >= 4 else 0
                    p_layout = (p_layouts or {}).get(block_page)

                    for zone_data in ref_zones:
                        if zone_data.get("page") != block_page:
                            continue
                        zone_col = zone_data.get("column_index", 0)
                        if p_layout and p_layout.column_count > 1:
                            bcol = _get_column_index_by_boundaries(x_center, p_layout.column_boundaries)
                            if bcol != zone_col:
                                continue
                        if y_center >= zone_data.get("y_start", 0):
                            in_reference_zone = True
                            break

                page = block.get("page", 1) or 1
                if in_reference_zone or (not ref_zones and refs_start_page is not None and page >= refs_start_page):
                    text = str(block.get("text") or block.get("block_content") or "")
                    text_matches_ref = bool(re.search(r"^\d+\.\s", text.strip())) if text else False
                    if not text_matches_ref:
                        continue
                    if "reference_family" in family_profiles and "body_family" in family_profiles:
                        ref_fam_p = family_profiles["reference_family"]
                        if ref_fam_p.get("quality") in ("moderate", "strong"):
                            ref_match = compare_against_family(bp, ref_fam_p)
                            body_match_r = compare_against_family(bp, family_profiles["body_family"])
                            if (
                                ref_match["size_compatible"]
                                and ref_match["match_score"] > body_match_r["match_score"] + 0.1
                            ):
                                old_role = block.get("role")
                                block["role"] = "reference_item"
                                if old_role != block["role"]:
                                    record_decision(
                                        block,
                                        stage="rescue_reference",
                                        old_role=old_role,
                                        new_role=block["role"],
                                        reason="body_paragraph rescued to reference_item via family profile match",
                                    )
                                block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.2, 1.0)
                                block.setdefault("evidence", []).append(
                                    "rescue_family: body_paragraph → reference_item"
                                )
                                ref_rescued = True
                    if not ref_rescued:
                        ref_fam = role_profiles.get("reference_item", {})
                        if ref_fam:
                            threshold = 0.7 if degraded_mode_active else 0.5
                            match = compare_against_role_family(bp, ref_fam)
                        if match["size_compatible"] and match["match_score"] > threshold:
                            old_role = block.get("role")
                            block["role"] = "reference_item"
                            if old_role != block["role"]:
                                record_decision(
                                    block,
                                    stage="rescue_reference",
                                    old_role=old_role,
                                    new_role=block["role"],
                                    reason="body_paragraph rescued to reference_item via role family match",
                                )
                            block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.2, 1.0)
                            block.setdefault("evidence", []).append("rescue: body_paragraph → reference_item")

        # --- Rule 3: weak heading with body font → body_paragraph
        if degraded_mode_active:
            continue
        if (
            role in {"section_heading", "subsection_heading", "sub_subsection_heading"}
            and block.get("role_confidence", 1.0) < 0.6
        ):
            text = str(block.get("text", "") or block.get("block_content", "") or "")
            if _has_heading_numbering(text):
                continue
            bp = extract_block_span_profile(block)
            if bp:
                heading_demoted = False
                if "heading_family" in family_profiles and "body_family" in family_profiles:
                    heading_fam = family_profiles["heading_family"]
                    if heading_fam.get("quality") in ("moderate", "strong"):
                        heading_match = compare_against_family(bp, heading_fam)
                        body_match_h = compare_against_family(bp, family_profiles["body_family"])
                        if (
                            body_match_h["size_compatible"]
                            and body_match_h["match_score"] > heading_match["match_score"] + 0.1
                        ):
                            old_role = block.get("role")
                            block["role"] = "body_paragraph"
                            if old_role != block["role"]:
                                record_decision(
                                    block,
                                    stage="rescue_heading",
                                    old_role=old_role,
                                    new_role=block["role"],
                                    reason="weak heading demoted to body_paragraph via family profile match",
                                )
                            block.setdefault("evidence", []).append("rescue_family: heading → body_paragraph")
                            heading_demoted = True
                if not heading_demoted:
                    body_fam = role_profiles.get("body_paragraph", {})
                    if body_fam:
                        match = compare_against_role_family(bp, body_fam)
                        if match["size_compatible"] and match["match_score"] > 0.5:
                            old_role = block.get("role")
                            block["role"] = "body_paragraph"
                            if old_role != block["role"]:
                                record_decision(
                                    block,
                                    stage="rescue_heading",
                                    old_role=old_role,
                                    new_role=block["role"],
                                    reason="weak heading demoted to body_paragraph via role family match",
                                )
                            block.setdefault("evidence", []).append("rescue: heading → body_paragraph")

    return result


def analyze_document_structure(blocks: list[dict]) -> DocumentStructure:
    """Produce a structured document boundary object.

    Uses the existing _detect_forward_body_end, _detect_backward_backmatter_start,
    etc. internally. Returns a DocumentStructure with all boundary info.
    """
    page_layouts = _build_page_layout_profiles(blocks)
    body_family_anchor = discover_body_family_anchor(blocks)
    reference_family_anchor = discover_reference_family_anchor(blocks)
    region_bus = infer_zones(
        blocks,
        {
            "body_family_anchor": body_family_anchor,
            "reference_family_anchor": reference_family_anchor,
        },
    )
    _apply_zone_labels(blocks, region_bus)
    partition_zone_families(
        blocks,
        {
            "body_family_anchor": body_family_anchor,
            "reference_family_anchor": reference_family_anchor,
        },
    )
    tail_spread = _reconcile_tail_spread(blocks, page_layouts)
    if tail_spread is not None:
        backmatter_form = _classify_backmatter_form(tail_spread, blocks)
        _label_backmatter_regime(tail_spread, backmatter_form, blocks)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
    else:
        backmatter_form = "flat"

    ds = DocumentStructure(
        body_end_page=tail_spread.body_end_page if tail_spread else None,
        backmatter_start=PagePosition(page=tail_spread.backmatter_start, y=0.0)
        if tail_spread and tail_spread.backmatter_start is not None
        else None,
        references_start=PagePosition(page=tail_spread.references_start, y=0.0)
        if tail_spread and tail_spread.references_start is not None
        else None,
        spread_start=tail_spread.spread_start if tail_spread else None,
        spread_end=tail_spread.spread_end if tail_spread else None,
        backmatter_form=backmatter_form,
        body_family_anchor=body_family_anchor,
        reference_family_anchor=reference_family_anchor,
        page_layouts=page_layouts,
        region_bus=region_bus,
    )

    reading_segments = _build_tail_reading_order(blocks, page_layouts)
    ds.tail_reading_order = [dataclasses.asdict(seg) for seg in reading_segments] if reading_segments else None

    ref_zones = _detect_reference_zones(blocks, page_layouts)
    ds.reference_zones = [dataclasses.asdict(z) for z in ref_zones] if ref_zones else None

    # Build body spine using document structure for stable anchor pages
    _detect_body_spine(blocks, ds)

    return ds


def _apply_zone_labels(blocks: list[dict], region_bus: dict[str, dict] | None) -> None:
    if not region_bus:
        return

    block_ids_to_zone: dict[str, str] = {}
    for zone_name, zone in region_bus.items():
        for block_id in zone.get("block_ids") or []:
            block_ids_to_zone[str(block_id)] = zone_name
        for composite_id in zone.get("composite_block_ids") or []:
            block_ids_to_zone[str(composite_id)] = zone_name

    for block in blocks:
        if block.get("block_id") is None:
            continue
        zone_name = block_ids_to_zone.get(str(block.get("block_id"))) or block_ids_to_zone.get(_zone_block_key(block))
        if zone_name:
            block["zone"] = zone_name

    _apply_content_zone_fallback(blocks, region_bus)


def _apply_content_zone_fallback(blocks: list[dict], region_bus: dict[str, dict] | None) -> None:
    """Fill zone for content blocks not matched by region_bus."""
    ref_zone = region_bus.get("reference_zone", {}) if region_bus else {}
    ref_band = ref_zone.get("boundary_band") or {}
    ref_start = ref_band.get("start_page")
    ref_end = ref_band.get("end_page")

    # Detect post-reference backmatter start from region_bus
    post_ref_zone = region_bus.get("post_reference_backmatter_zone", {}) if region_bus else {}
    post_ref_band = post_ref_zone.get("boundary_band") or {}
    post_ref_start = post_ref_band.get("start_page")

    # Pre-scan: find reference heading pages and their y_top positions so we
    # can split same-page body vs reference content by vertical boundary.
    ref_heading_pages: dict[int, float] = {}
    for b in blocks:
        brole = b.get("role") or b.get("seed_role")
        if brole == "unassigned":
            brole = b.get("seed_role")
        if brole == "reference_heading":
            p = int(b.get("page", 0) or 0)
            if p > 0 and p not in ref_heading_pages:
                ref_heading_pages[p] = _block_y_top(b)

    # Fallback: pages with reference_item blocks but no reference_heading
    # (refs start directly without a heading). Use first ref_item y_top per page.
    if ref_start is not None:
        seen_ref_pages: set[int] = set()
        for b in blocks:
            brole = b.get("role") or b.get("seed_role")
            if brole == "unassigned":
                brole = b.get("seed_role")
            if brole == "reference_item":
                p = int(b.get("page", 0) or 0)
                if p > 0 and p not in ref_heading_pages and p >= ref_start and p not in seen_ref_pages:
                    ref_heading_pages[p] = _block_y_top(b)
                    seen_ref_pages.add(p)

    # Pre-scan: find the last body-section heading y_top on each page that
    # also has a reference heading.  Content below the last body heading but
    # above the reference heading is tail content (gratitude, etc.).
    _BODY_HEADING_ROLES = {"section_heading", "subsection_heading", "sub_subsection_heading"}
    last_body_heading_top: dict[int, float] = {}
    for b in blocks:
        brole = b.get("role") or b.get("seed_role")
        if brole == "unassigned":
            brole = b.get("seed_role")
        p = int(b.get("page", 0) or 0)
        if p in ref_heading_pages and brole in _BODY_HEADING_ROLES:
            yt = _block_y_top(b)
            if p not in last_body_heading_top or yt > last_body_heading_top[p]:
                last_body_heading_top[p] = yt

    for block in blocks:
        if block.get("zone"):
            continue
        role = block.get("role") or block.get("seed_role")
        if role == "unassigned":
            role = block.get("seed_role")
        page = int(block.get("page", 0) or 0)

        if role in {"noise", "frontmatter_noise", "media_asset", "figure_asset", "figure_inner_text"}:
            continue

        if role in {"paper_title", "authors", "affiliation", "frontmatter_support"} and page <= 2:
            block["zone"] = "frontmatter_main_zone"
            continue

        if role in {"reference_heading", "reference_item"}:
            # Blocks on or after post_ref_backmatter_start are NOT in reference_zone
            if post_ref_start is not None and page >= post_ref_start:
                continue
            in_ref_zone = (
                page in ref_heading_pages
                or (ref_start is not None and page >= ref_start and (ref_end is None or page <= ref_end))
            )
            if in_ref_zone:
                block["zone"] = "reference_zone"
            continue

        if role in {
            "section_heading", "subsection_heading", "sub_subsection_heading", "body_paragraph",
        }:
            if page in ref_heading_pages:
                # Same page as a reference heading: split by vertical position.
                ref_top = ref_heading_pages[page]
                body_top = last_body_heading_top.get(page)
                if _block_y_bottom(block) <= ref_top:
                    # Above the reference heading — check if below last body heading
                    if body_top is not None and _block_y_top(block) > body_top:
                        block["zone"] = "tail_nonref_hold_zone"
                    else:
                        block["zone"] = "body_zone"
                else:
                    block["zone"] = "tail_nonref_hold_zone"
            elif ref_start is None or page < ref_start:
                block["zone"] = "body_zone"


def _exclude_frontmatter_side_from_body_flow(blocks: list[dict]) -> None:
    for block in blocks:
        effective_role = block.get("role")
        if effective_role == "unassigned":
            effective_role = block.get("seed_role")
        if effective_role != "body_paragraph":
            continue
        if block.get("zone") != "frontmatter_side_zone":
            continue
        if block.get("style_family") != "support_like":
            continue
        old_role = block.get("role")
        block["role"] = "frontmatter_noise"
        if block.get("seed_role") == "body_paragraph":
            block["seed_role"] = "frontmatter_noise"
        if old_role != block["role"]:
            record_decision(
                block,
                stage="frontmatter_side_exclusion",
                old_role=old_role,
                new_role=block["role"],
                reason="frontmatter-side support block excluded from body flow",
            )
        block.setdefault("evidence", []).append("frontmatter_side_zone excluded from body flow")


def _exclude_tail_nonref_from_body_flow(blocks: list[dict]) -> None:
    for block in blocks:
        effective_role = block.get("role")
        if effective_role == "unassigned":
            effective_role = block.get("seed_role")
        if effective_role != "body_paragraph":
            continue
        if block.get("zone") != "tail_nonref_hold_zone":
            continue
        old_role = block.get("role")
        block["role"] = "backmatter_body"
        if block.get("seed_role") == "body_paragraph":
            block["seed_role"] = "backmatter_body"
        if old_role != block["role"]:
            record_decision(
                block,
                stage="tail_nonref_exclusion",
                old_role=old_role,
                new_role=block["role"],
                reason="tail non-reference body block excluded from body flow",
            )
        block.setdefault("evidence", []).append("tail_nonref_hold_zone excluded from body flow")


def _get_column(block: dict, page_width: float = 1200) -> int:
    bbox = block.get("bbox") or block.get("block_bbox")
    if bbox and len(bbox) >= 4:
        x_center = (bbox[0] + bbox[2]) / 2
        return 0 if x_center < page_width / 2 else 1
    return 0


def _is_in_usable_content(
    block: dict,
    header_band: float | None,
    footer_band: float | None,
) -> bool:
    bbox = block.get("bbox") or block.get("block_bbox")
    if not bbox or len(bbox) < 4:
        return True
    y1, y2 = bbox[1], bbox[3]
    if header_band is not None and y2 < header_band:
        return False
    return not (footer_band is not None and y1 > footer_band)


def _estimate_noise_bands(
    structured_blocks: list[dict],
) -> tuple[float | None, float | None]:
    header_candidates: list[float] = []
    footer_candidates: list[float] = []

    for block in structured_blocks:
        role = block.get("role", "")
        bbox = block.get("bbox") or block.get("block_bbox")
        if not bbox or len(bbox) < 4:
            continue
        page_height = block.get("page_height", 0) or 0
        if page_height == 0:
            continue
        y2, y1 = bbox[3], bbox[1]

        noise_roles = {"noise", "header", "footer", "number"}
        raw_label = block.get("raw_label", "")
        if role in noise_roles or raw_label in ("header", "footer", "number"):
            if y2 < page_height * 0.15:
                header_candidates.append(y2)
            if y1 > page_height * 0.85:
                footer_candidates.append(y1)

    header_band = max(header_candidates) if header_candidates else None
    footer_band = min(footer_candidates) if footer_candidates else None
    return header_band, footer_band


def _has_same_column_anchor_above(
    body: dict,
    anchors: list[dict],
    page_width: float = 1200,
) -> bool:
    body_bbox = body.get("bbox") or body.get("block_bbox")
    if not body_bbox or len(body_bbox) < 4:
        return False

    body_y = body_bbox[1]
    body_col = _get_column(body, page_width)

    for anchor in anchors:
        anchor_bbox = anchor.get("bbox") or anchor.get("block_bbox")
        if not anchor_bbox or len(anchor_bbox) < 4:
            continue
        if _get_column(anchor, page_width) != body_col:
            continue
        if anchor_bbox[3] <= body_y:
            return True
    return False


def _find_best_anchor(
    body: dict,
    anchors: list[dict],
    ref_heading: dict | None = None,
    page_width: float = 1200,
) -> int | None:
    body_bbox = body.get("bbox") or body.get("block_bbox")
    if not body_bbox or len(body_bbox) < 4:
        return None
    body_y = body_bbox[1]
    body_page = body.get("page", 0) or 0
    body_mid = (body_bbox[0] + body_bbox[2]) / 2
    pw_mid = page_width / 2
    body_col = 0 if body_mid < pw_mid else 1

    best_same: tuple[int, float] | None = None
    best_other: tuple[int, float] | None = None

    for idx, anchor in enumerate(anchors):
        if anchor is ref_heading:
            continue
        a_bbox = anchor.get("bbox") or anchor.get("block_bbox")
        if not a_bbox or len(a_bbox) < 4:
            continue

        anchor_page = anchor.get("page", 0) or 0
        if anchor_page > body_page:
            continue

        a_bottom = a_bbox[3]
        if anchor_page == body_page and a_bottom > body_y:
            continue

        a_mid = (a_bbox[0] + a_bbox[2]) / 2
        a_col = 0 if a_mid < pw_mid else 1

        if anchor_page == body_page:
            dist = body_y - a_bottom
        else:
            page_extent = body.get("page_height", 0) or page_width
            dist = (body_page - anchor_page) * page_extent + max(0.0, page_extent - a_bottom)

        if body_col == a_col:
            if best_same is None or dist < best_same[1]:
                best_same = (idx, dist)
        else:
            if best_other is None or dist < best_other[1]:
                best_other = (idx, dist)

    best = best_same or best_other
    return best[0] if best is not None else None


def _promote_tail_body_candidates(
    blocks: list[dict],
    doc: DocumentStructure | None,
    header_band: float | None = None,
    footer_band: float | None = None,
) -> list[dict]:
    if doc is None or doc.spread_start is None or doc.spread_end is None:
        return blocks

    spread_start, spread_end = doc.spread_start, doc.spread_end
    by_page: dict[int, list[int]] = {}
    for idx, block in enumerate(blocks):
        page = block.get("page")
        if page is not None:
            by_page.setdefault(page, []).append(idx)

    result = [dict(block) for block in blocks]
    for page, indices in by_page.items():
        if page < spread_start or page > spread_end:
            continue

        page_blocks = [result[i] for i in indices]
        local_headings = [
            b for b in page_blocks if b.get("role") in ("backmatter_heading", "backmatter_boundary_heading")
        ]
        ref_heading = next((b for b in page_blocks if b.get("role") == "reference_heading"), None)
        local_anchors = local_headings
        local_tops = []
        for anchor in [*local_headings, *([ref_heading] if ref_heading else [])]:
            bbox = anchor.get("bbox") or anchor.get("block_bbox")
            if bbox and len(bbox) >= 4:
                local_tops.append(bbox[1])
        first_local_anchor_top = min(local_tops) if local_tops else None

        for idx in indices:
            block = result[idx]
            if block.get("role") != "body_paragraph":
                continue
            if not _is_in_usable_content(block, header_band, footer_band):
                continue

            # Reference zone ownership is stronger than generic tail/body fallback.
            # Blocks already identified as reference-zone members must not be
            # re-promoted to tail_candidate_body during tail resolution.
            if doc is not None and doc.reference_zones:
                if any(
                    idx in (z.get("block_indices") or []) for z in doc.reference_zones
                ):
                    continue

            bbox = block.get("bbox") or block.get("block_bbox")
            if not bbox or len(bbox) < 4:
                continue

            promote = False
            page_width = block.get("page_width", 1200) or 1200
            if local_anchors and _has_same_column_anchor_above(block, local_anchors, page_width):
                promote = True
            elif page > spread_start:
                body_top = bbox[1]
                if first_local_anchor_top is None or body_top < first_local_anchor_top:
                    promote = True

            if promote:
                old_role = block.get("role")
                block["role"] = "tail_candidate_body"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="tail_candidate_promotion",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="promoted in tail spread from body_paragraph",
                    )
                block["evidence"] = list(block.get("evidence") or []) + ["promoted in tail spread from body_paragraph"]

    return result


def _assign_tail_spread_ownership(
    blocks: list[dict],
    doc: DocumentStructure | None = None,
) -> list[dict]:
    tail_heading_roles = {"backmatter_heading", "backmatter_boundary_heading"}
    anchors = [b for b in blocks if b.get("role") in tail_heading_roles]
    ref_heading = next((b for b in blocks if b.get("role") == "reference_heading"), None)

    if doc is not None and doc.spread_start is not None and doc.spread_end is not None:
        spread_start, spread_end = doc.spread_start, doc.spread_end
    else:
        spread_start, spread_end = 0, 0

    if not anchors:
        result = []
        for b in blocks:
            if b.get("role") == "tail_candidate_body":
                old_role = b.get("role")
                new_block = {**b, "role": "body_paragraph"}
                if old_role != new_block["role"]:
                    record_decision(
                        new_block,
                        stage="tail_spread_ownership",
                        old_role=old_role,
                        new_role=new_block["role"],
                        reason="no backmatter anchors, tail candidate demoted to body",
                    )
                result.append(new_block)
            else:
                result.append(b)
        return result

    result = list(blocks)
    for i, block in enumerate(result):
        if block.get("role") != "tail_candidate_body":
            continue

        block_page = block.get("page", 0) or 0

        if doc is not None and (block_page < spread_start or block_page > spread_end):
            old_role = block.get("role")
            result[i] = dict(block)
            result[i]["role"] = "body_paragraph"
            if old_role != result[i]["role"]:
                record_decision(
                    result[i],
                    stage="tail_spread_ownership",
                    old_role=old_role,
                    new_role=result[i]["role"],
                    reason="tail candidate outside spread, demoted to body",
                )
            continue

        # Reference zone ownership is stronger than generic tail/body fallback.
        # Blocks inside a reference zone must not be re-assigned to
        # backmatter_body or re-demoted to body_paragraph.
        if doc is not None and doc.reference_zones:
            if any(
                i in (z.get("block_indices") or []) for z in doc.reference_zones
            ):
                continue

        pw = block.get("page_width", 0) or 1200
        idx = _find_best_anchor(block, anchors, ref_heading, pw)
        old_role = block.get("role")
        result[i] = dict(block)
        if idx is not None:
            anchor_page = anchors[idx].get("page", 0)
            result[i]["role"] = "backmatter_body"
            if old_role != result[i]["role"]:
                record_decision(
                    result[i],
                    stage="tail_spread_ownership",
                    old_role=old_role,
                    new_role=result[i]["role"],
                    reason=f"tail candidate assigned to backmatter anchor on page {anchor_page}",
                )
            result[i]["_spread_anchor"] = anchor_page
        else:
            result[i]["role"] = "body_paragraph"
            if old_role != result[i]["role"]:
                record_decision(
                    result[i],
                    stage="tail_spread_ownership",
                    old_role=old_role,
                    new_role=result[i]["role"],
                    reason="no backmatter anchor found, tail candidate demoted to body",
                )
    return result


def _select_body_anchor_pages(blocks: list[dict], doc: DocumentStructure | None = None) -> list[int]:
    """Select stable middle pages for body baseline derivation.

    Excludes:
    - Page 1 (frontmatter contamination)
    - Tail spread pages (backmatter/references)
    - Pages with few body paragraphs

    Returns sorted list of anchor page numbers.
    """
    if not blocks:
        return []

    # Determine tail start
    tail_start = None
    if doc and doc.spread_start is not None:
        tail_start = doc.spread_start

    by_page: dict[int, list[dict]] = {}
    for b in blocks:
        p = b.get("page", 1)
        by_page.setdefault(p, []).append(b)

    all_pages = sorted(by_page.keys())

    scores: list[tuple[float, int]] = []
    for p in all_pages:
        if p == 1:
            continue  # exclude frontmatter
        if tail_start is not None and p >= tail_start:
            continue  # exclude tail spread

        page_blocks = by_page[p]
        body_count = sum(1 for b in page_blocks if b.get("role") == "body_paragraph")
        total_count = max(len(page_blocks), 1)
        body_ratio = body_count / total_count

        # Prefer pages with >40% body paragraphs
        if body_ratio > 0.4:
            # Boost central pages: distance from edges
            idx = all_pages.index(p)
            dist = min(idx, len(all_pages) - 1 - idx)
            central_boost = 1.0 + dist * 0.1
            scores.append((body_ratio * central_boost, p))

    # Pick top pages
    scores.sort(reverse=True)
    anchor_pages = [p for _, p in scores[: max(3, len(scores) // 2)]]
    if anchor_pages:
        return sorted(anchor_pages)
    # Fallback: exclude page 1 even in fallback
    fallback = [p for p in all_pages if p != 1][:3]
    return fallback if fallback else []


def _is_body_spine_training_block(block: dict, idx: int, region_prepass: RegionPrepass | None) -> bool:
    if block.get("role") != "body_paragraph":
        return False
    if region_prepass is None:
        return True
    return region_prepass.block_regions.get(idx, "body") == "body"


def _detect_body_spine(
    blocks: list[dict],
    doc: DocumentStructure | None = None,
    region_prepass: RegionPrepass | None = None,
) -> dict[int, dict]:
    """Detect the main body column characteristics per page.

    Uses a two-pass approach:
    1. First pass: collect fonts and widths ONLY from anchor pages
       (stable middle-body pages, excluding page 1 and tail).
    2. Second pass: use the global anchor baseline for non-anchor pages
       instead of deriving from local (contaminated) data.

    When ``doc`` is provided, uses ``doc.spread_start`` for tail boundary
    detection.  Falls back to ``_reconcile_tail_spread`` when no doc is given.

    Returns dict[page_num, {"median_width": float, "median_x": float,
                            "anchor_median_width": float,
                            "anchor_fonts": set[str],
                            "anchor_pages": list[int],
                            "per_page_width": float,
                            "width_range": tuple[float, float],
                            "core_width_range": tuple[float, float],
                            "core_width_median": float,
                            "all_fonts": set[str],
                            "quality": str}]
    """
    import statistics

    by_page: dict[int, list[dict]] = {}
    block_idx: dict[int, int] = {}
    for idx, block in enumerate(blocks):
        page = block.get("page", 1)
        by_page.setdefault(page, []).append(block)
        block_idx[id(block)] = idx

    all_pages = sorted(by_page.keys())
    if not all_pages:
        return {}

    # Detect body/tail boundaries to derive anchor pages
    if doc is not None:
        anchor_pages = _select_body_anchor_pages(blocks, doc)
    else:
        # Fallback: detect boundaries via reconciliation
        tail_spine = _reconcile_tail_spread(blocks)
        if tail_spine is not None:
            temp_doc = DocumentStructure(
                spread_start=tail_spine.spread_start,
            )
            anchor_pages = _select_body_anchor_pages(blocks, temp_doc)
        else:
            anchor_pages = _select_body_anchor_pages(blocks)

    # ---- Pass 1: collect global anchor baseline from anchor pages only ----
    anchor_widths: list[float] = []
    anchor_x_starts: list[float] = []
    anchor_fonts: set[str] = set()
    anchor_font_counts: dict[str, int] = {}
    total_font_blocks = 0

    for page in anchor_pages:
        for b in by_page.get(page, []):
            if _is_body_spine_training_block(b, block_idx.get(id(b), -1), region_prepass):
                bbox = b.get("bbox", [0, 0, 0, 0])
                w = bbox[2] - bbox[0]
                if w >= 400:
                    anchor_widths.append(w)
                    anchor_x_starts.append(bbox[0])
                    span = b.get("span_metadata") or {}
                    first_font: str | None = None
                    if isinstance(span, list):
                        for s in span:
                            fam = s.get("font", "")
                            if fam:
                                anchor_fonts.add(str(fam).lower())
                                if first_font is None:
                                    first_font = str(fam).lower()
                    elif isinstance(span, dict):
                        fam = span.get("font", "")
                        if fam:
                            anchor_fonts.add(str(fam).lower())
                            first_font = str(fam).lower()
                    if first_font:
                        anchor_font_counts[first_font] = anchor_font_counts.get(first_font, 0) + 1
                        total_font_blocks += 1

    if anchor_widths:
        anchor_max = max(anchor_widths)
        core_anchor_widths = [w for w in anchor_widths if w >= 0.6 * anchor_max]
        core_width_median = statistics.median_low(core_anchor_widths) if core_anchor_widths else anchor_max
        core_width_range = (core_width_median * 0.7, core_width_median * 1.3)
    else:
        core_width_median = 500.0
        core_width_range = (350.0, 650.0)

    has_anchors = bool(anchor_pages)

    # ---- Per-page spine computation ----
    per_page_spine: dict[int, dict | None] = {}
    for page in all_pages:
        page_blocks = by_page[page]
        body_blocks = [
            b for b in page_blocks if _is_body_spine_training_block(b, block_idx.get(id(b), -1), region_prepass)
        ]

        if body_blocks:
            widths = []
            x_starts = []
            fonts: set[str] = set()
            for b in body_blocks:
                bbox = b.get("bbox", [0, 0, 0, 0])
                widths.append(bbox[2] - bbox[0])
                x_starts.append(bbox[0])
                span = b.get("span_metadata") or {}
                if isinstance(span, list):
                    for s in span:
                        fam = s.get("font", "")
                        if fam:
                            fonts.add(str(fam).lower())
                elif isinstance(span, dict):
                    fam = span.get("font", "")
                    if fam:
                        fonts.add(str(fam).lower())

            # For anchor pages: use local clustering (robust estimation)
            # For non-anchor pages with anchor data: use global anchor baseline
            # When no anchors exist (e.g. single-page doc), fall back to
            # per-page computation (original behavior).
            if page in anchor_pages:
                max_width = max(widths)
                core_widths = [w for w in widths if w >= 0.6 * max_width]
                median_width = statistics.median_low(core_widths) if core_widths else max_width
                median_x = statistics.median_low(x_starts)
                min_width = min(widths) if widths else max_width
                width_dispersion = (max_width - min_width) / median_width if median_width > 0 else 1.0
                font_coherence = len(fonts) <= 2
                sample_count = len(anchor_pages)
                if sample_count >= 3 and font_coherence and width_dispersion < 0.3:
                    quality = "strong"
                elif sample_count >= 1 and width_dispersion < 0.5:
                    quality = "moderate"
                else:
                    quality = "weak"
                per_page_spine[page] = {
                    "median_width": median_width,
                    "median_x": median_x,
                    "anchor_median_width": core_width_median,
                    "anchor_fonts": anchor_fonts,
                    "anchor_pages": anchor_pages,
                    "per_page_width": median_width,
                    "width_range": (median_width * 0.7, median_width * 1.3),
                    "fonts": fonts,
                    "all_fonts": anchor_fonts,
                    "core_width_range": core_width_range,
                    "core_width_median": core_width_median,
                    "quality": quality,
                }
            elif has_anchors:
                local_max_width = max(widths)
                local_min_width = min(widths)
                width_dispersion = (
                    (local_max_width - local_min_width) / core_width_median if core_width_median > 0 else 1.0
                )
                font_coherence = len(fonts) <= 2
                sample_count = len(anchor_pages)
                if sample_count >= 3 and font_coherence and width_dispersion < 0.3:
                    quality = "strong"
                elif sample_count >= 1 and width_dispersion < 0.5:
                    quality = "moderate"
                else:
                    quality = "weak"
                per_page_spine[page] = {
                    "median_width": core_width_median,
                    "median_x": statistics.median_low(x_starts) if x_starts else 100,
                    "anchor_median_width": core_width_median,
                    "anchor_fonts": anchor_fonts,
                    "anchor_pages": anchor_pages,
                    "per_page_width": statistics.median_low(widths) if widths else core_width_median,
                    "width_range": core_width_range,
                    "fonts": fonts,
                    "all_fonts": anchor_fonts,
                    "core_width_range": core_width_range,
                    "core_width_median": core_width_median,
                    "quality": quality,
                }
            else:
                # No anchors: per-page computation (original behavior)
                max_width = max(widths)
                core_widths = [w for w in widths if w >= 0.6 * max_width]
                median_width = statistics.median_low(core_widths) if core_widths else max_width
                median_x = statistics.median_low(x_starts)
                min_width = min(widths) if widths else max_width
                width_dispersion = (max_width - min_width) / median_width if median_width > 0 else 1.0
                font_coherence = len(fonts) <= 2
                sample_count = len(anchor_pages)
                if sample_count >= 3 and font_coherence and width_dispersion < 0.3:
                    quality = "strong"
                elif sample_count >= 1 and width_dispersion < 0.5:
                    quality = "moderate"
                else:
                    quality = "weak"
                all_body_fonts: set[str] = set()
                for b in body_blocks:
                    span = b.get("span_metadata") or {}
                    if isinstance(span, list):
                        for s in span:
                            fam = s.get("font", "")
                            if fam:
                                all_body_fonts.add(str(fam).lower())
                    elif isinstance(span, dict):
                        fam = span.get("font", "")
                        if fam:
                            all_body_fonts.add(str(fam).lower())
                per_page_spine[page] = {
                    "median_width": median_width,
                    "median_x": median_x,
                    "anchor_median_width": core_width_median,
                    "anchor_fonts": all_body_fonts,
                    "anchor_pages": anchor_pages,
                    "per_page_width": median_width,
                    "width_range": (median_width * 0.7, median_width * 1.3),
                    "fonts": fonts,
                    "all_fonts": all_body_fonts,
                    "core_width_range": core_width_range,
                    "core_width_median": core_width_median,
                    "quality": quality,
                }
        else:
            per_page_spine[page] = None

    # Fill missing pages
    filled: dict[int, dict] = {}
    prev_val = None
    for page in all_pages:
        if per_page_spine[page] is not None:
            prev_val = per_page_spine[page]
            filled[page] = per_page_spine[page]
        elif prev_val is not None:
            filled[page] = prev_val
        else:
            next_val = None
            for p in all_pages:
                if p > page and per_page_spine[p] is not None:
                    next_val = per_page_spine[p]
                    break
            filled[page] = (
                prev_val
                or next_val
                or {
                    "median_width": core_width_median,
                    "median_x": 100,
                    "anchor_median_width": core_width_median,
                    "anchor_fonts": anchor_fonts,
                    "anchor_pages": anchor_pages,
                    "per_page_width": core_width_median,
                    "width_range": core_width_range,
                    "fonts": set(),
                    "all_fonts": anchor_fonts,
                    "core_width_range": core_width_range,
                    "core_width_median": core_width_median,
                    "quality": "weak",
                }
            )

    # Compute _meta quality from anchor data (after per-page loop to avoid
    # variable shadowing from per-page font_coherence / width_dispersion).
    meta_font_coherence = 0.0
    if total_font_blocks > 0 and anchor_font_counts:
        majority_count = max(anchor_font_counts.values())
        meta_font_coherence = majority_count / total_font_blocks

    meta_width_dispersion = 0.0
    if len(anchor_widths) >= 2:
        meta_width_dispersion = statistics.stdev(anchor_widths) / statistics.mean(anchor_widths)

    meta_sample_count = len(anchor_widths)

    if len(anchor_pages) >= 3 and meta_font_coherence > 0.8 and meta_width_dispersion < 0.3:
        meta_quality = "strong"
    elif len(anchor_pages) >= 1:
        meta_quality = "moderate"
    else:
        meta_quality = "weak"

    filled["_meta"] = {
        "anchor_pages": anchor_pages,
        "sample_count": meta_sample_count,
        "font_coherence": meta_font_coherence,
        "width_dispersion": meta_width_dispersion,
        "quality": meta_quality,
    }

    return filled


def _detect_non_body_insert_clusters(
    blocks: list[dict],
    body_spine: dict[int, dict],
    page_height: float = 1600,
    page_width: float = 1200,
    body_end_page: int | None = None,
) -> set[int]:
    """Return indices of blocks that belong to early-page non-body insert clusters.

    Detection criteria:
    1. Early document region (relative to body length, not an absolute page number)
    2. Block role is ``body_paragraph``, ``figure_caption``, or ``unknown_structural``
       (NOT frontmatter_noise — those are genuine furniture blocks)
       ``figure_caption`` is included because PaddleOCR sometimes labels narrow
       author-bio side-panel blocks as figure_title/figure_caption.
    Width signal: block width < 70% of body spine median,
      falling back to page_width * 0.5 if median is contaminated
    Font-family signal (secondary): block's font differs from body spine fonts
    Cluster requirement: 2+ candidates on the same page
    """
    indices: set[int] = set()

    # Use a relative early-page bound instead of an absolute page gate
    max_early_page = min(3, max(1, (body_end_page or 12) // 4 + 1))

    def _first_font(block: dict) -> str | None:
        span = block.get("span_metadata") or {}
        if isinstance(span, list):
            for s in span:
                fam = s.get("font", "")
                if fam:
                    return str(fam).lower()
        elif isinstance(span, dict):
            return str(span.get("font", "") or "").lower() or None
        return None

    # Read spine trust quality from _meta (not per-page quality, which is
    # contaminated on early pages).  Strong spine: width/font baseline is
    # reliable enough to trust either signal in isolation.  Moderate spine:
    # need both signals or cluster support.  Weak spine: no anchor pages
    # existed, so width/font data are untrustworthy — require both signals.
    spine_meta = body_spine.get("_meta", {})
    quality = spine_meta.get("quality", "weak")

    candidates_by_page: dict[int, list[int]] = {}
    for i, block in enumerate(blocks):
        page = block.get("page", 1)
        if page > max_early_page:
            continue

        # body_paragraph, figure_caption, figure_caption_candidate, and
        # unknown_structural can be non-body inserts — bio/profile blocks that
        # OCR misclassified as body text or figure titles.  frontmatter_noise
        # blocks are genuine furniture, not bios, so they are excluded.
        _INSERT_CANDIDATE_ROLES = {"body_paragraph", "figure_caption", "figure_caption_candidate", "unknown_structural"}
        if block.get("role") not in _INSERT_CANDIDATE_ROLES:
            continue

        # Never mark page-1 title-like blocks as non_body_insert
        if page == 1:
            text = (block.get("text") or "").strip()
            if len(text) > 20 and not any(m in text.lower() for m in ["\u2022", "-", "*"]):
                continue

        bbox = block.get("bbox", [0, 0, 0, 0])

        # Skip blocks without valid bbox (text-less spacers, rule lines)
        if len(bbox) < 4:
            continue
        block_width = bbox[2] - bbox[0]
        if block_width <= 10:
            continue

        spine_key = page if page in body_spine else 1
        spine = body_spine.get(spine_key, {"median_width": 500})
        median_width = spine.get("median_width", 500)
        if not isinstance(median_width, (int, float)) or median_width <= 0:
            median_width = 500

        is_narrow = block_width < 0.7 * median_width or (
            page_width > 0 and median_width < page_width * 0.4 and block_width < page_width * 0.35
        )

        block_font = _first_font(block)
        spine_fonts = spine.get("all_fonts") or spine.get("fonts", set())
        if not isinstance(spine_fonts, set):
            spine_fonts = set(spine_fonts) if spine_fonts else set()
        font_mismatch = bool(block_font and spine_fonts and block_font not in spine_fonts)

        if quality == "strong":
            passes = is_narrow or (font_mismatch and block_width < 0.9 * median_width)
        elif quality == "moderate":
            passes = is_narrow and (font_mismatch or len(candidates_by_page.get(page, [])) >= 1)
        else:
            passes = is_narrow and font_mismatch

        if passes:
            candidates_by_page.setdefault(page, []).append(i)

    for candidate_indices in candidates_by_page.values():
        if len(candidate_indices) >= 2:
            indices.update(candidate_indices)

    # Second pass: expand to orphan continuation fragments adjacent to
    # detected non-body inserts.  These are body-width blocks (same width
    # as the body spine) that share a font with the insert cluster but
    # were split off by OCR and start with a lowercase letter (no
    # standalone paragraph start).
    if indices:
        insert_fonts: set[str] = set()
        for idx in indices:
            f = _first_font(blocks[idx])
            if f:
                insert_fonts.add(f)
        if insert_fonts:
            for i, block in enumerate(blocks):
                if i in indices:
                    continue
                page = block.get("page", 1)
                if page > max_early_page:
                    continue
                if block.get("role") not in _INSERT_CANDIDATE_ROLES:
                    continue
                text = block.get("text", "")
                if not text or not text[0].islower():
                    continue
                block_font = _first_font(block)
                if block_font and block_font in insert_fonts:
                    # Check adjacency to existing cluster members on the same page
                    for idx in indices:
                        if blocks[idx].get("page") == page and abs(i - idx) <= 2:
                            indices.add(i)
                            break

    return indices


def _looks_like_figure_narrative_prose(text: str) -> bool:
    """Detect narrative prose blocks that start with Fig. but are not formal legends."""
    sentence_count = text.count(". ") + text.count(".\n")
    if sentence_count >= 2:
        return True
    lower = text.lower()
    prose_markers = ["we ", "our ", "this study", "here we", "in this"]
    if any(m in lower for m in prose_markers):
        return True
    if re.search(
        r"\b(?:figure|fig\.?)\s+\d+[a-z]?\s+(?:shows|show|shown|demonstrates|demonstrate|illustrates|illustrate|depicts|presents|reveals|indicates|compares|summarizes)\b",
        lower,
    ):
        return True
    return bool(re.search(r"\$?\^\{[^}]+\}\$?", text) and sentence_count >= 1)


def _check_caption_style_match(block: dict, blocks: list[dict]) -> bool:
    """Check if block's span style matches known figure_caption blocks."""
    span = block.get("span_metadata") or {}
    if isinstance(span, list):
        span = span[0] if span else {}
    block_size = span.get("size")
    block_font = str(span.get("font", "") or "").lower()
    if block_size is None:
        return False
    caption_sizes: list[float] = []
    caption_fonts: set[str] = set()
    for b in blocks:
        if b.get("role") == "figure_caption":
            s = b.get("span_metadata") or {}
            if isinstance(s, list):
                s = s[0] if s else {}
            sz = s.get("size")
            if sz is not None:
                caption_sizes.append(sz)
            fn = str(s.get("font", "") or "").lower()
            if fn:
                caption_fonts.add(fn)
    if not caption_sizes:
        return False
    size_match = any(abs(block_size - sz) <= 1.0 for sz in caption_sizes)
    font_match = (block_font in caption_fonts) if block_font else True
    return size_match and font_match


def _resolve_ambiguous_candidates(
    blocks: list[dict],
    doc_structure: DocumentStructure,
    page_layouts: dict[int, PageLayoutProfile],
) -> None:
    """Resolve candidate roles from seed pass into final roles using document context.

    Mutates blocks in place.
    """
    body_end_page = doc_structure.body_end_page
    backmatter_start_page: int | None = doc_structure.backmatter_start.page if doc_structure.backmatter_start else None
    references_start_page: int | None = doc_structure.references_start.page if doc_structure.references_start else None
    backmatter_form = doc_structure.backmatter_form

    # Detect container boundary heading (independent of form classification,
    # since form is determined before resolution promotes candidates)
    has_container_boundary = False
    container_boundary_page: int | None = None
    for b in blocks:
        if b.get("role") in _BOUNDARY_ROLES:
            has_container_boundary = True
            container_boundary_page = b.get("page")
            break

    def _child_heading_count(
        start_idx: int,
        page: int,
        col: int,
        boundaries: list[float],
    ) -> float:
        count = 0.0
        for j in range(start_idx + 1, min(start_idx + 10, len(blocks))):
            nb = blocks[j]
            if nb.get("page") != page:
                continue
            if len(boundaries) > 1:
                nbb = nb.get("bbox") or nb.get("block_bbox") or [0, 0, 0, 0]
                nx = (nbb[0] + nbb[2]) / 2
                ncol = _get_column_index_by_boundaries(nx, boundaries)
                if ncol != col:
                    continue
            nr = nb.get("role", "")
            if nr in ("backmatter_heading", "backmatter_heading_candidate"):
                count += 1.0
            elif nr == "backmatter_body":
                count += 0.5
        return count

    for i, block in enumerate(blocks):
        role = block.get("role", "")
        page = block.get("page", 1)
        bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]

        # ---- 2.1 Resolve backmatter_heading_candidate ----
        if role == "backmatter_heading_candidate":
            # Papers with a container boundary heading: headings on earlier
            # pages than the boundary are demoted to body_paragraph.  On the
            # same page, only headings in a different column than the boundary
            # (multi-column layout with independent streams) are kept visible.
            if has_container_boundary and page < container_boundary_page:
                old_role = block.get("role")
                block["role"] = "body_paragraph"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="candidate_resolution",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="backmatter heading candidate before container boundary, demoted to body",
                    )
                block["role_confidence"] = 0.5
                continue

            if has_container_boundary and page == container_boundary_page:
                layout = page_layouts.get(page)
                _same_column = True  # single-column → same column
                boundary_bottom = 0
                if layout and layout.column_count > 1:
                    boundaries = layout.column_boundaries
                    x_center = (bbox[0] + bbox[2]) / 2
                    col = _get_column_index_by_boundaries(x_center, boundaries)
                    for b in blocks:
                        if b.get("role") in _BOUNDARY_ROLES and b.get("page") == page:
                            bb = b.get("bbox") or b.get("block_bbox") or [0, 0, 0, 0]
                            bx = (bb[0] + bb[2]) / 2
                            boundary_col = _get_column_index_by_boundaries(bx, boundaries)
                            _same_column = col == boundary_col
                            boundary_bottom = bb[3] if len(bb) > 3 else 0
                            break
                    else:
                        boundary_bottom = 0
                if _same_column and bbox[1] < boundary_bottom:
                    old_role = block.get("role")
                    block["role"] = "body_paragraph"
                    if old_role != block["role"]:
                        record_decision(
                            block,
                            stage="candidate_resolution",
                            old_role=old_role,
                            new_role=block["role"],
                            reason="backmatter heading candidate in same column above boundary, demoted to body",
                        )
                    block["role_confidence"] = 0.5
                    continue
                # Different column on boundary page → container child in
                # multi-column layout (e.g. FUNDING left col, ADDITIONAL
                # INFORMATION right col).  Promote to backmatter_heading.
                old_role = block.get("role")
                block["role"] = "backmatter_heading"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="candidate_resolution",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="backmatter heading candidate in different column, promoted to backmatter heading",
                    )
                block["role_confidence"] = 0.5
                continue

            if backmatter_start_page is None:
                old_role = block.get("role")
                block["role"] = "section_heading"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="candidate_resolution",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="backmatter heading candidate with no backmatter start, treated as section_heading",
                    )
                block["role_confidence"] = 0.5
                continue

            if page < backmatter_start_page:
                if has_container_boundary and page == container_boundary_page:
                    old_role = block.get("role")
                    block["role"] = "backmatter_heading"
                    if old_role != block["role"]:
                        record_decision(
                            block,
                            stage="candidate_resolution",
                            old_role=old_role,
                            new_role=block["role"],
                            reason="backmatter heading candidate on container boundary page, promoted to backmatter heading",
                        )
                    block["role_confidence"] = 0.5
                else:
                    old_role = block.get("role")
                    block["role"] = "section_heading"
                    if old_role != block["role"]:
                        record_decision(
                            block,
                            stage="candidate_resolution",
                            old_role=old_role,
                            new_role=block["role"],
                            reason="backmatter heading candidate before backmatter start, treated as section_heading",
                        )
                    block["role_confidence"] = 0.5
                continue

            if page == backmatter_start_page:
                layout = page_layouts.get(page)
                if layout and layout.column_count > 1:
                    boundaries = layout.column_boundaries
                    x_center = (bbox[0] + bbox[2]) / 2
                    col = _get_column_index_by_boundaries(x_center, boundaries)
                    if col == 0:
                        old_role = block.get("role")
                        block["role"] = "section_heading"
                        if old_role != block["role"]:
                            record_decision(
                                block,
                                stage="candidate_resolution",
                                old_role=old_role,
                                new_role=block["role"],
                                reason="backmatter heading candidate in left column of split backmatter page, treated as section_heading",
                            )
                        block["role_confidence"] = 0.5
                        continue
                old_role = block.get("role")
                block["role"] = "backmatter_heading"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="candidate_resolution",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="backmatter heading candidate on backmatter start page, promoted to backmatter heading",
                    )
                continue

            old_role = block.get("role")
            block["role"] = "backmatter_heading"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="candidate_resolution",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="backmatter heading candidate in backmatter region, promoted to backmatter heading",
                )

        # ---- 2.2 Resolve figure_caption_candidate ----
        if role == "figure_caption_candidate":
            text = block.get("text", "") or ""
            page_blocks = [b for b in blocks if b.get("page") == page]
            zone = str(block.get("zone") or "")
            style_family = str(block.get("style_family") or "")
            raw_label = str(block.get("raw_label") or block.get("block_label") or "")

            near_media = _is_near_figure_media(block, page_blocks)
            caption_style = _check_caption_style_match(block, blocks)
            is_prose = _looks_like_figure_narrative_prose(text)
            in_body_spine = body_end_page is not None and page <= body_end_page

            has_main_figure = bool(re.search(r"(?:Figure|Fig\.?)\s+\d+(?:\.\d+)?(?![a-z0-9])", text))
            has_subfigure_letter = bool(re.search(r"(?:Figure|Fig\.?)\s+\d+[a-z]", text))

            # Narrative figure mentions inside the body spine are body prose,
            # not captions, even if they start with a figure marker.
            if (
                in_body_spine
                and is_prose
                and not (zone == "display_zone" and style_family == "legend_like" and raw_label == "figure_title")
            ):
                old_role = block.get("role")
                block["role"] = "body_paragraph"
                if old_role != block["role"]:
                    reason = (
                        "subfigure reference with narrative prose in body spine, demoted to body"
                        if has_subfigure_letter
                        else "figure mention with narrative prose in body spine, demoted to body"
                    )
                    record_decision(
                        block, stage="candidate_resolution", old_role=old_role, new_role=block["role"], reason=reason
                    )
                continue

            if zone == "display_zone" and style_family == "legend_like" and raw_label == "figure_title":
                old_role = block.get("role")
                block["role"] = "figure_caption"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="candidate_resolution",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="display-zone figure_title legend stays figure caption",
                    )
                continue

            if near_media or caption_style or has_main_figure:
                old_role = block.get("role")
                block["role"] = "figure_caption"
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="candidate_resolution",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="figure caption candidate resolved as figure caption",
                    )
                continue
    # ---- 3. Activation gates (inline) ----
    for block in blocks:
        role = block.get("role", "")
        page = block.get("page", 1)
        text_lower = str(block.get("text") or "").strip().lower()

        if (
            role in ("backmatter_heading", "backmatter_body")
            and backmatter_start_page is not None
            and page < backmatter_start_page
            and backmatter_form != "container"
        ):
            old_role = block.get("role")
            block["role"] = "body_paragraph"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="candidate_resolution",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="backmatter block before backmatter start (non-container form), demoted to body",
                )

        if role == "reference_item" and references_start_page is not None and page < references_start_page:
            old_role = block.get("role")
            block["role"] = "body_paragraph"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="candidate_resolution",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="reference item before references start, demoted to body",
                )

        if role == "backmatter_heading_candidate" and body_end_page is not None and page <= body_end_page:
            old_role = block.get("role")
            block["role"] = "body_paragraph"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="candidate_resolution",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="backmatter heading candidate in body region, demoted to body",
                )

        if (
            role in {"section_heading", "subsection_heading", "sub_subsection_heading"}
            and "published online" in text_lower
        ):
            old_role = block.get("role")
            block["role"] = "frontmatter_noise"
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="candidate_resolution",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="published-online furniture cannot survive as heading",
                )


def _mark_non_body_media(blocks: list[dict]) -> None:
    insert_blocks_by_page: dict[int, list[dict]] = {}
    for block in blocks:
        if block.get("_non_body_insert"):
            page = block.get("page", 1)
            insert_blocks_by_page.setdefault(page, []).append(block)

    if not insert_blocks_by_page:
        return

    for page, inserts in insert_blocks_by_page.items():
        bboxes = []
        for ins in inserts:
            b = ins.get("bbox") or ins.get("block_bbox")
            if b and len(b) >= 4:
                bboxes.append(b)
        if not bboxes:
            continue

        cluster_min_x = min(b[0] for b in bboxes)
        cluster_min_y = min(b[1] for b in bboxes)
        cluster_max_x = max(b[2] for b in bboxes)
        cluster_max_y = max(b[3] for b in bboxes)

        margin = 50
        cluster_min_x -= margin
        cluster_min_y -= margin
        cluster_max_x += margin
        cluster_max_y += margin

        for block in blocks:
            if block.get("page", 1) != page:
                continue
            if block.get("_non_body_media"):
                continue
            role = block.get("role", "")
            if role not in ("figure_asset", "media_asset"):
                continue

            b = block.get("bbox") or block.get("block_bbox")
            if not b or len(b) < 4:
                continue

            cx = (b[0] + b[2]) / 2
            cy = (b[1] + b[3]) / 2

            if cluster_min_x <= cx <= cluster_max_x and cluster_min_y <= cy <= cluster_max_y:
                block["_non_body_media"] = True


_TITLE_SENTENCE_VERBS = frozenset(
    (
        "provides",
        "shows",
        "demonstrates",
        "describes",
        "reports",
        "indicates",
        "suggests",
        "reveals",
        "examines",
        "investigates",
        "explores",
        "analyzes",
        "presents",
        "discusses",
        "proposes",
        "introduces",
        "highlights",
        "summarizes",
        "evaluates",
        "compares",
        "identifies",
        "includes",
        "contains",
        "represents",
        "involves",
        "requires",
        "produces",
        "results",
        "performed",
        "conducted",
        "observed",
        "measured",
        "show",
        "demonstrate",
        "describe",
        "indicate",
        "suggest",
        "reveal",
        "present",
        "discuss",
        "propose",
        "introduce",
        "examine",
        "investigate",
    )
)


def _is_page1_title(text: str) -> bool:
    t = text.strip()
    if not t or len(t) < 20:
        return False
    if "\u2022" in t or t.startswith("- "):
        return False
    tl = t.lower()
    if any(v in tl for v in (" is ", " are ", " was ", " were ")):
        return False
    return all(w not in _TITLE_SENTENCE_VERBS for w in tl.split())


def _detect_structured_insert_clusters(blocks: list[dict]) -> set[int]:
    """Cluster structured insert candidates into organized insert regions.

    Uses:
    - detached geometry (blocks near each other but separated from body flow)
    - heading + short items pattern (short heading followed by bullet/text blocks)
    - list shape / line-height / family mismatch as supporting evidence

    Returns set of block indices to mark as structured_insert.
    """
    candidate_indices = {i for i, b in enumerate(blocks) if b.get("role") == "structured_insert_candidate"}
    if len(candidate_indices) < 1:
        return set()

    # Group by page
    from collections import defaultdict

    by_page = defaultdict(list)
    for idx in candidate_indices:
        p = blocks[idx].get("page", 1)
        by_page[p].append(idx)

    # Per page: check if candidates form a coherent cluster
    result = set()
    for page, indices in by_page.items():
        # Get bboxes
        bboxes = []
        for idx in indices:
            bb = blocks[idx].get("bbox") or blocks[idx].get("block_bbox") or [0, 0, 0, 0]
            bboxes.append((idx, bb))

        has_box_anchor = any(
            _looks_like_box_anchor(str(blocks[idx].get("text") or blocks[idx].get("block_content") or ""))
            for idx in indices
        )
        if has_box_anchor:
            result.update(indices)
            continue

        # A single box anchor is enough to seed a sidebar cluster when adjacent
        # mixed-role blocks exist on the same page; expansion will absorb the
        # neighboring table/html/footnote payload.
        if len(indices) == 1:
            idx = indices[0]
            text = str(blocks[idx].get("text") or blocks[idx].get("block_content") or "")
            if _looks_like_box_anchor(text):
                result.add(idx)
                continue

        # Check if blocks are near each other (vertical gaps < 100px)
        bboxes.sort(key=lambda x: x[1][1])
        cluster_indices = []
        for i, (idx, bb) in enumerate(bboxes):
            if not cluster_indices:
                cluster_indices.append(idx)
                continue
            prev_bb = bboxes[i - 1][1]
            gap = bb[1] - prev_bb[3]
            if gap < 100 and gap >= -20:  # overlapping or close
                cluster_indices.append(idx)

        if len(cluster_indices) >= 2:
            result.update(cluster_indices)

    return result


def _expand_structured_insert_cluster_with_mixed_sidebar_blocks(
    blocks: list[dict],
    indices: set[int],
) -> set[int]:
    if not indices:
        return indices

    expanded = set(indices)
    by_page: dict[int, list[int]] = {}
    for idx in indices:
        page = int(blocks[idx].get("page", 1) or 1)
        by_page.setdefault(page, []).append(idx)

    heading_roles = {
        "section_heading",
        "subsection_heading",
        "sub_subsection_heading",
        "reference_heading",
        "backmatter_heading",
    }
    mixed_roles = {"media_asset", "table_html", "unknown_structural", "structured_insert_candidate"}

    for page, page_indices in by_page.items():
        changed = True
        while changed:
            changed = False
            current_page_indices = [idx for idx in expanded if int(blocks[idx].get("page", 1) or 1) == page]
            current_texts = [str(blocks[idx].get("text") or "") for idx in current_page_indices]
            has_box_anchor = any(_looks_like_box_anchor(text) for text in current_texts)
            bboxes = [blocks[idx].get("bbox") or blocks[idx].get("block_bbox") for idx in current_page_indices]
            bboxes = [bb for bb in bboxes if bb and len(bb) >= 4]
            if not bboxes:
                break

            cluster_min_x = min(bb[0] for bb in bboxes)
            cluster_max_x = max(bb[2] for bb in bboxes)
            cluster_min_y = min(bb[1] for bb in bboxes)
            cluster_max_y = max(bb[3] for bb in bboxes)

            next_heading_top = None
            for i, block in enumerate(blocks):
                if int(block.get("page", 1) or 1) != page or i in expanded:
                    continue
                role = block.get("role", "")
                if role not in heading_roles:
                    continue
                bb = block.get("bbox") or block.get("block_bbox")
                if not bb or len(bb) < 4:
                    continue
                block_x_center = (bb[0] + bb[2]) / 2
                same_column = block_x_center < (cluster_min_x + cluster_max_x) / 2 + 200
                if (
                    has_box_anchor
                    and same_column
                    and bb[0] <= cluster_max_x + 40
                    and bb[2] >= cluster_min_x - 40
                    and (bb[1] - cluster_max_y) <= 140
                ):
                    continue
                if bb[1] > cluster_max_y and (next_heading_top is None or bb[1] < next_heading_top):
                    next_heading_top = bb[1]

            for i, block in enumerate(blocks):
                if int(block.get("page", 1) or 1) != page or i in expanded:
                    continue
                role = block.get("role", "")
                text = str(block.get("text") or "").strip()
                bb = block.get("bbox") or block.get("block_bbox")
                if not bb or len(bb) < 4:
                    continue
                if next_heading_top is not None and bb[1] >= next_heading_top:
                    continue

                page_width = max(block.get("page_width", 0) or 0, 1200)
                cluster_x_center = (cluster_min_x + cluster_max_x) / 2
                block_x_center = (bb[0] + bb[2]) / 2
                same_column = (cluster_x_center < page_width * 0.5 and block_x_center < page_width * 0.55) or (
                    cluster_x_center >= page_width * 0.5 and block_x_center >= page_width * 0.45
                )
                overlaps_x = bb[0] <= cluster_max_x + 40 and bb[2] >= cluster_min_x - 40
                near_y = bb[1] <= cluster_max_y + 80 and bb[3] >= cluster_min_y - 20
                bullet_like = text.startswith(("•", "-", "*"))
                table_like = text.lower().startswith("<table")
                vision_footnote_like = str(block.get("raw_label") or "") == "vision_footnote"

                if (
                    overlaps_x
                    and near_y
                    and same_column
                    and (role in mixed_roles or bullet_like or table_like or vision_footnote_like)
                ):
                    expanded.add(i)
                    changed = True

    return expanded


def _is_full_width_heading(block: dict, page_width: float) -> bool:
    bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
    return len(bbox) >= 4 and (bbox[2] - bbox[0]) > page_width * 0.55


def _overlap_area_ratio(bbox_a: list[float], bbox_b: list[float]) -> float:
    x_overlap = max(0, min(bbox_a[2], bbox_b[2]) - max(bbox_a[0], bbox_b[0]))
    y_overlap = max(0, min(bbox_a[3], bbox_b[3]) - max(bbox_a[1], bbox_b[1]))
    if x_overlap <= 0 or y_overlap <= 0:
        return 0.0
    overlap = x_overlap * y_overlap
    area_a = max((bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1]), 1)
    area_b = max((bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1]), 1)
    return overlap / min(area_a, area_b)


def _run_layout_audit(
    blocks: list[dict],
    body_spine: dict | None = None,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> dict:
    """Check resolved structure for obvious geometric contradictions.

    Returns dict with severity-gated anomalies:
        status: str "pass", "warn" (warning_count>0), or "fail" (error_count>0)
        info_count / warning_count / error_count: int
        anomaly_count: int (total, backward compatible)
        anomaly_pages: list[int] (error pages only)
        anomalies: list[dict] with type/severity/page/reason/evidence
    """
    anomalies: list[dict] = []

    by_page: dict[int, list[dict]] = {}
    for b in blocks:
        p = b.get("page", 1)
        by_page.setdefault(p, []).append(b)

    spine_quality = "weak"
    if body_spine and isinstance(body_spine, dict):
        meta = body_spine.get("_meta", {})
        if isinstance(meta, dict):
            spine_quality = meta.get("quality", "weak") or "weak"

    for page, page_blocks in by_page.items():
        page_width = max((b.get("page_width", 0) or 0) for b in page_blocks) or 1200
        pw_mid = page_width / 2

        page_layout_conf = 0.0
        if page_layouts and page in page_layouts:
            page_layout_conf = page_layouts[page].confidence

        headings = [b for b in page_blocks if b.get("role") in ("section_heading", "subsection_heading")]
        body_blocks = [b for b in page_blocks if b.get("role") == "body_paragraph"]

        # Check 1: heading owns body above it (cross-column)
        for h in headings:
            hb = h.get("bbox") or h.get("block_bbox") or [0, 0, 0, 0]
            if len(hb) < 4:
                continue
            hx = (hb[0] + hb[2]) / 2
            hy = hb[1]
            h_col = 0 if hx < pw_mid else 1
            for body in body_blocks:
                bb = body.get("bbox") or body.get("block_bbox") or [0, 0, 0, 0]
                if len(bb) < 4:
                    continue
                bx = (bb[0] + bb[2]) / 2
                by_ = bb[1]
                b_col = 0 if bx < pw_mid else 1
                if h_col != b_col and by_ < hy:
                    is_full_width = _is_full_width_heading(h, page_width)
                    has_nearer_heading = False
                    for h2 in headings:
                        if h2 is h:
                            continue
                        h2b = h2.get("bbox") or h2.get("block_bbox") or [0, 0, 0, 0]
                        if len(h2b) < 4:
                            continue
                        h2x = (h2b[0] + h2b[2]) / 2
                        h2_col = 0 if h2x < pw_mid else 1
                        if h2_col == b_col and h2b[3] <= by_:
                            has_nearer_heading = True
                            break

                    if page_layout_conf >= 0.7 and not is_full_width and not has_nearer_heading:
                        severity = "error"
                    else:
                        severity = "info"

                    if severity == "error" and page_layout_conf < 0.7:
                        severity = "info"

                    anomalies.append(
                        {
                            "type": "heading_cross_column_ownership",
                            "severity": severity,
                            "page": page,
                            "reason": f"heading on column {h_col} owns body in column {b_col} above it",
                            "evidence": {},
                        }
                    )
                    break

        # Check 2: structured_insert overlaps body region
        inserts = [b for b in page_blocks if b.get("role") in ("non_body_insert", "structured_insert")]
        body_blocks_p2 = [b for b in page_blocks if b.get("role") == "body_paragraph"]
        for ins in inserts:
            ib = ins.get("bbox") or ins.get("block_bbox") or [0, 0, 0, 0]
            if len(ib) < 4:
                continue
            for body in body_blocks_p2:
                bb = body.get("bbox") or body.get("block_bbox") or [0, 0, 0, 0]
                if len(bb) < 4:
                    continue
                if ib[0] < bb[2] and ib[2] > bb[0] and ib[1] < bb[3] and ib[3] > bb[1]:
                    overlap_ratio = _overlap_area_ratio(ib, bb)
                    insert_score_val = float(
                        (ins.get("insert_score") or {}).get("score", 0.0)
                        if isinstance(ins.get("insert_score"), dict)
                        else 0.0
                    )
                    body_raw_label = (body.get("raw_label") or "").lower()
                    is_body_real = body_raw_label not in ("figure", "table", "inner_text")

                    if (
                        insert_score_val >= 0.7
                        and spine_quality in ("strong", "moderate")
                        and overlap_ratio > 0.3
                        and is_body_real
                    ):  # noqa: E501
                        severity = "warning" if overlap_ratio < 0.6 else "error"
                    else:
                        severity = "info"

                    if severity == "error" and page_layout_conf < 0.7:
                        severity = "info"

                    anomalies.append(
                        {
                            "type": "structured_insert_body_overlap",
                            "severity": severity,
                            "page": page,
                            "reason": f"{ins.get('role', 'insert')} overlaps body region",
                            "evidence": {"overlap_area_ratio": overlap_ratio},
                        }
                    )
                    break

    error_count = sum(1 for a in anomalies if a["severity"] == "error")
    warning_count = sum(1 for a in anomalies if a["severity"] == "warning")
    info_count = sum(1 for a in anomalies if a["severity"] == "info")

    if error_count > 0:
        status = "fail"
    elif warning_count > 0:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "info_count": info_count,
        "warning_count": warning_count,
        "error_count": error_count,
        "anomaly_count": len(anomalies),
        "anomaly_pages": sorted({a["page"] for a in anomalies if a["severity"] == "error"}),
        "anomalies": anomalies,
    }


def _doc_get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _build_source_frontmatter_anchor_ids(doc_structure, blocks: list[dict]) -> dict[str, set]:
    result = {"title": set(), "authors": set(), "doi": set()}

    # New / explicit shape
    ids = _doc_get(doc_structure, "source_frontmatter_anchor_ids", {}) or {}
    for field in ("title", "authors", "doi"):
        vals = _doc_get(ids, field, set()) or set()
        if isinstance(vals, (list, tuple, set)):
            result[field].update(vals)
        elif vals:
            result[field].add(vals)

    # Existing production shape (source_frontmatter_anchors with _source_anchor suffix keys)
    anchors = _doc_get(doc_structure, "source_frontmatter_anchors", {}) or {}
    for field in ("title", "authors", "doi"):
        anchor = _doc_get(anchors, f"{field}_source_anchor", {}) or {}
        bid = _doc_get(anchor, "ocr_block_id")
        if bid is not None:
            result[field].add(bid)
            page = _doc_get(anchor, "ocr_page")
            if page is not None:
                result[field].add(f"p{page}:{bid}")

    return result


def _collect_unverified_required_roles(blocks: list[dict]) -> list[dict]:
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED

    return [
        block
        for block in blocks
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT"
    ]


def _assert_verified_required_roles(blocks: list[dict]) -> None:
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED

    offenders = [
        block.get("block_id")
        for block in blocks
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT"
    ]
    if offenders:
        raise ValueError(f"Unverified structural roles after OCR gate: {offenders[:10]}")


def _build_accepted_heading_block_ids(blocks: list[dict], doc_structure) -> set:
    heading_artifact = _doc_get(doc_structure, "accepted_heading_block_ids", set()) or set()
    result = set(heading_artifact)
    _HEADING_SEED_ROLES = {"section_heading", "subsection_heading", "sub_subsection_heading"}
    for block in blocks:
        if block.get("seed_role") in _HEADING_SEED_ROLES and block.get("zone") in {"body_zone", "tail_body_zone"}:
            bid = block.get("block_id")
            if bid is not None:
                result.add(bid)
    return result


def _build_accepted_caption_block_ids(
    figure_inventory: dict | None, reader_payload: dict | None, blocks: list[dict]
) -> set:
    accepted = set()
    for figure in (reader_payload or {}).get("reader_figures", []):
        for item in figure.get("consumed_caption_block_ids", []):
            if isinstance(item, dict):
                accepted.add(item.get("block_id"))
            else:
                accepted.add(item)
    accepted.discard(None)
    return accepted


def _build_accepted_table_block_ids(table_inventory: dict | None, blocks: list[dict]) -> set:
    accepted = set()
    for table in (table_inventory or {}).get("matched_tables", []):
        for key in ("block_id", "table_block_id", "html_block_id"):
            if table.get(key) is not None:
                accepted.add(table[key])
    return accepted


def _demote_early_frontmatter_body_leaks(blocks: list[dict]) -> None:
    heading_seen_by_page: dict[int, bool] = {}
    for block in blocks:
        page = int(block.get("page", 0) or 0)
        if block.get("role") in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            heading_seen_by_page[page] = True
            continue
        if block.get("role") != "body_paragraph":
            continue
        if page <= 0 or page > 2:
            continue
        if heading_seen_by_page.get(page):
            continue
        if block.get("seed_role") == "abstract_body":
            continue
        text = _block_text(block).strip()
        text_plain = _strip_inline_html(text)
        lower = text.lower()
        if not text:
            continue
        if (
            _looks_like_author_list(text_plain)
            or _looks_like_affiliation(text_plain)
            or ("<sup>" in text and text.count(",") >= 2)
            or (text_plain.count("Dr ") >= 2 or text_plain.count("Prof ") >= 2 or " dr med" in text_plain.lower())
            or re.match(r"^[a-z]\.\s", text_plain.lower())
        ):
            block["role"] = "frontmatter_support"
            block["render_default"] = False
            continue
        if lower.startswith(("pii:", "reference:", "to appear in:", "revised date:", "doi ", "doi:", "received:", "accepted date:")):
            block["role"] = "frontmatter_noise"
            block["render_default"] = False
            continue


def _restore_numbered_body_from_tail_hold(blocks: list[dict]) -> None:
    active_numbered_body = False
    for block in blocks:
        role = block.get("role")
        text = _canonical_section_text(block)
        marker_type = str(((block.get("marker_signature") or {}).get("type")) or "none")

        if role in {"reference_heading", "backmatter_heading", "backmatter_boundary_heading"}:
            active_numbered_body = False
            continue

        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            active_numbered_body = (
                (
                    marker_type
                    in {"heading_numbered", "heading_arabic", "heading_decimal", "heading_roman", "heading_alpha"}
                    or (
                        block.get("zone") == "tail_nonref_hold_zone"
                        and str(block.get("style_family") or "") == "heading_like"
                    )
                )
                and text not in _BACKMATTER_TITLE_DENY_LIST
            )
            continue

        if role == "backmatter_body" and active_numbered_body:
            block["role"] = "body_paragraph"


def normalize_document_structure(
    blocks: list[dict],
    source_frontmatter_anchors: dict | None = None,
) -> tuple[DocumentStructure, list[dict]]:
    """Analyze document structure and normalize roles.

    Returns (document_structure, normalized_blocks).
    Normalization includes:
    - backmatter form classification
    - backmatter role normalization after boundary
    - tail body candidate promotion
    - tail spread ownership assignment
    """
    page_layouts = _build_page_layout_profiles(blocks)
    body_family_anchor = discover_body_family_anchor(blocks)
    reference_family_anchor = discover_reference_family_anchor(blocks)
    region_bus = infer_zones(
        blocks,
        {
            "body_family_anchor": body_family_anchor,
            "reference_family_anchor": reference_family_anchor,
        },
    )
    _apply_zone_labels(blocks, region_bus)
    partition_zone_families(
        blocks,
        {
            "body_family_anchor": body_family_anchor,
            "reference_family_anchor": reference_family_anchor,
        },
    )
    _exclude_frontmatter_side_from_body_flow(blocks)
    _exclude_tail_nonref_from_body_flow(blocks)

    from paperforge.worker.ocr_roles import resolve_final_role

    family_context = {
        str(block.get("block_id") or f"block_{idx}"): {
            "zone": block.get("zone"),
            "style_family": block.get("style_family"),
            "style_family_authority": block.get("style_family_authority"),
        }
        for idx, block in enumerate(blocks)
    }
    anchor_context = {
        "body_family_anchor": body_family_anchor,
        "reference_family_anchor": reference_family_anchor,
    }
    for block in blocks:
        resolved = resolve_final_role(block, anchors=anchor_context, families=family_context)
        if resolved.role != block.get("role"):
            block["role"] = resolved.role
            block["role_confidence"] = resolved.confidence
            if resolved.evidence:
                block.setdefault("evidence", []).extend(resolved.evidence)

    # Backmatter heading candidate promotion: confirm candidates that are
    # followed by body-like text on the same page.  This runs after role
    # resolution (which may have reclassified the candidate via editorial
    # phrase detection) and uses seed_role to recover the original intent.
    for idx, block in enumerate(blocks):
        is_candidate = (
            block.get("role") == "backmatter_heading_candidate"
            or block.get("seed_role") == "backmatter_heading_candidate"
        )
        if not is_candidate:
            continue
        if block.get("role") == "backmatter_heading":
            continue
        next_body = _next_nonempty_block_same_page(blocks, idx)
        if next_body and next_body.get("role") in {"body_paragraph", "backmatter_body"}:
            if _looks_like_tail_body(next_body):
                old_role = block.get("role")
                block["role"] = "backmatter_heading"
                block.setdefault("role_confidence", 0.6)
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="backmatter_candidate_promotion",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="backmatter heading candidate promoted: followed by tail-like body on same page",
                    )
                # Convert follower body paragraphs to backmatter_body
                for j in range(idx + 1, len(blocks)):
                    if blocks[j].get("page") != block.get("page"):
                        break
                    if blocks[j].get("role") == "body_paragraph":
                        old_follower_role = blocks[j].get("role")
                        blocks[j]["role"] = "backmatter_body"
                        blocks[j].setdefault("role_confidence", 0.6)
                        if old_follower_role != blocks[j]["role"]:
                            record_decision(
                                blocks[j],
                                stage="backmatter_candidate_promotion",
                                old_role=old_follower_role,
                                new_role=blocks[j]["role"],
                                reason="follower body converted to backmatter_body under confirmed heading",
                            )
                break  # only promote one candidate per pass

    # Re-run tail non-ref exclusion after role resolution so blocks that
    # were assigned tail_nonref_hold_zone get their role converted.
    _exclude_tail_nonref_from_body_flow(blocks)

    # Recompute page layouts after role resolution — initial layout may have
    # underestimated column count because raw OCR labels (text, paragraph_title)
    # are not layout-eligible, whereas resolved roles (reference_item, body_paragraph) are.
    page_layouts = _build_page_layout_profiles(blocks)

    tail_spread = _reconcile_tail_spread(blocks, page_layouts)
    if tail_spread is not None:
        backmatter_form = _classify_backmatter_form(tail_spread, blocks)
        _label_backmatter_regime(tail_spread, backmatter_form, blocks)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
    else:
        backmatter_form = "flat"

    # Backmatter zone normalization: in post_reference_backmatter_zone,
    # headings become backmatter_heading, everything else becomes backmatter_body.
    # Blocks in this zone are past the verified reference range; any reference_item
    # here is a misclassification that the structural gate would hold to
    # unknown_structural anyway, so normalize early to let the gate accept them.
    _HEADING_ROLES = {"section_heading", "subsection_heading", "sub_subsection_heading"}
    for block in blocks:
        if block.get("zone") != "post_reference_backmatter_zone":
            continue
        role = block.get("role")
        if role in _HEADING_ROLES:
            old_role = role
            block["role"] = "backmatter_heading"
            record_decision(
                block,
                stage="backmatter_heading_promotion",
                old_role=old_role,
                new_role="backmatter_heading",
                reason="heading in post_reference_backmatter_zone promoted to backmatter_heading",
            )
        elif role != "backmatter_heading":
            old_role = block.get("role")
            if old_role != "backmatter_body":
                block["role"] = "backmatter_body"
                block.setdefault("render_default", True)
                record_decision(
                    block,
                    stage="backmatter_body_normalization",
                    old_role=old_role,
                    new_role="backmatter_body",
                    reason="non-heading block in post_reference_backmatter_zone normalized to backmatter_body",
                )

    doc_structure = DocumentStructure(
        body_end_page=tail_spread.body_end_page if tail_spread else None,
        backmatter_start=PagePosition(page=tail_spread.backmatter_start, y=0.0)
        if tail_spread and tail_spread.backmatter_start is not None
        else None,
        references_start=PagePosition(page=tail_spread.references_start, y=0.0)
        if tail_spread and tail_spread.references_start is not None
        else None,
        spread_start=tail_spread.spread_start if tail_spread else None,
        spread_end=tail_spread.spread_end if tail_spread else None,
        backmatter_form=backmatter_form,
        body_family_anchor=body_family_anchor,
        reference_family_anchor=reference_family_anchor,
        page_layouts=page_layouts,
        region_bus=region_bus,
    )
    if source_frontmatter_anchors:
        doc_structure.source_frontmatter_anchors = source_frontmatter_anchors

    header_band, footer_band = _estimate_noise_bands(blocks)

    reading_segments = _build_tail_reading_order(blocks, page_layouts)
    doc_structure.tail_reading_order = (
        [dataclasses.asdict(seg) for seg in reading_segments] if reading_segments else None
    )

    ref_zones = _detect_reference_zones(blocks, page_layouts)
    doc_structure.reference_zones = [dataclasses.asdict(z) for z in ref_zones] if ref_zones else None

    blocks = _promote_tail_body_candidates(blocks, doc_structure, header_band=header_band, footer_band=footer_band)
    blocks = _assign_tail_spread_ownership(blocks, doc_structure)

    # Compute span coverage for degraded mode detection
    doc_structure.span_coverage = _compute_span_coverage(blocks)

    # Build region prepass: classify frontmatter/structured_insert/body by geometry
    region_prepass = _build_region_prepass(blocks)
    doc_structure.region_prepass = region_prepass  # type: ignore[attr-defined]

    # Mark prepass-identified structured insert blocks as candidates before spine
    for idx in region_prepass.structured_insert_indices:
        if idx < len(blocks):
            role = blocks[idx].get("role", "")
            if role in {"body_paragraph", "section_heading", "subsection_heading", "sub_subsection_heading"}:
                old_role = blocks[idx].get("role")
                blocks[idx]["role"] = "structured_insert_candidate"
                if old_role != blocks[idx]["role"]:
                    record_decision(
                        blocks[idx],
                        stage="structured_insert_promotion",
                        old_role=old_role,
                        new_role=blocks[idx]["role"],
                        reason="region prepass identified as structured insert candidate",
                    )

    # Also mark blocks whose insert_score indicates a candidate (needed for
    # cluster detection to pick them up even when their region is "body").
    for idx in range(len(blocks)):
        score_data = blocks[idx].get("insert_score", {})
        if score_data.get("decision") == "structured_insert_candidate":
            role = blocks[idx].get("role", "")
            if role in {"body_paragraph", "section_heading", "subsection_heading", "sub_subsection_heading"}:
                old_role = blocks[idx].get("role")
                blocks[idx]["role"] = "structured_insert_candidate"
                if old_role != blocks[idx]["role"]:
                    record_decision(
                        blocks[idx],
                        stage="structured_insert_promotion",
                        old_role=old_role,
                        new_role=blocks[idx]["role"],
                        reason="scorer identified as structured insert candidate",
                    )

    # Detect structured insert clusters BEFORE body spine and non-body gates
    structured_insert_indices = _detect_structured_insert_clusters(blocks)
    for idx in structured_insert_indices:
        if idx < len(blocks):
            old_role = blocks[idx].get("role")
            blocks[idx]["role"] = "structured_insert"
            if old_role != blocks[idx]["role"]:
                record_decision(
                    blocks[idx],
                    stage="structured_insert_promotion",
                    old_role=old_role,
                    new_role=blocks[idx]["role"],
                    reason="cluster detection promoted to structured insert",
                )

    # Fallback: promote single structured_insert_candidate blocks that the
    # region prepass independently identified as structured inserts, even
    # when clustering could not form (only one candidate on the page).
    for idx in region_prepass.structured_insert_indices:
        if idx < len(blocks) and blocks[idx].get("role") == "structured_insert_candidate":
            old_role = blocks[idx].get("role")
            blocks[idx]["role"] = "structured_insert"
            if old_role != blocks[idx]["role"]:
                record_decision(
                    blocks[idx],
                    stage="structured_insert_promotion",
                    old_role=old_role,
                    new_role=blocks[idx]["role"],
                    reason="single candidate promoted to structured insert (fallback)",
                )

    structured_insert_indices = {i for i, b in enumerate(blocks) if b.get("role") == "structured_insert"}
    structured_insert_indices = _expand_structured_insert_cluster_with_mixed_sidebar_blocks(
        blocks, structured_insert_indices
    )
    for idx in structured_insert_indices:
        if idx < len(blocks):
            old_role = blocks[idx].get("role")
            blocks[idx]["role"] = "structured_insert"
            if old_role != blocks[idx]["role"]:
                record_decision(
                    blocks[idx],
                    stage="structured_insert_promotion",
                    old_role=old_role,
                    new_role=blocks[idx]["role"],
                    reason="expanded cluster promoted to structured insert",
                )

    # Detect body spine from region-approved body blocks only
    body_spine = _detect_body_spine(blocks, doc_structure, region_prepass=region_prepass)

    # Detect non-body insert clusters on early pages (relative to body length)
    pw = max((b.get("page_width", 0) or 0) for b in blocks) or 1200
    insert_indices = _detect_non_body_insert_clusters(
        blocks,
        body_spine,
        page_width=pw,
        body_end_page=tail_spread.body_end_page if tail_spread else None,
    )
    for idx in insert_indices:
        if idx < len(blocks):
            b = blocks[idx]
            if b.get("page") == 1 and _is_page1_title(b.get("text", "")):
                old_role = b.get("role")
                b["role"] = "body_paragraph"
                if old_role != b["role"]:
                    record_decision(
                        b,
                        stage="non_body_insert_marking",
                        old_role=old_role,
                        new_role=b["role"],
                        reason="page 1 title-like block, not a non-body insert",
                    )
                continue
            old_role = b.get("role")
            b["role"] = "non_body_insert"
            if old_role != b["role"]:
                record_decision(
                    b,
                    stage="non_body_insert_marking",
                    old_role=old_role,
                    new_role=b["role"],
                    reason="marked as non-body insert cluster member",
                )
            b["_non_body_insert"] = True

    _mark_non_body_media(blocks)
    _resolve_ambiguous_candidates(blocks, doc_structure, page_layouts)

    # Run layout audit after all resolution is done
    layout_audit = _run_layout_audit(blocks, body_spine=body_spine, page_layouts=page_layouts)
    doc_structure.layout_audit = layout_audit

    # Compute tail boundary confidence score
    from paperforge.worker.ocr_scores import score_tail_boundary

    doc_structure.tail_boundary_score = score_tail_boundary(
        forward_body_end=doc_structure.body_end_page,
        backward_backmatter_start=doc_structure.backmatter_start.page if doc_structure.backmatter_start else None,
        references_start={"page": doc_structure.references_start.page} if doc_structure.references_start else None,
    )

    # Rebuild tail reading order after role normalization and block reassignment.
    # Without this, reading segment block_indices reference stale positions
    # from before _promote_tail_body_candidates reassigned the blocks list.
    final_segments = _build_tail_reading_order(blocks, page_layouts)
    final_segments = _enforce_body_before_references_in_segments(
        final_segments, blocks, doc_structure.spread_start, doc_structure.spread_end
    )
    doc_structure.tail_reading_order = [dataclasses.asdict(seg) for seg in final_segments] if final_segments else None
    # When the fallback reference-only tail spread was detected (no backmatter),
    # clear tail reading order since it cannot help multi-column reordering.
    if tail_spread is not None and tail_spread.backmatter_start == tail_spread.references_start:
        doc_structure.tail_reading_order = None

    # Build abstract_span from document-level zone artifacts
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    fm_main_zone = (
        region_bus.get("frontmatter_main_zone")
        if isinstance(region_bus, dict)
        else getattr(region_bus, "frontmatter_main_zone", None)
    )
    fm_side_zone = (
        region_bus.get("frontmatter_side_zone")
        if isinstance(region_bus, dict)
        else getattr(region_bus, "frontmatter_side_zone", None)
    )
    fm_main_ids = {
        zid
        for zid in (fm_main_zone.get("block_ids", []) if isinstance(fm_main_zone, dict) else [])
    }
    fm_support_ids = {
        zid
        for zid in (fm_side_zone.get("block_ids", []) if isinstance(fm_side_zone, dict) else [])
    }
    duplicate_block_ids = _duplicate_block_ids_from_blocks(blocks)

    # Find body_start_block_id from the first body-zone block
    body_start_block_id = None
    for block in blocks:
        if block.get("role") in {
            "section_heading",
            "subsection_heading",
        } and block.get("zone") != "frontmatter_main_zone":
            body_start_block_id = _artifact_block_id(block, duplicate_block_ids)
            break
    if body_start_block_id is None:
        for block in blocks:
            if block.get("zone") == "body_zone" and block.get("role") in {
            "body_paragraph",
            "section_heading",
            "subsection_heading",
            }:
                body_start_block_id = _artifact_block_id(block, duplicate_block_ids)
                break

    abstract_span = build_document_abstract_span(
        blocks,
        {
            "body_start_block_id": body_start_block_id,
            "frontmatter_main_zone_ids": fm_main_ids,
            "frontmatter_support_zone_ids": fm_support_ids,
            "publisher_sidebar_zone_ids": set(),
            "correspondence_zone_ids": set(),
            "affiliation_zone_ids": set(),
        },
    )
    doc_structure.abstract_span = abstract_span

    # When abstract span ends at a keywords block, tag it as structured_insert.
    # The abstract span builder stops before the keywords block but doesn't assign a role.
    if abstract_span.get("stop_reason") == "keywords" and abstract_span.get("body_block_ids"):
        body_ids = abstract_span["body_block_ids"]
        # Find the block immediately after the last abstract body block
        last_body_idx = None
        for i, b in enumerate(blocks):
            if _artifact_block_id(b, duplicate_block_ids) in body_ids:
                last_body_idx = i
        if last_body_idx is not None and last_body_idx + 1 < len(blocks):
            kw_block = blocks[last_body_idx + 1]
            kw_text = str(kw_block.get("text") or "").strip().lower()
            if kw_text.startswith(("keywords", "key words")) and kw_block.get("role") in {"body_paragraph", "unknown_structural", "frontmatter_noise"}:
                old_role = kw_block.get("role")
                kw_block["role"] = "structured_insert"
                record_decision(
                    kw_block,
                    stage="abstract_span_keywords_boundary",
                    old_role=old_role,
                    new_role="structured_insert",
                    reason="block after abstract body matches keywords stop_reason",
                )

    # Build verified reference_zone from document-level artifacts
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    ref_zone = (
        region_bus.get("reference_zone")
        if isinstance(region_bus, dict)
        else getattr(region_bus, "reference_zone", None)
    )
    ref_zone_ids = {
        zid for zid in (ref_zone.get("block_ids", []) if isinstance(ref_zone, dict) else [])
    }
    tail_spread_dict = None
    if tail_spread is not None:
        tail_spread_dict = {
            "reference_end_before_block_id": getattr(tail_spread, "backmatter_start", None),
        }

    reference_zone = build_verified_reference_zone_from_artifacts(
        blocks,
        {
            "reference_family_anchor": reference_family_anchor,
            "region_bus": {"reference_zone_ids": ref_zone_ids},
            "tail_spread": tail_spread_dict or {},
        },
    )
    doc_structure.reference_zone = reference_zone

    # Run verified role gate
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED, RoleGateContext, resolve_verified_role

    gate_context = RoleGateContext(
        source_frontmatter_anchor_ids=_build_source_frontmatter_anchor_ids(doc_structure, blocks),
        abstract_span=abstract_span,
        reference_zone=reference_zone,
        accepted_heading_block_ids=_build_accepted_heading_block_ids(blocks, doc_structure),
        accepted_caption_block_ids=_build_accepted_caption_block_ids({}, {}, blocks),
        accepted_table_block_ids=_build_accepted_table_block_ids({}, blocks),
    )

    # Convert unresolved object seeds to candidates when artifacts are not available
    if not gate_context.accepted_caption_block_ids:
        for block in blocks:
            if block.get("seed_role") == "figure_caption":
                block["role"] = "figure_caption_candidate"
    if not gate_context.accepted_table_block_ids:
        for block in blocks:
            if block.get("seed_role") == "table_caption":
                block["role"] = "table_caption_candidate"
            if block.get("seed_role") == "table_html":
                block["role"] = "table_html_candidate"

    decisions = []
    for block in blocks:
        decision = resolve_verified_role(block, gate_context)
        decisions.append(decision)
        block.update(decision.as_block_fields())

    # Compute role gate health summary
    from paperforge.worker.ocr_structural_gate import compute_role_gate_health

    doc_structure.role_gate_summary = compute_role_gate_health(decisions)

    # Handle offenders: degrade without raising
    offenders = set()
    for block in blocks:
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT":
            offenders.add(block.get("block_id"))
    for block in blocks:
        if block.get("block_id") in offenders:
            block["role_candidate"] = block.get("role") or block.get("seed_role")
            if block.get("role") == "body_paragraph":
                block["role_source"] = "structural_gate_fallback"
                block["render_default"] = True
                continue
            if block.get("role") in {
                "frontmatter_noise",
                "frontmatter_support",
                "structured_insert",
                "non_body_insert",
            }:
                block["role_source"] = "structural_gate_fallback"
                continue
            block["role"] = "unknown_structural"
            block["render_default"] = False
    doc_structure.role_gate_summary["rendered_unverified_structural_role_count"] = 0
    doc_structure.role_gate_summary["downgraded_unverified_structural_role_count"] = len(offenders)

    _demote_early_frontmatter_body_leaks(blocks)
    _restore_numbered_body_from_tail_hold(blocks)

    return doc_structure, blocks
