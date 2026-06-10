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


_READER_STATUS_MAP = {
    "matched_figures": "RESOLVED",
    "held_figures": "DEFERRED",
    "ambiguous_figures": "GROUPED_APPROXIMATE",
    "unmatched_legends": "CAPTION_ONLY",
    "unresolved_clusters": "ORPHAN_ASSETS",
}


def _stable_reader_figure_id(
    figure_number: int | None,
    *,
    page: int | None = None,
    first_asset_block_id: int | str | None = None,
    ordinal: int | None = None,
    suffix: str = "",
) -> str:
    if figure_number is not None:
        base = f"figure_{int(figure_number):03d}_reader"
    elif first_asset_block_id is not None:
        base = f"visual_group_{int(page or 0)}_{first_asset_block_id}_reader"
    else:
        base = f"visual_group_{int(page or 0)}_{int(ordinal or 0)}_reader"
    return f"{base}{suffix}"


def _materialize_reader_figure(
    normalized_item: dict,
    source_bucket: str,
    ordinal: int,
) -> dict:
    figure_number = normalized_item.get("figure_number")
    asset_ids = normalized_item.get("asset_block_ids", [])
    first_asset = asset_ids[0] if asset_ids else None
    rf_id = _stable_reader_figure_id(
        figure_number,
        page=normalized_item.get("zone"),
        first_asset_block_id=first_asset,
        ordinal=ordinal,
    )
    return {
        "reader_figure_id": rf_id,
        "figure_number": figure_number,
        "reader_status": _READER_STATUS_MAP.get(source_bucket, "UNKNOWN"),
        "strict_status": normalized_item.get("strict_status", source_bucket.removesuffix("s")),
        "strict_source": source_bucket,
        "caption_text": normalized_item.get("caption_text", ""),
        "legend_block_id": normalized_item.get("legend_block_id"),
        "asset_block_ids": normalized_item.get("asset_block_ids", []),
        "candidate_asset_ids": normalized_item.get("candidate_asset_ids", []),
        "marker_type": normalized_item.get("marker_type"),
        "inline_mention": normalized_item.get("inline_mention", False),
        "panel_label": normalized_item.get("panel_label", False),
        "zone": normalized_item.get("zone"),
        "style_family": normalized_item.get("style_family"),
    }


def synthesize_reader_figures(
    strict_inventory: dict,
    structured_blocks: list[dict],
    document_structure: object | None = None,
) -> dict:
    normalized = _normalize_strict_figure_inventory(strict_inventory, structured_blocks)
    reader_figures: list[dict] = []
    consumed_caption_ids: list[int | str] = []
    consumed_asset_ids: list[int | str] = []

    ordinal = 0
    for bucket_name in (
        "matched_figures",
        "held_figures",
        "ambiguous_figures",
        "unmatched_legends",
        "unresolved_clusters",
    ):
        for item in normalized.get(bucket_name, []):
            reader_figures.append(_materialize_reader_figure(item, bucket_name, ordinal))
            legend_id = item.get("legend_block_id")
            if legend_id is not None:
                consumed_caption_ids.append(legend_id)
            consumed_asset_ids.extend(item.get("asset_block_ids", []))
            ordinal += 1

    total = len(reader_figures)
    return {
        "normalized_inputs": normalized,
        "reader_figures": reader_figures,
        "reader_coverage": ReaderCoverage(total=total, accounted=total, gap_count=0).as_dict(),
        "consumed_caption_block_ids": consumed_caption_ids,
        "consumed_asset_block_ids": consumed_asset_ids,
    }


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
