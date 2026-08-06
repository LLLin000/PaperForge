"""Pure deterministic reconciliation engine (#130 Slice A, owned exclusively by #131).

`reconcile(contract, survey) -> DeterministicAudit` evaluates every contract rule
against observed survey facts. It never queries GitHub, never touches the network,
never auto-changes lifecycle status, and never modifies its inputs.

Assessment precedence (#131): failed > incomplete > findings > clean.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
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
    AuthorityRole,
    CanonicalWriteFact,
    CoverageEntry,
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
    _review_projection_digest,
    _rule_entity_metas,
    validate_audit,
    validate_contract,
    validate_report_view,
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


def _stable_failure_digest(value: Any) -> str:
    """Hash malformed layer values without object-address-dependent repr output."""
    def normalize(item: Any) -> Any:
        if item is None or isinstance(item, (bool, float, int, str)):
            return item
        if isinstance(item, Enum):
            return {
                "enum": f"{type(item).__module__}.{type(item).__qualname__}",
                "value": normalize(item.value),
            }
        if is_dataclass(item) and not isinstance(item, type):
            return {
                "dataclass": f"{type(item).__module__}.{type(item).__qualname__}",
                "fields": {field.name: normalize(getattr(item, field.name)) for field in fields(item)},
            }
        if isinstance(item, Mapping):
            pairs = [(normalize(key), normalize(entry)) for key, entry in item.items()]
            return {"mapping": sorted(pairs, key=canonical_json)}
        if isinstance(item, (list, tuple)):
            return [normalize(entry) for entry in item]
        if isinstance(item, (set, frozenset)):
            return sorted((normalize(entry) for entry in item), key=canonical_json)
        return {"type": f"{type(item).__module__}.{type(item).__qualname__}"}

    return sha256_digest(canonical_json(normalize(value)))

def _required_coverage(contract: ArchitectureContract, survey: ArchitectureSurvey) -> tuple[CoverageEntry, ...]:
    """Return the union of contract-required and survey-required coverage."""
    rows = {entry.extractor: entry for entry in survey.coverage}
    required_names = set(contract.required_extractors)
    required_names.update(entry.extractor for entry in survey.coverage if entry.required)
    result: list[CoverageEntry] = []
    for extractor in sorted(required_names):
        entry = rows.get(
            extractor,
            CoverageEntry(
                extractor=extractor,
                status=CoverageStatus.UNAVAILABLE,
                required=True,
                diagnostics=("missing coverage row",),
            ),
        )
        if not entry.required:
            entry = CoverageEntry(
                extractor=entry.extractor,
                status=entry.status,
                required=True,
                diagnostics=entry.diagnostics,
            )
        result.append(entry)
    return tuple(result)


def _absence_is_observed(contract: ArchitectureContract, survey: ArchitectureSurvey) -> bool:
    """Absence is meaningful only after at least one required extractor completed."""
    coverage = _required_coverage(contract, survey)
    return bool(coverage) and not survey.parse_errors and all(
        entry.status is CoverageStatus.COMPLETE for entry in coverage
    )


def _evidence_of(fact: Any) -> list[Evidence]:
    evidence = getattr(fact, "evidence", None)
    result = [evidence] if evidence is not None else []
    consumer_evidence = getattr(fact, "consumer_evidence", ())
    result.extend(consumer_evidence)
    return result


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
    role = rule.authority_role or ""
    return [
        fact
        for fact in survey.facts
        if isinstance(fact, RoleAuthorityFact) and fact.operation_id == rule.subject and fact.role == role
    ]

def _declared_role_authority(
    contract: ArchitectureContract,
    operation_id: str,
    role: str,
) -> tuple[str, ...] | None:
    declared: list[str] = []
    for operation in contract.operations:
        if operation.operation_id != operation_id:
            continue
        for authority in operation.authorities:
            if authority.role.value == role:
                declared.append(authority.authority_id)
            if role == AuthorityRole.OBSERVER.value:
                declared.extend(authority.observers)
            elif role == AuthorityRole.DELEGATED_EXECUTOR.value:
                declared.extend(authority.delegated_executors)
        break
    identities = tuple(dict.fromkeys(declared))
    return identities or None


def _declared_unit(contract: ArchitectureContract, unit_id: str):
    return next((unit for unit in contract.publication_units if unit.unit_id == unit_id), None)

def _effective_lifecycle(rule: Rule, contract: ArchitectureContract) -> LifecycleStatus:
    lifecycles = [rule.lifecycle, *(meta.lifecycle for meta in _rule_entity_metas(rule, contract))]
    if LifecycleStatus.DEPRECATED in lifecycles:
        return LifecycleStatus.DEPRECATED
    if LifecycleStatus.PLANNED in lifecycles:
        return LifecycleStatus.PLANNED
    return LifecycleStatus.ACTIVE


def _effective_enforcement(rule: Rule, contract: ArchitectureContract) -> EnforcementMode:
    modes = [
        rule.enforcement,
        *(meta.enforcement for meta in _rule_entity_metas(rule, contract) if meta.enforcement is not None),
    ]
    return max(
        modes,
        key={
            EnforcementMode.OBSERVE: 0,
            EnforcementMode.ADVISORY: 1,
            EnforcementMode.BLOCKING: 2,
        }.__getitem__,
    )


# ---------------------------------------------------------------- rule evaluation

# #130 review B2: rules that assert universal/negative properties over the
# whole codebase (all remote ops carry intent, all signals consumed, no UI
# writer, all writes via protocol) cannot conclude satisfied from partial
# facts while required coverage is incomplete — the unseen callsites may
# violate. Only enumeration-complete audits may conclude on them.
_ENUMERATION_KINDS = (
    RuleKind.QUERY_SIDE_EFFECT,
    RuleKind.REMOTE_INTENT,
    RuleKind.SIGNAL_CONSUMER,
    RuleKind.CANONICAL_WRITER,
    RuleKind.PUBLICATION_MARKER,
    RuleKind.PUBLICATION_AUTHORITY,
    RuleKind.ROLE_AUTHORITY,
)


def _required_coverage_complete(contract: ArchitectureContract, survey: ArchitectureSurvey) -> bool:
    coverage = _required_coverage(contract, survey)
    return bool(coverage) and all(entry.status is CoverageStatus.COMPLETE for entry in coverage)


def _evaluate_rule(
    rule: Rule,
    contract: ArchitectureContract,
    survey: ArchitectureSurvey,
) -> tuple[RuleStatus, str, list[Evidence]]:
    """Evaluate one active rule against observed facts. Returns (status, message, evidence)."""

    if rule.kind in _ENUMERATION_KINDS and not _required_coverage_complete(contract, survey):
        return RuleStatus.UNRESOLVED, "coverage incomplete: cannot enumerate all callsites", []

    if rule.kind is RuleKind.QUERY_SIDE_EFFECT:
        violations, effects = _forbidden_query_effects(rule, survey)
        if not effects:
            if _absence_is_observed(contract, survey):
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
            if _absence_is_observed(contract, survey):
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
            if _absence_is_observed(contract, survey):
                return RuleStatus.SATISFIED, "no signals observed", []
            return RuleStatus.UNRESOLVED, "no signal facts and coverage incomplete", []
        orphans = [
            fact
            for fact in signals
            if fact.consumer_kind in required
            and (
                not fact.has_code_consumer
                or fact.consumer is None
                or not fact.consumer_evidence
            )
        ]
        if orphans:
            ids = ", ".join(sorted({fact.signal_id for fact in orphans}))
            return RuleStatus.VIOLATED, f"signals without auditable required consumer: {ids}", [
                e for fact in orphans for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "all signals have consumers for their declared kind", [
            e for fact in signals for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.PUBLICATION_AUTHORITY:
        units = _unit_facts(rule, survey)
        if not units:
            return RuleStatus.UNRESOLVED, "no unit authority facts observed", []
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
        role = rule.authority_role or "?"
        if not facts:
            return RuleStatus.UNRESOLVED, f"no {role} authority facts observed", []
        declared = _declared_role_authority(contract, rule.subject, role)
        if declared is None:
            return RuleStatus.UNRESOLVED, f"no declared {role} authority for operation {rule.subject}", []
        multi_valued = role in {
            AuthorityRole.OBSERVER.value,
            AuthorityRole.DELEGATED_EXECUTOR.value,
        }
        for fact in facts:
            if not fact.authorities:
                return (
                    RuleStatus.VIOLATED,
                    f"operation {fact.operation_id} role {fact.role!r} has no authorities",
                    _evidence_of(fact),
                )
            if not multi_valued and len(fact.authorities) != 1:
                count = len(fact.authorities)
                return (
                    RuleStatus.VIOLATED,
                    f"operation {fact.operation_id} role {fact.role!r} has {count} authorities; exactly one required",
                    _evidence_of(fact),
                )
            if multi_valued:
                observed = set(fact.authorities)
                declared_set = set(declared)
                if observed != declared_set:
                    missing = sorted(declared_set - observed)
                    unexpected = sorted(observed - declared_set)
                    return (
                        RuleStatus.VIOLATED,
                        f"operation {fact.operation_id} role {fact.role!r} authorities differ from declared "
                        f"{declared!r}; missing={missing!r}, unexpected={unexpected!r}",
                        _evidence_of(fact),
                    )
            elif fact.authorities[0] not in declared:
                return (
                    RuleStatus.VIOLATED,
                    f"operation {fact.operation_id} role {fact.role!r} observed authority "
                    f"{fact.authorities[0]!r} differs from declared {declared!r}",
                    _evidence_of(fact),
                )
        return RuleStatus.SATISFIED, "observed authorities match the declaration", [
            e for fact in facts for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.CANONICAL_WRITER:
        writes = _write_facts(rule, survey)
        if not writes:
            if _absence_is_observed(contract, survey):
                return RuleStatus.SATISFIED, "no canonical writes observed", []
            return RuleStatus.UNRESOLVED, "no canonical-write facts and coverage incomplete", []
        unit = _declared_unit(contract, rule.subject)
        violations: list[CanonicalWriteFact] = []
        messages: list[str] = []
        for fact in writes:
            writer = fact.writer_id or fact.actor_kind
            if fact.actor_kind == "ui":
                violations.append(fact)
                messages.append("UI directly writes a publication unit")
            if unit is not None and unit.authorized_writers and writer not in unit.authorized_writers:
                violations.append(fact)
                messages.append(f"writer {writer!r} is not authorized")
            if unit is not None and not fact.via_publication_protocol:
                violations.append(fact)
                messages.append("write bypasses the publication protocol")
            if (
                unit is not None
                and fact.publication_authority is not None
                and fact.publication_authority != unit.publication_authority
            ):
                violations.append(fact)
                messages.append("write uses a different publication authority")
        if violations:
            return RuleStatus.VIOLATED, "; ".join(sorted(set(messages))), [
                e for fact in violations for e in _evidence_of(fact)
            ]
        return RuleStatus.SATISFIED, "all canonical writes use authorized protocol writers", [
            e for fact in writes for e in _evidence_of(fact)
        ]

    if rule.kind is RuleKind.PUBLICATION_MARKER:
        writes = _write_facts(rule, survey)
        if not writes:
            if _absence_is_observed(contract, survey):
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
        required = _required_coverage(contract, survey)
        if not required:
            return RuleStatus.UNRESOLVED, "no required extractor coverage declared", []
        incomplete = [c for c in required if c.status is not CoverageStatus.COMPLETE]
        if incomplete:
            names = ", ".join(sorted({f"{c.extractor}={c.status.value}" for c in incomplete}))
            return RuleStatus.VIOLATED, f"required coverage incomplete: {names}", []
        return RuleStatus.SATISFIED, "all required extractor coverage complete", []

    return RuleStatus.NOT_EVALUATED, f"no evaluation for rule kind {rule.kind.value}", []


# ---------------------------------------------------------------- assessment


def _assess(
    contract: ArchitectureContract,
    survey: ArchitectureSurvey,
    findings: list[Finding],
    failed_reasons: list[str],
) -> Assessment:
    coverage = _required_coverage(contract, survey)
    failed_reasons.extend(
        f"{entry.extractor}_coverage_failed"
        for entry in coverage
        if entry.status is CoverageStatus.FAILED
    )
    failed_reasons.extend(f"parse_error: {error}" for error in survey.parse_errors)
    if failed_reasons:
        return Assessment(
            status=AssessmentStatus.FAILED,
            gate_eligible=False,
            reasons=tuple(sorted(set(failed_reasons))),
        )
    incomplete = [entry for entry in coverage if entry.status is not CoverageStatus.COMPLETE]
    if not coverage:
        incomplete = [CoverageEntry(extractor="coverage", status=CoverageStatus.UNAVAILABLE)]
    if incomplete:
        return Assessment(
            status=AssessmentStatus.INCOMPLETE,
            gate_eligible=False,
            reasons=tuple(sorted({f"{entry.extractor}_coverage_{entry.status.value}" for entry in incomplete})),
        )
    if findings:
        return Assessment(status=AssessmentStatus.FINDINGS, gate_eligible=True)
    return Assessment(status=AssessmentStatus.CLEAN, gate_eligible=True)

def _failed_coverage(
    contract: ArchitectureContract,
    survey: ArchitectureSurvey,
) -> tuple[CoverageEntry, ...]:
    """Normalize malformed input coverage, preserving contract-required rows."""
    rows: dict[str, CoverageEntry] = {}
    for entry in survey.coverage:
        if entry.extractor not in rows:
            rows[entry.extractor] = CoverageEntry(
                extractor=entry.extractor,
                status=CoverageStatus.FAILED,
                required=True,
                diagnostics=tuple(dict.fromkeys((*entry.diagnostics, "validation failed"))),
            )
    required_names = set(contract.required_extractors)
    required_names.update(entry.extractor for entry in survey.coverage if entry.required)
    for extractor in required_names:
        rows.setdefault(
            extractor,
            CoverageEntry(
                extractor=extractor,
                status=CoverageStatus.FAILED,
                required=True,
                diagnostics=("validation failed",),
            ),
        )
    return tuple(rows[name] for name in sorted(rows))



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
        try:
            contract_digest = sha256_digest(canonical_json(contract.to_dict()))
        except (AttributeError, TypeError, ValueError):
            contract_digest = _stable_failure_digest(contract)
        try:
            survey_digest = semantic_digest(survey.semantic_content())
        except (AttributeError, TypeError, ValueError):
            survey_digest = _stable_failure_digest(survey)
        content = AuditContent(
            reconciler_version=RECONCILER_VERSION,
            bound_contract_digest=contract_digest,
            bound_survey_digest=survey_digest,
            findings=(),
            rule_coverage=(),
            assessment=Assessment(
                status=AssessmentStatus.FAILED,
                gate_eligible=False,
                reasons=(f"validation_failed: {exc}",),
            ),
            coverage=_failed_coverage(contract, survey),
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
        lifecycle = _effective_lifecycle(rule, contract)
        if lifecycle is LifecycleStatus.DEPRECATED:
            coverage_rows.append(RuleCoverage(rule_id=rule.rule_id, evaluated=False, reason="deprecated"))
            continue

        if lifecycle is LifecycleStatus.PLANNED:
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

        if status not in (RuleStatus.VIOLATED, RuleStatus.EXCEPTION_APPLIED, RuleStatus.UNRESOLVED):
            continue
        enforcement = _effective_enforcement(rule, contract)
        severity = (
            "blocking"
            if enforcement is EnforcementMode.BLOCKING
            else "advisory" if enforcement is EnforcementMode.ADVISORY else "informational"
        )
        finding_subjects = [rule.subject, *rule.scope]
        if rule.authority_role:
            finding_subjects.append(f"authority_role:{rule.authority_role}")
        findings.append(
            Finding(
                finding_id=finding_id(
                    rule.rule_id,
                    finding_subjects,
                    [{"file": e.file, "symbol": e.symbol} for e in evidence],
                ),
                rule_id=rule.rule_id,
                subject=rule.subject,
                rule_status=status,
                severity=severity,
                message=message,
                evidence=tuple(dict.fromkeys(evidence)),
            )
        )

    assessment = _assess(contract, survey, findings, failed_reasons)
    content = AuditContent(
        reconciler_version=RECONCILER_VERSION,
        bound_contract_digest=sha256_digest(canonical_json(contract.to_dict())),
        bound_survey_digest=semantic_digest(survey.semantic_content()),
        findings=tuple(findings),
        rule_coverage=tuple(coverage_rows),
        assessment=assessment,
        coverage=tuple(_required_coverage(contract, survey)),
    )
    return DeterministicAudit(
        schema_version=SCHEMA_VERSION,
        content=content,
        run_metadata={},
        semantic_digest=semantic_digest(content.to_dict()),
    )


# ---------------------------------------------------------------- compose


def compose(audit: DeterministicAudit, review: ArchitectureReview | None = None) -> ArchitectureReportView:
    """Read-only projection. Rejects tampered audits and stale Reviews."""
    validate_audit(audit)
    if review is not None:
        validate_review(review, audit)
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

    view = ArchitectureReportView(
        schema_version=SCHEMA_VERSION,
        audit_digest=audit.semantic_digest,
        review_digest=(
            _review_projection_digest(
                review.adjudications,
                review.semantic_findings,
                review.evidence_requests,
            )
            if review is not None and (
                review.adjudications or review.semantic_findings or review.evidence_requests
            )
            else None
        ),
        assessment=audit.content.assessment,
        deterministic_findings=audit.content.findings,
        review_adjudications=review.adjudications if review is not None else (),
        semantic_findings=review.semantic_findings if review is not None else (),
        evidence_requests=review.evidence_requests if review is not None else (),
    )
    validate_report_view(view, audit)
    return view
