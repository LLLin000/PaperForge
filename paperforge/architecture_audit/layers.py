"""Architecture Audit — immutable layer models (#130 Slice A).

Five layers with strict epistemic separation:

1. **ArchitectureContract** — declared intent (manual).
2. **ArchitectureSurvey** — deterministic observation only.
3. **DeterministicAudit** — deterministic reconciliation of Contract + Survey.
4. **ArchitectureReview** — Agent/Human overlay, digest-bound, advisory.
5. **ArchitectureReportView** — read-only projection for presentation.

Review can never mutate Survey facts or deterministic findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- enums


class LifecycleStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class EnforcementMode(str, Enum):
    OBSERVE = "observe"
    ADVISORY = "advisory"
    BLOCKING = "blocking"


class EpistemicStatus(str, Enum):
    DECLARED = "declared"
    OBSERVED_STATIC = "observed_static"
    OBSERVED_RUNTIME = "observed_runtime"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"


class Confidence(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleKind(str, Enum):
    QUERY_SIDE_EFFECT = "query_side_effect"
    REMOTE_INTENT = "remote_intent"
    SIGNAL_CONSUMER = "signal_consumer"
    PUBLICATION_AUTHORITY = "publication_authority"
    ROLE_AUTHORITY = "role_authority"
    CANONICAL_WRITER = "canonical_writer"
    PUBLICATION_MARKER = "publication_marker"
    COVERAGE_COMPLETE = "coverage_complete"


class RuleStatus(str, Enum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    PLANNED_GAP = "planned_gap"
    EXCEPTION_APPLIED = "exception_applied"
    UNRESOLVED = "unresolved"
    NOT_EVALUATED = "not_evaluated"


class AdjudicationKind(str, Enum):
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    CONTRACT_DRIFT = "contract_drift"
    INTENTIONAL_EXCEPTION_RECOMMENDED = "intentional_exception_recommended"
    NEEDS_EVIDENCE = "needs_evidence"


class AssessmentStatus(str, Enum):
    CLEAN = "clean"
    FINDINGS = "findings"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


class SignalConsumerKind(str, Enum):
    CODE = "code"
    HUMAN_TERMINAL = "human_terminal"
    DIAGNOSTIC_LOG = "diagnostic_log"
    OPTIONAL_OBSERVER = "optional_observer"


class IntentMode(str, Enum):
    DIRECT_INVOCATION = "direct_invocation"
    UI_MODAL = "ui_modal"
    EXPLICIT_FLAG = "explicit_flag"
    INTERACTIVE_PROMPT = "interactive_prompt"
    IMPLICIT = "implicit"  # no direct user intent; never an accepted mode


class EffectKind(str, Enum):
    BUSINESS_MUTATION = "business_mutation"
    MATERIALIZATION_BUILD = "materialization_build"
    REMOTE_OPERATION = "remote_operation"
    DISPOSABLE_SNAPSHOT = "disposable_snapshot"
    LOG_DIAGNOSTIC = "log_diagnostic"


class CoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


# ---------------------------------------------------------------- shared


class ArchitectureError(ValueError):
    """Invalid layer payload; raised at construction/load time."""


@dataclass(frozen=True)
class Evidence:
    file: str  # POSIX repository-relative path
    file_digest: str  # "sha256:<hex>"
    symbol: str
    line_start: int
    line_end: int
    extractor: str
    epistemic_status: EpistemicStatus
    confidence: Confidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "file_digest": self.file_digest,
            "symbol": self.symbol,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "extractor": self.extractor,
            "epistemic_status": self.epistemic_status.value,
            "confidence": self.confidence.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Evidence:
        return cls(
            file=data["file"],
            file_digest=data["file_digest"],
            symbol=data["symbol"],
            line_start=data["line_start"],
            line_end=data["line_end"],
            extractor=data["extractor"],
            epistemic_status=EpistemicStatus(data["epistemic_status"]),
            confidence=Confidence(data["confidence"]),
        )


# ---------------------------------------------------------------- contract


@dataclass(frozen=True)
class EffectiveAfter:
    issue: str
    commit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"issue": self.issue}
        if self.commit is not None:
            out["commit"] = self.commit
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EffectiveAfter:
        return cls(issue=data["issue"], commit=data.get("commit"))


@dataclass(frozen=True)
class KnownGap:
    issue: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {"issue": self.issue, "rationale": self.rationale}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnownGap:
        return cls(issue=data["issue"], rationale=data["rationale"])


@dataclass(frozen=True)
class Rule:
    rule_id: str
    kind: RuleKind
    subject: str  # publication unit / operation / signal id
    scope: tuple[str, ...] = ()
    description: str = ""
    lifecycle: LifecycleStatus = LifecycleStatus.ACTIVE
    enforcement: EnforcementMode = EnforcementMode.BLOCKING
    effective_after: EffectiveAfter | None = None
    known_gap: KnownGap | None = None
    # kind-specific parameters
    allowed_query_effects: tuple[EffectKind, ...] = ()
    accepted_intent_modes: tuple[IntentMode, ...] = ()
    required_consumer_kinds: tuple[SignalConsumerKind, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rule_id": self.rule_id,
            "kind": self.kind.value,
            "subject": self.subject,
            "lifecycle": self.lifecycle.value,
            "enforcement": self.enforcement.value,
        }
        if self.scope:
            out["scope"] = list(self.scope)
        if self.description:
            out["description"] = self.description
        if self.effective_after is not None:
            out["effective_after"] = self.effective_after.to_dict()
        if self.known_gap is not None:
            out["known_gap"] = self.known_gap.to_dict()
        if self.allowed_query_effects:
            out["allowed_query_effects"] = [e.value for e in self.allowed_query_effects]
        if self.accepted_intent_modes:
            out["accepted_intent_modes"] = [m.value for m in self.accepted_intent_modes]
        if self.required_consumer_kinds:
            out["required_consumer_kinds"] = [k.value for k in self.required_consumer_kinds]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        return cls(
            rule_id=data["rule_id"],
            kind=RuleKind(data["kind"]),
            subject=data["subject"],
            scope=tuple(data.get("scope", [])),
            description=data.get("description", ""),
            lifecycle=LifecycleStatus(data.get("lifecycle", "active")),
            enforcement=EnforcementMode(data.get("enforcement", "blocking")),
            effective_after=(
                EffectiveAfter.from_dict(data["effective_after"]) if data.get("effective_after") else None
            ),
            known_gap=KnownGap.from_dict(data["known_gap"]) if data.get("known_gap") else None,
            allowed_query_effects=tuple(EffectKind(e) for e in data.get("allowed_query_effects", [])),
            accepted_intent_modes=tuple(IntentMode(m) for m in data.get("accepted_intent_modes", [])),
            required_consumer_kinds=tuple(
                SignalConsumerKind(k) for k in data.get("required_consumer_kinds", [])
            ),
        )


@dataclass(frozen=True)
class ExceptionDecl:
    exception_id: str
    rule_id: str
    subject: str
    rationale: str
    review_condition: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "exception_id": self.exception_id,
            "rule_id": self.rule_id,
            "subject": self.subject,
            "rationale": self.rationale,
        }
        if self.review_condition:
            out["review_condition"] = self.review_condition
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExceptionDecl:
        return cls(
            exception_id=data["exception_id"],
            rule_id=data["rule_id"],
            subject=data["subject"],
            rationale=data["rationale"],
            review_condition=data.get("review_condition", ""),
        )


@dataclass(frozen=True)
class PublicationUnitDecl:
    unit_id: str
    asset_group: str
    publication_authority: str  # exactly one
    authorized_writers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "unit_id": self.unit_id,
            "asset_group": self.asset_group,
            "publication_authority": self.publication_authority,
        }
        if self.authorized_writers:
            out["authorized_writers"] = list(self.authorized_writers)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PublicationUnitDecl:
        return cls(
            unit_id=data["unit_id"],
            asset_group=data["asset_group"],
            publication_authority=data["publication_authority"],
            authorized_writers=tuple(data.get("authorized_writers", [])),
        )


@dataclass(frozen=True)
class ArchitectureContract:
    schema_version: int
    asset_groups: tuple[str, ...]
    publication_units: tuple[PublicationUnitDecl, ...]
    operations: tuple[str, ...]
    rules: tuple[Rule, ...]
    exceptions: tuple[ExceptionDecl, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "asset_groups": list(self.asset_groups),
            "publication_units": [u.to_dict() for u in self.publication_units],
            "operations": list(self.operations),
            "rules": [r.to_dict() for r in self.rules],
            "exceptions": [e.to_dict() for e in self.exceptions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchitectureContract:
        return cls(
            schema_version=data["schema_version"],
            asset_groups=tuple(data["asset_groups"]),
            publication_units=tuple(
                PublicationUnitDecl.from_dict(u) for u in data.get("publication_units", [])
            ),
            operations=tuple(data["operations"]),
            rules=tuple(Rule.from_dict(r) for r in data["rules"]),
            exceptions=tuple(ExceptionDecl.from_dict(e) for e in data.get("exceptions", [])),
        )


# ---------------------------------------------------------------- survey


@dataclass(frozen=True)
class CoverageEntry:
    extractor: str
    status: CoverageStatus
    required: bool = True
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "extractor": self.extractor,
            "status": self.status.value,
        }
        if not self.required:
            out["required"] = False
        if self.diagnostics:
            out["diagnostics"] = list(self.diagnostics)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoverageEntry:
        return cls(
            extractor=data["extractor"],
            status=CoverageStatus(data["status"]),
            required=data.get("required", True),
            diagnostics=tuple(data.get("diagnostics", [])),
        )


@dataclass(frozen=True)
class EffectFact:
    operation_id: str
    effect_kind: EffectKind
    intent_mode: IntentMode | None = None
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "effect",
            "operation_id": self.operation_id,
            "effect_kind": self.effect_kind.value,
        }
        if self.intent_mode is not None:
            out["intent_mode"] = self.intent_mode.value
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EffectFact:
        return cls(
            operation_id=data["operation_id"],
            effect_kind=EffectKind(data["effect_kind"]),
            intent_mode=IntentMode(data["intent_mode"]) if data.get("intent_mode") else None,
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class SignalFact:
    signal_id: str
    producer: str
    consumer_kind: SignalConsumerKind
    has_code_consumer: bool = False
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "signal",
            "signal_id": self.signal_id,
            "producer": self.producer,
            "consumer_kind": self.consumer_kind.value,
            "has_code_consumer": self.has_code_consumer,
        }
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalFact:
        return cls(
            signal_id=data["signal_id"],
            producer=data["producer"],
            consumer_kind=SignalConsumerKind(data["consumer_kind"]),
            has_code_consumer=data.get("has_code_consumer", False),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class UnitAuthorityFact:
    unit_id: str
    publication_authorities: tuple[str, ...]
    authorized_writers: tuple[str, ...] = ()
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "unit_authority",
            "unit_id": self.unit_id,
            "publication_authorities": list(self.publication_authorities),
        }
        if self.authorized_writers:
            out["authorized_writers"] = list(self.authorized_writers)
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnitAuthorityFact:
        return cls(
            unit_id=data["unit_id"],
            publication_authorities=tuple(data["publication_authorities"]),
            authorized_writers=tuple(data.get("authorized_writers", [])),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class RoleAuthorityFact:
    operation_id: str
    role: str  # execution | lifecycle_state | stop | observer | adapter | delegated_executor
    authorities: tuple[str, ...]
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "role_authority",
            "operation_id": self.operation_id,
            "role": self.role,
            "authorities": list(self.authorities),
        }
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoleAuthorityFact:
        return cls(
            operation_id=data["operation_id"],
            role=data["role"],
            authorities=tuple(data["authorities"]),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class CanonicalWriteFact:
    unit_id: str
    actor_kind: str  # "ui" | "backend" | "worker" | "cli" | ...
    via_publication_protocol: bool
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "canonical_write",
            "unit_id": self.unit_id,
            "actor_kind": self.actor_kind,
            "via_publication_protocol": self.via_publication_protocol,
        }
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanonicalWriteFact:
        return cls(
            unit_id=data["unit_id"],
            actor_kind=data["actor_kind"],
            via_publication_protocol=data.get("via_publication_protocol", False),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


FACT_KINDS = {
    "effect": EffectFact,
    "signal": SignalFact,
    "unit_authority": UnitAuthorityFact,
    "role_authority": RoleAuthorityFact,
    "canonical_write": CanonicalWriteFact,
}

SurveyFact = EffectFact | SignalFact | UnitAuthorityFact | RoleAuthorityFact | CanonicalWriteFact


def fact_from_dict(data: dict[str, Any]) -> SurveyFact:
    kind = data.get("kind")
    if not isinstance(kind, str):
        raise ArchitectureError(f"survey fact missing string kind: {kind!r}")
    factory = FACT_KINDS.get(kind)
    if factory is None:
        raise ArchitectureError(f"unknown survey fact kind: {kind!r}")
    return factory.from_dict(data)


@dataclass(frozen=True)
class ArchitectureSurvey:
    schema_version: int
    scope: str
    coverage: tuple[CoverageEntry, ...]
    facts: tuple[SurveyFact, ...]
    source_digest: str  # sha256 over normalized observed source (semantic)
    parse_errors: tuple[str, ...] = ()
    excluded_roots: tuple[str, ...] = ()
    # execution-only metadata (never part of semantic digest)
    run_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scope": self.scope,
            "coverage": [c.to_dict() for c in self.coverage],
            "facts": [f.to_dict() for f in self.facts],
            "source_digest": self.source_digest,
            "parse_errors": list(self.parse_errors),
            "excluded_roots": list(self.excluded_roots),
            "run_metadata": dict(self.run_metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchitectureSurvey:
        return cls(
            schema_version=data["schema_version"],
            scope=data["scope"],
            coverage=tuple(CoverageEntry.from_dict(c) for c in data["coverage"]),
            facts=tuple(fact_from_dict(f) for f in data["facts"]),
            source_digest=data["source_digest"],
            parse_errors=tuple(data.get("parse_errors", [])),
            excluded_roots=tuple(data.get("excluded_roots", [])),
            run_metadata=dict(data.get("run_metadata", {})),
        )

    def semantic_content(self) -> dict[str, Any]:
        """Semantic payload: coverage, facts, source identity. Excludes run_metadata."""
        return {
            "schema_version": self.schema_version,
            "scope": self.scope,
            "coverage": [c.to_dict() for c in self.coverage],
            "facts": [f.to_dict() for f in self.facts],
            "source_digest": self.source_digest,
            "parse_errors": list(self.parse_errors),
            "excluded_roots": list(self.excluded_roots),
        }


# ---------------------------------------------------------------- audit


@dataclass(frozen=True)
class RuleCoverage:
    rule_id: str
    evaluated: bool
    status: RuleStatus | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"rule_id": self.rule_id, "evaluated": self.evaluated}
        if self.status is not None:
            out["status"] = self.status.value
        if self.reason:
            out["reason"] = self.reason
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleCoverage:
        return cls(
            rule_id=data["rule_id"],
            evaluated=data["evaluated"],
            status=RuleStatus(data["status"]) if data.get("status") else None,
            reason=data.get("reason", ""),
        )


@dataclass(frozen=True)
class Finding:
    finding_id: str
    rule_id: str
    subject: str
    rule_status: RuleStatus
    severity: str  # "blocking" | "advisory" | "informational"
    message: str
    evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "subject": self.subject,
            "rule_status": self.rule_status.value,
            "severity": self.severity,
            "message": self.message,
        }
        if self.evidence:
            out["evidence"] = [e.to_dict() for e in self.evidence]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        return cls(
            finding_id=data["finding_id"],
            rule_id=data["rule_id"],
            subject=data["subject"],
            rule_status=RuleStatus(data["rule_status"]),
            severity=data["severity"],
            message=data["message"],
            evidence=tuple(Evidence.from_dict(e) for e in data.get("evidence", [])),
        )


@dataclass(frozen=True)
class Assessment:
    status: AssessmentStatus
    gate_eligible: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "status": self.status.value,
            "gate_eligible": self.gate_eligible,
        }
        if self.reasons:
            out["reasons"] = list(self.reasons)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Assessment:
        return cls(
            status=AssessmentStatus(data["status"]),
            gate_eligible=data["gate_eligible"],
            reasons=tuple(data.get("reasons", [])),
        )


@dataclass(frozen=True)
class AuditContent:
    reconciler_version: str
    bound_contract_digest: str
    bound_survey_digest: str
    findings: tuple[Finding, ...]
    rule_coverage: tuple[RuleCoverage, ...]
    assessment: Assessment
    coverage: tuple[CoverageEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciler_version": self.reconciler_version,
            "bound_contract_digest": self.bound_contract_digest,
            "bound_survey_digest": self.bound_survey_digest,
            "findings": [f.to_dict() for f in self.findings],
            "rule_coverage": [r.to_dict() for r in self.rule_coverage],
            "assessment": self.assessment.to_dict(),
            "coverage": [c.to_dict() for c in self.coverage],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditContent:
        return cls(
            reconciler_version=data["reconciler_version"],
            bound_contract_digest=data["bound_contract_digest"],
            bound_survey_digest=data["bound_survey_digest"],
            findings=tuple(Finding.from_dict(f) for f in data["findings"]),
            rule_coverage=tuple(RuleCoverage.from_dict(r) for r in data["rule_coverage"]),
            assessment=Assessment.from_dict(data["assessment"]),
            coverage=tuple(CoverageEntry.from_dict(c) for c in data["coverage"]),
        )


@dataclass(frozen=True)
class DeterministicAudit:
    schema_version: int
    content: AuditContent
    run_metadata: dict[str, Any]
    semantic_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "content": self.content.to_dict(),
            "run_metadata": dict(self.run_metadata),
            "semantic_digest": self.semantic_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeterministicAudit:
        return cls(
            schema_version=data["schema_version"],
            content=AuditContent.from_dict(data["content"]),
            run_metadata=dict(data.get("run_metadata", {})),
            semantic_digest=data["semantic_digest"],
        )


# ---------------------------------------------------------------- review


@dataclass(frozen=True)
class Adjudication:
    finding_id: str
    adjudication: AdjudicationKind
    rationale: str
    epistemic_status: EpistemicStatus  # inferred | unresolved only
    reviewer: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "finding_id": self.finding_id,
            "adjudication": self.adjudication.value,
            "rationale": self.rationale,
            "epistemic_status": self.epistemic_status.value,
        }
        if self.reviewer:
            out["reviewer"] = self.reviewer
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Adjudication:
        return cls(
            finding_id=data["finding_id"],
            adjudication=AdjudicationKind(data["adjudication"]),
            rationale=data["rationale"],
            epistemic_status=EpistemicStatus(data["epistemic_status"]),
            reviewer=data.get("reviewer", ""),
        )


@dataclass(frozen=True)
class SemanticFinding:
    finding_id: str
    message: str
    epistemic_status: EpistemicStatus
    rationale: str = ""
    evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "finding_id": self.finding_id,
            "message": self.message,
            "epistemic_status": self.epistemic_status.value,
        }
        if self.rationale:
            out["rationale"] = self.rationale
        if self.evidence:
            out["evidence"] = [e.to_dict() for e in self.evidence]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticFinding:
        return cls(
            finding_id=data["finding_id"],
            message=data["message"],
            epistemic_status=EpistemicStatus(data["epistemic_status"]),
            rationale=data.get("rationale", ""),
            evidence=tuple(Evidence.from_dict(e) for e in data.get("evidence", [])),
        )


@dataclass(frozen=True)
class EvidenceRequest:
    request_id: str
    subject: str
    question: str

    def to_dict(self) -> dict[str, Any]:
        return {"request_id": self.request_id, "subject": self.subject, "question": self.question}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceRequest:
        return cls(
            request_id=data["request_id"],
            subject=data["subject"],
            question=data["question"],
        )


@dataclass(frozen=True)
class ArchitectureReview:
    schema_version: int
    reviewer_type: str
    contract_digest: str
    survey_digest: str
    audit_digest: str
    reconciler_version: str
    adjudications: tuple[Adjudication, ...] = ()
    semantic_findings: tuple[SemanticFinding, ...] = ()
    evidence_requests: tuple[EvidenceRequest, ...] = ()
    rationale: str = ""
    # execution-only metadata
    run_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "reviewer_type": self.reviewer_type,
            "contract_digest": self.contract_digest,
            "survey_digest": self.survey_digest,
            "audit_digest": self.audit_digest,
            "reconciler_version": self.reconciler_version,
            "adjudications": [a.to_dict() for a in self.adjudications],
            "semantic_findings": [s.to_dict() for s in self.semantic_findings],
            "evidence_requests": [r.to_dict() for r in self.evidence_requests],
            "rationale": self.rationale,
            "run_metadata": dict(self.run_metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchitectureReview:
        return cls(
            schema_version=data["schema_version"],
            reviewer_type=data["reviewer_type"],
            contract_digest=data["contract_digest"],
            survey_digest=data["survey_digest"],
            audit_digest=data["audit_digest"],
            reconciler_version=data["reconciler_version"],
            adjudications=tuple(Adjudication.from_dict(a) for a in data.get("adjudications", [])),
            semantic_findings=tuple(
                SemanticFinding.from_dict(s) for s in data.get("semantic_findings", [])
            ),
            evidence_requests=tuple(
                EvidenceRequest.from_dict(r) for r in data.get("evidence_requests", [])
            ),
            rationale=data.get("rationale", ""),
            run_metadata=dict(data.get("run_metadata", {})),
        )

    def semantic_content(self) -> dict[str, Any]:
        """Semantic payload for review digest. Excludes run_metadata."""
        return {
            "schema_version": self.schema_version,
            "reviewer_type": self.reviewer_type,
            "contract_digest": self.contract_digest,
            "survey_digest": self.survey_digest,
            "audit_digest": self.audit_digest,
            "reconciler_version": self.reconciler_version,
            "adjudications": [a.to_dict() for a in self.adjudications],
            "semantic_findings": [s.to_dict() for s in self.semantic_findings],
            "evidence_requests": [r.to_dict() for r in self.evidence_requests],
            "rationale": self.rationale,
        }


# ---------------------------------------------------------------- view


@dataclass(frozen=True)
class ArchitectureReportView:
    schema_version: int
    audit_digest: str
    review_digest: str | None
    assessment: Assessment
    deterministic_findings: tuple[Finding, ...]
    review_adjudications: tuple[Adjudication, ...]
    semantic_findings: tuple[SemanticFinding, ...]
    evidence_requests: tuple[EvidenceRequest, ...]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "audit_digest": self.audit_digest,
            "review_digest": self.review_digest,
            "assessment": self.assessment.to_dict(),
            "deterministic_findings": [f.to_dict() for f in self.deterministic_findings],
            "review_adjudications": [a.to_dict() for a in self.review_adjudications],
            "semantic_findings": [s.to_dict() for s in self.semantic_findings],
            "evidence_requests": [r.to_dict() for r in self.evidence_requests],
        }
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchitectureReportView:
        return cls(
            schema_version=data["schema_version"],
            audit_digest=data["audit_digest"],
            review_digest=data.get("review_digest"),
            assessment=Assessment.from_dict(data["assessment"]),
            deterministic_findings=tuple(
                Finding.from_dict(f) for f in data["deterministic_findings"]
            ),
            review_adjudications=tuple(
                Adjudication.from_dict(a) for a in data["review_adjudications"]
            ),
            semantic_findings=tuple(
                SemanticFinding.from_dict(s) for s in data["semantic_findings"]
            ),
            evidence_requests=tuple(
                EvidenceRequest.from_dict(r) for r in data["evidence_requests"]
            ),
        )


# ---------------------------------------------------------------- validation


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArchitectureError(message)


def validate_contract(contract: ArchitectureContract) -> None:
    _require(
        contract.schema_version == SCHEMA_VERSION,
        f"unsupported contract schema_version: {contract.schema_version}",
    )
    rule_ids = [r.rule_id for r in contract.rules]
    _require(len(set(rule_ids)) == len(rule_ids), "duplicate rule_id in contract")
    unit_ids = [u.unit_id for u in contract.publication_units]
    _require(len(set(unit_ids)) == len(unit_ids), "duplicate publication unit_id in contract")
    for unit in contract.publication_units:
        _require(
            unit.asset_group in contract.asset_groups,
            f"unit {unit.unit_id} references unknown asset_group {unit.asset_group!r}",
        )
    exception_rule_ids = {e.rule_id for e in contract.exceptions}
    _require(exception_rule_ids <= set(rule_ids), "exception references unknown rule_id")
    for rule in contract.rules:
        if IntentMode.IMPLICIT in rule.accepted_intent_modes:
            raise ArchitectureError(f"rule {rule.rule_id}: IMPLICIT is never an accepted intent mode")
        if rule.lifecycle is LifecycleStatus.PLANNED and rule.effective_after is None and rule.known_gap is None:
            raise ArchitectureError(f"rule {rule.rule_id}: planned rule must declare effective_after or known_gap")
        if rule.kind is RuleKind.REMOTE_INTENT and not rule.accepted_intent_modes:
            raise ArchitectureError(f"rule {rule.rule_id}: REMOTE_INTENT requires accepted_intent_modes")


def validate_survey(survey: ArchitectureSurvey) -> None:
    _require(survey.schema_version == SCHEMA_VERSION, f"unsupported survey schema_version: {survey.schema_version}")
    extractors = [c.extractor for c in survey.coverage]
    _require(len(set(extractors)) == len(extractors), "duplicate coverage extractor in survey")
    _require(survey.source_digest.startswith("sha256:"), "survey source_digest must be sha256:<hex>")
    for fact in survey.facts:
        evidence = getattr(fact, "evidence", None)
        if evidence is not None and evidence.epistemic_status in (
            EpistemicStatus.INFERRED,
            EpistemicStatus.UNRESOLVED,
        ):
            raise ArchitectureError("survey facts cannot carry inferred/unresolved epistemic status")


def validate_review(review: ArchitectureReview) -> None:
    _require(review.schema_version == SCHEMA_VERSION, f"unsupported review schema_version: {review.schema_version}")
    for adjudication in review.adjudications:
        if adjudication.epistemic_status not in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED):
            raise ArchitectureError("review adjudication epistemic_status must be inferred or unresolved")
    for finding in review.semantic_findings:
        if finding.epistemic_status not in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED):
            raise ArchitectureError("review semantic finding epistemic_status must be inferred or unresolved")
