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
    r"(?:S)?(\d+(?:\.\d+)?)",
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


def _looks_like_inline_figure_mention(text: str) -> bool:
    t = " ".join(text.strip().split())
    lower = t.lower()

    # Text starting with "Figure N." / "Fig. N." is a self-identifying
    # caption — never flag as body mention regardless of verb content.
    if re.match(r"^(?:Figure|Fig\.?)\s+\d+\b", t, re.IGNORECASE):
        return False

    if not re.search(r"\bfi(?:g(?:ure)?\.?\s*\d+)", lower):
        return False

    # Explicitly NOT inline: Frontiers format FIGURE N | ...
    if re.match(r"^figure\s+\d+[a-z]?\s*\|", t, re.I):
        return False

    # "as shown in Figure X" / "shown in Figure X" / "see Figure X"
    if re.search(r"\b(as shown in|shown in|see |according to|consistent with)\s+(fig(?:ure)?\.?\s*\d+)", lower):
        return True

    # Long sentence with a prose verb
    words = t.split()
    if len(words) >= 10 and any(re.search(rf"\b{v}\b", lower) for v in _INLINE_FIGURE_MENTION_VERBS):
        return True

    return False


def _extract_figure_number(text: str) -> int | None:
    m = _FIGURE_NUMBER_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


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

    return (
        zone in {"body_zone", "display_zone", "tail_nonref_hold_zone"}
        and style_family == "legend_like"
    ) or (
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


def _media_clusters(blocks: list[dict], page_width: float = 1200) -> list[list[dict]]:
    media = [
        b
        for b in blocks
        if not b.get("_non_body_media")
        and (
            b.get("role") == "figure_asset"
            or (b.get("role") == "media_asset" and b.get("raw_label", "") in {"image", "chart", "figure"})
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


def _bbox_width(bbox: list[float]) -> float:
    return float(bbox[2] - bbox[0])


def _bbox_height(bbox: list[float]) -> float:
    return float(bbox[3] - bbox[1])


def _bbox_center_y(bbox: list[float]) -> float:
    return float(bbox[1] + bbox[3]) / 2.0


def _candidate_group_entry(group_id: str, page: int, media_blocks: list[dict], group_type: str, evidence: list[str]) -> dict:
    return {
        "group_id": group_id,
        "page": page,
        "group_type": group_type,
        "asset_block_ids": [b.get("block_id") for b in media_blocks if b.get("block_id") is not None],
        "media_blocks": media_blocks,
        "cluster_bbox": _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in media_blocks]),
        "group_evidence": evidence,
    }


def _build_candidate_figure_groups_from_assets(assets: list[dict], page_width: float = 1200) -> list[dict]:
    media = [
        b for b in assets
        if not b.get("_non_body_media")
        and (b.get("role") == "figure_asset" or (b.get("role") == "media_asset" and b.get("raw_label", "") in {"image", "chart", "figure"}))
    ]
    media.sort(key=lambda b: (b.get("page", 0), (b.get("bbox") or [0, 0, 0, 0])[1], (b.get("bbox") or [0, 0, 0, 0])[0]))

    groups: list[dict] = []
    next_id = 1
    by_page: dict[int, list[dict]] = {}
    for block in media:
        by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    for page, page_media in by_page.items():
        for block in page_media:
            groups.append(_candidate_group_entry(f"group_{next_id:03d}", page, [block], "single_asset", ["single_asset"]))
            next_id += 1

        for start in range(len(page_media)):
            for size in (2, 3):
                chunk = page_media[start:start + size]
                if len(chunk) != size:
                    continue
                bboxes = [b.get("bbox", [0, 0, 0, 0]) for b in chunk]
                heights = [_bbox_height(bb) for bb in bboxes]
                centers_y = [_bbox_center_y(bb) for bb in bboxes]
                if max(centers_y) - min(centers_y) > max(40.0, min(heights) * 0.35):
                    continue
                if max(heights) - min(heights) > max(40.0, min(heights) * 0.4):
                    continue
                gaps = []
                ordered = sorted(chunk, key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[0])
                for left, right in zip(ordered, ordered[1:]):
                    lb = left.get("bbox", [0, 0, 0, 0])
                    rb = right.get("bbox", [0, 0, 0, 0])
                    gaps.append(max(0.0, rb[0] - lb[2]))
                if any(gap > page_width * 0.08 for gap in gaps):
                    continue
                group_type = "same_row_pair" if size == 2 else "same_row_triple"
                evidence = ["same_page", "same_row_band", "size_similar", "tight_horizontal_gap"]
                groups.append(_candidate_group_entry(f"group_{next_id:03d}", page, ordered, group_type, evidence))
                next_id += 1

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
    if group.get("group_type") == "single_asset":
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
        coherence_bonus = 0.05
        match_score = dict(match_score)
        match_score["score"] = min(1.0, match_score["score"] + coherence_bonus)
        match_score.setdefault("evidence", []).append("multi_asset_coherence_bonus")
        if match_score["score"] >= 0.6 and match_score.get("decision") == "ambiguous":
            match_score["decision"] = "matched"
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
            if cap.get("block_id") != legend.get("block_id")
            and (cap.get("bbox") or [0, 0, 0, 0])[1] > cy2
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
            min_width = max(1.0, min(cx2 - cx1, ax2 - ax1))
            wide_enough_overlap = horizontal_overlap >= min_width * 0.25
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
            if _is_body_mention(block):
                continue
            if (
                role == "figure_caption_candidate"
                and str(block.get("zone") or "") != "display_zone"
                and str(block.get("style_family") or "") != "legend_like"
                and _looks_like_figure_narrative_prose(block.get("text", ""))
                and _extract_figure_number(block.get("text", "")) is None
            ):
                continue
            if not _is_formal_legend(block.get("text", ""), block, page_width):
                block["caption_score"] = score_figure_caption(
                    block,
                    nearby_media=False,
                    caption_style_match=False,
                    body_prose_likelihood=_looks_like_inline_figure_mention(block.get("text", "")),
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

    numbered_legends = [leg for leg in legends if _extract_figure_number(leg.get("text", "")) is not None]
    unnumbered_legends = [leg for leg in legends if _extract_figure_number(leg.get("text", "")) is None]
    ordered_legends = numbered_legends + unnumbered_legends

    # Deduplicate legends by figure number — keep the version on a page that
    # has assets, otherwise keep the first occurrence
    _dedup_map: dict[int, dict] = {}
    for legend in ordered_legends:
        fn = _extract_figure_number(legend.get("text", ""))
        if fn is None:
            continue
        if fn not in _dedup_map:
            _dedup_map[fn] = legend
        else:
            existing = _dedup_map[fn]
            existing_has_asset = any(a.get("page") == existing.get("page") for a in assets)
            current_has_asset = any(a.get("page") == legend.get("page") for a in assets)
            if current_has_asset and not existing_has_asset:
                _dedup_map[fn] = legend
            elif not current_has_asset and not existing_has_asset:
                # Both copies on pages without assets — keep the later one
                # (figure compilations are always after the body)
                if (legend.get("page", 0) or 0) > (existing.get("page", 0) or 0):
                    _dedup_map[fn] = legend

    seen_fig_nums: set[int] = set()
    deduped_legends: list[dict] = []
    deduped_legend_ids: list[dict] = []
    for legend in ordered_legends:
        fn = _extract_figure_number(legend.get("text", ""))
        if fn is not None:
            if fn in seen_fig_nums:
                deduped_legend_ids.append({
                    "page": legend.get("page"),
                    "block_id": legend.get("block_id", ""),
                })
                continue
            seen_fig_nums.add(fn)
            deduped_legends.append(_dedup_map[fn])
        else:
            deduped_legends.append(legend)
    ordered_legends = deduped_legends

    candidate_groups = _build_candidate_figure_groups_from_assets(assets, page_width=page_width)
    used_asset_page_ids: set[tuple] = set()
    page_caption_index = _formal_figure_caption_blocks(structured_blocks)
    for legend in ordered_legends:
        legend_page = legend.get("page", 0)
        legend_text = legend.get("text", "")
        fig_num = _extract_figure_number(legend_text)
        is_validation_first_candidate = _is_validation_first_legend_candidate(legend)
        is_weak_truncated = _is_insufficient_legend_evidence(legend)

        body_prose_likelihood = _looks_like_inline_figure_mention(legend_text)

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
                legend_bb = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
                lcx = (legend_bb[0] + legend_bb[2]) / 2 if len(legend_bb) >= 4 else 0
                best = close[0]
                best_delta = abs(
                    lcx - ((best[1].get("cluster_bbox", [0, 0, 0, 0])[0] + best[1].get("cluster_bbox", [0, 0, 0, 0])[2]) / 2)
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
                    ambiguous_figures.append(
                        {
                            "legend_block_id": legend.get("block_id", ""),
                            "page": legend_page,
                            "caption_score": caption_score,
                            "candidates": [
                                {
                                    "asset_block_id": g.get("media_blocks", [{}])[0].get("block_id", ""),
                                    "group_type": g.get("group_type", ""),
                                    "match_score": s,
                                }
                                for _, g, s in close
                            ],
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
                    ambiguous_figures.append(
                        {
                            "legend_block_id": legend.get("block_id", ""),
                            "page": legend_page,
                            "caption_score": caption_score,
                            "candidates": [
                                {
                                    "asset_block_id": best_group.get("media_blocks", [{}])[0].get("block_id", ""),
                                    "group_type": best_group.get("group_type", ""),
                                    "match_score": best_score,
                                }
                            ],
                        }
                    )
                    ambiguous = True

        is_legend_only = len(matched_assets) == 0

        if caption_score.get("score", 0.0) < 0.4:
            unmatched_legends.append(legend)
            continue

        if is_weak_truncated and is_validation_first_candidate:
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

        if is_weak_truncated:
            ambiguous_figures.append(
                {
                    "legend_block_id": legend.get("block_id", ""),
                    "page": legend_page,
                    "text": legend_text,
                    "figure_number": fig_num,
                    "caption_score": caption_score,
                    "candidates": [],
                    "hold_reason": "ambiguous_truncated_legend",
                    "zone": legend.get("zone"),
                    "style_family": legend.get("style_family"),
                    "marker_signature": legend.get("marker_signature") or {},
                }
            )
            unmatched_legends.append(legend)
            continue

        if is_legend_only:
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

        fig_id = f"figure_{fig_num:03d}" if fig_num else f"figure_unknown_{len(matched_figures):03d}"
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
        if region_match is not None and len(matched_assets) > 1:
            entry["cluster_bbox"] = region_match["cluster_bbox"]
        matched_figures.append(entry)

    for _i, asset in enumerate(assets):
        asset_page = asset.get("page")
        asset_bid = asset.get("block_id", "")
        if not asset_bid or (asset_page, asset_bid) not in used_asset_page_ids:
            unmatched_assets.append(asset)

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
        seq_matched: list[dict] = []
        for cap in sorted_caps:
            fn = _extract_figure_number(cap.get("text", ""))
            if fn is None:
                continue
            while ai < len(sorted_asts):
                asset = sorted_asts[ai]
                ap = asset.get("page", 0) or 0
                cp = cap.get("page", 0) or 0
                if ap >= cp:
                    break
                ai += 1
            if ai >= len(sorted_asts):
                break
            asset = sorted_asts[ai]
            asset_bid = asset.get("block_id", "")
            asset_page = asset.get("page", 0)
            if asset_bid is not None and (asset_page, asset_bid) in used_asset_page_ids:
                ai += 1
                continue
            ai += 1
            fig_id = f"figure_{fn:03d}"
            caption_score = score_figure_caption(
                cap, nearby_media=True, caption_style_match=False, body_prose_likelihood=False
            )
            seq_matched.append(cap)
            matched_figures.append({
                "figure_id": fig_id,
                "legend_block_id": cap.get("block_id", ""),
                "page": asset.get("page", 0),
                "text": cap.get("text", ""),
                "figure_number": fn,
                "matched_assets": [{
                    "block_id": asset.get("block_id", ""),
                    "bbox": asset.get("bbox", [0, 0, 0, 0]),
                }],
                "group_type": "",
                "group_evidence": [],
                "confidence": 0.35,
                "match_score": {"score": 0.35, "decision": "matched", "evidence": ["sequential_fallback"]},
                "flags": ["sequential_match"],
                "caption_score": caption_score,
            })
            if asset_bid:
                used_asset_page_ids.add((asset_page, asset_bid))
        for cap in seq_matched:
            unmatched_legends[:] = [l for l in unmatched_legends if l is not cap]

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
        r"(?:S)?(\d+(?:\.\d+)?)",
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
            promoted_entry = {
                "figure_id": f"figure_{fn:03d}",
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


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
