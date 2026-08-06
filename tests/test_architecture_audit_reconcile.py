"""#131 Slice A — pure reconciliation: rule evaluation, assessment, compose binding.

Covers every rule kind, the assessment precedence (failed > incomplete >
findings > clean), planned-gap vs exception vs violation semantics, and the
Review digest binding contract.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from paperforge.architecture_audit import (
    SCHEMA_VERSION,
    Adjudication,
    AdjudicationKind,
    ArchitectureContract,
    ArchitectureReview,
    ArchitectureSurvey,
    AssessmentStatus,
    DigestMismatch,
    EpistemicStatus,
    RuleStatus,
    compose,
    reconcile,
)

ASSET_GROUPS = ("library", "ocr_derived", "retrieval", "vectors")


def _contract(
    rules: list[dict],
    units: tuple[dict, ...] = (),
    exceptions: tuple[dict, ...] = (),
    operations: tuple[str | dict, ...] | None = None,
    required_extractors: tuple[str, ...] = (),
) -> ArchitectureContract:
    return ArchitectureContract.from_dict({
        "schema_version": SCHEMA_VERSION,
        "asset_groups": list(ASSET_GROUPS),
        "publication_units": list(units),
        "operations": list(operations or ("sync", "probe_status", "ocr_rebuild")),
        "rules": rules,
        "exceptions": list(exceptions),
        "required_extractors": list(required_extractors),
    })


def _infer_fact_kind(fact: dict) -> str:
    """Test helper: infer the fact kind from its distinguishing fields."""
    if "effect_kind" in fact:
        return "effect"
    if "signal_id" in fact:
        return "signal"
    if "actor_kind" in fact:
        return "canonical_write"
    if "publication_authorities" in fact:
        return "unit_authority"
    if "role" in fact:
        return "role_authority"
    raise AssertionError(f"cannot infer fact kind from {sorted(fact)}")


def _survey(
    facts: tuple = (),
    coverage: tuple[dict, ...] = ({"extractor": "python_ast", "status": "complete"},),
    schema_version: int = SCHEMA_VERSION,
) -> ArchitectureSurvey:
    normalized = []
    for fact in facts:
        entry = dict(fact)
        entry.setdefault("kind", _infer_fact_kind(entry))
        normalized.append(entry)
    return ArchitectureSurvey.from_dict({
        "schema_version": schema_version,
        "scope": "paperforge",
        "coverage": list(coverage),
        "facts": normalized,
        "source_digest": "sha256:" + "0" * 64,
        "parse_errors": [],
        "excluded_roots": [],
        "run_metadata": {},
    })


def _evidence(symbol: str = "run", line: int = 10) -> dict:
    return {
        "file": "commands/sync.py",
        "file_digest": "sha256:" + "0" * 64,
        "symbol": symbol,
        "line_start": line,
        "line_end": line + 2,
        "extractor": "python_ast",
        "epistemic_status": "observed_static",
        "confidence": "exact",
    }


def _rule(**kwargs) -> dict:
    base = {"rule_id": "r1", "kind": "query_side_effect", "subject": "probe_status",
            "lifecycle": "active", "enforcement": "blocking"}
    base.update(kwargs)
    return base


def _finding(audit, rule_id: str):
    return next(f for f in audit.content.findings if f.rule_id == rule_id)


def _coverage(audit, rule_id: str) -> RuleStatus:
    row = next(r for r in audit.content.rule_coverage if r.rule_id == rule_id)
    assert row.status is not None
    return row.status


# ---------------------------------------------------------------- rule kinds


class TestQuerySideEffect:
    def test_business_mutation_violates(self):
        audit = reconcile(
            _contract([_rule()]),
            _survey(({
                "operation_id": "probe_status",
                "effect_kind": "business_mutation",
                "evidence": _evidence(),
            },)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED
        assert audit.content.assessment.status is AssessmentStatus.FINDINGS

    def test_declared_snapshot_and_log_are_allowed(self):
        audit = reconcile(
            _contract([_rule()]),
            _survey((
                {"operation_id": "probe_status", "effect_kind": "disposable_snapshot", "evidence": _evidence("snap", 5)},
                {"operation_id": "probe_status", "effect_kind": "log_diagnostic", "evidence": _evidence("log", 6)},
            )),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED
        assert audit.content.assessment.status is AssessmentStatus.CLEAN

    def test_materialization_build_is_not_a_query_effect(self):
        audit = reconcile(
            _contract([_rule()]),
            _survey(({"operation_id": "probe_status", "effect_kind": "materialization_build", "evidence": _evidence()},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED


class TestRemoteIntent:
    def test_implicit_followup_violates(self):
        audit = reconcile(
            _contract([_rule(
                kind="remote_intent", subject="sync",
                accepted_intent_modes=["direct_invocation", "ui_modal", "explicit_flag", "interactive_prompt"],
            )]),
            _survey(({"operation_id": "sync", "effect_kind": "remote_operation", "intent_mode": "implicit",
                      "evidence": _evidence("run", 93)},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED

    def test_direct_invocation_satisfies(self):
        audit = reconcile(
            _contract([_rule(
                kind="remote_intent", subject="sync",
                accepted_intent_modes=["direct_invocation"],
            )]),
            _survey(({"operation_id": "sync", "effect_kind": "remote_operation", "intent_mode": "direct_invocation",
                      "evidence": _evidence()},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED


class TestSignalConsumer:
    def test_code_signal_without_consumer_violates(self):
        audit = reconcile(
            _contract([_rule(kind="signal_consumer", subject="OCR_DONE")]),
            _survey(({"signal_id": "OCR_DONE", "producer": "worker.ocr",
                      "consumer_kind": "code", "has_code_consumer": False,
                      "evidence": _evidence("emit", 12)},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED


    def test_true_code_signal_requires_auditable_consumer(self):
        audit = reconcile(
            _contract([_rule(kind="signal_consumer", subject="OCR_DONE")]),
            _survey(({"signal_id": "OCR_DONE", "producer": "worker.ocr",
                      "consumer_kind": "code", "has_code_consumer": True,
                      "evidence": _evidence("emit", 12)},)),
        )
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert not audit.content.findings
    def test_human_terminal_signal_needs_no_code_consumer(self):
        audit = reconcile(
            _contract([_rule(kind="signal_consumer", subject="OCR_SUMMARY")]),
            _survey(({"signal_id": "OCR_SUMMARY", "producer": "worker.ocr",
                      "consumer_kind": "human_terminal", "has_code_consumer": False,
                      "evidence": _evidence("print_summary", 20)},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED

    def test_diagnostic_log_signal_needs_no_code_consumer(self):
        audit = reconcile(
            _contract([_rule(kind="signal_consumer", subject="SUPPORT_LOG")]),
            _survey(({"signal_id": "SUPPORT_LOG", "producer": "worker.ocr",
                      "consumer_kind": "diagnostic_log", "has_code_consumer": False,
                      "evidence": _evidence("log", 21)},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED


class TestPublicationAuthority:
    UNIT = {
        "unit_id": "ocr_derived.generation",
        "asset_group": "ocr_derived",
        "publication_authority": "ocr.publisher",
    }

    def test_one_authority_with_multiple_writers_satisfies(self):
        audit = reconcile(
            _contract([_rule(kind="publication_authority", subject="ocr_derived.generation")],
                      units=(self.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation",
                      "publication_authorities": ("ocr.publisher",),
                      "authorized_writers": ("ocr.postprocess", "ocr.rebuild"),
                      "evidence": _evidence("publish", 30)},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED

    def test_two_authorities_violate(self):
        audit = reconcile(
            _contract([_rule(kind="publication_authority", subject="ocr_derived.generation")],
                      units=(self.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation",
                      "publication_authorities": ("ocr.publisher", "ui.writer"),
                      "evidence": _evidence("publish", 30)},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED

    def test_single_authority_mismatching_declaration_violates(self):
        """A single-but-wrong authority is a contract/survey mismatch, not clean."""
        audit = reconcile(
            _contract([_rule(kind="publication_authority", subject="ocr_derived.generation")],
                      units=(self.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation",
                      "publication_authorities": ("ui.writer",),
                      "evidence": _evidence("publish", 30)},)),
        )
        finding = _finding(audit, "r1")
        assert finding.rule_status is RuleStatus.VIOLATED
        assert "differs from declared" in finding.message
class TestRoleAuthority:
    def test_one_authority_per_role_satisfies(self):
        audit = reconcile(
            _contract(
                [_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",))],
                operations=(
                    "sync",
                    "probe_status",
                    {
                        "operation_id": "ocr_rebuild",
                        "authorities": [{"role": "stop", "authority_id": "plugin.controller"}],
                    },
                ),
            ),
            _survey(({"operation_id": "ocr_rebuild", "role": "stop",
                      "authorities": ("plugin.controller",),
                      "evidence": _evidence("stop", 40)},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED

    def test_two_stop_authorities_violate(self):
        audit = reconcile(
            _contract(
                [_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",))],
                operations=(
                    "sync",
                    "probe_status",
                    {
                        "operation_id": "ocr_rebuild",
                        "authorities": [{"role": "stop", "authority_id": "plugin.controller"}],
                    },
                ),
            ),
            _survey(({"operation_id": "ocr_rebuild", "role": "stop",
                      "authorities": ("plugin.controller", "settings.view"),
                      "evidence": _evidence("stop", 40)},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED

    def test_missing_declared_authority_is_unresolved(self):
        audit = reconcile(
            _contract([_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",))]),
            _survey(({"operation_id": "ocr_rebuild", "role": "stop",
                      "authorities": ("plugin.controller",),
                      "evidence": _evidence("stop", 40)},)),
        )
        finding = _finding(audit, "r1")
        assert finding.rule_status is RuleStatus.UNRESOLVED
        assert "no declared stop authority" in finding.message


    @pytest.mark.parametrize(
        ("role", "authority"),
        (("observer", "terminal"), ("delegated_executor", "worker")),
    )
    def test_declared_observer_and_delegated_executor_sets_satisfy(self, role, authority):
        audit = reconcile(
            _contract(
                [_rule(kind="role_authority", subject="ocr_rebuild", scope=(role,))],
                operations=(
                    "sync",
                    "probe_status",
                    {
                        "operation_id": "ocr_rebuild",
                        "authorities": [{
                            "role": "stop",
                            "authority_id": "plugin.controller",
                            "observers": ["terminal"],
                            "delegated_executors": ["worker"],
                        }],
                    },
                ),
            ),
            _survey(({
                "operation_id": "ocr_rebuild",
                "role": role,
                "authorities": (authority,),
                "evidence": _evidence(role, 40),
            },)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED


    def test_multi_valued_role_requires_complete_declared_set(self):
        audit = reconcile(
            _contract(
                [_rule(kind="role_authority", subject="ocr_rebuild", scope=("observer",))],
                operations=(
                    "sync",
                    "probe_status",
                    {
                        "operation_id": "ocr_rebuild",
                        "authorities": [{
                            "role": "stop",
                            "authority_id": "plugin.controller",
                            "observers": ["terminal", "ops"],
                        }],
                    },
                ),
            ),
            _survey(({
                "operation_id": "ocr_rebuild",
                "role": "observer",
                "authorities": ("terminal",),
                "evidence": _evidence("observer", 40),
            },)),
        )
        finding = _finding(audit, "r1")
        assert finding.rule_status is RuleStatus.VIOLATED
        assert "missing" in finding.message



    def test_role_rule_serializes_authority_role_without_legacy_scope(self):
        contract = _contract([_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",))])
        rule = contract.rules[0]
        assert rule.authority_role == "stop"
        assert rule.scope == ()
        assert "scope" not in rule.to_dict()
        assert rule.to_dict()["authority_role"] == "stop"
class TestCanonicalWriter:
    def test_ui_write_violates(self):
        audit = reconcile(
            _contract([_rule(kind="canonical_writer", subject="ocr_derived.generation")],
                      units=(TestPublicationAuthority.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation", "actor_kind": "ui",
                      "via_publication_protocol": False,
                      "evidence": _evidence("restoreVersion", 162)},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED

    def test_backend_write_satisfies(self):
        audit = reconcile(
            _contract([_rule(kind="canonical_writer", subject="ocr_derived.generation")],
                      units=(TestPublicationAuthority.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation", "actor_kind": "worker",
                      "via_publication_protocol": True,
                      "evidence": _evidence("publish", 30)},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED


class TestPublicationMarker:
    def test_bypass_violates(self):
        audit = reconcile(
            _contract([_rule(kind="publication_marker", subject="ocr_derived.generation")],
                      units=(TestPublicationAuthority.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation", "actor_kind": "worker",
                      "via_publication_protocol": False,
                      "evidence": _evidence("run_derived_rebuild", 210)},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED

    def test_protocol_write_satisfies(self):
        audit = reconcile(
            _contract([_rule(kind="publication_marker", subject="ocr_derived.generation")],
                      units=(TestPublicationAuthority.UNIT,)),
            _survey(({"unit_id": "ocr_derived.generation", "actor_kind": "worker",
                      "via_publication_protocol": True,
                      "evidence": _evidence("publish", 30)},)),
        )
        assert _coverage(audit, "r1") is RuleStatus.SATISFIED


class TestCoverageComplete:
    def test_missing_typescript_coverage_cannot_produce_clean_audit(self):
        audit = reconcile(
            _contract([_rule(kind="coverage_complete", subject="")]),
            _survey((), coverage=(
                {"extractor": "python_ast", "status": "complete"},
                {"extractor": "typescript", "status": "unavailable"},
            )),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE
        assert audit.content.assessment.gate_eligible is False
        assert "typescript_coverage_unavailable" in audit.content.assessment.reasons

    def test_contract_and_survey_required_coverage_are_unioned(self):
        from dataclasses import replace

        contract = replace(_contract([_rule(kind="coverage_complete", subject="")]), required_extractors=("python_ast",))
        audit = reconcile(
            contract,
            _survey((), coverage=(
                {"extractor": "python_ast", "status": "complete"},
                {"extractor": "typescript", "status": "failed", "required": True},
            )),
        )
        assert [entry.extractor for entry in audit.content.coverage] == ["python_ast", "typescript"]
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED
        assert audit.content.assessment.status is AssessmentStatus.FAILED

    def test_coverage_rule_without_required_rows_is_unresolved(self):
        audit = reconcile(
            _contract([_rule(kind="coverage_complete", subject="")]),
            _survey((), coverage=({"extractor": "typescript", "status": "complete", "required": False},)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.UNRESOLVED
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE


# ---------------------------------------------------------------- lifecycle and exceptions


class TestLifecycle:
    def test_planned_rule_produces_planned_gap(self):
        audit = reconcile(
            _contract([_rule(lifecycle="planned", effective_after={"issue": "#126"})]),
            _survey(()),
        )
        finding = _finding(audit, "r1")
        assert finding.rule_status is RuleStatus.PLANNED_GAP
        assert finding.severity == "informational"
        assert audit.content.assessment.status is AssessmentStatus.FINDINGS

    def test_planned_gap_distinct_from_intentional_exception(self):
        planned = reconcile(
            _contract([_rule(lifecycle="planned", effective_after={"issue": "#126"})]),
            _survey(()),
        )
        excepted = reconcile(
            _contract([_rule()], exceptions=({
                "exception_id": "e1",
                "rule_id": "r1",
                "subject": "probe_status",
                "rationale": "declared",
                "review_condition": "revisit after probe contract changes",
            },)),
            _survey(({"operation_id": "probe_status", "effect_kind": "business_mutation",
                      "evidence": _evidence()},)),
        )
        assert _finding(planned, "r1").rule_status is RuleStatus.PLANNED_GAP
        assert _finding(excepted, "r1").rule_status is RuleStatus.EXCEPTION_APPLIED

    def test_deprecated_rule_not_evaluated(self):
        audit = reconcile(
            _contract([_rule(lifecycle="deprecated")]),
            _survey(()),
        )
        coverage = next(r for r in audit.content.rule_coverage if r.rule_id == "r1")
        assert coverage.evaluated is False
        assert audit.content.assessment.status is AssessmentStatus.CLEAN

    def test_planned_subject_entity_requires_planned_rule(self):
        contract = _contract(
            [_rule(
                kind="remote_intent",
                subject="sync",
                accepted_intent_modes=["direct_invocation"],
            )],
            operations=(
                {
                    "operation_id": "sync",
                    "meta": {"lifecycle": "planned", "effective_after": {"issue": "#127"}},
                },
                "probe_status",
                "ocr_rebuild",
            ),
        )
        audit = reconcile(contract, _survey(()))
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert any("must be planned" in reason for reason in audit.content.assessment.reasons)

    def test_entity_enforcement_cannot_be_weakened_by_rule(self):
        contract = _contract(
            [_rule(enforcement="observe")],
            operations=(
                "sync",
                {
                    "operation_id": "probe_status",
                    "meta": {"enforcement": "advisory"},
                },
                "ocr_rebuild",
            ),
        )
        audit = reconcile(
            contract,
            _survey(({"operation_id": "probe_status", "effect_kind": "business_mutation",
                      "evidence": _evidence()},)),
        )
        assert _finding(audit, "r1").severity == "advisory"


class TestSeverity:
    def test_blocking_violation_severity(self):
        audit = reconcile(_contract([_rule()]),
                          _survey(({"operation_id": "probe_status", "effect_kind": "business_mutation",
                                    "evidence": _evidence()},)))
        assert _finding(audit, "r1").severity == "blocking"

    def test_advisory_violation_severity(self):
        audit = reconcile(_contract([_rule(enforcement="advisory")]),
                          _survey(({"operation_id": "probe_status", "effect_kind": "business_mutation",
                                    "evidence": _evidence()},)))
        assert _finding(audit, "r1").severity == "advisory"


# ---------------------------------------------------------------- assessment


class TestAssessment:
    def test_validation_failure_produces_failed_assessment(self):
        """Precedence top: schema/validation failure yields `failed`, not findings."""
        from paperforge.architecture_audit import ArchitectureContract

        payload = {
            "schema_version": 999,
            "asset_groups": list(ASSET_GROUPS),
            "publication_units": [],
            "operations": ["sync"],
            "rules": [],
            "exceptions": [],
        }
        audit = reconcile(ArchitectureContract.from_dict(payload), _survey(()))
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert audit.content.assessment.gate_eligible is False
        assert any("validation_failed" in reason for reason in audit.content.assessment.reasons)
        assert audit.semantic_digest.startswith("sha256:")

    def test_invalid_authority_role_produces_failed_assessment(self):
        audit = reconcile(
            _contract([_rule(kind="role_authority", authority_role="not_a_role")]),
            _survey(()),
        )
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert any("unknown authority role" in reason for reason in audit.content.assessment.reasons)

    def test_failed_assessment_preserves_contract_required_coverage(self):
        audit = reconcile(
            _contract([], required_extractors=("typescript",)),
            _survey(schema_version=999),
        )
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        coverage = {entry.extractor: entry for entry in audit.content.coverage}
        assert set(coverage) == {"python_ast", "typescript"}
        assert all(entry.required and entry.status.value == "failed" for entry in coverage.values())

    def test_invalid_manual_enforcement_produces_failed_assessment(self):
        contract = _contract([_rule()])
        contract = replace(contract, rules=(replace(contract.rules[0], enforcement="typo"),))
        audit = reconcile(contract, _survey(()))
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert any("invalid enforcement" in reason for reason in audit.content.assessment.reasons)

    def test_failed_digest_is_deterministic_for_unknown_objects(self):
        def malformed_contract():
            contract = _contract([_rule()])
            return replace(contract, rules=(replace(contract.rules[0], enforcement=object()),))

        first = reconcile(malformed_contract(), _survey(()))
        second = reconcile(malformed_contract(), _survey(()))
        assert first.content.bound_contract_digest == second.content.bound_contract_digest
        assert first.semantic_digest == second.semantic_digest

    def test_clean_when_no_findings_and_complete_coverage(self):
        audit = reconcile(_contract([_rule(kind="coverage_complete", subject="")]), _survey(()))
        assert audit.content.assessment.status is AssessmentStatus.CLEAN
        assert audit.content.assessment.gate_eligible is True

    def test_incomplete_coverage_makes_universal_rules_unresolved(self):
        """#130 review B2: with required coverage incomplete, a universal rule
        cannot conclude violated OR satisfied from partial facts — the unseen
        callsites may violate. It becomes unresolved, and incomplete beats it."""
        audit = reconcile(
            _contract([_rule(), _rule(rule_id="r2", kind="coverage_complete", subject="")]),
            _survey(({"operation_id": "probe_status", "effect_kind": "business_mutation",
                      "evidence": _evidence()},),
                    coverage=({"extractor": "python_ast", "status": "complete"},
                              {"extractor": "typescript", "status": "partial"})),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.UNRESOLVED
        assert "cannot enumerate" in _finding(audit, "r1").message
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE
        assert audit.content.assessment.gate_eligible is False

    def test_universal_rule_satisfied_requires_complete_coverage(self):
        """Even a clearly satisfied universal rule must not be satisfied while
        required coverage is incomplete."""
        audit = reconcile(
            _contract([_rule(kind="query_side_effect", subject="probe_status")]),
            _survey(({"operation_id": "probe_status", "effect_kind": "disposable_snapshot",
                      "evidence": _evidence()},),
                    coverage=({"extractor": "python_ast", "status": "complete"},
                              {"extractor": "typescript", "status": "unavailable"})),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.UNRESOLVED


# ---------------------------------------------------------------- digests and binding


class TestDigestBinding:
    def test_identical_inputs_identical_audit_digest(self):
        contract = _contract([_rule(kind="coverage_complete", subject="")])
        survey = _survey(())
        first = reconcile(contract, survey)
        second = reconcile(contract, survey)
        assert first.semantic_digest == second.semantic_digest

    def test_survey_change_changes_audit_digest(self):
        contract = _contract([_rule()])
        base = reconcile(contract, _survey(()))
        changed = reconcile(contract, _survey(
            ({"operation_id": "probe_status", "effect_kind": "business_mutation", "evidence": _evidence()},)
        ))
        assert base.semantic_digest != changed.semantic_digest

    def test_compose_rejects_stale_review(self):
        contract = _contract([_rule(kind="coverage_complete", subject="")])
        survey = _survey(())
        audit = reconcile(contract, survey)
        other_audit = reconcile(
            _contract([_rule(rule_id="other", kind="coverage_complete", subject="")]),
            _survey(()),
        )
        stale_review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=other_audit.content.bound_contract_digest,
            survey_digest=other_audit.content.bound_survey_digest,
            audit_digest=other_audit.semantic_digest,
            reconciler_version="1.0.0",
        )
        with pytest.raises(DigestMismatch):
            compose(audit, stale_review)

    def test_compose_rejects_mismatched_reconciler_version(self):
        contract = _contract([_rule(kind="coverage_complete", subject="")])
        audit = reconcile(contract, _survey(()))
        wrong_version = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=audit.content.bound_contract_digest,
            survey_digest=audit.content.bound_survey_digest,
            audit_digest=audit.semantic_digest,
            reconciler_version="9.9.9",
        )
        with pytest.raises(DigestMismatch):
            compose(audit, wrong_version)

    def test_compose_accepts_bound_review(self):
        contract = _contract([_rule()])
        audit = reconcile(
            contract,
            _survey(({
                "operation_id": "probe_status",
                "effect_kind": "business_mutation",
                "evidence": _evidence(),
            },)),
        )
        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=audit.content.bound_contract_digest,
            survey_digest=audit.content.bound_survey_digest,
            audit_digest=audit.semantic_digest,
            reconciler_version="1.0.0",
            adjudications=(
                Adjudication(
                    finding_id=audit.content.findings[0].finding_id,
                    adjudication=AdjudicationKind.CONFIRMED,
                    rationale="confirmed against deterministic evidence",
                    epistemic_status=EpistemicStatus.INFERRED,
                ),
            ),
        )
        view = compose(audit, review)
        assert view.audit_digest == audit.semantic_digest
        assert view.review_digest is not None
        assert len(view.review_adjudications) == 1
        # view is a projection; source records are untouched
        assert len(audit.content.findings) == 1
        assert len(review.adjudications) == 1

    def test_compose_without_review_produces_deterministic_view(self):
        contract = _contract([_rule(kind="coverage_complete", subject="")])
        audit = reconcile(contract, _survey(()))
        first = compose(audit)
        second = compose(audit)
        assert first.to_dict() == second.to_dict()
        assert first.review_digest is None

    def test_report_view_cannot_rewrite_deterministic_content(self):
        from dataclasses import replace

        from paperforge.architecture_audit import ArchitectureError, validate_report_view

        audit = reconcile(
            _contract([_rule()]),
            _survey(({
                "operation_id": "probe_status",
                "effect_kind": "business_mutation",
                "evidence": _evidence(),
            },)),
        )
        tampered = replace(compose(audit), deterministic_findings=())
        with pytest.raises(ArchitectureError):
            validate_report_view(tampered, audit)
    def test_standalone_report_view_rejects_tampered_review_projection(self):
        from dataclasses import replace

        from paperforge.architecture_audit import ArchitectureError, validate_report_view

        audit = reconcile(
            _contract([_rule()]),
            _survey(({
                "operation_id": "probe_status",
                "effect_kind": "business_mutation",
                "evidence": _evidence(),
            },)),
        )
        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=audit.content.bound_contract_digest,
            survey_digest=audit.content.bound_survey_digest,
            audit_digest=audit.semantic_digest,
            reconciler_version="1.0.0",
            adjudications=(
                Adjudication(
                    finding_id=audit.content.findings[0].finding_id,
                    adjudication=AdjudicationKind.CONFIRMED,
                    rationale="confirmed against deterministic evidence",
                    epistemic_status=EpistemicStatus.INFERRED,
                ),
            ),
        )
        view = compose(audit, review)
        tampered = replace(view, review_adjudications=())
        with pytest.raises(ArchitectureError, match="review digest"):
            validate_report_view(tampered)

    def test_report_view_rejects_missing_review_digest(self):
        from dataclasses import replace

        from paperforge.architecture_audit import ArchitectureError

        audit = reconcile(
            _contract([_rule()]),
            _survey(({"operation_id": "probe_status", "effect_kind": "business_mutation",
                      "evidence": _evidence()},)),
        )
        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=audit.content.bound_contract_digest,
            survey_digest=audit.content.bound_survey_digest,
            audit_digest=audit.semantic_digest,
            reconciler_version="1.0.0",
            adjudications=(
                Adjudication(
                    finding_id=audit.content.findings[0].finding_id,
                    adjudication=AdjudicationKind.CONFIRMED,
                    rationale="confirmed",
                    epistemic_status=EpistemicStatus.INFERRED,
                ),
            ),
        )
        tampered = replace(compose(audit, review), review_digest=None)
        with pytest.raises(ArchitectureError, match="presence mismatch"):
            from paperforge.architecture_audit import validate_report_view
            validate_report_view(tampered)

    def test_finding_id_includes_explicit_authority_role(self):
        survey = _survey(({
            "operation_id": "ocr_rebuild",
            "role": "stop",
            "authorities": ("plugin.controller", "settings.view"),
            "evidence": _evidence("stop", 40),
        },))
        first = reconcile(
            _contract([_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",), authority_role="stop")]),
            survey,
        )
        second = reconcile(
            _contract([_rule(kind="role_authority", subject="ocr_rebuild", authority_role="execution")]),
            survey,
        )
        assert _finding(first, "r1").finding_id != _finding(second, "r1").finding_id



class TestCoverageAndFailureSemantics:
    def test_empty_coverage_is_incomplete_not_clean(self):
        audit = reconcile(_contract([_rule()]), _survey((), coverage=()))
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE
        assert audit.content.assessment.gate_eligible is False

    def test_parse_error_is_failed(self):
        survey = _survey(())
        survey = ArchitectureSurvey.from_dict({
            **survey.to_dict(),
            "parse_errors": ["python parser failed"],
        })
        audit = reconcile(_contract([_rule()]), survey)
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert audit.content.assessment.gate_eligible is False

    def test_failed_coverage_is_failed_not_incomplete(self):
        audit = reconcile(
            _contract([_rule(kind="coverage_complete", subject="")]),
            _survey((), coverage=({"extractor": "python_ast", "status": "failed"},)),
        )
        assert audit.content.assessment.status is AssessmentStatus.FAILED

    def test_missing_declared_extractor_is_incomplete(self):
        from dataclasses import replace

        contract = replace(_contract([_rule()]), required_extractors=("typescript",))
        audit = reconcile(contract, _survey(()))
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE
        assert "typescript_coverage_unavailable" in audit.content.assessment.reasons

    def test_duplicate_coverage_validation_failure_can_compose(self):
        survey = _survey((), coverage=(
            {"extractor": "python_ast", "status": "complete"},
            {"extractor": "python_ast", "status": "complete"},
        ))
        audit = reconcile(_contract([_rule()]), survey)
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert len(audit.content.coverage) == 1
        assert compose(audit).assessment.status is AssessmentStatus.FAILED


class TestDeclaredAuthoritySemantics:
    def test_role_authority_must_match_declared_authority(self):
        contract = ArchitectureContract.from_dict({
            **_contract([_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",))]).to_dict(),
            "operations": [{
                "operation_id": "ocr_rebuild",
                "authorities": [{"role": "stop", "authority_id": "controller.stop"}],
            }],
        })
        audit = reconcile(
            contract,
            _survey(({
                "operation_id": "ocr_rebuild",
                "role": "stop",
                "authorities": ("settings.view",),
                "evidence": _evidence("stop", 40),
            },)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED
        assert "differs from declared" in _finding(audit, "r1").message

    def test_rogue_writer_violates_even_when_backend(self):
        unit = {
            "unit_id": "ocr_derived.generation",
            "asset_group": "ocr_derived",
            "publication_authority": "ocr.publisher",
            "authorized_writers": ["approved.writer"],
        }
        audit = reconcile(
            _contract([_rule(kind="canonical_writer", subject=unit["unit_id"])], units=(unit,)),
            _survey(({
                "unit_id": unit["unit_id"],
                "actor_kind": "worker",
                "writer_id": "rogue.writer",
                "via_publication_protocol": True,
                "evidence": _evidence("publish", 30),
            },)),
        )
        assert _finding(audit, "r1").rule_status is RuleStatus.VIOLATED


class TestLayerValidation:
    def test_compose_rejects_tampered_audit_content(self):
        from dataclasses import replace

        from paperforge.architecture_audit import ArchitectureError, validate_audit

        audit = reconcile(_contract([_rule()]), _survey(({
            "operation_id": "probe_status",
            "effect_kind": "business_mutation",
            "evidence": _evidence(),
        },)))
        tampered = replace(audit, content=replace(audit.content, findings=()))
        with pytest.raises(ArchitectureError, match="semantic_digest"):
            validate_audit(tampered)
        with pytest.raises(ArchitectureError):
            compose(tampered)

    def test_compose_rejects_review_unknown_finding(self):
        from paperforge.architecture_audit import ArchitectureError

        audit = reconcile(_contract([_rule()]), _survey(({
            "operation_id": "probe_status",
            "effect_kind": "business_mutation",
            "evidence": _evidence(),
        },)))
        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=audit.content.bound_contract_digest,
            survey_digest=audit.content.bound_survey_digest,
            audit_digest=audit.semantic_digest,
            reconciler_version="1.0.0",
            adjudications=(
                Adjudication(
                    finding_id="finding:unknown",
                    adjudication=AdjudicationKind.CONFIRMED,
                    rationale="not in audit",
                    epistemic_status=EpistemicStatus.INFERRED,
                ),
            ),
        )
        with pytest.raises(ArchitectureError, match="unknown finding_id"):
            compose(audit, review)

    def test_review_cannot_embed_observed_evidence(self):
        from paperforge.architecture_audit import ArchitectureError, Confidence, Evidence, SemanticFinding

        audit = reconcile(_contract([_rule()]), _survey(({
            "operation_id": "probe_status",
            "effect_kind": "business_mutation",
            "evidence": _evidence(),
        },)))
        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest=audit.content.bound_contract_digest,
            survey_digest=audit.content.bound_survey_digest,
            audit_digest=audit.semantic_digest,
            reconciler_version="1.0.0",
            semantic_findings=(
                SemanticFinding(
                    finding_id="review:new",
                    message="agent claim",
                    epistemic_status=EpistemicStatus.INFERRED,
                    evidence=(Evidence(
                        file="paperforge/commands/sync.py",
                        file_digest="sha256:" + "1" * 64,
                        symbol="run",
                        line_start=1,
                        line_end=2,
                        extractor="python_ast",
                        epistemic_status=EpistemicStatus.OBSERVED_STATIC,
                        confidence=Confidence.HIGH,
                    ),),
                ),
            ),
        )
        with pytest.raises(ArchitectureError, match="evidence epistemic status"):
            compose(audit, review)

    def test_unknown_role_authority_fact_fails_validation(self):
        audit = reconcile(
            _contract([_rule(kind="role_authority", subject="ocr_rebuild", scope=("stop",))]),
            _survey(({
                "operation_id": "ocr_rebuild",
                "role": "typo",
                "authorities": ("plugin.controller",),
                "evidence": _evidence("stop", 40),
            },)),
        )
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        assert any(reason.startswith("validation_failed: unknown authority role") for reason in audit.content.assessment.reasons)

    def test_standalone_review_allows_unbound_evidence_references(self):
        from paperforge.architecture_audit import SemanticFinding, validate_review

        review = ArchitectureReview(
            schema_version=SCHEMA_VERSION,
            reviewer_type="agent",
            contract_digest="sha256:" + "a" * 64,
            survey_digest="sha256:" + "b" * 64,
            audit_digest="sha256:" + "c" * 64,
            reconciler_version="1.0.0",
            semantic_findings=(
                SemanticFinding(
                    finding_id="review:external",
                    message="needs evidence",
                    epistemic_status=EpistemicStatus.INFERRED,
                    evidence_ids=("evidence:external",),
                ),
            ),
        )
        validate_review(review)

    def test_standalone_report_rejects_unknown_adjudication(self):
        from dataclasses import replace

        from paperforge.architecture_audit import ArchitectureError, validate_report_view
        from paperforge.architecture_audit.layers import _review_projection_digest

        audit = reconcile(_contract([_rule()]), _survey(({
            "operation_id": "probe_status",
            "effect_kind": "business_mutation",
            "evidence": _evidence(),
        },)))
        unknown = Adjudication(
            finding_id="finding:unknown",
            adjudication=AdjudicationKind.CONFIRMED,
            rationale="not in deterministic findings",
            epistemic_status=EpistemicStatus.INFERRED,
        )
        tampered = replace(
            compose(audit),
            review_digest=_review_projection_digest((unknown,), (), ()),
            review_adjudications=(unknown,),
        )
        with pytest.raises(ArchitectureError, match="adjudicates unknown finding"):
            validate_report_view(tampered)