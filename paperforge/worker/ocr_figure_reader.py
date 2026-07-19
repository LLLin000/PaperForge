from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass

_FIGURE_NUM_PATTERN = re.compile(
    r"(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+"
    r"(?:S)?(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)


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


def _index_blocks_by_page_and_id(blocks: list[dict]) -> dict[tuple[int | str | None, int | str], dict]:
    return {(block.get("page"), block.get("block_id")): block for block in blocks if block.get("block_id") is not None}


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


def _candidate_asset_ids_from_item(item: dict) -> list[int | str]:
    if "candidate_asset_ids" in item:
        return list(item.get("candidate_asset_ids", []))
    if "candidates" in item:
        return [
            asset.get("asset_block_id")
            for asset in item.get("candidates", [])
            if asset.get("asset_block_id") is not None
        ]
    return []


def _formal_legend_blocks(blocks: list[dict]) -> list[dict]:
    """Return blocks that are formal figure legends, excluding table_caption."""
    legends = []
    for block in blocks:
        role = block.get("role")
        if role == "table_caption":
            continue
        marker_type = str((block.get("marker_signature") or {}).get("type") or "")
        style_family = str(block.get("style_family") or "")
        if role in {"figure_caption", "legend"}:
            legends.append(block)
            continue
        if marker_type == "figure_number" and style_family in {"legend_like"}:
            legends.append(block)
    return legends


def _normalize_bucket(
    items: list[dict],
    bucket_name: str,
    block_index: dict[int | str, dict],
    legends_index: dict[int | str, dict] | None = None,
    *,
    page_block_index: dict | None = None,
    page_legends_index: dict | None = None,
) -> list[dict]:
    candidate_buckets = {"held_figures", "ambiguous_figures"}
    normalized = []
    for item in items:
        source_item = item
        legend_block_id = _legend_block_id(source_item)
        source_page = source_item.get("page")
        block = (page_block_index or {}).get((source_page, legend_block_id), block_index.get(legend_block_id, {}))
        source_text = str(source_item.get("text", source_item.get("caption_text", block.get("text", ""))) or "")
        legend_data = (page_legends_index or {}).get(
            (source_page, legend_block_id), (legends_index or {}).get(legend_block_id, {})
        )
        source_marker = (
            source_item.get("marker_signature")
            or legend_data.get("marker_signature")
            or block.get("marker_signature")
            or {}
        )

        _inferred_figure_number: int | None = None
        _inferred_marker_type: str | None = None
        _text_for_inference = source_text or block.get("text", "")
        if not source_item.get("marker_type") and not source_marker.get("type") and _text_for_inference:
            _m = _FIGURE_NUM_PATTERN.search(_text_for_inference)
            if _m:
                _inferred_marker_type = "figure_number"
                with contextlib.suppress(ValueError):
                    _inferred_figure_number = int(float(_m.group(1)))

        normalized.append(
            {
                "figure_id": source_item.get("figure_id", ""),
                "figure_number": source_item.get("figure_number")
                or source_marker.get("number")
                or _inferred_figure_number,
                "legend_block_id": legend_block_id,
                "caption_text": source_text,
                "asset_block_ids": _asset_ids_from_item(source_item),
                "candidate_asset_ids": (
                    _candidate_asset_ids_from_item(source_item) if bucket_name in candidate_buckets else []
                ),
                "marker_type": source_item.get("marker_type") or source_marker.get("type") or _inferred_marker_type,
                "inline_mention": bool(source_item.get("inline_mention", False)),
                "panel_label": bool(source_item.get("panel_label", False)),
                "body_prose_likelihood": float(source_item.get("body_prose_likelihood", 0.0)),
                "strict_reject": bool(source_item.get("strict_reject", False)),
                "linked_legend_block_id": source_item.get("linked_legend_block_id"),
                "cluster_area_ratio": float(source_item.get("cluster_area_ratio", 0.0)),
                "width_ratio": float(source_item.get("width_ratio", 0.0)),
                "height_ratio": float(source_item.get("height_ratio", 0.0)),
                "media_block_count": int(source_item.get("media_block_count", len(_asset_ids_from_item(source_item)))),
                "page": source_item.get("page", block.get("page")),
                "legend_page": source_item.get("legend_page", source_page),
                "zone": (legend_data.get("zone") or source_item.get("zone") or block.get("zone")),
                "style_family": (
                    legend_data.get("style_family") or source_item.get("style_family") or block.get("style_family")
                ),
                "strict_status": source_item.get("strict_status", bucket_name.removesuffix("s")),
                "bridge_block_ids": source_item.get("bridge_block_ids", []),
                "source_item": source_item,
            }
        )
    return normalized


def _build_bucket(
    strict_inventory: dict,
    key: str,
    block_index: dict[int | str, dict],
    legends_index: dict[int | str, dict] | None = None,
    *,
    page_block_index: dict | None = None,
    page_legends_index: dict | None = None,
) -> list[dict]:
    return _normalize_bucket(
        strict_inventory.get(key, []),
        key,
        block_index,
        legends_index,
        page_block_index=page_block_index,
        page_legends_index=page_legends_index,
    )


def _caption_consumption_page(item: dict) -> int | str | None:
    return item.get("legend_page", item.get("page"))


_READER_STATUS_MAP = {
    "matched_figures": "EXACT_MATCH",
    "held_figures": "HOLD",
    "ambiguous_figures": "GROUPED_APPROXIMATE",
    "unmatched_legends": "LEGEND_ONLY",
    "unresolved_clusters": "ASSET_GROUP_ONLY",
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


def _materialize_hold_outcome(
    *,
    legend_block_id: int | str | None,
    caption_text: str,
    page: int | None,
    candidate_asset_ids: list[int | str],
    hold_visibility: str,
) -> dict:
    reader_visible = hold_visibility == "reader_hold"
    return {
        "reader_figure_id": _stable_reader_figure_id(None, page=page, ordinal=0, suffix="_hold"),
        "figure_number": None,
        "reader_status": "HOLD",
        "strict_status": "held",
        "strict_source": "held_figures",
        "caption_block_id": legend_block_id,
        "caption_text": caption_text,
        "visual_groups": [],
        "consumed_caption_block_ids": (
            [{"page": page, "block_id": legend_block_id}]
            if reader_visible and legend_block_id is not None and caption_text
            else []
        ),
        "consumed_asset_block_ids": [],
        "debug_refs": {"candidate_asset_ids": list(candidate_asset_ids), "hold_visibility": hold_visibility},
    }


def _placeholder_visual_group(
    *,
    page: int | None,
    status: str,
    candidate_asset_ids: list[int | str] | None = None,
    rendered_as_representative: bool = False,
) -> dict:
    return {
        "page": page,
        "asset_block_ids": list(candidate_asset_ids or []),
        "group_status": status,
        "rendered_as_representative": rendered_as_representative,
    }


def _materialize_reader_figure(
    normalized_item: dict,
    source_bucket: str,
    ordinal: int,
) -> dict | None:
    figure_number = normalized_item.get("figure_number")
    caption_text = normalized_item.get("caption_text", "")
    legend_block_id = normalized_item.get("legend_block_id")

    if source_bucket == "matched_figures":
        asset_ids = list(normalized_item.get("asset_block_ids", []))
        strict_status = normalized_item.get("strict_status", "matched")
        reader_status = "SEQUENCE_MATCH" if strict_status == "sequence_match" else "EXACT_MATCH"
        return {
            "reader_figure_id": _stable_reader_figure_id(
                figure_number,
                page=normalized_item.get("page"),
                first_asset_block_id=asset_ids[0] if asset_ids else None,
                ordinal=ordinal,
            ),
            "figure_id": normalized_item.get("figure_id", ""),
            "figure_number": figure_number,
            "reader_status": reader_status,
            "strict_status": strict_status,
            "strict_source": source_bucket,
            "caption_block_id": legend_block_id,
            "caption_text": caption_text,
            "visual_groups": [
                {
                    "page": normalized_item.get("page"),
                    "asset_block_ids": asset_ids,
                    "group_status": "matched_group",
                    "rendered_as_representative": True,
                }
            ],
            "consumed_caption_block_ids": (([{"page": _caption_consumption_page(normalized_item), "block_id": legend_block_id}] if legend_block_id is not None else [])
            + [{"page": normalized_item.get("page"), "block_id": bid} for bid in normalized_item.get("bridge_block_ids", [])]),
            "consumed_asset_block_ids": [{"page": normalized_item.get("page"), "block_id": aid} for aid in asset_ids],
            "debug_refs": {},
        }

    if source_bucket in {"held_figures", "ambiguous_figures"}:
        candidate_asset_ids = list(normalized_item.get("candidate_asset_ids", []))
        if candidate_asset_ids:
            return {
                "reader_figure_id": _stable_reader_figure_id(
                    figure_number,
                    page=normalized_item.get("page"),
                    first_asset_block_id=candidate_asset_ids[0] if candidate_asset_ids else None,
                    ordinal=ordinal,
                ),
                "figure_number": figure_number,
                "reader_status": "GROUPED_APPROXIMATE",
                "strict_status": normalized_item.get("strict_status", "ambiguous"),
                "strict_source": source_bucket,
                "caption_block_id": legend_block_id,
                "caption_text": caption_text,
                "visual_groups": [
                    {
                        "page": normalized_item.get("page"),
                        "asset_block_ids": candidate_asset_ids,
                        "group_status": "candidate_group",
                        "rendered_as_representative": False,
                    }
                ],
                "consumed_caption_block_ids": [{"page": _caption_consumption_page(normalized_item), "block_id": legend_block_id}]
                if legend_block_id is not None
                else [],
                "consumed_asset_block_ids": [],
                "debug_refs": {"candidate_asset_ids": candidate_asset_ids},
            }
        if caption_text:
            return {
                "reader_figure_id": _stable_reader_figure_id(
                    figure_number,
                    page=normalized_item.get("page"),
                    ordinal=ordinal,
                ),
                "figure_number": figure_number,
                "reader_status": "LEGEND_ONLY",
                "strict_status": normalized_item.get("strict_status", "held"),
                "strict_source": source_bucket,
                "caption_block_id": legend_block_id,
                "caption_text": caption_text,
                "visual_groups": [
                    _placeholder_visual_group(
                        page=normalized_item.get("page"),
                        status="legend_only_group",
                    )
                ],
                "consumed_caption_block_ids": [{"page": _caption_consumption_page(normalized_item), "block_id": legend_block_id}]
                if legend_block_id is not None
                else [],
                "consumed_asset_block_ids": [],
                "debug_refs": {},
            }
        return None

    if source_bucket == "unmatched_legends":
        return {
            "reader_figure_id": _stable_reader_figure_id(
                figure_number,
                page=normalized_item.get("page"),
                ordinal=ordinal,
            ),
            "figure_number": figure_number,
            "reader_status": "LEGEND_ONLY",
            "strict_status": normalized_item.get("strict_status", "unmatched"),
            "strict_source": source_bucket,
            "caption_block_id": legend_block_id,
            "caption_text": caption_text,
            "visual_groups": [
                _placeholder_visual_group(
                    page=normalized_item.get("page"),
                    status="legend_only_group",
                )
            ],
            "consumed_caption_block_ids": [{"page": _caption_consumption_page(normalized_item), "block_id": legend_block_id}]
            if legend_block_id is not None
            else [],
            "consumed_asset_block_ids": [],
            "debug_refs": {},
        }

    if source_bucket == "unresolved_clusters":
        asset_ids = list(normalized_item.get("asset_block_ids", []))
        return {
            "reader_figure_id": _stable_reader_figure_id(
                None,
                page=normalized_item.get("page"),
                first_asset_block_id=asset_ids[0] if asset_ids else None,
                ordinal=ordinal,
            ),
            "figure_number": None,
            "reader_status": "ASSET_GROUP_ONLY",
            "strict_status": normalized_item.get("strict_status", "unresolved_cluster"),
            "strict_source": source_bucket,
            "caption_block_id": None,
            "caption_text": "",
            "visual_groups": [
                {
                    "page": normalized_item.get("page"),
                    "asset_block_ids": asset_ids,
                    "group_status": "candidate_group",
                    "rendered_as_representative": True,
                }
            ],
            "consumed_caption_block_ids": [],
            "consumed_asset_block_ids": [{"page": normalized_item.get("page"), "block_id": aid} for aid in asset_ids],
            "debug_refs": {},
        }

    return None


def _passes_formal_legend_gate(item: dict) -> bool:
    return (
        item.get("marker_type") == "figure_number"
        and not bool(item.get("inline_mention"))
        and not bool(item.get("panel_label"))
        and float(item.get("body_prose_likelihood", 0.0)) < 0.5
        and not bool(item.get("strict_reject"))
    )


def _passes_salient_visual_group_gate(item: dict) -> bool:
    zone = str(item.get("zone") or "")
    if zone == "preproof_cover_zone":
        return False
    area_ratio = float(item.get("cluster_area_ratio", 0.0))
    width_ratio = float(item.get("width_ratio", 0.0))
    height_ratio = float(item.get("height_ratio", 0.0))
    media_count = int(item.get("media_block_count", len(item.get("asset_block_ids", []))))
    if area_ratio >= 0.03:
        return True
    if width_ratio >= 0.30 and height_ratio >= 0.08:
        return True
    if media_count >= 3:
        return True
    return bool(media_count >= 2 and area_ratio >= 0.02)


def _collect_reader_eligible_inputs(normalized: dict) -> list[dict]:
    eligible: list[dict] = []
    seen_legends: set[tuple[int | str | None, int | str | None]] = set()

    for source_name in ("matched_figures", "held_figures", "ambiguous_figures"):
        for item in normalized.get(source_name, []):
            legend_id = (item.get("page"), item.get("legend_block_id"))
            if legend_id in seen_legends:
                continue
            if not _passes_formal_legend_gate(item):
                continue
            seen_legends.add(legend_id)
            eligible.append({"kind": "legend", "source": source_name, "item": item})

    for item in normalized.get("unmatched_legends", []):
        legend_id = (item.get("page"), item.get("legend_block_id"))
        if legend_id in seen_legends:
            continue
        if not _passes_formal_legend_gate(item):
            continue
        seen_legends.add(legend_id)
        eligible.append({"kind": "legend", "source": "unmatched_legends", "item": item})

    for item in normalized.get("unresolved_clusters", []):
        if item.get("linked_legend_block_id") is not None:
            continue
        if not _passes_salient_visual_group_gate(item):
            continue
        eligible.append({"kind": "visual_group", "source": "unresolved_clusters", "item": item})

    return eligible


def synthesize_reader_figures(
    strict_inventory: dict,
    structured_blocks: list[dict],
    document_structure: object | None = None,
) -> dict:
    normalized = _normalize_strict_figure_inventory(strict_inventory, structured_blocks)
    eligible_inputs = _collect_reader_eligible_inputs(normalized)

    reader_figures: list[dict] = []
    consumed_caption_ids: list[int | str] = []
    consumed_asset_ids: list[int | str] = []

    for ordinal, entry in enumerate(eligible_inputs):
        item = entry["item"]
        source_name = entry["source"]
        materialized = _materialize_reader_figure(item, source_name, ordinal)
        if materialized is None:
            continue
        reader_figures.append(materialized)
        consumed_caption_ids.extend(materialized.get("consumed_caption_block_ids", []))
        consumed_asset_ids.extend(materialized.get("consumed_asset_block_ids", []))

    deduped_legend_ids: list[dict] = strict_inventory.get("deduped_legend_ids", [])
    for item in deduped_legend_ids:
        page = item.get("page") if isinstance(item, dict) else None
        block_id = item.get("block_id") if isinstance(item, dict) else item
        if block_id is not None:
            consumed_caption_ids.append({"page": page, "block_id": block_id})

    coverage_total = len(eligible_inputs)
    return {
        "normalized_inputs": normalized,
        "reader_figures": reader_figures,
        "reader_coverage": ReaderCoverage(
            total=coverage_total,
            accounted=len(reader_figures),
            gap_count=coverage_total - len(reader_figures),
        ).as_dict(),
        "consumed_caption_block_ids": consumed_caption_ids,
        "consumed_asset_block_ids": consumed_asset_ids,
    }


def _normalize_strict_figure_inventory(
    strict_inventory: dict,
    structured_blocks: list[dict],
) -> dict:
    block_index = _index_structured_blocks(structured_blocks)
    page_block_index = _index_blocks_by_page_and_id(structured_blocks)
    legends_index: dict[int | str, dict] = {
        item.get("block_id"): item
        for item in strict_inventory.get("figure_legends", [])
        if item.get("block_id") is not None
    }
    page_legends_index: dict[tuple[int | str | None, int | str], dict] = {
        (item.get("page"), item.get("block_id")): item
        for item in strict_inventory.get("figure_legends", [])
        if item.get("block_id") is not None
    }
    return {
        "matched_figures": _build_bucket(
            strict_inventory,
            "matched_figures",
            block_index,
            legends_index,
            page_block_index=page_block_index,
            page_legends_index=page_legends_index,
        ),
        "held_figures": _build_bucket(
            strict_inventory,
            "held_figures",
            block_index,
            legends_index,
            page_block_index=page_block_index,
            page_legends_index=page_legends_index,
        ),
        "ambiguous_figures": _build_bucket(
            strict_inventory,
            "ambiguous_figures",
            block_index,
            legends_index,
            page_block_index=page_block_index,
            page_legends_index=page_legends_index,
        ),
        "unmatched_legends": _build_bucket(
            strict_inventory,
            "unmatched_legends",
            block_index,
            legends_index,
            page_block_index=page_block_index,
            page_legends_index=page_legends_index,
        ),
        "unresolved_clusters": _build_bucket(
            strict_inventory,
            "unresolved_clusters",
            block_index,
            legends_index,
            page_block_index=page_block_index,
            page_legends_index=page_legends_index,
        ),
        "block_index": block_index,
    }
