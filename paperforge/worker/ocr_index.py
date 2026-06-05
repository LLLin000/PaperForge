from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


def build_role_indexes(
    structured_blocks: list[dict[str, Any]],
    resolved_metadata: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    body_roles = {
        "body_paragraph",
        "section_heading",
        "subsection_heading",
        "abstract_body",
        "abstract_heading",
        "introduction_heading",
    }
    body: list[dict[str, Any]] = []
    captions: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    all_blocks: list[dict[str, Any]] = []

    for block in structured_blocks:
        role = block.get("role", "")
        entry = {
            "paper_id": block.get("paper_id", ""),
            "page": block.get("page", 0),
            "block_id": block.get("block_id", ""),
            "role": role,
            "text": block.get("text", ""),
        }
        all_blocks.append(entry)

        if role in body_roles:
            body.append(entry)
        elif role == "figure_caption":
            captions.append(entry)
        elif role == "table_caption":
            tables.append(entry)
        elif role == "reference_item":
            references.append(entry)

    metadata_index: list[dict[str, Any]] = []
    for key in ("title", "authors", "doi", "journal", "year"):
        value = resolved_metadata.get(key, {}).get("value", "")
        if value:
            metadata_index.append({
                "paper_id": structured_blocks[0].get("paper_id", "") if structured_blocks else "",
                "page": 0,
                "block_id": f"meta_{key}",
                "role": f"metadata_{key}",
                "text": str(value),
            })

    return {
        "body": body,
        "captions": captions,
        "tables": tables,
        "metadata": metadata_index,
        "references": references,
        "all_blocks": all_blocks,
    }


def write_role_index(index_root: Path, indexes: dict[str, Any]) -> None:
    index_root.mkdir(parents=True, exist_ok=True)
    write_json(index_root / "role-index.json", indexes)
