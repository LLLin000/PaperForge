from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


def build_structure_tree(
    heading_events: list[dict[str, Any]],
    emitted_block_events: list[dict[str, Any]],
    structured_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build nested structure tree from heading events and emitted block events.

    Uses PaperIndex stack algorithm for nesting, then assigns own_block_ids
    and subtree_block_ids via interval computation based on emitted_order.
    """
    if not heading_events:
        paper_id = structured_blocks[0].get("paper_id", "") if structured_blocks else ""
        return {"paper_id": paper_id, "nodes": []}

    heading_events = sorted(heading_events, key=lambda h: h["emitted_order"])

    # ── stack algorithm ──
    root_nodes: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    
    for h in heading_events:
        base_id = f"sec:{h['block_id']}"
        # ponytail: same block_id appears on different pages for different
        # headings (e.g. running headers). Disambiguate with emitted_order.
        node_id = base_id
        while node_id in seen_node_ids:
            node_id = f"{base_id}:order{h['emitted_order']}"
        seen_node_ids.add(node_id)
        
        node = {
            "node_id": node_id,
            "kind": "section",
            "title": h["title"],
            "level": h["markdown_level"],
            "block_id": h["block_id"],
            "page_span": [h["page"], h["page"]],
            "own_block_ids": [],
            "subtree_block_ids": [],
            "children": [],
            "objects": [],
        }
        while stack and stack[-1]["level"] >= h["markdown_level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            root_nodes.append(node)
        stack.append(node)

    # ── build bounds map ──
    bounds_map: dict[str | int, dict[str, int | float]] = {}
    for i, h in enumerate(heading_events):
        next_sibling: int | float | None = None
        for h2 in heading_events[i + 1 :]:
            if h2["markdown_level"] <= h["markdown_level"]:
                next_sibling = h2["emitted_order"]
                break
        bounds_map[h["block_id"]] = {
            "start": h["emitted_order"],
            "end": next_sibling or float("inf"),
        }

    # ── interval assignment (recursive) ──
    def _assign_intervals(node: dict[str, Any]) -> None:
        bounds = bounds_map.get(node["block_id"])
        if bounds is None:
            return

        start = bounds["start"]
        end = bounds["end"]

        node["subtree_block_ids"] = [
            str(e["block_id"]) for e in emitted_block_events if start <= e["emitted_order"] < end
        ]

        # Extend page_span from emitted blocks
        for e in emitted_block_events:
            if start <= e["emitted_order"] < end:
                page = e.get("page")
                if page is not None:
                    if page < node["page_span"][0]:
                        node["page_span"][0] = page
                    if page > node["page_span"][1]:
                        node["page_span"][1] = page

        for child in node.get("children", []):
            _assign_intervals(child)

        # own = subtree - all children subtrees - heading block
        child_ids: set[str] = set()
        for child in node.get("children", []):
            child_ids.update(child.get("subtree_block_ids", []))
        child_ids.add(str(node["block_id"]))

        node["own_block_ids"] = [bid for bid in node["subtree_block_ids"] if bid not in child_ids]

    for n in root_nodes:
        _assign_intervals(n)

    paper_id = structured_blocks[0].get("paper_id", "") if structured_blocks else ""
    return {"paper_id": paper_id, "nodes": root_nodes}


def write_structure_tree(index_root: Path, tree: dict[str, Any]) -> None:
    """Write structure tree to index/structure-tree.json."""
    index_root.mkdir(parents=True, exist_ok=True)
    write_json(index_root / "structure-tree.json", tree)


def summarize_role_index(role_index: dict[str, Any]) -> dict[str, Any]:
    """Summarize role index by counting entries per role."""
    role_counts: dict[str, int] = {}
    for key, entries in role_index.items():
        if isinstance(entries, list):
            role_counts[key] = len(entries)
    return {"role_counts": role_counts}
