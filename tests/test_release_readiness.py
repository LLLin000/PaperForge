"""#265 I4: the release-evidence validator (failure-first)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "release_readiness", REPO / "scripts" / "release_readiness.py"
)
rr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(rr)

SHA = "a" * 40
WHEEL = "b" * 64
CANDIDATE = {"source_sha": SHA, "version": "2.0.0", "wheel_sha256": WHEEL}
MATRIX = [
    {
        "capability_id": "A06",
        "host_profile": "P0",
        "required_layer": "H",
        "applicability": "required",
        "cases": ["A06"],
    }
]


def record(**overrides):
    base = {
        "case_id": "A06",
        "status": "pass",
        "source_sha": SHA,
        "host_profile": "P0",
        "runner_kind": "owner-machine",
        "artifacts": {"wheel_sha256": WHEEL},
        "occurred_at": "2026-10-18T00:00:00Z",
    }
    base.update(overrides)
    return base


def decide(matrix, records, candidate=CANDIDATE):
    return rr.evaluate(candidate, matrix, records)


def test_eligible_with_matching_evidence():
    result = decide(MATRIX, {"A06": [record()]})
    assert result["content"]["verdict"] == "eligible"
    assert result["content"]["cells"][0]["decision"] == "VERIFIED"


def test_old_candidate_sha_is_incomplete():
    result = decide(MATRIX, {"A06": [record(source_sha="c" * 40)]})
    assert result["content"]["verdict"] == "incomplete"
    assert "does not match" in result["content"]["cells"][0]["reason"]


def test_missing_required_case_is_incomplete():
    result = decide(MATRIX, {})
    assert result["content"]["verdict"] == "incomplete"
    assert "no evidence file" in result["content"]["cells"][0]["reason"]


def test_skipped_is_not_passed():
    result = decide(MATRIX, {"A06": [record(status="skipped")]})
    assert result["content"]["cells"][0]["decision"] == "UNTESTED"


def test_pass_with_timeout_step_is_not_a_pass():
    history = [
        record(
            status="pass",
            verdict="pass",
            steps=[
                {"id": "installation", "status": "pass"},
                {"id": "probe_all", "status": "timeout"},
            ],
        )
    ]
    result = decide(MATRIX, {"A06": history})
    assert result["content"]["cells"][0]["decision"] == "UNTESTED"
    assert "probe_all" in result["content"]["cells"][0]["reason"]


def test_cli_only_evidence_cannot_prove_host_layer():
    result = decide(MATRIX, {"A06": [record(runner_kind="harness_cli")]})
    assert result["content"]["cells"][0]["decision"] == "UNTESTED"
    assert "layer H" in result["content"]["cells"][0]["reason"]


def test_first_failure_is_kept_and_r9_blocks_retry_green():
    history = [
        record(status="fail", occurred_at="2026-10-17T00:00:00Z"),
        record(status="pass", occurred_at="2026-10-18T00:00:00Z"),
    ]
    result = decide(MATRIX, {"A06": history})
    cell = result["content"]["cells"][0]
    assert cell["decision"] == "UNTESTED"
    assert "R9" in cell["reason"]
    assert cell["evidence"][0]["first_failure"]["occurred_at"] == "2026-10-17T00:00:00Z"


def test_not_applicable_needs_reason_and_is_not_verified():
    without = decide(
        [{**MATRIX[0], "applicability": "not_applicable"}], {"A06": [record()]}
    )
    assert without["content"]["cells"][0]["decision"] == "UNDEFINED"
    with_reason = decide(
        [
            {
                **MATRIX[0],
                "applicability": "not_applicable",
                "reason": "ARM64 is outside the declared support set",
            }
        ],
        {"A06": [record()]},
    )
    assert with_reason["content"]["cells"][0]["decision"] == "NOT_APPLICABLE"
    assert with_reason["content"]["verdict"] != "eligible"


def test_duplicate_records_use_the_last_and_report_history():
    history = [
        record(status="pass", occurred_at="2026-10-17T00:00:00Z"),
        record(status="pass", occurred_at="2026-10-18T00:00:00Z"),
    ]
    result = decide(MATRIX, {"A06": history})
    assert result["content"]["cells"][0]["evidence"][0]["records"] == 2
    assert result["content"]["verdict"] == "eligible"


def test_tampered_evidence_is_rejected():
    result = decide(MATRIX, {"A06": [{"__invalid__": "A06.json is not valid JSON"}]})
    assert result["content"]["cells"][0]["decision"] == "UNTESTED"
    assert "invalid evidence" in result["content"]["cells"][0]["reason"]


def test_evidence_for_another_profile_does_not_fill_a_cell():
    matrix = [dict(MATRIX[0], host_profile="P1")]
    result = decide(matrix, {"A06": [record(host_profile="P0")]})
    cell = result["content"]["cells"][0]
    assert cell["decision"] == "UNTESTED"
    assert "does not match cell profile" in cell["reason"]


def test_undeclared_profile_is_undefined_not_inherited():
    extra = dict(record(host_profile="P2"))
    result = decide(MATRIX, {"A06": [record()], "B01": [extra]})
    assert "P2" in result["content"]["undefined_profiles"]


def test_content_hash_is_recomputable_and_time_stable():
    first = decide(MATRIX, {"A06": [record()]})
    second = decide(MATRIX, {"A06": [record()]})
    assert first["content_sha256"] == second["content_sha256"]
    assert "generated_at" not in first["content"]


@pytest.mark.parametrize(
    "mutation",
    [
        {"source_sha": None},
        {"artifacts": {"wheel_sha256": "d" * 64}},
    ],
)
def test_identity_defects_are_incomplete(mutation):
    result = decide(MATRIX, {"A06": [record(**mutation)]})
    assert result["content"]["verdict"] == "incomplete"
