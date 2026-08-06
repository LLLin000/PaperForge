"""Deterministic CI gate (#134).

The gate is the only place release automation reads the architecture audit.
Semantics:

- Only **reviewed low-false-positive rules** (an explicit allowlist of
  rule_ids) can block; planned gaps, advisory/informational findings,
  unresolved evidence, and the review overlay never determine exit status.
- Gate eligibility still requires an active contract rule, blocking
  enforcement, complete required extractor coverage, deterministic evidence,
  and a reviewed low-false-positive rule implementation — that is exactly
  `Audit.assessment.gate_eligible` plus a non-empty allowlist.
- The Audit's own `assessment.status`, `gate_eligible`, and reasons are
  authoritative; this module never re-derives coverage completeness.
- Ineligible audits are reported `skipped` with reasons (exit 0) — the gate
  only *blocks on violations it is configured to enforce*.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.architecture_audit.layers import (
    DeterministicAudit,
    RuleStatus,
    validate_audit,
)

EXIT_PASS = 0
EXIT_BLOCK = 1
EXIT_USAGE = 2


@dataclass(frozen=True)
class GateResult:
    status: str  # "pass" | "block" | "skipped"
    eligible: bool
    blocking_rules: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    findings: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def exit_code(self) -> int:
        if self.status == "block":
            return EXIT_BLOCK
        return EXIT_PASS


def evaluate_gate(
    audit: DeterministicAudit,
    allowlist: tuple[str, ...] = (),
) -> GateResult:
    """Evaluate one authoritative Audit against a reviewed rule allowlist."""
    validate_audit(audit)
    assessment = audit.content.assessment
    if not assessment.gate_eligible:
        return GateResult(
            status="skipped",
            eligible=False,
            reasons=tuple(assessment.reasons),
        )
    if not allowlist:
        return GateResult(
            status="skipped",
            eligible=True,
            reasons=("no reviewed rules in the allowlist",),
        )
    allowed = set(allowlist)
    blocking: list[dict[str, Any]] = []
    for finding in audit.content.findings:
        if finding.rule_id not in allowed:
            continue
        if finding.rule_status is not RuleStatus.VIOLATED:
            continue
        if finding.severity != "blocking":
            continue
        blocking.append(finding.to_dict())
    if blocking:
        return GateResult(
            status="block",
            eligible=True,
            blocking_rules=tuple(sorted(f["rule_id"] for f in blocking)),
            findings=tuple(blocking),
        )
    return GateResult(
        status="pass",
        eligible=True,
        blocking_rules=(),
        reasons=("no allowlisted blocking violations",),
    )


def load_audit(path: Path) -> DeterministicAudit:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DeterministicAudit.from_dict(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paperforge-architecture-gate",
        description="Deterministic architecture CI gate (#134) — consumes DeterministicAudit only.",
    )
    parser.add_argument("--audit", required=True, help="audit.json path")
    parser.add_argument(
        "--allowlist", nargs="*", default=(), help="reviewed rule ids allowed to block"
    )
    parser.add_argument("--json", action="store_true", help="emit GateResult as JSON")
    args = parser.parse_args(argv)

    try:
        audit = load_audit(Path(args.audit))
    except (OSError, ValueError) as exc:
        print(f"gate usage error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    result = evaluate_gate(audit, tuple(args.allowlist))
    if args.json:
        print(
            json.dumps(
                {
                    "status": result.status,
                    "eligible": result.eligible,
                    "blocking_rules": list(result.blocking_rules),
                    "reasons": list(result.reasons),
                    "exit_code": result.exit_code,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(
            f"gate={result.status} eligible={result.eligible} "
            f"blocking={','.join(result.blocking_rules) or '-'} "
            f"reasons={','.join(result.reasons) or '-'}"
        )
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
