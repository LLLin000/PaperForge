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

    def test_rule_subject_must_reference_declared_registry(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["rules"] = [{
            "rule_id": "r1",
            "kind": "remote_intent",
            "subject": "missing_operation",
            "accepted_intent_modes": ["direct_invocation"],
        }]
        with pytest.raises(ArchitectureError):
            validate_contract(ArchitectureContract.from_dict(payload))


class TestEvidenceIdentity:
    def test_evidence_id_includes_line_range(self):
        from paperforge.architecture_audit import Evidence

        base = {
            "file": "a.py",
            "file_digest": "sha256:x",
            "symbol": "run",
            "line_start": 1,
            "line_end": 2,
            "extractor": "python_ast",
            "epistemic_status": "observed_static",
            "confidence": "exact",
        }
        first = Evidence.from_dict(base)
        second = Evidence.from_dict({**base, "line_start": 3, "line_end": 4})
        assert first.evidence_id != second.evidence_id


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



class TestExpandedSchema:
    def test_contract_entities_declare_authority_and_stable_ids(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract
        payload = _base_contract_payload()
        payload["asset_groups"] = [{"group_id": "library"}, {"group_id": "ocr_derived"}]
        payload["operations"] = [{
            "operation_id": "probe_status",
            "authorities": [{
                "role": "stop",
                "authority_id": "cli.stop",
                "observers": ["terminal"],
                "delegated_executors": ["worker"],
            }],
        }]
        payload["interfaces"] = [{
            "interface_id": "probe.cli",
            "provider": "cli",
            "consumer": "worker",
            "operation_id": "probe_status",
        }]
        payload["traces"] = [{
            "trace_id": "trace.probe",
            "operation_id": "probe_status",
            "interface_id": "probe.cli",
        }]
        contract = ArchitectureContract.from_dict(payload)
        validate_contract(contract)
        assert contract.asset_groups[0].group_id == "library"
        assert contract.operations[0].authorities[0].authority_id == "cli.stop"
        assert contract.interfaces[0].interface_id == "probe.cli"
        assert contract.traces[0].trace_id == "trace.probe"

    def test_exception_requires_review_condition(self):
        from paperforge.architecture_audit import ArchitectureContract, validate_contract

        payload = _base_contract_payload()
        payload["rules"] = [{"rule_id": "r1", "kind": "coverage_complete", "subject": ""}]
        payload["exceptions"] = [{
            "exception_id": "e1",
            "rule_id": "r1",
            "subject": "",
            "rationale": "temporary",
        }]
        with pytest.raises(ArchitectureError, match="review_condition"):
            validate_contract(ArchitectureContract.from_dict(payload))

    def test_unresolved_fact_keeps_observed_evidence_on_separate_axis(self):
        from paperforge.architecture_audit import ArchitectureSurvey, validate_survey

        payload = _base_survey_payload()
        payload["facts"] = [{
            "kind": "unresolved",
            "unresolved_id": "unresolved.1",
            "expression": "dynamic_call(target)",
            "reason": "target is not statically resolvable",
            "possible_effects": ["remote_operation"],
            "evidence": {
                "file": "paperforge/commands/sync.py",
                "file_digest": "sha256:x",
                "symbol": "dynamic_call",
                "line_start": 1,
                "line_end": 2,
                "extractor": "python_ast",
                "epistemic_status": "observed_static",
                "confidence": "high",
            },
            "epistemic_status": "unresolved",
        }]
        survey = ArchitectureSurvey.from_dict(payload)
        validate_survey(survey)
        assert survey.facts[0].epistemic_status is EpistemicStatus.UNRESOLVED
        assert survey.facts[0].evidence.epistemic_status is EpistemicStatus.OBSERVED_STATIC

    def test_run_metadata_is_deeply_immutable(self):
        from paperforge.architecture_audit import ArchitectureSurvey

        survey = ArchitectureSurvey.from_dict({
            **_base_survey_payload(),
            "run_metadata": {"nested": {"revision": "one"}},
        })
        with pytest.raises(TypeError):
            survey.run_metadata["nested"]["revision"] = "two"