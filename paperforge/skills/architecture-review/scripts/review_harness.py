#!/usr/bin/env python3
"""Deterministic review-process machinery for the architecture-review Skill (#132).

The Skill is model-invoked; this harness is the process machinery it drives so
every run follows the same steps and the completion invariants stay checkable:

- `audit` — load and validate a DeterministicAudit (from a Slice A fixture or
  saved JSON), then print the summary the review must bind to: digests,
  reconciler version, assessment, findings, scoped operations, evidence pool.
- `emit` — validate a drafted ArchitectureReview (+ optional trace manifest)
  against that audit: schema, digest/reconciler-version binding, epistemic
  status, finding-ID integrity, adjudication completeness, trace completeness.

The harness never edits source, Contract, Survey, or production artifacts; the
review file it writes (with `--out`) is the Skill's own output overlay.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
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

# Every scoped operation ends in one trace covering these eight stages.
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


def evidence_pool_from_survey(survey: Any) -> list[str]:
    """All evidence IDs carried by survey facts — the pool a trace may cite."""
    pool: list[str] = []
    for fact in survey.facts:
        for evidence in _evidence_of(fact):
            pool.append(evidence.evidence_id)
    return pool


def _evidence_of(fact: Any) -> list[Any]:
    result = [fact.evidence] if getattr(fact, "evidence", None) is not None else []
    result.extend(getattr(fact, "consumer_evidence", ()) or ())
    return result


# ---------------------------------------------------------------- scope


def scope(audit: DeterministicAudit) -> list[str]:
    """Scoped operations: the distinct subjects the audit reports on."""
    return sorted({finding.subject for finding in audit.content.findings if finding.subject})


def required_findings(audit: DeterministicAudit) -> list[Any]:
    """Findings that must be adjudicated (violated or unresolved)."""
    return [f for f in audit.content.findings if f.rule_status in REQUIRED_STATUSES]


def audit_summary(audit: DeterministicAudit, evidence_pool: Sequence[str] = ()) -> dict[str, Any]:
    """The fixed inputs a review binds to; also the Skill's scope list."""
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
        "evidence_pool": sorted(set(evidence_pool)),
        "trace_stages": list(TRACE_STAGES),
    }


# ---------------------------------------------------------------- emit


def validate_emission(
    audit: DeterministicAudit,
    review: ArchitectureReview,
    trace: dict[str, Any] | None,
    evidence_pool: Sequence[str] | None = None,
    operations: Sequence[str] | None = None,
) -> list[str]:
    """Return process problems; empty list means the emission is valid.

    Covers every testable completion invariant: validated-input-first,
    digest/reconciler-version binding, epistemic status, finding-ID integrity,
    adjudication completeness, and the eight-stage trace completion. `trace`
    is mandatory — every emission must end in a scoped trace — and the
    evidence pool must be known so fabricated evidence is refused.
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

    # Trace completion: one trace per scoped operation, all eight stages, no
    # silent empty stage, no unknown operation or fabricated evidence.
    if trace is None:
        problems.append("trace manifest required: every emission must end in a scoped trace")
    else:
        if evidence_pool is None:
            problems.append(
                "trace validation requires an evidence pool (re-audit with --fixture/--survey)"
            )
        known_pool = set(evidence_pool) if evidence_pool is not None else None
        declared = list(operations) if operations is not None else scope(audit)
        declared_set = set(declared)
        trace_keys = set(trace)
        if trace_keys != declared_set:
            missing = sorted(declared_set - trace_keys)
            extra = sorted(trace_keys - declared_set)
            if missing:
                problems.append(f"trace missing scoped operations: {', '.join(missing)}")
            if extra:
                problems.append(f"trace covers unknown operations: {', '.join(extra)}")
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
                value = stages[stage]
                if isinstance(value, list):
                    if not value:
                        problems.append(f"trace {operation}: stage {stage} is empty")
                    for evidence_id in value:
                        if known_pool is not None and evidence_id not in known_pool:
                            problems.append(
                                f"trace {operation}: stage {stage} cites unknown evidence {evidence_id}"
                            )
                elif not (isinstance(value, str) and value.strip()):
                    problems.append(
                        f"trace {operation}: stage {stage} must be evidence ids or a note"
                    )

    return problems


# ---------------------------------------------------------------- CLI


def _cmd_audit(args: argparse.Namespace) -> int:
    try:
        audit = load_audit(fixture=args.fixture, contract=args.contract, survey=args.survey,
                           audit_path=args.audit)
    except (ArchitectureError, ValueError, OSError, KeyError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    pool: list[str] | None
    if args.fixture:
        _, survey_layer = load_fixture(args.fixture)
        pool = evidence_pool_from_survey(survey_layer)
    elif args.survey:
        pool = evidence_pool_from_survey(_load_layer("survey", args.survey))
    elif "evidence_pool" in audit.run_metadata:
        pool = audit.run_metadata["evidence_pool"]
    else:
        pool = None
    print(json.dumps(audit_summary(audit, pool or ()), indent=2, ensure_ascii=False))
    if args.out:
        payload = audit.to_dict()
        if pool is not None:
            payload["run_metadata"] = {
                **payload.get("run_metadata", {}),
                "evidence_pool": list(dict.fromkeys(pool)),
            }
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"audit written to {args.out}", file=sys.stderr)
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
    except (ArchitectureError, ValueError, KeyError, TypeError, OSError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    pool: list[str] | None = None
    if args.fixture:
        _, survey_layer = load_fixture(args.fixture)
        pool = evidence_pool_from_survey(survey_layer)
    elif args.survey:
        pool = evidence_pool_from_survey(_load_layer("survey", args.survey))
    elif "evidence_pool" in audit.run_metadata:
        pool = audit.run_metadata["evidence_pool"]
    problems = validate_emission(
        audit, review, trace, pool, operations=args.operations.split(",") if args.operations else None
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
