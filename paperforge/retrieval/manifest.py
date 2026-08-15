"""Paper manifest builder for the retrieval substrate.

The manifest records provenance metadata for a paper's retrieval units:
the OCR and structure-tree hashes it was built from, the policy version
used, and counts of the produced units.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

RETRIEVAL_POLICY_VERSION = "l4.body.v3"

# P1-D: the units-hash field set can evolve (adding fields changes the
# digest).  Record the algorithm version so a historical snapshot that
# fails today's hash is UNVERIFIABLE (algorithm drift), never falsely
# CORRUPT.
HASH_ALGO_VERSION = "1"


def compute_body_units_hash(
    units: list[dict], retrieval_policy_version: str = RETRIEVAL_POLICY_VERSION
) -> str:
    """Compute a canonical hash for body units to detect changes.

    P1-D: the policy version is part of the hash material and must be the
    version the MANIFEST was built under — historical snapshots hash with
    their recorded policy, so "old but intact" is distinguishable from
    "actually corrupted"."""
    raw = json.dumps(
        [
            {
                "unit_id": u["unit_id"],
                "node_id": u.get("node_id", ""),
                "section_path": u["section_path"],
                "section_path_json": u.get("section_path_json", "[]"),
                "section_level": u.get("section_level", 0),
                "section_title": u.get("section_title", ""),
                "unit_kind": u.get("unit_kind", "body"),
                "part_ordinal": u.get("part_ordinal", 0),
                "unit_text": u["unit_text"],
                "retrieval_policy_version": retrieval_policy_version,
            }
            for u in units
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256(raw.encode()).hexdigest()


def compute_object_units_hash(
    units: list[dict], retrieval_policy_version: str = RETRIEVAL_POLICY_VERSION
) -> str:
    """Compute a canonical hash for object units to detect changes.

    P1-D: hash with the MANIFEST's recorded policy, not the current one —
    otherwise an intact old snapshot looks corrupt after a policy bump."""
    raw = json.dumps(
        [
            {
                "unit_id": u["unit_id"],
                "paper_id": u["paper_id"],
                "node_id": u.get("node_id", ""),
                "section_path": u.get("section_path", ""),
                "section_path_json": u.get("section_path_json", "[]"),
                "object_kind": u.get("object_kind", ""),
                "object_label": u.get("object_label", ""),
                "caption_text": u.get("caption_text", ""),
                "nearby_body_text": u.get("nearby_body_text", ""),
                "retrieval_policy_version": retrieval_policy_version,
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
    """Build a provenance manifest for a paper's retrieval units.

    #162/T1: ``retrieval_identity`` is the content-addressed lineage identity
    of the retrieval layer — identical rebuild → identical digest.
    """
    from paperforge.lineage import compute_retrieval_identity

    structure_tree_hash = sha256(structure_tree_bytes).hexdigest()
    body_units_hash = compute_body_units_hash(body_units)
    object_units_hash = compute_object_units_hash(object_units)
    return {
        "paper_id": paper_id,
        "ocr_result_hash": ocr_result_hash,
        "structure_tree_hash": structure_tree_hash,
        "retrieval_policy_version": retrieval_policy_version,
        "hash_algo_version": HASH_ALGO_VERSION,
        "body_unit_count": len(body_units),
        "body_units_hash": body_units_hash,
        "object_unit_count": len(object_units),
        "object_units_hash": object_units_hash,
        "retrieval_identity": compute_retrieval_identity(
            ocr_result_hash=ocr_result_hash,
            retrieval_policy_version=retrieval_policy_version,
            structure_tree_hash=structure_tree_hash,
            body_units_hash=body_units_hash,
            object_units_hash=object_units_hash,
        ),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_paths": dict(source_paths),
    }
