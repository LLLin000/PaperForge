from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)


def _extract_table_number(text: str) -> int | None:
    m = _TABLE_PREFIX_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


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

        candidate_pages = [caption_page, caption_page + 1, caption_page - 1]
        matched_asset = None

        for page in candidate_pages:
            if page < 1:
                continue
            for i, asset in enumerate(assets):
                if asset.get("page", 0) == page and i not in used_asset_indices:
                    matched_asset = asset
                    used_asset_indices.add(i)
                    break
            if matched_asset:
                break

        tables.append({
            "caption_block_id": caption.get("block_id", ""),
            "page": caption_page,
            "caption_text": caption_text,
            "table_number": table_num,
            "asset_block_id": matched_asset.get("block_id", "") if matched_asset else "",
            "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]) if matched_asset else [],
            "assistive_text": (matched_asset.get("text", "") or "") if matched_asset else "",
            "truth_source": "image",
            "has_asset": matched_asset is not None,
        })

    for caption in captions:
        if not any(
            t["caption_block_id"] == caption.get("block_id", "")
            for t in tables
            if t["has_asset"]
        ):
            unmatched_captions.append(caption)

    for i, asset in enumerate(assets):
        if i not in used_asset_indices:
            unmatched_assets.append(asset)

    return {
        "tables": tables,
        "unmatched_captions": unmatched_captions,
        "unmatched_assets": unmatched_assets,
        "official_table_count": len([t for t in tables if t["has_asset"]]),
    }


def write_table_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
