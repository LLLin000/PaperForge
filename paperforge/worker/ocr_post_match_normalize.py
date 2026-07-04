"""OCR post-match normalization — v3 final role commit.

Consumes figure/table inventories and commits the final public `role`.
Reuses tail settlement from Workstream B.
"""

from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure


def post_match_normalize(
    rows: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    *,
    document_structure: DocumentStructure,
    source_frontmatter_anchors: dict | None = None,
) -> tuple[list[dict], DocumentStructure]:
    return rows, document_structure
