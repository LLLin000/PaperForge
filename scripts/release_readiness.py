"""Minimal release-evidence validator (#265 I4).

Judges whether the *existing* evidence supports a release claim for a candidate.
It never runs tests and never writes into the evidence archive: report-only.

Inputs
------
candidate.json
    {"source_sha", "version", "wheel_sha256", "bundle_sha256"?, "plugin_version"?}
matrix.json
    [{"capability_id", "host_profile", "required_layer", "applicability":
      "required"|"not_applicable", "reason"?, "cases": ["<CASE_ID>", ...]}]
evidence/
    one `<CASE_ID>.json` per case, each an **append array** of records
    (standard 6).  Consumers use the last record; the first failure is kept.

Decision vocabulary (standard R4, plus the two evidence states of the task book):
    VERIFIED | UNTESTED | NOT_APPLICABLE | UNDEFINED

Rules implemented:
  * identity match: source_sha must equal the candidate's; a release claim also
    needs an artifact hash (wheel or bundle) equal to the candidate's;
  * skip/timeout/PASS_WITH_WARNINGS/unknown records never count as verified - a
    `steps` array is inspected, so a top-level PASS carrying a timed-out step
    does not pass;
  * a CLI-only evidence kind (harness_cli) cannot satisfy an H/V requirement;
  * a failure before a green rerun keeps the cell UNTESTED (standard R9);
  * not_applicable needs a reason and is never "passed";
  * a profile seen only outside the matrix is UNDEFINED, never inherited.

Exit code: 0 eligible, 1 not eligible (report still written), 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA = "paperforge.release-readiness/1"
HOST_RUNNERS = {"hosted", "owner-vm", "owner-machine"}
PASSING_STEP = {"pass", "ok", "verified", "success"}


def _record_identity_ok(record: dict, candidate: dict) -> tuple[bool, str]:
    sha = record.get("source_sha")
    if not sha:
        return False, "record has no source_sha"
    if sha != candidate.get("source_sha"):
        return False, f"source_sha {str(sha)[:12]}... does not match the candidate"
    wanted = {
        "wheel_sha256": candidate.get("wheel_sha256"),
        "bundle_sha256": candidate.get("bundle_sha256"),
    }
    claimed = {k: v for k, v in wanted.items() if v}
    if not claimed:
        return False, "candidate carries no artifact hash"
    artifacts = record.get("artifacts") or {}
    if not any(artifacts.get(k) == v for k, v in claimed.items()):
        return False, "record artifacts do not match the candidate"
    return True, ""


PASSING_STATUS = {"pass", "passed", "verified", "success", "ok"}


def _record_passed(record: dict) -> tuple[bool, str]:
    # Fail-closed allowlist: anything not explicitly a pass (fail, skipped,
    # timeout, unknown, error, PASS_WITH_WARNINGS, a missing status) is not one.
    status = str(record.get("status", "")).strip().lower()
    if status not in PASSING_STATUS:
        return False, f"status {status or '(missing)'}"
    steps = record.get("steps")
    if isinstance(steps, list):
        bad = [
            s.get("id") or s.get("name") or "?"
            for s in steps
            if str(s.get("status", "")).strip().lower() not in PASSING_STEP
        ]
        if bad:
            return False, f"steps not passing: {', '.join(map(str, bad[:4]))}"
    if str(record.get("verdict", "")).lower() not in {"", "pass", "verified", "success"}:
        return False, f"verdict {record.get('verdict')}"
    return True, ""


def _layer_ok(record: dict, required_layer: str) -> tuple[bool, str]:
    runner = str(record.get("runner_kind", "")).strip()
    if required_layer.upper() in {"H", "V"} and runner not in HOST_RUNNERS:
        return False, f"runner_kind {runner or '(missing)'} cannot prove layer {required_layer}"
    return True, ""


def _load_evidence(evidence_dir: Path) -> dict[str, list[dict]]:
    files: dict[str, list[dict]] = {}
    if not evidence_dir.is_dir():
        return files
    for path in sorted(evidence_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            files[path.stem] = [{"__invalid__": f"{path.name} is not valid JSON"}]
            continue
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            files[path.stem] = [{"__invalid__": f"{path.name} is not an evidence array"}]
            continue
        files[path.stem] = [r for r in payload if isinstance(r, dict)]
    return files


def judge_cell(candidate: dict, row: dict, records: dict[str, list[dict]]) -> dict:
    cell = {
        "capability_id": row.get("capability_id"),
        "host_profile": row.get("host_profile"),
        "required_layer": row.get("required_layer"),
    }
    if row.get("applicability") == "not_applicable":
        if not row.get("reason"):
            return {**cell, "decision": "UNDEFINED", "reason": "not_applicable without a reason"}
        return {**cell, "decision": "NOT_APPLICABLE", "reason": row["reason"], "evidence": []}

    cases = list(row.get("cases") or [])
    if not cases:
        return {**cell, "decision": "UNDEFINED", "reason": "no evidence case declared"}

    refs: list[dict] = []
    failures: list[str] = []
    for case in cases:
        history = records.get(case)
        if not history:
            failures.append(f"{case}: no evidence file")
            continue
        invalid = [r for r in history if "__invalid__" in r]
        if invalid:
            failures.append(f"{case}: invalid evidence ({invalid[0]['__invalid__']})")
            continue
        first_fail = next(
            (
                r
                for r in history
                if not (_record_passed(r)[0] and _record_identity_ok(r, candidate)[0])
            ),
            None,
        )
        last = history[-1]
        refs.append(
            {
                "case": case,
                "records": len(history),
                "last_status": last.get("status"),
                "evidence_file": f"{case}.json",
                "first_failure": None
                if first_fail is None
                else {
                    "status": first_fail.get("status"),
                    "source_sha": first_fail.get("source_sha"),
                    "occurred_at": first_fail.get("occurred_at"),
                },
            }
        )
        ok, why = _record_identity_ok(last, candidate)
        if not ok:
            failures.append(f"{case}: {why}")
            continue
        ok, why = _record_passed(last)
        if not ok:
            failures.append(f"{case}: {why}")
            continue
        ok, why = _layer_ok(last, str(row.get("required_layer") or ""))
        if not ok:
            failures.append(f"{case}: {why}")
            continue
        # A record states the profile it ran on; a cell is never filled by
        # evidence from another profile (no implicit P0 inheritance).
        record_profile = last.get("host_profile")
        if not isinstance(record_profile, str) or record_profile != row.get("host_profile"):
            failures.append(
                f"{case}: evidence profile {record_profile!r} does not match cell profile {row.get('host_profile')!r}"
            )
            continue
        if first_fail is not None and first_fail is not last:
            failures.append(f"{case}: R9 - green only after a failure, first failure kept")
            continue

    if failures:
        return {**cell, "decision": "UNTESTED", "reason": "; ".join(failures), "evidence": refs}
    return {**cell, "decision": "VERIFIED", "reason": "", "evidence": refs}


def evaluate(candidate: dict, matrix: list[dict], records: dict[str, list[dict]]) -> dict:
    cells = [judge_cell(candidate, row, records) for row in matrix]
    required = [c for c in cells if c["decision"] != "NOT_APPLICABLE"]
    verified = [c for c in cells if c["decision"] == "VERIFIED"]
    if any(c["decision"] == "UNTESTED" for c in required):
        verdict = "incomplete"
    elif required and all(c["decision"] == "VERIFIED" for c in required):
        verdict = "eligible"
    else:
        verdict = "not_decided"
    declared = sorted({c["host_profile"] for c in verified})
    seen = set()
    for history in records.values():
        for record in history:
            profile = record.get("host_profile")
            if isinstance(profile, str):
                seen.add(profile)
    matrix_profiles = {row.get("host_profile") for row in matrix if row.get("host_profile")}
    content = {
        "schema": SCHEMA,
        "candidate": candidate,
        "verdict": verdict,
        "cells": cells,
        "declared_support_profiles": declared,
        "undefined_profiles": sorted(seen - matrix_profiles),
    }
    digest = hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {"content": content, "content_sha256": digest}


def render_markdown(result: dict) -> str:
    content = result["content"]
    lines = [
        "# Release readiness (report-only)",
        "",
        f"- candidate: `{str(content['candidate'].get('source_sha', ''))[:12]}...` "
        f"v{content['candidate'].get('version', '?')}",
        f"- verdict: **{content['verdict']}**",
        f"- content sha256: `{result['content_sha256']}`",
        "",
        "| capability | profile | layer | decision | reason |",
        "|---|---|---|---|---|",
    ]
    for cell in content["cells"]:
        lines.append(
            f"| {cell['capability_id']} | {cell['host_profile']} | "
            f"{cell['required_layer']} | {cell['decision']} | {cell['reason'] or ''} |"
        )
    lines += [
        "",
        "- declared support profiles: "
        + (", ".join(content["declared_support_profiles"]) or "(none)"),
        "- undefined profiles: " + (", ".join(content["undefined_profiles"]) or "(none)"),
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="release evidence validator (report-only)")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=Path("release-readiness.json"))
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"cannot read inputs: {error}", file=sys.stderr)
        return 2
    if not isinstance(matrix, list):
        print("matrix must be a JSON array", file=sys.stderr)
        return 2
    result = evaluate(candidate, matrix, _load_evidence(args.evidence))
    payload = {"generated_at": None, **result["content"], "content_sha256": result["content_sha256"]}
    args.out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.report:
        args.report.write_text(render_markdown(result), encoding="utf-8")
    print(f"verdict={result['content']['verdict']} content_sha256={result['content_sha256'][:16]}...")
    return 0 if result["content"]["verdict"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
