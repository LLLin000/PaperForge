from __future__ import annotations

from pathlib import Path
from typing import Any


def build_ocr_health(
    *,
    page_count: int,
    raw_blocks_count: int,
    structured_blocks: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
) -> dict[str, Any]:
    section_heading_count = sum(1 for b in structured_blocks if b.get("role") == "section_heading")
    abstract_found = any(
        b.get("role") in ("abstract_heading", "abstract_body") or b.get("raw_label") == "abstract"
        for b in structured_blocks
    )
    references_found = any(
        b.get("role") in ("reference_heading", "reference_item") or b.get("raw_label") == "reference_content"
        for b in structured_blocks
    )
    figure_caption_count = sum(1 for b in structured_blocks if b.get("role") == "figure_caption")
    table_caption_count = sum(1 for b in structured_blocks if b.get("role") == "table_caption")

    figure_asset_count = len(figure_inventory.get("matched_figures", []))
    unmatched_legends = len(figure_inventory.get("unmatched_legends", []))
    unmatched_figure_assets = len(figure_inventory.get("unmatched_assets", []))
    tables = table_inventory.get("tables", [])
    table_asset_count = sum(1 for t in tables if t.get("has_asset"))
    empty_tables = sum(1 for t in tables if not t.get("has_asset"))
    formal_table_count = len([t for t in tables if not t.get("is_continuation")])
    entries_with_asset = sum(1 for t in tables if t.get("has_asset"))
    table_segment_count = entries_with_asset + len(table_inventory.get("unmatched_assets", []))

    media_without_caption = unmatched_figure_assets
    caption_without_media = unmatched_legends + len(table_inventory.get("unmatched_captions", []))

    frontmatter_quality = 1.0 if abstract_found and references_found else 0.5

    issues = 0
    if caption_without_media > 0:
        issues += 1
    if media_without_caption > 0:
        issues += 1
    if empty_tables > 0:
        issues += 1
    if not abstract_found:
        issues += 1
    if not references_found:
        issues += 1
    if section_heading_count < 2:
        issues += 1

    if issues == 0 and frontmatter_quality >= 0.5:
        overall = "green"
    elif issues <= 2:
        overall = "yellow"
    else:
        overall = "red"

    return {
        "page_count": page_count,
        "blocks_count": raw_blocks_count,
        "section_heading_count": section_heading_count,
        "abstract_found": abstract_found,
        "references_found": references_found,
        "figure_caption_count": figure_caption_count,
        "figure_asset_count": figure_asset_count,
        "table_caption_count": table_caption_count,
        "table_asset_count": table_asset_count,
        "formal_table_count": formal_table_count,
        "table_segment_count": table_segment_count,
        "media_without_caption_count": media_without_caption,
        "caption_without_media_count": caption_without_media,
        "empty_table_count": empty_tables,
        "frontmatter_quality": frontmatter_quality,
        "overall": overall,
    }


def write_ocr_health(health_root: Path, report: dict[str, Any]) -> None:
    from paperforge.core.io import write_json

    health_root.mkdir(parents=True, exist_ok=True)
    write_json(health_root / "ocr_health.json", report)
