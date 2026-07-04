"""OCR post-match normalization — v3 final role commit.

Consumes figure/table inventories and commits the final public `role`.
Reuses tail settlement from Workstream B.
"""

from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure, normalize_document_structure
from paperforge.worker.ocr_tail_settlement import settle_tail_and_backmatter


def post_match_normalize(
    rows: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    *,
    document_structure: DocumentStructure,
    source_frontmatter_anchors: dict | None = None,
) -> tuple[list[dict], DocumentStructure]:
    """Shadow normalize rows, commit final roles, run tail settlement."""
    live_rows = [dict(row) for row in rows]
    shadow_doc, shadow_rows = normalize_document_structure(
        [dict(row) for row in rows],
        source_frontmatter_anchors=source_frontmatter_anchors,
    )
    for live, shadow in zip(live_rows, shadow_rows):
        live["role"] = shadow.get("role", live.get("role"))
        live["role_source"] = shadow.get("role_source", live.get("role_source"))
        live["role_confidence"] = shadow.get("role_confidence", live.get("role_confidence"))
        live["role_candidate"] = live.get("role_candidate") or shadow.get("role")
        live["render_default"] = shadow.get("render_default", live.get("render_default"))
        live["index_default"] = shadow.get("index_default", live.get("index_default"))
    settle_tail_and_backmatter(structured_blocks=live_rows, document_structure=shadow_doc)
    return live_rows, shadow_doc
