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

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

from paperforge.architecture_audit.canonical import semantic_digest

SCHEMA_VERSION = 1

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

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
    CANONICAL_READ = "canonical_read"
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
class AuthorityRole(str, Enum):
    EXECUTION = "execution"
    LIFECYCLE_STATE = "lifecycle_state"
    STOP = "stop"
    OBSERVER = "observer"
    ADAPTER = "adapter"
    DELEGATED_EXECUTOR = "delegated_executor"


class ArgumentRole(str, Enum):
    PATH = "path"
    ARGV = "argv"
    ENV = "env"
    OPERATION = "operation"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------- shared


class ArchitectureError(ValueError):
    """Invalid layer payload; raised at construction/load time."""


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_thaw(item) for item in value)
    return value


def _stable_evidence_id(file: str, symbol: str, line_start: int, line_end: int, extractor: str) -> str:
    payload = "\x1f".join((
        file.replace("\\", "/"),
        symbol,
        str(line_start),
        str(line_end),
        extractor,
    ))
    return "evidence:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Evidence:
    evidence_id: str = ""
    file: str = ""  # POSIX repository-relative path
    file_digest: str = ""  # "sha256:<hex>"
    symbol: str = ""
    line_start: int = 0
    line_end: int = 0
    extractor: str = ""
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED_STATIC
    confidence: Confidence = Confidence.MEDIUM

    def __post_init__(self) -> None:
        if not self.evidence_id:
            object.__setattr__(
                self,
                "evidence_id",
                _stable_evidence_id(
                    self.file,
                    self.symbol,
                    self.line_start,
                    self.line_end,
                    self.extractor,
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
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
            evidence_id=data.get("evidence_id", ""),
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
class ContractEntityMeta:
    lifecycle: LifecycleStatus = LifecycleStatus.ACTIVE
    enforcement: EnforcementMode | None = None
    effective_after: EffectiveAfter | None = None
    known_gap: KnownGap | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"lifecycle": self.lifecycle.value}
        if self.enforcement is not None:
            out["enforcement"] = self.enforcement.value
        if self.effective_after is not None:
            out["effective_after"] = self.effective_after.to_dict()
        if self.known_gap is not None:
            out["known_gap"] = self.known_gap.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ContractEntityMeta:
        data = data or {}
        return cls(
            lifecycle=LifecycleStatus(data.get("lifecycle", "active")),
            enforcement=EnforcementMode(data["enforcement"]) if data.get("enforcement") else None,
            effective_after=(
                EffectiveAfter.from_dict(data["effective_after"])
                if data.get("effective_after")
                else None
            ),
            known_gap=KnownGap.from_dict(data["known_gap"]) if data.get("known_gap") else None,
        )

    def is_default(self) -> bool:
        return (
            self.lifecycle is LifecycleStatus.ACTIVE
            and self.enforcement is None
            and self.effective_after is None
            and self.known_gap is None
        )


@dataclass(frozen=True)
class AssetGroupDecl:
    group_id: str
    meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)

    def to_dict(self) -> str | dict[str, Any]:
        if self.meta.is_default():
            return self.group_id
        return {"group_id": self.group_id, "meta": self.meta.to_dict()}

    @classmethod
    def from_dict(cls, data: str | dict[str, Any]) -> AssetGroupDecl:
        if isinstance(data, str):
            return cls(group_id=data)
        return cls(group_id=data["group_id"], meta=ContractEntityMeta.from_dict(data.get("meta")))


@dataclass(frozen=True)
class AuthorityRoleDecl:
    role: AuthorityRole
    authority_id: str
    observers: tuple[str, ...] = ()
    delegated_executors: tuple[str, ...] = ()
    meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "role": self.role.value,
            "authority_id": self.authority_id,
        }
        if self.observers:
            out["observers"] = list(self.observers)
        if self.delegated_executors:
            out["delegated_executors"] = list(self.delegated_executors)
        if not self.meta.is_default():
            out["meta"] = self.meta.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuthorityRoleDecl:
        return cls(
            role=AuthorityRole(data["role"]),
            authority_id=data["authority_id"],
            observers=tuple(data.get("observers", [])),
            delegated_executors=tuple(data.get("delegated_executors", [])),
            meta=ContractEntityMeta.from_dict(data.get("meta")),
        )


@dataclass(frozen=True)
class OperationDecl:
    operation_id: str
    meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)
    authorities: tuple[AuthorityRoleDecl, ...] = ()

    def to_dict(self) -> str | dict[str, Any]:
        if self.meta.is_default() and not self.authorities:
            return self.operation_id
        return {
            "operation_id": self.operation_id,
            "meta": self.meta.to_dict(),
            "authorities": [a.to_dict() for a in self.authorities],
        }

    @classmethod
    def from_dict(cls, data: str | dict[str, Any]) -> OperationDecl:
        if isinstance(data, str):
            return cls(operation_id=data)
        return cls(
            operation_id=data["operation_id"],
            meta=ContractEntityMeta.from_dict(data.get("meta")),
            authorities=tuple(AuthorityRoleDecl.from_dict(a) for a in data.get("authorities", [])),
        )


@dataclass(frozen=True)
class InterfaceDecl:
    interface_id: str
    provider: str
    consumer: str
    operation_id: str = ""
    meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "interface_id": self.interface_id,
            "provider": self.provider,
            "consumer": self.consumer,
        }
        if self.operation_id:
            out["operation_id"] = self.operation_id
        if not self.meta.is_default():
            out["meta"] = self.meta.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceDecl:
        return cls(
            interface_id=data["interface_id"],
            provider=data["provider"],
            consumer=data["consumer"],
            operation_id=data.get("operation_id", ""),
            meta=ContractEntityMeta.from_dict(data.get("meta")),
        )


@dataclass(frozen=True)
class TraceDecl:
    trace_id: str
    operation_id: str
    interface_id: str = ""
    trace_kind: str = "call"
    meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "trace_id": self.trace_id,
            "operation_id": self.operation_id,
            "trace_kind": self.trace_kind,
        }
        if self.interface_id:
            out["interface_id"] = self.interface_id
        if not self.meta.is_default():
            out["meta"] = self.meta.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceDecl:
        return cls(
            trace_id=data["trace_id"],
            operation_id=data["operation_id"],
            interface_id=data.get("interface_id", ""),
            trace_kind=data.get("trace_kind", "call"),
            meta=ContractEntityMeta.from_dict(data.get("meta")),
        )


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
    authority_role: str | None = None
    # kind-specific parameters
    allowed_query_effects: tuple[EffectKind, ...] = ()
    accepted_intent_modes: tuple[IntentMode, ...] = ()
    required_consumer_kinds: tuple[SignalConsumerKind, ...] = ()
    # NOTE (#149 authority): wrapper MEANING lives in the collector wrapper
    # registry; semantic exemptions live in first-class contract
    # operations/roles.  A rule NEVER carries a wrapper allowlist.

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rule_id": self.rule_id,
            "kind": self.kind.value,
            "subject": self.subject,
            "lifecycle": self.lifecycle.value,
            "enforcement": self.enforcement.value,
        }
        if self.scope and self.kind is not RuleKind.ROLE_AUTHORITY:
            out["scope"] = list(self.scope)
        if self.description:
            out["description"] = self.description
        if self.effective_after is not None:
            out["effective_after"] = self.effective_after.to_dict()
        if self.known_gap is not None:
            out["known_gap"] = self.known_gap.to_dict()
        if self.authority_role is not None:
            out["authority_role"] = self.authority_role
        if self.allowed_query_effects:
            out["allowed_query_effects"] = [e.value for e in self.allowed_query_effects]
        if self.accepted_intent_modes:
            out["accepted_intent_modes"] = [m.value for m in self.accepted_intent_modes]
        if self.required_consumer_kinds:
            out["required_consumer_kinds"] = [k.value for k in self.required_consumer_kinds]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        kind = RuleKind(data["kind"])
        scope = tuple(data.get("scope", []))
        authority_role = data.get("authority_role")
        if kind is RuleKind.ROLE_AUTHORITY:
            if len(scope) > 1:
                raise ArchitectureError("ROLE_AUTHORITY scope may contain only one legacy role selector")
            if authority_role is not None and scope and scope[0] != authority_role:
                raise ArchitectureError("ROLE_AUTHORITY scope and authority_role disagree")
            authority_role = authority_role or (scope[0] if scope else None)
            scope = ()
        return cls(
            rule_id=data["rule_id"],
            kind=kind,
            subject=data["subject"],
            scope=scope,
            description=data.get("description", ""),
            lifecycle=LifecycleStatus(data.get("lifecycle", "active")),
            enforcement=EnforcementMode(data.get("enforcement", "blocking")),
            effective_after=(
                EffectiveAfter.from_dict(data["effective_after"]) if data.get("effective_after") else None
            ),
            known_gap=KnownGap.from_dict(data["known_gap"]) if data.get("known_gap") else None,
            authority_role=authority_role,
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
    meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)
    authority_meta: ContractEntityMeta = field(default_factory=ContractEntityMeta)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "unit_id": self.unit_id,
            "asset_group": self.asset_group,
            "publication_authority": self.publication_authority,
        }
        if self.authorized_writers:
            out["authorized_writers"] = list(self.authorized_writers)
        if not self.meta.is_default():
            out["meta"] = self.meta.to_dict()
        if not self.authority_meta.is_default():
            out["authority_meta"] = self.authority_meta.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PublicationUnitDecl:
        return cls(
            unit_id=data["unit_id"],
            asset_group=data["asset_group"],
            publication_authority=data["publication_authority"],
            authorized_writers=tuple(data.get("authorized_writers", [])),
            meta=ContractEntityMeta.from_dict(data.get("meta")),
            authority_meta=ContractEntityMeta.from_dict(data.get("authority_meta")),
        )


@dataclass(frozen=True)
class ArchitectureContract:
    schema_version: int
    asset_groups: tuple[AssetGroupDecl, ...]
    publication_units: tuple[PublicationUnitDecl, ...]
    operations: tuple[OperationDecl, ...]
    rules: tuple[Rule, ...]
    exceptions: tuple[ExceptionDecl, ...] = ()
    required_extractors: tuple[str, ...] = ()
    interfaces: tuple[InterfaceDecl, ...] = ()
    traces: tuple[TraceDecl, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "asset_groups": [g.to_dict() for g in self.asset_groups],
            "publication_units": [u.to_dict() for u in self.publication_units],
            "operations": [o.to_dict() for o in self.operations],
            "rules": [r.to_dict() for r in self.rules],
            "exceptions": [e.to_dict() for e in self.exceptions],
        }
        if self.required_extractors:
            out["required_extractors"] = list(self.required_extractors)
        if self.interfaces:
            out["interfaces"] = [i.to_dict() for i in self.interfaces]
        if self.traces:
            out["traces"] = [t.to_dict() for t in self.traces]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchitectureContract:
        return cls(
            schema_version=data["schema_version"],
            asset_groups=tuple(AssetGroupDecl.from_dict(g) for g in data["asset_groups"]),
            publication_units=tuple(
                PublicationUnitDecl.from_dict(u) for u in data.get("publication_units", [])
            ),
            operations=tuple(OperationDecl.from_dict(o) for o in data.get("operations", [])),
            rules=tuple(Rule.from_dict(r) for r in data["rules"]),
            exceptions=tuple(ExceptionDecl.from_dict(e) for e in data.get("exceptions", [])),
            required_extractors=tuple(data.get("required_extractors", [])),
            interfaces=tuple(InterfaceDecl.from_dict(i) for i in data.get("interfaces", [])),
            traces=tuple(TraceDecl.from_dict(t) for t in data.get("traces", [])),
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
    consumer: str | None = None
    evidence: Evidence | None = None
    consumer_evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "signal",
            "signal_id": self.signal_id,
            "producer": self.producer,
            "consumer_kind": self.consumer_kind.value,
            "has_code_consumer": self.has_code_consumer,
        }
        if self.consumer is not None:
            out["consumer"] = self.consumer
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        if self.consumer_evidence:
            out["consumer_evidence"] = [e.to_dict() for e in self.consumer_evidence]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalFact:
        return cls(
            signal_id=data["signal_id"],
            producer=data["producer"],
            consumer_kind=SignalConsumerKind(data["consumer_kind"]),
            has_code_consumer=data.get("has_code_consumer", False),
            consumer=data.get("consumer"),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
            consumer_evidence=tuple(
                Evidence.from_dict(e) for e in data.get("consumer_evidence", [])
            ),
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
class FilesystemReadFact:
    """#149 frozen shape — the only new fact for CANONICAL_READ.

    Wrapper attribution is COLLECTOR knowledge: a read that went through a
    registered wrapper carries its wrapper_id; a bare/direct read leaves it
    None and is a determinate violation.  No rule-level wrapper allowlist.
    """
    operation_id: str
    unit_id: str
    wrapper_id: str | None = None
    path_expression: str = ""
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "filesystem_read",
            "operation_id": self.operation_id,
            "unit_id": self.unit_id,
        }
        if self.wrapper_id is not None:
            out["wrapper_id"] = self.wrapper_id
        if self.path_expression:
            out["path_expression"] = self.path_expression
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilesystemReadFact:
        return cls(
            operation_id=data["operation_id"],
            unit_id=data["unit_id"],
            wrapper_id=data.get("wrapper_id"),
            path_expression=data.get("path_expression", ""),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class CanonicalWriteFact:
    unit_id: str
    actor_kind: str  # "ui" | "backend" | "worker" | "cli" | ...
    via_publication_protocol: bool
    writer_id: str | None = None
    publication_authority: str | None = None
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "canonical_write",
            "unit_id": self.unit_id,
            "actor_kind": self.actor_kind,
            "via_publication_protocol": self.via_publication_protocol,
        }
        if self.writer_id is not None:
            out["writer_id"] = self.writer_id
        if self.publication_authority is not None:
            out["publication_authority"] = self.publication_authority
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CanonicalWriteFact:
        return cls(
            unit_id=data["unit_id"],
            actor_kind=data["actor_kind"],
            via_publication_protocol=data.get("via_publication_protocol", False),
            writer_id=data.get("writer_id"),
            publication_authority=data.get("publication_authority"),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )

@dataclass(frozen=True)
class UnresolvedFact:
    unresolved_id: str
    expression: str
    reason: str
    possible_effects: tuple[EffectKind, ...]
    evidence: Evidence
    epistemic_status: EpistemicStatus = EpistemicStatus.UNRESOLVED

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "unresolved",
            "unresolved_id": self.unresolved_id,
            "expression": self.expression,
            "reason": self.reason,
            "possible_effects": [e.value for e in self.possible_effects],
            "evidence": self.evidence.to_dict(),
            "epistemic_status": self.epistemic_status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnresolvedFact:
        return cls(
            unresolved_id=data["unresolved_id"],
            expression=data["expression"],
            reason=data["reason"],
            possible_effects=tuple(EffectKind(e) for e in data.get("possible_effects", [])),
            evidence=Evidence.from_dict(data["evidence"]),
            epistemic_status=EpistemicStatus(data.get("epistemic_status", "unresolved")),
        )


@dataclass(frozen=True)
class CandidateFact:
    candidate_id: str
    fact_kind: str
    summary: str
    evidence: Evidence | None = None
    epistemic_status: EpistemicStatus = EpistemicStatus.UNRESOLVED

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "candidate",
            "candidate_id": self.candidate_id,
            "fact_kind": self.fact_kind,
            "summary": self.summary,
            "epistemic_status": self.epistemic_status.value,
        }
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CandidateFact:
        return cls(
            candidate_id=data["candidate_id"],
            fact_kind=data["fact_kind"],
            summary=data["summary"],
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
            epistemic_status=EpistemicStatus(data.get("epistemic_status", "unresolved")),
        )


@dataclass(frozen=True)
class InterfaceFact:
    interface_id: str
    provider: str
    consumer: str
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "interface",
            "interface_id": self.interface_id,
            "provider": self.provider,
            "consumer": self.consumer,
        }
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceFact:
        return cls(
            interface_id=data["interface_id"],
            provider=data["provider"],
            consumer=data["consumer"],
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class TraceFact:
    trace_id: str
    operation_id: str
    interface_id: str = ""
    trace_kind: str = "call"
    evidence: Evidence | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": "trace",
            "trace_id": self.trace_id,
            "operation_id": self.operation_id,
            "trace_kind": self.trace_kind,
        }
        if self.interface_id:
            out["interface_id"] = self.interface_id
        if self.evidence is not None:
            out["evidence"] = self.evidence.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceFact:
        return cls(
            trace_id=data["trace_id"],
            operation_id=data["operation_id"],
            interface_id=data.get("interface_id", ""),
            trace_kind=data.get("trace_kind", "call"),
            evidence=Evidence.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass(frozen=True)
class WrapperSummary:
    wrapper_id: str
    qualified_symbol: str
    effect_kinds: tuple[EffectKind, ...]
    argument_roles: tuple[ArgumentRole, ...]
    confidence: Confidence
    evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "wrapper_id": self.wrapper_id,
            "qualified_symbol": self.qualified_symbol,
            "effect_kinds": [e.value for e in self.effect_kinds],
            "argument_roles": [r.value for r in self.argument_roles],
            "confidence": self.confidence.value,
        }
        if self.evidence:
            out["evidence"] = [e.to_dict() for e in self.evidence]
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WrapperSummary:
        return cls(
            wrapper_id=data["wrapper_id"],
            qualified_symbol=data["qualified_symbol"],
            effect_kinds=tuple(EffectKind(e) for e in data.get("effect_kinds", [])),
            argument_roles=tuple(ArgumentRole(r) for r in data.get("argument_roles", [])),
            confidence=Confidence(data["confidence"]),
            evidence=tuple(Evidence.from_dict(e) for e in data.get("evidence", [])),
        )


FACT_KINDS = {
    "effect": EffectFact,
    "signal": SignalFact,
    "unit_authority": UnitAuthorityFact,
    "role_authority": RoleAuthorityFact,
    "canonical_write": CanonicalWriteFact,
    "unresolved": UnresolvedFact,
    "filesystem_read": FilesystemReadFact,
    "candidate": CandidateFact,
    "interface": InterfaceFact,
    "trace": TraceFact,
}

SurveyFact = (
    EffectFact
    | SignalFact
    | UnitAuthorityFact
    | RoleAuthorityFact
    | CanonicalWriteFact
    | UnresolvedFact
    | CandidateFact
    | InterfaceFact
    | TraceFact
)


def fact_from_dict(data: dict[str, Any]) -> SurveyFact:
    kind = data.get("kind")
    if not isinstance(kind, str):
        raise ArchitectureError(f"survey fact missing string kind: {kind!r}")
    factory = FACT_KINDS.get(kind)
    if factory is None:
        raise ArchitectureError(f"unknown survey fact kind: {kind!r}")
    return factory.from_dict(data)


@dataclass(frozen=True)
class RepositoryState:
    """Reproducibility state of the surveyed tree (semantic — part of the
    survey digest). Dirty state affects gate eligibility, so it must be bound
    into the deterministic chain, never left in run_metadata only."""

    revision: str = ""
    dirty: bool = False
    dirty_diff_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"revision": self.revision, "dirty": self.dirty}
        if self.dirty_diff_digest:
            out["dirty_diff_digest"] = self.dirty_diff_digest
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> RepositoryState:
        if not data:
            return cls()
        return cls(
            revision=str(data.get("revision", "")),
            dirty=bool(data.get("dirty", False)),
            dirty_diff_digest=str(data.get("dirty_diff_digest", "")),
        )


    def is_default(self) -> bool:
        return not self.dirty and not self.revision and not self.dirty_diff_digest


@dataclass(frozen=True)
class ArchitectureSurvey:
    schema_version: int
    scope: str
    coverage: tuple[CoverageEntry, ...]
    facts: tuple[SurveyFact, ...]
    source_digest: str  # sha256 over normalized observed source (semantic)
    parse_errors: tuple[str, ...] = ()
    excluded_roots: tuple[str, ...] = ()
    wrapper_summaries: tuple[WrapperSummary, ...] = ()
    # reproducibility state (semantic — binds dirty into the digest chain)
    repository_state: RepositoryState = field(default_factory=RepositoryState)
    # execution-only metadata (never part of semantic digest)
    run_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_metadata", _freeze(self.run_metadata))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "scope": self.scope,
            "coverage": [c.to_dict() for c in self.coverage],
            "facts": [f.to_dict() for f in self.facts],
            "source_digest": self.source_digest,
            "parse_errors": list(self.parse_errors),
            "excluded_roots": list(self.excluded_roots),
            "run_metadata": _thaw(self.run_metadata),
        }
        if self.wrapper_summaries:
            out["wrapper_summaries"] = [w.to_dict() for w in self.wrapper_summaries]
        if not self.repository_state.is_default():
            out["repository_state"] = self.repository_state.to_dict()
        return out

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
            wrapper_summaries=tuple(
                WrapperSummary.from_dict(w) for w in data.get("wrapper_summaries", [])
            ),
            repository_state=RepositoryState.from_dict(data.get("repository_state")),
            run_metadata=dict(data.get("run_metadata", {})),
        )

    def semantic_content(self) -> dict[str, Any]:
        """Semantic payload: coverage, facts, source identity, repo state.
        Excludes run_metadata."""
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "scope": self.scope,
            "coverage": [c.to_dict() for c in self.coverage],
            "facts": [f.to_dict() for f in self.facts],
            "source_digest": self.source_digest,
            "parse_errors": list(self.parse_errors),
            "excluded_roots": list(self.excluded_roots),
        }
        if self.wrapper_summaries:
            out["wrapper_summaries"] = [w.to_dict() for w in self.wrapper_summaries]
        if not self.repository_state.is_default():
            out["repository_state"] = self.repository_state.to_dict()
        return out


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
    run_metadata: Mapping[str, Any]
    semantic_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_metadata", _freeze(self.run_metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "content": self.content.to_dict(),
            "run_metadata": _thaw(self.run_metadata),
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


@dataclass(frozen=True)
class Adjudication:
    finding_id: str
    adjudication: AdjudicationKind
    rationale: str
    epistemic_status: EpistemicStatus  # inferred | unresolved only
    reviewer: str = ""
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "finding_id": self.finding_id,
            "adjudication": self.adjudication.value,
            "rationale": self.rationale,
            "epistemic_status": self.epistemic_status.value,
        }
        if self.reviewer:
            out["reviewer"] = self.reviewer
        if self.evidence_ids:
            out["evidence_ids"] = list(self.evidence_ids)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Adjudication:
        return cls(
            finding_id=data["finding_id"],
            adjudication=AdjudicationKind(data["adjudication"]),
            rationale=data["rationale"],
            epistemic_status=EpistemicStatus(data["epistemic_status"]),
            reviewer=data.get("reviewer", ""),
            evidence_ids=tuple(data.get("evidence_ids", [])),
        )


@dataclass(frozen=True)
class SemanticFinding:
    finding_id: str
    message: str
    epistemic_status: EpistemicStatus
    rationale: str = ""
    evidence: tuple[Evidence, ...] = ()
    evidence_ids: tuple[str, ...] = ()

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
        if self.evidence_ids:
            out["evidence_ids"] = list(self.evidence_ids)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticFinding:
        return cls(
            finding_id=data["finding_id"],
            message=data["message"],
            epistemic_status=EpistemicStatus(data["epistemic_status"]),
            rationale=data.get("rationale", ""),
            evidence=tuple(Evidence.from_dict(e) for e in data.get("evidence", [])),
            evidence_ids=tuple(data.get("evidence_ids", [])),
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
    run_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_metadata", _freeze(self.run_metadata))

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
            "run_metadata": _thaw(self.run_metadata),
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


def _review_projection_digest(
    adjudications: tuple[Adjudication, ...],
    semantic_findings: tuple[SemanticFinding, ...],
    evidence_requests: tuple[EvidenceRequest, ...],
) -> str:
    """Digest the review fields projected into a report view."""
    return semantic_digest(
        {
            "review_adjudications": [a.to_dict() for a in adjudications],
            "semantic_findings": [f.to_dict() for f in semantic_findings],
            "evidence_requests": [r.to_dict() for r in evidence_requests],
        }
    )


# ---------------------------------------------------------------- validation


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArchitectureError(message)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _validate_meta(meta: ContractEntityMeta, label: str) -> None:
    _require(isinstance(meta.lifecycle, LifecycleStatus), f"{label}: invalid lifecycle")
    _require(
        meta.enforcement is None or isinstance(meta.enforcement, EnforcementMode),
        f"{label}: invalid enforcement",
    )
    if meta.lifecycle is LifecycleStatus.PLANNED and meta.effective_after is None and meta.known_gap is None:
        raise ArchitectureError(f"{label}: planned entity must declare effective_after or known_gap")
    if meta.known_gap is not None and not meta.known_gap.rationale.strip():
        raise ArchitectureError(f"{label}: known_gap rationale must not be empty")


def _validate_evidence(evidence: Evidence, *, review: bool = False) -> None:
    expected_id = _stable_evidence_id(
        evidence.file,
        evidence.symbol,
        evidence.line_start,
        evidence.line_end,
        evidence.extractor,
    )
    _require(evidence.evidence_id == expected_id, f"evidence_id does not match evidence identity: {evidence.file}")
    _require(bool(evidence.file), "evidence file must not be empty")
    _require(not evidence.file.startswith(("/", "\\")), f"evidence file must be relative: {evidence.file!r}")
    _require("\\" not in evidence.file, f"evidence file must use POSIX separators: {evidence.file!r}")
    _require(".." not in evidence.file.split("/"), f"evidence file escapes repository: {evidence.file!r}")
    _require(_is_sha256(evidence.file_digest), "evidence file_digest must match sha256:<64 lowercase hex>")
    _require(bool(evidence.symbol), "evidence symbol must not be empty")
    _require(evidence.line_start > 0 and evidence.line_end >= evidence.line_start, "invalid evidence line range")
    _require(bool(evidence.extractor), "evidence extractor must not be empty")
    allowed = (
        (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED)
        if review
        else (EpistemicStatus.OBSERVED_STATIC, EpistemicStatus.OBSERVED_RUNTIME)
    )
    _require(evidence.epistemic_status in allowed, "evidence epistemic status is invalid for this layer")


def _evidence_values(value: Any) -> list[Evidence]:
    result: list[Evidence] = []
    for name in ("evidence", "consumer_evidence"):
        item = getattr(value, name, None)
        if isinstance(item, Evidence):
            result.append(item)
        elif isinstance(item, tuple):
            result.extend(e for e in item if isinstance(e, Evidence))
    return result

def _rule_entity_metas(rule: Rule, contract: ArchitectureContract) -> tuple[ContractEntityMeta, ...]:
    unit_rule_kinds = {
        RuleKind.PUBLICATION_AUTHORITY,
        RuleKind.CANONICAL_WRITER,
        RuleKind.PUBLICATION_MARKER,
    }
    operation_rule_kinds = {
        RuleKind.QUERY_SIDE_EFFECT,
        RuleKind.REMOTE_INTENT,
        RuleKind.ROLE_AUTHORITY,
    }
    if rule.kind in unit_rule_kinds:
        unit = next((unit for unit in contract.publication_units if unit.unit_id == rule.subject), None)
        if unit is None:
            return ()
        metas = [unit.meta]
        if rule.kind is RuleKind.PUBLICATION_AUTHORITY:
            metas.append(unit.authority_meta)
        return tuple(metas)
    if rule.kind not in operation_rule_kinds:
        return ()
    operation = next((item for item in contract.operations if item.operation_id == rule.subject), None)
    if operation is None:
        return ()
    metas = [operation.meta]
    if rule.kind is RuleKind.ROLE_AUTHORITY and rule.authority_role:
        for authority in operation.authorities:
            matches_role = authority.role.value == rule.authority_role
            matches_observer = (
                rule.authority_role == AuthorityRole.OBSERVER.value
                and bool(authority.observers)
            )
            matches_delegate = (
                rule.authority_role == AuthorityRole.DELEGATED_EXECUTOR.value
                and bool(authority.delegated_executors)
            )
            if matches_role or matches_observer or matches_delegate:
                metas.append(authority.meta)
    return tuple(metas)


def _validate_rule_entity_lifecycle(rule: Rule, contract: ArchitectureContract) -> None:
    for meta in _rule_entity_metas(rule, contract):
        if meta.lifecycle is LifecycleStatus.PLANNED:
            _require(
                rule.lifecycle is LifecycleStatus.PLANNED,
                f"rule {rule.rule_id} must be planned when its subject entity is planned",
            )
        elif meta.lifecycle is LifecycleStatus.DEPRECATED:
            _require(
                rule.lifecycle is not LifecycleStatus.ACTIVE,
                f"rule {rule.rule_id} cannot be active when its subject entity is deprecated",
            )


def _validate_rule_subject(rule: Rule, contract: ArchitectureContract) -> None:
    unit_rule_kinds = {
        RuleKind.PUBLICATION_AUTHORITY,
        RuleKind.CANONICAL_WRITER,
        RuleKind.PUBLICATION_MARKER,
    }
    operation_rule_kinds = {
        RuleKind.QUERY_SIDE_EFFECT,
        RuleKind.REMOTE_INTENT,
        RuleKind.ROLE_AUTHORITY,
    }
    if rule.kind is RuleKind.COVERAGE_COMPLETE:
        return
    _require(bool(rule.subject), f"rule {rule.rule_id} must declare a subject")
    if rule.kind in unit_rule_kinds:
        declared = {unit.unit_id for unit in contract.publication_units}
        _require(
            rule.subject in declared,
            f"rule {rule.rule_id} references unknown publication unit {rule.subject!r}",
        )
    elif rule.kind in operation_rule_kinds:
        declared = {operation.operation_id for operation in contract.operations}
        _require(
            rule.subject in declared,
            f"rule {rule.rule_id} references unknown operation {rule.subject!r}",
        )


def validate_contract(contract: ArchitectureContract) -> None:
    _require(
        contract.schema_version == SCHEMA_VERSION,
        f"unsupported contract schema_version: {contract.schema_version}",
    )
    group_ids = [g.group_id for g in contract.asset_groups]
    _require(all(group_ids), "asset group ids must not be empty")
    _require(len(set(group_ids)) == len(group_ids), "duplicate asset_group id in contract")
    for group in contract.asset_groups:
        _validate_meta(group.meta, f"asset group {group.group_id}")

    unit_ids = [u.unit_id for u in contract.publication_units]
    _require(len(set(unit_ids)) == len(unit_ids), "duplicate publication unit_id in contract")
    for unit in contract.publication_units:
        _require(
            unit.asset_group in set(group_ids),
            f"unit {unit.unit_id} references unknown asset_group {unit.asset_group!r}",
        )
        _require(unit.publication_authority, f"unit {unit.unit_id} must declare one publication authority")
        _require(
            len(set(unit.authorized_writers)) == len(unit.authorized_writers),
            f"unit {unit.unit_id} has duplicate authorized writer",
        )
        _validate_meta(unit.meta, f"publication unit {unit.unit_id}")
        _validate_meta(unit.authority_meta, f"publication authority {unit.publication_authority}")

    operation_ids = [o.operation_id for o in contract.operations]
    _require(all(operation_ids), "operation ids must not be empty")
    _require(len(set(operation_ids)) == len(operation_ids), "duplicate operation_id in contract")
    operation_id_set = set(operation_ids)
    for operation in contract.operations:
        _validate_meta(operation.meta, f"operation {operation.operation_id}")
        roles = [authority.role for authority in operation.authorities]
        _require(len(set(roles)) == len(roles), f"operation {operation.operation_id} has duplicate authority role")
        for authority in operation.authorities:
            _require(authority.authority_id, f"operation {operation.operation_id} authority id must not be empty")
            _require(
                len(set(authority.observers)) == len(authority.observers),
                f"operation {operation.operation_id} has duplicate observer",
            )
            _require(
                len(set(authority.delegated_executors)) == len(authority.delegated_executors),
                f"operation {operation.operation_id} has duplicate delegated executor",
            )
            _validate_meta(authority.meta, f"authority {authority.authority_id}")

    interface_ids = [interface.interface_id for interface in contract.interfaces]
    _require(len(set(interface_ids)) == len(interface_ids), "duplicate interface_id in contract")
    for interface in contract.interfaces:
        _require(
            interface.interface_id and interface.provider and interface.consumer,
            "interface identity is incomplete",
        )
        _validate_meta(interface.meta, f"interface {interface.interface_id}")
        _require(
            not interface.operation_id or interface.operation_id in operation_id_set,
            f"interface {interface.interface_id} references unknown operation",
        )

    trace_ids = [trace.trace_id for trace in contract.traces]
    _require(len(set(trace_ids)) == len(trace_ids), "duplicate trace_id in contract")
    interface_id_set = set(interface_ids)
    for trace in contract.traces:
        _require(trace.trace_id and trace.operation_id, "trace identity is incomplete")
        _require(
            trace.operation_id in operation_id_set,
            f"trace {trace.trace_id} references unknown operation",
        )
        _validate_meta(trace.meta, f"trace {trace.trace_id}")
        _require(
            not trace.interface_id or trace.interface_id in interface_id_set,
            f"trace {trace.trace_id} references unknown interface",
        )

    rule_ids = [r.rule_id for r in contract.rules]
    _require(len(set(rule_ids)) == len(rule_ids), "duplicate rule_id in contract")
    for rule in contract.rules:
        _require(isinstance(rule.kind, RuleKind), f"rule {rule.rule_id}: invalid rule kind")
        _require(isinstance(rule.lifecycle, LifecycleStatus), f"rule {rule.rule_id}: invalid lifecycle")
        _require(isinstance(rule.enforcement, EnforcementMode), f"rule {rule.rule_id}: invalid enforcement")
        _require(
            all(isinstance(effect, EffectKind) for effect in rule.allowed_query_effects),
            f"rule {rule.rule_id}: invalid allowed query effect",
        )
        _require(
            all(isinstance(mode, IntentMode) for mode in rule.accepted_intent_modes),
            f"rule {rule.rule_id}: invalid accepted intent mode",
        )
        _require(
            all(isinstance(kind, SignalConsumerKind) for kind in rule.required_consumer_kinds),
            f"rule {rule.rule_id}: invalid required consumer kind",
        )
        _validate_rule_subject(rule, contract)
        if IntentMode.IMPLICIT in rule.accepted_intent_modes:
            raise ArchitectureError(f"rule {rule.rule_id}: IMPLICIT is never an accepted intent mode")
        if rule.lifecycle is LifecycleStatus.PLANNED and rule.effective_after is None and rule.known_gap is None:
            raise ArchitectureError(f"rule {rule.rule_id}: planned rule must declare effective_after or known_gap")
        if rule.known_gap is not None and not rule.known_gap.rationale.strip():
            raise ArchitectureError(f"rule {rule.rule_id}: known_gap rationale must not be empty")
        if rule.kind is RuleKind.REMOTE_INTENT and not rule.accepted_intent_modes:
            raise ArchitectureError(f"rule {rule.rule_id}: REMOTE_INTENT requires accepted_intent_modes")
        if rule.kind is RuleKind.ROLE_AUTHORITY:
            _require(rule.authority_role is not None, f"rule {rule.rule_id}: ROLE_AUTHORITY requires authority_role")
            if rule.scope:
                _require(
                    len(rule.scope) == 1 and rule.scope[0] == rule.authority_role,
                    f"rule {rule.rule_id}: scope and authority_role disagree",
                )
            try:
                AuthorityRole(rule.authority_role)
            except ValueError as exc:
                raise ArchitectureError(
                    f"rule {rule.rule_id}: unknown authority role {rule.authority_role!r}"
                ) from exc
        _validate_rule_entity_lifecycle(rule, contract)

    exception_ids = [e.exception_id for e in contract.exceptions]
    _require(len(set(exception_ids)) == len(exception_ids), "duplicate exception_id in contract")
    exception_keys = [(e.rule_id, e.subject) for e in contract.exceptions]
    _require(len(set(exception_keys)) == len(exception_keys), "duplicate rule/subject exception in contract")
    _require(
        {e.rule_id for e in contract.exceptions} <= set(rule_ids),
        "exception references unknown rule_id",
    )
    for exception in contract.exceptions:
        _require(exception.rationale.strip(), f"exception {exception.exception_id} requires rationale")
        _require(exception.review_condition.strip(), f"exception {exception.exception_id} requires review_condition")

    _require(
        len(set(contract.required_extractors)) == len(contract.required_extractors),
        "duplicate required extractor in contract",
    )


def validate_survey(survey: ArchitectureSurvey) -> None:
    _require(survey.schema_version == SCHEMA_VERSION, f"unsupported survey schema_version: {survey.schema_version}")
    extractors = [c.extractor for c in survey.coverage]
    _require(all(extractors), "coverage extractor must not be empty")
    _require(len(set(extractors)) == len(extractors), "duplicate coverage extractor in survey")
    _require(_is_sha256(survey.source_digest), "survey source_digest must match sha256:<64 lowercase hex>")
    for fact in survey.facts:
        if isinstance(fact, SignalFact) and fact.consumer_kind is SignalConsumerKind.CODE:
            has_auditable_consumer = bool(fact.consumer and fact.consumer_evidence)
            _require(
                fact.has_code_consumer == has_auditable_consumer,
                "code signal consumer requires matching consumer identity and evidence",
            )
        if isinstance(fact, RoleAuthorityFact):
            try:
                AuthorityRole(fact.role)
            except ValueError as exc:
                raise ArchitectureError(f"unknown authority role in survey: {fact.role!r}") from exc
        if isinstance(fact, UnresolvedFact):
            _require(fact.epistemic_status is EpistemicStatus.UNRESOLVED, "unresolved fact must be unresolved")
        if isinstance(fact, CandidateFact):
            _require(
                fact.epistemic_status in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED),
                "candidate fact must be inferred or unresolved",
            )
        for evidence in _evidence_values(fact):
            _validate_evidence(evidence)


    wrapper_ids = [wrapper.wrapper_id for wrapper in survey.wrapper_summaries]
    _require(all(wrapper_ids), "wrapper summary ids must not be empty")
    _require(len(set(wrapper_ids)) == len(wrapper_ids), "duplicate wrapper_id in survey")
    for wrapper in survey.wrapper_summaries:
        _require(wrapper.qualified_symbol, f"wrapper {wrapper.wrapper_id} qualified symbol must not be empty")
        for evidence in wrapper.evidence:
            _validate_evidence(evidence)

def validate_audit(audit: DeterministicAudit) -> None:
    from paperforge.architecture_audit.canonical import semantic_digest

    _require(audit.schema_version == SCHEMA_VERSION, f"unsupported audit schema_version: {audit.schema_version}")
    content = audit.content
    _require(content.reconciler_version, "audit reconciler_version must not be empty")
    _require(_is_sha256(content.bound_contract_digest), "audit contract digest must match sha256:<64 lowercase hex>")
    _require(_is_sha256(content.bound_survey_digest), "audit survey digest must match sha256:<64 lowercase hex>")
    _require(
        audit.semantic_digest == semantic_digest(content.to_dict()),
        "audit semantic_digest does not match content",
    )
    coverage_extractors = [c.extractor for c in content.coverage]
    _require(len(set(coverage_extractors)) == len(coverage_extractors), "duplicate audit coverage extractor")
    rule_ids = [row.rule_id for row in content.rule_coverage]
    _require(len(set(rule_ids)) == len(rule_ids), "duplicate audit rule coverage")
    finding_ids = [finding.finding_id for finding in content.findings]
    _require(len(set(finding_ids)) == len(finding_ids), "duplicate audit finding_id")
    for row in content.rule_coverage:
        _require(row.evaluated == (row.status is not None), f"rule coverage evaluation mismatch: {row.rule_id}")
    for finding in content.findings:
        _require(finding.rule_status is not RuleStatus.SATISFIED, "satisfied rule cannot be an audit finding")
        for evidence in finding.evidence:
            _validate_evidence(evidence)
    if content.assessment.status in (AssessmentStatus.FAILED, AssessmentStatus.INCOMPLETE):
        _require(not content.assessment.gate_eligible, "failed/incomplete audit cannot be gate eligible")
    if content.assessment.status is AssessmentStatus.CLEAN:
        _require(not content.findings, "clean audit cannot contain findings")


def validate_review(review: ArchitectureReview, audit: DeterministicAudit | None = None) -> None:
    _require(review.schema_version == SCHEMA_VERSION, f"unsupported review schema_version: {review.schema_version}")
    for name, value in (
        ("contract_digest", review.contract_digest),
        ("survey_digest", review.survey_digest),
        ("audit_digest", review.audit_digest),
    ):
        _require(_is_sha256(value), f"audit {name} must match sha256:<64 lowercase hex>")
    deterministic_ids: set[str] = set()
    evidence_ids: set[str] = set()
    if audit is not None:
        validate_audit(audit)
        deterministic_ids = {finding.finding_id for finding in audit.content.findings}
        evidence_ids = {
            evidence.evidence_id
            for finding in audit.content.findings
            for evidence in finding.evidence
        }
    adjudication_ids = [a.finding_id for a in review.adjudications]
    _require(len(set(adjudication_ids)) == len(adjudication_ids), "duplicate adjudication for finding")
    for adjudication in review.adjudications:
        _require(
            adjudication.epistemic_status in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED),
            "review adjudication epistemic_status must be inferred or unresolved",
        )
        _require(adjudication.rationale.strip(), "review adjudication rationale must not be empty")
        if audit is not None:
            _require(
                adjudication.finding_id in deterministic_ids,
                f"review references unknown finding_id {adjudication.finding_id!r}",
            )
            _require(
                set(adjudication.evidence_ids) <= evidence_ids,
                f"review references unknown evidence_id for {adjudication.finding_id!r}",
            )
    semantic_ids = [finding.finding_id for finding in review.semantic_findings]
    _require(len(set(semantic_ids)) == len(semantic_ids), "duplicate review semantic finding_id")
    for finding in review.semantic_findings:
        _require(
            finding.epistemic_status in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED),
            "review semantic finding epistemic_status must be inferred or unresolved",
        )
        _require(
            finding.finding_id not in deterministic_ids,
            f"review semantic finding collides with deterministic finding_id {finding.finding_id!r}",
        )
        if audit is not None:
            _require(
                set(finding.evidence_ids) <= evidence_ids,
                f"review references unknown evidence_id {finding.finding_id!r}",
            )
        for evidence in finding.evidence:
            _validate_evidence(evidence, review=True)
    request_ids = [request.request_id for request in review.evidence_requests]
    _require(len(set(request_ids)) == len(request_ids), "duplicate review evidence request_id")


def validate_report_view(view: ArchitectureReportView, audit: DeterministicAudit | None = None) -> None:
    _require(view.schema_version == SCHEMA_VERSION, f"unsupported report view schema_version: {view.schema_version}")
    _require(_is_sha256(view.audit_digest), "report view audit digest must match sha256:<64 lowercase hex>")
    has_review_payload = bool(
        view.review_adjudications or view.semantic_findings or view.evidence_requests
    )
    _require(
        (view.review_digest is not None) == has_review_payload,
        "report view review digest/payload presence mismatch",
    )
    if view.review_digest is not None:
        _require(_is_sha256(view.review_digest), "report view review digest must match sha256:<64 lowercase hex>")
        _require(
            view.review_digest
            == _review_projection_digest(
                view.review_adjudications,
                view.semantic_findings,
                view.evidence_requests,
            ),
            "report view review digest differs from projected review fields",
        )
    finding_ids = [finding.finding_id for finding in view.deterministic_findings]
    _require(len(set(finding_ids)) == len(finding_ids), "duplicate report view finding_id")
    adjudication_ids = [adjudication.finding_id for adjudication in view.review_adjudications]
    _require(len(set(adjudication_ids)) == len(adjudication_ids), "duplicate report view adjudication")
    deterministic_evidence_ids = {
        evidence.evidence_id
        for finding in view.deterministic_findings
        for evidence in finding.evidence
    }
    for finding in view.deterministic_findings:
        _require(finding.rule_status is not RuleStatus.SATISFIED, "satisfied rule cannot be a report finding")
        for evidence in finding.evidence:
            _validate_evidence(evidence)
    for adjudication in view.review_adjudications:
        _require(
            set(adjudication.evidence_ids) <= deterministic_evidence_ids,
            f"report adjudication references unknown evidence_id {adjudication.finding_id!r}",
        )
        _require(
            adjudication.epistemic_status in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED),
            "report adjudication epistemic_status must be inferred or unresolved",
        )
        _require(adjudication.rationale.strip(), "report adjudication rationale must not be empty")
    semantic_ids = [finding.finding_id for finding in view.semantic_findings]
    _require(len(set(semantic_ids)) == len(semantic_ids), "duplicate report semantic finding_id")
    for finding in view.semantic_findings:
        _require(
            finding.epistemic_status in (EpistemicStatus.INFERRED, EpistemicStatus.UNRESOLVED),
            "report semantic finding epistemic_status must be inferred or unresolved",
        )
        _require(
            finding.finding_id not in finding_ids,
            f"report semantic finding collides with deterministic finding_id {finding.finding_id!r}",
        )
        _require(
            set(finding.evidence_ids) <= deterministic_evidence_ids,
            f"report references unknown evidence_id {finding.finding_id!r}",
        )
        for evidence in finding.evidence:
            _validate_evidence(evidence, review=True)
    _require(set(adjudication_ids) <= set(finding_ids), "report view adjudicates unknown finding")
    if audit is not None:
        _require(view.audit_digest == audit.semantic_digest, "report view is not bound to audit")
        _require(
            view.assessment == audit.content.assessment,
            "report view assessment differs from bound audit",
        )
        _require(
            view.deterministic_findings == audit.content.findings,
            "report view findings differ from bound audit",
        )
