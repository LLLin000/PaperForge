from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json

_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)

_CONTINUATION_PATTERN = re.compile(r"\(cont(?:inued)?\.?\)", re.IGNORECASE)


def _extract_table_number(text: str) -> int | None:
    m = _TABLE_PREFIX_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


def _is_continuation_caption(text: str) -> bool:
    return bool(_CONTINUATION_PATTERN.search(text))


def _extract_base_table_number(text: str) -> int | None:
    cleaned = _CONTINUATION_PATTERN.sub("", text).strip()
    return _extract_table_number(cleaned)


def _compute_asset_score(
    asset: dict,
    caption_bottom: float,
) -> float:
    asset_bbox = asset.get("bbox", [0, 0, 0, 0])
    asset_top = asset_bbox[1] if len(asset_bbox) > 1 else 0
    distance = caption_bottom - asset_top
    if distance > 0:
        return distance
    return abs(distance) + 100000.0


def _pick_best_asset(
    page_assets: list[tuple[int, dict]],
    caption_bottom: float,
) -> tuple[int, dict] | None:
    best = None
    best_score = float("inf")
    for i, asset in page_assets:
        score = _compute_asset_score(asset, caption_bottom)
        if score < best_score:
            best_score = score
            best = (i, asset)
    return best


def build_table_inventory(structured_blocks: list[dict]) -> dict[str, Any]:
    tables: list[dict] = []
    captions: list[dict] = []
    assets: list[dict] = []
    unmatched_captions: list[dict] = []
    unmatched_assets: list[dict] = []

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
    for caption in captions:
        caption_page = caption.get("page", 0)
        caption_text = caption.get("text", "")
        table_num = _extract_table_number(caption_text)
        formal_table_number = _extract_base_table_number(caption_text)
        is_cont = _is_continuation_caption(caption_text)

        candidate_pages = [caption_page] if is_cont else [caption_page, caption_page + 1]

        caption_bbox = caption.get("bbox", [0, 0, 0, 0])
        caption_bottom = caption_bbox[3] if len(caption_bbox) > 3 else 0

        matched_asset = None
        for page in candidate_pages:
            if page < 1:
                continue
            page_assets = [
                (i, asset)
                for i, asset in enumerate(assets)
                if i not in used_asset_indices and asset.get("page", 0) == page
            ]
            if not page_assets:
                continue
            best = _pick_best_asset(page_assets, caption_bottom)
            if best is not None:
                best_idx, best_asset = best
                matched_asset = best_asset
                used_asset_indices.add(best_idx)
                break

        continuation_of = None
        if is_cont and formal_table_number is not None:
            for t in tables:
                tt = t.get("formal_table_number")
                if tt == formal_table_number and not t.get("is_continuation"):
                    continuation_of = formal_table_number
                    break

        segments: list[dict] = []
        if matched_asset:
            segments.append({
                "page": matched_asset.get("page", 0),
                "asset_block_id": matched_asset.get("block_id", ""),
                "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]),
                "is_continuation": is_cont,
            })

        tables.append({
            "caption_block_id": caption.get("block_id", ""),
            "page": caption_page,
            "caption_text": caption_text,
            "table_number": table_num,
            "formal_table_number": formal_table_number,
            "asset_block_id": matched_asset.get("block_id", "") if matched_asset else "",
            "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]) if matched_asset else [],
            "assistive_text": (matched_asset.get("text", "") or "") if matched_asset else "",
            "truth_source": "image",
            "has_asset": matched_asset is not None,
            "segments": segments,
            "is_continuation": is_cont,
            "continuation_of": continuation_of,
        })

    cap_block_ids_with_asset = {
        t["caption_block_id"] for t in tables if t["has_asset"]
    }
    for caption in captions:
        if caption.get("block_id", "") not in cap_block_ids_with_asset:
            unmatched_captions.append(caption)

    for i, asset in enumerate(assets):
        if i not in used_asset_indices:
            unmatched_assets.append(asset)

    return {
        "tables": tables,
        "unmatched_captions": unmatched_captions,
        "unmatched_assets": unmatched_assets,
        "official_table_count": len(
            [t for t in tables if t["has_asset"] and not t["is_continuation"]]
        ),
    }


def write_table_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
