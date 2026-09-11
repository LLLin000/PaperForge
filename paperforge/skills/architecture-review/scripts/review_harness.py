#!/usr/bin/env python3
"""Deterministic review-process machinery for the architecture-review Skill (#132).

The Skill is model-invoked; this harness is the process machinery it drives so
every run follows the same steps and the completion invariants stay checkable:

- `audit` — load and validate a DeterministicAudit, then print digests,
  declared operation scope, operation-scoped evidence candidates, and required
  adjudications.
- `plan` — derive a bounded review packet from the validated audit and evidence
  index; the model reads only the packet's candidates and exact source reads.
- `emit` — validate a drafted ArchitectureReview and typed trace manifest
  against that audit.

The harness never edits source, Contract, Survey, or production artifacts; the
review file it writes (with `--out`) is the Skill's own output overlay.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from paperforge.architecture_audit import (
    ArchitectureError,
    ArchitectureReview,
    DeterministicAudit,
    DigestMismatch,
    RuleStatus,
    compose,
    reconcile,
    validate_audit,
)
from paperforge.architecture_audit.fixtures import load_fixture
TRACE_STAGES = (
    "input",
    "output",
    "transport",
    "side_effects",
    "publication",
    "invalidation",
    "failure",
    "final_consumer",
)

TRACE_STATUSES = frozenset({"observed", "not_applicable", "needs_evidence"})
TRACE_REASON_CODES = frozenset(
    {f"no_{stage}" for stage in TRACE_STAGES}
    | {"not_applicable_by_contract", "not_in_scope"}
)

# Fact kinds are deliberately mapped conservatively. An evidence item may only
# support stages the deterministic layer can justify from its fact kind.
FACT_STAGE_MAP = {
    "effect": ("side_effects", "failure"),
    "signal": ("transport", "final_consumer"),
    "unit_authority": ("publication", "final_consumer"),
    "role_authority": ("side_effects", "publication", "final_consumer"),
    "canonical_write": ("publication", "invalidation"),
    "unresolved": ("side_effects", "failure"),
    "filesystem_read": ("input", "output"),
    "operation_binding": ("input", "output"),
    "candidate": TRACE_STAGES,
    "interface": ("transport", "final_consumer"),
    "trace": TRACE_STAGES,
}

# Findings that must be adjudicated: deterministic violations and unresolved
# edges. Planned gaps are declarative and informational; exceptions are
# already declared in the Contract. Nothing else demands review attention.
REQUIRED_STATUSES = (RuleStatus.VIOLATED, RuleStatus.UNRESOLVED)


# ---------------------------------------------------------------- loading


def load_audit(
    fixture: str | None = None,
    contract: str | None = None,
    survey: str | None = None,
    audit_path: str | None = None,
) -> DeterministicAudit:
    """Load a validated DeterministicAudit from fixture names, JSON paths, or a saved audit.

    Raises ArchitectureError/ValueError when input is invalid — the Skill must
    load validated input first and stop on refusal.
    """
    if audit_path is not None:
        payload = json.loads(Path(audit_path).read_text(encoding="utf-8"))
        audit = DeterministicAudit.from_dict(payload)
        validate_audit(audit)
        return audit
    if fixture is not None:
        contract_layer, survey_layer = load_fixture(fixture)
    elif contract is not None and survey is not None:
        contract_layer = _load_layer("contract", contract)
        survey_layer = _load_layer("survey", survey)
    else:
        raise ValueError("audit requires --fixture NAME, --contract+--survey, or --audit PATH")
    return reconcile(contract_layer, survey_layer)


def _load_layer(kind: str, ref: str) -> Any:
    from paperforge.architecture_audit import ArchitectureContract, ArchitectureSurvey

    payload = json.loads(Path(ref).read_text(encoding="utf-8"))
    layer_cls = ArchitectureContract if kind == "contract" else ArchitectureSurvey
    return layer_cls.from_dict(payload)


def _evidence_of(fact: Any) -> list[Any]:
    result = [fact.evidence] if getattr(fact, "evidence", None) is not None else []
    result.extend(getattr(fact, "consumer_evidence", ()) or ())
    return result


def _fact_kind(fact: Any) -> str:
    names = {
        "EffectFact": "effect",
        "SignalFact": "signal",
        "UnitAuthorityFact": "unit_authority",
        "RoleAuthorityFact": "role_authority",
        "CanonicalWriteFact": "canonical_write",
        "UnresolvedFact": "unresolved",
        "FilesystemReadFact": "filesystem_read",
        "OperationBindingFact": "operation_binding",
        "CandidateFact": "candidate",
        "InterfaceFact": "interface",
        "TraceFact": "trace",
    }
    return names.get(type(fact).__name__, type(fact).__name__.lower())


def evidence_index_from_survey(survey: Any) -> dict[str, dict[str, Any]]:
    """Index each evidence item by its owning fact, operation, subject, and stages."""
    index: dict[str, dict[str, Any]] = {}
    for fact in survey.facts:
        kind = _fact_kind(fact)
        operation_ids = {
            operation_id
            for operation_id in (getattr(fact, "operation_id", None),)
            if operation_id
        }
        subjects = {
            subject
            for subject in (
                getattr(fact, "signal_id", None),
                getattr(fact, "unit_id", None),
                getattr(fact, "interface_id", None),
                getattr(fact, "trace_id", None),
                getattr(fact, "candidate_id", None),
            )
            if subject
        }
        for evidence in _evidence_of(fact):
            entry = index.setdefault(
                evidence.evidence_id,
                {
                    "file": evidence.file,
                    "symbol": evidence.symbol,
                    "fact_kinds": set(),
                    "operation_ids": set(),
                    "subjects": set(),
                    "stages": set(),
                },
            )
            entry["fact_kinds"].add(kind)
            entry["operation_ids"].update(operation_ids)
            entry["subjects"].update(subjects)
            entry["stages"].update(FACT_STAGE_MAP.get(kind, ()))
    return {
        evidence_id: {
            **entry,
            "fact_kinds": sorted(entry["fact_kinds"]),
            "operation_ids": sorted(entry["operation_ids"]),
            "subjects": sorted(entry["subjects"]),
            "stages": sorted(entry["stages"]),
        }
        for evidence_id, entry in sorted(index.items())
    }


# ---------------------------------------------------------------- scope


def scope(audit: DeterministicAudit) -> list[str]:
    """Declared Contract operations preserved by the deterministic audit."""
    operation_scope = audit.run_metadata.get("operation_scope")
    if operation_scope is None:
        raise ArchitectureError(
            "audit missing deterministic operation_scope; rerun the audit before review"
        )
    if isinstance(operation_scope, (str, bytes)) or not isinstance(operation_scope, Sequence):
        raise ArchitectureError("audit operation_scope must be a sequence")
    return sorted({operation for operation in operation_scope if isinstance(operation, str) and operation})


def evidence_candidates(
    audit: DeterministicAudit,
    evidence_index: Mapping[str, Mapping[str, Any]],
    operations: Sequence[str] | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Return evidence IDs that are relevant to each operation and stage."""
    declared = list(operations) if operations is not None else scope(audit)
    candidates = {operation: {stage: [] for stage in TRACE_STAGES} for operation in declared}
    finding_evidence: dict[str, set[str]] = {}
    for finding in audit.content.findings:
        finding_evidence.setdefault(finding.subject, set()).update(
            evidence.evidence_id for evidence in finding.evidence
        )
    for evidence_id, metadata in evidence_index.items():
        owners = set(metadata.get("operation_ids", ()))
        for operation in declared:
            if evidence_id in finding_evidence.get(operation, set()):
                owners.add(operation)
        for operation in owners.intersection(candidates):
            for stage in set(metadata.get("stages", ())).intersection(TRACE_STAGES):
                candidates[operation][stage].append(evidence_id)
    for stages in candidates.values():
        for stage in stages:
            stages[stage].sort()
    return candidates


def required_findings(audit: DeterministicAudit) -> list[Any]:
    """Findings that must be adjudicated (violated or unresolved)."""
    return [f for f in audit.content.findings if f.rule_status in REQUIRED_STATUSES]


def audit_summary(
    audit: DeterministicAudit,
    evidence_index: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """The fixed inputs a review binds to; also the Skill's scope list."""
    index = dict(evidence_index or {})
    return {
        "schema_version": audit.schema_version,
        "reconciler_version": audit.content.reconciler_version,
        "audit_digest": audit.semantic_digest,
        "contract_digest": audit.content.bound_contract_digest,
        "survey_digest": audit.content.bound_survey_digest,
        "assessment": {
            "status": audit.content.assessment.status.value,
            "gate_eligible": audit.content.assessment.gate_eligible,
            "reasons": list(audit.content.assessment.reasons),
        },
        "findings": [
            {
                "finding_id": finding.finding_id,
                "rule_id": finding.rule_id,
                "subject": finding.subject,
                "rule_status": finding.rule_status.value,
                "severity": finding.severity,
                "message": finding.message,
            }
            for finding in audit.content.findings
        ],
        "scope": scope(audit),
        "must_adjudicate": [finding.finding_id for finding in required_findings(audit)],
        "evidence_index": index,
        "evidence_candidates": evidence_candidates(audit, index) if index else {},
        "trace_stages": list(TRACE_STAGES),
        "trace_statuses": sorted(TRACE_STATUSES),
    }


# ---------------------------------------------------------------- emit


def _validate_trace_stage(
    operation: str,
    stage: str,
    value: Any,
    evidence_index: Mapping[str, Mapping[str, Any]],
    candidates: Mapping[str, Mapping[str, Sequence[str]]],
) -> list[str]:
    problems: list[str] = []
    prefix = f"trace {operation}: stage {stage}"
    if not isinstance(value, dict):
        return [f"{prefix} must be a typed object"]
    status = value.get("status")
    if status not in TRACE_STATUSES:
        return [f"{prefix} has invalid status {status!r}"]
    expected_keys = {
        "observed": {"status", "evidence_ids"},
        "not_applicable": {"status", "reason_code"},
        "needs_evidence": {"status", "question"},
    }[status]
    extra_keys = sorted(set(value) - expected_keys)
    if extra_keys:
        problems.append(f"{prefix} has unexpected fields: {', '.join(extra_keys)}")
    if status == "observed":
        evidence_ids = value.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            problems.append(f"{prefix} observed requires non-empty evidence_ids")
            return problems
        if len(set(evidence_ids)) != len(evidence_ids):
            problems.append(f"{prefix} observed repeats an evidence ID")
        relevant = set(candidates.get(operation, {}).get(stage, ()))
        for evidence_id in evidence_ids:
            if not isinstance(evidence_id, str):
                problems.append(f"{prefix} evidence IDs must be strings")
                continue
            if evidence_id not in evidence_index:
                problems.append(f"{prefix} cites unknown evidence {evidence_id}")
            elif evidence_id not in relevant:
                problems.append(
                    f"{prefix} cites evidence {evidence_id} not relevant to this operation/stage"
                )
    elif status == "not_applicable":
        reason_code = value.get("reason_code")
        if reason_code not in TRACE_REASON_CODES:
            problems.append(f"{prefix} has invalid reason_code {reason_code!r}")
    else:
        question = value.get("question")
        if not isinstance(question, str) or not question.strip():
            problems.append(f"{prefix} needs_evidence requires a question")
    return problems


def validate_emission(
    audit: DeterministicAudit,
    review: ArchitectureReview,
    trace: dict[str, Any] | None,
    evidence_index: Mapping[str, Mapping[str, Any]] | None = None,
    operations: Sequence[str] | None = None,
) -> list[str]:
    """Return process problems; empty list means the emission is valid.

    Trace stages are typed: ``observed`` cites operation/stage-relevant
    evidence, ``not_applicable`` carries a reason code, and
    ``needs_evidence`` carries a question. Free-text stage fillers and a global
    evidence pool are intentionally rejected.
    """
    problems: list[str] = []

    # Binding + schema: compose() re-validates the review and rejects stale
    # digests or a mismatched reconciler version with a precise message.
    try:
        compose(audit, review)
    except ArchitectureError as exc:
        problems.append(str(exc))
    except DigestMismatch as exc:
        problems.append(str(exc))

    if not review.reviewer_type.strip():
        problems.append("review reviewer_type must not be empty")

    # Adjudication completeness: no high-risk/unresolved edge may be skipped.
    adjudicated = {adjudication.finding_id for adjudication in review.adjudications}
    for finding in required_findings(audit):
        if finding.finding_id not in adjudicated:
            problems.append(
                f"no adjudication for required finding {finding.finding_id} ({finding.rule_id})"
            )

    # Trace completion: one trace per scoped operation, all eight typed stages,
    # no unknown operation, fabricated evidence, or cross-operation evidence.
    if trace is None:
        problems.append("trace manifest required: every emission must end in a scoped trace")
        return problems
    if evidence_index is None:
        problems.append(
            "trace validation requires an evidence index (re-audit with --fixture/--survey)"
        )
    try:
        declared = list(operations) if operations is not None else scope(audit)
    except ArchitectureError as exc:
        problems.append(str(exc))
        declared = []
    declared_set = set(declared)
    trace_keys = set(trace)
    if trace_keys != declared_set:
        missing = sorted(declared_set - trace_keys)
        extra = sorted(trace_keys - declared_set)
        if missing:
            problems.append(f"trace missing scoped operations: {', '.join(missing)}")
        if extra:
            problems.append(f"trace covers unknown operations: {', '.join(extra)}")
    index = evidence_index or {}
    candidates = evidence_candidates(audit, index, declared)
    for operation, stages in trace.items():
        if operation not in declared_set:
            continue
        if not isinstance(stages, dict):
            problems.append(f"trace {operation}: stages must be an object")
            continue
        for stage in TRACE_STAGES:
            if stage not in stages:
                problems.append(f"trace {operation}: missing stage {stage}")
                continue
            problems.extend(_validate_trace_stage(operation, stage, stages[stage], index, candidates))
    return problems


# ---------------------------------------------------------------- planning / CLI


def _evidence_index_for_args(args: argparse.Namespace, audit: DeterministicAudit) -> dict[str, dict[str, Any]] | None:
    if getattr(args, "fixture", None):
        _, survey_layer = load_fixture(args.fixture)
        return evidence_index_from_survey(survey_layer)
    if getattr(args, "survey", None):
        return evidence_index_from_survey(_load_layer("survey", args.survey))
    stored = audit.run_metadata.get("evidence_index")
    return dict(stored) if isinstance(stored, Mapping) else None


def build_review_plan(
    audit: DeterministicAudit,
    evidence_index: Mapping[str, Mapping[str, Any]],
    *,
    mode: str = "delta",
    changed_files: Sequence[str] = (),
    operations: Sequence[str] = (),
) -> dict[str, Any]:
    """Build the bounded packet the model must use for an architecture review."""
    all_operations = scope(audit)
    candidates = evidence_candidates(audit, evidence_index)
    changed = {path.replace("\\", "/") for path in changed_files}
    requested = [operation for operation in operations if operation]
    if requested:
        affected = sorted(set(requested).intersection(all_operations))
    elif mode in {"gate", "focused"}:
        affected = []
    else:
        affected = sorted(
            operation
            for operation in all_operations
            if any(evidence_index[evidence_id].get("file") in changed
                   for stage in candidates[operation].values()
                   for evidence_id in stage)
        )
    finding_ids = {
        finding.finding_id
        for finding in audit.content.findings
        if finding.subject in affected
        or any(evidence.file in changed for evidence in finding.evidence)
    }
    source_reads: dict[tuple[str, str], dict[str, str]] = {}
    for operation in affected:
        for evidence_ids in candidates[operation].values():
            for evidence_id in evidence_ids:
                metadata = evidence_index[evidence_id]
                source_reads[(metadata["file"], metadata["symbol"])] = {
                    "file": metadata["file"],
                    "symbol": metadata["symbol"],
                    "why": f"candidate evidence for {operation}",
                }
    for finding in required_findings(audit):
        for evidence in finding.evidence:
            source_reads[(evidence.file, evidence.symbol)] = {
                "file": evidence.file,
                "symbol": evidence.symbol,
                "why": f"required adjudication {finding.finding_id}",
            }
    trace: dict[str, dict[str, dict[str, Any]]] = {}
    unresolved_questions: list[dict[str, str]] = []
    for operation in affected:
        trace[operation] = {}
        for stage in TRACE_STAGES:
            candidate_ids = candidates[operation][stage]
            if candidate_ids:
                trace[operation][stage] = {
                    "state": "observed",
                    "candidate_evidence": candidate_ids,
                }
            else:
                question = f"Which source path proves {operation}.{stage}?"
                trace[operation][stage] = {"state": "needs_review", "question": question}
                unresolved_questions.append(
                    {"operation": operation, "stage": stage, "question": question}
                )
    stop_conditions = [
        "Use packet evidence before opening another file.",
        "Read only listed file/symbol candidates, then expand callers or callees by one hop.",
        "Stop after two hops and emit needs_evidence when the edge remains unbound.",
    ]
    if mode == "delta" and not affected:
        stop_conditions.append("No changed operation was deterministically bound; do not run a full survey.")
    return {
        "mode": mode,
        "scope": all_operations,
        "affected_operations": affected,
        "affected_rules": sorted(finding_ids),
        "must_adjudicate": [finding.finding_id for finding in required_findings(audit)],
        "evidence_candidates": {
            operation: candidates[operation] for operation in affected
        },
        "trace": trace,
        "unresolved_questions": unresolved_questions,
        "source_reads": sorted(source_reads.values(), key=lambda row: (row["file"], row["symbol"])),
        "stop_conditions": stop_conditions,
        "bindings": {
            "audit_digest": audit.semantic_digest,
            "contract_digest": audit.content.bound_contract_digest,
            "survey_digest": audit.content.bound_survey_digest,
            "reconciler_version": audit.content.reconciler_version,
        },
    }


def _cmd_audit(args: argparse.Namespace) -> int:
    try:
        audit = load_audit(fixture=args.fixture, contract=args.contract, survey=args.survey,
                           audit_path=args.audit)
        evidence_index = _evidence_index_for_args(args, audit)
        summary = audit_summary(audit, evidence_index)
    except (ArchitectureError, ValueError, OSError, KeyError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.out:
        payload = audit.to_dict()
        if evidence_index is not None:
            payload["run_metadata"] = {
                **payload.get("run_metadata", {}),
                "evidence_index": evidence_index,
            }
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"audit written to {args.out}", file=sys.stderr)
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    try:
        audit = load_audit(fixture=args.fixture, contract=args.contract, survey=args.survey,
                           audit_path=args.audit)
        evidence_index = _evidence_index_for_args(args, audit)
        if evidence_index is None:
            raise ArchitectureError("plan requires an evidence index; use --fixture or --survey")
        plan = build_review_plan(
            audit,
            evidence_index,
            mode=args.mode,
            changed_files=args.changed_file,
            operations=args.operations.split(",") if args.operations else (),
        )
    except (ArchitectureError, ValueError, OSError, KeyError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(plan, indent=2, ensure_ascii=False)
    print(payload)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
        print(f"review plan written to {args.out}", file=sys.stderr)
    return 0


def _cmd_emit(args: argparse.Namespace) -> int:
    try:
        audit = load_audit(fixture=args.fixture, contract=args.contract, survey=args.survey,
                           audit_path=args.audit)
    except (ArchitectureError, ValueError, OSError, KeyError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    try:
        review_payload = json.loads(Path(args.review).read_text(encoding="utf-8"))
        if args.fill_digests:
            review_payload["contract_digest"] = audit.content.bound_contract_digest
            review_payload["survey_digest"] = audit.content.bound_survey_digest
            review_payload["audit_digest"] = audit.semantic_digest
            review_payload["reconciler_version"] = audit.content.reconciler_version
        review = ArchitectureReview.from_dict(review_payload)
        trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
        evidence_index = _evidence_index_for_args(args, audit)
    except (ArchitectureError, ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    problems = validate_emission(
        audit,
        review,
        trace,
        evidence_index,
        operations=args.operations.split(",") if args.operations else None,
    )
    if problems:
        print("PROBLEMS:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    if args.out:
        Path(args.out).write_text(
            json.dumps(review.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"OK: bound review written to {args.out}")
    else:
        print("OK: review bound to audit, all completion invariants satisfied")
    return 0

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="architecture-review process harness (#132)")
    sub = parser.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="load and print a validated audit summary")
    audit_p.add_argument("--fixture")
    audit_p.add_argument("--contract")
    audit_p.add_argument("--survey")
    audit_p.add_argument("--audit")
    audit_p.add_argument("--out", help="write the validated audit JSON for a later emit")
    audit_p.set_defaults(func=_cmd_audit)

    plan_p = sub.add_parser("plan", help="build a bounded deterministic review packet")
    plan_p.add_argument("--fixture")
    plan_p.add_argument("--contract")
    plan_p.add_argument("--survey")
    plan_p.add_argument("--audit")
    plan_p.add_argument(
        "--mode",
        choices=("gate", "delta", "focused", "deep-trace", "full-release"),
        default="delta",
    )
    plan_p.add_argument("--changed-file", action="append", default=[])
    plan_p.add_argument("--operations")
    plan_p.add_argument("--out")
    plan_p.set_defaults(func=_cmd_plan)

    emit_p = sub.add_parser("emit", help="validate a drafted ArchitectureReview against the audit")
    emit_p.add_argument("--audit", required=True)
    emit_p.add_argument("--review", required=True)
    emit_p.add_argument("--trace", required=True)
    emit_p.add_argument("--fixture")
    emit_p.add_argument("--contract")
    emit_p.add_argument("--survey")
    emit_p.add_argument("--operations")
    emit_p.add_argument("--fill-digests", action="store_true")
    emit_p.add_argument("--out")
    emit_p.set_defaults(func=_cmd_emit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
