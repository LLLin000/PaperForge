"""#131 Slice A — fixture validation: synthetic scenarios and golden evidence chains.

Golden fixtures record repository revision and source digests of the observed
files; issue text supplies declared intent only. All fixtures must validate
against the schema and reconcile to the documented semantic outcomes.
"""
from __future__ import annotations

from paperforge.architecture_audit import AssessmentStatus, RuleStatus, reconcile
from paperforge.architecture_audit.fixtures import FIXTURE_NAMES, load_fixture, load_fixture_dict


class TestFixtureIntegrity:
    def test_every_fixture_validates_and_reconciles(self):
        """All 11 fixtures load, validate through reconcile, and produce a digest."""
        for name in FIXTURE_NAMES:
            contract, survey = load_fixture(name)
            audit = reconcile(contract, survey)
            assert audit.semantic_digest.startswith("sha256:")
            assert audit.content.bound_contract_digest.startswith("sha256:")
            assert audit.content.bound_survey_digest.startswith("sha256:")

    def test_golden_fixtures_record_revision_and_source_digests(self):
        from paperforge.architecture_audit.fixtures import load_fixture_dict

        # golden_126/129 still pin the #125-era observation; golden_127 was
        # re-observed after #127 reworked commands/sync.py (7372383b).
        expected_revisions = {
            "golden_126_ocr_rebuild": "dea041db",
            "golden_127_sync_embed": "7372383b",
            "golden_129_display_restore": "1a1bb895",
        }
        for name, expected_revision in expected_revisions.items():
            payload = load_fixture_dict(name)
            run_metadata = payload["survey"]["run_metadata"]
            assert run_metadata["repository_revision"] == expected_revision
            assert run_metadata["repository_dirty"] is False
            assert payload["survey"]["source_digest"].startswith("sha256:")
            for fact in payload["survey"]["facts"]:
                evidence = fact.get("evidence")
                if evidence:
                    assert evidence["file_digest"].startswith("sha256:")

    def test_golden_fixtures_have_no_agent_authored_observed_facts(self):
        """Survey evidence epistemic status must be observed_static; inferred
        claims are a Review-layer concept and never appear in a Survey."""
        for name in ("golden_126_ocr_rebuild", "golden_127_sync_embed", "golden_129_display_restore"):
            _, survey = load_fixture(name)
            for fact in survey.facts:
                evidence = getattr(fact, "evidence", None)
                assert evidence is None or evidence.epistemic_status.value == "observed_static"

    def test_golden_evidence_paths_are_repository_relative(self):
        """Evidence.file must be a POSIX repo-relative path a consumer can reopen."""
        from paperforge.architecture_audit.fixtures import load_fixture_dict

        for name in ("golden_126_ocr_rebuild", "golden_127_sync_embed", "golden_129_display_restore"):
            payload = load_fixture_dict(name)
            for fact in payload["survey"]["facts"]:
                evidence = fact.get("evidence")
                if not evidence:
                    continue
                file = evidence["file"]
                assert not file.startswith(("/", "\\")), (name, file)
                assert "\\" not in file, (name, file)
                assert file.startswith(("paperforge/", "tests/", "fixtures/")), (name, file)


class TestSyntheticOutcomes:
    def test_query_side_effect_violated(self):
        _, survey = load_fixture("synthetic_query_side_effect")
        audit = reconcile(load_fixture("synthetic_query_side_effect")[0], survey)
        finding = next(f for f in audit.content.findings)
        assert finding.rule_status is RuleStatus.VIOLATED
        assert audit.content.assessment.status is AssessmentStatus.FINDINGS

    def test_unmatched_signal_violated(self):
        contract, survey = load_fixture("synthetic_unmatched_signal")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_status is RuleStatus.VIOLATED

    def test_ui_canonical_write_violated(self):
        contract, survey = load_fixture("synthetic_ui_canonical_write")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_status is RuleStatus.VIOLATED

    def test_implicit_remote_followup_violated(self):
        contract, survey = load_fixture("synthetic_implicit_remote_followup")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_status is RuleStatus.VIOLATED

    def test_publication_bypass_violated(self):
        contract, survey = load_fixture("synthetic_publication_bypass")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_status is RuleStatus.VIOLATED

    def test_planned_gap_fixture(self):
        contract, survey = load_fixture("synthetic_planned_gap")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_status is RuleStatus.PLANNED_GAP
        assert audit.content.assessment.gate_eligible is True

    def test_intentional_exception_applied(self):
        contract, survey = load_fixture("synthetic_intentional_exception")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_status is RuleStatus.EXCEPTION_APPLIED

    def test_partial_coverage_incomplete(self):
        contract, survey = load_fixture("synthetic_partial_coverage")
        audit = reconcile(contract, survey)
        assert audit.content.assessment.status is AssessmentStatus.INCOMPLETE
        assert audit.content.assessment.gate_eligible is False
        assert "typescript_coverage_unavailable" in audit.content.assessment.reasons


class TestGoldenOutcomes:
    def test_126_planned_contract_rules_produce_planned_gaps(self):
        """#126 target behavior is declared but not yet effective.

        The fixed revision has no observable publication-authority seam, so the
        active authority rule remains unresolved instead of copying Contract
        intent into Survey facts.
        """
        contract, survey = load_fixture("golden_126_ocr_rebuild")
        audit = reconcile(contract, survey)
        statuses = {f.rule_id: f.rule_status for f in audit.content.findings}
        assert statuses["remote_intent.embed_resume"] is RuleStatus.PLANNED_GAP
        assert statuses["publication.hash_marker"] is RuleStatus.PLANNED_GAP
        assert statuses["signal.rebuild_progress"] is RuleStatus.PLANNED_GAP
        assert statuses["publication.authority"] is RuleStatus.UNRESOLVED

    def test_127_observed_implicit_embed_is_declared_planned_gap(self):
        """The sync fire-and-forget embed is observed as implicit; the policy
        rule is planned, so the audit reports a planned gap rather than a
        confirmed violation — the distinction the layer split exists for."""
        contract, survey = load_fixture("golden_127_sync_embed")
        audit = reconcile(contract, survey)
        assert audit.content.findings[0].rule_id == "remote_intent.sync_followup"
        assert audit.content.findings[0].rule_status is RuleStatus.PLANNED_GAP

    def test_129_ui_restore_write_is_planned_gap_and_drift_signal_satisfied(self):
        contract, survey = load_fixture("golden_129_display_restore")
        audit = reconcile(contract, survey)
        statuses = {f.rule_id: f.rule_status for f in audit.content.findings}
        assert statuses["canonical_writer.restore"] is RuleStatus.PLANNED_GAP
        assert "signal.drift_state" not in statuses  # active + satisfied



class TestGoldenEvidenceVerification:
    def test_pinned_evidence_files_symbols_ranges_and_aggregate_digest(self):
        import hashlib
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        names = (
            "golden_126_ocr_rebuild",
            "golden_127_sync_embed",
            "golden_129_display_restore",
        )
        for name in names:
            payload = load_fixture_dict(name)
            pairs = set()
            for fact in payload["survey"]["facts"]:
                evidence_items = []
                if fact.get("evidence"):
                    evidence_items.append(fact["evidence"])
                evidence_items.extend(fact.get("consumer_evidence", []))
                for evidence in evidence_items:
                    path = root / evidence["file"]
                    assert path.is_file(), (name, evidence["file"])
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    assert digest == evidence["file_digest"].removeprefix("sha256:"), (name, evidence["file"])
                    lines = path.read_text(encoding="utf-8").splitlines()
                    selected = lines[evidence["line_start"] - 1:evidence["line_end"]]
                    assert any(evidence["symbol"] in line for line in selected), (
                        name,
                        evidence["symbol"],
                    )
                    pairs.add((evidence["file"], evidence["file_digest"]))
            aggregate = "\n".join(f"{file}\n{digest}" for file, digest in sorted(pairs))
            expected = "sha256:" + hashlib.sha256(aggregate.encode("utf-8")).hexdigest()
            assert payload["survey"]["source_digest"] == expected, name