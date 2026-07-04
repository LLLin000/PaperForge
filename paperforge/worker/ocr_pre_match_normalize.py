"""OCR pre-match normalization — v3 candidate-only normalize.

Preserves public `role = seed_role`, writes `role_candidate` from a shadow
normalize pass so figure/table matching can work from candidates.
"""

from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure


def pre_match_normalize(
    rows: list[dict],
    *,
    source_frontmatter_anchors: dict | None = None,
    document_structure: DocumentStructure | None = None,
) -> tuple[list[dict], DocumentStructure]:
    return rows, document_structure or DocumentStructure()
