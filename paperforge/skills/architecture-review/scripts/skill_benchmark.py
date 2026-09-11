#!/usr/bin/env python3
"""Run the architecture-review Skill benchmark corpus.

Fixture cases are executable against the deterministic audit. Historical cases
are retained as issue-grounded prompts until a replay fixture exists; they are
reported as ``not_run`` rather than guessed. Optional v1/v2 answer artifacts
are evaluated only for the fields they actually record, so this tool never
invents model quality, tool-use, token, or timing measurements.

Answer artifact shape::

    {"cases": {
      "case-id": {
        "valid_emission": true,
        "fabricated_evidence_ids": 0,
        "cross_scope_evidence": 0,
        "typed_trace_complete": true,
        "files_opened": 4,
        "tool_calls": 7,
        "input_tokens": 1200,
        "output_tokens": 600,
        "wall_time_ms": 9000
      }
    }}

The quality fields are optional individually, but absent values remain absent
from aggregates. A supplied artifact is therefore evidence of only what it
records, not a license to infer the rest.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from paperforge.architecture_audit import reconcile
from paperforge.architecture_audit.fixtures import FIXTURE_NAMES, load_fixture

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "references" / "benchmark-cases.json"
ANSWER_BOOLEAN_FIELDS = ("valid_emission", "typed_trace_complete")
ANSWER_COUNT_FIELDS = (
    "fabricated_evidence_ids",
    "cross_scope_evidence",
    "files_opened",
    "tool_calls",
    "input_tokens",
    "output_tokens",
    "wall_time_ms",
)


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    """Load and validate the benchmark manifest before executing any case."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("benchmark manifest schema_version must be 1")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark manifest cases must be a non-empty list")
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("benchmark case must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen:
            raise ValueError(f"benchmark case_id must be unique and non-empty: {case_id!r}")
        seen.add(case_id)
        fixture = case.get("fixture")
        if fixture is not None and fixture not in FIXTURE_NAMES:
            raise ValueError(f"benchmark case {case_id!r} names unknown fixture {fixture!r}")
        if fixture is None and case.get("kind") != "historical_incident":
            raise ValueError(f"benchmark case {case_id!r} without fixture must be historical_incident")
        if fixture is not None:
            expected = case.get("expected_findings")
            if not isinstance(expected, list):
                raise ValueError(f"fixture case {case_id!r} needs expected_findings")
    return payload


def _finding_snapshot(audit: Any) -> list[dict[str, str]]:
    return sorted(
        (
            {
                "rule_id": finding.rule_id,
                "status": finding.rule_status.value,
                "subject": finding.subject,
            }
            for finding in audit.content.findings
        ),
        key=lambda row: (row["rule_id"], row["status"], row["subject"]),
    )


def _expected_snapshot(case: Mapping[str, Any]) -> list[dict[str, str]]:
    return sorted(
        (
            {
                "rule_id": item["rule_id"],
                "status": item["status"],
            }
            for item in case["expected_findings"]
        ),
        key=lambda row: (row["rule_id"], row["status"]),
    )


def run_deterministic_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """Execute one fixture case or explicitly preserve a historical gap."""
    case_id = case["case_id"]
    fixture = case.get("fixture")
    if fixture is None:
        return {
            "case_id": case_id,
            "kind": case["kind"],
            "status": "not_run",
            "reason": "historical incident has no replay fixture; answer evaluation remains separate",
            "source_issue": case.get("source_issue"),
        }

    contract, survey = load_fixture(fixture)
    audit = reconcile(contract, survey)
    actual = _finding_snapshot(audit)
    expected = _expected_snapshot(case)
    actual_keys = [
        {"rule_id": finding["rule_id"], "status": finding["status"]}
        for finding in actual
    ]
    problems: list[str] = []
    if actual_keys != expected:
        problems.append(f"findings mismatch: expected {expected!r}, got {actual_keys!r}")
    expected_assessment = case.get("expected_assessment")
    actual_assessment = audit.content.assessment.status.value
    if expected_assessment is not None and expected_assessment != actual_assessment:
        problems.append(
            f"assessment mismatch: expected {expected_assessment!r}, got {actual_assessment!r}"
        )
    return {
        "case_id": case_id,
        "kind": case["kind"],
        "fixture": fixture,
        "status": "pass" if not problems else "fail",
        "problems": problems,
        "findings": actual,
        "assessment": actual_assessment,
        "gate_eligible": audit.content.assessment.gate_eligible,
    }


def _answer_records(payload: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        raise ValueError("answer artifact must be a JSON object")
    records = payload.get("cases")
    if isinstance(records, Mapping):
        result = dict(records)
    elif isinstance(records, list):
        result = {}
        for record in records:
            if not isinstance(record, Mapping) or not isinstance(record.get("case_id"), str):
                raise ValueError("answer list entries need a string case_id")
            result[record["case_id"]] = record
    else:
        raise ValueError("answer artifact cases must be an object or list")
    for case_id, record in result.items():
        if not isinstance(case_id, str) or not isinstance(record, Mapping):
            raise ValueError("answer artifact case records must be objects")
    return result


def _numeric_values(records: Mapping[str, Mapping[str, Any]], field: str) -> list[int | float]:
    values: list[int | float] = []
    for record in records.values():
        value = record.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            continue
        values.append(value)
    return values


def summarize_answers(
    path: str | Path | None,
    known_case_ids: set[str],
    *,
    label: str,
) -> dict[str, Any]:
    """Summarize one answer artifact without imputing missing measurements."""
    if path is None:
        return {
            "label": label,
            "status": "not_run",
            "reason": "answer artifact not supplied",
        }
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = _answer_records(payload)
    unknown = sorted(set(records) - known_case_ids)
    if unknown:
        raise ValueError(f"{label} answer artifact has unknown case IDs: {unknown}")
    metrics: dict[str, Any] = {}
    valid_values = [record["valid_emission"] for record in records.values() if isinstance(record.get("valid_emission"), bool)]
    if valid_values:
        metrics["valid_emission_rate"] = sum(valid_values) / len(valid_values)
    trace_values = [record["typed_trace_complete"] for record in records.values() if isinstance(record.get("typed_trace_complete"), bool)]
    if trace_values:
        metrics["typed_trace_completion_rate"] = sum(trace_values) / len(trace_values)
    for field in ("fabricated_evidence_ids", "cross_scope_evidence"):
        values = _numeric_values(records, field)
        if values:
            metrics[f"{field}_cases"] = sum(value > 0 for value in values)
            metrics[f"{field}_total"] = sum(values)
    for field in ("files_opened", "tool_calls", "input_tokens", "output_tokens", "wall_time_ms"):
        values = _numeric_values(records, field)
        if values:
            metrics[f"median_{field}"] = statistics.median(values)
    missing_record_fields = {
        case_id: [field for field in (*ANSWER_BOOLEAN_FIELDS, *ANSWER_COUNT_FIELDS) if field not in record]
        for case_id, record in records.items()
    }
    incomplete = {case_id: fields for case_id, fields in missing_record_fields.items() if fields}
    return {
        "label": label,
        "status": "observed",
        "cases_provided": len(records),
        "metrics": metrics,
        "incomplete_records": incomplete,
    }


def _compare_runs(v1: Mapping[str, Any], v2: Mapping[str, Any]) -> dict[str, Any]:
    left = v1.get("metrics", {})
    right = v2.get("metrics", {})
    numeric = sorted(set(left).intersection(right))
    return {key: right[key] - left[key] for key in numeric if isinstance(left[key], (int, float)) and isinstance(right[key], (int, float))}


def run_benchmark(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    *,
    answers_v1: str | Path | None = None,
    answers_v2: str | Path | None = None,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    outcomes = [run_deterministic_case(case) for case in manifest["cases"]]
    executable = [outcome for outcome in outcomes if "fixture" in outcome]
    deterministic = {
        "cases": len(executable),
        "passed": sum(outcome["status"] == "pass" for outcome in executable),
        "failed": sum(outcome["status"] == "fail" for outcome in executable),
        "historical_not_run": sum(outcome["status"] == "not_run" for outcome in outcomes),
        "outcomes": outcomes,
    }
    known_case_ids = {case["case_id"] for case in manifest["cases"]}
    v1 = summarize_answers(answers_v1, known_case_ids, label="v1")
    v2 = summarize_answers(answers_v2, known_case_ids, label="v2")
    result: dict[str, Any] = {
        "schema_version": 1,
        "manifest": str(Path(manifest_path)),
        "deterministic": deterministic,
        "skill_runs": {"v1": v1, "v2": v2},
    }
    if v1.get("status") == "observed" and v2.get("status") == "observed":
        result["comparison"] = _compare_runs(v1, v2)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the architecture-review benchmark corpus")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--answers-v1")
    parser.add_argument("--answers-v2")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        result = run_benchmark(args.manifest, answers_v1=args.answers_v1, answers_v2=args.answers_v2)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    print(payload)
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    return 0 if result["deterministic"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
