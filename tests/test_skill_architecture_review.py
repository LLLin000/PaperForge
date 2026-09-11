"""#132 Slice B — architecture-review Skill process evals.

Tests the review process machinery the Skill drives, plus the Skill document's
own contracts. Process evals assert predictability, not prose: validated-input
first, digest/reconciler-version binding, epistemic labeling, finding-ID
integrity, adjudication completeness, and the eight-stage trace completion —
evidence relevance, typed stage states, and bounded review planning.
"""
from __future__ import annotations

from dataclasses import replace
import json
import sys
from pathlib import Path

import pytest

from paperforge.architecture_audit import (
    SCHEMA_VERSION,
    ArchitectureReview,
    reconcile,
)
from paperforge.architecture_audit.fixtures import load_fixture

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "paperforge" / "skills" / "architecture-review"
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
import review_harness as rh  # noqa: E402
import skill_benchmark as sb  # noqa: E402

# ---------------------------------------------------------------- helpers


def _audit(fixture: str):
    contract, survey = load_fixture(fixture)
    audit = reconcile(contract, survey)
    context = rh.load_bound_context(fixture=fixture, audit=audit)
    return audit, survey, context

def _make_review(audit, adjudications=(), semantic=(), requests=(), reviewer_type="test-reviewer") -> ArchitectureReview:
    return ArchitectureReview.from_dict({
        "schema_version": SCHEMA_VERSION,
        "reviewer_type": reviewer_type,
        "contract_digest": audit.content.bound_contract_digest,
        "survey_digest": audit.content.bound_survey_digest,
        "audit_digest": audit.semantic_digest,
        "reconciler_version": audit.content.reconciler_version,
        "adjudications": list(adjudications),
        "semantic_findings": list(semantic),
        "evidence_requests": list(requests),
        "rationale": "test review",
        "run_metadata": {"model": "test-model", "created_at": "2026-08-05T00:00:00Z"},
    })


def _adjudication(finding_id: str, kind: str = "needs_evidence", status: str = "unresolved") -> dict:
    return {
        "finding_id": finding_id,
        "adjudication": kind,
        "rationale": "traced through the evidence chain",
        "epistemic_status": status,
    }


def _index(survey) -> dict[str, dict]:
    return rh.evidence_index_from_survey(survey)


def _full_trace(operations, evidence_index=None) -> dict:
    """A typed eight-stage trace using only operation/stage candidates."""
    evidence_index = evidence_index or {}
    trace = {}
    for operation in operations:
        stages = {}
        for stage in rh.TRACE_STAGES:
            candidates = sorted(
                evidence_id
                for evidence_id, metadata in evidence_index.items()
                if operation in metadata.get("operation_ids", ())
                and stage in metadata.get("stages", ())
            )
            stages[stage] = (
                {"status": "observed", "evidence_ids": candidates}
                if candidates
                else {
                    "status": "needs_evidence",
                    "question": f"Which source path proves {operation}.{stage}?",
                }
            )
        trace[operation] = stages
    return trace


def _adjudicate_all(audit) -> list[dict]:
    return [_adjudication(f.finding_id) for f in rh.required_findings(audit)]


# ---------------------------------------------------------------- process: validated input first


class TestValidatedInputFirst:
    def test_audit_loads_fixture_and_prints_bindings(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        summary = rh.audit_summary(audit, context)
        assert summary["audit_digest"] == audit.semantic_digest
        assert summary["reconciler_version"] == audit.content.reconciler_version
        # T9 (#170): publication.authority is blocking + UNRESOLVED →
        # INCOMPLETE, gate not green (unresolved dynamic callsites).
        assert summary["assessment"]["status"] == "incomplete"
        assert summary["assessment"]["gate_eligible"] is False
        assert summary["scope"] == ["embed_build_resume", "memory_build", "ocr_rebuild"]
        assert len(summary["must_adjudicate"]) == 1  # publication.authority unresolved
        assert summary["evidence_candidates"]["ocr_rebuild"]["side_effects"]
    def test_clean_audit_scope_uses_contract_operations(self):
        contract, survey = load_fixture("golden_126_ocr_rebuild")
        clean_contract = replace(contract, rules=())
        audit = reconcile(clean_contract, survey)
        context = rh.BoundReviewContext(clean_contract, survey)
        assert not audit.content.findings
        assert rh.scope(audit, context) == ["embed_build_resume", "memory_build", "ocr_rebuild"]

    def test_refuses_invalid_audit_input(self):
        with pytest.raises((OSError, ValueError)):
            rh.load_audit(audit_path=str(REPO_ROOT / "missing-audit.json"))

    def test_refuses_unknown_schema_version(self, tmp_path):
        audit, _, _ = _audit("golden_126_ocr_rebuild")
        payload = audit.to_dict()
        payload["schema_version"] = 999
        path = tmp_path / "bad_audit.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(Exception, match="schema_version"):
            rh.load_audit(audit_path=str(path))


# ---------------------------------------------------------------- process: branches


class TestBranches:
    def test_full_survey_golden126_all_edges_adjudicated(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        assert rh.validate_emission(audit, review, trace, context) == []

    def test_full_survey_golden127_and_129(self):
        for fixture in ("golden_127_sync_embed", "golden_129_display_restore"):
            audit, survey, context = _audit(fixture)
            review = _make_review(audit, adjudications=_adjudicate_all(audit))
            trace = _full_trace(rh.scope(audit, context), _index(survey))
            assert rh.validate_emission(audit, review, trace, context) == []

    def test_focused_signal_branch_synthetic_unmatched_signal(self):
        audit, survey, context = _audit("synthetic_unmatched_signal")
        assert rh.scope(audit, context) == ["ocr_rebuild", "probe_status", "sync"]
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        assert rh.validate_emission(audit, review, trace, context) == []

    def test_changed_interface_branch_publication_bypass(self):
        audit, survey, context = _audit("synthetic_publication_bypass")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        assert rh.validate_emission(audit, review, trace, context) == []

    def test_operations_narrowing_covers_exactly_declared_operations(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(["embed_build_resume"], _index(survey))
        problems = rh.validate_emission(
            audit, review, trace, context, operations=["embed_build_resume"]
        )
        assert problems == []


# ---------------------------------------------------------------- process: refusal


class TestRefusal:
    def test_refuses_digest_mismatch(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        other, _, _ = _audit("golden_127_sync_embed")
        stale = _make_review(
            other,
            adjudications=[_adjudication(f.finding_id) for f in rh.required_findings(audit)],
        )
        problems = rh.validate_emission(audit, stale, None, context)
        assert any("not bound" in p or "digest" in p for p in problems)

    def test_refuses_reconciler_version_mismatch(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        review = ArchitectureReview.from_dict({**review.to_dict(), "reconciler_version": "9.9.9"})
        problems = rh.validate_emission(audit, review, None, context)
        assert any("reconciler_version" in p for p in problems)

    def test_refuses_bound_context_digest_mismatch(self):
        audit, _, _ = _audit("golden_126_ocr_rebuild")
        with pytest.raises(rh.ArchitectureError, match="not bound"):
            rh.load_bound_context(fixture="golden_127_sync_embed", audit=audit)

    def test_refuses_observed_static_claims(self):
        audit, _, context = _audit("synthetic_publication_bypass")
        review = _make_review(
            audit,
            adjudications=[
                _adjudication(f.finding_id, status="observed_static")
                for f in rh.required_findings(audit)
            ],
        )
        problems = rh.validate_emission(audit, review, None, context)
        assert any("epistemic" in p for p in problems)

    def test_refuses_fabricated_finding_id(self):
        audit, _, context = _audit("synthetic_publication_bypass")
        review = _make_review(audit, adjudications=[_adjudication("finding:deadbeef")])
        problems = rh.validate_emission(audit, review, None, context)
        assert any("unknown finding_id" in p for p in problems)

    def test_refuses_missing_adjudication(self):
        audit, _, context = _audit("synthetic_publication_bypass")
        review = _make_review(audit)
        problems = rh.validate_emission(audit, review, None, context)
        assert any("no adjudication" in p for p in problems)

    def test_refuses_semantic_finding_collision(self):
        audit, _, context = _audit("synthetic_publication_bypass")
        finding = rh.required_findings(audit)[0]
        review = _make_review(
            audit,
            adjudications=_adjudicate_all(audit),
            semantic=[{
                "finding_id": finding.finding_id,
                "message": "collision",
                "epistemic_status": "inferred",
            }],
        )
        problems = rh.validate_emission(audit, review, None, context)
        assert any("collides" in p for p in problems)

    def test_refuses_empty_reviewer_type(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit), reviewer_type=" ")
        problems = rh.validate_emission(audit, review, None, context)
        assert any("reviewer_type" in p for p in problems)

    def test_refuses_incomplete_coverage_audit_for_review(self):
        """partial coverage yields incomplete assessment; emit still binds and
        adjudicates the violated coverage finding — no silent all-clear."""
        audit, survey, context = _audit("synthetic_partial_coverage")
        assert audit.content.assessment.status.value == "incomplete"
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        assert rh.validate_emission(audit, review, trace, context) == []

    def test_refuses_emission_without_trace_manifest(self):
        """trace is the completion invariant — an overlay without a scoped
        trace must never be accepted."""
        audit, _, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        problems = rh.validate_emission(audit, review, None, context)
        assert any("trace manifest required" in p for p in problems)

    def test_refuses_emission_without_bound_context(self):
        """saved audit metadata cannot substitute for Contract + Survey context."""
        audit, _, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), context.evidence_index)
        problems = rh.validate_emission(audit, review, trace, None)
        assert any("bound review context" in p for p in problems)

    def test_saved_metadata_cannot_change_review_scope(self, tmp_path):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        payload = audit.to_dict()
        payload["run_metadata"] = {
            "operation_scope": ["not_an_operation"],
            "evidence_index": {"evidence:forged": {"operation_ids": ["not_an_operation"]}},
        }
        path = tmp_path / "tampered-audit.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        tampered = rh.load_audit(audit_path=str(path))
        bound = rh.load_bound_context(fixture="golden_126_ocr_rebuild", audit=tampered)
        plan = rh.build_review_plan(tampered, bound, mode="full-release")
        assert plan["scope"] == rh.scope(audit, context)
        assert "evidence:forged" not in json.dumps(plan)


# ---------------------------------------------------------------- process: trace completion


class TestTraceCompletion:
    def test_missing_stage_fails(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        del trace["ocr_rebuild"]["failure"]
        problems = rh.validate_emission(audit, review, trace, context)
        assert any("missing stage failure" in p for p in problems)

    def test_typed_empty_stage_fails(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        trace["ocr_rebuild"]["side_effects"] = {
            "status": "observed",
            "evidence_ids": [],
        }
        problems = rh.validate_emission(audit, review, trace, context)
        assert any("observed requires non-empty evidence_ids" in p for p in problems)

    def test_unknown_evidence_fails(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        index = _index(survey)
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), index)
        trace["ocr_rebuild"]["side_effects"] = {
            "status": "observed",
            "evidence_ids": ["evidence:fabricated"],
        }
        problems = rh.validate_emission(audit, review, trace, context)
        assert any("unknown evidence" in p for p in problems)

    def test_cross_operation_evidence_fails(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        index = _index(survey)
        evidence_id = next(
            evidence_id
            for evidence_id, metadata in index.items()
            if "ocr_rebuild" in metadata["operation_ids"]
            and "side_effects" in metadata["stages"]
        )
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), index)
        trace["memory_build"]["side_effects"] = {
            "status": "observed",
            "evidence_ids": [evidence_id],
        }
        problems = rh.validate_emission(audit, review, trace, context)
        assert any("not relevant to this operation/stage" in p for p in problems)

    def test_free_text_stage_fails(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        index = _index(survey)
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), index)
        trace["ocr_rebuild"]["input"] = "no evidence in this stage"
        problems = rh.validate_emission(audit, review, trace, context)
        assert any("must be a typed object" in p for p in problems)

    def test_unknown_operation_fails(self):
        audit, survey, context = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit, context), _index(survey))
        trace["not_an_operation"] = _full_trace(["not_an_operation"])["not_an_operation"]
        problems = rh.validate_emission(audit, review, trace, context)
        assert any("unknown operations" in p for p in problems)


class TestReviewPlan:
    def test_delta_plan_is_bounded_to_changed_operation(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        plan = rh.build_review_plan(
            audit,
            context,
            mode="delta",
            changed_files=["paperforge/worker/ocr_rebuild.py"],
        )
        assert plan["affected_operations"] == ["ocr_rebuild"]
        assert plan["scope"] == ["embed_build_resume", "memory_build", "ocr_rebuild"]
        assert plan["source_reads"]
        assert all(operation == "ocr_rebuild" for operation in plan["trace"])

    def test_delta_plan_stops_when_no_operation_is_affected(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        plan = rh.build_review_plan(audit, context, mode="delta")
        assert plan["affected_operations"] == []
        assert any("do not run a full survey" in item for item in plan["stop_conditions"])

    def test_gate_has_no_model_trace_and_rejects_narrowing(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        plan = rh.build_review_plan(audit, context, mode="gate")
        assert plan["affected_operations"] == []
        with pytest.raises(rh.ArchitectureError, match="gate"):
            rh.build_review_plan(audit, context, mode="gate", operations=["ocr_rebuild"])

    def test_focused_requires_named_operations(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        with pytest.raises(rh.ArchitectureError, match="requires"):
            rh.build_review_plan(audit, context, mode="focused")
        plan = rh.build_review_plan(
            audit, context, mode="focused", operations=["memory_build"]
        )
        assert plan["affected_operations"] == ["memory_build"]
        with pytest.raises(rh.ArchitectureError, match="unknown"):
            rh.build_review_plan(
                audit, context, mode="focused", operations=["not_an_operation"]
            )

    def test_deep_trace_defaults_to_all_or_accepts_named_operations(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        all_plan = rh.build_review_plan(audit, context, mode="deep-trace")
        assert all_plan["affected_operations"] == all_plan["scope"]
        focused_plan = rh.build_review_plan(
            audit, context, mode="deep-trace", operations=["memory_build"]
        )
        assert focused_plan["affected_operations"] == ["memory_build"]

    def test_full_release_covers_every_contract_operation(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        plan = rh.build_review_plan(audit, context, mode="full-release")
        assert plan["affected_operations"] == plan["scope"]
        with pytest.raises(rh.ArchitectureError, match="every Contract operation"):
            rh.build_review_plan(
                audit, context, mode="full-release", operations=["memory_build"]
            )

    def test_affected_rule_and_finding_ids_are_separate(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        plan = rh.build_review_plan(
            audit,
            context,
            mode="delta",
            changed_files=["paperforge/worker/ocr_rebuild.py"],
        )
        assert "affected_rules" not in plan
        assert all(
            finding.rule_id in plan["affected_rule_ids"]
            for finding in audit.content.findings
            if finding.finding_id in plan["affected_finding_ids"]
        )

    def test_delta_plan_binds_partial_trace_for_emit(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        packet = rh.build_review_plan(
            audit,
            context,
            mode="delta",
            changed_files=["paperforge/worker/ocr_rebuild.py"],
        )
        bound = rh.bind_review_plan(audit, context, json.loads(json.dumps(packet)))
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(bound["affected_operations"], context.evidence_index)
        assert rh.validate_emission(
            audit, review, trace, context, operations=bound["affected_operations"]
        ) == []

    def test_focused_plan_binds_selected_operation_trace_for_emit(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        packet = rh.build_review_plan(
            audit, context, mode="focused", operations=["memory_build"]
        )
        bound = rh.bind_review_plan(audit, context, packet)
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(bound["affected_operations"], context.evidence_index)
        assert rh.validate_emission(
            audit, review, trace, context, operations=bound["affected_operations"]
        ) == []

    def test_full_release_packet_rejects_subset_trace(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        packet = rh.build_review_plan(audit, context, mode="full-release")
        bound = rh.bind_review_plan(audit, context, packet)
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(["memory_build"], context.evidence_index)
        problems = rh.validate_emission(
            audit, review, trace, context, operations=bound["affected_operations"]
        )
        assert any("trace missing scoped operations" in problem for problem in problems)

    def test_tampered_packet_scope_fails_rebinding(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        packet = rh.build_review_plan(
            audit,
            context,
            mode="delta",
            changed_files=["paperforge/worker/ocr_rebuild.py"],
        )
        packet["affected_operations"] = []
        with pytest.raises(rh.ArchitectureError, match="re-derivation"):
            rh.bind_review_plan(audit, context, packet)

    def test_gate_packet_cannot_emit_model_overlay(self):
        audit, _, context = _audit("golden_126_ocr_rebuild")
        packet = rh.build_review_plan(audit, context, mode="gate")
        with pytest.raises(rh.ArchitectureError, match="gate mode"):
            rh.bind_review_plan(audit, context, packet)

    def test_emit_requires_plan_argument(self):
        with pytest.raises(SystemExit):
            rh.main([
                "emit",
                "--audit",
                "audit.json",
                "--review",
                "review.json",
                "--trace",
                "trace.json",
                "--fixture",
                "golden_126_ocr_rebuild",
            ])

    def test_cli_emit_accepts_bound_delta_plan(self, tmp_path):
        fixture = "golden_126_ocr_rebuild"
        audit, _, context = _audit(fixture)
        packet = rh.build_review_plan(
            audit,
            context,
            mode="delta",
            changed_files=["paperforge/worker/ocr_rebuild.py"],
        )
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(packet["affected_operations"], context.evidence_index)
        audit_path = tmp_path / "audit.json"
        plan_path = tmp_path / "plan.json"
        review_path = tmp_path / "review.json"
        trace_path = tmp_path / "trace.json"
        out_path = tmp_path / "emitted.json"
        audit_path.write_text(json.dumps(audit.to_dict()), encoding="utf-8")
        plan_path.write_text(json.dumps(packet), encoding="utf-8")
        review_path.write_text(json.dumps(review.to_dict()), encoding="utf-8")
        trace_path.write_text(json.dumps(trace), encoding="utf-8")
        assert rh.main([
            "emit",
            "--audit",
            str(audit_path),
            "--plan",
            str(plan_path),
            "--review",
            str(review_path),
            "--trace",
            str(trace_path),
            "--fixture",
            fixture,
            "--out",
            str(out_path),
        ]) == 0
        assert out_path.exists()


class TestSkillBenchmark:
    def test_manifest_contains_executable_and_historical_cases(self):
        manifest = sb.load_manifest()
        cases = manifest["cases"]
        assert len(cases) == 14
        assert sum(case.get("fixture") is not None for case in cases) == 11
        assert sum(case["kind"] == "historical_incident" for case in cases) == 3
        assert {case["source_issue"] for case in cases if case["kind"] == "historical_incident"} == {
            220,
            229,
            231,
        }

    def test_deterministic_cases_pass_and_historical_cases_are_explicitly_unrun(self):
        result = sb.run_benchmark()
        assert result["deterministic"]["cases"] == 11
        assert result["deterministic"]["passed"] == 11
        assert result["deterministic"]["failed"] == 0
        assert result["deterministic"]["historical_not_run"] == 3
        assert result["skill_runs"]["v1"]["status"] == "not_run"
        assert result["skill_runs"]["v2"]["status"] == "not_run"

    def test_answer_metrics_compare_only_supplied_measurements(self, tmp_path):
        v1_path = tmp_path / "v1.json"
        v2_path = tmp_path / "v2.json"
        v1_path.write_text(json.dumps({
            "cases": {
                "query-business-mutation": {
                    "valid_emission": False,
                    "fabricated_evidence_ids": 1,
                    "files_opened": 4,
                }
            }
        }), encoding="utf-8")
        v2_path.write_text(json.dumps({
            "cases": {
                "query-business-mutation": {
                    "valid_emission": True,
                    "fabricated_evidence_ids": 0,
                    "files_opened": 2,
                }
            }
        }), encoding="utf-8")
        result = sb.run_benchmark(answers_v1=v1_path, answers_v2=v2_path)
        assert result["skill_runs"]["v1"]["status"] == "observed"
        assert result["skill_runs"]["v1"]["metrics"]["valid_emission_rate"] == 0
        assert result["skill_runs"]["v2"]["metrics"]["valid_emission_rate"] == 1
        assert result["comparison"]["valid_emission_rate"] == 1
        assert "median_tool_calls" not in result["skill_runs"]["v1"]["metrics"]


# ---------------------------------------------------------------- process: review record


class TestReviewRecord:
    def test_identity_and_time_recorded_in_run_metadata(self):
        audit, _, _ = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        assert review.run_metadata["model"] == "test-model"
        assert review.run_metadata["created_at"] == "2026-08-05T00:00:00Z"

    def test_semantic_digest_stable_across_run_metadata(self):
        """created time / session identity are execution metadata: changing them
        must not change the review's semantic payload."""
        audit, _, _ = _audit("golden_126_ocr_rebuild")
        base = _make_review(audit, adjudications=_adjudicate_all(audit))
        moved = _make_review(audit, adjudications=_adjudicate_all(audit))
        moved = ArchitectureReview.from_dict(
            {**moved.to_dict(), "run_metadata": {"model": "other", "created_at": "2026-08-06T00:00:00Z"}}
        )
        assert base.semantic_content() == moved.semantic_content()

    def test_no_observed_fact_mutation(self):
        """Review cannot touch survey facts or deterministic findings."""
        audit, _, _ = _audit("golden_126_ocr_rebuild")
        findings_before = [f.to_dict() for f in audit.content.findings]
        _make_review(audit, adjudications=_adjudicate_all(audit))
        findings_after = [f.to_dict() for f in audit.content.findings]
        assert findings_before == findings_after


# ---------------------------------------------------------------- skill document contracts


SKILL_MD = SKILL_DIR / "SKILL.md"
TAXONOMY_MD = SKILL_DIR / "references" / "adjudication-taxonomy.md"
BRANCHES_MD = SKILL_DIR / "references" / "branches.md"
FIXTURES_MD = SKILL_DIR / "references" / "fixtures.md"


class TestSkillDocument:
    def test_skill_declares_model_invocation_and_leading_word(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "architecture-review" in text
        assert "**Leading word: trace.**" in text

    def test_skill_has_checkable_completion_criteria(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "## Completion checklist" in text
        assert "emit prints `OK`" in text
        assert "must_adjudicate" in text

    def test_skill_points_to_harness_and_references(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "scripts/review_harness.py" in text
        assert "scripts/skill_benchmark.py" in text
        assert "references/adjudication-taxonomy.md" in text
        assert "references/branches.md" in text
        assert "references/fixtures.md" in text
        assert "references/benchmark-cases.json" in text

    def test_skill_never_manufactures_observed_evidence(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "observed-static" in text or "observed_static" in text
        assert "never" in text.lower()

    def test_taxonomy_defines_all_five_adjudications(self):
        text = TAXONOMY_MD.read_text(encoding="utf-8")
        for kind in ("confirmed", "false_positive", "contract_drift",
                     "intentional_exception_recommended", "needs_evidence"):
            assert f"`{kind}`" in text

    def test_branches_define_five_review_modes(self):
        text = BRANCHES_MD.read_text(encoding="utf-8")
        for mode in ("Gate", "Delta", "Focused", "Deep-trace", "Full-release"):
            assert mode in text

    def test_fixtures_reference_records_revision(self):
        text = FIXTURES_MD.read_text(encoding="utf-8")
        assert "1f02281b" in text
        assert "golden_126_ocr_rebuild" in text
