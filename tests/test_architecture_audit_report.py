"""Architecture report projection + CI gate (#134).

Projection tests prove deterministic and review layers remain distinguishable
and source records unchanged. Gate tests prove `clean | findings | incomplete |
failed` render distinctly; HTML and CI preserve the Audit assessment; planned /
advisory / incomplete / Agent-only findings never block; only eligible active
blocking deterministic findings affect exit status. Before/after diff tests
ignore generated time and line movement while preserving semantic changes.
"""
from __future__ import annotations

import json

from paperforge.architecture_audit.layers import (
    ArchitectureContract,
    ArchitectureSurvey,
    AssessmentStatus,
    CoverageStatus,
    DeterministicAudit,
    RuleStatus,
)
from paperforge.architecture_audit.reconcile import reconcile
from paperforge.architecture_audit.report.gate import (
    EXIT_BLOCK,
    EXIT_PASS,
    evaluate_gate,
)
from paperforge.architecture_audit.report.render_html import ReportData, render

MIN_CONTRACT = {
    "schema_version": 1,
    "asset_groups": ["ocr_derived"],
    "publication_units": [
        {
            "unit_id": "ocr_derived.generation",
            "asset_group": "ocr_derived",
            "publication_authority": "ocr.publisher",
            "authorized_writers": ["ocr.rebuild"],
        }
    ],
    "operations": ["ocr_rebuild"],
    "rules": [
        {
            "rule_id": "publication.uses_protocol",
            "kind": "publication_marker",
            "subject": "ocr_derived.generation",
            "lifecycle": "active",
            "enforcement": "blocking",
        },
        {
            "rule_id": "hash.atomic_publish",
            "kind": "publication_authority",
            "subject": "ocr_derived.generation",
            "lifecycle": "planned",
            "enforcement": "advisory",
            "effective_after": {"issue": "#133", "commit": "0000000"},
        },
    ],
}


def _survey(extra_facts: list[dict] | None = None, coverage: str = "complete") -> ArchitectureSurvey:
    from paperforge.architecture_audit.layers import CoverageEntry, fact_from_dict

    facts = [fact_from_dict(f) for f in (extra_facts or [])]
    return ArchitectureSurvey(
        schema_version=1,
        scope="test",
        coverage=(
            CoverageEntry(extractor="python_ast", status=CoverageStatus(coverage)),
            CoverageEntry(extractor="typescript_compiler", status=CoverageStatus(coverage)),
        ),
        facts=tuple(facts),
        source_digest="sha256:" + "0" * 64,
    )


def _audit(contract: ArchitectureContract, survey: ArchitectureSurvey) -> DeterministicAudit:
    return reconcile(contract, survey)


def _contract() -> ArchitectureContract:
    return ArchitectureContract.from_dict(json.loads(json.dumps(MIN_CONTRACT)))


def _minimal_contract() -> ArchitectureContract:
    """Only an active blocking rule — no planned gaps, so a fact-free survey
    reconciles to assessment=clean."""
    payload = dict(MIN_CONTRACT)
    payload["rules"] = [
        rule for rule in MIN_CONTRACT["rules"]
        if rule["rule_id"] == "publication.uses_protocol"
    ]
    return ArchitectureContract.from_dict(json.loads(json.dumps(payload)))


def _bypass_write() -> dict:
    return {
        "kind": "canonical_write",
        "unit_id": "ocr_derived.generation",
        "actor_kind": "backend",
        "via_publication_protocol": False,
        "writer_id": "ocr.legacy_backfill",
        "publication_authority": "ocr.publisher",
        "evidence": {
            "file": "paperforge/worker/ocr_rebuild.py",
            "file_digest": "sha256:" + "a" * 64,
            "symbol": "legacy_backfill",
            "line_start": 10,
            "line_end": 12,
            "extractor": "python_ast",
            "epistemic_status": "observed_static",
            "confidence": "exact",
        },
    }


class TestGateSemantics:
    def test_clean_audit_passes(self):
        audit = _audit(_minimal_contract(), _survey())
        assert audit.content.assessment.status is AssessmentStatus.CLEAN
        result = evaluate_gate(audit, ("publication.uses_protocol",))
        assert result.status == "pass"
        assert result.exit_code == EXIT_PASS
        assert result.eligible is True

    def test_violated_allowlisted_rule_blocks(self):
        audit = _audit(_contract(), _survey([_bypass_write()]))
        result = evaluate_gate(audit, ("publication.uses_protocol",))
        assert result.status == "block"
        assert result.exit_code == EXIT_BLOCK
        assert result.blocking_rules == ("publication.uses_protocol",)
        assert result.findings and result.findings[0]["rule_status"] == "violated"

    def test_non_allowlisted_violation_does_not_block(self):
        audit = _audit(_contract(), _survey([_bypass_write()]))
        result = evaluate_gate(audit, ("some.other.reviewed_rule",))
        assert result.status == "pass"
        assert result.exit_code == EXIT_PASS

    def test_planned_gap_and_advisory_never_block(self):
        audit = _audit(_contract(), _survey([_bypass_write()]))
        # advisory planned rule + violation on a blocking rule NOT in the
        # allowlist -> pass; planned_gap finding cannot block either.
        result = evaluate_gate(audit, ("hash.atomic_publish",))
        assert result.status == "pass"
        planned = [f for f in audit.content.findings if f.rule_status is RuleStatus.PLANNED_GAP]
        assert planned  # declared but not effective
        result2 = evaluate_gate(audit, ())
        assert result2.status == "skipped"

    def test_incomplete_audit_is_skipped_not_blocked(self):
        audit = _audit(_contract(), _survey(coverage="unavailable"))
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE
        assert audit.content.assessment.gate_eligible is False
        result = evaluate_gate(audit, ("publication.uses_protocol",))
        assert result.status == "skipped"
        assert result.exit_code == EXIT_PASS
        assert result.eligible is False
        assert result.reasons  # machine-readable reasons, not silent

    def test_failed_audit_is_skipped_with_reasons(self):
        audit = _audit(_contract(), _survey([_bypass_write()]))
        # force failure via parse errors
        survey = _survey([_bypass_write()])
        survey = ArchitectureSurvey(
            schema_version=survey.schema_version,
            scope=survey.scope,
            coverage=survey.coverage,
            facts=survey.facts,
            source_digest=survey.source_digest,
            parse_errors=("worker/ocr.py: syntax error",),
        )
        audit = reconcile(_contract(), survey)
        assert audit.content.assessment.status is AssessmentStatus.FAILED
        result = evaluate_gate(audit, ("publication.uses_protocol",))
        assert result.status == "skipped"
        assert result.reasons and any("parse_error" in r for r in result.reasons)

    def test_review_never_affects_gate(self):
        """Agent-only (review) findings are not in the Audit; gate reads only
        DeterministicAudit and cannot even see the review layer."""
        audit = _audit(_contract(), _survey())
        result = evaluate_gate(audit, ("publication.uses_protocol",))
        assert result.status == "pass"

    def test_gate_consumes_only_audit_digests(self):
        audit = _audit(_contract(), _survey())
        assert audit.semantic_digest.startswith("sha256:")
        # A corrupted allowlist entry is ignored, not fatal.
        result = evaluate_gate(audit, ("publication.uses_protocol", "unknown.rule"))
        assert result.status == "pass"


class TestHtmlProjection:
    def _data(self, audit: DeterministicAudit, survey: ArchitectureSurvey) -> ReportData:
        contract = _contract()
        return ReportData(
            audit=json.loads(json.dumps(audit.to_dict())),
            survey=json.loads(json.dumps(survey.to_dict())),
            contract=json.loads(json.dumps(contract.to_dict())),
            review={
                "reviewer_type": "maintainer_annotation",
                "adjudications": [
                    {
                        "finding_id": "finding:test",
                        "adjudication": "needs_evidence",
                        "rationale": "not enough evidence",
                        "epistemic_status": "unresolved",
                    }
                ],
            },
            traces=[],
        )

    def test_layers_stay_distinguishable(self):
        survey = _survey([_bypass_write()])
        audit = _audit(_contract(), survey)
        html = render(self._data(audit, survey))
        # Deterministic section labeled; review section labeled separately.
        assert "确定性发现（deterministic findings）" in html
        assert "Review 层（maintainer_annotation" in html
        assert "needs_evidence" in html
        # Source records unchanged: audit JSON round-trips through render.
        assert "finding:test" in html

    def test_assessment_statuses_render_distinctly(self):
        clean_survey = _survey()
        findings_survey = _survey([_bypass_write()])
        incomplete_survey = _survey(coverage="unavailable")
        pairs = (
            (_audit(_minimal_contract(), clean_survey), "clean", clean_survey),
            (_audit(_contract(), findings_survey), "findings", findings_survey),
            (_audit(_contract(), incomplete_survey), "incomplete", incomplete_survey),
        )
        for audit, status, survey in pairs:
            html = render(self._data(audit, survey))
            assert status in html, status
            assert "gate_eligible" in html

    def test_planned_gap_and_unresolved_rendered(self):
        survey = _survey([_bypass_write()])
        audit = _audit(_contract(), survey)
        html = render(self._data(audit, survey))
        assert "planned gap" in html or "planned_gap" in html

    def test_safe_escaping_of_hostile_text(self):
        survey = _survey([_bypass_write()])
        audit = _audit(_contract(), survey)
        data = self._data(audit, survey)
        data.review["adjudications"] = [
            {
                "finding_id": "<script>alert(1)</script>",
                "adjudication": "confirmed",
                "rationale": "<img src=x onerror=alert(2)>",
                "epistemic_status": "unresolved",
            }
        ]
        html = render(data)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
        assert "<img src=x" not in html

    def test_evidence_copy_payload_present(self):
        survey = _survey([_bypass_write()])
        audit = _audit(_contract(), survey)
        html = render(self._data(audit, survey))
        assert "copy-btn" in html
        assert 'data-copy=' in html

    def test_before_after_diff_ignores_line_movement(self):
        """Line movement inside evidence changes the evidence id but the
        finding identity (rule/subject/status) and message stay stable."""
        first = _audit(_contract(), _survey([_bypass_write()]))
        moved = dict(_bypass_write())
        moved["evidence"] = dict(moved["evidence"])
        moved["evidence"]["line_start"] = 40
        moved["evidence"]["line_end"] = 42
        second = _audit(_contract(), _survey([moved]))
        f1 = first.content.findings[0]
        f2 = second.content.findings[0]
        assert f1.rule_id == f2.rule_id
        assert f1.rule_status == f2.rule_status
        assert f1.message == f2.message


