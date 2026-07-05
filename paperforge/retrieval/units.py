"""BodyUnit / ObjectUnit builders for the retrieval substrate.

Produces atomic retrieval units from a paper's structure tree, structured
blocks, and role index.  Each unit is a self-contained chunk that can be
indexed by FTS and retrieved independently.
"""

from __future__ import annotations

from typing import Any


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


def build_body_units(
    *,
    tree: dict[str, Any],
    structured_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build body-text retrieval units for every section node in the tree.

    Each body unit groups all ``body_paragraph`` blocks inside the section's
    ``block_span``, joined by double newlines.
    """
    units: list[dict[str, Any]] = []
    paper_id = tree.get("paper_id", "")
    for node in tree.get("nodes", []):
        block_ids = {block_id for _, block_id in node.get("block_span", [])}
        texts = [
            b.get("text", "")
            for b in structured_blocks
            if b.get("block_id") in block_ids and b.get("role") == "body_paragraph"
        ]
        unit_text = "\n\n".join(t for t in texts if t)
        span = node.get("block_span", [])
        unit = {
            "unit_id": build_unit_id(
                paper_id,
                "body",
                node["node_id"],
                node["page_span"][0],
                span[0][1] if span else "",
                node["page_span"][1],
                span[-1][1] if span else "",
            ),
            "paper_id": paper_id,
            "section_path": "/".join(node.get("section_path", [])),
            "page_span": node.get("page_span", []),
            "block_span": span,
            "unit_text": unit_text,
            "token_estimate": len(unit_text) // 4,
            "unit_kind": "body",
            "indexable": bool(unit_text.strip()),
            "veto_reason": "" if unit_text.strip() else "empty",
            "quality_hints": [],
        }
        units.append(unit)
    return units


def build_object_units(
    *,
    tree: dict[str, Any],
    structured_blocks: list[dict[str, Any]],
    role_index: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build object retrieval units from the role index scoped by section.

    For each section node, objects (figures, tables, equations, …) whose
    ``block_id`` falls within the node's ``block_span`` are collected from
    the role index and emitted as individual object units with structured
    metadata fields (``object_kind``, ``object_label``, ``caption_text``,
    ``nearby_body_text``).
    """
    import re

    units: list[dict[str, Any]] = []
    paper_id = tree.get("paper_id", "")
    for node in tree.get("nodes", []):
        block_ids = {block_id for _, block_id in node.get("block_span", [])}
        span = node.get("block_span", [])

        # Pre-collect body text from this section for nearby_body_text
        body_texts = [
            b.get("text", "")
            for b in structured_blocks
            if b.get("block_id") in block_ids and b.get("role") == "body_paragraph"
        ]
        nearby_body = "\n\n".join(t for t in body_texts if t)

        for role, entries in role_index.items():
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("block_id") not in block_ids:
                    continue
                text = str(entry.get("text", ""))
                uid = build_unit_id(
                    paper_id, "object", node["node_id"],
                    node["page_span"][0], entry.get("block_id", ""),
                    node["page_span"][1], entry.get("block_id", ""),
                )

                # Map role to object_kind
                role_lower = role.lower()
                if role_lower.startswith("figure") or "figure" in role_lower:
                    object_kind = "figure"
                elif role_lower.startswith("table") or "table" in role_lower:
                    object_kind = "table"
                else:
                    object_kind = role

                # Extract object_label from caption prefix
                label_match = re.match(r'(Figure|Fig\.?\s*|Table|Tab\.?\s*)\s*\d+', text, re.IGNORECASE)
                object_label = label_match.group(0) if label_match else entry.get("block_id", "")

                unit = {
                    "unit_id": uid,
                    "paper_id": paper_id,
                    "section_path": "/".join(node.get("section_path", [])),
                    "page_span": node.get("page_span", []),
                    "block_span": span,
                    "object_kind": object_kind,
                    "object_label": object_label,
                    "caption_text": text,
                    "nearby_body_text": nearby_body,
                    "token_estimate": len(text) // 4,
                    "unit_kind": "object",
                    "indexable": bool(text.strip()),
                    "veto_reason": "" if text.strip() else "empty",
                    "quality_hints": [],
                }
                units.append(unit)
    return units
