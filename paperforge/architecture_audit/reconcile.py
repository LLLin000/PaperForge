"""Pure deterministic reconciliation engine (#130 Slice A, owned exclusively by #131).

`reconcile(contract, survey) -> DeterministicAudit` evaluates every contract rule
against observed survey facts. It never queries GitHub, never touches the network,
never auto-changes lifecycle status, and never modifies its inputs.

Assessment precedence (#131): failed > incomplete > findings > clean.
"""
from __future__ import annotations

from typing import Any

from paperforge.architecture_audit.canonical import (
    canonical_json,
    finding_id,
    semantic_digest,
    sha256_digest,
)
from paperforge.architecture_audit.layers import (
    SCHEMA_VERSION,
    ArchitectureContract,
    ArchitectureError,
    ArchitectureReportView,
    ArchitectureReview,
    ArchitectureSurvey,
    Assessment,
    AssessmentStatus,
    AuditContent,
    CanonicalWriteFact,
    CoverageStatus,
    DeterministicAudit,
    EffectFact,
    EffectKind,
    EnforcementMode,
    Evidence,
    Finding,
    IntentMode,
    LifecycleStatus,
    RoleAuthorityFact,
    Rule,
    RuleCoverage,
    RuleKind,
    RuleStatus,
    SignalConsumerKind,
    SignalFact,
    UnitAuthorityFact,
    validate_contract,
    validate_review,
    validate_survey,
)

RECONCILER_VERSION = "1.0.0"

DEFAULT_ALLOWED_QUERY_EFFECTS = (
    EffectKind.DISPOSABLE_SNAPSHOT,
    EffectKind.LOG_DIAGNOSTIC,
)
DEFAULT_REQUIRED_CONSUMER_KINDS = (SignalConsumerKind.CODE,)
DEFAULT_ACCEPTED_INTENT_MODES = (
    IntentMode.DIRECT_INVOCATION,
    IntentMode.UI_MODAL,
    IntentMode.EXPLICIT_FLAG,
    IntentMode.INTERACTIVE_PROMPT,
)


class DigestMismatch(ValueError):
    """Review is not bound to the exact Contract/Survey/Audit it was written for."""


# ---------------------------------------------------------------- helpers


def _facts_of(survey: ArchitectureSurvey, kind: type) -> list[Any]:
    return [fact for fact in survey.facts if isinstance(fact, kind)]


def _absence_is_observed(survey: ArchitectureSurvey) -> bool:
    """Absence of facts counts as satisfaction only when required coverage is complete."""
    required = [c for c in survey.coverage if c.required]
    return all(c.status is CoverageStatus.COMPLETE for c in required) if required else True


def _evidence_of(fact: Any) -> list[Evidence]:
    evidence = getattr(fact, "evidence", None)
    return [evidence] if evidence is not None else []


def _forbidden_query_effects(rule: Rule, survey: ArchitectureSurvey) -> tuple[list[EffectFact], list[EffectFact]]:
    allowed = set(rule.allowed_query_effects or DEFAULT_ALLOWED_QUERY_EFFECTS)
    effects = [fact for fact in _facts_of(survey, EffectFact) if fact.operation_id == rule.subject]
    violations = [fact for fact in effects if fact.effect_kind not in allowed]
    return violations, effects


def _remote_facts(rule: Rule, survey: ArchitectureSurvey) -> list[EffectFact]:
    return [
        fact
        for fact in _facts_of(survey, EffectFact)
        if fact.operation_id == rule.subject and fact.effect_kind is EffectKind.REMOTE_OPERATION
    ]


def _signal_facts(rule: Rule, survey: ArchitectureSurvey) -> list[SignalFact]:
    return [fact for fact in _facts_of(survey, SignalFact) if fact.signal_id == rule.subject]


def _unit_facts(rule: Rule, survey: ArchitectureSurvey) -> list[UnitAuthorityFact]:
    return [fact for fact in _facts_of(survey, UnitAuthorityFact) if fact.unit_id == rule.subject]


def _write_facts(rule: Rule, survey: ArchitectureSurvey) -> list[CanonicalWriteFact]:
    return [fact for fact in _facts_of(survey, CanonicalWriteFact) if fact.unit_id == rule.subject]


def _role_facts(rule: Rule, survey: ArchitectureSurvey) -> list[RoleAuthorityFact]:
    role = rule.scope[0] if rule.scope else ""
    return [
        fact
        for fact in survey.facts
        if isinstance(fact, RoleAuthorityFact) and fact.operation_id == rule.subject and fact.role == role
    ]


# ---------------------------------------------------------------- rule evaluation


def _evaluate_rule(
    rule: Rule,
    contract: ArchitectureContract,
    survey: ArchitectureSurvey,
) -> tuple[RuleStatus, str, list[Evidence]]:
    """Evaluate one active rule against observed facts. Returns (status, message, evidence)."""

    if rule.kind is RuleKind.QUERY_SIDE_EFFECT:
        violations, effects = _forbidden_query_effects(rule, survey)
        if not effects:
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, "no observed side effects", []
            return RuleStatus.UNRESOLVED, "no effect facts and coverage incomplete", []
        if violations:
            names = ", ".join(sorted({fact.effect_kind.value for fact in violations}))
            return RuleStatus.VIOLATED, f"forbidden query effects observed: {names}", [
                e for fact in violations for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "all observed effects allowed", [
            e for fact in effects for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.REMOTE_INTENT:
        accepted = set(rule.accepted_intent_modes or DEFAULT_ACCEPTED_INTENT_MODES)
        remote = _remote_facts(rule, survey)
        if not remote:
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, "no remote operations observed", []
            return RuleStatus.UNRESOLVED, "no remote-operation facts and coverage incomplete", []
        violations = [fact for fact in remote if fact.intent_mode not in accepted]
        if violations:
            modes = ", ".join(sorted({(fact.intent_mode or IntentMode.IMPLICIT).value for fact in violations}))
            return RuleStatus.VIOLATED, f"remote operations without accepted intent: {modes}", [
                e for fact in violations for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "all remote operations carry accepted intent", [
            e for fact in remote for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.SIGNAL_CONSUMER:
        required = set(rule.required_consumer_kinds or DEFAULT_REQUIRED_CONSUMER_KINDS)
        signals = _signal_facts(rule, survey)
        if not signals:
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, "no signals observed", []
            return RuleStatus.UNRESOLVED, "no signal facts and coverage incomplete", []
        orphans = [fact for fact in signals if fact.consumer_kind in required and not fact.has_code_consumer]
        if orphans:
            ids = ", ".join(sorted({fact.signal_id for fact in orphans}))
            return RuleStatus.VIOLATED, f"signals without required code consumer: {ids}", [
                e for fact in orphans for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "all signals have consumers for their declared kind", [
            e for fact in signals for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.PUBLICATION_AUTHORITY:
        units = _unit_facts(rule, survey)
        if not units:
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, "no unit authority facts observed", []
            return RuleStatus.UNRESOLVED, "no unit authority facts and coverage incomplete", []
        declared = next(
            (u.publication_authority for u in contract.publication_units if u.unit_id == rule.subject),
            None,
        )
        for unit in units:
            if len(unit.publication_authorities) != 1:
                count = len(unit.publication_authorities)
                return (
                    RuleStatus.VIOLATED,
                    f"unit {unit.unit_id} has {count} publication authorities; exactly one required",
                    _evidence_of(unit),
                )
            if declared is not None and unit.publication_authorities[0] != declared:
                return (
                    RuleStatus.VIOLATED,
                    f"unit {unit.unit_id} observed authority {unit.publication_authorities[0]!r} "
                    f"differs from declared {declared!r}",
                    _evidence_of(unit),
                )
        return RuleStatus.SATISFIED, "one publication authority per unit matching the declaration", [
            e for unit in units for e in _evidence_of(unit)
        ]

    if rule.kind is RuleKind.ROLE_AUTHORITY:
        facts = _role_facts(rule, survey)
        if not facts:
            role = rule.scope[0] if rule.scope else "?"
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, f"no {role} authority facts observed", []
            return RuleStatus.UNRESOLVED, f"no {role} authority facts and coverage incomplete", []
        for fact in facts:
            if len(fact.authorities) != 1:
                count = len(fact.authorities)
                return (
                    RuleStatus.VIOLATED,
                    f"operation {fact.operation_id} role {fact.role!r} has {count} authorities; exactly one required",
                    _evidence_of(fact),
                )
        return RuleStatus.SATISFIED, "one authority per role", [e for fact in facts for e in _evidence_of(fact)]

    if rule.kind is RuleKind.CANONICAL_WRITER:
        writes = _write_facts(rule, survey)
        if not writes:
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, "no canonical writes observed", []
            return RuleStatus.UNRESOLVED, "no canonical-write facts and coverage incomplete", []
        ui_writes = [fact for fact in writes if fact.actor_kind == "ui"]
        if ui_writes:
            return RuleStatus.VIOLATED, "UI directly writes a canonical publication unit", [
                e for fact in ui_writes for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "canonical writes originate from backend actors", [
            e for fact in writes for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.PUBLICATION_MARKER:
        writes = _write_facts(rule, survey)
        if not writes:
            if _absence_is_observed(survey):
                return RuleStatus.SATISFIED, "no canonical writes observed", []
            return RuleStatus.UNRESOLVED, "no canonical-write facts and coverage incomplete", []
        bypass = [fact for fact in writes if not fact.via_publication_protocol]
        if bypass:
            return RuleStatus.VIOLATED, "canonical writes bypass the publication protocol", [
                e for fact in bypass for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "all canonical writes use the publication protocol", [
            e for fact in writes for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.COVERAGE_COMPLETE:
        incomplete = [c for c in survey.coverage if c.required and c.status is not CoverageStatus.COMPLETE]
        if incomplete:
            names = ", ".join(sorted({f"{c.extractor}={c.status.value}" for c in incomplete}))
            return RuleStatus.VIOLATED, f"required coverage incomplete: {names}", []
        return RuleStatus.SATISFIED, "all required extractor coverage complete", []

    return RuleStatus.NOT_EVALUATED, f"no evaluation for rule kind {rule.kind.value}", []


# ---------------------------------------------------------------- assessment


def _assess(survey: ArchitectureSurvey, findings: list[Finding], failed_reasons: list[str]) -> Assessment:
    if failed_reasons:
        return Assessment(status=AssessmentStatus.FAILED, gate_eligible=False, reasons=tuple(failed_reasons))
    incomplete = [c for c in survey.coverage if c.required and c.status is not CoverageStatus.COMPLETE]
    if incomplete:
        return Assessment(
            status=AssessmentStatus.INCOMPLETE,
            gate_eligible=False,
            reasons=tuple(sorted({f"{c.extractor}_coverage_{c.status.value}" for c in incomplete})),
        )
    if findings:
        return Assessment(status=AssessmentStatus.FINDINGS, gate_eligible=True)
    return Assessment(status=AssessmentStatus.CLEAN, gate_eligible=True)


# ---------------------------------------------------------------- reconcile


def reconcile(contract: ArchitectureContract, survey: ArchitectureSurvey) -> DeterministicAudit:
    """Deterministic, side-effect-free evaluation of Contract rules against Survey facts.

    Validation failures produce a `failed` assessment audit instead of raising,
    so the whole chain stays serializable and downstream consumers see one
    authoritative outcome. Direct `validate_*()` calls still raise for load-time
    rejection.
    """
    try:
        validate_contract(contract)
        validate_survey(survey)
    except ArchitectureError as exc:
        content = AuditContent(
            reconciler_version=RECONCILER_VERSION,
            bound_contract_digest=sha256_digest(canonical_json(contract.to_dict())),
            bound_survey_digest=semantic_digest(survey.semantic_content()),
            findings=(),
            rule_coverage=(),
            assessment=Assessment(
                status=AssessmentStatus.FAILED,
                gate_eligible=False,
                reasons=(f"validation_failed: {exc}",),
            ),
            coverage=tuple(survey.coverage),
        )
        return DeterministicAudit(
            schema_version=SCHEMA_VERSION,
            content=content,
            run_metadata={},
            semantic_digest=semantic_digest(content.to_dict()),
        )

    findings: list[Finding] = []
    coverage_rows: list[RuleCoverage] = []
    failed_reasons: list[str] = []

    for rule in contract.rules:
        if rule.lifecycle is LifecycleStatus.DEPRECATED:
            coverage_rows.append(RuleCoverage(rule_id=rule.rule_id, evaluated=False, reason="deprecated"))
            continue

        if rule.lifecycle is LifecycleStatus.PLANNED:
            coverage_rows.append(RuleCoverage(rule_id=rule.rule_id, evaluated=False, reason="planned"))
            findings.append(Finding(
                finding_id=finding_id(rule.rule_id, [rule.subject], []),
                rule_id=rule.rule_id,
                subject=rule.subject,
                rule_status=RuleStatus.PLANNED_GAP,
                severity="informational",
                message="declared but not yet effective",
            ))
            continue

        status, message, evidence = _evaluate_rule(rule, contract, survey)
        if status is RuleStatus.VIOLATED and any(
            e.rule_id == rule.rule_id and e.subject == rule.subject for e in contract.exceptions
        ):
            status = RuleStatus.EXCEPTION_APPLIED
            message = f"violation covered by declared exception; {message}"

        coverage_rows.append(RuleCoverage(rule_id=rule.rule_id, evaluated=True, status=status, reason=message))

        if status in (RuleStatus.VIOLATED, RuleStatus.EXCEPTION_APPLIED):
            severity = (
                "blocking"
                if rule.enforcement is EnforcementMode.BLOCKING
                else "advisory" if rule.enforcement is EnforcementMode.ADVISORY else "informational"
            )
            findings.append(Finding(
                finding_id=finding_id(
                    rule.rule_id,
                    [rule.subject, *rule.scope],
                    [e.symbol for e in evidence],
                ),
                rule_id=rule.rule_id,
                subject=rule.subject,
                rule_status=status,
                severity=severity,
                message=message,
                evidence=tuple(evidence),
            ))

    assessment = _assess(survey, findings, failed_reasons)
    content = AuditContent(
        reconciler_version=RECONCILER_VERSION,
        bound_contract_digest=sha256_digest(canonical_json(contract.to_dict())),
        bound_survey_digest=semantic_digest(survey.semantic_content()),
        findings=tuple(findings),
        rule_coverage=tuple(coverage_rows),
        assessment=assessment,
        coverage=tuple(survey.coverage),
    )
    return DeterministicAudit(
        schema_version=SCHEMA_VERSION,
        content=content,
        run_metadata={},
        semantic_digest=semantic_digest(content.to_dict()),
    )


# ---------------------------------------------------------------- compose


def compose(audit: DeterministicAudit, review: ArchitectureReview | None = None) -> ArchitectureReportView:
    """Read-only projection. Rejects a Review not bound to this exact Audit."""
    if review is not None:
        validate_review(review)
        mismatches = []
        if review.audit_digest != audit.semantic_digest:
            mismatches.append("audit_digest")
        if review.contract_digest != audit.content.bound_contract_digest:
            mismatches.append("contract_digest")
        if review.survey_digest != audit.content.bound_survey_digest:
            mismatches.append("survey_digest")
        if review.reconciler_version != audit.content.reconciler_version:
            mismatches.append("reconciler_version")
        if mismatches:
            raise DigestMismatch("review not bound to this audit: " + ", ".join(mismatches))

    return ArchitectureReportView(
        schema_version=SCHEMA_VERSION,
        audit_digest=audit.semantic_digest,
        review_digest=semantic_digest(review.semantic_content()) if review is not None else None,
        assessment=audit.content.assessment,
        deterministic_findings=audit.content.findings,
        review_adjudications=review.adjudications if review is not None else (),
        semantic_findings=review.semantic_findings if review is not None else (),
        evidence_requests=review.evidence_requests if review is not None else (),
    )
