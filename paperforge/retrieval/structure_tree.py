from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


def build_structure_tree(structured_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    for block in structured_blocks:
        role = block.get("role")
        text = str(block.get("text", "")).strip()
        if role in {"section_heading", "subsection_heading", "introduction_heading", "abstract_heading"} and text:
            parent_title = nodes[-1]["title"] if nodes else ""
            current_section = {
                "node_id": f"sec:{block.get('block_id')}",
                "kind": "section",
                "title": text,
                "level": 1 if role != "subsection_heading" else 2,
                "section_path": [text] if role != "subsection_heading" else [parent_title, text],
                "page_span": [block.get("page", 0), block.get("page", 0)],
                "block_span": [[block.get("page", 0), block.get("block_id", "")]],
                "children": [],
                "objects": [],
            }
            nodes.append(current_section)
        elif current_section is not None:
            current_section["page_span"][1] = block.get("page", current_section["page_span"][1])
            current_section["block_span"].append([block.get("page", 0), block.get("block_id", "")])
    return {"paper_id": structured_blocks[0].get("paper_id", "") if structured_blocks else "", "nodes": nodes}


def write_structure_tree(index_root: Path, tree: dict[str, Any]) -> None:
    index_root.mkdir(parents=True, exist_ok=True)
    write_json(index_root / "structure-tree.json", tree)


def summarize_role_index(role_index: dict[str, Any]) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    for key, entries in role_index.items():
        if isinstance(entries, list):
            role_counts[key] = len(entries)
    return {"role_counts": role_counts}
