"""#131 Slice A — layer schemas: round-trip, schema version, validation invariants.

Good tests assert public schema behavior (serialization round-trip, rejection
of unknown versions, layer invariants); they never touch private internals.
"""
from __future__ import annotations

import pytest

from paperforge.architecture_audit import (
    SCHEMA_VERSION,
    ArchitectureError,
    EpistemicStatus,
)


def _base_contract_payload() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "asset_groups": ["library", "ocr_derived"],
        "publication_units": [{
            "unit_id": "ocr_derived.generation",
            "asset_group": "ocr_derived",
            "publication_authority": "ocr.publisher",
        }],
        "operations": ["probe_status"],
        "rules": [],
        "exceptions": [],
    }


def _base_survey_payload() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "paperforge",
        "coverage": [{"extractor": "python_ast", "status": "complete"}],
        "facts": [],
        "source_digest": "sha256:abc",
        "parse_errors": [],
        "excluded_roots": [],
        "run_metadata": {},
    }


class TestRoundTrip:
    def test_contract_round_trip(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        contract = ArchitectureContract.from_dict(payload)
        validate_contract(contract)
        assert contract.to_dict() == payload

    def test_survey_round_trip(self):
        from paperforge.architecture_audit import ArchitectureSurvey, validate_survey

        payload = _base_survey_payload()
        payload["facts"] = [{
            "kind": "signal",
            "signal_id": "OCR_DONE",
            "producer": "worker.ocr",
            "consumer_kind": "code",
            "has_code_consumer": True,
        }]
        survey = ArchitectureSurvey.from_dict(payload)
        validate_survey(survey)
        assert survey.to_dict() == payload

    def test_review_round_trip(self):
        from paperforge.architecture_audit import ArchitectureReview, validate_review

        payload = {
            "schema_version": SCHEMA_VERSION,
            "reviewer_type": "agent",
            "contract_digest": "sha256:a",
            "survey_digest": "sha256:b",
            "audit_digest": "sha256:c",
            "reconciler_version": "1.0.0",
            "adjudications": [],
            "semantic_findings": [],
            "evidence_requests": [],
            "rationale": "",
            "run_metadata": {},
        }
        review = ArchitectureReview.from_dict(payload)
        validate_review(review)
        assert review.to_dict() == payload


class TestSchemaVersionRejection:
    def test_contract_unknown_version_rejected(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["schema_version"] = 999
        contract = ArchitectureContract.from_dict(payload)
        with pytest.raises(ArchitectureError):
            validate_contract(contract)

    def test_survey_unknown_version_rejected(self):
        from paperforge.architecture_audit import ArchitectureSurvey, validate_survey

        payload = _base_survey_payload()
        payload["schema_version"] = 999
        survey = ArchitectureSurvey.from_dict(payload)
        with pytest.raises(ArchitectureError):
            validate_survey(survey)


class TestContractValidation:
    def test_duplicate_rule_id_rejected(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["rules"] = [
            {"rule_id": "r1", "kind": "coverage_complete", "subject": ""},
            {"rule_id": "r1", "kind": "coverage_complete", "subject": ""},
        ]
        with pytest.raises(ArchitectureError):
            validate_contract(ArchitectureContract.from_dict(payload))

    def test_unknown_asset_group_rejected(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["publication_units"][0]["asset_group"] = "nope"
        with pytest.raises(ArchitectureError):
            validate_contract(ArchitectureContract.from_dict(payload))

    def test_implicit_never_accepted_intent_mode(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["rules"] = [{
            "rule_id": "r1", "kind": "remote_intent", "subject": "sync",
            "accepted_intent_modes": ["implicit"],
        }]
        with pytest.raises(ArchitectureError):
            validate_contract(ArchitectureContract.from_dict(payload))

    def test_planned_rule_requires_effective_after_or_known_gap(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["rules"] = [{
            "rule_id": "r1", "kind": "remote_intent", "subject": "sync",
            "lifecycle": "planned",
            "accepted_intent_modes": ["direct_invocation"],
        }]
        with pytest.raises(ArchitectureError):
            validate_contract(ArchitectureContract.from_dict(payload))

    def test_exception_references_unknown_rule_rejected(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["exceptions"] = [{
            "exception_id": "e1", "rule_id": "ghost", "subject": "x", "rationale": "r",
        }]
        with pytest.raises(ArchitectureError):
            validate_contract(ArchitectureContract.from_dict(payload))


class TestSurveyValidation:
    def test_duplicate_coverage_extractor_rejected(self):
        from paperforge.architecture_audit import ArchitectureSurvey, validate_survey

        payload = _base_survey_payload()
        payload["coverage"] = [
            {"extractor": "python_ast", "status": "complete"},
            {"extractor": "python_ast", "status": "complete"},
        ]
        with pytest.raises(ArchitectureError):
            validate_survey(ArchitectureSurvey.from_dict(payload))

    def test_survey_fact_cannot_carry_inferred_epistemic_status(self):
        from paperforge.architecture_audit import ArchitectureSurvey, validate_survey

        payload = _base_survey_payload()
        payload["facts"] = [{
            "kind": "effect",
            "operation_id": "sync",
            "effect_kind": "remote_operation",
            "evidence": {
                "file": "a.py", "file_digest": "sha256:x", "symbol": "run",
                "line_start": 1, "line_end": 2, "extractor": "python_ast",
                "epistemic_status": "inferred", "confidence": "high",
            },
        }]
        with pytest.raises(ArchitectureError):
            validate_survey(ArchitectureSurvey.from_dict(payload))


class TestReviewImmutability:
    def test_review_cannot_mutate_survey_facts(self):
        """Review carries its own payloads; survey facts are never reachable from it."""
        from paperforge.architecture_audit import (
            Adjudication,
            AdjudicationKind,
            ArchitectureReview,
        )

        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest="sha256:c",
            survey_digest="sha256:s",
            audit_digest="sha256:a",
            reconciler_version="1.0.0",
            adjudications=(
                Adjudication(
                    finding_id="finding:1",
                    adjudication=AdjudicationKind.CONFIRMED,
                    rationale="verified against source",
                    epistemic_status=EpistemicStatus.INFERRED,
                ),
            ),
        )
        # Adjudication only references a finding id; there is no fact payload to mutate.
        assert review.adjudications[0].finding_id == "finding:1"
        assert len(review.semantic_findings) == 0

    def test_review_adjudication_requires_inferred_or_unresolved(self):
        from paperforge.architecture_audit import (
            Adjudication,
            AdjudicationKind,
            ArchitectureReview,
            validate_review,
        )

        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest="sha256:c",
            survey_digest="sha256:s",
            audit_digest="sha256:a",
            reconciler_version="1.0.0",
            adjudications=(
                Adjudication(
                    finding_id="finding:1",
                    adjudication=AdjudicationKind.CONFIRMED,
                    rationale="r",
                    epistemic_status=EpistemicStatus.OBSERVED_STATIC,
                ),
            ),
        )
        with pytest.raises(ArchitectureError):
            validate_review(review)
