from __future__ import annotations

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
    "shows", "show", "shown", "illustrates", "illustrate",
    "depicts", "demonstrates", "demonstrate", "presents", "present",
    "indicates", "indicate", "reveals", "reveal", "suggests", "suggest",
    "summarizes", "summarize", "compares", "compare",
)


def _looks_like_inline_figure_mention(text: str) -> bool:
    t = " ".join(text.strip().split())
    lower = t.lower()

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
    if re.search(r'\$?\^\{[^}]+\}\$?', text):
        return True
    return False


def _is_body_mention(block: dict) -> bool:
    raw_role = block.get("raw_role", block.get("role", ""))
    if raw_role == "body_paragraph":
        return True
    if raw_role == "figure_caption_candidate":
        text = block.get("text", "")
        if text and _looks_like_figure_narrative_prose(text):
            return True
    if block.get("block_label", "") == "text":
        text = block.get("text", "")
        return bool(_BODY_MENTION_PATTERN.search(text))
    return False


_PANEL_SUBCAPTION_PATTERN = re.compile(r"^\s*[a-z][\.\)]\s")


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


def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    legends: list[dict] = []
    rejected_legends: list[dict] = []
    assets: list[dict] = []
    unmatched_legends: list[dict] = []
    unmatched_assets: list[dict] = []
    matched_figures: list[dict] = []
    unresolved_clusters: list[dict] = []

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
        if role in ("figure_caption", "figure_caption_candidate"):
            if _is_body_mention(block):
                continue
            if role == "figure_caption_candidate" and _looks_like_figure_narrative_prose(block.get("text", "")):
                continue
            if not _is_formal_legend(block.get("text", ""), block, page_width):
                block["caption_score"] = score_figure_caption(
                    block, nearby_media=False, caption_style_match=False,
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

    used_asset_indices: set[int] = set()
    ambiguous_figures: list[dict] = []
    for legend in ordered_legends:
        legend_page = legend.get("page", 0)
        legend_text = legend.get("text", "")
        fig_num = _extract_figure_number(legend_text)

        body_prose_likelihood = _looks_like_inline_figure_mention(legend_text)

        caption_score = score_figure_caption(
            legend,
            nearby_media=any(a.get("page", 0) == legend_page for a in assets),
            caption_style_match=_caption_style_match(legend, structured_blocks),
            body_prose_likelihood=body_prose_likelihood,
        )

        candidates = []
        for ai, asset in enumerate(assets):
            if ai in used_asset_indices or asset.get("page", 0) != legend_page:
                continue
            match_score = score_figure_match(legend, asset, caption_score=caption_score)
            if match_score["decision"] != "rejected":
                candidates.append((ai, asset, match_score))
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
                ambiguous_figures.append({
                    "legend_block_id": legend.get("block_id", ""),
                    "page": legend_page,
                    "caption_score": caption_score,
                    "candidates": [
                        {"asset_block_id": asset.get("block_id", ""), "match_score": score}
                        for _, asset, score in close
                    ],
                })
                ambiguous = True
                matched_assets = []
            else:
                best_idx, best_asset, best_score = candidates[0]
                matched_assets = [best_asset]
                used_asset_indices.add(best_idx)
                region_match = {"media_blocks": [best_asset], "match_score": best_score}

        is_legend_only = len(matched_assets) == 0

        if caption_score.get("score", 0.0) < 0.4:
            unmatched_legends.append(legend)
            continue

        fig_id = f"figure_{fig_num:03d}" if fig_num else f"unmatched_legend_{len(matched_figures):03d}"

        if not ambiguous:
            match_score = region_match["match_score"] if region_match is not None else {
                "score": 0.0,
                "decision": "legend_only",
                "evidence": ["no_asset_match"],
            }
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
                "confidence": match_score["score"],
                "match_score": match_score,
                "flags": [] if not is_legend_only else ["legend_only"],
                "caption_score": caption_score,
            }
            if region_match is not None and len(matched_assets) > 1:
                entry["cluster_bbox"] = region_match["cluster_bbox"]
            matched_figures.append(entry)

        if is_legend_only:
            unmatched_legends.append(legend)

    for i, asset in enumerate(assets):
        if i not in used_asset_indices:
            unmatched_assets.append(asset)

    # Build unresolved clusters: spatial clusters of unmatched assets on
    # pages where all candidate legends were rejected (multi-panel figures
    # with axis labels or informal captions)
    if rejected_legends and unmatched_assets:
        rejected_pages = {leg.get("page") for leg in rejected_legends if leg.get("page")}
        for cluster in _media_clusters(unmatched_assets, page_width):
            cluster_page = cluster[0].get("page", 0)
            if cluster_page not in rejected_pages:
                continue
            cluster_id = f"unresolved_cluster_{len(unresolved_clusters) + 1:03d}"
            cluster_ids = [b.get("block_id", "") for b in cluster]
            unresolved_clusters.append({
                "cluster_id": cluster_id,
                "media_block_ids": cluster_ids,
                "cluster_bbox": _cluster_bbox([b.get("bbox", [0, 0, 0, 0]) for b in cluster]),
                "page": cluster_page,
            })
        if unresolved_clusters:
            consumed = {bid for uc in unresolved_clusters for bid in uc["media_block_ids"]}
            unmatched_assets = [a for a in unmatched_assets if a.get("block_id", "") not in consumed]

    return {
        "figure_legends": legends,
        "figure_assets": assets,
        "matched_figures": matched_figures,
        "ambiguous_figures": ambiguous_figures,
        "unmatched_legends": unmatched_legends,
        "unmatched_assets": unmatched_assets,
        "rejected_legends": rejected_legends,
        "unresolved_clusters": unresolved_clusters,
        "official_figure_count": len(matched_figures),
    }


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
