"""BodyUnit / ObjectUnit builders for the retrieval substrate.

Produces atomic retrieval units from a paper's structure tree, structured
blocks, and role index. Each unit is a self-contained chunk that can be
indexed by FTS and retrieved independently.
"""

from __future__ import annotations

import json
from itertools import groupby
from typing import Any


# ── Role helper ──

def _body_unit_role_kind(role: str) -> str | None:
    """Map a block's role to body unit kind, or None if excluded."""
    if role == "body_paragraph":
        return "body"
    if role in {"structured_insert", "non_body_insert", "backmatter_body"}:
        return "backmatter_body"
    return None  # reference_item, reference_heading, heading, caption, asset, etc.


def _split_if_oversized(text: str, max_tokens: int = 1000) -> list[str]:
    """Split text by paragraph if token estimate exceeds max_tokens."""
    if len(text) // 4 <= max_tokens:
        return [text]
    paragraphs = text.split("\n\n")
    parts: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for para in paragraphs:
        para_tokens = len(para) // 4
        if current_tokens + para_tokens > max_tokens and current:
            parts.append("\n\n".join(current))
            current = [para]
            current_tokens = para_tokens
        else:
            current.append(para)
            current_tokens += para_tokens
    if current:
        parts.append("\n\n".join(current))
    # Fallback: if a single oversized paragraph wasn't split, halve it
    if len(parts) == 1 and len(parts[0]) // 4 > max_tokens:
        mid = len(parts[0]) // 2
        break_at = parts[0].rfind(". ", 0, mid)
        if break_at < mid // 2:
            break_at = parts[0].rfind(" ", 0, mid)
        if break_at > 0:
            return [parts[0][:break_at + 1].strip(), parts[0][break_at + 1:].strip()]
    return parts if parts else [text]


def build_unit_id(
    paper_id: str,
    kind: str,
    node_id: str,
    start_page: int,
    start_block: str,
    end_page: int,
    end_block: str,
) -> str:
    """Stable, deterministic unit identifier."""
    return f"{paper_id}:{kind}:{node_id}:{start_page}-{start_block}:{end_page}-{end_block}"


def build_unit_id_v2(
    paper_id: str,
    kind: str,
    node_id: str,
    part_suffix: str = "",
) -> str:
    """Simplified unit identifier without block span."""
    return f"{paper_id}:{kind}:{node_id}{part_suffix}"


def build_body_units(
    *,
    tree: dict[str, Any],
    structured_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build body-text retrieval units recursively from the structure tree.

    Walks each node in the tree, collects own_block_ids that match body
    roles, groups by unit_kind (body / backmatter_body), splits oversized
    units, and produces schema v4 compatible output.
    """
    units: list[dict[str, Any]] = []
    paper_id = tree.get("paper_id", "")
    if not paper_id or not tree.get("nodes"):
        return units

    block_map: dict[str | int, dict[str, Any]] = {}
    for b in structured_blocks:
        bid = b.get("block_id")
        if bid is not None:
            block_map[str(bid)] = b
            block_map[bid] = b

    def walk(node: dict[str, Any], inherited_path: list[str]) -> None:
        this_path = inherited_path + [node["title"]]

        # Collect own blocks that match body/backmatter roles
        own_body_blocks: list[dict[str, Any]] = []
        for bid in node.get("own_block_ids", []):
            b = block_map.get(bid) or block_map.get(str(bid))
            if b is None:
                continue
            kind = _body_unit_role_kind(b.get("role", ""))
            if kind is not None:
                own_body_blocks.append(b)

        if own_body_blocks:
            # Group by unit_kind
            groups: list[tuple[str, list[dict[str, Any]]]] = []
            sorted_blocks = sorted(
                own_body_blocks,
                key=lambda b: _body_unit_role_kind(b.get("role", "")),
            )
            for kind, grp in groupby(
                sorted_blocks,
                key=lambda b: _body_unit_role_kind(b.get("role", "")),
            ):
                if kind:
                    groups.append((kind, list(grp)))

            for unit_kind, blocks in groups:
                all_text = "\n\n".join(
                    b.get("text", "") for b in blocks if b.get("text")
                )
                if not all_text.strip():
                    continue

                parts = _split_if_oversized(all_text, max_tokens=1000)
                n_parts = len(parts)

                for p_idx, part_text in enumerate(parts):
                    part_ordinal = p_idx + 1 if n_parts > 1 else 0
                    suffix = f":part_{part_ordinal:03d}" if part_ordinal else ""
                    uid = build_unit_id_v2(
                        paper_id, "body", node["node_id"], suffix,
                    )

                    unit = {
                        "unit_id": uid,
                        "paper_id": paper_id,
                        "section_path": "/".join(this_path),
                        "section_path_json": json.dumps(this_path),
                        "section_level": node.get("level", 0),
                        "section_title": node.get("title", ""),
                        "page_span": node.get("page_span", []),
                        "block_span": [],
                        "unit_text": part_text,
                        "token_estimate": len(part_text) // 4,
                        "unit_kind": unit_kind,
                        "part_ordinal": part_ordinal,
                        "indexable": True,
                        "veto_reason": "",
                        "quality_hints": [],
                    }
                    units.append(unit)

        for child in node.get("children", []):
            walk(child, this_path)

    for root in tree.get("nodes", []):
        walk(root, [])

    return units


def build_object_units(
    *,
    tree: dict[str, Any],
    structured_blocks: list[dict[str, Any]],
    role_index: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build object retrieval units from the role index scoped by section.

    Each object unit captures a figure/table/object with its caption and
    nearby body text, scoped to the most specific section that owns it.
    """
    import re

    units: list[dict[str, Any]] = []
    paper_id = tree.get("paper_id", "")

    # Build block_map for text resolution
    block_map: dict[str | int, dict[str, Any]] = {}
    for b in structured_blocks:
        bid = b.get("block_id")
        if bid is not None:
            block_map[str(bid)] = b
            block_map[bid] = b

    # Collect all objects from role_index (figures, tables, etc.)
    objects = role_index.get("figure_captions", []) + role_index.get("table_captions", [])

    def find_owning_node(node: dict[str, Any], object_block_id: str) -> dict[str, Any] | None:
        """Find the most specific section that owns an object block."""
        # Check children first (most specific)
        for child in node.get("children", []):
            result = find_owning_node(child, object_block_id)
            if result:
                return result
        # If object is in this node's subtree but not in any child's subtree
        str_bid = str(object_block_id)
        if str_bid in node.get("subtree_block_ids", []):
            return node
        return None

    for obj in objects:
        obj_id = obj.get("figure_id") or obj.get("table_id") or ""
        obj_type = "figure" if "figure_id" in obj else "table"
        caption = str(obj.get("text", "") or "")
        owning_node: dict[str, Any] | None = None

        # Try to find a caption block or asset block in this object
        caption_bid = obj.get("caption_block_id")
        if caption_bid:
            for root in tree.get("nodes", []):
                owning_node = find_owning_node(root, str(caption_bid))
                if owning_node:
                    break

        if not owning_node:
            # Fallback: iterate all roots to find the first that contains object block_ids
            consumed_ids = [
                str(x) if not isinstance(x, dict) else str(x.get("block_id", ""))
                for x in obj.get("consumed_block_ids", [])
            ]
            for cid in consumed_ids:
                if cid:
                    for root in tree.get("nodes", []):
                        owning_node = find_owning_node(root, cid)
                        if owning_node:
                            break
                if owning_node:
                    break

        if not owning_node:
            owning_node = tree.get("nodes", [{}])[0] if tree.get("nodes") else None

        if not owning_node:
            continue

        # Build section path
        section_path_parts: list[str] = []

        def _build_path(n: dict[str, Any], target: dict[str, Any]) -> list[str]:
            if n is target:
                return [n.get("title", "")]
            for child in n.get("children", []):
                result = _build_path(child, target)
                if result:
                    return [n.get("title", "")] + result
            return []

        for root in tree.get("nodes", []):
            section_path_parts = _build_path(root, owning_node)
            if section_path_parts:
                break

        uid = f"{paper_id}:obj:{obj_id}"
        unit = {
            "unit_id": uid,
            "paper_id": paper_id,
            "section_path": "/".join(section_path_parts),
            "object_kind": obj_type,
            "object_label": obj_id,
            "caption_text": caption,
            "nearby_body_text": "",  # Can be populated from own_block_ids text
            "page_span": [
                owning_node.get("page_span", [0, 0])[0],
                owning_node.get("page_span", [0, 0])[1],
            ],
            "block_span": [],
            "token_estimate": len(caption) // 4,
            "indexable": bool(caption.strip()),
            "veto_reason": "" if caption.strip() else "empty_caption",
            "quality_hints": [],
        }
        units.append(unit)

    return units
