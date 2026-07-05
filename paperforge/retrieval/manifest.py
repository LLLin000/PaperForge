"""Paper manifest builder for the retrieval substrate.

The manifest records provenance metadata for a paper's retrieval units:
the OCR and structure-tree hashes it was built from, the policy version
used, and counts of the produced units.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


def build_paper_manifest(
    *,
    paper_id: str,
    ocr_result_hash: str,
    structure_tree_bytes: bytes,
    retrieval_policy_version: str,
    body_units: list[dict],
    object_units: list[dict],
    source_paths: dict[str, str],
) -> dict[str, Any]:
    """Build a provenance manifest for a paper's retrieval units."""
    structure_tree_hash = sha256(structure_tree_bytes).hexdigest()
    return {
        "paper_id": paper_id,
        "ocr_result_hash": ocr_result_hash,
        "structure_tree_hash": structure_tree_hash,
        "retrieval_policy_version": retrieval_policy_version,
        "body_unit_count": len(body_units),
        "object_unit_count": len(object_units),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_paths": dict(source_paths),
    }
