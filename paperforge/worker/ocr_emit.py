from __future__ import annotations

# NOTE: This module is not used in the OCR production path.
# Production OCR structure is owned by ocr_document.py, ocr_figures.py,
# ocr_tables.py, ocr_render.py, and ocr_health.py.
# Keep this module only for compatibility/experimental tests.


def emit_page_markdown(
    page_index: int,
    ordered_spine: list,
    attachments: list,
    page_width: int = 0,
    page_height: int = 0,
) -> str:
    lines: list[str] = [f"<!-- page {page_index} -->"]
    attachment_by_anchor: dict[str, list] = {}

    for att in attachments:
        anchor = getattr(att, "anchor_node_id", "") if hasattr(att, "anchor_node_id") else att.get("anchor_node_id", "")
        if anchor:
            attachment_by_anchor.setdefault(anchor, []).append(att)

    inserted_ids: set = set()

    for node in ordered_spine:
        node_id = (
            getattr(node, "node_id", "")
            if hasattr(node, "node_id")
            else node.get("node_id", "")
        )
        node_type = (
            getattr(node, "node_type", "paragraph")
            if hasattr(node, "node_type")
            else node.get("node_type", "paragraph")
        )
        text = (
            getattr(node, "text", "")
            if hasattr(node, "text")
            else node.get("text", "")
        )

        if node_id in attachment_by_anchor:
            for att in attachment_by_anchor[node_id]:
                att_id = getattr(att, "attachment_id", id(att)) if hasattr(att, "attachment_id") else att.get("attachment_id", id(att))
                if att_id not in inserted_ids:
                    inserted_ids.add(att_id)
                    kind = getattr(att, "kind", "figure") if hasattr(att, "kind") else att.get("kind", "figure")
                    lines.append(f"[{kind.upper()} attached: {att_id}]")

        if node_type in ("section_heading", "subsection_heading"):
            lines.append(f"### {text}")
        else:
            if text:
                lines.append(text)

    return "\n".join(lines)
