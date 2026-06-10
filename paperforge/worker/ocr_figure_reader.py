from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReaderCoverage:
    total: int
    accounted: int
    gap_count: int

    def as_dict(self) -> dict:
        ratio = 1.0 if self.total == 0 else self.accounted / self.total
        return {
            "total": self.total,
            "accounted": self.accounted,
            "gap_count": self.gap_count,
            "ratio": ratio,
        }


def _index_structured_blocks(structured_blocks: list[dict]) -> dict[int | str, dict]:
    return {block.get("block_id"): block for block in structured_blocks if block.get("block_id") is not None}


def _legend_block_id(item: dict) -> int | str | None:
    return item.get("legend_block_id", item.get("block_id"))


def _caption_text(item: dict) -> str:
    return str(item.get("caption_text", item.get("text", "")) or "")


def _asset_ids_from_item(item: dict) -> list[int | str]:
    if "asset_block_ids" in item:
        return list(item.get("asset_block_ids", []))
    if "matched_assets" in item:
        return [asset.get("block_id") for asset in item.get("matched_assets", []) if asset.get("block_id") is not None]
    if "candidates" in item:
        return [
            asset.get("asset_block_id")
            for asset in item.get("candidates", [])
            if asset.get("asset_block_id") is not None
        ]
    if "media_block_ids" in item:
        return list(item.get("media_block_ids", []))
    return []


def _normalize_bucket(
    items: list[dict],
    bucket_name: str,
    block_index: dict[int | str, dict],
) -> list[dict]:
    candidate_buckets = {"held_figures", "ambiguous_figures"}
    normalized = []
    for item in items:
        legend_block_id = _legend_block_id(item)
        block = block_index.get(legend_block_id, {})
        normalized.append(
            {
                "figure_number": item.get("figure_number"),
                "legend_block_id": legend_block_id,
                "caption_text": _caption_text(item),
                "asset_block_ids": _asset_ids_from_item(item),
                "candidate_asset_ids": (_asset_ids_from_item(item) if bucket_name in candidate_buckets else []),
                "marker_type": item.get("marker_type") or (block.get("marker_signature") or {}).get("type"),
                "inline_mention": bool(item.get("inline_mention", False)),
                "panel_label": bool(item.get("panel_label", False)),
                "body_prose_likelihood": float(item.get("body_prose_likelihood", 0.0)),
                "zone": item.get("zone") or block.get("zone"),
                "style_family": item.get("style_family") or block.get("style_family"),
                "strict_status": item.get("strict_status", bucket_name.removesuffix("s")),
                "source_item": item,
            }
        )
    return normalized


def _build_bucket(
    strict_inventory: dict,
    key: str,
    block_index: dict[int | str, dict],
) -> list[dict]:
    return _normalize_bucket(strict_inventory.get(key, []), key, block_index)


def _normalize_strict_figure_inventory(
    strict_inventory: dict,
    structured_blocks: list[dict],
) -> dict:
    block_index = _index_structured_blocks(structured_blocks)
    return {
        "matched_figures": _build_bucket(strict_inventory, "matched_figures", block_index),
        "held_figures": _build_bucket(strict_inventory, "held_figures", block_index),
        "ambiguous_figures": _build_bucket(strict_inventory, "ambiguous_figures", block_index),
        "unmatched_legends": _build_bucket(strict_inventory, "unmatched_legends", block_index),
        "unresolved_clusters": _build_bucket(strict_inventory, "unresolved_clusters", block_index),
        "block_index": block_index,
    }
