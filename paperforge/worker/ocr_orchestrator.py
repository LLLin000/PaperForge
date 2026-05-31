from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BlockAnnotated:
    block: dict
    role: str = "unknown_structural"
    role_confidence: float = 0.0
    in_body_spine: bool = False


def _bbox_order_key(block: dict) -> tuple:
    bbox = block.get("block_bbox", [0, 0, 0, 0])
    return (int(bbox[1]), int(bbox[0]))


def reorder_blocks_layered(
    blocks: list[dict],
    page_width: int = 0,
    page_height: int = 0,
) -> list[dict]:
    if not blocks:
        return blocks

    try:
        from paperforge.worker.ocr_roles import assign_block_role
        from paperforge.worker.ocr_body_spine import BodySpineNode
        from paperforge.worker.ocr_layout import detect_layout_zones, order_body_spine
    except ImportError:
        return blocks

    annotated: list[BlockAnnotated] = []
    for b in blocks:
        role = assign_block_role(b, blocks, page_width=page_width, page_height=page_height)
        annotated.append(
            BlockAnnotated(block=b, role=role.role, role_confidence=role.confidence)
        )

    body_annotated = [a for a in annotated if a.role in {"section_heading", "subsection_heading", "body_paragraph"}]
    non_body = [a for a in annotated if a not in body_annotated]

    if not body_annotated:
        return blocks

    spine_nodes: list[BodySpineNode] = []
    for i, a in enumerate(body_annotated):
        bbox = tuple(a.block.get("block_bbox", [0, 0, 0, 0]))
        node_type = (
            a.role
            if a.role in {"section_heading", "subsection_heading"}
            else "paragraph"
        )
        spine_nodes.append(
            BodySpineNode(
                node_id=f"body-{i}",
                node_type=node_type,
                text=a.block.get("block_content", ""),
                bbox=bbox,
                role_confidence=a.role_confidence,
                block_ids=[i],
            )
        )

    zones = detect_layout_zones(spine_nodes, page_width=page_width, page_height=page_height)
    ordered_nodes = order_body_spine(spine_nodes, zones, mode="column_major")

    node_id_to_idx: dict[str, int] = {}
    for i, node in enumerate(spine_nodes):
        node_id_to_idx[node.node_id] = i

    body_result: list[dict] = []
    for node in ordered_nodes:
        idx = node_id_to_idx.get(node.node_id)
        if idx is not None and idx < len(body_annotated):
            body_result.append(body_annotated[idx].block)

    non_body_result: list[dict] = [a.block for a in non_body]
    return body_result + non_body_result
