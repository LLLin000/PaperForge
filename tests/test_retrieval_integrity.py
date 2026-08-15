"""P1-D: retrieval snapshot integrity — verified/corrupt/unknown/absent,
policy currency, and the policy-parameterized hash (old-but-intact ≠
corrupt)."""

from __future__ import annotations

from typing import Any

from paperforge.materialization.retrieval import (
    POLICY_CURRENT,
    POLICY_OLD,
    SNAPSHOT_ABSENT,
    SNAPSHOT_CORRUPT,
    SNAPSHOT_UNKNOWN,
    SNAPSHOT_VERIFIED,
    lineage_trust,
    policy_currency,
    snapshot_integrity,
)
from paperforge.retrieval.manifest import (
    RETRIEVAL_POLICY_VERSION,
    compute_body_units_hash,
    compute_object_units_hash,
)

_BODY = [{"unit_id": "u1", "section_path": ["s"], "unit_text": "t"}]
_OBJ = [{"unit_id": "o1", "paper_id": "K", "section_path": "s"}]


def _manifest(**overrides: Any) -> dict[str, Any]:
    m = {
        "body_unit_count": 1,
        "object_unit_count": 1,
        "body_units_hash": compute_body_units_hash(_BODY),
        "object_units_hash": compute_object_units_hash(_OBJ),
        "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
        "hash_algo_version": "1",
        "retrieval_identity": "id1",
    }
    m.update(overrides)
    return m


class TestSnapshotIntegrity:
    def test_verified_when_everything_matches(self) -> None:
        assert snapshot_integrity(_manifest(), _BODY, _OBJ, body_count=1, object_count=1) == SNAPSHOT_VERIFIED

    def test_absent_without_manifest(self) -> None:
        assert snapshot_integrity(None, _BODY, _OBJ, body_count=1, object_count=1) == SNAPSHOT_ABSENT

    def test_corrupt_on_count_mismatch(self) -> None:
        assert snapshot_integrity(_manifest(), _BODY, _OBJ, body_count=2, object_count=1) == SNAPSHOT_CORRUPT

    def test_corrupt_on_hash_mismatch(self) -> None:
        bad_body = [{"unit_id": "u1", "section_path": ["s"], "unit_text": "DIFFERENT"}]
        assert snapshot_integrity(_manifest(), bad_body, _OBJ, body_count=1, object_count=1) == SNAPSHOT_CORRUPT

    def test_unknown_when_manifest_has_no_hashes(self) -> None:
        m = _manifest(body_units_hash="", object_units_hash="")
        assert snapshot_integrity(m, _BODY, _OBJ, body_count=1, object_count=1) == SNAPSHOT_UNKNOWN

    def test_corrupt_on_duplicate_unit_ids(self) -> None:
        dup = [_BODY[0], dict(_BODY[0])]
        assert snapshot_integrity(_manifest(body_unit_count=2), dup, _OBJ, body_count=2, object_count=1) == SNAPSHOT_CORRUPT

    def test_old_policy_snapshot_intact_not_corrupt(self) -> None:
        """P1-D key case: a snapshot built under an OLD policy hashes with
        its OWN policy — intact old ≠ corrupt."""
        old_policy = "l4.body.v2"
        m = _manifest(
            retrieval_policy_version=old_policy,
            body_units_hash=compute_body_units_hash(_BODY, old_policy),
            object_units_hash=compute_object_units_hash(_OBJ, old_policy),
        )
        assert policy_currency(m) == POLICY_OLD
        assert snapshot_integrity(m, _BODY, _OBJ, body_count=1, object_count=1) == SNAPSHOT_VERIFIED


class TestPolicyAndLineage:
    def test_policy_current(self) -> None:
        assert policy_currency(_manifest()) == POLICY_CURRENT

    def test_policy_old(self) -> None:
        assert policy_currency(_manifest(retrieval_policy_version="l4.body.v1")) == POLICY_OLD

    def test_lineage_verified(self) -> None:
        assert lineage_trust(_manifest(), "id1") == "verified"

    def test_lineage_mismatched(self) -> None:
        assert lineage_trust(_manifest(), "other-id") == "mismatched"

    def test_lineage_unverified_without_identity(self) -> None:
        assert lineage_trust(_manifest(retrieval_identity=""), "id1") == "unverified"

    def test_hash_mismatch_without_algo_version_is_unverifiable(self) -> None:
        """P1-D: a hash mismatch on a manifest WITHOUT hash_algo_version is
        algorithm drift (old field set), not provable corruption."""
        m = _manifest()
        m.pop("hash_algo_version", None)
        bad_body = [{"unit_id": "u1", "section_path": ["s"], "unit_text": "DIFFERENT"}]
        assert snapshot_integrity(m, bad_body, _OBJ, body_count=1, object_count=1) == SNAPSHOT_UNKNOWN
