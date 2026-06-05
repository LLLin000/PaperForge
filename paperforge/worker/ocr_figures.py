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


def _compute_text_confidence(text: str, bbox: list[float], profile_legends: list[dict]) -> bool:
    """Check if a block's text/geometry is similar to known formal legends."""
    if not text or not profile_legends:
        return False
    if len(text) > 200:
        return False
    if any(w in text.lower() for w in [" is ", " are ", " was ", " were "]):
        return False
    if profile_legends:
        widths = [
            l.get("bbox", [0, 0, 0, 0])[2] - l.get("bbox", [0, 0, 0, 0])[0]
            for l in profile_legends
            if l.get("bbox")
        ]
        if widths:
            avg_width = sum(widths) / len(widths)
            bbox_width = bbox[2] - bbox[0]
            if abs(bbox_width - avg_width) / max(1, avg_width) < 0.5:
                return True
    return False


def build_figure_inventory(structured_blocks: list[dict]) -> dict[str, Any]:
    legends: list[dict] = []
    assets: list[dict] = []

    for block in structured_blocks:
        role = block.get("role", "")
        if role == "figure_caption":
            legends.append(block)
        elif role == "figure_asset":
            assets.append(block)
        elif role == "media_asset":
            raw_label = str(block.get("raw_label", "")).strip()
            if raw_label in {"image", "chart", "figure_title", "figure"} or not raw_label:
                assets.append(block)

    # --- Step 1: Classify each legend with confidence level ---
    # All legends are included; the classification affects confidence scoring
    legend_classification: dict[int, str] = {}  # legend index -> "formal" | "candidate" | "fallback"
    for i, leg in enumerate(legends):
        text = leg.get("text", "")
        bbox = leg.get("bbox", [0, 0, 0, 0])
        if _extract_figure_number(text) is not None:
            legend_classification[i] = "formal"
        elif _compute_text_confidence(text, bbox, [legends[j] for j in range(i) if legend_classification.get(j) == "formal"]):
            legend_classification[i] = "candidate"
        else:
            legend_classification[i] = "fallback"

    # --- Step 2: Multi-signal matching ---
    used_asset_indices: set[int] = set()
    matched_figures: list[dict] = []
    unmatched_legends: list[dict] = []

    for i_leg, legend in enumerate(legends):
        legend_page = legend.get("page", 0)
        legend_bbox = legend.get("bbox", [0, 0, 0, 0])
        legend_text = legend.get("text", "")
        fig_num = _extract_figure_number(legend_text)
        cls = legend_classification.get(i_leg, "fallback")
        is_formal = cls == "formal"

        candidate_pages = [legend_page, legend_page + 1, legend_page - 1]
        matched_assets = []

        for page in candidate_pages:
            if page < 1:
                continue
            page_assets = [
                (i, a) for i, a in enumerate(assets)
                if a.get("page", 0) == page and i not in used_asset_indices
            ]
            if not page_assets:
                continue

            scored = []
            for i, asset in page_assets:
                asset_bbox = asset.get("bbox", [0, 0, 0, 0])
                overlap = _compute_overlap_score(legend_bbox, asset_bbox)
                dist_y = abs(_centroid_y(legend_bbox) - _centroid_y(asset_bbox))
                dir_bonus = 1.0 if _centroid_y(asset_bbox) < _centroid_y(legend_bbox) else 0.5
                same_page = 2.0 if page == legend_page else 0.0
                # Horizontal alignment
                legend_cx = (legend_bbox[0] + legend_bbox[2]) / 2
                asset_cx = (asset_bbox[0] + asset_bbox[2]) / 2
                h_align = max(0, 1.0 - abs(legend_cx - asset_cx) / max(1, legend_bbox[2] - legend_bbox[0]))
                # Asset size bonus
                a_w = asset_bbox[2] - asset_bbox[0]
                a_h = asset_bbox[3] - asset_bbox[1]
                size_score = min(2.0, (a_w * a_h) / 50000)
                score = overlap * 10 + dir_bonus + same_page + h_align * 2 + size_score * 0.5 - dist_y * 0.01
                scored.append({"asset_index": i, "score": score, "overlap": overlap})

            scored.sort(key=lambda c: c["score"], reverse=True)
            for c in scored:
                if c["score"] <= -5:
                    continue
                if len(matched_assets) >= 3:
                    break
                matched_assets.append(assets[c["asset_index"]])
                used_asset_indices.add(c["asset_index"])

            if matched_assets:
                break

        # --- Step 3: Classify outcome ---
        flags: list[str] = []
        confidence = 0.85 if is_formal else 0.5
        if not matched_assets:
            flags.append("legend_only")
            confidence = 0.4 if is_formal else 0.2
            unmatched_legends.append(legend)
        elif confidence < 0.6:
            flags.append("low_confidence_match")
            confidence = 0.4

        matched_figures.append({
            "legend_block_id": legend.get("block_id", ""),
            "page": legend_page,
            "text": legend_text,
            "figure_number": fig_num,
            "matched_assets": [
                {"block_id": a.get("block_id", ""), "bbox": a.get("bbox", [0, 0, 0, 0])}
                for a in matched_assets
            ],
            "confidence": confidence,
            "flags": flags,
        })

    unmatched_assets_list = [
        asset for i, asset in enumerate(assets) if i not in used_asset_indices
    ]

    return {
        "figure_legends": legends,
        "figure_assets": assets,
        "matched_figures": matched_figures,
        "unmatched_legends": unmatched_legends,
        "unmatched_assets": unmatched_assets_list,
        "official_figure_count": len(matched_figures),
    }


def write_figure_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
