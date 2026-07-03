from __future__ import annotations

import contextlib
import itertools
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json
from paperforge.worker.ocr_roles import _PANEL_LABEL_PATTERN, _looks_like_figure_description_opening
from paperforge.worker.ocr_scores import score_figure_caption, score_figure_match

_FIGURE_NUMBER_PATTERN = re.compile(
    r"(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?|图|圖|ͼ)\s*"
    r"(?:S\.?\s*)?(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)

_FRONTMATTER_VISUAL_VETO = (
    "graphical abstract",
    "table of contents",
    "highlights",
    "available with this article",
    "supplementary data",
    "supporting information",
    "video abstract",
    "visual abstract",
)


def _has_frontmatter_visual_veto(text: str) -> bool:
    lower = " ".join(text.lower().split())
    if re.search(r"\btoc\b", lower):
        return True
    return any(
        phrase in lower
        for phrase in _FRONTMATTER_VISUAL_VETO
    )


_BODY_MENTION_VERBS = (
    "shows",
    "illustrates",
    "depicts",
    "presents",
    "summarizes",
    "demonstrates",
    "displays",
    "reveals",
    "indicates",
    "highlights",
    "compares",
    "outlines",
    "reports",
    "lists",
)

_BODY_MENTION_PATTERN = re.compile(
    r"\b(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+"
    r"\d+\.?\s+(?:" + "|".join(_BODY_MENTION_VERBS) + r")\b",
    flags=re.IGNORECASE,
)

_INLINE_FIGURE_MENTION_VERBS = (
    "shows",
    "show",
    "shown",
    "illustrates",
    "illustrate",
    "depicts",
    "demonstrates",
    "demonstrate",
    "presents",
    "present",
    "indicates",
    "indicate",
    "reveals",
    "reveal",
    "suggests",
    "suggest",
    "summarizes",
    "summarize",
    "compares",
    "compare",
)


def _looks_like_inline_figure_mention(text: str, block: dict | None = None) -> bool:
    """
    Ponytail: position and style are the reliable signals for distinguishing
    figure captions from body mentions.  Text-content heuristics (verb lists,
    word-count thresholds) introduce errors for long captions and non-English
    prose.  Default to False when the block is already classified as a figure
    caption in a display zone.
    """
    if block is not None:
        role = str(block.get("role") or "")
        zone = str(block.get("zone") or "")
        style = str(block.get("style_family") or "")
        if role == "figure_caption":
            return False
        if role == "figure_caption_candidate" and zone != "body_zone":
            return False
        if zone == "display_zone" and style == "legend_like":
            return False
    return False


def _extract_figure_number(text: str) -> int | None:
    m = _FIGURE_NUMBER_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


def _extract_figure_namespace(text: str) -> str:
    lower = text.lower()
    if "supplementary" in lower:
        return "supplementary"
    if "extended data" in lower:
        return "extended_data"
    return "main"


_FIGURE_MARKER_PATTERN = re.compile(
    r"(?P<prefix>Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?|"
    r"Figure|Fig\.?)\s*"
    r"(?P<s_prefix>S\.?\s*)?"
    r"(?P<number>\d+(?:\.\d+)?)",
    re.I,
)

_FIGURE_DESCRIPTION_OPENING = re.compile(
    r"^(?:This figure|The figure|This Fig\.?|The Fig\.?|Figure\s+\d+|Fig\.?\s+\d+)\b",
    flags=re.IGNORECASE,
)


def _extract_figure_marker(text: str) -> dict:
    m = _FIGURE_MARKER_PATTERN.search(text)
    if not m:
        return {
            "namespace": "main",
            "number": None,
            "raw_prefix": "",
            "has_s_prefix": False,
            "marker_text": "",
        }
    lower = text.lower()
    has_s = bool(m.group("s_prefix"))
    if has_s or "supplementary" in lower or "supporting" in lower or "additional file" in lower or "appendix" in lower:
        namespace = "supplementary"
    elif "extended data" in lower or "extended figure" in lower:
        namespace = "extended_data"
    else:
        namespace = "main"
    number_raw = m.group("number")
    try:
        number = int(float(number_raw))
    except ValueError:
        number = None
    return {
        "namespace": namespace,
        "number": number,
        "raw_prefix": m.group("prefix"),
        "has_s_prefix": has_s,
        "marker_text": m.group(0),
    }


def _validate_page_local_caption_grammar(
    hypotheses: list[dict],
    legends: list[dict],
) -> list[dict]:
    """Annotate local pairing hypotheses with grammar consistency status.

    If a page has multiple captions with different prefix styles
    (e.g. "Figure 1." vs "Fig 1."), those hypotheses are marked
    'conflict'. Uniform styles get 'accepted'. Annotation-only;
    does not change matching behavior.
    """
    import re

    _GRAMMAR_PREFIX_PATTERN = re.compile(r"^(?:Fig(?:ure)?|FIG(?:URE)?)\s*[\.:]?\s*(\d+)", re.IGNORECASE)

    def _grammar_prefix(text: str) -> str:
        m = _GRAMMAR_PREFIX_PATTERN.search(text)
        if not m:
            return ""
        prefix_start = text[:m.start(1)]
        return prefix_start.strip().lower().replace(".", "").replace(":", "").replace(" ", "")

    legend_by_id: dict[str, dict] = {}
    for leg in legends:
        legend_by_id[str(leg.get("block_id", ""))] = leg

    page_grammar: dict[int, set[str]] = {}
    for h in hypotheses:
        lid = str(h.get("legend_block_id", ""))
        leg = legend_by_id.get(lid)
        if leg is None:
            continue
        page = int(leg.get("page", 0) or 0)
        prefix = _grammar_prefix(str(leg.get("text", "") or ""))
        if prefix:
            page_grammar.setdefault(page, set()).add(prefix)

    for h in hypotheses:
        lid = str(h.get("legend_block_id", ""))
        leg = legend_by_id.get(lid)
        if leg is None:
            h["grammar_status"] = "deferred"
            h["grammar_reason"] = "legend not found"
            h["grammar_evidence"] = []
            continue

        page = int(leg.get("page", 0) or 0)
        prefixes = page_grammar.get(page, set())

        if not prefixes:
            h["grammar_status"] = "deferred"
            h["grammar_reason"] = "no grammar prefix detected"
            h["grammar_evidence"] = []
        elif len(prefixes) == 1:
            h["grammar_status"] = "accepted"
            h["grammar_reason"] = f"uniform page-local grammar ({list(prefixes)[0]})"
            h["grammar_evidence"] = [f"grammar_prefix:{list(prefixes)[0]}"]
        else:
            h["grammar_status"] = "conflict"
            h["grammar_reason"] = f"mixed page-local grammar ({', '.join(sorted(prefixes))})"
            h["grammar_evidence"] = [f"grammar_prefix:{p}" for p in sorted(prefixes)]

    return hypotheses


def _format_figure_id(namespace: str, number: int) -> str:
    if namespace == "supplementary":
        return f"figure_s{number:03d}"
    if namespace == "extended_data":
        return f"figure_ed{number:03d}"
    return f"figure_{number:03d}"


def _page_assets_strict_ok(page_legends: list[dict], page_assets_count: int, full_captions_on_page: set[str]) -> bool:
    if len(page_legends) == 1:
        return True
    return not full_captions_on_page


TABLE_LIKE_RAW = frozenset({"table", "table_image"})


def _column_band_id(bbox: list[float], page_width: float) -> int | None:
    """Classify a bbox into left (0), right (1), or center (None) column band."""
    if not bbox or len(bbox) < 4 or page_width <= 0:
        return None
    center_x = (bbox[0] + bbox[2]) / 2.0
    if center_x < page_width * 0.45:
        return 0
    if center_x > page_width * 0.55:
        return 1
    return None


def _is_safe_page_assets_group(
    group: dict,
    legend: dict,
    page_blocks: list[dict],
    page_numbered_legend_count: int,
    page_width: float,
    page_height: float,
) -> tuple[bool, list[str]]:
    evidence: list[str] = []

    # 1. Legend must have a formal figure number
    if _extract_figure_number(str(legend.get("text") or "")) is None:
        return False, ["legend_not_numbered"]

    # 2. Single deduped numbered legend on page
    if page_numbered_legend_count != 1:
        return False, ["multiple_numbered_legends"]

    # 3. Page context
    if not page_blocks or page_height <= 0:
        return False, ["missing_page_context"]

    media_blocks = group.get("media_blocks", [])
    cluster_bbox = group.get("cluster_bbox")
    if not cluster_bbox or len(cluster_bbox) < 4:
        return False, ["invalid_cluster_bbox"]

    # 4. Require at least 3 media blocks
    if len(media_blocks) < 3:
        return False, ["insufficient_media_count"]

    # 5. Page coverage
    cw = cluster_bbox[2] - cluster_bbox[0]
    ch = cluster_bbox[3] - cluster_bbox[1]
    page_area = max(1.0, page_width * page_height)
    cluster_area = max(1.0, cw * ch)
    coverage_ratio = cluster_area / page_area
    asset_area_sum = 0.0
    for mb in media_blocks:
        bb = mb.get("bbox") or [0, 0, 0, 0]
        if len(bb) >= 4:
            asset_area_sum += max(0.0, (bb[2] - bb[0]) * (bb[3] - bb[1]))
    fill_ratio = asset_area_sum / cluster_area if cluster_area > 0 else 0.0
    if coverage_ratio > 0.75:
        return False, ["excessive_page_coverage"]
    if coverage_ratio > 0.65 and fill_ratio < 0.25:
        return False, ["excessive_coverage_low_fill"]

    # 6. Compact geometry: media_blocks must form ONE semantic cluster
    semantic_clusters = _cluster_semantic_page_assets(
        media_blocks, page_blocks, page_width, page_height,
    )
    group_block_ids = {str(b.get("block_id")) for b in media_blocks if b.get("block_id")}
    cluster_member_ids = [
        {str(b.get("block_id")) for b in cluster if b.get("block_id")}
        for cluster in semantic_clusters
    ]
    if group_block_ids not in cluster_member_ids:
        return False, ["media_not_compact"]

    # 7. No text separator between any paired media blocks
    for a, b in itertools.combinations(media_blocks, 2):
        if _has_text_separator(a, b, page_blocks):
            return False, ["text_separator_between_assets"]

    # 8. No table-like assets
    for mb in media_blocks:
        raw_label = str(mb.get("raw_label") or "").lower()
        text = str(mb.get("text") or "").lower()
        if raw_label in TABLE_LIKE_RAW and "<img" not in text:
            return False, ["group_contains_table_like_asset"]
        hint = str(mb.get("asset_family_hint") or "")
        if hint == "table_like":
            conf = float(mb.get("asset_family_confidence", 0) or 0)
            if conf >= 0.70:
                return False, ["group_contains_table_like_asset"]

    # 9. Cross-column rejection gate
    cw = cluster_bbox[2] - cluster_bbox[0]
    full_width_group = cw >= page_width * 0.65 and page_numbered_legend_count == 1
    if not full_width_group:
        bands = {
            _column_band_id(mb.get("bbox") or [0, 0, 0, 0], page_width)
            for mb in media_blocks
        }
        bands.discard(None)
        if len(bands) > 1:
            return False, ["cross_column_media"]

    return True, evidence


def _compute_overlap_score(a_bbox: list[float], b_bbox: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a_bbox
    bx1, by1, bx2, by2 = b_bbox

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    intersection = iw * ih
    if intersection == 0:
        return 0.0

    a_area = (ax2 - ax1) * (ay2 - ay1)
    b_area = (bx2 - bx1) * (by2 - by1)
    union = a_area + b_area - intersection
    if union == 0:
        return 0.0
    return intersection / union


def _centroid_y(bbox: list[float]) -> float:
    return (bbox[1] + bbox[3]) / 2


def _looks_like_figure_narrative_prose(text: str) -> bool:
    if not text:
        return False
    after_fig = _FIGURE_NUMBER_PATTERN.sub("", text, count=1).strip().lstrip(". ")
    if after_fig.count(". ") >= 2:
        return True
    prose_markers = ["we ", "our ", "this study ", "here we ", "in this "]
    if any(m in text.lower() for m in prose_markers):
        return True
    if re.search(r"\$?\^\{[^}]+\}\$?", text):
        return True
    return False


def _is_body_mention(block: dict) -> bool:
    zone = str(block.get("zone") or "")
    style_family = str(block.get("style_family") or "")
    raw_role = block.get("raw_role", block.get("role", ""))
    if zone == "display_zone" and style_family == "legend_like":
        return False
    if raw_role == "body_paragraph":
        return True
    if raw_role == "figure_caption_candidate":
        text = block.get("text", "")
        if text and _FIGURE_NUMBER_PATTERN.search(text):
            if _looks_like_inline_figure_mention(text, block):
                return True
            return False
        if text and _looks_like_figure_narrative_prose(text):
            return True
    if block.get("block_label", "") == "text":
        text = block.get("text", "")
        return bool(_BODY_MENTION_PATTERN.search(text))
    return False


_PANEL_SUBCAPTION_PATTERN = re.compile(r"^\s*[a-z][\.\)]\s")
_TRUNCATED_LEGEND_ONLY_PATTERN = re.compile(
    r"^(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+(?:S)?\d+(?:\.0+)?\.?$",
    flags=re.IGNORECASE,
)


def _is_validation_first_legend_candidate(block: dict) -> bool:
    role = str(block.get("role") or "")
    marker_signature = block.get("marker_signature") or {}
    marker_type = str(marker_signature.get("type") or "none")
    zone = str(block.get("zone") or "")
    style_family = str(block.get("style_family") or "")
    seed_role = str(block.get("seed_role") or "")
    raw_label = str(block.get("raw_label") or "")

    if role in {"figure_caption", "figure_caption_candidate"}:
        return False
    if marker_type != "figure_number":
        return False

    return (zone in {"body_zone", "display_zone", "tail_nonref_hold_zone"} and style_family == "legend_like") or (
        role not in {"figure_caption", "figure_caption_candidate"}
        and zone == "display_zone"
        and raw_label == "figure_title"
        and seed_role == "figure_caption"
    )


def _has_anchor_supported_legend_context(block: dict) -> bool:
    marker_signature = block.get("marker_signature") or {}
    marker_type = str(marker_signature.get("type") or "none")
    style_family = str(block.get("style_family") or "")
    style_family_authority = str(block.get("style_family_authority") or "")
    zone = str(block.get("zone") or "")
    seed_role = str(block.get("seed_role") or "")
    raw_label = str(block.get("raw_label") or "")
    return (
        marker_type == "figure_number"
        and style_family == "legend_like"
        and style_family_authority in {"figure_marker", "figure_family_anchor"}
    ) or (
        marker_type == "figure_number"
        and zone == "display_zone"
        and raw_label == "figure_title"
        and seed_role == "figure_caption"
    )


def _is_insufficient_legend_evidence(block: dict) -> bool:
    text = str(block.get("text") or "").strip()
    marker_signature = block.get("marker_signature") or {}
    marker_type = str(marker_signature.get("type") or "none")
    style_family = str(block.get("style_family") or "")

    if marker_type != "figure_number":
        return False
    if style_family != "legend_like":
        return False
    if not _TRUNCATED_LEGEND_ONLY_PATTERN.fullmatch(text):
        return False

    return True


def _has_strong_explicit_caption_text(block: dict) -> bool:
    text = str(block.get("text") or "").strip()
    role = str(block.get("role") or "")
    if role not in {"figure_caption", "figure_caption_candidate"} and not _is_validation_first_legend_candidate(block):
        return False
    if _is_insufficient_legend_evidence(block):
        return False
    words = [w for w in re.split(r"\s+", text) if w]
    return len(words) >= 5 and len(text) >= 30


_PREVIOUS_PAGE_LOCATOR_PATTERN = re.compile(
    r"(?:see|refer)\s+(?:to\s+)?(?:the\s+)?(?:legend|figure|caption)\s+(?:on\s+)?(?:the\s+)?(?:preceding|previous|facing)\s+page",
    re.IGNORECASE,
)


def _is_previous_page_legend_locator(block: dict) -> bool:
    """Detect locator captions like 'Fig. 10 (See legend on previous page)'.

    These are short captions that point to a full legend on the preceding page.
    They should not enter ordinary legend matching; instead they bridge the
    previous page's full legend to the current page's visual group.
    """
    role = str(block.get("role") or "")
    if role not in {"figure_caption", "figure_caption_candidate"}:
        return False
    text = str(block.get("text") or "").strip()
    if not text or _extract_figure_number(text) is None:
        return False
    return bool(_PREVIOUS_PAGE_LOCATOR_PATTERN.search(text))


def _is_tight_asset_cluster(assets: list[dict], below_top: float) -> bool:
    """Check if assets form a single tight visual cluster below a threshold."""
    if len(assets) < 1:
        return False
    bboxes = [a.get("bbox") or a.get("block_bbox") or [0, 0, 0, 0] for a in assets]
    valid = [b for b in bboxes if len(b) >= 4 and b[2] > b[0] and b[3] > b[1]]
    if not valid:
        return False
    union_top = min(b[1] for b in valid)
    union_bot = max(b[3] for b in valid)
    union_left = min(b[0] for b in valid)
    union_right = max(b[2] for b in valid)
    spread_x = union_right - union_left
    spread_y = union_bot - union_top
    # Cluster is tight if vertical span < 90% of space to locator,
    # and horizontal spread is within page width limits.
    return spread_y < (below_top - union_top) * 0.9 and spread_x < 1500

def _is_formal_legend(text: str, block: dict | None = None, page_width: float = 1200) -> bool:
    if not text:
        return False

    if _FIGURE_NUMBER_PATTERN.search(text):
        return True

    if block is not None:
        bbox = block.get("bbox") or block.get("block_bbox")
        if bbox and len(bbox) >= 4:
            block_width = bbox[2] - bbox[0]
            if block_width < page_width * 0.3:
                return False

        lower = text.lower().strip()
        axis_words = {
            "days",
            "time",
            "concentration",
            "percentage",
            "volume",
            "frequency",
            "intensity",
            "ratio",
            "expression",
            "level",
            "content",
            "activity",
            "treatment",
            "group",
            "control",
            "dose",
            "response",
            "size",
            "culture",
            "medium",
            "supplemented",
            "differentiation",
            "osteogenic",
            "chondrogenic",
            "adipogenic",
            "induction",
            "stimulation",
            "exposure",
            "incubation",
            "harvest",
            "collection",
        }
        words = set(lower.rstrip(". ").split())
        stop_words = {
            "of",
            "the",
            "in",
            "and",
            "to",
            "a",
            "an",
            "by",
            "at",
            "for",
            "with",
            "on",
            "is",
            "are",
            "was",
            "were",
            "post",
            "after",
            "during",
            "before",
        }
        text_len = len(text)
        if text_len < 100 and words and words.issubset(axis_words | stop_words):
            return False

    return not (_PANEL_SUBCAPTION_PATTERN.match(text) and not _FIGURE_NUMBER_PATTERN.search(text))


def _cluster_bbox(bboxes: list[list[float]]) -> list[float]:
    if not bboxes:
        return [0, 0, 0, 0]
    x1 = min(b[0] for b in bboxes)
    y1 = min(b[1] for b in bboxes)
    x2 = max(b[2] for b in bboxes)
    y2 = max(b[3] for b in bboxes)
    return [x1, y1, x2, y2]


def _asset_gap_right(a: dict, b: dict) -> float:
    ab = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    return max(0.0, bb[0] - ab[2])


def _asset_gap_below(a: dict, b: dict) -> float:
    ab = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    return max(0.0, bb[1] - ab[3])


def _rect_intersection_area(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _has_text_separator(a: dict, b: dict, page_blocks: list[dict]) -> bool:
    ab = a.get("bbox", [0, 0, 0, 0])
    bb = b.get("bbox", [0, 0, 0, 0])
    a_page = a.get("page")

    a_y1, a_y2 = ab[1], ab[3]
    b_y1, b_y2 = bb[1], bb[3]
    a_x1, a_x2 = ab[0], ab[2]
    b_x1, b_x2 = bb[0], bb[2]

    v_overlap = max(0.0, min(a_y2, b_y2) - max(a_y1, b_y1))
    h_gap = max(0.0, b_x1 - a_x2, a_x1 - b_x2)
    h_overlap = max(0.0, min(a_x2, b_x2) - max(a_x1, b_x1))
    v_gap = max(0.0, b_y1 - a_y2, a_y1 - b_y2)

    if v_overlap > 0 and h_gap > 0:
        gap_rect = [min(a_x2, b_x2), max(a_y1, b_y1), max(a_x1, b_x1), min(a_y2, b_y2)]
    elif h_overlap > 0 and v_gap > 0:
        gap_rect = [max(a_x1, b_x1), min(a_y2, b_y2), min(a_x2, b_x2), max(a_y1, b_y1)]
    else:
        gap_rect = [min(a_x1, b_x1), min(a_y1, b_y1), max(a_x2, b_x2), max(a_y2, b_y2)]

    for block in page_blocks:
        if block.get("page") != a_page:
            continue
        role = block.get("role", "")
        if role not in (
            "body_paragraph",
            "section_heading",
            "subsection_heading",
            "sub_subsection_heading",
            "backmatter_heading",
            "backmatter_body",
            "tail_candidate_body",
            "reference_heading",
            "reference_item",
        ):
            continue
        txt = str(block.get("text", "") or "").strip()
        if not txt or len(txt) < 10:
            continue
        cb = block.get("bbox", [0, 0, 0, 0])
        block_area = max(1.0, (cb[2] - cb[0]) * (cb[3] - cb[1]))
        if _rect_intersection_area(gap_rect, cb) / block_area >= 0.3:
            return True
    return False


def _cluster_page_assets(
    page_assets: list[dict],
    all_blocks: list[dict],
    n_legends: int,
    page_width: float,
    page_height: float,
) -> list[list[dict]]:
    if not page_assets:
        return []
    if len(page_assets) == 1:
        return [list(page_assets)]

    h_threshold = max(page_width * 0.12, 40.0)
    v_threshold = max(min(page_width, page_height) * 0.08, 40.0)
    parent = list(range(len(page_assets)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[py] = px

    for i in range(len(page_assets)):
        for j in range(i + 1, len(page_assets)):
            a, b = page_assets[i], page_assets[j]
            ab = a.get("bbox", [0, 0, 0, 0])
            bb = b.get("bbox", [0, 0, 0, 0])

            h_gap = max(0.0, bb[0] - ab[2], ab[0] - bb[2])
            v_gap = max(0.0, bb[1] - ab[3], ab[1] - bb[3])

            if h_gap > h_threshold:
                if n_legends <= 1:
                    a_y1, a_y2 = ab[1], ab[3]
                    b_y1, b_y2 = bb[1], bb[3]
                    y_overlap = max(0, min(a_y2, b_y2) - max(a_y1, b_y1))
                    shorter_h = min(a_y2 - a_y1, b_y2 - b_y1)
                    if shorter_h > 0 and y_overlap / shorter_h >= 0.5:
                        if h_gap > page_width * 0.25:
                            continue
                    else:
                        continue
                else:
                    continue

            if v_gap > v_threshold:
                continue

            if _has_text_separator(a, b, all_blocks):
                continue

            union(i, j)

    clusters: dict[int, list[dict]] = {}
    for i, block in enumerate(page_assets):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(block)

    return list(clusters.values())


def _media_clusters(blocks: list[dict], page_width: float = 1200) -> list[list[dict]]:
    media = [
        b
        for b in blocks
        if not b.get("_non_body_media")
        and (
            b.get("role") == "figure_asset"
            or (
                b.get("role") == "media_asset"
                and (
                    b.get("raw_label", "") in {"image", "chart", "figure"}
                    or (b.get("raw_label", "") == "table" and "<img" in str(b.get("text") or "").lower())
                )
            )
        )
    ]
    media.sort(key=lambda b: (b.get("page", 0), b.get("bbox", [0, 0, 0, 0])[1], b.get("bbox", [0, 0, 0, 0])[0]))

    clusters: list[list[dict]] = []
    for m in media:
        page = m.get("page", 0)
        bbox = m.get("bbox", [0, 0, 0, 0])
        placed = False
        for cluster in clusters:
            c_page = cluster[0].get("page", 0)
            if c_page != page:
                continue
            c_bbox = _cluster_bbox([cb.get("bbox", [0, 0, 0, 0]) for cb in cluster])
            mx1, my1, mx2, my2 = bbox
            cx1, cy1, cx2, cy2 = c_bbox
            h_overlap = mx1 < cx2 and cx1 < mx2
            v_overlap = my1 < cy2 and cy1 < my2
            h_gap = max(cx1 - mx2, mx1 - cx2, 0)
            v_gap = max(cy1 - my2, my1 - cy2, 0)
            small_h = min(my2 - my1, cy2 - cy1)
            if h_overlap and v_gap < small_h * 0.3:
                cluster.append(m)
                placed = True
                break
            if v_overlap and h_gap < 50:
                cluster.append(m)
                placed = True
                break
        if not placed:
            clusters.append([m])
    return clusters


def _filter_figure_assets(assets: list[dict]) -> list[dict]:
    result = []
    for b in assets:
        if b.get("_non_body_media"):
            continue
        role = b.get("role", "")
        if role == "figure_asset":
            result.append(b)
        elif role == "media_asset":
            rl = str(b.get("raw_label", "") or "")
            if (
                rl in {"image", "chart", "figure"}
                or not rl.strip()
                or rl == "table"
                and "<img" in str(b.get("text", "") or "").lower()
            ):
                result.append(b)
    return result


def _bbox_width(bbox: list[float]) -> float:
    return float(bbox[2] - bbox[0])


def _bbox_height(bbox: list[float]) -> float:
    return float(bbox[3] - bbox[1])


def _bbox_center_y(bbox: list[float]) -> float:
    return float(bbox[1] + bbox[3]) / 2.0


def _candidate_group_entry(
    group_id: str, page: int, media_blocks: list[dict], group_type: str, evidence: list[str]
) -> dict:
    return {
        "group_id": group_id,
        "page": page,
        "group_type": group_type,
        "asset_block_ids": [b.get("block_id") for b in media_blocks if b.get("block_id") is not None],
        "media_blocks": media_blocks,
        "cluster_bbox": _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in media_blocks]),
        "group_evidence": evidence,
    }


def _semantic_group_topology(groups: list[dict]) -> set[frozenset[str]]:
    return {frozenset(str(bid) for bid in g.get("asset_block_ids", [])) for g in groups}


def _estimate_page_height(page_blocks: list[dict]) -> float:
    explicit = [float(b["page_height"]) for b in page_blocks if b.get("page_height")]
    if explicit:
        return max(explicit)
    bottoms = [float((b.get("bbox") or [0, 0, 0, 0])[3]) for b in page_blocks if len(b.get("bbox") or []) >= 4]
    return max(bottoms, default=1600.0)


def _cluster_semantic_page_assets(
    page_assets: list[dict],
    page_blocks: list[dict],
    page_width: float,
    page_height: float,
) -> list[list[dict]]:
    if not page_assets:
        return []
    if len(page_assets) == 1:
        return [list(page_assets)]

    # Semantic grouping stays stricter than the legacy caption-aware path so
    # ordinary side-by-side same-page figures do not collapse into one group.
    h_threshold = max(page_width * 0.03, 40.0)
    v_threshold = max(min(page_width, page_height) * 0.08, 40.0)
    parent = list(range(len(page_assets)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[py] = px

    for i in range(len(page_assets)):
        for j in range(i + 1, len(page_assets)):
            a, b = page_assets[i], page_assets[j]
            ab = a.get("bbox", [0, 0, 0, 0])
            bb = b.get("bbox", [0, 0, 0, 0])

            h_gap = max(0.0, bb[0] - ab[2], ab[0] - bb[2])
            v_gap = max(0.0, bb[1] - ab[3], ab[1] - bb[3])

            if h_gap > h_threshold:
                continue
            if v_gap > v_threshold:
                continue
            if _has_text_separator(a, b, page_blocks):
                continue

            union(i, j)

    clusters: dict[int, list[dict]] = {}
    for i, block in enumerate(page_assets):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(block)

    return list(clusters.values())


def _build_semantic_figure_groups_from_assets(
    assets: list[dict],
    all_blocks: list[dict],
    *,
    page_width: float = 1200,
) -> list[dict]:
    # semantic groups are caption-independent; caption/text may only act as neutral separators
    # and caption count may not change topology.
    media = _filter_figure_assets(assets)
    groups: list[dict] = []
    next_id = 1

    by_page: dict[int, list[dict]] = {}
    for block in media:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_media in by_page.items():
        page_blocks = [b for b in all_blocks if int(b.get("page", 0) or 0) == page]
        page_height = _estimate_page_height(page_blocks)
        clusters = _cluster_semantic_page_assets(page_media, page_blocks, page_width, page_height)
        page_groups: list[dict] = []
        for cluster in clusters:
            gt = "distance_cluster" if len(cluster) >= 2 else "single_asset"
            entry = _candidate_group_entry(
                f"group_{next_id:04d}",
                page,
                cluster,
                gt,
                ["same_page", "distance_clustered" if gt == "distance_cluster" else "single_asset"],
            )
            page_groups.append(entry)
            next_id += 1

        page_group_count = len(page_groups)
        page_distance_cluster_count = sum(1 for g in page_groups if g["group_type"] == "distance_cluster")
        for g in page_groups:
            g["page_group_count"] = page_group_count
            g["page_distance_cluster_count"] = page_distance_cluster_count
            g["safe_auto_match"] = (
                page_group_count == 1
                and g["group_type"] == "distance_cluster"
                and len(g.get("media_blocks", [])) >= 2
            )

        groups.extend(page_groups)

    return groups


def _build_caption_band_group_assist(
    semantic_groups: list[dict],
    page_legends: list[dict],
    page_media: list[dict],
    page_height: float,
) -> dict[str, dict]:
    if len(page_legends) < 2 or not semantic_groups or not page_media:
        return {}

    band_map = _partition_assets_by_caption_bands(page_legends, page_media, page_height)
    assist: dict[str, dict] = {}
    for group in semantic_groups:
        asset_ids = {str(bid) for bid in group.get("asset_block_ids", []) if bid is not None}
        if not asset_ids:
            assist[str(group.get("group_id", ""))] = {
                "caption_band_ids": [],
                "best_caption_band_id": None,
                "overlap_ratio": 0.0,
                "band_overlap": {},
                "evidence": [],
            }
            continue

        overlap_by_band: dict[str, float] = {}
        for band_id, band_assets in band_map.items():
            band_asset_ids = {str(a.get("block_id", "")) for a in band_assets if a.get("block_id") is not None}
            if not band_asset_ids:
                continue
            overlap = len(asset_ids & band_asset_ids) / max(1, len(asset_ids))
            if overlap > 0:
                overlap_by_band[str(band_id)] = overlap

        best_caption_band_id = None
        overlap_ratio = 0.0
        if overlap_by_band:
            best_caption_band_id, overlap_ratio = max(overlap_by_band.items(), key=lambda item: item[1])

        assist[str(group.get("group_id", ""))] = {
            "caption_band_ids": sorted(overlap_by_band),
            "best_caption_band_id": best_caption_band_id,
            "overlap_ratio": overlap_ratio,
            "band_overlap": overlap_by_band,
            "evidence": ["caption_band_assist"] if overlap_by_band else [],
        }

    return assist


def _build_candidate_figure_groups_from_assets(
    assets: list[dict],
    all_blocks: list[dict],
    legends: list[dict],
    page_width: float = 1200,
) -> list[dict]:
    groups = _build_semantic_figure_groups_from_assets(assets, all_blocks, page_width=page_width)
    groups_by_page: dict[int, list[dict]] = {}
    media_by_page: dict[int, list[dict]] = {}
    for group in groups:
        groups_by_page.setdefault(int(group.get("page", 0) or 0), []).append(group)
    for block in _filter_figure_assets(assets):
        media_by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_groups in groups_by_page.items():
        page_blocks = [b for b in all_blocks if int(b.get("page", 0) or 0) == page]
        page_height = _estimate_page_height(page_blocks)
        page_legends = [l for l in legends if l.get("page") == page]
        band_assist = _build_caption_band_group_assist(
            page_groups,
            page_legends,
            media_by_page.get(page, []),
            page_height,
        )
        for group in page_groups:
            group["page_legend_count"] = len(page_legends)
            group["assist"] = band_assist.get(str(group.get("group_id", "")), {
                "caption_band_ids": [],
                "best_caption_band_id": None,
                "overlap_ratio": 0.0,
                "band_overlap": {},
                "evidence": [],
            })

    return groups


def _score_legend_to_group(
    legend: dict,
    group: dict,
    *,
    caption_score: dict,
    page_width: float = 1200,
    page_height: float = 0,
    page_blocks: list[dict] | None = None,
    page_numbered_legend_count: int = 0,
    anchor_supported: bool = False,
    caption_text_supported: bool = False,
    family_supported: bool = False,
    zone_supported: bool = False,
) -> dict:
    gt = group.get("group_type", "")

    if gt == "distance_cluster":
        num_assets = len(group.get("media_blocks", []))
        if group.get("safe_auto_match") and num_assets >= 2:
            return {
                "score": 0.85,
                "decision": "matched",
                "evidence": ["same_page", "distance_clustered", "safe_auto_match"],
            }

        cluster_bbox = group.get("cluster_bbox", [0, 0, 0, 0])
        match_score = _score_legend_to_asset_with_orientation(
            legend,
            {"bbox": cluster_bbox, "page": group.get("page", 0)},
            caption_score=caption_score,
            anchor_supported=anchor_supported,
            caption_text_supported=caption_text_supported,
            family_supported=family_supported,
            zone_supported=zone_supported,
        )
        if num_assets >= 2 and match_score.get("score", 0) > 0:
            match_score = dict(match_score)
            match_score["score"] = min(1.0, match_score["score"] + 0.15)
            match_score.setdefault("evidence", []).append("multi_asset_coherence_bonus")
            if match_score["score"] >= 0.5 and match_score.get("decision") in ("candidate", "ambiguous"):
                match_score["decision"] = "matched"
        return match_score

    if gt == "page_assets":
        if not page_blocks or page_height <= 0:
            return {
                "score": 0.0,
                "decision": "rejected",
                "evidence": ["page_assets_missing_page_context"],
            }
        safe, gate_evidence = _is_safe_page_assets_group(
            group, legend, page_blocks, page_numbered_legend_count,
            page_width=page_width, page_height=page_height,
        )
        if not safe:
            return {
                "score": 0.0,
                "decision": "rejected",
                "evidence": ["page_assets_requires_gate"] + gate_evidence,
            }
        basic = {
            "score": 0.72,
            "decision": "matched",
            "evidence": ["same_page", "page_assets_safe_gate"] + gate_evidence,
        }
        if family_supported:
            basic["score"] = min(1.0, basic["score"] + 0.1)
            basic["evidence"].append("family_supported")
        return basic

    if gt == "single_asset":
        asset = group["media_blocks"][0]
        return _score_legend_to_asset_with_orientation(
            legend,
            asset,
            caption_score=caption_score,
            anchor_supported=anchor_supported,
            caption_text_supported=caption_text_supported,
            family_supported=family_supported,
            zone_supported=zone_supported,
        )

    cluster_bbox = group.get("cluster_bbox", [0, 0, 0, 0])
    match_score = _score_legend_to_asset_with_orientation(
        legend,
        {"bbox": cluster_bbox, "page": group.get("page", 0)},
        caption_score=caption_score,
        anchor_supported=anchor_supported,
        caption_text_supported=caption_text_supported,
        family_supported=family_supported,
        zone_supported=zone_supported,
    )
    num_assets = len(group.get("media_blocks", []))
    if num_assets > 1 and match_score.get("score", 0) > 0:
        coherence_bonus = 0.15
        match_score = dict(match_score)
        match_score["score"] = min(1.0, match_score["score"] + coherence_bonus)
        match_score.setdefault("evidence", []).append("multi_asset_coherence_bonus")
        if match_score["score"] >= 0.5 and match_score.get("decision") in ("ambiguous", "candidate"):
            match_score["decision"] = "matched"
        if match_score.get("decision") == "rejected":
            match_score["decision"] = "candidate"
    return match_score


def _asset_page_id(page: Any, block_id: Any) -> tuple[int, str] | None:
    if block_id in (None, ""):
        return None
    return (int(page or 0), str(block_id))


def _make_local_pairing_hypothesis(
    legend: dict,
    group: dict,
    *,
    mode: str,
    local_score: float,
    evidence: list[str] | None = None,
    conflicts: list[str] | None = None,
) -> dict:
    media_blocks = group.get("media_blocks", [])
    if media_blocks:
        asset_ids = [
            aid
            for block in media_blocks
            if (aid := _asset_page_id(block.get("page", group.get("page", 0)), block.get("block_id", ""))) is not None
        ]
    else:
        group_page = group.get("page", 0)
        asset_ids = [
            aid for block_id in group.get("asset_block_ids", []) if (aid := _asset_page_id(group_page, block_id)) is not None
        ]
    return {
        "legend_block_id": str(legend.get("block_id", "")),
        "group_id": str(group.get("group_id", "")),
        "mode": str(mode),
        "local_score": float(local_score),
        "evidence": list(evidence or []),
        "conflicts": list(conflicts or []),
        "would_consume_asset_ids": asset_ids,
    }


def _infer_local_pairing_mode(legend: dict, group: dict, *, page_width: float = 1200) -> str:
    legend_bbox = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
    group_bbox = group.get("cluster_bbox") or [0, 0, 0, 0]
    if len(legend_bbox) >= 4 and len(group_bbox) >= 4:
        legend_width = float(legend_bbox[2] - legend_bbox[0])
        legend_height = max(1.0, float(legend_bbox[3] - legend_bbox[1]))
        group_height = max(1.0, float(group_bbox[3] - group_bbox[1]))
        y_overlap = max(0.0, min(legend_bbox[3], group_bbox[3]) - max(legend_bbox[1], group_bbox[1]))
        x_gap = min(abs(group_bbox[0] - legend_bbox[2]), abs(legend_bbox[0] - group_bbox[2]))
        if (
            y_overlap >= min(legend_height, group_height) * 0.5
            and x_gap <= float(page_width) * 0.25
            and legend_width < float(page_width) * 0.6
        ):
            return "caption_sidecar"
    vertical_side = _asset_vertical_side(legend, group)
    if vertical_side == "below":
        return "caption_above"
    if vertical_side == "above":
        return "caption_below"
    return "caption_below"


def _mark_hypothesis_conflict(hypothesis: dict, conflict: str) -> None:
    if not conflict:
        return
    conflicts = hypothesis.setdefault("conflicts", [])
    if conflict not in conflicts:
        conflicts.append(conflict)


def _project_asset_record(asset: dict) -> dict:
    record = {
        "block_id": asset.get("block_id", ""),
        "bbox": asset.get("bbox", [0, 0, 0, 0]),
        "page": int(asset.get("page", 0) or 0),
    }
    for key in ("asset_family_hint", "asset_family_confidence", "asset_family_evidence"):
        if key in asset:
            record[key] = asset.get(key)
    return record


def _has_protected_figure_ownership(entry: dict, *, unresolved_legend_ids: set[str] | None = None) -> bool:
    settlement_type = str(entry.get("settlement_type") or "")
    if settlement_type not in {
        "same_page",
        "grouped_approximate",
        "composite_parent",
        "scoped_composite_parent",
    }:
        return False
    matched_assets = entry.get("matched_assets", []) or []
    if len(matched_assets) < 1:
        return False
    flags = set(entry.get("flags", []) or [])
    if "ordering_violation" in flags or "ownership_ambiguous" in flags:
        return False
    unresolved = unresolved_legend_ids or set()
    if settlement_type == "same_page":
        if len(matched_assets) > 1 and "composite_parent_match" not in flags:
            return False
        if unresolved and str(entry.get("legend_block_id", "")) not in unresolved and len(matched_assets) > 1:
            return False
    return True


class FigureOwnershipRegistry:
    def __init__(
        self,
        *,
        used_group_ids: set[str] | None = None,
        used_asset_page_ids: set[tuple[int, str]] | None = None,
    ) -> None:
        self.used_group_ids = used_group_ids if used_group_ids is not None else set()
        self.used_asset_page_ids = used_asset_page_ids if used_asset_page_ids is not None else set()
        self.group_states: dict[str, dict[str, str]] = {}
        self.asset_states: dict[tuple[int, str], dict[str, str]] = {}

    def reserve_group(self, group_id: str, *, reason: str) -> None:
        self._require_reason(reason)
        self.group_states[str(group_id)] = {"state": "reserved", "reason": reason}

    def transition_reserved_to_held(self, group_id: str, *, reason: str) -> None:
        self._require_reason(reason)
        self.group_states[str(group_id)] = {"state": "held", "reason": reason}

    def match_group(self, group: dict, *, owner_id: str, owner_family: str) -> None:
        group_id = str(group.get("group_id", ""))
        if group_id:
            self.group_states[group_id] = {
                "state": "matched",
                "owner_id": str(owner_id),
                "owner_family": str(owner_family),
            }
            self.used_group_ids.add(group_id)
        self.mark_assets_owned(self._group_asset_page_ids(group), owner_id=owner_id, owner_family=owner_family)

    def mark_assets_owned(
        self,
        asset_ids: list[tuple[int, str]],
        *,
        owner_id: str,
        owner_family: str,
    ) -> None:
        normalized_owner_id = str(owner_id)
        normalized_owner_family = str(owner_family)
        for asset_id in asset_ids:
            normalized = _asset_page_id(asset_id[0], asset_id[1])
            if normalized is None:
                continue
            current = self.asset_states.get(normalized)
            if current and current.get("owner_family") != normalized_owner_family:
                raise ValueError(f"Asset {normalized[1]} already owned by {current.get('owner_family')}")
            self.asset_states[normalized] = {
                "state": f"owned_by_{normalized_owner_family}",
                "owner_id": normalized_owner_id,
                "owner_family": normalized_owner_family,
            }
            self.used_asset_page_ids.add(normalized)

    def block_asset(self, asset_id: tuple[int, str], *, reason: str) -> None:
        self._require_reason(reason)
        normalized = _asset_page_id(asset_id[0], asset_id[1])
        if normalized is None:
            raise ValueError("blocked asset requires an asset id")
        self.asset_states[normalized] = {"state": "blocked", "reason": reason}

    def can_consume_group(self, group: dict) -> bool:
        group_id = str(group.get("group_id", ""))
        if group_id and group_id in self.used_group_ids:
            return False
        return self.can_consume_assets(self._group_asset_page_ids(group))

    def can_consume_assets(self, asset_ids: list[tuple[int, str]]) -> bool:
        for asset_id in asset_ids:
            normalized = _asset_page_id(asset_id[0], asset_id[1])
            if normalized is None:
                continue
            if normalized in self.used_asset_page_ids:
                return False
            state = self.asset_states.get(normalized)
            if state and state.get("state") == "soft_reserved":
                return False
        return True

    def soft_reserve_assets(self, asset_ids: list[tuple[int, str]], *, owner_id: str, reason: str) -> None:
        self._require_reason(reason)
        normalized_owner_id = str(owner_id)
        for asset_id in asset_ids:
            normalized = _asset_page_id(asset_id[0], asset_id[1])
            if normalized is None:
                continue
            self.asset_states[normalized] = {
                "state": "soft_reserved",
                "owner_id": normalized_owner_id,
                "reason": reason,
            }

    def finalize_soft_reservation(self, asset_ids: list[tuple[int, str]], *, owner_id: str, owner_family: str) -> None:
        normalized_owner_id = str(owner_id)
        normalized_owner_family = str(owner_family)
        for asset_id in asset_ids:
            normalized = _asset_page_id(asset_id[0], asset_id[1])
            if normalized is None:
                continue
            current = self.asset_states.get(normalized)
            if current is None or current.get("state") != "soft_reserved":
                continue
            self.asset_states[normalized] = {
                "state": f"owned_by_{normalized_owner_family}",
                "owner_id": normalized_owner_id,
                "owner_family": normalized_owner_family,
            }
            self.used_asset_page_ids.add(normalized)

    def release_soft_reservation(self, asset_ids: list[tuple[int, str]], *, owner_id: str) -> None:
        normalized_owner_id = str(owner_id)
        for asset_id in asset_ids:
            normalized = _asset_page_id(asset_id[0], asset_id[1])
            if normalized is None:
                continue
            current = self.asset_states.get(normalized)
            if current and current.get("state") == "soft_reserved" and current.get("owner_id") == normalized_owner_id:
                del self.asset_states[normalized]

    def _group_asset_page_ids(self, group: dict) -> list[tuple[int, str]]:
        media_blocks = group.get("media_blocks", [])
        if media_blocks:
            return [
                normalized
                for block in media_blocks
                if (normalized := _asset_page_id(block.get("page", group.get("page", 0)), block.get("block_id", "")))
                is not None
            ]
        group_page = group.get("page", 0)
        return [
            normalized
            for bid in group.get("asset_block_ids", [])
            if (normalized := _asset_page_id(group_page, bid)) is not None
        ]

    def _require_reason(self, reason: str) -> None:
        if not str(reason).strip():
            raise ValueError("ownership reason is required")


def _ownership_decision_metadata(decision: str, provenance: str, *, strong: bool, reason: str = "") -> dict:
    return {
        "ownership_decision": decision,
        "decision_provenance": provenance,
        "strong_ownership": strong,
        "decision_reason": reason,
    }


def _fallback_eligible_asset_page_ids(
    asset_page_ids: list[tuple[int, str]],
    *,
    used_asset_page_ids: set[tuple[int, str]],
    blocked_asset_page_ids: set[tuple[int, str]],
    grouped_asset_page_ids: set[tuple[int, str]] | None = None,
    allow_grouped: bool = False,
) -> list[tuple[int, str]]:
    grouped = grouped_asset_page_ids or set()
    eligible: list[tuple[int, str]] = []
    for page, block_id in asset_page_ids:
        asset_id = _asset_page_id(page, block_id)
        if asset_id is None:
            continue
        if asset_id in used_asset_page_ids or asset_id in blocked_asset_page_ids:
            continue
        if not allow_grouped and asset_id in grouped:
            continue
        eligible.append(asset_id)
    return eligible


def _fallback_can_consume(
    asset_page_ids: list[tuple[int, str]],
    *,
    used_asset_page_ids: set[tuple[int, str]],
    blocked_asset_page_ids: set[tuple[int, str]],
    grouped_asset_page_ids: set[tuple[int, str]] | None = None,
    allow_grouped: bool = False,
) -> bool:
    normalized = [aid for aid in (_asset_page_id(page, block_id) for page, block_id in asset_page_ids) if aid is not None]
    return len(_fallback_eligible_asset_page_ids(
        normalized,
        used_asset_page_ids=used_asset_page_ids,
        blocked_asset_page_ids=blocked_asset_page_ids,
        grouped_asset_page_ids=grouped_asset_page_ids,
        allow_grouped=allow_grouped,
    )) == len(normalized)


def _fallback_eligible_groups(
    groups: list[dict],
    *,
    used_group_ids: set[str],
    used_asset_page_ids: set[tuple[int, str]],
    blocked_asset_page_ids: set[tuple[int, str]] | None = None,
    grouped_asset_page_ids: set[tuple[int, str]] | None = None,
    allow_grouped: bool = True,
) -> list[dict]:
    blocked = blocked_asset_page_ids or set()
    eligible: list[dict] = []
    for group in groups:
        group_id = str(group.get("group_id", ""))
        if group_id and group_id in used_group_ids:
            continue
        asset_ids = [
            aid
            for aid in (
                _asset_page_id(group.get("page", 0), bid)
                for bid in group.get("asset_block_ids", [])
            )
            if aid is not None
        ]
        if not _fallback_can_consume(
            asset_ids,
            used_asset_page_ids=used_asset_page_ids,
            blocked_asset_page_ids=blocked,
            grouped_asset_page_ids=grouped_asset_page_ids,
            allow_grouped=allow_grouped,
        ):
            continue
        eligible.append(group)
    return eligible


def _expand_matched_assets_locally(
    legend: dict,
    matched_assets: list[dict],
    assets: list[dict],
    ownership: FigureOwnershipRegistry,
    page_captions: list[dict],
) -> list[dict]:
    if not matched_assets:
        return matched_assets

    legend_bbox = legend.get("bbox") or [0, 0, 0, 0]
    legend_top = legend_bbox[1] if len(legend_bbox) >= 4 else 0
    current = list(matched_assets)
    changed = True

    while changed:
        changed = False
        cluster_bbox = _cluster_bbox([a.get("bbox", [0, 0, 0, 0]) for a in current])
        cx1, cy1, cx2, cy2 = cluster_bbox

        lower_caption_tops = [
            (cap.get("bbox") or [0, 0, 0, 0])[1]
            for cap in page_captions
            if cap.get("block_id") != legend.get("block_id") and (cap.get("bbox") or [0, 0, 0, 0])[1] > cy2
        ]
        next_caption_top = min(lower_caption_tops) if lower_caption_tops else None

        for asset in assets:
            ap = asset.get("page", 0)
            aid = asset.get("block_id", "")
            if not aid or not ownership.can_consume_assets([(ap, aid)]):
                continue
            if ap != legend.get("page", 0):
                continue

            bbox = asset.get("bbox") or [0, 0, 0, 0]
            ax1, ay1, ax2, ay2 = bbox
            if ay2 >= legend_top:
                continue
            if next_caption_top is not None and ay1 >= next_caption_top:
                continue

            vertical_gap = max(0.0, max(ay1 - cy2, cy1 - ay2))
            horizontal_overlap = max(0.0, min(cx2, ax2) - max(cx1, ax1))
            horizontal_gap = max(0.0, ax1 - cx2, cx1 - ax2)
            min_width = max(1.0, min(cx2 - cx1, ax2 - ax1))
            wide_enough_overlap = horizontal_overlap >= min_width * 0.25 or (
                horizontal_gap <= 30.0 and horizontal_gap < min_width * 0.1
            )
            touches_stack = vertical_gap <= 30.0

            if touches_stack and wide_enough_overlap:
                current.append(asset)
                ownership.mark_assets_owned([(ap, aid)], owner_id=str(legend.get("block_id", "")), owner_family="figure")
                changed = True

    current.sort(key=lambda a: ((a.get("bbox") or [0, 0, 0, 0])[1], (a.get("bbox") or [0, 0, 0, 0])[0]))
    return current


def _caption_style_match(block: dict, all_blocks: list[dict]) -> bool:
    span = block.get("span_metadata") or {}
    if isinstance(span, list):
        span = span[0] if span else {}
    block_size = span.get("size")
    block_font = str(span.get("font", "") or "").lower()
    if block_size is None and not block_font:
        return False
    for b in all_blocks:
        if b is block:
            continue
        if b.get("role") != "figure_caption":
            continue
        s = b.get("span_metadata") or {}
        if isinstance(s, list):
            s = s[0] if s else {}
        sz = s.get("size")
        fn = str(s.get("font", "") or "").lower()
        if block_size is not None and sz is not None and abs(block_size - sz) <= 1.0:
            return True
        if block_font and fn and block_font == fn:
            return True
    return False


def _precaption_media_region(media_cluster: list[dict], caption_block: dict) -> bool:
    cluster_bottom = max(b.get("bbox", [0, 0, 0, 0])[3] for b in media_cluster)
    caption_top = caption_block.get("bbox", [0, 0, 0, 0])[1]
    tolerance = 10
    return cluster_bottom < caption_top + tolerance


def _compute_candidate_figure_regions(blocks: list[dict], page_width: float = 1200) -> list[dict]:
    clusters = _media_clusters(blocks, page_width)
    captions = [b for b in blocks if b.get("role") == "figure_caption"]
    regions: list[dict] = []
    for i, cluster in enumerate(clusters):
        cluster_bbox = _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in cluster])
        page = cluster[0].get("page", 0)
        attached: list[dict] = []
        unvalidated: list[dict] = []
        for cap in captions:
            if cap.get("page", 0) != page:
                continue
            if _precaption_media_region(cluster, cap):
                attached.append(cap)
            else:
                unvalidated.append(cap)
        regions.append(
            {
                "region_id": f"region_{i + 1:03d}",
                "page": page,
                "cluster_bbox": cluster_bbox,
                "media_blocks": cluster,
                "attached_captions": attached,
                "unvalidated_captions": unvalidated,
            }
        )
    return regions


def is_embedded_figure_text(block: dict, all_blocks: list[dict], page_width: float = 1200) -> bool:
    role = block.get("role", "")
    if role in ("figure_caption", "figure_caption_candidate"):
        return False
    text = block.get("text", "")
    if text and _is_formal_legend(text, block, page_width):
        return False

    block_bbox = block.get("bbox") or block.get("block_bbox")
    if not block_bbox or len(block_bbox) < 4:
        return False
    bx1, by1, bx2, by2 = block_bbox[:4]
    cx = (bx1 + bx2) / 2
    cy = (by1 + by2) / 2
    block_page = block.get("page", 0)

    for other in all_blocks:
        if other is block:
            continue
        if other.get("role") not in ("figure_asset", "media_asset"):
            continue
        if other.get("page", 0) != block_page:
            continue
        ob = other.get("bbox") or other.get("block_bbox")
        if not ob or len(ob) < 4:
            continue
        ox1, oy1, ox2, oy2 = ob[:4]
        if ox1 <= cx <= ox2 and oy1 <= cy <= oy2:
            return True
        block_width = bx2 - bx1
        if block_width < page_width * 0.2:
            h_overlap = bx1 < ox2 and ox1 < bx2
            if h_overlap:
                return True

    return False


def _formal_figure_caption_blocks(blocks: list[dict]) -> dict[int, list[dict]]:
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        role = str(block.get("role") or "")
        text = str(block.get("text") or "")
        if role not in {"figure_caption", "figure_caption_candidate"}:
            continue
        if _extract_figure_number(text) is None:
            continue
        page = int(block.get("page", 0) or 0)
        by_page.setdefault(page, []).append(block)
    for page_blocks in by_page.values():
        page_blocks.sort(key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
    return by_page


def _caption_width_ratio(block: dict, page_width: float) -> float:
    bbox = block.get("bbox") or [0, 0, 0, 0]
    if len(bbox) < 4 or page_width <= 0:
        return 0.0
    return max(0.0, float(bbox[2] - bbox[0]) / float(page_width))


def _same_page_narrow_caption_column(page_captions: list[dict], page_width: float) -> list[dict]:
    formal = [
        cap
        for cap in page_captions
        if _extract_figure_number(str(cap.get("text", ""))) is not None
        if _caption_width_ratio(cap, page_width) < 0.6
        and not _PANEL_LABEL_PATTERN.match(str(cap.get("text", "")).strip())
    ]
    if len(formal) < 2:
        return []

    def _center_x(cap: dict) -> float:
        bb = cap.get("bbox") or [0, 0, 0, 0]
        return (bb[0] + bb[2]) / 2

    max_spread = page_width * 0.08
    centers = [_center_x(cap) for cap in formal]

    if max(centers) - min(centers) <= max_spread:
        return sorted(formal, key=lambda cap: (cap.get("bbox") or [0, 0, 0, 0])[1])

    # Outlier-tolerant: cluster by x-center and keep the largest aligned column.
    ordered_by_x = sorted(formal, key=_center_x)
    clusters: list[list[dict]] = []

    for cap in ordered_by_x:
        cx = _center_x(cap)
        placed = False
        for cluster in clusters:
            cluster_centers = [_center_x(c) for c in cluster]
            cluster_mean = sum(cluster_centers) / len(cluster_centers)
            if abs(cx - cluster_mean) <= max_spread:
                cluster.append(cap)
                placed = True
                break
        if not placed:
            clusters.append([cap])

    viable = [c for c in clusters if len(c) >= 2]
    if not viable:
        return []

    best = max(viable, key=lambda c: (len(c), -_center_x(c[0])))

    best_centers = [_center_x(c) for c in best]
    if max(best_centers) - min(best_centers) > max_spread:
        return []

    return sorted(best, key=lambda cap: (cap.get("bbox") or [0, 0, 0, 0])[1])


def _caption_row_coupled_assets(caption: dict, assets: list[dict], *, page_width: float = 1200) -> list[dict]:
    caption_bbox = caption.get("bbox") or [0, 0, 0, 0]
    if len(caption_bbox) < 4:
        return []
    caption_height = max(1.0, float(caption_bbox[3] - caption_bbox[1]))
    coupled: list[dict] = []
    for asset in assets:
        asset_bbox = asset.get("bbox") or [0, 0, 0, 0]
        if len(asset_bbox) < 4:
            continue
        y_overlap = max(0.0, min(caption_bbox[3], asset_bbox[3]) - max(caption_bbox[1], asset_bbox[1]))
        x_gap = min(abs(asset_bbox[0] - caption_bbox[2]), abs(caption_bbox[0] - asset_bbox[2]))
        if y_overlap >= caption_height * 0.5 and x_gap <= float(page_width) * 0.25:
            coupled.append(asset)
    return coupled


def _identify_bundle_source_legend_ids(legends: list[dict], assets: list[dict]) -> set[str]:
    assets_by_page: dict[int, int] = {}
    for asset in assets:
        page = int(asset.get("page", 0) or 0)
        assets_by_page[page] = assets_by_page.get(page, 0) + 1

    legends_by_page: dict[int, list[dict]] = {}
    for legend in legends:
        if _extract_figure_number(str(legend.get("text", "") or "")) is None:
            continue
        page = int(legend.get("page", 0) or 0)
        legends_by_page.setdefault(page, []).append(legend)

    bundle_source_ids: set[str] = set()
    for page, page_legends in legends_by_page.items():
        if len(page_legends) < 3:
            continue
        if assets_by_page.get(page, 0) > 0:
            continue
        for legend in page_legends:
            bundle_source_ids.add(str(legend.get("block_id", "")))
    return bundle_source_ids


def _legend_has_same_page_asset(legend: dict, assets: list[dict]) -> bool:
    legend_page = int(legend.get("page", 0) or 0)
    return any(int(asset.get("page", 0) or 0) == legend_page for asset in assets)


def _legend_has_adjacent_page_asset(legend: dict, assets: list[dict]) -> bool:
    legend_page = int(legend.get("page", 0) or 0)
    return any(abs(int(asset.get("page", 0) or 0) - legend_page) == 1 for asset in assets)


def _strip_caption_number_prefix(text: str) -> str:
    return _FIGURE_NUMBER_PATTERN.sub("", text, count=1).strip()


def _normalized_caption_body(text: str) -> str:
    body = _strip_caption_number_prefix(text).lower().strip()
    body = re.sub(r"[.!?:;,]+$", "", body)
    body = " ".join(body.split())
    return body


def _legend_dedup_priority(legend: dict, *, bundle_source_legend_ids: set[str], assets: list[dict]) -> tuple[int, int, int, int, int]:
    legend_id = str(legend.get("block_id", ""))
    role = str(legend.get("role") or "")
    return (
        0 if legend_id in bundle_source_legend_ids else 1,
        1 if _legend_has_same_page_asset(legend, assets) else 0,
        1 if _legend_has_adjacent_page_asset(legend, assets) else 0,
        1 if _has_strong_explicit_caption_text(legend) else 0,
        1 if role == "figure_caption" else 0,
    )


def _build_composite_parent_figure_groups_visual_only(
    atomic_groups: list[dict],
    assets: list[dict],
    structured_blocks: list[dict],
    page_width: float,
) -> list[dict]:
    """Build same-page composite parent candidates from visual geometry only.

    Composite parents are sets of atomic groups on the same page that
    share strong horizontal alignment and are vertically adjacent --
    typical of multi-panel figures (2x2 grids, columnar stacks).
    Caption/legend identity is intentionally excluded from topology.
    """
    groups_by_page: dict[int, list[dict]] = {}
    for group in atomic_groups:
        groups_by_page.setdefault(int(group.get("page", 0) or 0), []).append(group)

    results: list[dict] = []

    for page, page_groups in groups_by_page.items():
        if len(page_groups) < 2:
            continue

        n = len(page_groups)

        def _x_overlap_ratio(b1: list[float], b2: list[float]) -> float:
            if len(b1) < 4 or len(b2) < 4:
                return 0.0
            x1 = max(b1[0], b2[0])
            x2 = min(b1[2], b2[2])
            overlap = max(0.0, x2 - x1)
            min_width = min(b1[2] - b1[0], b2[2] - b2[0])
            return overlap / min_width if min_width > 0 else 0.0

        def _height_similarity(b1: list[float], b2: list[float]) -> float:
            if len(b1) < 4 or len(b2) < 4:
                return 0.0
            h1 = b1[3] - b1[1]
            h2 = b2[3] - b2[1]
            if max(h1, h2) == 0:
                return 0.0
            return min(h1, h2) / max(h1, h2)

        def _width_similarity(b1: list[float], b2: list[float]) -> float:
            if len(b1) < 4 or len(b2) < 4:
                return 0.0
            w1 = b1[2] - b1[0]
            w2 = b2[2] - b2[0]
            if max(w1, w2) == 0:
                return 0.0
            return min(w1, w2) / max(w1, w2)

        # Union-Find for connected components
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        for i in range(n):
            for j in range(i + 1, n):
                bi = page_groups[i].get("cluster_bbox") or [0, 0, 0, 0]
                bj = page_groups[j].get("cluster_bbox") or [0, 0, 0, 0]
                if len(bi) < 4 or len(bj) < 4:
                    continue
                x_overlap = _x_overlap_ratio(bi, bj)
                h_sim = _height_similarity(bi, bj)
                w_sim = _width_similarity(bi, bj)
                if x_overlap >= 0.5 and (h_sim >= 0.4 or w_sim >= 0.5):
                    union(i, j)

        # Collect components with ≥2 groups
        components: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            components.setdefault(root, []).append(i)

        for root, indices in components.items():
            if len(indices) < 2:
                continue
            child_groups = [page_groups[i] for i in indices]
            child_ids = [str(g.get("group_id", "")) for g in child_groups]
            all_assets = []
            for g in child_groups:
                all_assets.extend(g.get("asset_block_ids", []))
            all_bboxes = [
                b for g in child_groups
                if (b := g.get("cluster_bbox")) and len(b) >= 4
            ]
            cluster_bbox = _cluster_bbox(all_bboxes) if all_bboxes else [0, 0, 0, 0]

            # Confidence scoring
            confidence = 0.50
            if len(child_groups) >= 3:
                confidence += 0.05
            if len(child_groups) >= 4:
                confidence += 0.05
            widths = []
            heights = []
            for g in child_groups:
                cb = g.get("cluster_bbox") or [0, 0, 0, 0]
                if len(cb) >= 4:
                    widths.append(cb[2] - cb[0])
                    heights.append(cb[3] - cb[1])
            if len(widths) >= 2:
                mean_w = sum(widths) / len(widths)
                if mean_w > 0:
                    cv_w = (sum((w - mean_w) ** 2 for w in widths) / len(widths)) ** 0.5 / mean_w
                    if cv_w < 0.25:
                        confidence += 0.05
            if len(heights) >= 2:
                mean_h = sum(heights) / len(heights)
                if mean_h > 0:
                    cv_h = (sum((h - mean_h) ** 2 for h in heights) / len(heights)) ** 0.5 / mean_h
                    if cv_h < 0.25:
                        confidence += 0.05
            confidence = min(0.75, confidence)

            results.append({
                "group_id": f"composite_parent_{page:04d}_{len(results):03d}",
                "group_type": "composite_parent",
                "page": page,
                "child_group_ids": child_ids,
                "asset_block_ids": list(dict.fromkeys(all_assets)),
                "cluster_bbox": cluster_bbox,
                "parent_evidence": [
                    "same_page",
                    "horizontal_alignment",
                    f"{len(child_groups)}_child_groups",
                ],
                "parent_confidence": confidence,
                "ownership_enabled": False,
            })

    return results


def _compute_grid_score(envelopes: list[dict]) -> float:
    if len(envelopes) < 2:
        return 0.0
    bboxes = [
        cb
        for env in envelopes
        if (cb := env.get("cluster_bbox") or env.get("bbox")) and len(cb) >= 4
    ]
    if len(bboxes) < 2:
        return 0.0
    y_centers = [(b[1] + b[3]) / 2 for b in bboxes]
    mean_y = sum(y_centers) / len(y_centers)
    page_h = max(b[3] for b in bboxes) - min(b[1] for b in bboxes)
    if page_h <= 0:
        return 0.0
    y_spread = sum(abs(y - mean_y) for y in y_centers) / len(y_centers)
    row_score = max(0.0, 1.0 - y_spread / page_h)
    x_centers = [(b[0] + b[2]) / 2 for b in bboxes]
    mean_x = sum(x_centers) / len(x_centers)
    page_w = max(b[2] for b in bboxes) - min(b[0] for b in bboxes)
    if page_w <= 0:
        return 0.0
    x_spread = sum(abs(x - mean_x) for x in x_centers) / len(x_centers)
    col_score = max(0.0, 1.0 - x_spread / page_w)
    return min(1.0, (row_score + col_score) / 2)


def _build_dense_composite_parent_candidates(
    atomic_groups: list[dict],
    unresolved_clusters: list[dict],
    numbered_legend_pages: set[int],
    page_width: float,
) -> list[dict]:
    results: list[dict] = []
    groups_by_page: dict[int, list[dict]] = {}
    for group in atomic_groups:
        page = int(group.get("page", 0) or 0)
        if page in numbered_legend_pages:
            groups_by_page.setdefault(page, []).append(group)

    uc_by_page: dict[int, list[dict]] = {}
    for uc in unresolved_clusters:
        page = int(uc.get("page", 0) or 0)
        if page in numbered_legend_pages:
            uc_by_page.setdefault(page, []).append(uc)

    for page in numbered_legend_pages:
        page_groups = groups_by_page.get(page, [])
        page_ucs = uc_by_page.get(page, [])

        total_asset_ids: set[str] = set()
        for g in page_groups:
            for bid in g.get("asset_block_ids", []):
                if bid:
                    total_asset_ids.add(str(bid))
        for uc in page_ucs:
            for bid in uc.get("media_block_ids", []):
                if bid:
                    total_asset_ids.add(str(bid))

        fragment_count = len(total_asset_ids)
        if fragment_count < 4:
            continue

        envelopes: list[dict] = []
        for g in page_groups:
            cb = g.get("cluster_bbox")
            if cb and len(cb) >= 4:
                envelopes.append({"cluster_bbox": cb})
        for uc in page_ucs:
            cb = uc.get("cluster_bbox")
            if cb and len(cb) >= 4:
                envelopes.append({"cluster_bbox": cb})

        if not envelopes:
            continue

        cluster_bbox = _cluster_bbox([e["cluster_bbox"] for e in envelopes])
        page_area = page_width * 1600.0
        envelope_area = (
            (cluster_bbox[2] - cluster_bbox[0]) * (cluster_bbox[3] - cluster_bbox[1])
            if len(cluster_bbox) >= 4
            else 0.0
        )
        compactness = min(1.0, envelope_area / max(1.0, page_area))

        grid_score = _compute_grid_score(envelopes)

        child_group_ids = [str(g.get("group_id", "")) for g in page_groups if g.get("group_id")]
        unresolved_cluster_ids = [
            str(uc.get("cluster_id", "")) for uc in page_ucs if uc.get("cluster_id")
        ]
        all_asset_ids: list[str] = list(dict.fromkeys(
            bid for g in page_groups for bid in g.get("asset_block_ids", []) if bid is not None
        ))

        reason = ["dense_fragment_page", f"{fragment_count}_visual_fragments"]
        if page_ucs:
            reason.append(f"{len(page_ucs)}_unresolved_clusters")

        results.append({
            "group_id": f"dense_composite_parent_{page:04d}_{len(results):03d}",
            "group_type": "composite_parent",
            "parent_subtype": "dense_composite",
            "page": page,
            "child_group_ids": child_group_ids,
            "unresolved_cluster_ids": unresolved_cluster_ids,
            "asset_block_ids": all_asset_ids,
            "embedded_text_block_ids": [],
            "cluster_bbox": cluster_bbox,
            "parent_evidence": reason,
            "parent_confidence": round(grid_score, 4),
            "fragment_count": fragment_count,
            "atomic_child_count": len(page_groups),
            "unresolved_child_count": len(page_ucs),
            "visual_mass": float(len(all_asset_ids)),
            "compactness": round(compactness, 4),
            "grid_score": round(grid_score, 4),
            "construction_reason": reason,
            "crosses_caption_boundary": False,
            "ownership_enabled": False,
        })

    return results


def _score_dense_parent_candidate_against_local_ownership(
    parent: dict,
    *,
    owned_asset_ids: set[str],
    unresolved_asset_ids: set[str],
) -> dict:
    asset_block_ids = {str(bid) for bid in parent.get("asset_block_ids", [])}
    unresolved_absorbed = asset_block_ids & unresolved_asset_ids
    already_owned = asset_block_ids & owned_asset_ids
    total_asset_count = max(1, len(asset_block_ids))
    coverage_gain = len(unresolved_absorbed)
    leftover_mass_absorbed = len(unresolved_absorbed)
    unresolved_reduction_ratio = round(len(unresolved_absorbed) / total_asset_count, 4)
    return {
        "coverage_gain": coverage_gain,
        "leftover_mass_absorbed": leftover_mass_absorbed,
        "unresolved_reduction_ratio": unresolved_reduction_ratio,
        "already_owned_count": len(already_owned),
        "total_parent_asset_count": total_asset_count,
    }


def _should_suppress_panel_title_candidate(
    block: dict,
    *,
    page_has_numbered_legend: bool,
    visual_envelopes: list[dict],
    page_width: float,
) -> bool:
    """Structurally demote short unnumbered text that looks like a caption
    but is actually a panel title inside a figure visual envelope.

    Signals (all required):
    1. no figure number
    2. short text span (<= 50 chars)
    3. inside a likely visual parent envelope (overlaps a candidate_group
       or composite_parent bbox on the same page)
    4. page already has a strong numbered figure caption
    5. title-like geometry (narrow block or small text relative to page)

    No literal string blacklist.
    """
    if not page_has_numbered_legend:
        return False
    text = str(block.get("text") or "").strip()
    if _extract_figure_number(text) is not None:
        return False
    if len(text) > 50:
        return False
    if len(text.split()) > 4:
        return False
    bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
    if len(bbox) < 4:
        return False
    block_width = bbox[2] - bbox[0]
    block_page = int(block.get("page", 0) or 0)
    page_envelopes = [
        env
        for env in visual_envelopes
        if int(env.get("page", 0) or 0) == block_page
    ]
    inside_envelope = False
    for env in page_envelopes:
        eb = env.get("cluster_bbox") or env.get("bbox") or [0, 0, 0, 0]
        if len(eb) < 4:
            continue
        x_overlap = bbox[0] < eb[2] and bbox[2] > eb[0]
        y_overlap = bbox[1] < eb[3] and bbox[3] > eb[1]
        x_near = max(0.0, eb[0] - bbox[2], bbox[0] - eb[2]) <= page_width * 0.3
        y_near = max(0.0, eb[1] - bbox[3], bbox[1] - eb[3]) <= 80
        if (x_overlap or x_near) and (y_overlap or y_near):
            inside_envelope = True
            break
    if not inside_envelope:
        return False
    if block_width > page_width * 0.7:
        return False
    return True


def _asset_vertical_side(legend: dict, group: dict) -> str:
    legend_bbox = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
    cluster_bbox = group.get("cluster_bbox") or [0, 0, 0, 0]
    if len(legend_bbox) < 4 or len(cluster_bbox) < 4:
        return "overlap"
    if cluster_bbox[3] <= legend_bbox[1]:
        return "above"
    if cluster_bbox[1] >= legend_bbox[3]:
        return "below"
    return "overlap"


def _allow_previous_page_sequential_match(cap: dict, asset: dict) -> bool:
    cp = int(cap.get("page", 0) or 0)
    ap = int(asset.get("page", 0) or 0)
    if ap != cp - 1:
        return False
    cap_bbox = cap.get("bbox") or [0, 0, 0, 0]
    asset_bbox = asset.get("bbox") or [0, 0, 0, 0]
    if len(cap_bbox) < 4 or len(asset_bbox) < 4:
        return False
    cap_top = cap_bbox[1]
    cap_width = cap_bbox[2] - cap_bbox[0]
    asset_bottom = asset_bbox[3]
    asset_width = asset_bbox[2] - asset_bbox[0]
    page_width = float(cap.get("page_width") or asset.get("page_width") or 1200)
    page_height = float(cap.get("page_height") or asset.get("page_height") or 1600)
    strong_numbered_caption = _extract_figure_number(str(cap.get("text", ""))) is not None
    post_reference_layout = str(cap.get("zone") or "") in {"post_reference_backmatter_zone", "display_zone"}
    starts_page = cap_top <= 220
    prior_asset_near_bottom = asset_bottom >= page_height * 0.7
    wide_caption = cap_width >= page_width * 0.6
    substantial_asset = asset_width >= page_width * 0.2
    return (
        strong_numbered_caption
        and post_reference_layout
        and starts_page
        and prior_asset_near_bottom
        and wide_caption
        and substantial_asset
    )


def _partition_assets_by_caption_bands(
    page_captions: list[dict], page_assets: list[dict], page_height: float
) -> dict[str, list[dict]]:
    if len(page_captions) < 2:
        return {}

    ordered = sorted(page_captions, key=lambda cap: (cap.get("bbox") or [0, 0, 0, 0])[1])
    result: dict[str, list[dict]] = {str(cap.get("block_id", "")): [] for cap in ordered}

    cap_bboxes = [(cap.get("bbox") or [0, 0, 0, 0]) for cap in ordered]
    side_by_side = all(cap_bboxes[i][2] <= cap_bboxes[i + 1][0] for i in range(len(cap_bboxes) - 1))

    if side_by_side:
        for asset in page_assets:
            bbox = asset.get("bbox") or [0, 0, 0, 0]
            ax = (bbox[0] + bbox[2]) / 2
            best_idx = min(
                range(len(ordered)),
                key=lambda idx: abs(ax - (cap_bboxes[idx][0] + cap_bboxes[idx][2]) / 2),
            )
            result[str(ordered[best_idx].get("block_id", ""))].append(asset)
        return result

    caption_tops = [cb[1] for cb in cap_bboxes]
    asset_centers = [
        (((asset.get("bbox") or [0, 0, 0, 0])[1] + (asset.get("bbox") or [0, 0, 0, 0])[3]) / 2) for asset in page_assets
    ]
    captions_precede_assets = bool(asset_centers) and min(caption_tops) <= min(asset_centers)

    boundaries: list[float] = [0.0]
    for upper, lower in zip(ordered, ordered[1:]):
        ub = upper.get("bbox") or [0, 0, 0, 0]
        lb = lower.get("bbox") or [0, 0, 0, 0]
        boundaries.append(((ub[1] + ub[3]) / 2 + (lb[1] + lb[3]) / 2) / 2)
    boundaries.append(float(page_height))

    for asset in page_assets:
        bbox = asset.get("bbox") or [0, 0, 0, 0]
        cy = (bbox[1] + bbox[3]) / 2 if len(bbox) >= 4 else 0
        if captions_precede_assets:
            for idx, cap in enumerate(ordered):
                if boundaries[idx] <= cy < boundaries[idx + 1]:
                    result[str(cap.get("block_id", ""))].append(asset)
                    break
        else:
            assigned = False
            for cap in ordered:
                cap_bbox = cap.get("bbox") or [0, 0, 0, 0]
                cap_top = cap_bbox[1] if len(cap_bbox) >= 4 else float(page_height)
                if cy <= cap_top:
                    result[str(cap.get("block_id", ""))].append(asset)
                    assigned = True
                    break
            if not assigned:
                result[str(ordered[-1].get("block_id", ""))].append(asset)
    return result


# --- Cross-page figure matching helpers (Stage 1) ---


def _is_strong_numbered_legend(
    block: dict,
    *,
    caption_score: dict | None = None,
    anchor_supported: bool | None = None,
    caption_text_supported: bool | None = None,
) -> bool:
    if _extract_figure_number(str(block.get("text") or "")) is None:
        return False
    if not _is_formal_legend(block.get("text", ""), block):
        return False
    if _is_insufficient_legend_evidence(block):
        return False
    cs = (
        caption_score
        if caption_score is not None
        else score_figure_caption(
            block,
            nearby_media=False,
            caption_style_match=False,
            body_prose_likelihood=_looks_like_inline_figure_mention(block.get("text", ""), block),
        )
    )
    if cs.get("score", 0) < 0.4:
        return False
    if _is_validation_first_legend_candidate(block):
        a_s = anchor_supported if anchor_supported is not None else _has_anchor_supported_legend_context(block)
        c_s = caption_text_supported if caption_text_supported is not None else _has_strong_explicit_caption_text(block)
        if not a_s and not c_s:
            return False
    return True


def _is_structurally_matchable_group(group: dict, *, competing_caption_pages: set[int]) -> bool:
    if not group.get("asset_block_ids"):
        return False
    if group.get("_non_body_media"):
        return False
    cb = group.get("cluster_bbox")
    if not cb or len(cb) < 4:
        return False
    if group.get("group_type") == "page_assets" and group.get("page") in competing_caption_pages:
        return False
    return True


def _is_unowned_matchable_group(
    group: dict,
    *,
    competing_caption_pages: set[int],
    used_group_ids: set[str],
    used_asset_page_ids: set[tuple],
) -> bool:
    if not _is_structurally_matchable_group(group, competing_caption_pages=competing_caption_pages):
        return False
    if str(group.get("group_id", "")) in used_group_ids:
        return False
    g_page = group.get("page", 0)
    for bid in group.get("asset_block_ids", []):
        if bid and (g_page, bid) in used_asset_page_ids:
            return False
    return True


def _build_page_ledger(legends: list[dict], candidate_groups: list[dict]) -> dict[int, dict]:
    ledger: dict[int, dict] = {}
    for leg in legends:
        p = int(leg.get("page", 0) or 0)
        if p not in ledger:
            ledger[p] = {
                "page": p,
                "legend_count": 0,
                "numbered_legend_count": 0,
                "group_count": 0,
                "top_legend_count": 0,
                "bottom_legend_count": 0,
                "delta": 0,
            }
        ledger[p]["legend_count"] += 1
        if _extract_figure_number(str(leg.get("text") or "")) is not None:
            ledger[p]["numbered_legend_count"] += 1
    for g in candidate_groups:
        p = int(g.get("page", 0) or 0)
        if p not in ledger:
            ledger[p] = {
                "page": p,
                "legend_count": 0,
                "numbered_legend_count": 0,
                "group_count": 0,
                "top_legend_count": 0,
                "bottom_legend_count": 0,
                "delta": 0,
            }
        ledger[p]["group_count"] += 1
    for p in ledger:
        ledger[p]["delta"] = ledger[p]["legend_count"] - ledger[p]["group_count"]
    return ledger


def _build_residual_ledger(
    legends: list[dict],
    candidate_groups: list[dict],
    *,
    competing_caption_pages: set[int],
) -> dict[int, dict]:
    ledger: dict[int, dict] = {}
    for leg in legends:
        p = int(leg.get("page", 0) or 0)
        if not _is_strong_numbered_legend(leg):
            continue
        if p not in ledger:
            ledger[p] = {
                "page": p,
                "unmatched_strong_legend_count": 0,
                "unmatched_matchable_group_count": 0,
                "residual_delta": 0,
            }
        ledger[p]["unmatched_strong_legend_count"] += 1
    for g in candidate_groups:
        p = int(g.get("page", 0) or 0)
        if not _is_structurally_matchable_group(g, competing_caption_pages=competing_caption_pages):
            continue
        if p not in ledger:
            ledger[p] = {
                "page": p,
                "unmatched_strong_legend_count": 0,
                "unmatched_matchable_group_count": 0,
                "residual_delta": 0,
            }
        ledger[p]["unmatched_matchable_group_count"] += 1
    for p in ledger:
        ledger[p]["residual_delta"] = (
            ledger[p]["unmatched_strong_legend_count"] - ledger[p]["unmatched_matchable_group_count"]
        )
    return ledger


def _residual_group_surplus(pages: list[int], residual_ledger: dict[int, dict]) -> int:
    return sum(
        max(
            0,
            residual_ledger[p]["unmatched_matchable_group_count"] - residual_ledger[p]["unmatched_strong_legend_count"],
        )
        for p in pages
        if p in residual_ledger
    )


def _residual_legend_surplus(pages: list[int], residual_ledger: dict[int, dict]) -> int:
    return sum(
        max(
            0,
            residual_ledger[p]["unmatched_strong_legend_count"] - residual_ledger[p]["unmatched_matchable_group_count"],
        )
        for p in pages
        if p in residual_ledger
    )


def _grouped_asset_page_ids(candidate_groups: list[dict]) -> set[tuple[int, str]]:
    return {
        (int(group.get("page", 0) or 0), str(bid))
        for group in candidate_groups
        for bid in group.get("asset_block_ids", [])
        if bid is not None
    }


def _recompute_final_unmatched_assets(
    assets: list[dict],
    used_asset_page_ids: set[tuple],
    unresolved_clusters: list[dict],
) -> list[dict]:
    unresolved_asset_page_ids: set[tuple[int, str]] = set()
    for cluster in unresolved_clusters:
        page = int(cluster.get("page", 0) or 0)
        for bid in cluster.get("media_block_ids", []):
            if bid is not None:
                unresolved_asset_page_ids.add((page, str(bid)))

    final_unmatched: list[dict] = []
    for asset in assets:
        page = int(asset.get("page", 0) or 0)
        bid = asset.get("block_id", "")
        if not bid:
            final_unmatched.append(asset)
            continue
        page_bid = (page, str(bid))
        if page_bid in used_asset_page_ids or page_bid in unresolved_asset_page_ids:
            continue
        final_unmatched.append(asset)
    return final_unmatched


def _reserve_cross_page_objects(
    legends: list[dict],
    candidate_groups: list[dict],
    residual_ledger: dict[int, dict],
    *,
    competing_caption_pages: set[int],
    sidecar_pages: set[int],
    used_group_ids: set[str] | None = None,
    used_asset_page_ids: set[tuple] | None = None,
) -> tuple[set[str], set[str]]:
    reserved_legend_ids: set[tuple[int, str]] = set()
    reserved_group_ids: set[str] = set()

    legends_by_page: dict[int, list[dict]] = {}
    for leg in legends:
        p = int(leg.get("page", 0) or 0)
        legends_by_page.setdefault(p, []).append(leg)

    groups_by_page: dict[int, list[dict]] = {}
    for g in candidate_groups:
        p = int(g.get("page", 0) or 0)
        groups_by_page.setdefault(p, []).append(g)

    used_gids = used_group_ids or set()
    used_aids = used_asset_page_ids or set()

    for page, entry in residual_ledger.items():
        if page in sidecar_pages:
            continue
        if entry["residual_delta"] > 0:
            k = min(entry["residual_delta"], _residual_group_surplus([page - 1, page - 2], residual_ledger))
            if k <= 0:
                continue
            page_legends = sorted(
                [l for l in legends_by_page.get(page, []) if _is_strong_numbered_legend(l)],
                key=lambda l: (l.get("bbox") or [0, 0, 0, 0])[1],
            )
            for leg in page_legends[:k]:
                reserved_legend_ids.add((int(leg.get("page", 0) or 0), str(leg.get("block_id", ""))))
        if entry["residual_delta"] < 0:
            k = min(-entry["residual_delta"], _residual_legend_surplus([page + 1, page + 2], residual_ledger))
            if k <= 0:
                continue
            page_groups = sorted(
                [
                    g
                    for g in groups_by_page.get(page, [])
                    if _is_unowned_matchable_group(
                        g,
                        competing_caption_pages=competing_caption_pages,
                        used_group_ids=used_gids,
                        used_asset_page_ids=used_aids,
                    )
                ],
                key=lambda g: (g.get("cluster_bbox") or [0, 0, 0, 0])[3],
                reverse=True,
            )
            for grp in page_groups[:k]:
                reserved_group_ids.add(str(grp.get("group_id", "")))

    return reserved_legend_ids, reserved_group_ids


def _reserved_legend_block_ids(reserved_legend_ids: set[tuple[int, str]]) -> set[str]:
    return {block_id for _, block_id in reserved_legend_ids}


INTERRUPTION_ROLES = {
    "section_heading",
    "subsection_heading",
    "sub_subsection_heading",
    "table_caption",
    "table_html",
    "reference_heading",
    "reference_item",
    "backmatter_heading",
    "backmatter_body",
}


def _has_strong_interruption(page: int, structured_blocks: list[dict]) -> bool:
    body_count = sum(
        1 for b in structured_blocks if int(b.get("page", 0) or 0) == page and b.get("role") == "body_paragraph"
    )
    if body_count >= 3:
        return True
    return any(
        int(b.get("page", 0) or 0) == page and b.get("role", "") in INTERRUPTION_ROLES for b in structured_blocks
    )


def _settle_cross_page_reserved_objects(
    reserved_legend_ids: set[tuple[int, str]],
    reserved_group_ids: set[str],
    legends: list[dict],
    candidate_groups: list[dict],
    structured_blocks: list[dict],
    matched_figures: list[dict],
    ambiguous_figures: list[dict],
    unmatched_legends: list[dict],
    used_group_ids: set[str],
    used_asset_page_ids: set[tuple],
    ownership: FigureOwnershipRegistry,
    *,
    residual_ledger: dict[int, dict],
    competing_caption_pages: set[int],
    page_width: float = 1200,
) -> None:
    legends_by_id = {
        (int(leg.get("page", 0) or 0), str(leg.get("block_id", ""))): leg
        for leg in legends
    }
    groups_by_id = {str(g.get("group_id", "")): g for g in candidate_groups}

    failed_legend_ids: set[tuple[int, str]] = set()
    failed_group_ids: set[str] = set()

    # reserved legends look backward
    for lid in sorted(reserved_legend_ids):
        legend = legends_by_id.get(lid)
        if legend is None:
            continue
        leg_page = int(legend.get("page", 0) or 0)
        for pp in (leg_page - 1, leg_page - 2):
            if pp < 0:
                continue
            if pp == leg_page - 2 and _has_strong_interruption(leg_page - 1, structured_blocks):
                continue
            target_groups = sorted(
                [
                    g
                    for g in candidate_groups
                    if str(g.get("group_id", "")) not in used_group_ids and g.get("page") == pp
                ],
                key=lambda g: (g.get("cluster_bbox") or [0, 0, 0, 0])[3],
                reverse=True,
            )
            if not target_groups:
                continue
            best_group = target_groups[0]
            came_from_reserved = str(best_group.get("group_id", "")) in reserved_group_ids

            legend_text = str(legend.get("text") or "")
            fn = _extract_figure_number(legend_text)
            if fn is None:
                continue
            ns = _extract_figure_namespace(legend_text)
            fig_id = _format_figure_id(ns, fn)

            caption_score = score_figure_caption(
                legend, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
            )

            group_page = int(best_group.get("page", 0) or 0)
            group_assets = [g for g in best_group.get("media_blocks", [])]

            ownership.match_group(best_group, owner_id=f"{lid[0]}:{lid[1]}", owner_family="figure")

            asset_pages = sorted({int(a.get("page", 0) or 0) for a in group_assets})
            matched_figures.append(
                {
                    "figure_id": fig_id,
                    "figure_namespace": ns,
                    "legend_block_id": legend.get("block_id", ""),
                    "page": group_page,
                    "legend_page": leg_page,
                    "asset_pages": asset_pages if asset_pages else [group_page],
                    "text": legend_text,
                    "figure_number": fn,
                    "matched_assets": [
                        {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])} for a in group_assets
                    ],
                    "asset_block_ids": [str(a.get("block_id", "")) for a in group_assets if a.get("block_id")],
                    "bridge_block_ids": [],
                    "group_type": best_group.get("group_type", ""),
                    "group_evidence": best_group.get("group_evidence", []) + ["cross_page_backward"],
                    "cluster_bbox": best_group.get("cluster_bbox", [0, 0, 0, 0]),
                    "confidence": 0.5,
                    "match_score": {"score": 0.5, "decision": "matched", "evidence": ["cross_page_backward"]},
                    "flags": ["cross_page_match"],
                    "caption_score": caption_score,
                    "settlement_type": "cross_page_backward",
                }
            )
            unmatched_legends[:] = [
                u for u in unmatched_legends
                if (int(u.get("page", 0) or 0), str(u.get("block_id", ""))) != lid
            ]
            break
        else:
            failed_legend_ids.add(lid)

    # Build set of already-matched legend IDs to prevent double-matching
    _used_legend_ids: set[str] = {
        str(m.get("legend_block_id", "")) for m in matched_figures if m.get("legend_block_id")
    }

    # reserved groups look forward
    for gid in sorted(reserved_group_ids):
        if gid in used_group_ids:
            continue
        group = groups_by_id.get(gid)
        if group is None:
            continue
        group_page = int(group.get("page", 0) or 0)
        for np in (group_page + 1, group_page + 2):
            if np == group_page + 2 and _has_strong_interruption(group_page + 1, structured_blocks):
                continue
            candidate_legends = sorted(
                [
                    l
                    for l in legends
                    if str(l.get("block_id", "")) not in _used_legend_ids
                    and (int(l.get("page", 0) or 0), str(l.get("block_id", ""))) not in failed_legend_ids
                    and int(l.get("page", 0) or 0) == np
                    and _is_strong_numbered_legend(l)
                ],
                key=lambda l: (l.get("bbox") or [0, 0, 0, 0])[1],
            )
            if not candidate_legends:
                continue
            best_legend = candidate_legends[0]
            lid = str(best_legend.get("block_id", ""))

            legend_text = str(best_legend.get("text") or "")
            fn = _extract_figure_number(legend_text)
            if fn is None:
                continue
            ns = _extract_figure_namespace(legend_text)
            fig_id = _format_figure_id(ns, fn)

            caption_score = score_figure_caption(
                best_legend, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
            )

            group_assets = [g for g in group.get("media_blocks", [])]
            ownership.match_group(group, owner_id=lid, owner_family="figure")

            asset_pages = sorted({int(a.get("page", 0) or 0) for a in group_assets})
            matched_figures.append(
                {
                    "figure_id": fig_id,
                    "figure_namespace": ns,
                    "legend_block_id": best_legend.get("block_id", ""),
                    "page": group_page,
                    "legend_page": np,
                    "asset_pages": asset_pages if asset_pages else [group_page],
                    "text": legend_text,
                    "figure_number": fn,
                    "matched_assets": [
                        {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])} for a in group_assets
                    ],
                    "asset_block_ids": [str(a.get("block_id", "")) for a in group_assets if a.get("block_id")],
                    "bridge_block_ids": [],
                    "group_type": group.get("group_type", ""),
                    "group_evidence": group.get("group_evidence", []) + ["cross_page_forward"],
                    "cluster_bbox": group.get("cluster_bbox", [0, 0, 0, 0]),
                    "confidence": 0.5,
                    "match_score": {"score": 0.5, "decision": "matched", "evidence": ["cross_page_forward"]},
                    "flags": ["cross_page_match"],
                    "caption_score": caption_score,
                    "settlement_type": "cross_page_forward",
                }
            )
            unmatched_legends[:] = [u for u in unmatched_legends if str(u.get("block_id", "")) != lid]
            break
        else:
            failed_group_ids.add(gid)

    # Failed reserved legends
    for lid in failed_legend_ids:
        legend = legends_by_id.get(lid)
        if legend is None:
            continue
        ambiguous_figures.append(
            {
                "legend_block_id": lid[1],
                "page": legend.get("page", 0),
                "text": legend.get("text", ""),
                "figure_number": _extract_figure_number(str(legend.get("text", "") or "")),
                "hold_reason": "reserved_cross_page_no_valid_group",
            }
        )


def _resolve_figure_id_collisions(figure_inventory: dict) -> None:
    _collision_seen: dict[str, int] = {}
    for _fig in (
        *figure_inventory.get("matched_figures", []),
        *figure_inventory.get("held_figures", []),
        *figure_inventory.get("ambiguous_figures", []),
    ):
        _fig_id = _fig.get("figure_id", "")
        if not _fig_id:
            continue
        if _fig_id in _collision_seen:
            _collision_seen[_fig_id] += 1
            _fig["figure_id"] = f"figure_{'s' * _collision_seen[_fig_id]}{_fig_id.removeprefix('figure_')}"
        else:
            _collision_seen[_fig_id] = 0


def _coerce_int_figure_number(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _resolve_legend_bbox(
    matched_item: dict,
    structured_blocks: list[dict],
    inventory: dict,
) -> list[float] | None:
    legend_bbox = matched_item.get("legend_bbox")
    if legend_bbox:
        return legend_bbox
    legend_block_id = str(matched_item.get("legend_block_id") or "")
    if legend_block_id:
        legend_page = matched_item.get("legend_page")
        for block in structured_blocks:
            if str(block.get("block_id") or "") == legend_block_id and block.get("page") == legend_page:
                return block.get("bbox")
        for entry in inventory.get("figure_legends", []):
            if str(entry.get("block_id") or "") == legend_block_id:
                return entry.get("bbox")
    return None


def _infer_missing_main_figure_numbers(
    inventory: dict,
    structured_blocks: list[dict],
) -> dict:
    matched = inventory.get("matched_figures", [])
    known_set: set[int] = set()
    for item in matched:
        num = _coerce_int_figure_number(item.get("figure_number"))
        if num is None:
            continue
        marker = _extract_figure_marker(str(item.get("text", "")))
        if marker["namespace"] != "main" or marker["has_s_prefix"]:
            continue
        if num in known_set:
            inventory["figure_number_inference"] = {
                "status": "skipped",
                "method": "leading_gap",
                "reason": "duplicate_known_main_numbers",
                "eligible_unknown_count": 0,
                "known_main_numbers": [],
                "inferred_figure_number": None,
            }
            return inventory
        known_set.add(num)

    eligible: list[tuple[dict, list[float]]] = []
    for item in matched:
        num = _coerce_int_figure_number(item.get("figure_number"))
        if num is not None:
            continue
        marker = _extract_figure_marker(str(item.get("text", "")))
        if marker["namespace"] != "main" or marker["has_s_prefix"]:
            continue
        legend_block_id = str(item.get("legend_block_id") or "")
        if not legend_block_id.strip():
            continue
        asset_block_ids = item.get("asset_block_ids", [])
        if not isinstance(asset_block_ids, list) or not asset_block_ids:
            continue
        settlement_type = item.get("settlement_type", "")
        if settlement_type not in {"same_page", "group_sequential", "cross_page_forward",
                                   "cross_page_backward", "composite_parent"}:
            continue
        item_text = str(item.get("text", ""))
        legend_text = ""
        for entry in inventory.get("figure_legends", []):
            if str(entry.get("block_id", "")) == str(legend_block_id):
                legend_text = str(entry.get("text", ""))
                break
        combined = item_text + " " + legend_text
        if _has_frontmatter_visual_veto(combined):
            continue
        legend_bbox = _resolve_legend_bbox(item, structured_blocks, inventory)
        if legend_bbox is None:
            continue
        eligible.append((item, legend_bbox))

    if not eligible:
        inventory["figure_number_inference"] = {
            "status": "skipped",
            "method": "leading_gap",
            "reason": "no_eligible_unknowns",
            "eligible_unknown_count": 0,
            "known_main_numbers": sorted(known_set),
            "inferred_figure_number": None,
        }
        return inventory

    if not known_set or min(known_set) != 2:
        inventory["figure_number_inference"] = {
            "status": "skipped",
            "method": "leading_gap",
            "reason": "known_min_not_2",
            "eligible_unknown_count": len(eligible),
            "known_main_numbers": sorted(known_set),
            "inferred_figure_number": None,
        }
        return inventory

    if len(eligible) != 1:
        inventory["figure_number_inference"] = {
            "status": "skipped",
            "method": "leading_gap",
            "reason": "multiple_eligible_unknowns",
            "eligible_unknown_count": len(eligible),
            "known_main_numbers": sorted(known_set),
            "inferred_figure_number": None,
        }
        return inventory

    unknown_item, unknown_bbox = eligible[0]
    first_known = None
    for item in matched:
        num = _coerce_int_figure_number(item.get("figure_number"))
        if num == min(known_set):
            first_known = item
            break
    if first_known is None:
        inventory["figure_number_inference"] = {
            "status": "skipped",
            "method": "leading_gap",
            "reason": "first_known_not_found",
            "eligible_unknown_count": len(eligible),
            "known_main_numbers": sorted(known_set),
            "inferred_figure_number": None,
        }
        return inventory

    def _fig_order_key(_item, _bbox):
        return (
            min(_item.get("asset_pages") or [_item.get("page", 1)]),
            _item.get("legend_page") or _item.get("page", 1),
            _bbox[1],
            _bbox[0],
        )

    first_known_bbox = _resolve_legend_bbox(first_known, structured_blocks, inventory)
    if first_known_bbox is None:
        inventory["figure_number_inference"] = {
            "status": "skipped",
            "method": "leading_gap",
            "reason": "first_known_bbox_unresolvable",
            "eligible_unknown_count": len(eligible),
            "known_main_numbers": sorted(known_set),
            "inferred_figure_number": None,
        }
        return inventory

    unknown_key = _fig_order_key(unknown_item, unknown_bbox)
    first_known_key = _fig_order_key(first_known, first_known_bbox)
    if unknown_key >= first_known_key:
        inventory["figure_number_inference"] = {
            "status": "skipped",
            "method": "leading_gap",
            "reason": "unknown_not_before_first_known",
            "eligible_unknown_count": len(eligible),
            "known_main_numbers": sorted(known_set),
            "inferred_figure_number": None,
        }
        return inventory

    all_items: list[dict] = list(matched) + inventory.get("held_figures", []) + inventory.get("ambiguous_figures", [])
    for noise in all_items:
        if noise is unknown_item or noise is first_known:
            continue
        noise_bbox = _resolve_legend_bbox(noise, structured_blocks, inventory)
        if noise_bbox is None:
            inventory["figure_number_inference"] = {
                "status": "skipped",
                "method": "leading_gap",
                "reason": "intervening_unknown_unorderable",
                "eligible_unknown_count": len(eligible),
                "known_main_numbers": sorted(known_set),
                "inferred_figure_number": None,
            }
            return inventory
        noise_key = _fig_order_key(noise, noise_bbox)
        if unknown_key < noise_key < first_known_key:
            inventory["figure_number_inference"] = {
                "status": "skipped",
                "method": "leading_gap",
                "reason": "intervening_items_between",
                "eligible_unknown_count": len(eligible),
                "known_main_numbers": sorted(known_set),
                "inferred_figure_number": None,
            }
            return inventory

    unknown_item["figure_number"] = 1
    unknown_item["figure_id"] = _format_figure_id("main", 1)
    unknown_item["figure_namespace"] = "main"
    unknown_item["number_inference"] = {
        "status": "accepted",
        "method": "leading_gap",
        "inferred_number": 1,
        "known_numbers": sorted(known_set),
    }
    for legend in inventory.get("figure_legends", []):
        if str(legend.get("block_id", "")) == str(unknown_item.get("legend_block_id", "")):
            legend["inferred_figure_number"] = 1
            legend["figure_number_source"] = "sequence_gap_inference"
            break

    inventory["figure_number_inference"] = {
        "status": "accepted",
        "method": "leading_gap",
        "reason": "accepted",
        "eligible_unknown_count": len(eligible),
        "known_main_numbers": sorted(known_set),
        "inferred_figure_number": 1,
    }
    return inventory


def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200, page_pdf_lines_by_page: dict[int, list[dict]] | None = None) -> dict[str, Any]:
    return build_figure_inventory_vnext(structured_blocks, page_width)

def build_figure_inventory_vnext(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    from .ocr_figure_vnext_accounting_pass import FinalAccountingPass
    from .ocr_figure_vnext_bundle_pass import LegendBundlePass
    from .ocr_figure_vnext_classic_seq_pass import ClassicSequentialPass, UnresolvedClusterConsolidation
    from .ocr_figure_vnext_composite_pass import CompositeParentPass
    from .ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
    from .ocr_figure_vnext_group_seq_pass import GroupSequentialPass
    from .ocr_figure_vnext_locator_pass import LocatorBridgePass
    from .ocr_figure_vnext_passes import (
        CrossPageReservationPass,
        CrossPageSettlementPass,
        PrimarySamePagePass,
        _resource_page,
    )
    from .ocr_figure_vnext_sidecar_pass import SidecarPass
    from .ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

    corpus = FigureCorpus.from_blocks(structured_blocks, page_width=page_width)
    candidate_index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=candidate_index, ledger=OwnershipLedger())
    reports = []
    for pass_cls in (
        PrimarySamePagePass,
        CompositeParentPass,
        SidecarPass,
        LocatorBridgePass,
        CrossPageReservationPass,
        CrossPageSettlementPass,
        LegendBundlePass,
        GroupSequentialPass,
        ClassicSequentialPass,
        UnresolvedClusterConsolidation,
        FinalAccountingPass,
    ):
        reports.append(pass_cls().run(state))
    matched_ids = {str(m.get("legend_block_id", "")) for m in state.matches}

    return {
        "pipeline_mode": "vnext",
        "matched_figures": state.matches,
        "ambiguous_figures": [],
        "unmatched_legends": [b for b in candidate_index.deduped_legends if str(b.get("block_id", "")) not in matched_ids],
        "unmatched_assets": [
            a for a in corpus.raw_assets
            if (_resource_page(a) is not None
                and state.ledger.owner_of_asset(page=_resource_page(a), block_id=a.get("block_id")) is None)
        ],
        "unresolved_clusters": list(state.unresolved),
        "held_figures": list(candidate_index.held_legends),
        "rejected_legends": list(candidate_index.rejected_legends),
        "page_ledger": {},
        "residual_ledger": {},
        "local_pairing_hypotheses": [],
        "pass_reports": [asdict(r) for r in reports],
        "completeness": state.completeness or {
            "total_numbered_legends": len(candidate_index.deduped_legends),
            "accounted_for": len(state.matches),
            "details": [],
        },
    }

def build_figure_inventory_legacy(structured_blocks: list[dict], page_width: float = 1200, page_pdf_lines_by_page: dict[int, list[dict]] | None = None) -> dict[str, Any]:
    """[DEPRECATED] Legacy figure inventory builder — use build_figure_inventory_vnext instead.

    Retained for comparison tooling (scripts/dev/compare_figure_inventory_legacy_vs_vnext.py).
    Will be removed when vnext comparison is no longer needed.
    """
    legends: list[dict] = []
    held_figures: list[dict] = []
    rejected_legends: list[dict] = []
    assets: list[dict] = []
    unmatched_legends: list[dict] = []
    unmatched_assets: list[dict] = []
    figure_locators: list[dict] = []
    matched_figures: list[dict] = []
    unresolved_clusters: list[dict] = []
    ambiguous_figures: list[dict] = []
    local_pairing_hypotheses: list[dict] = []
    used_group_ids: set[str] = set()
    used_asset_page_ids: set[tuple[int, str]] = set()
    ownership = FigureOwnershipRegistry(used_group_ids=used_group_ids, used_asset_page_ids=used_asset_page_ids)

    def _collect_bridge_blocks(page: int) -> list[dict]:
        bridges: list[dict] = []
        for block in structured_blocks:
            if int(block.get("page", 0) or 0) != page:
                continue
            if not block.get("bridge_eligible"):
                continue
            if str(block.get("layout_region") or "") != "display_zone":
                continue
            bridges.append(block)
        return bridges

    for block in structured_blocks:
        if block.get("page_width"):
            page_width = float(block["page_width"])

    for block in structured_blocks:
        role = block.get("role", "")
        if block.get("_non_body_media") or role == "non_body_insert":
            continue
        # Skip single-letter panel labels (A, B, (C), A.) in figure legends
        if _PANEL_LABEL_PATTERN.match(str(block.get("text", "")).strip()):
            continue
        # Skip body_paragraph that was demoted from figure_caption_candidate —
        # candidate resolution already judged it as narrative prose, not a legend.
        # Re-activating it via geometry/style signals causes body text to leak
        # into legend matching (e.g. YGH7VEX6 Figure 11).
        if role == "body_paragraph" and str(block.get("seed_role") or "") in {
            "figure_caption_candidate", "figure_caption"
        }:
            block["_rejected_legend"] = {
                "reason": "demoted_body_paragraph",
                "role": role,
                "seed_role": str(block.get("seed_role") or ""),
            }
            rejected_legends.append(block)
            continue
        is_validation_first_candidate = _is_validation_first_legend_candidate(block)
        if role in ("figure_caption", "figure_caption_candidate") or is_validation_first_candidate:
            text = str(block.get("text", "") or "")

            # PDF prefix recovery: restore "Figure N" heading missed by OCR
            # Must run BEFORE the zone/style filter that checks _extract_figure_number()
            if page_pdf_lines_by_page and _extract_figure_number(text) is None:
                recovered = _recover_figure_heading_prefix(block, page_pdf_lines_by_page)
                if recovered:
                    block["text"] = recovered
                    text = recovered
            raw_label = str(block.get("raw_label") or "")
            rotated_orientation_prematch = (
                role == "figure_caption_candidate"
                and raw_label == "vision_footnote"
                and _caption_has_rotated_text(block)
                and _looks_like_figure_description_opening(text)
            )
            if role == "figure_caption_candidate" and (
                (str(block.get("zone") or "") == "body_zone"
                 and _extract_figure_number(block.get("text", "")) is None)  # skips recovery-rescued captions
                or (
                    str(block.get("zone") or "") != "display_zone"
                    and str(block.get("style_family") or "") != "legend_like"
                    and _looks_like_figure_narrative_prose(block.get("text", ""))
                    and _extract_figure_number(block.get("text", "")) is None
                )
            ):
                if rotated_orientation_prematch:
                    block["_rotated_caption_prematch"] = True
                    legends.append(block)
                else:
                    # Vision-footnote figure descriptions: add to rejected_legends
                    # so synthetic vector fallback can match them to unmatched assets.
                    if raw_label == "vision_footnote":
                        block["_rejected_legend"] = {
                            "reason": "vision_footnote_body_zone",
                            "role": role,
                            "raw_label": raw_label,
                        }
                        rejected_legends.append(block)
                continue
            if not _is_formal_legend(text, block, page_width):
                if rotated_orientation_prematch:
                    block["_rotated_caption_prematch"] = True
                    legends.append(block)
                else:
                    block["caption_score"] = score_figure_caption(
                        block,
                        nearby_media=False,
                        caption_style_match=False,
                        body_prose_likelihood=_looks_like_inline_figure_mention(block.get("text", ""), block),
                    )
                    rejected_legends.append(block)
            else:
                if _is_previous_page_legend_locator(block):
                    figure_locators.append(block)
                else:
                    legends.append(block)
        elif role == "figure_asset":
            assets.append(block)
        elif role == "media_asset":
            raw_label = str(block.get("raw_label", "")).strip()
            if (
                raw_label in {"image", "chart", "figure_title", "figure"}
                or not raw_label
                or raw_label == "table"
                and "<img" in str(block.get("text") or "").lower()
            ):
                assets.append(block)

    # --- P3A: annotate asset family hints ---
    for asset in assets:
        raw_label = str(asset.get("raw_label", "")).strip().lower()
        if raw_label in {"image", "chart", "figure_title", "figure"}:
            asset["asset_family_hint"] = "figure_like"
            asset["asset_family_confidence"] = 0.70
            asset["asset_family_evidence"] = [f"raw_label:{raw_label}"]
        elif raw_label == "table":
            asset["asset_family_hint"] = "table_like"
            asset["asset_family_confidence"] = 0.70
            asset["asset_family_evidence"] = ["raw_label:table"]
        else:
            asset["asset_family_hint"] = "ambiguous"
            asset["asset_family_confidence"] = 0.35
            asset["asset_family_evidence"] = ["no_label_signal"]

    numbered_legends = [leg for leg in legends if _extract_figure_number(leg.get("text", "")) is not None]
    unnumbered_legends = [leg for leg in legends if _extract_figure_number(leg.get("text", "")) is None]
    ordered_legends = numbered_legends + unnumbered_legends
    bundle_source_legend_ids = _identify_bundle_source_legend_ids(numbered_legends, assets)
    legend_sort_order = {
        (int(legend.get("page", 0) or 0), str(legend.get("block_id", ""))): index
        for index, legend in enumerate(ordered_legends)
    }

    # Deduplicate numbered legends by family, but treat caption-list / bundle-source
    # pages as lower-priority duplicates when a stronger real legend instance exists.
    _dedup_map: dict[tuple[str, int], dict] = {}
    _same_number_distinct_keys: set[tuple[str, int, int, str]] = set()
    for legend in ordered_legends:
        text = legend.get("text", "")
        fn = _extract_figure_number(text)
        if fn is None:
            continue
        ns = _extract_figure_namespace(text)
        key = (ns, fn)
        if key not in _dedup_map:
            _dedup_map[key] = legend
        else:
            existing = _dedup_map[key]
            existing_body = _normalized_caption_body(str(existing.get("text", "")))
            new_body = _normalized_caption_body(text)
            existing_is_bundle = str(existing.get("block_id", "")) in bundle_source_legend_ids
            new_is_bundle = str(legend.get("block_id", "")) in bundle_source_legend_ids

            # Always determine winner/loser via dedup priority
            if _legend_dedup_priority(
                legend,
                bundle_source_legend_ids=bundle_source_legend_ids,
                assets=assets,
            ) > _legend_dedup_priority(
                existing,
                bundle_source_legend_ids=bundle_source_legend_ids,
                assets=assets,
            ):
                winner, loser = legend, existing
            else:
                winner, loser = existing, legend

            if (
                existing_body
                and new_body
                and existing_body != new_body
                and not existing_is_bundle
                and not new_is_bundle
            ):
                _dedup_map[key] = winner
                _same_number_distinct_keys.add(
                    (ns, fn, int(loser.get("page", 0) or 0), str(loser.get("block_id", "")))
                )
            else:
                _dedup_map[key] = winner

    emitted_winner_keys: set[tuple[str, int]] = set()
    deduped_legends: list[dict] = []
    deduped_legend_ids: list[dict] = []
    for legend in ordered_legends:
        text = legend.get("text", "")
        fn = _extract_figure_number(text)
        if fn is not None:
            ns = _extract_figure_namespace(text)
            key = (ns, fn)
            _distinct_check = (
                ns,
                fn,
                int(legend.get("page", 0) or 0),
                str(legend.get("block_id", "")),
            )
            if _distinct_check in _same_number_distinct_keys:
                deduped_legends.append(legend)
                deduped_legend_ids.append(
                    {
                        "page": legend.get("page"),
                        "block_id": legend.get("block_id", ""),
                        "dedup_reason": "same_number_distinct_caption_text",
                    }
                )
                continue
            kept = _dedup_map[key]
            current_id = str(legend.get("block_id", ""))
            kept_id = str(kept.get("block_id", ""))
            current_page = int(legend.get("page", 0) or 0)
            kept_page = int(kept.get("page", 0) or 0)
            if key in emitted_winner_keys or current_id != kept_id or current_page != kept_page:
                deduped_legend_ids.append(
                    {
                        "page": legend.get("page"),
                        "block_id": legend.get("block_id", ""),
                        "dedup_reason": (
                            "bundle_source_duplicate_loser"
                            if str(legend.get("block_id", "")) in bundle_source_legend_ids
                            and str(kept.get("block_id", "")) != str(legend.get("block_id", ""))
                            else "duplicate_loser"
                        ),
                        "kept_block_id": kept.get("block_id", ""),
                        "kept_page": kept.get("page"),
                    }
                )
                if key in emitted_winner_keys:
                    continue
                if current_id != kept_id or current_page != kept_page:
                    emitted_winner_keys.add(key)
                    deduped_legends.append(kept)
                    continue
            emitted_winner_keys.add(key)
            deduped_legends.append(kept)
        else:
            deduped_legends.append(legend)
    deduped_legends.sort(
        key=lambda legend: (
            legend_sort_order.get((int(legend.get("page", 0) or 0), str(legend.get("block_id", ""))), 10**9),
            int(legend.get("page", 0) or 0),
            (legend.get("bbox") or [0, 0, 0, 0])[1],
            (legend.get("bbox") or [0, 0, 0, 0])[0],
        )
    )
    ordered_legends = deduped_legends

    candidate_groups = _build_candidate_figure_groups_from_assets(
        assets,
        structured_blocks,
        ordered_legends,
        page_width=page_width,
    )

    composite_parent_candidates = _build_composite_parent_figure_groups_visual_only(
        candidate_groups,
        assets,
        structured_blocks,
        page_width,
    )

    # --- Dense composite parent construction before legend loop so
    # dense parents participate in arbitration ---
    _numbered_pages_early = {
        int(leg.get("page", 0) or 0)
        for leg in legends
        if _extract_figure_number(str(leg.get("text") or "")) is not None
    }
    _early_dense_parents = _build_dense_composite_parent_candidates(
        candidate_groups,
        [],
        _numbered_pages_early,
        page_width,
    )
    _parent_dict = {
        str(p.get("group_id", "")): p
        for p in composite_parent_candidates
        if str(p.get("group_id", ""))
    }
    for p in _early_dense_parents:
        pid = str(p.get("group_id", ""))
        if pid:
            _parent_dict[pid] = p
    composite_parent_candidates = list(_parent_dict.values())

    # --- Panel-title suppression: demote short unnumbered text inside visual
    # envelopes from formal legend matching on pages with numbered captions ---
    _numbered_pages = {
        int(leg.get("page", 0) or 0)
        for leg in legends
        if _extract_figure_number(str(leg.get("text") or "")) is not None
    }
    visual_envelopes: list[dict] = list(candidate_groups) + list(composite_parent_candidates)
    suppressed_caption_candidates: list[dict] = []
    remaining_legends: list[dict] = []
    for leg in legends:
        if _should_suppress_panel_title_candidate(
            leg,
            page_has_numbered_legend=int(leg.get("page", 0) or 0) in _numbered_pages,
            visual_envelopes=visual_envelopes,
            page_width=page_width,
        ):
            suppressed_caption_candidates.append(
                {
                    "block_id": leg.get("block_id", ""),
                    "page": leg.get("page"),
                    "text": leg.get("text", ""),
                    "suppression_reason": "panel_title_inside_visual_envelope",
                    "retained_as": "embedded_figure_text",
                }
            )
        else:
            remaining_legends.append(leg)
    legends = remaining_legends
    ordered_legends = [
        leg for leg in ordered_legends
        if not _should_suppress_panel_title_candidate(
            leg,
            page_has_numbered_legend=int(leg.get("page", 0) or 0) in _numbered_pages,
            visual_envelopes=visual_envelopes,
            page_width=page_width,
        )
    ]

    # Gate: suppress page_assets groups on pages with competing captions
    # so one big group doesn't swallow assets meant for multiple figures.
    # Only count legends with a real figure number — sub-panel labels
    # ("Tensile strength", "RND") are not captions and should not gate.
    _page_captions_for_gate: dict[int, set[str]] = {}
    for legend in ordered_legends:
        fid = legend.get("block_id")
        if fid and _extract_figure_number(str(legend.get("text") or "")) is not None:
            _page_captions_for_gate.setdefault(legend.get("page", 0), set()).add(str(fid))
    _competing_caption_pages = {p for p, ids in _page_captions_for_gate.items() if len(ids) > 1}
    candidate_groups = [
        g
        for g in candidate_groups
        if not (g.get("group_type") == "page_assets" and g.get("page") in _competing_caption_pages)
    ]
    _candidate_groups_by_id = {
        str(group.get("group_id", "")): group
        for group in candidate_groups
        if str(group.get("group_id", ""))
    }

    # --- Stage 1: page ledger, reservation ---
    _ledger = _build_page_ledger(ordered_legends, candidate_groups)
    _residual_ledger = _build_residual_ledger(
        ordered_legends, candidate_groups, competing_caption_pages=_competing_caption_pages
    )
    _legends_by_page: dict[int, list[dict]] = {}
    for leg in ordered_legends:
        _legends_by_page.setdefault(int(leg.get("page", 0) or 0), []).append(leg)
    _sidecar_pages: set[int] = set()
    for sp, spl in _legends_by_page.items():
        if len(_same_page_narrow_caption_column(spl, page_width)) >= 2:
            _sidecar_pages.add(sp)
    _reserved_legend_ids, _reserved_group_ids = _reserve_cross_page_objects(
        ordered_legends,
        candidate_groups,
        _residual_ledger,
        competing_caption_pages=_competing_caption_pages,
        sidecar_pages=_sidecar_pages,
    )
    # --- end Stage 1 reservation ---

    # Pre-compute page context for page_assets safety gate
    _page_blocks_by_page: dict[int, list[dict]] = {}
    for block in structured_blocks:
        bp = int(block.get("page", 0) or 0)
        _page_blocks_by_page.setdefault(bp, []).append(block)

    _page_height_by_page: dict[int, float] = {}
    for page, page_blocks_on_page in _page_blocks_by_page.items():
        explicit = max(
            (float(b.get("page_height") or 0)) for b in page_blocks_on_page
        )
        _page_height_by_page[page] = explicit if explicit > 0 else _estimate_page_height(page_blocks_on_page)

    _numbered_legend_count_by_page: dict[int, int] = {}
    for leg in ordered_legends:
        lp = int(leg.get("page", 0) or 0)
        if _extract_figure_number(str(leg.get("text") or "")) is not None:
            _numbered_legend_count_by_page[lp] = _numbered_legend_count_by_page.get(lp, 0) + 1

    page_caption_index = _formal_figure_caption_blocks(structured_blocks)
    for legend in ordered_legends:
        legend_id = str(legend.get("block_id", ""))
        legend_reserved_for_cross_page = (int(legend.get("page", 0) or 0), legend_id) in _reserved_legend_ids
        legend_page = legend.get("page", 0)
        legend_text = str(legend.get("text") or "")
        ns = _extract_figure_namespace(legend_text)
        fig_num = _extract_figure_number(legend_text)
        # Text may be empty (stored as [] in raw block) but marker_signature
        # still carries the figure number.
        if fig_num is None:
            ms = legend.get("marker_signature") or {}
            if ms.get("type") == "figure_number":
                try:
                    fig_num = int(float(ms.get("number", 0) or 0))
                except (ValueError, TypeError):
                    pass
        is_validation_first_candidate = _is_validation_first_legend_candidate(legend)
        is_weak_truncated = _is_insufficient_legend_evidence(legend)

        body_prose_likelihood = _looks_like_inline_figure_mention(legend_text, legend)

        caption_score = score_figure_caption(
            legend,
            nearby_media=any(a.get("page", 0) == legend_page for a in assets),
            caption_style_match=_caption_style_match(legend, structured_blocks),
            body_prose_likelihood=body_prose_likelihood,
        )
        if legend.get("_rotated_caption_prematch"):
            caption_score = dict(caption_score)
            caption_score["score"] = max(float(caption_score.get("score", 0.0) or 0.0), 0.82)
            caption_score.setdefault("evidence", []).append("rotated_caption_prematch")
            if caption_score.get("decision") == "rejected":
                caption_score["decision"] = "candidate"


        candidates = []
        anchor_supported = _has_anchor_supported_legend_context(legend)
        caption_text_supported = _has_strong_explicit_caption_text(legend)
        family_supported = is_validation_first_candidate and str(legend.get("style_family") or "") == "legend_like"
        zone_supported = is_validation_first_candidate and str(legend.get("zone") or "") in {
            "body_zone",
            "display_zone",
        }

        # --- P1B: composite parent arbitration (before same-page candidate scan) ---
        _parent_accepted = False
        _parent_consumed_assets: list[dict] = []
        _parent_consumed_asset_ids: list[str] = []

        if fig_num is not None:
            _page_parents = [
                cp for cp in composite_parent_candidates
                if cp.get("page") == legend_page
                and not cp.get("ownership_consumed", False)
                and not (
                    cp.get("parent_subtype") == "dense_composite"
                    and len(_page_captions_for_gate.get(legend_page, set())) > 1
                )
            ]
            if _page_parents:
                # Prefer the parent with highest confidence
                _page_parents.sort(key=lambda cp: cp.get("parent_confidence", 0), reverse=True)
                _best_parent = _page_parents[0]
                _parent_conf = _best_parent.get("parent_confidence", 0)

                # Competing caption veto: if this page has >1 numbered legend,
                # do not promote a composite parent.
                _page_num_legends = _page_captions_for_gate.get(legend_page, set())
                _has_competing_caption = len(_page_num_legends) > 1

                _matching_child_groups = [
                    _candidate_groups_by_id[child_gid]
                    for child_gid in _best_parent.get("child_group_ids", [])
                    if child_gid in _candidate_groups_by_id
                    and str(
                        (
                            _candidate_groups_by_id[child_gid].get("assist", {}) or {}
                        ).get("best_caption_band_id") or ""
                    )
                    == legend_id
                ]
                _is_dense = _best_parent.get("parent_subtype") == "dense_composite"
                _all_child_groups = [
                    _candidate_groups_by_id[child_gid]
                    for child_gid in _best_parent.get("child_group_ids", [])
                    if child_gid in _candidate_groups_by_id
                ]
                # For dense parents with a single caption, consume all child groups.
                # With competing captions, keep caption-band scoping.
                _effective_child_groups = (
                    _all_child_groups if (_is_dense and not _has_competing_caption)
                    else (_matching_child_groups or _all_child_groups)
                )
                _effective_child_group_ids = [
                    str(group.get("group_id", "")) for group in _effective_child_groups if str(group.get("group_id", ""))
                ]
                _effective_asset_ids = list(
                    dict.fromkeys(
                        bid
                        for group in _effective_child_groups
                        for bid in group.get("asset_block_ids", [])
                    )
                )
                _band_scoped_parent = len(_matching_child_groups) >= 2
                _dense_parent_unresolved_count = int(_best_parent.get("unresolved_child_count", 0) or 0)
                _dense_parent_fragment_count = int(_best_parent.get("fragment_count", 0) or 0)
                _dense_parent_single_group_ok = (
                    _best_parent.get("parent_subtype") == "dense_composite"
                    and len(_effective_child_groups) == 1
                    and _dense_parent_fragment_count >= 4
                )

                if (
                    _parent_conf >= 0.60
                    and (not _has_competing_caption or _band_scoped_parent)
                    and (len(_effective_child_groups) >= 2 or _dense_parent_single_group_ok)
                ):
                    _parent_accepted = True
                    _parent_consumed_asset_ids = _effective_asset_ids
                    _best_parent["ownership_consumed"] = True

                    for bid in _parent_consumed_asset_ids:
                        asset = next((a for a in assets if a.get("block_id") == bid), None)
                        if asset:
                            _parent_consumed_assets.append(_project_asset_record(asset))
                            ownership.mark_assets_owned(
                                [(int(asset.get("page", 0) or 0), bid)],
                                owner_id=str(legend.get("block_id", "")),
                                owner_family="figure",
                            )

                    # Consume child groups
                    for child_gid in _effective_child_group_ids:
                        used_group_ids.add(child_gid)

        if _parent_accepted:
            _parent_fig_id = _format_figure_id(ns, fig_num)
            matched_figures.append(
                {
                    "figure_id": _parent_fig_id,
                    "figure_namespace": ns,
                    "legend_block_id": legend.get("block_id", ""),
                    "page": legend_page,
                    "text": str(legend.get("text", "")),
                    "figure_number": fig_num,
                    "matched_assets": _parent_consumed_assets,
                    "asset_block_ids": _parent_consumed_asset_ids,
                    "bridge_block_ids": [],
                    "caption_score": caption_score,
                    "match_score": {
                        "score": _parent_conf,
                        "decision": "matched",
                        "evidence": ["composite_parent"],
                    },
                    "confidence": _parent_conf,
                    "flags": ["composite_parent_match"],
                    "legend_page": legend_page,
                    "asset_pages": [legend_page],
                    "settlement_type": "composite_parent",
                }
            )
            unmatched_legends = [l for l in unmatched_legends if l.get("block_id") != legend.get("block_id")]
            continue  # skip normal same-page candidate scan for this legend
        # --- end P1B composite parent arbitration ---

        for gi, group in enumerate(candidate_groups):
            if group.get("page") != legend_page:
                continue
            group_id = str(group.get("group_id", ""))
            assist = group.get("assist", {}) or {}
            assist_band_id = str(assist.get("best_caption_band_id") or "")
            if (
                not legend_reserved_for_cross_page
                and legend_page in _competing_caption_pages
                and assist_band_id
                and assist_band_id != legend_id
            ):
                continue
            g_asset_block_ids = set(group.get("asset_block_ids", []))
            g_page = group.get("page", 0)
            g_qual = {(g_page, bid) for bid in g_asset_block_ids}
            group_reserved_for_cross_page = group_id in _reserved_group_ids
            if not group_reserved_for_cross_page and not ownership.can_consume_assets(list(g_qual)):
                continue
            # --- P3B/P3C: strong table-like veto in figure matcher ---
            _group_asset_ids = group.get("asset_block_ids", [])
            _strong_table_like = False
            if _group_asset_ids:
                _hint_map = {str(a.get("block_id", "")): a for a in assets}
                _table_like_count = sum(
                    1 for bid in _group_asset_ids
                    if _hint_map.get(str(bid), {}).get("asset_family_hint") == "table_like"
                    and float(_hint_map.get(str(bid), {}).get("asset_family_confidence", 0) or 0) >= 0.70
                )
                if _table_like_count >= len(_group_asset_ids):
                    _strong_table_like = True
            if _strong_table_like:
                continue
            # --- end P3B/P3C veto ---
            match_score = _score_legend_to_group(
                legend,
                group,
                caption_score=caption_score,
                page_width=page_width,
                page_blocks=_page_blocks_by_page.get(legend_page, []),
                page_height=_page_height_by_page.get(legend_page, 0.0),
                page_numbered_legend_count=_numbered_legend_count_by_page.get(legend_page, 0),
                anchor_supported=anchor_supported,
                caption_text_supported=caption_text_supported,
                family_supported=family_supported,
                zone_supported=zone_supported,
            )
            if match_score["decision"] != "rejected":
                hypothesis = _make_local_pairing_hypothesis(
                    legend,
                    group,
                    mode=_infer_local_pairing_mode(legend, group, page_width=page_width),
                    local_score=match_score.get("score", 0.0),
                    evidence=match_score.get("evidence", []),
                )
                if legend_reserved_for_cross_page or group_id in _reserved_group_ids:
                    _mark_hypothesis_conflict(hypothesis, "reserved_same_page_commit_deferred")
                local_pairing_hypotheses.append(hypothesis)
                candidates.append((gi, group, match_score))
        candidates.sort(key=lambda item: item[2]["score"], reverse=True)

        matched_assets = []
        region_match = None
        ambiguous = False
        defer_reserved_same_page_commit = False

        if candidates:
            top_score = candidates[0][2]["score"]
            close = [item for item in candidates if top_score - item[2]["score"] < 0.15]
            if top_score < 0.4:
                matched_assets = []
            elif len(close) > 1:
                close_sides = {_asset_vertical_side(legend, g) for _, g, _ in close}
                if "above" in close_sides and "below" in close_sides and fig_num is not None:
                    # If one candidate is the page_assets group (all assets),
                    # don't tie-break — it's the canonical match.
                    page_assets_candidate = next(
                        (item for item in close if item[1].get("group_type") == "page_assets"), None
                    )
                    if page_assets_candidate is not None:
                        close = [page_assets_candidate]
                    else:
                        # Caption sandwiched between two asset groups:
                        # prefer above (standard: image above, caption below).
                        above_only = [item for item in close if _asset_vertical_side(legend, item[1]) == "above"]
                        if above_only:
                            close = above_only
                        else:
                            ambiguous_figures.append(
                                {
                                    "legend_block_id": legend.get("block_id", ""),
                                    "page": legend_page,
                                    "text": legend_text,
                                    "figure_number": fig_num,
                                    "caption_score": caption_score,
                                    "candidates": [
                                        {
                                            "asset_block_id": g.get("media_blocks", [{}])[0].get("block_id", ""),
                                            "group_type": g.get("group_type", ""),
                                            "match_score": s,
                                        }
                                        for _, g, s in close
                                    ],
                                    "hold_reason": "close_asset_tie",
                                }
                            )
                            ambiguous = True
                            matched_assets = []
                            close = []
                if not close:
                    pass
                else:
                    legend_bb = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
                    lcx = (legend_bb[0] + legend_bb[2]) / 2 if len(legend_bb) >= 4 else 0
                    best = close[0]
                    best_delta = abs(
                        lcx
                        - (
                            (
                                best[1].get("cluster_bbox", [0, 0, 0, 0])[0]
                                + best[1].get("cluster_bbox", [0, 0, 0, 0])[2]
                            )
                            / 2
                        )
                    )
                    best_orig_score = best[2]["score"]
                    for ci, cg, cs in close:
                        cb = cg.get("cluster_bbox", [0, 0, 0, 0])
                        acx = (cb[0] + cb[2]) / 2 if len(cb) >= 4 else 0
                        delta = abs(lcx - acx)
                        ca_col_ok = delta + 20 < best_delta and cs["score"] >= best_orig_score - 0.01
                        if ca_col_ok:
                            best = (ci, cg, cs)
                            best_delta = delta
                    if best[2].get("decision") == "matched":
                        best_gi, best_group, best_score = best
                        if legend_reserved_for_cross_page or str(best_group.get("group_id", "")) in _reserved_group_ids:
                            defer_reserved_same_page_commit = True
                            matched_assets = []
                            region_match = None
                        else:
                            matched_assets = best_group.get("media_blocks", [])
                            g_page = best_group.get("page", 0)
                            ownership.match_group(best_group, owner_id=str(legend.get("block_id", "")), owner_family="figure")
                            matched_assets = _expand_matched_assets_locally(
                                legend,
                                matched_assets,
                                assets,
                                ownership,
                                page_caption_index.get(g_page, []),
                            )
                            region_match = {
                                "media_blocks": matched_assets,
                                "match_score": best_score,
                                "group_type": best_group.get("group_type", ""),
                                "group_evidence": best_group.get("group_evidence", []),
                            }
                            if "rotation_correction_deg" in best_score:
                                region_match["rotation_correction_deg"] = best_score["rotation_correction_deg"]
                                region_match["cluster_bbox"] = best_score.get("rotation_union_bbox", [0, 0, 0, 0])
                            elif len(matched_assets) > 1:
                                region_match["cluster_bbox"] = best_group.get("cluster_bbox", [0, 0, 0, 0])
                    else:
                        if (
                            fig_num is None
                            and str(legend.get("role") or "") in ("figure_caption", "figure_caption_candidate")
                            and len(legend_text) < 80
                        ):
                            unmatched_legends.append(legend)
                            continue
                        ambiguous_figures.append(
                            {
                                "legend_block_id": legend.get("block_id", ""),
                                "page": legend_page,
                                "caption_score": caption_score,
                                "figure_number": fig_num,
                                "candidates": [
                                    {
                                        "asset_block_id": g.get("media_blocks", [{}])[0].get("block_id", ""),
                                        "group_type": g.get("group_type", ""),
                                        "match_score": s,
                                    }
                                    for _, g, s in close
                                ],
                                "hold_reason": "close_unconfirmed_match",
                            }
                        )
                        ambiguous = True
                        matched_assets = []
            else:
                best_gi, best_group, best_score = candidates[0]
                if best_score["decision"] == "matched":
                    if legend_reserved_for_cross_page or str(best_group.get("group_id", "")) in _reserved_group_ids:
                        defer_reserved_same_page_commit = True
                        matched_assets = []
                        region_match = None
                    else:
                        matched_assets = best_group.get("media_blocks", [])
                        g_page = best_group.get("page", 0)
                        ownership.match_group(best_group, owner_id=str(legend.get("block_id", "")), owner_family="figure")
                        matched_assets = _expand_matched_assets_locally(
                            legend,
                            matched_assets,
                            assets,
                            ownership,
                            page_caption_index.get(g_page, []),
                        )
                        region_match = {
                            "media_blocks": matched_assets,
                            "match_score": best_score,
                            "group_type": best_group.get("group_type", ""),
                            "group_evidence": best_group.get("group_evidence", []),
                        }
                        if "rotation_correction_deg" in best_score:
                            region_match["rotation_correction_deg"] = best_score["rotation_correction_deg"]
                            region_match["cluster_bbox"] = best_score.get("rotation_union_bbox", [0, 0, 0, 0])
                        elif len(matched_assets) > 1:
                            region_match["cluster_bbox"] = best_group.get("cluster_bbox", [0, 0, 0, 0])
                else:
                    if fig_num is None and str(legend.get("role") or "") in (
                        "figure_caption",
                        "figure_caption_candidate",
                    ):
                        unmatched_legends.append(legend)
                        continue
                    ambiguous_figures.append(
                        {
                            "legend_block_id": legend.get("block_id", ""),
                            "page": legend_page,
                            "caption_score": caption_score,
                            "figure_number": fig_num,
                            "candidates": [
                                {
                                    "asset_block_id": best_group.get("media_blocks", [{}])[0].get("block_id", ""),
                                    "group_type": best_group.get("group_type", ""),
                                    "match_score": best_score,
                                }
                            ],
                            "hold_reason": "single_unconfirmed_match",
                        }
                    )
                    ambiguous = True
                    ambiguous = True

        is_legend_only = len(matched_assets) == 0

        if defer_reserved_same_page_commit:
            continue

        if caption_score.get("score", 0.0) < 0.4:
            unmatched_legends.append(legend)
            continue

        if is_weak_truncated and is_validation_first_candidate and is_legend_only:
            held_figures.append(
                {
                    "figure_id": f"held_figure_{len(held_figures) + 1:03d}",
                    "legend_block_id": legend.get("block_id", ""),
                    "page": legend_page,
                    "text": legend_text,
                    "figure_number": fig_num,
                    "hold_reason": "insufficient_legend_evidence",
                    "zone": legend.get("zone"),
                    "style_family": legend.get("style_family"),
                    "marker_signature": legend.get("marker_signature") or {},
                    "caption_score": caption_score,
                }
            )
            unmatched_legends.append(legend)
            continue

        # When multiple truncated legends ("Fig. 4" only) share a page,
        # they are sub-panel labels on a multi-figure gallery — skip them
        # and let the shared caption claim all assets.
        if is_weak_truncated:
            page_truncated_count = sum(
                1
                for leg in ordered_legends
                if leg.get("page", 0) == legend_page and _is_insufficient_legend_evidence(leg)
            )
            if page_truncated_count >= 2:
                unmatched_legends.append(legend)
                continue
            # Single truncated legend on page: match normally with candidates
            if is_legend_only:
                weak_candidates = [
                    {
                        "asset_block_id": g.get("media_blocks", [{}])[0].get("block_id", ""),
                        "group_type": g.get("group_type", ""),
                        "match_score": s,
                    }
                    for _, g, s in (candidates or [])
                ]
                ambiguous_figures.append(
                    {
                        "legend_block_id": legend.get("block_id", ""),
                        "page": legend_page,
                        "text": legend_text,
                        "figure_number": fig_num,
                        "caption_score": caption_score,
                        "candidates": weak_candidates,
                        "hold_reason": "ambiguous_truncated_legend",
                        "zone": legend.get("zone"),
                        "style_family": legend.get("style_family"),
                        "marker_signature": legend.get("marker_signature") or {},
                    }
                )
                unmatched_legends.append(legend)
                continue
            # Single truncated legend with matched assets — proceed to confirmation

        if is_legend_only:
            if legend_reserved_for_cross_page:
                continue
            if fig_num is None and str(legend.get("role") or "") in ("figure_caption_candidate", "figure_caption"):
                unmatched_legends.append(legend)
                continue
            weak_entry = {
                "legend_block_id": legend.get("block_id", ""),
                "page": legend_page,
                "text": legend_text,
                "figure_number": fig_num,
                "caption_score": caption_score,
                "candidates": [],
                "hold_reason": ("ambiguous_truncated_legend" if is_weak_truncated else "no_asset_match"),
                "zone": legend.get("zone"),
                "style_family": legend.get("style_family"),
                "marker_signature": legend.get("marker_signature") or {},
            }
            if not ambiguous:
                ambiguous_figures.append(weak_entry)
            unmatched_legends.append(legend)
            continue

        fig_id = _format_figure_id(ns, fig_num) if fig_num else f"figure_unknown_{len(matched_figures):03d}"
        match_score = (
            region_match["match_score"]
            if region_match is not None
            else {
                "score": 0.0,
                "decision": "rejected",
                "evidence": ["missing_region_match"],
            }
        )
        entry = {
            "figure_id": fig_id,
            "figure_namespace": ns,
            "legend_block_id": legend.get("block_id", ""),
            "page": legend_page,
            "text": legend_text,
            "figure_number": fig_num,
                "matched_assets": [_project_asset_record(a) for a in matched_assets],
            "group_type": region_match.get("group_type", "") if region_match is not None else "",
            "group_evidence": region_match.get("group_evidence", []) if region_match is not None else [],
            "confidence": match_score["score"],
            "match_score": match_score,
            "flags": [],
            "caption_score": caption_score,
            "legend_page": legend_page,
            "asset_pages": sorted({int(a.get("page", 0) or 0) for a in matched_assets}) or [legend_page],
            "settlement_type": "same_page_rotated" if region_match and region_match.get("rotation_correction_deg") else "same_page",
        }
        if region_match and region_match.get("rotation_correction_deg"):
            entry["rotation_correction_deg"] = region_match["rotation_correction_deg"]
            entry["cluster_bbox"] = region_match.get("cluster_bbox", [0, 0, 0, 0])
        local_bridges = _collect_bridge_blocks(int(legend_page or 0))
        entry["asset_block_ids"] = [str(a.get("block_id", "")) for a in matched_assets if a.get("block_id")]
        entry["bridge_block_ids"] = [str(b.get("block_id", "")) for b in local_bridges if b.get("block_id")]
        if "cluster_bbox" not in entry and len(matched_assets) > 1:
            entry["cluster_bbox"] = _cluster_bbox([a.get("bbox", [0, 0, 0, 0]) for a in matched_assets])
            # Push cluster_bbox top down past figure_inner_text blocks (panel labels)
            # to exclude (A), (B) etc. from the cropped figure image.
            leg_page = int(legend_page or 0)
            for ib in structured_blocks:
                if int(ib.get("page", 0) or 0) != leg_page or ib.get("role") != "figure_inner_text":
                    continue
                ib_bbox = ib.get("bbox") or ib.get("block_bbox") or [0, 0, 0, 0]
                cb = entry["cluster_bbox"]
                if len(ib_bbox) >= 4 and len(cb) >= 4:
                    # Horizontal overlap: inner text sits in the figure's column
                    x_overlap = ib_bbox[0] < cb[2] and ib_bbox[2] > cb[0]
                    # Text starts above cluster top and extends into it
                    is_above = ib_bbox[1] < cb[1] and ib_bbox[3] > cb[1]
                    if x_overlap and is_above:
                        cb[1] = max(cb[1], ib_bbox[3])
        matched_figures.append(entry)

    for _i, asset in enumerate(assets):
        asset_page = asset.get("page")
        asset_bid = asset.get("block_id", "")
        if not asset_bid or (asset_page, asset_bid) not in used_asset_page_ids:
            unmatched_assets.append(asset)

    # --- Stage 1: primary cross-page settlement before legacy fallback ---
    _settle_cross_page_reserved_objects(
        _reserved_legend_ids,
        _reserved_group_ids,
        ordered_legends,
        candidate_groups,
        structured_blocks,
        matched_figures,
        ambiguous_figures,
        unmatched_legends,
        used_group_ids,
        used_asset_page_ids,
        ownership,
        residual_ledger=_residual_ledger,
        competing_caption_pages=_competing_caption_pages,
        page_width=page_width,
    )
    # Rebuild unmatched_assets after cross-page settlement consumed some
    unmatched_assets.clear()
    for _a in assets:
        _ap = _a.get("page", 0)
        _bid = _a.get("block_id", "")
        if _bid and (_ap, _bid) not in used_asset_page_ids:
            unmatched_assets.append(_a)
    # Handle failed reserved groups: multi-asset -> unresolved_clusters, single -> unmatched_assets
    _failed_reserved_groups = [
        g
        for g in candidate_groups
        if str(g.get("group_id", "")) in _reserved_group_ids and str(g.get("group_id", "")) not in used_group_ids
    ]
    for _fg in _failed_reserved_groups:
        _fg_type = _fg.get("group_type", "")
        _fg_page = int(_fg.get("page", 0) or 0)
        _fg_bids = [str(b.get("block_id", "")) for b in _fg.get("media_blocks", []) if b.get("block_id")]
        if _fg_type == "single_asset" or len(_fg.get("media_blocks", [])) <= 1:
            # single-asset reserved group failure -> remain in unmatched_assets
            pass
        else:
            # multi-asset reserved group failure -> unresolved_clusters
            unresolved_clusters.append(
                {
                    "cluster_id": f"unresolved_cluster_{len(unresolved_clusters) + 1:03d}",
                    "media_block_ids": _fg_bids,
                    "cluster_bbox": _fg.get("cluster_bbox", [0, 0, 0, 0]),
                    "page": _fg_page,
                    "hold_reason": "reserved_cross_page_no_valid_legend",
                }
            )
            # Remove these bids from unmatched_assets
            unmatched_assets = [
                ua
                for ua in unmatched_assets
                if str(ua.get("block_id", "")) not in _fg_bids or ua.get("page", 0) != _fg_page
            ]
    # --- end Stage 1 cross-page settlement ---

    # Sidecar fallback: for pages with narrow same-column formal captions,
    # override normal figure matching with caption-band partitioning.
    # The normal spatial matcher cannot reliably assign assets to narrow
    # sidecar captions -- the visible image/caption pairing is column-based,
    # not gap/overlap based.
    # Uses the `deduped_legends` list (already filtered through the full multi-evidence
    # legend recognition pipeline + figure-number dedup) instead of raw caption index.
    _sidecar_by_page: dict[int, list[dict]] = {}
    for leg in deduped_legends:
        _sidecar_by_page.setdefault(int(leg.get("page", 0) or 0), []).append(leg)
    for sidecar_page, sidecar_legends in _sidecar_by_page.items():
        narrow_set = _same_page_narrow_caption_column(sidecar_legends, page_width)
        if len(narrow_set) < 2:
            continue
        # Trigger sidecar when any narrow-caption legend is unresolved, or
        # when the normal spatial matching violates vertical ordering (top
        # caption should own top assets, bottom caption bottom assets).
        nid_set = {str(cap.get("block_id", "")) for cap in narrow_set}
        page_unmatched = any(str(l.get("block_id", "")) in nid_set for l in unmatched_legends)
        page_ambiguous = any(str(af.get("legend_block_id", "")) in nid_set for af in ambiguous_figures)

        def _median_y(items: list[dict]) -> float:
            ys = sorted((a.get("bbox") or [0, 0, 0, 0])[1] for a in items)
            return float(ys[len(ys) // 2]) if ys else 0.0

        page_narrow_matched = [mf for mf in matched_figures if str(mf.get("legend_block_id", "")) in nid_set]
        page_unresolved_legend_ids = {
            str(item.get("block_id", ""))
            for item in unmatched_legends
            if str(item.get("block_id", "")) in nid_set
        } | {
            str(item.get("legend_block_id", ""))
            for item in ambiguous_figures
            if str(item.get("legend_block_id", "")) in nid_set
        }
        protected_by_legend_id = {
            str(mf.get("legend_block_id", "")): mf
            for mf in page_narrow_matched
            if str(mf.get("legend_block_id", ""))
            and _has_protected_figure_ownership(mf, unresolved_legend_ids=page_unresolved_legend_ids)
        }
        protected_asset_page_ids = {
            (int(a.get("page", mf.get("page", sidecar_page)) or 0), str(a.get("block_id", "")))
            for mf in protected_by_legend_id.values()
            for a in mf.get("matched_assets", [])
            if a.get("block_id") not in (None, "")
        }
        reclaimable_asset_page_ids = {
            (int(a.get("page", mf.get("page", sidecar_page)) or 0), str(a.get("block_id", "")))
            for mf in page_narrow_matched
            for a in mf.get("matched_assets", [])
            if a.get("block_id") not in (None, "")
            and str(mf.get("legend_block_id", "")) not in protected_by_legend_id
        }
        violation = len(page_narrow_matched) != len(narrow_set)
        if not violation and len(page_narrow_matched) > 1:
            ordered = sorted(page_narrow_matched, key=lambda mf: int(mf.get("figure_number", 0) or 0))
            asset_ys = [_median_y(mf.get("matched_assets", [])) for mf in ordered]
            for i in range(len(asset_ys) - 1):
                if not (asset_ys[i] <= asset_ys[i + 1]):
                    violation = True
                    break
        if not (page_unmatched or page_ambiguous or violation):
            continue
        page_assets_list = [a for a in assets if a.get("page") == sidecar_page and not a.get("_non_body_media")]
        if not page_assets_list:
            continue
        hypothesis_protected_asset_page_ids = {
            tuple(asset_id)
            for hypothesis in local_pairing_hypotheses
            if hypothesis.get("legend_block_id") not in nid_set
            and hypothesis.get("mode") in {"caption_below", "caption_above"}
            and float(hypothesis.get("local_score", 0.0) or 0.0) >= 0.7
            for asset_id in hypothesis.get("would_consume_asset_ids", [])
        }
        grouped_asset_page_ids = _grouped_asset_page_ids(candidate_groups)
        sidecar_page_height = float(
            max((b.get("bbox") or [0, 0, 0, 0])[3] for b in structured_blocks if b.get("page") == sidecar_page) or 1600
        )
        band_map = _partition_assets_by_caption_bands(narrow_set, page_assets_list, sidecar_page_height)
        sidecar_promoted: list[dict] = []
        sidecar_consumed_ids: set[tuple] = set()
        page_narrow_matched_by_legend = {
            str(mf.get("legend_block_id", "")): mf
            for mf in page_narrow_matched
            if str(mf.get("legend_block_id", ""))
        }
        for cap in narrow_set:
            lid = str(cap.get("block_id", ""))
            cap_text = str(cap.get("text") or "")
            fig_num = _extract_figure_number(cap_text)
            cap_ns = _extract_figure_namespace(cap_text)
            current_match = page_narrow_matched_by_legend.get(lid)
            cap_is_unresolved = any(str(l.get("block_id", "")) == lid for l in unmatched_legends) or any(
                str(af.get("legend_block_id", "")) == lid for af in ambiguous_figures
            )
            if lid in protected_by_legend_id:
                continue
            if not violation and current_match is not None and not cap_is_unresolved:
                continue
            raw_band_assets = [
                asset
                for asset in band_map.get(lid, [])
                if (int(asset.get("page", 0) or 0), str(asset.get("block_id", ""))) not in protected_asset_page_ids
                and (int(asset.get("page", 0) or 0), str(asset.get("block_id", ""))) not in hypothesis_protected_asset_page_ids
            ]
            # In sidecar mode _partition_assets_by_caption_bands is the
            # ownership unit.  Row-coupled geometry is too strict for
            # AJR-style caption-column layouts and can drop far-column
            # panels within the same caption band.
            band_assets = raw_band_assets
            if not band_assets:
                continue
            eligible_asset_ids = _fallback_eligible_asset_page_ids(
                [
                    (int(asset.get("page", 0) or 0), str(asset.get("block_id", "")))
                    for asset in band_assets
                    if asset.get("block_id") not in (None, "")
                ],
                used_asset_page_ids=used_asset_page_ids - reclaimable_asset_page_ids,
                blocked_asset_page_ids=set(),
                grouped_asset_page_ids=grouped_asset_page_ids,
                allow_grouped=True,
            )
            if not eligible_asset_ids:
                continue
            eligible_asset_id_set = set(eligible_asset_ids)
            band_assets = [
                asset
                for asset in band_assets
                if (int(asset.get("page", 0) or 0), str(asset.get("block_id", ""))) in eligible_asset_id_set
            ]
            if not band_assets:
                continue
            for ba in band_assets:
                ap = ba.get("page", 0)
                bid = ba.get("block_id", "")
                if bid is not None:
                    sidecar_consumed_ids.add((ap, bid))
            fig_id = (
                _format_figure_id(cap_ns, fig_num)
                if fig_num
                else f"figure_sidecar_{len(matched_figures) + len(sidecar_promoted):03d}"
            )
            sidecar_entry = {
                "figure_id": fig_id,
                "legend_block_id": cap.get("block_id", ""),
                "page": sidecar_page,
                "text": cap_text,
                "figure_number": fig_num,
                "matched_assets": [
                    {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])} for a in band_assets
                ],
                "asset_block_ids": [str(a.get("block_id", "")) for a in band_assets if a.get("block_id") is not None],
                "group_type": "sidecar_partition",
                "group_evidence": ["same_page", "narrow_caption_column", "sidecar_fallback"],
                "confidence": 0.5,
                "match_score": {"score": 0.5, "decision": "matched", "evidence": ["sidecar_fallback"]},
                "flags": ["sidecar_match"],
                "caption_score": score_figure_caption(
                    cap, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
                ),
                "legend_page": sidecar_page,
                "asset_pages": [sidecar_page],
                "settlement_type": "sidecar",
            }
            local_pairing_hypotheses.append(
                _make_local_pairing_hypothesis(
                    cap,
                    {
                        "group_id": f"sidecar_partition:{sidecar_page}:{lid}",
                        "page": sidecar_page,
                        "media_blocks": band_assets,
                    },
                    mode="caption_sidecar",
                    local_score=0.5,
                    evidence=["same_row_alignment", "narrow_caption_column", "sidecar_fallback"],
                )
            )
            if len(band_assets) > 1:
                sidecar_entry["cluster_bbox"] = _cluster_bbox([a.get("bbox", [0, 0, 0, 0]) for a in band_assets])
            sidecar_promoted.append(sidecar_entry)
        if not sidecar_promoted:
            continue
        reclaimable_group_ids = {
            str(group.get("group_id", ""))
            for group in candidate_groups
            if str(group.get("group_id", ""))
            and all(
                aid in reclaimable_asset_page_ids
                for aid in [
                    _asset_page_id(group.get("page", 0), bid)
                    for bid in group.get("asset_block_ids", [])
                    if bid is not None
                ]
                if aid is not None
            )
        }
        for asset_id in reclaimable_asset_page_ids:
            used_asset_page_ids.discard(asset_id)
        for group_id in reclaimable_group_ids:
            used_group_ids.discard(group_id)
        promoted_legend_ids = {str(entry.get("legend_block_id", "")) for entry in sidecar_promoted}
        matched_figures = [
            mf for mf in matched_figures if str(mf.get("legend_block_id", "")) not in promoted_legend_ids
        ]
        for legend in list(legends):
            if str(legend.get("block_id", "")) in promoted_legend_ids:
                ambiguous_figures[:] = [
                    af
                    for af in ambiguous_figures
                    if str(af.get("legend_block_id", "")) != str(legend.get("block_id", ""))
                ]
                unmatched_legends[:] = [
                    ul for ul in unmatched_legends if str(ul.get("block_id", "")) != str(legend.get("block_id", ""))
                ]
        matched_figures.extend(sidecar_promoted)
        ownership.mark_assets_owned(list(sidecar_consumed_ids), owner_id=f"sidecar_page_{sidecar_page}", owner_family="figure")

    # Preproof legend-bundling: when a page packs 3+ figure captions
    # with zero same-page assets, match them 1:1 by page order to
    # subsequent pages that each hold unclaimed assets.
    if unmatched_legends and unmatched_assets:
        # ponytail: only multi-asset clusters are protected from bundle consumption;
        # single-asset groups on pages without same-page captions are orphans that
        # the bundle fallback should be allowed to consume.
        cluster_asset_page_ids = {
            (int(group.get("page", 0) or 0), str(bid))
            for group in candidate_groups
            if group.get("group_type") == "distance_cluster"
            for bid in group.get("asset_block_ids", [])
            if bid is not None
        }
        page_captions: dict[int, list[dict]] = {}
        for leg in unmatched_legends:
            cp = int(leg.get("page", 0) or 0)
            if _extract_figure_number(str(leg.get("text", ""))) is not None:
                page_captions.setdefault(cp, []).append(leg)
        for cp, caps in sorted(page_captions.items()):
            has_bundle_source = any(
                str(cap.get("block_id", "")) in bundle_source_legend_ids
                for cap in caps
            )
            if len(caps) < 3 and not has_bundle_source:
                continue
            page_has_assets = any(a.get("page", 0) == cp for a in unmatched_assets)
            if page_has_assets:
                continue
            caps_sorted = sorted(caps, key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
            # Collect subsequent pages with unclaimed assets and no captions
            asset_pages: dict[int, list[dict]] = {}
            for ast in unmatched_assets:
                ap = int(ast.get("page", 0) or 0)
                bid = ast.get("block_id", "")
                if (ap, str(bid)) in cluster_asset_page_ids:
                    continue
                if ap <= cp:
                    continue
                if bid and (ap, bid) in used_asset_page_ids:
                    continue
                asset_pages.setdefault(ap, []).append(ast)
            page_order = sorted(asset_pages.keys())
            # Validate: no body/table blocks between legend page and first asset page,
            # and each asset page is free of competing body/table text.
            _NON_PURE_ROLES = {
                "body_paragraph",
                "section_heading",
                "subsection_heading",
                "table_caption",
                "table_asset",
                "table_html",
                "backmatter_heading",
                "backmatter_body",
                "reference_item",
            }
            intervening_pages = set(range(cp + 1, page_order[0])) if page_order else set()
            intervening_body = any(
                b.get("page", 0) in intervening_pages and b.get("role", "") in _NON_PURE_ROLES
                for b in structured_blocks
            )
            if intervening_body:
                continue
            valid_pages = []
            for ap in page_order:
                page_has_body = any(
                    b.get("page", 0) == ap and b.get("role", "") in _NON_PURE_ROLES for b in structured_blocks
                )
                if not page_has_body:
                    valid_pages.append(ap)
            if len(valid_pages) < len(caps_sorted):
                caps_sorted = caps_sorted[: len(valid_pages)]
            if not valid_pages:
                continue
            # Match captions to validated asset pages in order
            for idx, cap in enumerate(caps_sorted):
                if idx >= len(valid_pages):
                    break
                ap = valid_pages[idx]
                page_assets = asset_pages[ap]
                if not page_assets:
                    continue
                fn = _extract_figure_number(str(cap.get("text", "")))
                cap_ns = _extract_figure_namespace(str(cap.get("text", "")))
                fig_id = _format_figure_id(cap_ns, fn)
                cap_score = score_figure_caption(
                    cap, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
                )
                consumed = []
                for ast in page_assets:
                    bid = ast.get("block_id", "")
                    if bid:
                        ownership.mark_assets_owned([(ap, bid)], owner_id=str(cap.get("block_id", "")), owner_family="figure")
                consumed.append(_project_asset_record(ast))
                unmatched_legends = [l for l in unmatched_legends if l.get("block_id") != cap.get("block_id")]
                cp_page = int(cap.get("page", 0) or 0)
                matched_figures.append(
                    {
                        "figure_id": fig_id,
                        "figure_namespace": cap_ns,
                        "legend_block_id": cap.get("block_id", ""),
                        "page": ap,
                        "text": str(cap.get("text", "")),
                        "figure_number": fn,
                        "matched_assets": consumed,
                        "asset_block_ids": [c["block_id"] for c in consumed],
                        "bridge_block_ids": [],
                        "caption_score": cap_score,
                        "match_score": {"score": 0.3, "decision": "matched", "evidence": ["legend_bundle_fallback"]},
                        "confidence": 0.3,
                        "flags": ["legend_bundle_match"],
                        "legend_page": cp_page,
                        "asset_pages": [ap],
                        "settlement_type": "legend_bundle",
                    }
                )
            # De-dup ambiguous_figures: remove entries whose legend_block_id
            # was already matched by the bundle pass.
            bundle_legend_ids = {
                m["legend_block_id"] for m in matched_figures if "legend_bundle_match" in m.get("flags", [])
            }
            ambiguous_figures[:] = [a for a in ambiguous_figures if a.get("legend_block_id") not in bundle_legend_ids]


    # === Previous-page legend locator bridge ===
    # Some papers use a short locator caption like "Fig. 10 (See legend on previous page.)"
    # on the figure's page instead of a full legend. The full legend lives on the preceding
    # page. This bridge connects the three components:
    #   previous page: full_legend (unmatched after normal matching)
    #   locator page:  visual group (unowned assets above the locator)
    #   locator:       the "see previous page" caption itself
    #
    # Runs AFTER normal matching and legend_bundle, BEFORE generic fallbacks.
    if figure_locators:
        # Collect unmatched legends by figure_number for quick lookup
        _unmatched_by_number: dict[tuple[str, int], list[dict]] = {}
        for leg in unmatched_legends:
            fn = _extract_figure_number(str(leg.get("text", "")))
            if fn is None:
                continue
            ns = _extract_figure_namespace(str(leg.get("text", "")))
            _unmatched_by_number.setdefault((ns, fn), []).append(leg)
        # Rejected legends may hold full legends misclassified as body_paragraph
        # (e.g. OCR raw_label=footnote causing role demotion). Scan them too.
        for leg in rejected_legends:
            fn = _extract_figure_number(str(leg.get("text", "")))
            if fn is None:
                continue
            ns = _extract_figure_namespace(str(leg.get("text", "")))
            key = (ns, fn)
            if key in _unmatched_by_number:
                continue
            style = str(leg.get("style_family") or "")
            zone = str(leg.get("zone") or "")
            if style == "legend_like" and zone in ("display_zone", ""):
                _unmatched_by_number.setdefault(key, []).append(leg)

        # Collect unowned assets per page (candidate visual groups)
        _unowned_by_page: dict[int, list[dict]] = {}
        for ast in unmatched_assets:
            ap = int(ast.get("page", 0) or 0)
            if ap > 0:
                _unowned_by_page.setdefault(ap, []).append(ast)

        for locator in figure_locators:
            locator_text = str(locator.get("text", "") or "")
            fn = _extract_figure_number(locator_text)
            if fn is None:
                continue
            ns = _extract_figure_namespace(locator_text)
            locator_page = int(locator.get("page", 0) or 0)
            if locator_page <= 1:
                continue
            prev_page = locator_page - 1

            # Find full legend on previous page with same figure_number
            full_legends = _unmatched_by_number.get((ns, fn), [])
            full_legend = None
            for leg in full_legends:
                lp = int(leg.get("page", 0) or 0)
                if lp == prev_page:
                    leg_text = str(leg.get("text", "") or "")
                    # Must have substantial text (not itself a locator)
                    if len(leg_text) >= 60 and not _is_previous_page_legend_locator(leg):
                        full_legend = leg
                        break

            if full_legend is None:
                continue


            # Find visual group on locator's page:
            # 1) Priority: candidate_groups (distance_cluster, composite_parent)
            # 2) Fallback: only if there's one tight cluster above locator
            locator_bbox = locator.get("bbox") or [0, 0, 0, 0]
            locator_top = locator_bbox[1] if len(locator_bbox) >= 4 else 0

            best_group_assets: list[dict] = []
            all_groups = (candidate_groups or []) + (composite_parent_candidates or [])
            scored_groups: list[tuple[tuple[int, int, float], dict, list[str]]] = []
            _seen_group_bids: set[str] = set()
            for g in all_groups:
                gp = int(g.get("page", 0) or 0)
                if gp != locator_page:
                    continue
                g_bbox = g.get("cluster_bbox") or [0, 0, 0, 0]
                if len(g_bbox) < 4 or g_bbox[3] > locator_top:
                    continue
                g_asset_ids = g.get("asset_block_ids", [])
                g_unowned = [
                    bid for bid in g_asset_ids
                    if (locator_page, str(bid)) not in used_asset_page_ids
                ]
                if not g_unowned:
                    continue
                g_type = g.get("group_type", "")
                g_dist = abs(g_bbox[3] - locator_top)
                score = (
                    0 if g_type == "composite_parent" else
                    1 if g_type == "distance_cluster" else
                    2,
                    -len(g_unowned),
                    g_dist,
                )
                scored_groups.append((score, g, g_unowned))
                _seen_group_bids.update(g_unowned)

            if scored_groups:
                scored_groups.sort(key=lambda x: x[0])
                best = scored_groups[0]
                g_unowned = best[2]
                best_group_assets = [
                    a for a in _filter_figure_assets(assets)
                    if int(a.get("page", 0) or 0) == locator_page
                    and str(a.get("block_id", "")) in g_unowned
                ]

            # Fallback: no candidate group, but one tight asset cluster above locator
            if not best_group_assets:
                page_assets = [
                    a for a in _unowned_by_page.get(locator_page, [])
                    if (locator_page, str(a.get("block_id", ""))) not in used_asset_page_ids
                ]
                above = [a for a in page_assets if (a.get("bbox") or [0,0,0,0])[3] <= locator_top]
                if above and _is_tight_asset_cluster(above, locator_top):
                    best_group_assets = above

            if not best_group_assets:
                continue

            # Build matched figure entry: use full_legend as caption, locator as bridge
            fig_id = _format_figure_id(ns, fn)
            consumed = [_project_asset_record(a) for a in best_group_assets]
            # Compute cluster_bbox from consumed asset bboxes
            asset_bboxes = [
                a.get("bbox") or a.get("block_bbox") or [0, 0, 0, 0]
                for a in best_group_assets
            ]
            valid_bboxes = [b for b in asset_bboxes if len(b) >= 4 and b[2] > b[0] and b[3] > b[1]]
            cluster_bbox = _cluster_bbox(valid_bboxes) if valid_bboxes else [0, 0, 0, 0]

            for a in best_group_assets:
                bid = a.get("block_id", "")
                if bid:
                    ownership.mark_assets_owned(
                        [(locator_page, bid)],
                        owner_id=str(full_legend.get("block_id", "")),
                        owner_family="figure",
                    )
            # Remove full_legend from unmatched_legends (page-aware key)
            full_key = (
                int(full_legend.get("page", 0) or 0),
                str(full_legend.get("block_id", "")),
            )
            unmatched_legends = [
                l for l in unmatched_legends
                if (int(l.get("page", 0) or 0), str(l.get("block_id", ""))) != full_key
            ]
            # Remove consumed assets from unmatched_assets
            consumed_ids = {(locator_page, str(a.get("block_id", ""))) for a in best_group_assets}
            unmatched_assets = [
                a for a in unmatched_assets
                if (int(a.get("page", 0) or 0), str(a.get("block_id", ""))) not in consumed_ids
            ]

            matched_figures.append({
                "figure_id": fig_id,
                "figure_namespace": ns,
                "legend_block_id": full_legend.get("block_id", ""),
                "legend_page": prev_page,
                "text": str(full_legend.get("text", "")),
                "figure_number": fn,
                "matched_assets": consumed,
                "asset_block_ids": [c["block_id"] for c in consumed],
                "cluster_bbox": cluster_bbox,
                "group_type": "previous_page_locator_bridge",
                "group_evidence": ["explicit_previous_page_locator", "previous_page_full_legend", "same_page_visual_group"],
                "bridge_block_ids": [str(locator.get("block_id", ""))],
                "caption_score": score_figure_caption(
                    full_legend, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
                ),
                "match_score": {"score": 0.5, "decision": "matched", "evidence": ["previous_page_locator_bridge"]},
                "confidence": 0.5,
                "flags": ["previous_page_locator_match"],
                "page": locator_page,
                "locator_block_id": locator.get("block_id", ""),
                "locator_page": locator_page,
                "asset_pages": [locator_page],
                "settlement_type": "previous_page_legend_locator",
            })
            # Clean up ambiguous_figures that referenced the locator (page-aware)
            locator_key = (locator_page, str(locator.get("block_id", "")))
            ambiguous_figures[:] = [
                af for af in ambiguous_figures
                if (
                    int(af.get("page", 0) or 0),
                    str(af.get("legend_block_id", "")),
                ) != locator_key
            ]

    # === Group-aware sequential fallback ===
    # Consume unmatched distance_clusters that no same-page legend claimed.
    # Inserted AFTER preproof fallback, BEFORE old single-asset sequential fallback.
    local_asset_by_page_id: dict[tuple[int, str], dict] = {}
    for block in _filter_figure_assets(assets):
        local_asset_by_page_id[(int(block.get("page", 0) or 0), str(block.get("block_id", "")))] = block

    # ponytail: also include single_asset groups per Option 1 — group-aware fallback
    # handles them so old sequential fallback only sees true bare assets.
    unmatched_groups = [
        g
        for g in candidate_groups
        if str(g.get("group_id", "")) not in used_group_ids
        and g.get("group_type") in {"distance_cluster", "single_asset"}
        and not any(
            (int(g.get("page", 0) or 0), str(bid)) in used_asset_page_ids
            for bid in g.get("asset_block_ids", [])
            if bid is not None
        )
    ]
    unmatched_groups.sort(
        key=lambda g: (
            int(g.get("page", 0) or 0),
            (g.get("cluster_bbox") or [0, 0, 0, 0])[1],
        )
    )

    for legend in list(unmatched_legends):
        lg_page = int(legend.get("page", 0) or 0)
        cap_text = str(legend.get("text", "") or "")
        fn = _extract_figure_number(cap_text)
        if fn is None:
            continue
        cap_ns = _extract_figure_namespace(cap_text)
        fig_id = _format_figure_id(cap_ns, fn)

        # Collect candidate groups: prefer same-page, then next-page, then previous-page
        same_page = [g for g in unmatched_groups if g["page"] == lg_page]
        next_page = [g for g in unmatched_groups if g["page"] == lg_page + 1]
        prev_page = [g for g in unmatched_groups if g["page"] == lg_page - 1]

        best_group = None
        if same_page:
            scored = []
            for sg in same_page:
                sg_score = _score_legend_to_group(
                    legend,
                    sg,
                    caption_score=score_figure_caption(
                        legend,
                        nearby_media=True,
                        caption_style_match=False,
                        body_prose_likelihood=False,
                    ),
                    page_width=page_width,
                    page_blocks=_page_blocks_by_page.get(lg_page, []),
                    page_height=_page_height_by_page.get(lg_page, 0.0),
                    page_numbered_legend_count=_numbered_legend_count_by_page.get(lg_page, 0),
                )
                if sg_score.get("decision") == "matched" and sg_score.get("score", 0.0) >= 0.5:
                    scored.append((sg, sg_score.get("score", 0.0)))
            if scored:
                scored.sort(key=lambda x: x[1], reverse=True)
                best_group = scored[0][0]
        if best_group is None and next_page:
            best_group = next_page[0]
        if best_group is None and prev_page:
            first_bid = str(prev_page[0]["asset_block_ids"][0]) if prev_page[0]["asset_block_ids"] else ""
            first_asset = local_asset_by_page_id.get((prev_page[0]["page"], first_bid))
            if first_asset and _allow_previous_page_sequential_match(legend, first_asset):
                best_group = prev_page[0]

        if best_group is None:
            continue

        group_page = int(best_group.get("page", 0) or 0)
        caption_score = score_figure_caption(
            legend,
            nearby_media=True,
            caption_style_match=False,
            body_prose_likelihood=False,
        )

        group_assets = []
        for bid in best_group.get("asset_block_ids", []):
            if bid is None:
                continue
            asset = local_asset_by_page_id.get((group_page, str(bid)))
            if asset:
                group_assets.append(asset)
                ownership.mark_assets_owned([(group_page, str(bid))], owner_id=str(legend.get("block_id", "")), owner_family="figure")

        if not group_assets:
            continue

        matched_figures.append(
            {
                "figure_id": fig_id,
                "figure_namespace": cap_ns,
                "legend_block_id": legend.get("block_id", ""),
                "page": group_page,
                "text": cap_text,
                "figure_number": fn,
                    "matched_assets": [_project_asset_record(a) for a in group_assets],
                "asset_block_ids": [str(a.get("block_id", "")) for a in group_assets],
                "bridge_block_ids": [],
                "group_type": best_group.get("group_type", ""),
                "group_evidence": best_group.get("group_evidence", []) + ["group_sequential_fallback"],
                "cluster_bbox": best_group.get("cluster_bbox", [0, 0, 0, 0]),
                "confidence": 0.45,
                "match_score": {
                    "score": 0.45,
                    "decision": "matched",
                    "evidence": ["group_sequential_fallback"],
                },
                "flags": ["group_sequential_match"],
                "caption_score": caption_score,
                "legend_page": int(legend.get("page", 0) or 0),
                "asset_pages": sorted({int(a.get("page", 0) or 0) for a in group_assets}),
                "settlement_type": "group_sequential",
            }
        )

        ownership.match_group(best_group, owner_id=str(legend.get("block_id", "")), owner_family="figure")
        unmatched_legends.remove(legend)
        ambiguous_figures[:] = [
            af for af in ambiguous_figures if str(af.get("legend_block_id", "")) != str(legend.get("block_id", ""))
        ]

    # === End group-aware fallback ===

    # Sequential fallback: match unmatched captions to remaining assets in reading order.
    # Captions and figures often appear on different pages — humans match them by
    # sequential reading order, not spatial proximity. This is a necessary tradeoff.
    # Run BEFORE cluster building so sequential matching gets first pick of assets.
    # Stage 1 restriction: sequential fallback may not consume assets that belong
    # to any candidate group. Filter the input to the loop but keep unmatched_assets for output.
    _grouped_asset_ids = _grouped_asset_page_ids(candidate_groups)
    _ungrouped_unmatched = [
        ua
        for ua in unmatched_assets
        if (int(ua.get("page", 0) or 0), str(ua.get("block_id", ""))) not in _grouped_asset_ids
    ]
    if unmatched_legends and _ungrouped_unmatched:
        sorted_caps = sorted(
            unmatched_legends,
            key=lambda b: (b.get("page", 0) or 0, (b.get("bbox") or [0, 0, 0, 0])[1]),
        )
        sorted_asts = sorted(
            _ungrouped_unmatched,
            key=lambda b: (b.get("page", 0) or 0, (b.get("bbox") or [0, 0, 0, 0])[1]),
        )
        ai = 0
        seq_matched: list[tuple[dict, dict]] = []
        for cap in sorted_caps:
            cap_text = cap.get("text", "")
            fn = _extract_figure_number(cap_text)
            if fn is None:
                continue
            cap_ns = _extract_figure_namespace(cap_text)

            cp = cap.get("page", 0) or 0
            cap_bbox = cap.get("bbox") or [0, 0, 0, 0]
            cap_top = cap_bbox[1] if len(cap_bbox) >= 4 else 0
            previous_page_asset = None
            future_page_asset = None
            scan_index = ai

            while scan_index < len(sorted_asts):
                asset = sorted_asts[scan_index]
                ap = asset.get("page", 0) or 0
                asset_bid = asset.get("block_id", "")
                if asset_bid and (ap, asset_bid) in used_asset_page_ids:
                    scan_index += 1
                    continue
                if ap == cp - 1:
                    previous_page_asset = asset
                    scan_index += 1
                    continue
                if ap >= cp:
                    if ap > cp:
                        future_page_asset = asset
                    break
                scan_index += 1

            asset = None
            if (
                asset is None
                and previous_page_asset is not None
                and _allow_previous_page_sequential_match(cap, previous_page_asset)
            ):
                asset = previous_page_asset
            if asset is None and future_page_asset is not None:
                fap = future_page_asset.get("page", 0) or 0
                if fap >= cp:
                    asset = future_page_asset
            if asset is None:
                continue

            asset_bid = asset.get("block_id", "")
            asset_page = asset.get("page", 0)
            if asset_bid is not None and (asset_page, asset_bid) in used_asset_page_ids:
                continue
            while ai < len(sorted_asts):
                ai_asset = sorted_asts[ai]
                ai += 1
                if ai_asset.get("block_id", "") == asset_bid and ai_asset.get("page", 0) == asset_page:
                    break
            fig_id = _format_figure_id(cap_ns, fn)
            caption_score = score_figure_caption(
                cap, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
            )
            seq_matched.append((cap, asset))
            matched_figures.append(
                {
                    "figure_id": fig_id,
                    "figure_namespace": cap_ns,
                    "legend_block_id": cap.get("block_id", ""),
                    "page": asset.get("page", 0),
                    "text": cap.get("text", ""),
                    "figure_number": fn,
                    "matched_assets": [_project_asset_record(asset)],
                    "group_type": "",
                    "group_evidence": [],
                    "confidence": 0.35,
                    "match_score": {"score": 0.35, "decision": "matched", "evidence": ["sequential_fallback"]},
                    "flags": ["sequential_match"],
                    "caption_score": caption_score,
                    "legend_page": int(cap.get("page", 0) or 0),
                    "asset_pages": [int(asset.get("page", 0) or 0)],
                    "settlement_type": "sequential",
                }
            )
            if asset_bid:
                ownership.mark_assets_owned([(asset_page, asset_bid)], owner_id=str(cap.get("block_id", "")), owner_family="figure")
        for cap, asset in seq_matched:
            unmatched_legends[:] = [l for l in unmatched_legends if l is not cap]
            if int(asset.get("page", 0) or 0) < int(cap.get("page", 0) or 0):
                ambiguous_figures[:] = [
                    af for af in ambiguous_figures if str(af.get("legend_block_id", "")) != str(cap.get("block_id", ""))
                ]

    # Build unresolved clusters: spatial clusters of unmatched assets on
    # pages where all candidate legends were rejected (multi-panel figures
    # with axis labels or informal captions)
    if rejected_legends and unmatched_assets:
        rejected_pages = {leg.get("page") for leg in rejected_legends if leg.get("page")}
        for cluster in _media_clusters(unmatched_assets, page_width):
            if len(cluster) < 2:
                continue
            cluster_page = cluster[0].get("page", 0)
            if cluster_page not in rejected_pages:
                continue
            cluster_id = f"unresolved_cluster_{len(unresolved_clusters) + 1:03d}"
            cluster_ids = [b.get("block_id", "") for b in cluster]
            unresolved_clusters.append(
                {
                    "cluster_id": cluster_id,
                    "media_block_ids": cluster_ids,
                    "cluster_bbox": _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in cluster]),
                    "page": cluster_page,
                }
            )
        if unresolved_clusters:
            consumed = {
                (int(uc.get("page", 0) or 0), str(bid))
                for uc in unresolved_clusters
                for bid in uc["media_block_ids"]
            }
            unmatched_assets = [
                a for a in unmatched_assets
                if (int(a.get("page", 0) or 0), str(a.get("block_id", ""))) not in consumed
            ]

    unmatched_assets = _recompute_final_unmatched_assets(assets, used_asset_page_ids, unresolved_clusters)

    # --- Dense composite parent candidate construction from visual fragments ---
    dense_parents = _build_dense_composite_parent_candidates(
        candidate_groups,
        unresolved_clusters,
        _numbered_pages,
        page_width,
    )
    _composite_parent_by_id = {
        str(parent.get("group_id", "")): parent
        for parent in composite_parent_candidates
        if str(parent.get("group_id", ""))
    }
    for parent in dense_parents:
        parent_id = str(parent.get("group_id", ""))
        if parent_id:
            _composite_parent_by_id[parent_id] = parent
    composite_parent_candidates = list(_composite_parent_by_id.values())

    # --- Dense page unmatched consolidation: on pages where a dense composite
    # parent candidate exists, leftover unmatched assets are grouped into
    # unresolved clusters ---
    _dense_parent_pages = {
        int(p.get("page", 0) or 0)
        for p in composite_parent_candidates
        if p.get("parent_subtype") == "dense_composite"
    }
    if unmatched_assets and _dense_parent_pages:
        for cluster in _media_clusters(unmatched_assets, page_width):
            if len(cluster) < 2:
                continue
            cluster_page = cluster[0].get("page", 0)
            if cluster_page not in _dense_parent_pages:
                continue
            cluster_id = f"unresolved_cluster_dense_{len(unresolved_clusters) + 1:03d}"
            cluster_ids = [b.get("block_id", "") for b in cluster]
            unresolved_clusters.append(
                {
                    "cluster_id": cluster_id,
                    "media_block_ids": cluster_ids,
                    "cluster_bbox": _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in cluster]),
                    "page": cluster_page,
                    "cluster_source": "dense_page_leftovers",
                }
            )
        if unresolved_clusters:
            consumed_dense = {
                (int(uc.get("page", 0) or 0), str(bid))
                for uc in unresolved_clusters
                for bid in uc["media_block_ids"]
            }
            unmatched_assets = [
                a for a in unmatched_assets
                if (int(a.get("page", 0) or 0), str(a.get("block_id", ""))) not in consumed_dense
            ]

    # --- P2: page-local caption grammar validation ---
    local_pairing_hypotheses = _validate_page_local_caption_grammar(
        local_pairing_hypotheses, ordered_legends
    )

    # --- Remove blocks already matched to figures from unresolved clusters
    # (clusters are built before matching completes; dedup afterward) ---
    _owned_block_ids: set[tuple[int, str]] = set()
    for mf in matched_figures:
        mf_page = int(mf.get("page", 0) or 0)
        for bid in mf.get("asset_block_ids", []):
            _owned_block_ids.add((mf_page, str(bid)))
    if _owned_block_ids and unresolved_clusters:
        _clean_clusters: list[dict] = []
        for uc in unresolved_clusters:
            uc_page = int(uc.get("page", 0) or 0)
            mids = [str(bid) for bid in uc.get("media_block_ids", [])]
            kept = [bid for bid in mids if (uc_page, bid) not in _owned_block_ids]
            if not kept:
                continue
            uc["media_block_ids"] = kept
            _clean_clusters.append(uc)
        unresolved_clusters = _clean_clusters

    inventory = {
        "figure_legends": deduped_legends,
        "figure_assets": assets,
        "matched_figures": matched_figures,
        "held_figures": held_figures,
        "ambiguous_figures": ambiguous_figures,
        "local_pairing_hypotheses": local_pairing_hypotheses,
        "unmatched_legends": unmatched_legends,
        "unmatched_assets": unmatched_assets,
        "rejected_legends": rejected_legends,
        "unresolved_clusters": unresolved_clusters,
        "deduped_legend_ids": deduped_legend_ids,
        "same_number_distinct_legends": [
            {"figure_number": fn, "page": page, "block_id": str(bid), "reason": "same_number_different_caption_text"}
            for (_ns, fn, page, bid) in _same_number_distinct_keys
        ],
        "composite_parent_candidates": composite_parent_candidates,
        "suppressed_caption_candidates": suppressed_caption_candidates,
        "official_figure_count": len(matched_figures),
    }

    inventory = _promote_sequence_matches(inventory, structured_blocks)

    inventory = _infer_missing_main_figure_numbers(inventory, structured_blocks)
    # bbox-only synthetic vector figure fallback (Commit 4)
    _apply_bbox_only_synthetic_vector_fallback(
        matched_figures=inventory.setdefault("matched_figures", []),
        unmatched_legends=inventory.setdefault("unmatched_legends", []),
        rejected_legends=inventory.setdefault("rejected_legends", []),
        unmatched_assets=inventory.setdefault("unmatched_assets", []),
        ownership=ownership,
    )
    # Asset-internal figure number recovery
    _recover_missing_figure_numbers_from_assets(
        inventory=inventory,
        page_pdf_lines_by_page=page_pdf_lines_by_page,
    )

    _dedup_unmatched_assets_against_matched_figures(inventory)
    _dedup_unresolved_clusters_against_matched_figures(inventory)
    inventory["figure_legend_completeness"] = compute_figure_legend_completeness(
        structured_blocks,
        inventory,
    )

    _resolve_figure_id_collisions(inventory)

    return inventory


def compute_figure_legend_completeness(
    structured_blocks: list[dict],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    """Verify every numbered formal legend lands in an explicit outcome bucket.

    Outcomes for each numbered formal legend:
      - matched  (figure object emitted)
      - held     (insufficient evidence, waiting)
      - ambiguous (no asset or close-tie, unresolved)
      - unmatched (low caption score, not a formal legend)
      - gap      (no outcome assigned — legend was silently dropped)

    Note: unresolved_cluster is a separate inventory bucket for panel groups
    without legends; it is not a legend-level outcome.

    Returns a dict with total, accounted_for, gap_count, and per-legend
    details.  A gap_count > 0 means a formal legend was silently dropped.
    """
    figure_number_re = re.compile(
        r"(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
        r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+"
        r"(?:S\.?\s*)?(\d+(?:\.\d+)?)",
        flags=re.IGNORECASE,
    )

    # Collect all legend block_ids that entered the pipeline
    legend_ids_in_pipeline: set[str] = set()
    for block in structured_blocks:
        role = block.get("role", "")
        if block.get("_non_body_media") or role == "non_body_insert":
            continue
        if _PANEL_LABEL_PATTERN.match(str(block.get("text", "")).strip()):
            continue
        is_vfc = _is_validation_first_legend_candidate(block)
        if role in ("figure_caption", "figure_caption_candidate") or is_vfc:
            bid = block.get("block_id", "")
            if bid:
                legend_ids_in_pipeline.add(bid)

    # Build lookup sets for each outcome
    matched_ids: set[str] = set()
    for mf in inventory.get("matched_figures", []):
        bid = mf.get("legend_block_id", "")
        if bid:
            matched_ids.add(bid)

    held_ids: set[str] = set()
    for hf in inventory.get("held_figures", []):
        bid = hf.get("legend_block_id", "")
        if bid:
            held_ids.add(bid)

    ambiguous_ids: set[str] = set()
    for af in inventory.get("ambiguous_figures", []):
        bid = af.get("legend_block_id", "")
        if bid:
            ambiguous_ids.add(bid)

    unmatched_ids: set[str] = set()
    for ul in inventory.get("unmatched_legends", []):
        bid = ul.get("block_id", "")
        if bid:
            unmatched_ids.add(bid)

    deduped_ids: set[str] = set()
    for item in inventory.get("deduped_legend_ids", []):
        bid = item.get("block_id", "")
        if bid:
            deduped_ids.add(bid)

    # Check every numbered legend in the pipeline
    details: list[dict[str, Any]] = []
    total = 0
    accounted_for = 0
    gap_count = 0

    for block in structured_blocks:
        role = block.get("role", "")
        if block.get("_non_body_media") or role == "non_body_insert":
            continue
        if _PANEL_LABEL_PATTERN.match(str(block.get("text", "")).strip()):
            continue
        is_vfc = _is_validation_first_legend_candidate(block)
        if role not in ("figure_caption", "figure_caption_candidate") and not is_vfc:
            continue

        text = block.get("text", "")
        m = figure_number_re.search(text)
        if m is None:
            continue

        total += 1
        bid = block.get("block_id", "")
        fig_num = None
        with contextlib.suppress(ValueError):
            fig_num = int(float(m.group(1)))
        fig_ns = _extract_figure_namespace(text)

        if bid in matched_ids:
            status = "matched"
        elif bid in held_ids:
            status = "held"
        elif bid in ambiguous_ids:
            status = "ambiguous"
        elif bid in unmatched_ids:
            status = "unmatched"
        elif bid in deduped_ids:
            status = "deduped_duplicate"
        else:
            status = "gap"

        if status != "gap":
            accounted_for += 1
        else:
            gap_count += 1

        details.append(
            {
                "block_id": bid,
                "figure_number": fig_num,
                "figure_namespace": fig_ns,
                "status": status,
                "page": block.get("page"),
            }
        )

    return {
        "total": total,
        "accounted_for": accounted_for,
        "gap_count": gap_count,
        "details": details,
    }


def _promote_sequence_matches(figure_inventory: dict, blocks: list[dict]) -> dict:
    """Promote eligible ambiguous figures to sequence_match when
    contiguous figure numbers suggest reliable ordering.

    An ambiguous figure with a figure number adjacent to an already-matched
    figure number is promoted to ``matched_figures`` with
    ``strict_status="sequence_match"``.  This is a strict-layer operation;
    the reader layer projects the resulting status.

    Promotion preconditions (spec):
    1. Contiguous figure numbers (no gaps in numbered sequence)
    2. Compatible cluster/media count per figure
    3. Monotonic page/order alignment
    4. No contradiction with existing exact matches

    For this minimal implementation, the simple heuristic is:

      If this ambiguous figure has figure number N and we already have a
      matched figure at N-1 or N+1, it is part of a sequence and is promoted.
    """
    matched = figure_inventory.get("matched_figures", [])
    matched_fig_nums: set[int] = set()
    for mf in matched:
        fn = mf.get("figure_number")
        if fn is not None:
            matched_fig_nums.add(fn)

    ambiguous = figure_inventory.get("ambiguous_figures", [])
    promoted: list[dict] = []

    # Find ambiguous figures that are adjacent to a matched figure number
    remaining_ambiguous: list[dict] = []
    for af in ambiguous:
        fn = af.get("figure_number")
        if fn is None:
            remaining_ambiguous.append(af)
            continue
        if (fn - 1 in matched_fig_nums) or (fn + 1 in matched_fig_nums):
            asset_block_ids = af.get("asset_block_ids", [])
            if not asset_block_ids:
                af["sequence_skip_empty_assets"] = True
                af["hold_reason"] = "assetless_sequence_shell"
                remaining_ambiguous.append(af)
                continue
            matched_assets = list(af.get("matched_assets", []))
            asset_pages = list(af.get("asset_pages", []))
            legend_page = af.get("legend_page", af.get("page"))
            page = af.get("page")
            if not matched_assets or not asset_pages or legend_page is None or page is None:
                af["sequence_skip_incomplete_contract"] = True
                remaining_ambiguous.append(af)
                continue
            ns_promoted = _extract_figure_namespace(af.get("text", ""))
            promoted_entry = {
                "figure_id": _format_figure_id(ns_promoted, fn),
                "figure_namespace": ns_promoted,
                "legend_block_id": af.get("legend_block_id", ""),
                "page": page,
                "legend_page": legend_page,
                "asset_pages": asset_pages,
                "text": af.get("text", ""),
                "figure_number": fn,
                "matched_assets": matched_assets,
                "asset_block_ids": asset_block_ids,
                "group_type": "",
                "group_evidence": [],
                "confidence": 0.0,
                "match_score": {
                    "score": 0.0,
                    "decision": "sequence_match",
                    "evidence": ["sequence_promotion"],
                },
                "flags": ["sequence_match"],
                "caption_score": af.get("caption_score", {}),
                "strict_status": "sequence_match",
                "settlement_type": "sequence_match",
                "zone": af.get("zone"),
                "style_family": af.get("style_family"),
                "marker_signature": af.get("marker_signature") or {},
            }
            promoted.append(promoted_entry)
        else:
            remaining_ambiguous.append(af)

    if promoted:
        figure_inventory["matched_figures"].extend(promoted)
        figure_inventory["ambiguous_figures"] = remaining_ambiguous
        figure_inventory["official_figure_count"] = len(figure_inventory["matched_figures"])

    return figure_inventory



def _collect_matched_figure_asset_ids_from_list(matched_figures: list[dict]) -> set[tuple[int, str]]:
    consumed: set[tuple[int, str]] = set()
    for fig in matched_figures:
        fig_page = int(fig.get("page", 0) or 0)
        asset_pages = [int(p) for p in (fig.get("asset_pages") or []) if p is not None]

        for asset in fig.get("matched_assets", []) or []:
            bid = str(asset.get("block_id") or "")
            if not bid:
                continue
            ap = int(asset.get("page", 0) or 0) or fig_page
            if ap > 0:
                consumed.add((ap, bid))

        for bid_raw in fig.get("asset_block_ids", []) or []:
            bid = str(bid_raw or "")
            if not bid:
                continue
            if len(asset_pages) == 1:
                consumed.add((asset_pages[0], bid))
            elif fig_page > 0:
                consumed.add((fig_page, bid))

    return consumed


def _collect_matched_figure_asset_ids(inventory: dict) -> set[tuple[int, str]]:
    return _collect_matched_figure_asset_ids_from_list(inventory.get("matched_figures", []) or [])


def _dedup_unmatched_assets_against_matched_figures(inventory: dict) -> None:
    consumed = _collect_matched_figure_asset_ids(inventory)
    if not consumed:
        return
    inventory["unmatched_assets"] = [
        a for a in inventory.get("unmatched_assets", []) or []
        if (int(a.get("page", 0) or 0), str(a.get("block_id", "") or "")) not in consumed
    ]


def _dedup_unresolved_clusters_against_matched_figures(inventory: dict) -> None:
    consumed = _collect_matched_figure_asset_ids(inventory)
    if not consumed:
        return
    cleaned = []
    for cluster in inventory.get("unresolved_clusters", []) or []:
        page = int(cluster.get("page", 0) or 0)
        kept = [str(bid) for bid in (cluster.get("media_block_ids", []) or [])
                if (page, str(bid)) not in consumed]
        if not kept:
            continue
        cluster = dict(cluster)
        cluster["media_block_ids"] = kept
        cleaned.append(cluster)
    inventory["unresolved_clusters"] = cleaned

def _collect_figure_owned_asset_ids(figure_inventory: dict) -> set[tuple[int, str]]:
    return _collect_matched_figure_asset_ids(figure_inventory)


def _collect_table_owned_asset_ids(table_inventory: dict) -> set[tuple[int, str]]:
    owned: set[tuple[int, str]] = set()
    for table in table_inventory.get("tables", []):
        if not table.get("has_asset"):
            continue
        asset_id = _asset_page_id(table.get("page", 0), table.get("asset_block_id", ""))
        if asset_id is not None:
            owned.add(asset_id)
    return owned

def _table_ownership_strength(table: dict) -> tuple[int, int]:
    explicit = 1 if str(table.get("caption_text") or "").lower().startswith("table") else 0
    strong = 1 if str(table.get("match_status") or "") == "matched" else 0
    return (explicit, strong)


def _figure_ownership_strength(fig: dict) -> tuple[int, int]:
    text = str(fig.get("text") or "")
    explicit = 1 if text.lower().startswith(("figure", "fig.")) else 0
    strong = 1 if float((fig.get("match_score") or {}).get("score", 0.0) or 0.0) >= 0.70 else 0
    return (explicit, strong)


def resolve_media_asset_conflicts(figure_inventory: dict, table_inventory: dict) -> list[dict]:
    """Arbitrate shared assets between figure and table inventories.

    Only resolves clear asymmetric cases (explicit+strong vs weak).
    Equal-strength weak/weak stays unresolved — surfaced in ownership_conflicts.
    Returns list of resolution records.
    """
    resolutions: list[dict] = []
    tables_by_asset = {
        (int(t.get("page", 0) or 0), str(t.get("asset_block_id", ""))): t
        for t in table_inventory.get("tables", [])
        if t.get("has_asset") and t.get("asset_block_id")
    }

    kept_figures = []
    for fig in figure_inventory.get("matched_figures", []):
        asset_ids = [
            (int(fig.get("page", 0) or 0), str(bid))
            for bid in fig.get("asset_block_ids", [])
            if bid is not None
        ]
        conflict_id = next((aid for aid in asset_ids if aid in tables_by_asset), None)
        if conflict_id is None:
            kept_figures.append(fig)
            continue

        table = tables_by_asset[conflict_id]
        table_strength = _table_ownership_strength(table)
        figure_strength = _figure_ownership_strength(fig)

        if table_strength > figure_strength:
            resolutions.append({"page": conflict_id[0], "block_id": conflict_id[1], "winner": "table"})
            continue  # figure removed (not appended to kept_figures)
        if figure_strength > table_strength:
            resolutions.append({"page": conflict_id[0], "block_id": conflict_id[1], "winner": "figure"})
            table["has_asset"] = False
            table["asset_block_id"] = None
            kept_figures.append(fig)
            continue

        kept_figures.append(fig)  # weak/weak, no resolution

    figure_inventory["matched_figures"] = kept_figures
    figure_inventory["ownership_resolutions"] = resolutions
    return resolutions



def _build_ownership_conflicts(figure_inventory: dict, table_inventory: dict) -> list[dict]:
    figure_owned = _collect_figure_owned_asset_ids(figure_inventory)
    table_owned = _collect_table_owned_asset_ids(table_inventory)
    conflicts: list[dict] = []
    for asset_page_id in sorted(figure_owned & table_owned):
        page, block_id = asset_page_id
        conflicts.append(
            {
                "asset_page_id": asset_page_id,
                "page": page,
                "block_id": block_id,
                "conflict_type": "ownership_conflict",
                "owners": ["figure", "table"],
            }
        )
    return conflicts


def attach_ownership_conflicts(figure_inventory: dict, table_inventory: dict) -> None:
    figure_inventory["ownership_conflicts"] = _build_ownership_conflicts(figure_inventory, table_inventory)


def write_back_figure_roles(inventory: dict, structured_blocks: list[dict]) -> None:
    """Update structured block roles for matched figures from media_asset to figure_asset."""
    for figure in inventory.get("matched_figures", []):
        for asset in figure.get("matched_assets", []):
            asset_bid = asset.get("block_id")
            if not asset_bid:
                continue
            for block in structured_blocks:
                if block.get("block_id") == asset_bid and block.get("page") == figure.get("page"):
                    if block.get("role") in {"media_asset", "figure_asset"}:
                        block["role"] = "figure_asset"
                    break


_LEAK_ROLES = {
    "body_paragraph", "section_heading", "subsection_heading",
    "sub_subsection_heading", "backmatter_heading", "backmatter_body",
    "tail_candidate_body", "footnote", "structured_insert",
    "non_body_insert", "frontmatter_noise",
}


def _container_area_ok(container_bbox: list[float], page_width: float, page_height: float) -> bool:
    """Reject container bboxes that cover >65% of the page."""
    if len(container_bbox) < 4 or page_width <= 0 or page_height <= 0:
        return False
    cw = container_bbox[2] - container_bbox[0]
    ch = container_bbox[3] - container_bbox[1]
    page_area = max(1.0, page_width * page_height)
    container_area = max(1.0, cw * ch)
    if container_area >= page_area * 0.65:
        return False
    if cw >= page_width * 0.98 and ch >= page_height * 0.45:
        return False
    return True


def _container_has_media_asset(container_bbox: list[float], page_blocks: list[dict]) -> bool:
    """Check at least one figure/table asset falls inside the container."""
    for block in page_blocks:
        if block.get("role") not in {"figure_asset", "media_asset"}:
            continue
        bbox = block.get("bbox") or [0, 0, 0, 0]
        if len(bbox) < 4:
            continue
        if _is_contained(bbox, container_bbox):
            return True
    return False


def _validated_container_regions(page_blocks: list[dict], page_width: float, page_height: float) -> list[list[float]]:
    """Collect and validate unique _container_bbox values from blocks."""
    regions: list[list[float]] = []
    seen: set[tuple[float, float, float, float]] = set()
    for block in page_blocks:
        bbox = block.get("_container_bbox")
        if not bbox or len(bbox) < 4:
            continue
        tup = tuple(float(x) for x in bbox)
        if tup in seen:
            continue
        seen.add(tup)
        if not _container_area_ok(list(tup), page_width, page_height):
            continue
        if not _container_has_media_asset(list(tup), page_blocks):
            continue
        regions.append(list(tup))
    return regions


def _cluster_bboxes_by_proximity(
    bboxes: list[list[float]],
    margin: float = 40,
) -> list[list[float]]:
    if not bboxes:
        return []
    if len(bboxes) == 1:
        return [list(bboxes[0])]
    n = len(bboxes)
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        px, py = _find(x), _find(y)
        if px != py:
            parent[py] = px

    for i in range(n):
        ax1, ay1, ax2, ay2 = bboxes[i]
        for j in range(i + 1, n):
            bx1, by1, bx2, by2 = bboxes[j]
            if (max(ax1, bx1) - margin < min(ax2, bx2) + margin
                    and max(ay1, by1) - margin < min(ay2, by2) + margin):
                _union(i, j)

    clusters: dict[int, list[list[float]]] = {}
    for i in range(n):
        clusters.setdefault(_find(i), []).append(bboxes[i])
    return [
        [min(b[0] for b in g), min(b[1] for b in g),
         max(b[2] for b in g), max(b[3] for b in g)]
        for g in clusters.values()
    ]


def _is_contained(block_bbox: list[float], region_bbox: list[float]) -> bool:
    bx1, by1, bx2, by2 = block_bbox
    rx1, ry1, rx2, ry2 = region_bbox
    block_w = bx2 - bx1
    region_w = rx2 - rx1
    if block_w > region_w * 0.95:
        return False
    cx = (bx1 + bx2) / 2
    cy = (by1 + by2) / 2
    if not (rx1 <= cx <= rx2 and ry1 <= cy <= ry2):
        return False
    ix1 = max(bx1, rx1)
    iy1 = max(by1, ry1)
    ix2 = min(bx2, rx2)
    iy2 = min(by2, ry2)
    overlap = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    block_area = max(1.0, block_w * (by2 - by1))
    return overlap / block_area >= 0.85


def _highly_overlaps_any_matched_region(
    fallback_bbox: list[float],
    figure_regions: list[tuple[str, list[float]]],
) -> bool:
    fx1, fy1, fx2, fy2 = fallback_bbox
    fallback_area = max(1.0, (fx2 - fx1) * (fy2 - fy1))
    for tag, region_bbox in figure_regions:
        if tag != "matched":
            continue
        rx1, ry1, rx2, ry2 = region_bbox
        ix1 = max(fx1, rx1)
        iy1 = max(fy1, ry1)
        ix2 = min(fx2, rx2)
        iy2 = min(fy2, ry2)
        overlap = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        if overlap / fallback_area > 0.5:
            return True
    return False


def _figure_region_bbox(mf: dict) -> list[float] | None:
    cluster = mf.get("cluster_bbox")
    if cluster and len(cluster) >= 4:
        return cluster
    asset = mf.get("asset_bbox")
    if asset and len(asset) >= 4:
        return asset
    matched = mf.get("matched_assets", [])
    bboxes = [a["bbox"] for a in matched if len(a.get("bbox") or []) >= 4]
    if bboxes:
        return _cluster_bbox(bboxes)
    return None


def _matched_asset_keys(mf: dict) -> set[tuple[int, str]]:
    keys: set[tuple[int, str]] = set()
    page = int(mf.get("page", 0) or 0)
    for asset in mf.get("matched_assets", []):
        bid = asset.get("block_id")
        if bid is not None:
            keys.add((page, str(bid)))
    for bid in mf.get("asset_block_ids", []):
        if bid is not None:
            keys.add((page, str(bid)))
    return keys


def tag_figure_contained_text(
    blocks: list[dict],
    matched_figures: list[dict],
) -> None:
    pages = {b.get("page") for b in blocks if b.get("page") is not None}
    matched_by_page: dict[int, list[dict]] = {}
    for mf in matched_figures:
        p = mf.get("page")
        if p is not None:
            matched_by_page.setdefault(p, []).append(mf)
    for page in sorted(pages):
        page_blocks = [b for b in blocks if b.get("page") == page]
        figure_regions: list[tuple[str, list[float]]] = []
        covered_asset_keys: set[tuple[int, str]] = set()
        for mf in matched_by_page.get(page, []):
            region = _figure_region_bbox(mf)
            if region:
                figure_regions.append(("matched", region))
                covered_asset_keys |= _matched_asset_keys(mf)
        # ── Container bbox regions (validated _container_bbox) ──
        page_width = max((float(b.get("page_width") or 0.0) for b in page_blocks), default=0.0)
        page_height = max((float(b.get("page_height") or 0.0) for b in page_blocks), default=0.0)
        for cr in _validated_container_regions(page_blocks, page_width, page_height):
            if not _highly_overlaps_any_matched_region(cr, figure_regions):
                figure_regions.append(("container", cr))
        fallback_assets = [
            b for b in page_blocks
            if (int(b.get("page", 0) or 0), str(b.get("block_id", ""))) not in covered_asset_keys
            and b.get("role") in {"figure_asset", "media_asset"}
            and b.get("role") not in {"table_html", "table_asset"}
            and (
                b.get("asset_family_hint") == "figure_like"
                or str(b.get("raw_label", "") or "") in {"image", "chart", "figure_title", "figure"}
            )
        ]
        if fallback_assets:
            fallback_bboxes = [b["bbox"] for b in fallback_assets if len(b.get("bbox") or []) >= 4]
            for fr in _cluster_bboxes_by_proximity(fallback_bboxes, margin=40):
                if not _highly_overlaps_any_matched_region(fr, figure_regions):
                    figure_regions.append(("fallback", fr))
        if not figure_regions:
            continue
        for block in page_blocks:
            # Skip author bio blocks
            if block.get("_object_owner_family") == "author_bio" or block.get("_excluded_from_figure_inventory"):
                continue
            role = str(block.get("role") or "")
            if role in {"figure_asset", "media_asset", "noise", "author_bio_asset",
                        "figure_caption", "figure_caption_candidate",
                        "table_html", "table_asset",
                        "figure_inner_text"}:
                continue
            bbox = block.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            for _, fr in figure_regions:
                if _is_contained(bbox, fr):
                    block["_figure_contained"] = True
                    if role in _LEAK_ROLES:
                        block["role"] = "figure_inner_text"
                    break


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)

def _is_synthetic_vector_caption_candidate(caption: dict) -> bool:
    text = str(caption.get("text") or "")
    return bool(_FIGURE_DESCRIPTION_OPENING.match(text.strip())) \
        or bool(_extract_figure_number(text) is not None)

def _caption_has_rotated_text(caption: dict) -> bool:
    span = caption.get("span_metadata") or []
    if isinstance(span, dict):
        span = [span]
    if not isinstance(span, list):
        return False
    for entry in span:
        if not isinstance(entry, dict):
            continue
        direction = entry.get("dir")
        if not isinstance(direction, (list, tuple)) or len(direction) != 2:
            continue
        dx = float(direction[0])
        dy = float(direction[1])
        if abs(dy) > abs(dx):
            return True
    return False


def _rotate_rect_within_union(rect: list[float], union: list[float], *, clockwise: bool) -> list[float]:
    ux1, uy1, ux2, uy2 = union
    rx1, ry1, rx2, ry2 = rect
    width = max(0.0, ux2 - ux1)
    height = max(0.0, uy2 - uy1)
    pts = [
        (rx1 - ux1, ry1 - uy1),
        (rx2 - ux1, ry1 - uy1),
        (rx2 - ux1, ry2 - uy1),
        (rx1 - ux1, ry2 - uy1),
    ]
    if clockwise:
        rotated = [(height - y, x) for x, y in pts]
    else:
        rotated = [(y, width - x) for x, y in pts]
    xs = [p[0] for p in rotated]
    ys = [p[1] for p in rotated]
    return [min(xs), min(ys), max(xs), max(ys)]


def _prepare_rotated_caption_normalization(legend: dict, asset: dict) -> dict | None:
    if not _caption_has_rotated_text(legend):
        return None
    lb = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
    ab = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
    if len(lb) < 4 or len(ab) < 4:
        return None
    if int(legend.get("page", 0) or 0) != int(asset.get("page", 0) or 0):
        return None

    lx1, ly1, lx2, ly2 = lb
    ax1, ay1, ax2, ay2 = ab
    vertical_overlap = max(0.0, min(ly2, ay2) - max(ly1, ay1))
    min_height = max(1.0, min(ly2 - ly1, ay2 - ay1))
    y_ratio = vertical_overlap / min_height
    x_gap = max(ax1 - lx2, lx1 - ax2, 0.0)
    if y_ratio < 0.5 or x_gap > 80:
        return None

    union = [min(lx1, ax1), min(ly1, ay1), max(lx2, ax2), max(ly2, ay2)]
    clockwise = lx1 >= ax2
    rotation_correction_deg = 270 if clockwise else 90
    return {
        "legend_bbox": _rotate_rect_within_union(lb, union, clockwise=clockwise),
        "asset_bbox": _rotate_rect_within_union(ab, union, clockwise=clockwise),
        "rotation_correction_deg": rotation_correction_deg,
        "rotation_union_bbox": union,
    }


def _score_legend_to_asset_with_orientation(
    legend: dict,
    asset: dict,
    *,
    caption_score: dict,
    anchor_supported: bool = False,
    caption_text_supported: bool = False,
    family_supported: bool = False,
    zone_supported: bool = False,
) -> dict:
    normalized = _prepare_rotated_caption_normalization(legend, asset)
    if normalized is not None:
        norm_legend = dict(legend)
        norm_asset = dict(asset)
        norm_legend["bbox"] = normalized["legend_bbox"]
        norm_asset["bbox"] = normalized["asset_bbox"]
        match_score = score_figure_match(
            norm_legend,
            norm_asset,
            caption_score=caption_score,
            anchor_supported=anchor_supported,
            caption_text_supported=caption_text_supported,
            family_supported=family_supported,
            zone_supported=zone_supported,
        )
        match_score = dict(match_score)
        match_score.setdefault("evidence", []).append("rotated_caption_normalized")
        match_score["rotation_correction_deg"] = normalized["rotation_correction_deg"]
        match_score["rotation_union_bbox"] = normalized["rotation_union_bbox"]
        return match_score
    return score_figure_match(
        legend,
        asset,
        caption_score=caption_score,
        anchor_supported=anchor_supported,
        caption_text_supported=caption_text_supported,
        family_supported=family_supported,
        zone_supported=zone_supported,
    )



def _score_caption_to_unmatched_asset_for_synthetic(caption: dict, asset: dict) -> float:
    cb = caption.get("bbox") or caption.get("block_bbox") or [0, 0, 0, 0]
    ab = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
    if len(cb) < 4 or len(ab) < 4:
        return 0.0

    cx1, cy1, cx2, cy2 = cb
    ax1, ay1, ax2, ay2 = ab

    # Hard gate: must be same page
    if int(caption.get("page", 0) or 0) != int(asset.get("page", 0) or 0):
        return 0.0

    vertical_gap = max(0.0, max(cy1 - ay2, ay1 - cy2))
    if vertical_gap > 300:
        return 0.0

    normalized = _prepare_rotated_caption_normalization(caption, asset)
    if normalized is not None:
        cb = normalized["legend_bbox"]
        ab = normalized["asset_bbox"]
        cx1, cy1, cx2, cy2 = cb
        ax1, ay1, ax2, ay2 = ab
        vertical_gap = max(0.0, max(cy1 - ay2, ay1 - cy2))
        if vertical_gap > 300:
            return 0.0

    x_overlap = max(0.0, min(cx2, ax2) - max(cx1, ax1))
    min_width = max(1.0, min(cx2 - cx1, ax2 - ax1))
    x_ratio = x_overlap / min_width
    if x_ratio < 0.25:
        return 0.0

    score = 0.20  # same-page already verified

    if x_ratio >= 0.5:
        score += 0.45
    elif x_ratio >= 0.25:
        score += 0.25

    if vertical_gap <= 80:
        score += 0.35
    elif vertical_gap <= 180:
        score += 0.20
    elif vertical_gap <= 300:
        score += 0.10

    return min(score, 1.0)


def _build_bbox_only_synthetic_figure(caption, asset, *, index, score):
    text = str(caption.get("text") or "")
    fn = _extract_figure_number(text)
    ns = _extract_figure_namespace(text) if fn is not None else "figure"
    page = int(asset.get("page", caption.get("page", 0)) or 0)
    asset_record = _project_asset_record(asset)
    fig_id = _format_figure_id(ns, fn) if fn is not None else f"synthetic_figure_p{page}_{asset.get('block_id', index)}"
    normalized = _prepare_rotated_caption_normalization(caption, asset)
    entry = {
        "figure_id": fig_id, "figure_namespace": ns,
        "legend_block_id": caption.get("block_id", ""),
        "page": page, "legend_page": int(caption.get("page", 0) or 0),
        "asset_pages": [page] if page else [],
        "text": text, "figure_number": fn,
        "matched_assets": [asset_record],
        "asset_block_ids": [asset_record.get("block_id", "")],
        "cluster_bbox": (
            normalized["rotation_union_bbox"]
            if normalized is not None
            else asset.get("bbox") or asset.get("block_bbox") or []
        ),
        "caption_score": score_figure_caption(
            caption,
            nearby_media=True,
            caption_style_match=False,
            body_prose_likelihood=False,
        ),
        "match_score": {"score": score, "decision": "matched",
                        "evidence": ["bbox_only_synthetic_vector_fallback"]},
        "confidence": min(0.55, score),
        "flags": ["synthetic_vector_asset", "bbox_only_asset"],
        "truth_source": "vector_bbox",
        "strict_status": "bbox_only_synthetic",
        "settlement_type": "bbox_only_synthetic",
        "group_type": "",
        "group_evidence": [],
        "bridge_block_ids": [],
    }
    if normalized is not None:
        entry["rotation_correction_deg"] = normalized["rotation_correction_deg"]
    return entry


def _apply_bbox_only_synthetic_vector_fallback(
    *, matched_figures, unmatched_legends, rejected_legends, unmatched_assets, ownership,
) -> None:
    if not unmatched_assets:
        return
    candidates = [c for c in list(unmatched_legends) + list(rejected_legends)
                  if _is_synthetic_vector_caption_candidate(c)]
    if not candidates:
        return

    # Build existing figure number set to avoid duplicates (Amendment 6)
    _existing_numbered = {
        (str(fig.get("figure_namespace") or "figure"), fig.get("figure_number"))
        for fig in matched_figures
        if fig.get("figure_number") is not None
    }

    used_caption_ids: set[str] = set()
    used_asset_ids: set[tuple[int, str]] = set()

    for caption in candidates:
        cap_page = int(caption.get("page", 0) or 0)
        if cap_page <= 0:
            continue

        # Skip if figure number already exists (Amendment 6)
        fn = _extract_figure_number(str(caption.get("text") or ""))
        ns = _extract_figure_namespace(str(caption.get("text") or "")) if fn is not None else "figure"
        if fn is not None and (ns, fn) in _existing_numbered:
            continue

        page_assets = [
            a for a in unmatched_assets
            if int(a.get("page", 0) or 0) == cap_page
            and str(a.get("role") or "") in {"media_asset", "figure_asset"}
            and (a.get("asset_family_hint") == "figure_like"
                 or str(a.get("raw_label") or "") in {"image", "chart", "figure"})
        ]
        scored = []
        for asset in page_assets:
            aid = (int(asset.get("page", 0) or 0), str(asset.get("block_id", "") or ""))
            if aid in used_asset_ids or not ownership.can_consume_assets([aid]):
                continue
            s = _score_caption_to_unmatched_asset_for_synthetic(caption, asset)
            if s >= 0.65:
                scored.append((s, asset))
        if not scored:
            continue

        # Tie-breaking: skip if top two scores are too close (Amendment 5)
        scored.sort(key=lambda x: x[0], reverse=True)
        top_score, top_asset = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else -1.0
        if second_score >= 0 and top_score - second_score < 0.15:
            continue

        score, asset = top_score, top_asset
        aid = (int(asset.get("page", 0) or 0), str(asset.get("block_id", "") or ""))
        synthetic = _build_bbox_only_synthetic_figure(caption, asset, index=len(matched_figures) + 1, score=score)
        matched_figures.append(synthetic)

        # Track figure number for future dedup (Amendment 6)
        if fn is not None:
            _existing_numbered.add((ns, fn))

        if aid[1]:
            ownership.mark_assets_owned([aid], owner_id=str(caption.get("block_id", "")), owner_family="figure")
            used_asset_ids.add(aid)
        cid = str(caption.get("block_id", "") or "")
        if cid:
            used_caption_ids.add(cid)

    # Clean up consumed legends and assets
    if used_caption_ids:
        unmatched_legends[:] = [c for c in unmatched_legends if str(c.get("block_id", "") or "") not in used_caption_ids]
        rejected_legends[:] = [c for c in rejected_legends if str(c.get("block_id", "") or "") not in used_caption_ids]
    if used_asset_ids:
        unmatched_assets[:] = [a for a in unmatched_assets if (int(a.get("page", 0) or 0), str(a.get("block_id", "") or "")) not in used_asset_ids]
# === Asset-internal figure number recovery ===
_FIGURE_DESCRIPTION_OPENING = re.compile(
    r"^(this|the)\s+figure\b", re.IGNORECASE
)

_INTERNAL_FIGURE_LABEL_PATTERN = re.compile(
    r"^(?:Figure|Fig\.?)\s+(\d+(?:\.\d+)?)(?:[A-Za-z])?"
    r"(?:\.\:?\s*)?(?:\S.*)?$",
    flags=re.IGNORECASE,
)


def _looks_like_internal_figure_label(text: str) -> bool:
    """Check if text looks like a bare figure label (e.g. 'Figure 2.' or 'Fig. 3: ...')."""
    stripped = " ".join(text.split())
    if len(stripped) < 6 or len(stripped) > 200:
        return False
    if not _INTERNAL_FIGURE_LABEL_PATTERN.match(stripped):
        return False
    lower = stripped.lower()
    if re.match(r"^(?:figure|fig\.?)\s+\d+\s+(?:shows|showed|demonstrates|illustrates|indicates)\b", lower):
        return False
    return True


def _needs_asset_internal_figure_number_recovery(fig: dict) -> bool:
    """Check if a matched figure entry is eligible for asset-internal number recovery.
    Works for both:
    - synthetic_figure entries (from vector fallback, require bbox_only/synthetic flags)
    - figure_unknown entries (from normal prematch, no flag requirement)
    """
    if fig.get("figure_number") is not None:
        return False
    figure_id = str(fig.get("figure_id") or "")
    is_synthetic = figure_id.startswith("synthetic_figure")
    is_unknown = figure_id.startswith("figure_unknown")
    if not is_synthetic and not is_unknown:
        return False
    # Synthetic figures require bbox_only_asset or synthetic_vector_asset flags
    if is_synthetic:
        flags = set(fig.get("flags") or [])
        if not ("bbox_only_asset" in flags or "synthetic_vector_asset" in flags):
            return False
    text = str(fig.get("text") or "").strip()
    if not text:
        return False
    lower = text.lower()
    return (
        bool(_FIGURE_DESCRIPTION_OPENING.match(text))
        or lower.startswith("this figure ")
        or lower.startswith("the figure ")
    )


def _line_inside_or_overlaps_asset(line_bbox, asset_bbox) -> bool:
    """Check if a PDF line's center is inside the asset bbox, or overlaps it significantly."""
    lx1, ly1, lx2, ly2 = line_bbox
    ax1, ay1, ax2, ay2 = asset_bbox
    line_area = max(1.0, (lx2 - lx1) * (ly2 - ly1))
    ix1, iy1 = max(lx1, ax1), max(ly1, ay1)
    ix2, iy2 = min(lx2, ax2), min(ly2, ay2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    cx = (lx1 + lx2) / 2
    cy = (ly1 + ly2) / 2
    center_inside = ax1 <= cx <= ax2 and ay1 <= cy <= ay2
    return center_inside or (inter / line_area) >= 0.7


def _asset_edge_band_score(line_bbox, asset_bbox) -> float:
    """Score how close a line is to the edge of an asset (label-like position).
    Returns 1.0 (tight edge), 0.7 (near edge), 0.4 (loose edge), or 0.0 (reject).
    Also rejects lines covering >15% of asset area.
    """
    lx1, ly1, lx2, ly2 = line_bbox
    ax1, ay1, ax2, ay2 = asset_bbox
    asset_w = max(1.0, ax2 - ax1)
    asset_h = max(1.0, ay2 - ay1)
    line_w = lx2 - lx1
    line_h = ly2 - ly1
    if (line_w * line_h) / (asset_w * asset_h) > 0.15:
        return 0.0
    cx = (lx1 + lx2) / 2
    cy = (ly1 + ly2) / 2
    left_dist = abs(cx - ax1)
    right_dist = abs(cx - ax2)
    top_dist = abs(cy - ay1)
    bottom_dist = abs(cy - ay2)
    edge_dist = min(left_dist / asset_w, right_dist / asset_w,
                    top_dist / asset_h, bottom_dist / asset_h)
    if edge_dist <= 0.08:
        return 1.0
    if edge_dist <= 0.15:
        return 0.7
    if edge_dist <= 0.25:
        return 0.4
    return 0.0


def _iter_matched_figure_assets(fig: dict) -> list[dict]:
    """Iterate matched_assets that have valid bboxes."""
    assets = fig.get("matched_assets") or []
    return [a for a in assets if a.get("bbox") and len(a.get("bbox", [])) >= 4]


def _recover_asset_internal_figure_number(
    pdf_lines: list[dict], asset: dict, existing_numbers: set,
) -> dict | None:
    """Scan pdf_lines for a figure label inside asset bbox.
    Returns recovery dict with figure_number, text, bbox, figure_namespace, or None.
    """
    ab = asset.get("bbox")
    if not ab or len(ab) < 4:
        return None
    candidates: list[dict] = []
    for line in pdf_lines:
        lb = line.get("bbox")
        if not lb or len(lb) < 4:
            continue
        if not _line_inside_or_overlaps_asset(lb, ab):
            continue
        text = str(line.get("text") or "").strip()
        if not text:
            continue
        if _looks_like_internal_figure_label(text):
            m = _INTERNAL_FIGURE_LABEL_PATTERN.match(" ".join(text.split()))
            if m:
                number = int(m.group(1))
                edge_score = _asset_edge_band_score(lb, ab)
                if edge_score > 0:
                    candidates.append({
                        "figure_namespace": "figure",
                        "figure_number": number,
                        "text": text,
                        "bbox": lb,
                        "edge_score": edge_score,
                    })
    if not candidates:
        return None
    # Multiple different figure numbers -> conflict, don't recover
    numbers = {(c["figure_namespace"], c["figure_number"]) for c in candidates}
    if len(numbers) > 1:
        return None
    best = max(candidates, key=lambda c: c["edge_score"])
    ns, number = best["figure_namespace"], best["figure_number"]
    if (ns, number) in existing_numbers:
        return None
    return {
        "figure_namespace": ns,
        "figure_number": number,
        "text": best["text"],
        "bbox": best["bbox"],
    }


def _recover_missing_figure_numbers_from_assets(
    inventory: dict,
    page_pdf_lines_by_page: dict[int, list[dict]] | None,
) -> None:
    """Inventory pass: for each matched figure missing a figure_number,
    scan its matched_assets' internal PDF lines to recover the number.
    """
    if not page_pdf_lines_by_page:
        return
    matched = inventory.setdefault("matched_figures", [])
    for idx, fig in enumerate(matched):
        if not _needs_asset_internal_figure_number_recovery(fig):
            continue
        page = int(fig.get("page", 0) or 0)
        page_lines = page_pdf_lines_by_page.get(page, [])
        if not page_lines:
            continue
        # Build existing figure numbers excluding current figure
        existing_numbers = {
            (other.get("figure_namespace") or "figure", other.get("figure_number"))
            for j, other in enumerate(matched)
            if j != idx and other.get("figure_number") is not None
        }
        assets = _iter_matched_figure_assets(fig)
        recovered = None
        for asset in assets:
            recovered = _recover_asset_internal_figure_number(page_lines, asset, existing_numbers)
            if recovered is not None:
                break
        if recovered is None:
            continue
        number = recovered["figure_number"]
        ns = recovered["figure_namespace"]
        # Update figure metadata
        fig["figure_namespace"] = ns
        fig["figure_number"] = number
        fig["figure_id"] = _format_figure_id(ns, number)
        fig["recovered_label_text"] = recovered["text"]
        fig["recovered_label_bbox"] = recovered["bbox"]
        fig["figure_number_source"] = "asset_internal_pdf_line"
        fig["flags"] = list(dict.fromkeys((fig.get("flags") or []) + [
            "figure_number_recovered_from_asset_text",
        ]))


def _recover_figure_heading_prefix(
    block: dict,
    page_pdf_lines_by_page: dict[int, list[dict]],
) -> str | None:
    """Recover 'FIGURE N' heading prefix from PDF text layer for OCR-missed captions.

    When PaddleOCR fails to detect a standalone 'Figure N' / 'FIGURE N' heading
    (e.g. rendered in a bold/small-caps font that the OCR engine doesn't read),
    the caption body is captured as figure_caption_candidate but lacks the
    figure number prefix. This function checks the PDF text layer for the
    heading on the same page and prepends it if the line immediately after
    the heading matches the start of the caption text.

    Returns the complete caption text with prefix, or None if no recovery.
    """
    page = int(block.get("page", 0) or 0)
    pdf_lines = page_pdf_lines_by_page.get(page)
    if not pdf_lines:
        return None

    block_text = str(block.get("text", "") or "").strip()
    if not block_text or len(block_text) < 20:
        return None

    # Sort PDF lines top-to-bottom by y-center
    sorted_lines = sorted(
        pdf_lines,
        key=lambda l: (l.get("bbox") or [0, 0, 0, 0])[1],
    )

    for i, line in enumerate(sorted_lines):
        line_text = str(line.get("text", "") or "").strip()
        # Check: line starts with Figure N heading (short heading, not in-text ref)
        m = _FIGURE_NUMBER_PATTERN.match(line_text)
        if not m or m.start() != 0:
            continue
        if len(line_text) > 40:
            continue  # too long for a heading — probably in-text reference

        # Check the next PDF line (by y-order) matches the start of block text
        if i + 1 >= len(sorted_lines):
            continue
        next_text = str(sorted_lines[i + 1].get("text", "") or "").strip()
        if not next_text or len(next_text) < 10:
            continue

        # Common-prefix match: at least 15 chars case-insensitive
        common = 0
        for a, b in zip(next_text.lower(), block_text.lower()):
            if a == b:
                common += 1
            else:
                break
        if common >= 15:
            return line_text + "\n" + block_text

    return None
