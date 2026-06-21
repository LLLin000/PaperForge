from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json
from paperforge.worker.ocr_roles import _PANEL_LABEL_PATTERN
from paperforge.worker.ocr_scores import score_figure_caption, score_figure_match

_FIGURE_NUMBER_PATTERN = re.compile(
    r"(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+"
    r"(?:S\.?\s*)?(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
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
        if role not in ("body_paragraph", "section_heading", "subsection_heading",
                        "backmatter_heading", "backmatter_body"):
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


def _asset_gap_left(a: dict, b: dict) -> float:
    ab = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    return max(0.0, ab[0] - bb[2])


def _asset_gap_above(a: dict, b: dict) -> float:
    ab = a.get("bbox") or [0, 0, 0, 0]
    bb = b.get("bbox") or [0, 0, 0, 0]
    return max(0.0, ab[1] - bb[3])


def _grow_region_from_seed(seed: dict, others: list[dict], page_width: float) -> dict:
    group = [seed]
    growth_steps: list[dict] = []
    remaining = list(others)
    changed = True
    while changed:
        changed = False
        group_bbox = _cluster_bbox([g.get("bbox", [0, 0, 0, 0]) for g in group])
        next_remaining = []
        for candidate in remaining:
            reason = None
            cb = candidate.get("bbox") or [0, 0, 0, 0]
            if cb[0] >= group_bbox[2] and _asset_gap_right({"bbox": group_bbox}, candidate) <= max(page_width * 0.08, 40):
                reason = "adjacent_right"
            elif cb[1] >= group_bbox[3] and _asset_gap_below({"bbox": group_bbox}, candidate) <= max(page_width * 0.08, 40):
                reason = "adjacent_below"
            elif cb[2] <= group_bbox[0] and _asset_gap_left({"bbox": group_bbox}, candidate) <= max(page_width * 0.08, 40):
                reason = "adjacent_left"
            elif cb[3] <= group_bbox[1] and _asset_gap_above({"bbox": group_bbox}, candidate) <= max(page_width * 0.08, 40):
                reason = "adjacent_above"
            if reason:
                group.append(candidate)
                growth_steps.append({"added_block_id": candidate.get("block_id", ""), "reason": reason})
                changed = True
            else:
                next_remaining.append(candidate)
        remaining = next_remaining
    return {
        "seed_asset_block_id": seed.get("block_id", ""),
        "asset_block_ids": [g.get("block_id", "") for g in group if g.get("block_id")],
        "growth_steps": growth_steps,
        "group_bbox": _cluster_bbox([g.get("bbox", [0, 0, 0, 0]) for g in group]),
    }


def _validate_grown_region(group: dict, assets: list[dict], competing_caption_bboxes: list[list[float]] | None = None) -> dict:
    competing_caption_bboxes = competing_caption_bboxes or []
    asset_map = {str(a.get("block_id", "")): a for a in assets}
    group_assets = [asset_map[bid] for bid in group.get("asset_block_ids", []) if bid in asset_map]
    if len(group_assets) <= 1:
        return {"validation_status": "strict_match_ok", "validation_reason": "single_asset"}

    ordered = sorted(group_assets, key=lambda a: (a.get("bbox") or [0, 0, 0, 0])[0])
    max_gap = 0.0
    for left, right in zip(ordered, ordered[1:], strict=False):
        lb = left.get("bbox") or [0, 0, 0, 0]
        rb = right.get("bbox") or [0, 0, 0, 0]
        max_gap = max(max_gap, max(0.0, rb[0] - lb[2]))
    if max_gap > 250.0:
        return {"validation_status": "split_required", "validation_reason": "gap_too_large"}

    gb = group.get("group_bbox") or [0, 0, 0, 0]
    for cb in competing_caption_bboxes:
        if len(gb) >= 4 and len(cb) >= 4 and cb[0] < gb[2] and gb[0] < cb[2]:
            return {"validation_status": "grouped_evidence_only", "validation_reason": "crosses_competing_caption_zone"}

    return {"validation_status": "strict_match_ok", "validation_reason": "local_growth_validated"}


def _media_clusters(blocks: list[dict], page_width: float = 1200) -> list[list[dict]]:
    media = [
        b
        for b in blocks
        if not b.get("_non_body_media")
        and (
            b.get("role") == "figure_asset"
            or (b.get("role") == "media_asset" and (
                b.get("raw_label", "") in {"image", "chart", "figure"}
                or (b.get("raw_label", "") == "table" and "<img" in str(b.get("text") or "").lower())
            ))
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
            if rl in {"image", "chart", "figure"}:
                result.append(b)
            elif not rl.strip():
                result.append(b)
            elif rl == "table" and "<img" in str(b.get("text", "") or "").lower():
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


def _build_candidate_figure_groups_from_assets(
    assets: list[dict],
    all_blocks: list[dict],
    legends: list[dict],
    page_width: float = 1200,
) -> list[dict]:
    media = _filter_figure_assets(assets)
    groups: list[dict] = []
    next_id = 1

    def _estimate_page_height(page_blocks: list[dict]) -> float:
        explicit = [float(b["page_height"]) for b in page_blocks if b.get("page_height")]
        if explicit:
            return max(explicit)
        bottoms = [
            float((b.get("bbox") or [0, 0, 0, 0])[3])
            for b in page_blocks if len(b.get("bbox") or []) >= 4
        ]
        return max(bottoms, default=1600.0)

    by_page: dict[int, list[dict]] = {}
    for block in media:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_media in by_page.items():
        page_blocks = [b for b in all_blocks if int(b.get("page", 0) or 0) == page]
        page_height = _estimate_page_height(page_blocks)

        page_legends = [l for l in legends if l.get("page") == page]
        n_legends = len(page_legends)

        # Multi-legend: partition by caption bands first
        if n_legends >= 2:
            band_map = _partition_assets_by_caption_bands(page_legends, page_media, page_height)
            partitions: list[tuple[str | None, list[dict]]] = [
                (band_id, list(assets)) for band_id, assets in band_map.items() if assets
            ]
            assigned_ids = {id(a) for _, p in partitions for a in p}
            free = [a for a in page_media if id(a) not in assigned_ids]
            if free:
                partitions.append((None, free))
        else:
            partitions = [(None, list(page_media))]

        # Cluster each partition
        page_groups: list[dict] = []
        for band_id, partition in partitions:
            if not partition:
                continue
            clusters = _cluster_page_assets(partition, page_blocks, n_legends, page_width, page_height)
            for cluster in clusters:
                gt = "distance_cluster" if len(cluster) >= 2 else "single_asset"
                entry = _candidate_group_entry(
                    f"group_{next_id:04d}", page, cluster, gt,
                    ["same_page", "distance_clustered" if gt == "distance_cluster" else "single_asset"],
                )
                entry["caption_band_id"] = band_id
                entry["page_legend_count"] = n_legends
                entry["safe_auto_match"] = False
                page_groups.append(entry)
                next_id += 1

        page_group_count = len(page_groups)
        page_distance_cluster_count = sum(1 for g in page_groups if g["group_type"] == "distance_cluster")
        for g in page_groups:
            g["page_group_count"] = page_group_count
            g["page_distance_cluster_count"] = page_distance_cluster_count
            g["safe_auto_match"] = (
                n_legends == 1
                and page_group_count == 1
                and g["group_type"] == "distance_cluster"
                and len(g.get("media_blocks", [])) >= 2
            )

        groups.extend(page_groups)

    return groups


def _score_legend_to_group(
    legend: dict,
    group: dict,
    *,
    caption_score: dict,
    page_width: float = 1200,
    anchor_supported: bool = False,
    caption_text_supported: bool = False,
    family_supported: bool = False,
    zone_supported: bool = False,
) -> dict:
    gt = group.get("group_type", "")

    if gt == "distance_cluster":
        num_assets = len(group.get("media_blocks", []))
        if group.get("safe_auto_match") and num_assets >= 2:
            return {"score": 0.85, "decision": "matched",
                    "evidence": ["same_page", "distance_clustered", "safe_auto_match"]}

        cluster_bbox = group.get("cluster_bbox", [0, 0, 0, 0])
        match_score = score_figure_match(
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
        basic = {
            "score": 0.55,
            "decision": "matched",
            "evidence": ["same_page", "page_assets_group"],
        }
        if family_supported:
            basic["score"] = min(1.0, basic["score"] + 0.1)
            basic["evidence"].append("family_supported")
        return basic

    if gt == "single_asset":
        asset = group["media_blocks"][0]
        return score_figure_match(
            legend,
            asset,
            caption_score=caption_score,
            anchor_supported=anchor_supported,
            caption_text_supported=caption_text_supported,
            family_supported=family_supported,
            zone_supported=zone_supported,
        )

    cluster_bbox = group.get("cluster_bbox", [0, 0, 0, 0])
    match_score = score_figure_match(
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


def _expand_matched_assets_locally(
    legend: dict,
    matched_assets: list[dict],
    assets: list[dict],
    used_asset_page_ids: set[tuple],
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
            if not aid or (ap, aid) in used_asset_page_ids:
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
                used_asset_page_ids.add((ap, aid))
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
    centers = [((cap.get("bbox") or [0, 0, 0, 0])[0] + (cap.get("bbox") or [0, 0, 0, 0])[2]) / 2 for cap in formal]
    if max(centers) - min(centers) > page_width * 0.08:
        return []
    ordered = sorted(formal, key=lambda cap: (cap.get("bbox") or [0, 0, 0, 0])[1])
    return ordered


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


def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    legends: list[dict] = []
    held_figures: list[dict] = []
    rejected_legends: list[dict] = []
    assets: list[dict] = []
    unmatched_legends: list[dict] = []
    unmatched_assets: list[dict] = []
    matched_figures: list[dict] = []
    unresolved_clusters: list[dict] = []
    ambiguous_figures: list[dict] = []
    used_group_ids: set[str] = set()

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
        is_validation_first_candidate = _is_validation_first_legend_candidate(block)
        if role in ("figure_caption", "figure_caption_candidate") or is_validation_first_candidate:
            if role == "figure_caption_candidate" and (
                str(block.get("zone") or "") == "body_zone"
                or (
                    str(block.get("zone") or "") != "display_zone"
                    and str(block.get("style_family") or "") != "legend_like"
                    and _looks_like_figure_narrative_prose(block.get("text", ""))
                    and _extract_figure_number(block.get("text", "")) is None
                )
            ):
                continue
            if not _is_formal_legend(block.get("text", ""), block, page_width):
                block["caption_score"] = score_figure_caption(
                    block,
                    nearby_media=False,
                    caption_style_match=False,
                    body_prose_likelihood=_looks_like_inline_figure_mention(block.get("text", ""), block),
                )
                rejected_legends.append(block)
            else:
                legends.append(block)
        elif role == "figure_asset":
            assets.append(block)
        elif role == "media_asset":
            raw_label = str(block.get("raw_label", "")).strip()
            if raw_label in {"image", "chart", "figure_title", "figure"} or not raw_label:
                assets.append(block)
            elif raw_label == "table" and "<img" in str(block.get("text") or "").lower():
                assets.append(block)

    numbered_legends = [leg for leg in legends if _extract_figure_number(leg.get("text", "")) is not None]
    unnumbered_legends = [leg for leg in legends if _extract_figure_number(leg.get("text", "")) is None]
    ordered_legends = numbered_legends + unnumbered_legends

    # Deduplicate legends by (namespace, figure_number) — keep the version on a page that
    # has assets, otherwise keep the first occurrence.
    # Namespace separation prevents "Figure 1" and "Supplementary Figure S1" from colliding.
    _dedup_map: dict[tuple[str, int], dict] = {}
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
            existing_has_asset = any(a.get("page") == existing.get("page") for a in assets)
            current_has_asset = any(a.get("page") == legend.get("page") for a in assets)
            if current_has_asset and not existing_has_asset:
                _dedup_map[key] = legend
            elif current_has_asset and existing_has_asset or not current_has_asset and not existing_has_asset:
                existing_role = str(existing.get("role") or "")
                current_role = str(legend.get("role") or "")
                if current_role == "figure_caption" and existing_role != "figure_caption":
                    _dedup_map[key] = legend

    seen_fig_keys: set[tuple[str, int]] = set()
    deduped_legends: list[dict] = []
    deduped_legend_ids: list[dict] = []
    for legend in ordered_legends:
        text = legend.get("text", "")
        fn = _extract_figure_number(text)
        if fn is not None:
            ns = _extract_figure_namespace(text)
            key = (ns, fn)
            if key in seen_fig_keys:
                deduped_legend_ids.append(
                    {
                        "page": legend.get("page"),
                        "block_id": legend.get("block_id", ""),
                    }
                )
                continue
            seen_fig_keys.add(key)
            deduped_legends.append(_dedup_map[key])
        else:
            deduped_legends.append(legend)
    ordered_legends = deduped_legends

    candidate_groups = _build_candidate_figure_groups_from_assets(
        assets, structured_blocks, ordered_legends, page_width=page_width,
    )

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

    used_asset_page_ids: set[tuple] = set()
    page_caption_index = _formal_figure_caption_blocks(structured_blocks)
    for legend in ordered_legends:
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

        candidates = []
        anchor_supported = _has_anchor_supported_legend_context(legend)
        caption_text_supported = _has_strong_explicit_caption_text(legend)
        family_supported = is_validation_first_candidate and str(legend.get("style_family") or "") == "legend_like"
        zone_supported = is_validation_first_candidate and str(legend.get("zone") or "") in {
            "body_zone",
            "display_zone",
        }

        for gi, group in enumerate(candidate_groups):
            if group.get("page") != legend_page:
                continue
            g_asset_block_ids = set(group.get("asset_block_ids", []))
            g_page = group.get("page", 0)
            g_qual = {(g_page, bid) for bid in g_asset_block_ids}
            if g_qual & used_asset_page_ids:
                continue
            match_score = _score_legend_to_group(
                legend,
                group,
                caption_score=caption_score,
                page_width=page_width,
                anchor_supported=anchor_supported,
                caption_text_supported=caption_text_supported,
                family_supported=family_supported,
                zone_supported=zone_supported,
            )
            if match_score["decision"] != "rejected":
                candidates.append((gi, group, match_score))
        candidates.sort(key=lambda item: item[2]["score"], reverse=True)

        matched_assets = []
        region_match = None
        ambiguous = False

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
                    page_assets_candidate = next((item for item in close if item[1].get("group_type") == "page_assets"), None)
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
                        matched_assets = best_group.get("media_blocks", [])
                        g_page = best_group.get("page", 0)
                        used_asset_page_ids.update({(g_page, bid) for bid in best_group.get("asset_block_ids", [])})
                        used_group_ids.add(str(best_group.get("group_id", "")))
                        matched_assets = _expand_matched_assets_locally(
                            legend,
                            matched_assets,
                            assets,
                            used_asset_page_ids,
                            page_caption_index.get(g_page, []),
                        )
                        region_match = {
                            "media_blocks": matched_assets,
                            "match_score": best_score,
                            "group_type": best_group.get("group_type", ""),
                            "group_evidence": best_group.get("group_evidence", []),
                        }
                        if len(matched_assets) > 1:
                            region_match["cluster_bbox"] = best_group.get("cluster_bbox", [0, 0, 0, 0])
                    else:
                        if fig_num is None and str(legend.get("role") or "") in ("figure_caption", "figure_caption_candidate") and len(legend_text) < 80:
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
                    matched_assets = best_group.get("media_blocks", [])
                    g_page = best_group.get("page", 0)
                    used_asset_page_ids.update({(g_page, bid) for bid in best_group.get("asset_block_ids", [])})
                    used_group_ids.add(str(best_group.get("group_id", "")))
                    matched_assets = _expand_matched_assets_locally(
                        legend,
                        matched_assets,
                        assets,
                        used_asset_page_ids,
                        page_caption_index.get(g_page, []),
                    )
                    region_match = {
                        "media_blocks": matched_assets,
                        "match_score": best_score,
                        "group_type": best_group.get("group_type", ""),
                        "group_evidence": best_group.get("group_evidence", []),
                    }
                    if len(matched_assets) > 1:
                        region_match["cluster_bbox"] = best_group.get("cluster_bbox", [0, 0, 0, 0])
                else:
                    if fig_num is None and str(legend.get("role") or "") in ("figure_caption", "figure_caption_candidate"):
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
                1 for leg in ordered_legends
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
            "matched_assets": [
                {
                    "block_id": a.get("block_id", ""),
                    "bbox": a.get("bbox", [0, 0, 0, 0]),
                }
                for a in matched_assets
            ],
            "group_type": region_match.get("group_type", "") if region_match is not None else "",
            "group_evidence": region_match.get("group_evidence", []) if region_match is not None else [],
            "confidence": match_score["score"],
            "match_score": match_score,
            "flags": [],
            "caption_score": caption_score,
        }
        local_bridges = _collect_bridge_blocks(int(legend_page or 0))
        entry["asset_block_ids"] = [str(a.get("block_id", "")) for a in matched_assets if a.get("block_id")]
        entry["bridge_block_ids"] = [str(b.get("block_id", "")) for b in local_bridges if b.get("block_id")]
        if len(matched_assets) > 1:
            entry["cluster_bbox"] = _cluster_bbox([a.get("bbox", [0, 0, 0, 0]) for a in matched_assets])
        matched_figures.append(entry)

    for _i, asset in enumerate(assets):
        asset_page = asset.get("page")
        asset_bid = asset.get("block_id", "")
        if not asset_bid or (asset_page, asset_bid) not in used_asset_page_ids:
            unmatched_assets.append(asset)

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
        sidecar_page_height = float(
            max((b.get("bbox") or [0, 0, 0, 0])[3] for b in structured_blocks if b.get("page") == sidecar_page) or 1600
        )
        band_map = _partition_assets_by_caption_bands(narrow_set, page_assets_list, sidecar_page_height)
        sidecar_promoted: list[dict] = []
        sidecar_consumed_ids: set[tuple] = set()
        for cap in narrow_set:
            lid = str(cap.get("block_id", ""))
            cap_text = str(cap.get("text") or "")
            fig_num = _extract_figure_number(cap_text)
            cap_ns = _extract_figure_namespace(cap_text)
            band_assets = band_map.get(lid, [])
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
                "group_type": "sidecar_partition",
                "group_evidence": ["same_page", "narrow_caption_column", "sidecar_fallback"],
                "confidence": 0.5,
                "match_score": {"score": 0.5, "decision": "matched", "evidence": ["sidecar_fallback"]},
                "flags": ["sidecar_match"],
                "caption_score": score_figure_caption(
                    cap, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
                ),
            }
            if len(band_assets) > 1:
                sidecar_entry["cluster_bbox"] = _cluster_bbox([a.get("bbox", [0, 0, 0, 0]) for a in band_assets])
            sidecar_promoted.append(sidecar_entry)
        if not sidecar_promoted:
            continue
        matched_figures = [mf for mf in matched_figures if str(mf.get("legend_block_id", "")) not in nid_set]
        for legend in list(legends):
            if str(legend.get("block_id", "")) in nid_set:
                ambiguous_figures[:] = [
                    af
                    for af in ambiguous_figures
                    if str(af.get("legend_block_id", "")) != str(legend.get("block_id", ""))
                ]
                unmatched_legends[:] = [
                    ul for ul in unmatched_legends if str(ul.get("block_id", "")) != str(legend.get("block_id", ""))
                ]
        matched_figures.extend(sidecar_promoted)
        used_asset_page_ids.update(sidecar_consumed_ids)

    # Preproof legend-bundling: when a page packs 3+ figure captions
    # with zero same-page assets, match them 1:1 by page order to
    # subsequent pages that each hold unclaimed assets.
    if unmatched_legends and unmatched_assets:
        page_captions: dict[int, list[dict]] = {}
        for leg in unmatched_legends:
            cp = int(leg.get("page", 0) or 0)
            if _extract_figure_number(str(leg.get("text", ""))) is not None:
                page_captions.setdefault(cp, []).append(leg)
        for cp, caps in sorted(page_captions.items()):
            if len(caps) < 3:
                continue
            page_has_assets = any(
                a.get("page", 0) == cp for a in unmatched_assets
            )
            if page_has_assets:
                continue
            caps_sorted = sorted(caps, key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
            # Collect subsequent pages with unclaimed assets and no captions
            asset_pages: dict[int, list[dict]] = {}
            for ast in unmatched_assets:
                ap = int(ast.get("page", 0) or 0)
                bid = ast.get("block_id", "")
                if ap <= cp:
                    continue
                if bid and (ap, bid) in used_asset_page_ids:
                    continue
                asset_pages.setdefault(ap, []).append(ast)
            page_order = sorted(asset_pages.keys())
            # Validate: no body/table blocks between legend page and first asset page,
            # and each asset page is free of competing body/table text.
            _NON_PURE_ROLES = {"body_paragraph", "section_heading", "subsection_heading",
                               "table_caption", "table_asset", "table_html",
                               "backmatter_heading", "backmatter_body", "reference_item"}
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
                    b.get("page", 0) == ap and b.get("role", "") in _NON_PURE_ROLES
                    for b in structured_blocks
                )
                if not page_has_body:
                    valid_pages.append(ap)
            if len(valid_pages) < len(caps_sorted):
                caps_sorted = caps_sorted[:len(valid_pages)]
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
                        used_asset_page_ids.add((ap, bid))
                    consumed.append({
                        "block_id": bid,
                        "bbox": ast.get("bbox", [0, 0, 0, 0]),
                    })
                unmatched_legends = [l for l in unmatched_legends if l.get("block_id") != cap.get("block_id")]
                matched_figures.append({
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
                })
            # De-dup ambiguous_figures: remove entries whose legend_block_id
            # was already matched by the bundle pass.
            bundle_legend_ids = {m["legend_block_id"] for m in matched_figures if "legend_bundle_match" in m.get("flags", [])}
            ambiguous_figures[:] = [a for a in ambiguous_figures if a.get("legend_block_id") not in bundle_legend_ids]

    # === Group-aware sequential fallback ===
    # Consume unmatched distance_clusters that no same-page legend claimed.
    # Inserted AFTER preproof fallback, BEFORE old single-asset sequential fallback.
    local_asset_by_page_id: dict[tuple[int, str], dict] = {}
    for block in _filter_figure_assets(assets):
        local_asset_by_page_id[(int(block.get("page", 0) or 0), str(block.get("block_id", "")))] = block

    unmatched_groups = [
        g for g in candidate_groups
        if str(g.get("group_id", "")) not in used_group_ids
        and g.get("group_type") == "distance_cluster"
        and not any(
            (int(g.get("page", 0) or 0), str(bid)) in used_asset_page_ids
            for bid in g.get("asset_block_ids", [])
            if bid is not None
        )
    ]
    unmatched_groups.sort(key=lambda g: (
        int(g.get("page", 0) or 0),
        (g.get("cluster_bbox") or [0, 0, 0, 0])[1],
    ))

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
            for sg in same_page:
                sg_score = _score_legend_to_group(
                    legend, sg,
                    caption_score=score_figure_caption(
                        legend, nearby_media=True, caption_style_match=False,
                        body_prose_likelihood=False,
                    ),
                    page_width=page_width,
                )
                if sg_score.get("decision") == "matched" and sg_score.get("score", 0.0) >= 0.5:
                    best_group = sg
                    break
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
            legend, nearby_media=True, caption_style_match=False,
            body_prose_likelihood=False,
        )

        group_assets = []
        for bid in best_group.get("asset_block_ids", []):
            if bid is None:
                continue
            asset = local_asset_by_page_id.get((group_page, str(bid)))
            if asset:
                group_assets.append(asset)
                used_asset_page_ids.add((group_page, str(bid)))

        if not group_assets:
            continue

        matched_figures.append({
            "figure_id": fig_id,
            "figure_namespace": cap_ns,
            "legend_block_id": legend.get("block_id", ""),
            "page": group_page,
            "text": cap_text,
            "figure_number": fn,
            "matched_assets": [
                {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])}
                for a in group_assets
            ],
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
        })

        used_group_ids.add(str(best_group.get("group_id", "")))
        unmatched_legends.remove(legend)
        ambiguous_figures[:] = [
            af for af in ambiguous_figures
            if str(af.get("legend_block_id", "")) != str(legend.get("block_id", ""))
        ]

    # === End group-aware fallback ===

    # Sequential fallback: match unmatched captions to remaining assets in reading order.
    # Captions and figures often appear on different pages — humans match them by
    # sequential reading order, not spatial proximity. This is a necessary tradeoff.
    # Run BEFORE cluster building so sequential matching gets first pick of assets.
    if unmatched_legends and unmatched_assets:
        sorted_caps = sorted(
            unmatched_legends,
            key=lambda b: (b.get("page", 0) or 0, (b.get("bbox") or [0, 0, 0, 0])[1]),
        )
        sorted_asts = sorted(
            unmatched_assets,
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
                if fap in (cp, cp + 1):
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
                    "matched_assets": [
                        {
                            "block_id": asset.get("block_id", ""),
                            "bbox": asset.get("bbox", [0, 0, 0, 0]),
                        }
                    ],
                    "group_type": "",
                    "group_evidence": [],
                    "confidence": 0.35,
                    "match_score": {"score": 0.35, "decision": "matched", "evidence": ["sequential_fallback"]},
                    "flags": ["sequential_match"],
                    "caption_score": caption_score,
                }
            )
            if asset_bid:
                used_asset_page_ids.add((asset_page, asset_bid))
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
            consumed = {bid for uc in unresolved_clusters for bid in uc["media_block_ids"]}
            unmatched_assets = [a for a in unmatched_assets if a.get("block_id", "") not in consumed]

    inventory = {
        "figure_legends": deduped_legends,
        "figure_assets": assets,
        "matched_figures": matched_figures,
        "held_figures": held_figures,
        "ambiguous_figures": ambiguous_figures,
        "unmatched_legends": unmatched_legends,
        "unmatched_assets": unmatched_assets,
        "rejected_legends": rejected_legends,
        "unresolved_clusters": unresolved_clusters,
        "deduped_legend_ids": deduped_legend_ids,
        "official_figure_count": len(matched_figures),
    }

    inventory = _promote_sequence_matches(inventory, structured_blocks)

    inventory["figure_legend_completeness"] = compute_figure_legend_completeness(
        structured_blocks,
        inventory,
    )

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
                remaining_ambiguous.append(af)
                continue
            ns_promoted = _extract_figure_namespace(af.get("text", ""))
            promoted_entry = {
                "figure_id": _format_figure_id(ns_promoted, fn),
                "figure_namespace": ns_promoted,
                "legend_block_id": af.get("legend_block_id", ""),
                "page": af.get("page"),
                "text": af.get("text", ""),
                "figure_number": fn,
                "matched_assets": [],
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


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
