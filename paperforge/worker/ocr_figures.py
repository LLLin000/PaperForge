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
            "days", "time", "concentration", "percentage", "volume",
            "frequency", "intensity", "ratio", "expression", "level",
            "content", "activity", "treatment", "group", "control",
            "dose", "response", "size", "culture", "medium",
            "supplemented", "differentiation", "osteogenic",
            "chondrogenic", "adipogenic", "induction", "stimulation",
            "exposure", "incubation", "harvest", "collection",
        }
        words = set(lower.rstrip(". ").split())
        stop_words = {
            "of", "the", "in", "and", "to", "a", "an",
            "by", "at", "for", "with", "on", "is", "are",
            "was", "were", "post", "after", "during", "before",
        }
        text_len = len(text)
        if text_len < 100 and words and words.issubset(axis_words | stop_words):
            return False

    return True


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

    low_conf_legends: list[dict] = []

    for block in structured_blocks:
        role = block.get("role", "")
        if role == "figure_caption":
            if _is_body_mention(block):
                continue
            if not _is_formal_legend(block.get("text", ""), block, page_width):
                rejected_legends.append(block)
                low_conf_legends.append(block)
            else:
                legends.append(block)
        elif role == "figure_asset":
            assets.append(block)
        elif role == "media_asset":
            raw_label = str(block.get("raw_label", "")).strip()
            if raw_label in {"image", "chart", "figure_title", "figure"} or not raw_label:
                assets.append(block)

    used_asset_indices: set[int] = set()
    for legend in legends:
        legend_page = legend.get("page", 0)
        legend_bbox = legend.get("bbox", [0, 0, 0, 0])
        legend_text = legend.get("text", "")
        fig_num = _extract_figure_number(legend_text)

        candidate_pages = [legend_page]

        matched_assets = []
        for page in candidate_pages:
            if page < 1:
                continue
            page_assets = [
                (i, a) for i, a in enumerate(assets) if a.get("page", 0) == page and i not in used_asset_indices
            ]
            if not page_assets:
                continue

            candidates_for_page: list[dict] = []
            for i, asset in page_assets:
                asset_bbox = asset.get("bbox", [0, 0, 0, 0])
                overlap = _compute_overlap_score(legend_bbox, asset_bbox)
                dist_y = abs(_centroid_y(legend_bbox) - _centroid_y(asset_bbox))
                direction_bonus = 1.0 if _centroid_y(asset_bbox) < _centroid_y(legend_bbox) else 0.5
                score = overlap * 10 + direction_bonus + 2.0 - dist_y * 0.01
                candidates_for_page.append(
                    {
                        "asset_index": i,
                        "asset": asset,
                        "score": score,
                        "overlap": overlap,
                        "distance_y": dist_y,
                        "same_page": True,
                    }
                )

            candidates_for_page.sort(key=lambda c: c["score"], reverse=True)

            for candidate in candidates_for_page:
                if len(matched_assets) >= 3:
                    break
                if candidate["score"] > -5:
                    matched_assets.append(candidate["asset"])
                    used_asset_indices.add(candidate["asset_index"])

            if matched_assets:
                break

        is_legend_only = len(matched_assets) == 0

        matched_figures.append(
            {
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
                "confidence": 0.85 if not is_legend_only else 0.4,
                "flags": [] if not is_legend_only else ["legend_only"],
            }
        )

        if is_legend_only:
            unmatched_legends.append(legend)

    # Fallback: for low-confidence legends (rejected by formality check),
    # match them to the first unmatched asset on the same page.
    # Each low-confidence legend produces at most one figure entry.
    used_low_conf: set[int] = set()
    for li, legend in enumerate(low_conf_legends):
        leg_page = legend.get("page", 0)
        leg_text = legend.get("text", "")
        fig_num = _extract_figure_number(leg_text)

        # Find first unmatched asset on the legend's page
        match_idx = None
        for i, asset in enumerate(assets):
            if i not in used_asset_indices and asset.get("page", 0) == leg_page:
                match_idx = i
                break

        if match_idx is not None and li not in used_low_conf:
            matched_figures.append({
                "legend_block_id": legend.get("block_id", ""),
                "page": leg_page,
                "text": leg_text,
                "figure_number": fig_num,
                "matched_assets": [{
                    "block_id": assets[match_idx].get("block_id", ""),
                    "bbox": assets[match_idx].get("bbox", [0, 0, 0, 0]),
                }],
                "confidence": 0.3,
                "flags": ["legend_uncertain"],
            })
            used_asset_indices.add(match_idx)
            used_low_conf.add(li)

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
        "official_figure_count": len(matched_figures),
    }


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
