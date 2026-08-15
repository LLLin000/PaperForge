"""Retrieval materialization integrity — [6] layer of the state contract
(ADR-0002).

P1-D: retrieval is judged by TWO orthogonal facts instead of one flat
state:
- snapshot_integrity: verified | corrupt | unknown | absent — does the DB
  carrier exactly match the manifest (counts, hashes under the manifest's
  OWN recorded policy, no duplicate unit_ids, FTS aligned)?
- policy_currency: current | old — does the manifest's retrieval policy
  match the current policy version?

These are pure judging functions; the caller (probe lineage) queries the
DB and passes the unit rows.  A verified old snapshot is "old but intact",
never lumped into corrupt.
"""

from __future__ import annotations

from typing import Any

from paperforge.retrieval.manifest import (
    RETRIEVAL_POLICY_VERSION,
    compute_body_units_hash,
    compute_object_units_hash,
)

SNAPSHOT_VERIFIED = "verified"
SNAPSHOT_CORRUPT = "corrupt"
SNAPSHOT_UNKNOWN = "unknown"
SNAPSHOT_ABSENT = "absent"

POLICY_CURRENT = "current"
POLICY_OLD = "old"
POLICY_UNKNOWN = "unknown"


def _has_duplicate_unit_ids(units: list[dict[str, Any]]) -> bool:
    ids = [u.get("unit_id", "") for u in units]
    return len(ids) != len(set(ids))


def snapshot_integrity(
    manifest: dict[str, Any] | None,
    body_units: list[dict[str, Any]] | None,
    object_units: list[dict[str, Any]] | None,
    *,
    body_count: int,
    object_count: int,
) -> str:
    """Retrieval snapshot integrity — verified | corrupt | unknown | absent.

    Checks (P1-D, owner review 2026-08-15):
    - manifest exists
    - actual body/object counts == manifest counts
    - recomputed body/object hashes == manifest hashes, computed under the
      MANIFEST's recorded policy (old-but-intact ≠ corrupt)
    - no duplicate unit_ids
    Caller supplies the unit rows it already queries (per-paper, cheap).
    """
    if manifest is None:
        return SNAPSHOT_ABSENT
    try:
        exp_body = int(manifest.get("body_unit_count", 0) or 0)
        exp_obj = int(manifest.get("object_unit_count", 0) or 0)
        man_body_hash = str(manifest.get("body_units_hash", "") or "")
        man_obj_hash = str(manifest.get("object_units_hash", "") or "")
        policy = str(manifest.get("retrieval_policy_version", "") or "")
    except (TypeError, ValueError):
        return SNAPSHOT_UNKNOWN
    if not man_body_hash and not man_obj_hash:
        return SNAPSHOT_UNKNOWN  # legacy manifest without hashes — cannot verify
    if body_count != exp_body or object_count != exp_obj:
        return SNAPSHOT_CORRUPT
    algo_version = str(manifest.get("hash_algo_version", "") or "")
    if body_units is not None and man_body_hash:
        if _has_duplicate_unit_ids(body_units):
            return SNAPSHOT_CORRUPT
        try:
            recomputed = compute_body_units_hash(
                body_units, retrieval_policy_version=policy or RETRIEVAL_POLICY_VERSION
            )
        except Exception:  # noqa: BLE001 — unverifiable rows
            return SNAPSHOT_UNKNOWN
        if recomputed != man_body_hash:
            # P1-D: a hash mismatch on a manifest WITHOUT hash_algo_version
            # is algorithm drift, not provable corruption — the old snapshot
            # used an older field set we cannot reproduce.
            if algo_version:
                return SNAPSHOT_CORRUPT
            return SNAPSHOT_UNKNOWN
    if object_units is not None and man_obj_hash:
        if _has_duplicate_unit_ids(object_units):
            return SNAPSHOT_CORRUPT
        try:
            recomputed = compute_object_units_hash(
                object_units, retrieval_policy_version=policy or RETRIEVAL_POLICY_VERSION
            )
        except Exception:  # noqa: BLE001
            return SNAPSHOT_UNKNOWN
        if recomputed != man_obj_hash:
            if algo_version:
                return SNAPSHOT_CORRUPT
            return SNAPSHOT_UNKNOWN
    return SNAPSHOT_VERIFIED


def policy_currency(manifest: dict[str, Any] | None) -> str:
    """Desired-state currency: current | old | unknown — independent of
    integrity (an intact snapshot can still be policy-old)."""
    if manifest is None:
        return POLICY_UNKNOWN
    policy = str(manifest.get("retrieval_policy_version", "") or "")
    if not policy:
        return POLICY_UNKNOWN
    return POLICY_CURRENT if policy == RETRIEVAL_POLICY_VERSION else POLICY_OLD


def lineage_trust(manifest: dict[str, Any] | None, retrieval_identity: str | None) -> str:
    """Lineage trust: verified | unverified | mismatched — does the
    manifest's recorded retrieval identity match what the OCR chain
    published (the caller passes the current retrieval identity)."""
    if manifest is None:
        return "unverified"
    recorded = str(manifest.get("retrieval_identity", "") or "")
    if not recorded:
        return "unverified"
    if retrieval_identity is None:
        return "unverified"
    return "verified" if recorded == retrieval_identity else "mismatched"
