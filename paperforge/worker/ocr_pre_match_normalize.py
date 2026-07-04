"""OCR pre-match normalization — v3 candidate-only normalize.

Preserves public `role = seed_role`, writes `role_candidate` from a shadow
normalize pass so figure/table matching can work from candidates.
"""

from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure, normalize_document_structure


def pre_match_normalize(
    rows: list[dict],
    *,
    source_frontmatter_anchors: dict | None = None,
    document_structure: DocumentStructure | None = None,
) -> tuple[list[dict], DocumentStructure]:
    """Run shadow normalize to compute role_candidate; keep public role=seed_role."""
    live_rows = [dict(row) for row in rows]
    shadow_doc, shadow_rows = normalize_document_structure(
        [dict(row) for row in rows],
        source_frontmatter_anchors=source_frontmatter_anchors,
    )
    for live, shadow in zip(live_rows, shadow_rows):
        live["role_candidate"] = shadow.get("role") or shadow.get("seed_role") or live.get("seed_role")
        live["zone"] = shadow.get("zone", live.get("zone"))
        live["style_family"] = shadow.get("style_family", live.get("style_family"))
        live["marker_signature"] = shadow.get("marker_signature", live.get("marker_signature"))
        live["render_default"] = live.get("render_default", True)
        live["role"] = live.get("seed_role") or live.get("role")
    return live_rows, document_structure or shadow_doc
