"""Paper manifest builder for the retrieval substrate.

The manifest records provenance metadata for a paper's retrieval units:
the OCR and structure-tree hashes it was built from, the policy version
used, and counts of the produced units.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import json

RETRIEVAL_POLICY_VERSION = "l4.body.v1"


def compute_body_units_hash(units: list[dict]) -> str:
    """Compute a canonical hash for body units to detect changes."""
    raw = json.dumps(
        [
            {
                "unit_id": u["unit_id"],
                "section_path": u["section_path"],
                "section_level": u.get("section_level", 0),
                "section_title": u.get("section_title", ""),
                "unit_kind": u.get("unit_kind", "body"),
                "part_ordinal": u.get("part_ordinal", 0),
                "unit_text": u["unit_text"],
                "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            }
            for u in units
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256(raw.encode()).hexdigest()


def compute_object_units_hash(units: list[dict]) -> str:
    """Compute a canonical hash for object units to detect changes."""
    raw = json.dumps(
        [
            {
                "unit_id": u["unit_id"],
                "paper_id": u["paper_id"],
                "section_path": u.get("section_path", ""),
                "object_kind": u.get("object_kind", ""),
                "object_label": u.get("object_label", ""),
                "caption_text": u.get("caption_text", ""),
                "nearby_body_text": u.get("nearby_body_text", ""),
                "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            }
            for u in units
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256(raw.encode()).hexdigest()



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
        "body_units_hash": compute_body_units_hash(body_units),
        "object_unit_count": len(object_units),
        "object_units_hash": compute_object_units_hash(object_units),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_paths": dict(source_paths),
    }
