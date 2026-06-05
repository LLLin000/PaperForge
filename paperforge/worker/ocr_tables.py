from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json

_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)

_CONTINUATION_PATTERN = re.compile(r"\(Continued\)|\(cont\.\)|\(cont\)", re.IGNORECASE)


def _extract_table_number(text: str) -> int | None:
    m = _TABLE_PREFIX_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


def _compute_overlap_score(a_bbox: list[float], b_bbox: list[float]) -> float:
    if not a_bbox or not b_bbox or len(a_bbox) < 4 or len(b_bbox) < 4:
        return 0.0
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


def build_table_inventory(structured_blocks: list[dict]) -> dict[str, Any]:
    captions: list[dict] = []
    assets: list[dict] = []

    for block in structured_blocks:
        role = block.get("role", "")
        raw_label = str(block.get("raw_label", "") or "").strip()
        if role == "table_caption":
            captions.append(block)
        elif role in ("table_asset", "media_asset"):
            if role == "media_asset" and raw_label not in ("table",):
                continue
            assets.append(block)

    used_asset_indices: set[int] = set()
    tables: list[dict] = []
    unmatched_captions: list[dict] = []

    for caption in captions:
        caption_page = caption.get("page", 0)
        caption_text = caption.get("text", "") or ""
        caption_bbox = caption.get("bbox", [0, 0, 0, 0])
        table_num = _extract_table_number(caption_text)
        is_continuation = bool(_CONTINUATION_PATTERN.search(caption_text))

        # Continuations should only match same-page assets
        candidate_pages = [caption_page]
        if not is_continuation:
            candidate_pages.extend([caption_page + 1, caption_page - 1])

        best_match: tuple[int | None, float] = (None, -999)
        for page in candidate_pages:
            if page < 1:
                continue
            page_assets = [
                (i, a) for i, a in enumerate(assets)
                if a.get("page", 0) == page and i not in used_asset_indices
            ]
            for i, asset in page_assets:
                asset_bbox = asset.get("bbox", [0, 0, 0, 0])
                overlap = _compute_overlap_score(caption_bbox, asset_bbox)
                if is_continuation:
                    same_page = 3.0
                    h_align = 0.0
                    if len(caption_bbox) >= 4 and len(asset_bbox) >= 4:
                        ccx = (caption_bbox[0] + caption_bbox[2]) / 2
                        acx = (asset_bbox[0] + asset_bbox[2]) / 2
                        h_align = max(0, 1.0 - abs(ccx - acx) / max(1, caption_bbox[2] - caption_bbox[0]))
                    score = same_page + h_align * 3 + overlap * 5
                else:
                    dist_y = 0.0
                    if len(caption_bbox) >= 4 and len(asset_bbox) >= 4:
                        dist_y = abs((caption_bbox[1] + caption_bbox[3]) / 2 - (asset_bbox[1] + asset_bbox[3]) / 2)
                    same_page = 2.0 if page == caption_page else 0.0
                    direction = 1.0 if (len(asset_bbox) >= 4 and len(caption_bbox) >= 4
                                        and (asset_bbox[1] + asset_bbox[3]) / 2 < (caption_bbox[1] + caption_bbox[3]) / 2) else 0.5
                    h_align = 0.0
                    if len(caption_bbox) >= 4 and len(asset_bbox) >= 4:
                        ccx = (caption_bbox[0] + caption_bbox[2]) / 2
                        acx = (asset_bbox[0] + asset_bbox[2]) / 2
                        h_align = max(0, 1.0 - abs(ccx - acx) / max(1, caption_bbox[2] - caption_bbox[0]))
                    a_w = asset_bbox[2] - asset_bbox[0] if len(asset_bbox) >= 4 else 0
                    a_h = asset_bbox[3] - asset_bbox[1] if len(asset_bbox) >= 4 else 0
                    size_score = min(2.0, (a_w * a_h) / 50000)
                    score = overlap * 10 + same_page + direction + h_align * 2 + size_score * 0.5 - dist_y * 0.01
                if score > best_match[1]:
                    best_match = (i, score)

        matched_asset = assets[best_match[0]] if best_match[0] is not None else None
        if best_match[0] is not None:
            used_asset_indices.add(best_match[0])

        if matched_asset is None:
            unmatched_captions.append(caption)

        tables.append({
            "caption_block_id": caption.get("block_id", ""),
            "page": caption_page,
            "caption_text": caption_text,
            "table_number": table_num,
            "is_continuation": is_continuation,
            "asset_block_id": matched_asset.get("block_id", "") if matched_asset else "",
            "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]) if matched_asset else [],
            "assistive_text": (matched_asset.get("text", "") or "") if matched_asset else "",
            "truth_source": "image",
            "has_asset": matched_asset is not None,
        })

    unmatched_assets_list = [
        a for i, a in enumerate(assets) if i not in used_asset_indices
    ]

    official_count = len([t for t in tables if t["has_asset"] and not t["is_continuation"]])

    return {
        "tables": tables,
        "unmatched_captions": unmatched_captions,
        "unmatched_assets": unmatched_assets_list,
        "official_table_count": official_count,
    }


def write_table_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
