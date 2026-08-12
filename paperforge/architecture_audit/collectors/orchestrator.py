"""Maintainer-only audit orchestrator (#133).

Scans repository source deterministically, merges Python AST and TypeScript
compiler facts into one validated ArchitectureSurvey, invokes the #131 pure
reconciler, and writes survey/audit JSON plus a terminal summary.

No Agent, MCP, LSP, network, vault, credential, OCR, Memory, or Embedding
operation is invoked. TypeScript is never installed automatically: a missing
compiler produces explicit `unavailable` coverage and an error diagnostic —
never a silent all-clear.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.architecture_audit import (
    ArchitectureContract,
    ArchitectureSurvey,
    reconcile,
    validate_survey,
)
from paperforge.architecture_audit.collectors.common import (
    WrapperSpec,
    load_default_python_registry,
    load_wrapper_registry,
    operation_id_of,
    to_wrapper_summaries,
)
from paperforge.architecture_audit.collectors.python_ast import (
    EXTRACTOR as PY_EXTRACTOR,
)
from paperforge.architecture_audit.collectors.python_ast import (
    collect_python,
)
from paperforge.architecture_audit.layers import (
    CoverageEntry,
    CoverageStatus,
    RepositoryState,
    fact_from_dict,
)

TS_EXTRACTOR = "typescript_compiler"
TS_SCRIPT = Path(__file__).with_name("ts_collect.js")

DEFAULT_PY_ROOTS = ("paperforge",)
DEFAULT_TS_ROOTS = ("paperforge/plugin/src",)


@dataclass
class CollectOutcome:
    survey: ArchitectureSurvey | None = None
    audit: Any = None
    summary: dict[str, Any] = field(default_factory=dict)
    parse_errors: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    scanned_files: list[tuple[str, str]] = field(default_factory=list)
    facts: list[dict[str, Any]] = field(default_factory=list)
    wrapper_hits: list[dict[str, Any]] = field(default_factory=list)


def _git_state(repo: Path) -> RepositoryState:
    rev = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=repo
    ).stdout.strip()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=repo
    ).stdout
    dirty = bool(porcelain)
    diff_digest = ""
    if dirty:
        diff = subprocess.run(
            ["git", "diff"], capture_output=True, text=True, cwd=repo
        ).stdout
        diff_digest = "sha256:" + hashlib.sha256(diff.encode("utf-8")).hexdigest()
    return RepositoryState(revision=rev, dirty=dirty, dirty_diff_digest=diff_digest)


def _run_ts_collector(
    repo: Path,
    ts_root: Path,
    node_cmd: str,
    registry: tuple[WrapperSpec, ...],
) -> tuple[dict[str, Any], str | None]:
    """Run the Node collector. Returns (payload, diagnostic_or_None)."""
    if not ts_root.is_dir():
        return {}, f"typescript source root missing: {ts_root}"
    node = shutil.which(node_cmd) if node_cmd != "node" else shutil.which("node")
    if node is None:
        return {}, "node executable not found"
    cmd = [node, str(TS_SCRIPT), str(ts_root)]
    registry_payload = [w.to_dict() for w in registry]
    if registry_payload:
        import tempfile

        reg_file = Path(tempfile.gettempdir()) / "paperforge-ts-registry.json"
        reg_file.write_text(
            json.dumps(registry_payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        cmd.append(str(reg_file))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=repo, timeout=600, encoding="utf-8"
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, f"typescript collector failed to run: {exc}"
    if proc.returncode != 0:
        return {}, (
            f"typescript collector exited {proc.returncode}: "
            f"{(proc.stderr or proc.stdout).strip()[:200]}"
        )
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as exc:
        return {}, f"typescript collector produced invalid JSON: {exc}"


def _ts_facts_to_repo_relative(
    payload: dict[str, Any],
    ts_root_rel: str,
    known_operations: frozenset[str],
) -> list[dict[str, Any]]:
    """Re-base TS evidence paths to repository-relative and re-scope operation
    ids through the same `operation_id_of` mapping the Python side uses."""
    out: list[dict[str, Any]] = []
    for fact in payload.get("facts", []):
        fact = dict(fact)
        evidence = fact.get("evidence")
        if evidence:
            rel = evidence["file"]
            evidence = dict(evidence)
            evidence["file"] = f"{ts_root_rel}/{rel}"
            fact["evidence"] = evidence
        if "operation_id" in fact:
            rel = (fact.get("evidence") or {}).get("file", "")
            fact["operation_id"] = operation_id_of(
                rel, rel.split("/")[-1].removesuffix(".ts"), known_operations
            )
        out.append(fact)
    return out


def collect(
    repo: Path,
    *,
    contract: ArchitectureContract,
    py_roots: tuple[str, ...] = DEFAULT_PY_ROOTS,
    ts_roots: tuple[str, ...] = DEFAULT_TS_ROOTS,
    node_cmd: str = "node",
    python_registry: tuple[WrapperSpec, ...] | None = None,
    ts_registry: tuple[WrapperSpec, ...] | None = None,
) -> CollectOutcome:
    """Deterministic collect -> merge -> validate -> reconcile. Pure file/process
    I/O; never imports project runtime code."""
    outcome = CollectOutcome()
    registry = (
        python_registry if python_registry is not None else load_default_python_registry()
    )
    # #170 P0-1: the TS collector must receive the SAME default wrapper
    # registry as Python — read wrappers (bootstrap.pointer.read / …) are
    # collector knowledge, not an opt-in.
    ts_registry = ts_registry if ts_registry is not None else load_default_python_registry()
    known_operations = frozenset(op.operation_id for op in contract.operations)

    # ---- Python side
    py_scanned: list[tuple[str, str]] = []
    py_facts: list[dict[str, Any]] = []
    py_errors: list[str] = []
    for root_rel in py_roots:
        root = repo / root_rel
        if not root.is_dir():
            outcome.diagnostics.append(f"python source root missing: {root_rel}")
            continue
        result = collect_python(
            root,
            wrappers=registry,
            known_operations=known_operations,
        )
        py_scanned.extend(result.scanned_files)
        py_facts.extend(result.facts)
        py_errors.extend(result.parse_errors)
        outcome.wrapper_hits.extend(result.wrapper_hits)

    # ---- TypeScript side
    ts_diag: str | None = None
    ts_payload: dict[str, Any] = {}
    for root_rel in ts_roots:
        ts_root = repo / root_rel
        payload, diag = _run_ts_collector(repo, ts_root, node_cmd, ts_registry)
        if diag:
            ts_diag = diag
            outcome.diagnostics.append(diag)
            continue
        ts_payload = payload
        outcome.wrapper_hits.extend(payload.get("wrapper_hits", []))
        break  # first healthy TS root wins
    ts_scanned: list[tuple[str, str]] = []
    if ts_payload:
        ts_scanned = list(ts_payload.get("scanned", []))
        for rel, digest in ts_scanned:
            repo_rel_path = f"{ts_roots[0]}/{rel}"
            outcome.scanned_files.append((repo_rel_path, digest))
        py_facts.extend(
            _ts_facts_to_repo_relative(ts_payload, ts_roots[0], known_operations)
        )
        ts_errors = list(ts_payload.get("parse_errors", []))
    else:
        ts_errors = []

    # ---- coverage (honest; never synthesized)
    coverage_entries = [
        CoverageEntry(
            extractor=PY_EXTRACTOR,
            status=CoverageStatus.COMPLETE if not py_errors else CoverageStatus.PARTIAL,
            required=True,
            diagnostics=tuple(py_errors[:16]),
        ),
    ]
    if ts_roots:
        if ts_payload:
            coverage_entries.append(
                CoverageEntry(
                    extractor=TS_EXTRACTOR,
                    status=(
                        CoverageStatus.COMPLETE
                        if not ts_errors
                        else CoverageStatus.PARTIAL
                    ),
                    required=True,
                    diagnostics=tuple(ts_errors[:16]),
                )
            )
        else:
            coverage_entries.append(
                CoverageEntry(
                    extractor=TS_EXTRACTOR,
                    status=CoverageStatus.UNAVAILABLE,
                    required=True,
                    diagnostics=(ts_diag or "typescript collector produced no payload",),
                )
            )

    # ---- survey assembly
    all_facts = py_facts
    all_scanned = sorted(set(py_scanned) | set(outcome.scanned_files))
    source_aggregate = "\n".join(f"{rel}\n{dg}" for rel, dg in sorted(all_scanned))
    survey = ArchitectureSurvey(
        schema_version=contract.schema_version,
        scope=";".join(list(py_roots) + list(ts_roots)),
        coverage=tuple(coverage_entries),
        facts=tuple(fact_from_dict(f) for f in all_facts),
        source_digest="sha256:" + hashlib.sha256(source_aggregate.encode("utf-8")).hexdigest(),
        parse_errors=tuple(py_errors),
        excluded_roots=tuple(sorted(_excluded_roots(repo, py_roots + ts_roots))),
        wrapper_summaries=to_wrapper_summaries(registry),
        repository_state=_git_state(repo),
        run_metadata={
            "tool_version": "1.0.0",
            "extractor_versions": {PY_EXTRACTOR: "1", TS_EXTRACTOR: "1"},
            "generated_at": "collector",
        },
    )
    validate_survey(survey)
    outcome.survey = survey
    outcome.audit = reconcile(contract, survey)
    outcome.facts = all_facts
    outcome.scanned_files = all_scanned
    outcome.parse_errors = py_errors

    assessment = outcome.audit.content.assessment
    outcome.summary = {
        "assessment": assessment.status.value,
        "gate_eligible": assessment.gate_eligible,
        "reasons": list(assessment.reasons),
        "finding_counts": {
            status: sum(
                1 for f in outcome.audit.content.findings if f.rule_status.value == status
            )
            for status in ("satisfied", "violated", "unresolved", "planned_gap", "not_evaluated")
        },
        "facts": len(all_facts),
        "scanned_files": len(all_scanned),
        "coverage": [c.to_dict() for c in survey.coverage],
        "survey_digest": outcome.audit.content.bound_survey_digest,
    }
    return outcome


def _excluded_roots(repo: Path, roots: tuple[str, ...]) -> list[str]:
    from paperforge.architecture_audit.collectors.common import (
        EXCLUDED_DIR_NAMES,
        EXCLUDED_FILE_NAMES,
        EXCLUDED_FILE_SUFFIXES,
    )

    found: set[str] = set()
    for root_rel in roots:
        root = repo / root_rel
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
                found.add(str(rel.parts[0]))
            elif path.suffix in EXCLUDED_FILE_SUFFIXES or path.name in EXCLUDED_FILE_NAMES:
                found.add(path.name)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paperforge-architecture-collect",
        description="Deterministic architecture collector (#133) — maintainer tool.",
    )
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--contract", required=True, help="contract.json path")
    parser.add_argument("--out", required=True, help="output directory (survey/audit/summary)")
    parser.add_argument("--node", default="node", help="node executable (default: node)")
    parser.add_argument(
        "--py-roots", nargs="*", default=list(DEFAULT_PY_ROOTS), help="python source roots"
    )
    parser.add_argument(
        "--ts-roots", nargs="*", default=list(DEFAULT_TS_ROOTS), help="typescript source roots"
    )
    parser.add_argument("--python-registry", default="", help="extra wrapper registry JSON")
    args = parser.parse_args(argv)

    repo = Path(args.root).resolve()
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = repo / contract_path
    contract = ArchitectureContract.from_dict(
        json.loads(contract_path.read_text(encoding="utf-8"))
    )
    registry: tuple[WrapperSpec, ...] = load_default_python_registry()
    if args.python_registry:
        reg_path = Path(args.python_registry)
        if not reg_path.is_absolute():
            reg_path = repo / reg_path
        registry = load_wrapper_registry(
            json.loads(reg_path.read_text(encoding="utf-8"))
        )

    outcome = collect(
        repo,
        contract=contract,
        py_roots=tuple(args.py_roots),
        ts_roots=tuple(args.ts_roots),
        node_cmd=args.node,
        python_registry=registry,
    )

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = repo / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "survey.json").write_text(
        json.dumps(outcome.survey.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "audit.json").write_text(
        json.dumps(outcome.audit.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(
        json.dumps(outcome.summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    s = outcome.summary
    print(
        f"assessment={s['assessment']} gate={s['gate_eligible']} "
        f"facts={s['facts']} scanned={s['scanned_files']} "
        f"reasons={','.join(s['reasons'])}"
    )
    for diag in outcome.diagnostics:
        print(f"diagnostic: {diag}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
