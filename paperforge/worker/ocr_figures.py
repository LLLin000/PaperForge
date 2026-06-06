from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json

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


def _is_body_mention(block: dict) -> bool:
    raw_role = block.get("raw_role", block.get("role", ""))
    if raw_role == "body_paragraph":
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
        if b.get("role") == "figure_asset"
        or (b.get("role") == "media_asset" and b.get("raw_label", "") in {"image", "chart", "figure"})
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

    for block in structured_blocks:
        if block.get("page_width"):
            page_width = float(block["page_width"])

    for block in structured_blocks:
        role = block.get("role", "")
        if role == "figure_caption":
            if _is_body_mention(block):
                continue
            if not _is_formal_legend(block.get("text", ""), block, page_width):
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

    candidate_regions = _compute_candidate_figure_regions(structured_blocks, page_width)
    used_asset_indices: set[int] = set()
    used_region_ids: set[str] = set()
    for legend in ordered_legends:
        legend_page = legend.get("page", 0)
        legend_text = legend.get("text", "")
        fig_num = _extract_figure_number(legend_text)
        matched_assets = []
        region_match = None
        same_page_regions = [
            region
            for region in candidate_regions
            if region["page"] == legend_page and region["region_id"] not in used_region_ids
        ]
        attached_regions = [
            region
            for region in same_page_regions
            if any(cap.get("block_id") == legend.get("block_id") for cap in region.get("attached_captions", []))
        ]
        region_pool = attached_regions or same_page_regions
        if region_pool:
            region_match = max(
                region_pool,
                key=lambda region: len(region.get("media_blocks", [])),
            )
            matched_assets = list(region_match.get("media_blocks", []))
            used_region_ids.add(region_match["region_id"])
            for asset in matched_assets:
                for i, candidate in enumerate(assets):
                    if candidate.get("block_id") == asset.get("block_id") and candidate.get("page", 0) == asset.get(
                        "page", 0
                    ):
                        used_asset_indices.add(i)
                        break

        is_legend_only = len(matched_assets) == 0

        entry = {
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
            "confidence": 0.85 if region_match is not None else 0.4,
            "flags": [] if not is_legend_only else ["legend_only"],
        }
        if region_match is not None and len(matched_assets) > 1:
            entry["cluster_bbox"] = region_match["cluster_bbox"]
        matched_figures.append(entry)

        if is_legend_only:
            unmatched_legends.append(legend)

    # --- unresolved clusters ---
    # Candidate regions with 2+ media blocks that were NOT matched to a
    # formal legend become unresolved multi-panel clusters. Their media
    # blocks are consumed here so they do not spill into unmatched_assets.
    unresolved_clusters: list[dict] = []
    for region in candidate_regions:
        if region["region_id"] in used_region_ids:
            continue
        media_blocks = region.get("media_blocks", [])
        if len(media_blocks) < 2:
            continue

        media_block_ids = [b.get("block_id") for b in media_blocks if b.get("block_id") is not None]
        bbox = region.get("cluster_bbox", [0, 0, 0, 0])
        page = region.get("page", 0)

        for asset in media_blocks:
            for i, candidate in enumerate(assets):
                if candidate.get("block_id") == asset.get("block_id") and candidate.get("page", 0) == asset.get(
                    "page", 0
                ):
                    used_asset_indices.add(i)
                    break

        unresolved_clusters.append(
            {
                "cluster_id": f"cluster_{len(unresolved_clusters) + 1:03d}",
                "page": page,
                "bbox": bbox,
                "media_block_ids": media_block_ids,
                "matched_legend_block_id": None,
                "status": "unresolved_multi_panel",
                "confidence": 0.45,
                "flags": ["legend_rejected", "multi_panel_cluster"],
            }
        )

    for i, asset in enumerate(assets):
        if i not in used_asset_indices:
            unmatched_assets.append(asset)

    return {
        "figure_legends": legends,
        "figure_assets": assets,
        "matched_figures": matched_figures,
        "unmatched_legends": unmatched_legends,
        "unmatched_assets": unmatched_assets,
        "rejected_legends": rejected_legends,
        "unresolved_clusters": unresolved_clusters,
        "official_figure_count": len(matched_figures),
    }


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
