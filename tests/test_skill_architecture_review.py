"""#132 Slice B — architecture-review Skill process evals.

Tests the review process machinery the Skill drives, plus the Skill document's
own contracts. Process evals assert predictability, not prose: validated-input
first, digest/reconciler-version binding, epistemic labeling, finding-ID
integrity, adjudication completeness, and the eight-stage trace completion —
against the fixed Slice A fixtures, across the three branches.
"""
from __future__ import annotations

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

# ---------------------------------------------------------------- helpers


def _audit(fixture: str):
    contract, survey = load_fixture(fixture)
    return reconcile(contract, survey), survey


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


def _pool(survey) -> list[str]:
    return rh.evidence_pool_from_survey(survey)


def _full_trace(operations, pool=()) -> dict:
    """A complete eight-stage trace; stages cite pool evidence or a note."""
    trace = {}
    for operation in operations:
        stages = {}
        for stage in rh.TRACE_STAGES:
            stages[stage] = [pool[0]] if pool else "no evidence in this stage"
        trace[operation] = stages
    return trace


def _adjudicate_all(audit) -> list[dict]:
    return [_adjudication(f.finding_id) for f in rh.required_findings(audit)]


# ---------------------------------------------------------------- process: validated input first


class TestValidatedInputFirst:
    def test_audit_loads_fixture_and_prints_bindings(self):
        audit, _ = _audit("golden_126_ocr_rebuild")
        summary = rh.audit_summary(audit)
        assert summary["audit_digest"] == audit.semantic_digest
        assert summary["reconciler_version"] == audit.content.reconciler_version
        assert summary["assessment"]["status"] == "findings"
        assert "ocr_derived.generation" in summary["scope"]
        assert len(summary["must_adjudicate"]) == 1  # publication.authority unresolved

    def test_refuses_invalid_audit_input(self):
        with pytest.raises((OSError, ValueError)):
            rh.load_audit(audit_path=str(REPO_ROOT / "missing-audit.json"))

    def test_refuses_unknown_schema_version(self, tmp_path):
        audit, _ = _audit("golden_126_ocr_rebuild")
        payload = audit.to_dict()
        payload["schema_version"] = 999
        path = tmp_path / "bad_audit.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(Exception, match="schema_version"):
            rh.load_audit(audit_path=str(path))


# ---------------------------------------------------------------- process: branches


class TestBranches:
    def test_full_survey_golden126_all_edges_adjudicated(self):
        audit, survey = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        assert rh.validate_emission(audit, review, trace, _pool(survey)) == []

    def test_full_survey_golden127_and_129(self):
        for fixture in ("golden_127_sync_embed", "golden_129_display_restore"):
            audit, survey = _audit(fixture)
            review = _make_review(audit, adjudications=_adjudicate_all(audit))
            trace = _full_trace(rh.scope(audit), _pool(survey))
            assert rh.validate_emission(audit, review, trace, _pool(survey)) == []

    def test_focused_signal_branch_synthetic_unmatched_signal(self):
        audit, survey = _audit("synthetic_unmatched_signal")
        assert rh.scope(audit) == ["EVENT_BUS_EMIT"]
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        assert rh.validate_emission(audit, review, trace, _pool(survey)) == []

    def test_changed_interface_branch_publication_bypass(self):
        audit, survey = _audit("synthetic_publication_bypass")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        assert rh.validate_emission(audit, review, trace, _pool(survey)) == []

    def test_operations_narrowing_covers_exactly_declared_operations(self):
        audit, survey = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(["embed_build_resume"], _pool(survey))
        problems = rh.validate_emission(
            audit, review, trace, _pool(survey), operations=["embed_build_resume"]
        )
        assert problems == []


# ---------------------------------------------------------------- process: refusal


class TestRefusal:
    def test_refuses_digest_mismatch(self):
        audit, _ = _audit("golden_126_ocr_rebuild")
        other, _ = _audit("golden_127_sync_embed")
        stale = _make_review(other, adjudications=[_adjudication(f.finding_id) for f in rh.required_findings(audit)])
        problems = rh.validate_emission(audit, stale, None)
        assert any("not bound" in p or "digest" in p for p in problems)

    def test_refuses_reconciler_version_mismatch(self):
        audit, _ = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        review = ArchitectureReview.from_dict({**review.to_dict(), "reconciler_version": "9.9.9"})
        problems = rh.validate_emission(audit, review, None)
        assert any("reconciler_version" in p for p in problems)

    def test_refuses_observed_static_claims(self):
        audit, _ = _audit("synthetic_publication_bypass")
        review = _make_review(
            audit, adjudications=[_adjudication(f.finding_id, status="observed_static") for f in rh.required_findings(audit)]
        )
        problems = rh.validate_emission(audit, review, None)
        assert any("epistemic" in p for p in problems)

    def test_refuses_fabricated_finding_id(self):
        audit, _ = _audit("synthetic_publication_bypass")
        review = _make_review(audit, adjudications=[_adjudication("finding:deadbeef")])
        problems = rh.validate_emission(audit, review, None)
        assert any("unknown finding_id" in p for p in problems)

    def test_refuses_missing_adjudication(self):
        audit, _ = _audit("synthetic_publication_bypass")
        review = _make_review(audit)  # no adjudications
        problems = rh.validate_emission(audit, review, None)
        assert any("no adjudication" in p for p in problems)

    def test_refuses_semantic_finding_collision(self):
        audit, _ = _audit("synthetic_publication_bypass")
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
        problems = rh.validate_emission(audit, review, None)
        assert any("collides" in p for p in problems)

    def test_refuses_empty_reviewer_type(self):
        audit, _ = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit), reviewer_type=" ")
        problems = rh.validate_emission(audit, review, None)
        assert any("reviewer_type" in p for p in problems)

    def test_refuses_incomplete_coverage_audit_for_review(self):
        """partial coverage yields incomplete assessment; emit still binds and
        adjudicates the violated coverage finding — no silent all-clear."""
        audit, survey = _audit("synthetic_partial_coverage")
        assert audit.content.assessment.status.value == "incomplete"
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        assert rh.validate_emission(audit, review, trace, _pool(survey)) == []

    def test_refuses_emission_without_trace_manifest(self):
        """trace is the completion invariant — an overlay without a scoped
        trace must never be accepted."""
        audit, survey = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        problems = rh.validate_emission(audit, review, None, _pool(survey))
        assert any("trace manifest required" in p for p in problems)

    def test_refuses_trace_without_evidence_pool(self):
        """an unknown evidence pool must be refused, not silently skipped —
        fabricated stage evidence cannot pass when the pool is unavailable."""
        audit, _ = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit))
        problems = rh.validate_emission(audit, review, trace, None)
        assert any("evidence pool" in p for p in problems)


# ---------------------------------------------------------------- process: trace completion


class TestTraceCompletion:
    def test_missing_stage_fails(self):
        audit, survey = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        del trace["ocr_derived.generation"]["failure"]
        problems = rh.validate_emission(audit, review, trace, _pool(survey))
        assert any("missing stage failure" in p for p in problems)

    def test_silent_empty_stage_fails(self):
        audit, survey = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        trace["ocr_derived.generation"]["input"] = []
        problems = rh.validate_emission(audit, review, trace, _pool(survey))
        assert any("stage input is empty" in p for p in problems)

    def test_unknown_evidence_fails(self):
        audit, survey = _audit("golden_126_ocr_rebuild")
        pool = _pool(survey)
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), pool)
        trace["ocr_derived.generation"]["input"] = ["evidence:fabricated"]
        problems = rh.validate_emission(audit, review, trace, pool)
        assert any("unknown evidence" in p for p in problems)

    def test_unknown_operation_fails(self):
        audit, survey = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        trace = _full_trace(rh.scope(audit), _pool(survey))
        trace["not_an_operation"] = _full_trace(["not_an_operation"])["not_an_operation"]
        problems = rh.validate_emission(audit, review, trace, _pool(survey))
        assert any("unknown operations" in p for p in problems)


# ---------------------------------------------------------------- process: review record


class TestReviewRecord:
    def test_identity_and_time_recorded_in_run_metadata(self):
        audit, _ = _audit("golden_126_ocr_rebuild")
        review = _make_review(audit, adjudications=_adjudicate_all(audit))
        assert review.run_metadata["model"] == "test-model"
        assert review.run_metadata["created_at"] == "2026-08-05T00:00:00Z"

    def test_semantic_digest_stable_across_run_metadata(self):
        """created time / session identity are execution metadata: changing them
        must not change the review's semantic payload."""
        audit, _ = _audit("golden_126_ocr_rebuild")
        base = _make_review(audit, adjudications=_adjudicate_all(audit))
        moved = _make_review(audit, adjudications=_adjudicate_all(audit))
        moved = ArchitectureReview.from_dict(
            {**moved.to_dict(), "run_metadata": {"model": "other", "created_at": "2026-08-06T00:00:00Z"}}
        )
        assert base.semantic_content() == moved.semantic_content()

    def test_no_observed_fact_mutation(self):
        """Review cannot touch survey facts or deterministic findings."""
        audit, _ = _audit("golden_126_ocr_rebuild")
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
        assert "references/adjudication-taxonomy.md" in text
        assert "references/branches.md" in text
        assert "references/fixtures.md" in text

    def test_skill_never_manufactures_observed_evidence(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        assert "observed-static" in text or "observed_static" in text
        assert "never" in text.lower()

    def test_taxonomy_defines_all_five_adjudications(self):
        text = TAXONOMY_MD.read_text(encoding="utf-8")
        for kind in ("confirmed", "false_positive", "contract_drift",
                     "intentional_exception_recommended", "needs_evidence"):
            assert f"`{kind}`" in text

    def test_branches_define_three_shapes(self):
        text = BRANCHES_MD.read_text(encoding="utf-8")
        for branch in ("Full-survey", "Focused-signal", "Changed-interface"):
            assert branch in text

    def test_fixtures_reference_records_revision(self):
        text = FIXTURES_MD.read_text(encoding="utf-8")
        assert "1f02281b" in text
        assert "golden_126_ocr_rebuild" in text
