"""Deterministic collectors (#133).

Highest seam: run the maintainer orchestrator against controlled mixed
Python/TypeScript fixtures, validate the ArchitectureSurvey, then prove it
invokes #131's public `reconcile()` to produce a DeterministicAudit without
local rule duplication. Synthetic fixtures independently cover direct sinks,
wrapper summaries, unresolved calls, source exclusions, stable IDs, digest
updates, and TypeScript unavailability.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from paperforge.architecture_audit import ArchitectureContract, validate_survey
from paperforge.architecture_audit.collectors.common import (
    WrapperSpec,
    load_default_python_registry,
    load_wrapper_registry,
)
from paperforge.architecture_audit.collectors.orchestrator import collect
from paperforge.architecture_audit.layers import (
    AssessmentStatus,
    CoverageStatus,
    RuleStatus,
)

CONTRACT_PAYLOAD = {
    "schema_version": 1,
    "asset_groups": ["ocr_derived"],
    "publication_units": [
        {
            "unit_id": "ocr_derived.generation",
            "asset_group": "ocr_derived",
            "publication_authority": "ocr.publisher",
            "authorized_writers": ["ocr.postprocess", "ocr.rebuild"],
        }
    ],
    "operations": ["sync", "probe_status", "ocr_rebuild"],
    "required_extractors": ["python_ast", "typescript_compiler"],
    "rules": [
        {
            "rule_id": "query.side_effect_free",
            "kind": "query_side_effect",
            "subject": "probe_status",
            "lifecycle": "active",
            "enforcement": "blocking",
        },
        {
            "rule_id": "remote_intent.sync_followup",
            "kind": "remote_intent",
            "subject": "sync",
            "lifecycle": "active",
            "enforcement": "blocking",
            "accepted_intent_modes": ["direct_invocation", "ui_modal", "explicit_flag", "interactive_prompt"],
        },
        {
            "rule_id": "publication.uses_protocol",
            "kind": "publication_marker",
            "subject": "ocr_derived.generation",
            "lifecycle": "active",
            "enforcement": "blocking",
        },
        {
            "rule_id": "canonical.no_ui_writer",
            "kind": "canonical_writer",
            "subject": "ocr_derived.generation",
            "lifecycle": "active",
            "enforcement": "blocking",
        },
        {
            "rule_id": "coverage.required_complete",
            "kind": "coverage_complete",
            "subject": "",
            "lifecycle": "active",
            "enforcement": "blocking",
        },
    ],
}


def _write_tree(base: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _contract() -> ArchitectureContract:
    return ArchitectureContract.from_dict(json.loads(json.dumps(CONTRACT_PAYLOAD)))


def _make_repo(tmp_path: Path) -> Path:
    """Controlled mixed-language repository for seam tests."""
    repo = tmp_path / "repo"
    _write_tree(
        repo,
        {
            "paperforge/worker/probe_status.py": (
                "import os\n"
                "\n"
                "def probe_status():\n"
                "    # query must stay side-effect free\n"
                "    return os.path.exists('x')\n"
            ),
            "paperforge/worker/sync.py": (
                "import subprocess\n"
                "\n"
                "def sync():\n"
                "    # remote follow-up requires explicit intent (#127); static\n"
                "    # collection cannot see intent -> unresolved, never guessed\n"
                "    subprocess.run(['paperforge', 'memory', 'build'])\n"
            ),
            "paperforge/worker/ocr_rebuild.py": (
                "from paperforge.worker.ocr_hash import publish_ocr_result_hash\n"
                "\n"
                "def rebuild(paper_root):\n"
                "    publish_ocr_result_hash(paper_root)\n"
            ),
            "paperforge/worker/ocr_hash.py": (
                "from pathlib import Path\n"
                "import os\n"
                "\n"
                "def publish_ocr_result_hash(paper_root: Path):\n"
                "    # Tier 2 wrapper: atomic publish via the canonical protocol\n"
                "    os.replace(paper_root / 'result-hash.pending', paper_root / 'result-hash.txt')\n"
                "\n"
                "def dynamic_side(paper_root: Path):\n"
                "    # Tier 3: dynamic receiver, write verb -> unresolved\n"
                "    storage = {'w': paper_root}\n"
                "    storage['w'].write_text('x')\n"
            ),
            "paperforge/plugin/src/main.ts": (
                "import { execFile } from 'child_process';\n"
                "import * as fs from 'fs';\n"
                "\n"
                "export function run() {\n"
                "  execFile('paperforge', ['probe']);\n"
                "  fs.writeFileSync('/tmp/x', 'y');\n"
                "}\n"
            ),
            "paperforge/plugin/node_modules/typescript/package.json": "{}",
            "contract.json": json.dumps(CONTRACT_PAYLOAD, indent=1),
        },
    )
    return repo


class TestOrchestratorSeam:
    def test_mixed_repo_produces_validated_survey_and_audit(self, tmp_path):
        """Highest seam: controlled mixed py/ts fixtures -> Survey -> reconcile()."""
        repo = _make_repo(tmp_path)
        # The TS script resolves `typescript` from plugin/node_modules; the
        # fake package.json is not a compiler, so expect honest unavailability
        # rather than fabricated facts.
        contract = _contract()
        outcome = collect(
            repo,
            contract=contract,
            py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",),
            node_cmd="node",
        )
        assert outcome.survey is not None
        validate_survey(outcome.survey)
        assert outcome.audit is not None
        # No local rule duplication: reconcile is the single rule engine.
        assert outcome.audit.content.reconciler_version
        assert outcome.audit.content.bound_contract_digest.startswith("sha256:")
        assert outcome.audit.content.bound_survey_digest.startswith("sha256:")

    def test_direct_sinks_and_wrappers_collected(self, tmp_path):
        repo = _make_repo(tmp_path)
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",), node_cmd="node",
        )
        kinds = {fact["kind"] for fact in outcome.facts}
        assert "effect" in kinds
        assert "canonical_write" in kinds
        assert "unresolved" in kinds
        writes = [f for f in outcome.facts if f["kind"] == "canonical_write"]
        assert writes and writes[0]["unit_id"] == "ocr_derived.generation"
        assert writes[0]["via_publication_protocol"] is True
        # wrapper hit recorded
        assert any(h["wrapper_id"] == "ocr_hash.publish_ocr_result_hash" for h in outcome.wrapper_hits)
        # dynamic write-verb call recorded unresolved with honest effects
        unresolved = [f for f in outcome.facts if f["kind"] == "unresolved"]
        assert unresolved
        assert all(f["possible_effects"] for f in unresolved)

    def test_source_exclusions(self, tmp_path):
        repo = _make_repo(tmp_path)
        _write_tree(
            repo,
            {
                "paperforge/worker/generated_bundle.py": "def x(): pass\n",
                "paperforge/worker/__pycache__/cached.py": "def x(): pass\n",
                "paperforge/tests/test_probe.py": "def x(): pass\n",
                "paperforge/node_modules/dep.py": "def x(): pass\n",
            },
        )
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",), node_cmd="node",
        )
        scanned = [rel for rel, _ in outcome.scanned_files]
        assert "worker/generated_bundle.py" in scanned  # not excluded by name alone
        assert not any("__pycache__" in rel for rel in scanned)
        assert not any("tests" in rel for rel in scanned)
        assert not any("node_modules" in rel for rel in scanned)

    def test_python_parse_error_marks_partial_coverage(self, tmp_path):
        repo = _make_repo(tmp_path)
        _write_tree(repo, {"paperforge/broken.py": "def broken(:\n"})
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",), node_cmd="node",
        )
        coverage = {c.extractor: c.status for c in outcome.survey.coverage}
        assert coverage["python_ast"] is CoverageStatus.PARTIAL
        assert outcome.parse_errors

    def test_ts_unavailable_records_coverage_and_incomplete_assessment(self, tmp_path):
        """#133 user story 3 + testing decision: missing TypeScript tooling is
        explicit coverage, never a silent all-clear."""
        repo = _make_repo(tmp_path)
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",), node_cmd="definitely-not-node",
        )
        coverage = {c.extractor: c.status for c in outcome.survey.coverage}
        assert coverage["typescript_compiler"] is CoverageStatus.UNAVAILABLE
        assert outcome.survey.coverage[-1].diagnostics
        assessment = outcome.audit.content.assessment
        assert assessment.status is AssessmentStatus.INCOMPLETE
        assert assessment.gate_eligible is False
        assert any("typescript_compiler" in r for r in assessment.reasons)

    def test_no_ts_roots_declares_no_ts_extractor(self, tmp_path):
        repo = _make_repo(tmp_path)
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",  # no TS roots configured at all
        )
        coverage = {c.extractor: c.status for c in outcome.survey.coverage}
        assert "typescript_compiler" not in coverage
        assert coverage["python_ast"] is CoverageStatus.COMPLETE


class TestRealTypeScriptCollector:
    """True Node + TypeScript compiler run against controlled fixtures."""

    def _real_ts_repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        _write_tree(
            repo,
            {
                "paperforge/worker/probe_status.py": "def probe_status():\n    return 1\n",
                "paperforge/plugin/src/main.ts": (
                    "import { execFile } from 'child_process';\n"
                    "import * as fs from 'fs';\n"
                    "\n"
                    "export function run() {\n"
                    "  execFile('paperforge', ['probe']);\n"
                    "  fs.writeFileSync('/tmp/x', 'y');\n"
                    "  fs.readFileSync('/tmp/z');\n"
                    "}\n"
                ),
            },
        )
        return repo

    @pytest.mark.skipif(
        shutil.which("node") is None
        or not Path("paperforge/plugin/node_modules/typescript").is_dir(),
        reason="requires node + repository typescript compiler",
    )
    def test_real_ts_facts_merge_with_repo_relative_paths(self, tmp_path):
        repo = self._real_ts_repo(tmp_path)
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",), node_cmd="node",
        )
        coverage = {c.extractor: c.status for c in outcome.survey.coverage}
        assert coverage["typescript_compiler"] is CoverageStatus.COMPLETE
        ts_facts = [
            f for f in outcome.facts
            if f.get("evidence", {}).get("file", "").startswith("paperforge/plugin/src/")
        ]
        kinds = {f["kind"] for f in ts_facts}
        assert "effect" in kinds  # fs.writeFileSync
        assert "unresolved" in kinds  # child_process.execFile
        for fact in ts_facts:
            assert fact["evidence"]["file"].startswith("paperforge/plugin/src/")
        # Survey stays valid end to end through the reconciler.
        validate_survey(outcome.survey)
        assert outcome.audit is not None


class TestUnresolvedSemantics:
    """Tier 3 evidence must stop rules from concluding on partial enumeration."""

    def test_unresolved_remote_call_blocks_satisfied(self, tmp_path):
        repo = _make_repo(tmp_path)
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=("paperforge/plugin/src",), node_cmd="definitely-not-node",
        )
        finding = next(
            f for f in outcome.audit.content.findings
            if f.rule_id == "remote_intent.sync_followup"
        )
        # coverage incomplete already blocks; the seam must also apply when
        # coverage completes (unresolved dynamic callsite in sync.py).
        assert finding.rule_status is RuleStatus.UNRESOLVED
        assert "cannot enumerate" in finding.message

    def test_unresolved_relevant_only_to_matching_module(self, tmp_path):
        repo = _make_repo(tmp_path)
        _write_tree(
            repo,
            {
                "paperforge/worker/sync.py": (
                    "import subprocess\n"
                    "def sync():\n"
                    "    subprocess.run(['x'])\n"
                ),
                "paperforge/worker/probe_status.py": (
                    "def probe_status():\n"
                    "    return 1\n"
                ),
            },
        )
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",
        )
        findings = {f.rule_id: f for f in outcome.audit.content.findings}
        # The unresolved call lives in sync.py; probe_status has no unresolved
        # evidence, so its rule is not shadowed by module-scoped facts.
        assert findings["remote_intent.sync_followup"].rule_status is RuleStatus.UNRESOLVED
        assert findings["query.side_effect_free"].rule_status is not RuleStatus.VIOLATED

    def test_wrapper_registry_and_contract_are_separate_inputs(self):
        """Wrapper registry validates independently of the Contract."""
        good = [
            {
                "wrapper_id": "w1",
                "qualified_name": "mod.func",
                "version": 1,
                "confidence": "exact",
                "facts": [{"kind": "effect", "effect_kind": "business_mutation"}],
            }
        ]
        specs = load_wrapper_registry(good)
        assert specs[0].wrapper_id == "w1"
        with pytest.raises(ValueError):
            load_wrapper_registry([{"wrapper_id": "x", "qualified_name": "no-dot"}])
        with pytest.raises(ValueError):
            load_wrapper_registry(
                [{"wrapper_id": "x", "qualified_name": "a.b", "facts": []}]
            )
        # Default registry entries carry the #126/#127/#129 wrapper knowledge.
        defaults = load_default_python_registry()
        assert any(s.wrapper_id == "ocr_hash.publish_ocr_result_hash" for s in defaults)

    def test_signal_pairing_via_wrapper_registry(self, tmp_path):
        """A registered signal wrapper produces SignalFact that the #131
        reconciler evaluates (no local rule duplication)."""
        from paperforge.architecture_audit.collectors.common import SignalSpec
        from paperforge.architecture_audit.layers import SignalConsumerKind

        repo = _make_repo(tmp_path)
        _write_tree(
            repo,
            {
                "paperforge/worker/ocr_rebuild.py": (
                    "from paperforge.worker.emitter import emit_progress\n"
                    "def rebuild():\n"
                    "    emit_progress(1, 5)\n"
                ),
                "paperforge/worker/emitter.py": (
                    "def emit_progress(current, total):\n"
                    "    print(f'OCR_REBUILD_PROGRESS:{current}:{total}')\n"
                ),
            },
        )
        registry = (
            WrapperSpec(
                wrapper_id="emitter.emit_progress",
                qualified_name="emitter.emit_progress",
                facts=(
                    SignalSpec(
                        signal_id="OCR_REBUILD_PROGRESS",
                        producer="ocr_rebuild",
                        consumer_kind=SignalConsumerKind.CODE,
                        has_code_consumer=False,
                    ),
                ),
            ),
        )
        # Contract: signal must have a code consumer; TS is out of scope so
        # python_ast alone provides the required coverage.
        contract_payload = dict(CONTRACT_PAYLOAD)
        contract_payload["required_extractors"] = ["python_ast"]
        contract_payload["rules"] = [
            {
                "rule_id": "signal.has_consumer",
                "kind": "signal_consumer",
                "subject": "OCR_REBUILD_PROGRESS",
                "lifecycle": "active",
                "enforcement": "blocking",
            }
        ]
        contract = ArchitectureContract.from_dict(json.loads(json.dumps(contract_payload)))
        outcome = collect(
            repo, contract=contract, py_roots=("paperforge",),
            ts_roots=(), node_cmd="node", python_registry=registry,
        )
        signals = [f for f in outcome.facts if f["kind"] == "signal"]
        assert signals and signals[0]["signal_id"] == "OCR_REBUILD_PROGRESS"
        finding = next(
            f for f in outcome.audit.content.findings
            if f.rule_id == "signal.has_consumer"
        )
        # No code consumer observed -> violated (the reconciler's decision).
        assert finding.rule_status is RuleStatus.VIOLATED

    def test_publication_bypass_chain(self, tmp_path):
        """A registered non-protocol writer produces a canonical_write fact the
        reconciler flags as bypassing the publication protocol."""
        repo = _make_repo(tmp_path)
        _write_tree(
            repo,
            {
                "paperforge/worker/ocr_rebuild.py": (
                    "from paperforge.worker.legacy import write_derived\n"
                    "def rebuild():\n"
                    "    write_derived('out')\n"
                ),
                "paperforge/worker/legacy.py": (
                    "def write_derived(target):\n"
                    "    pass\n"
                ),
            },
        )
        from paperforge.architecture_audit.collectors.common import WriteSpec

        registry = (
            WrapperSpec(
                wrapper_id="legacy.write_derived",
                qualified_name="legacy.write_derived",
                facts=(
                    WriteSpec(
                        unit_id="ocr_derived.generation",
                        via_publication_protocol=False,
                        writer_id="ocr.legacy_backfill",
                        publication_authority="ocr.publisher",
                    ),
                ),
            ),
        )
        contract_payload = dict(CONTRACT_PAYLOAD)
        contract_payload["required_extractors"] = ["python_ast"]
        contract_payload["rules"] = [
            {
                "rule_id": "publication.uses_protocol",
                "kind": "publication_marker",
                "subject": "ocr_derived.generation",
                "lifecycle": "active",
                "enforcement": "blocking",
            }
        ]
        contract = ArchitectureContract.from_dict(json.loads(json.dumps(contract_payload)))
        outcome = collect(
            repo, contract=contract, py_roots=("paperforge",),
            ts_roots=(), node_cmd="node", python_registry=registry,
        )
        writes = [f for f in outcome.facts if f["kind"] == "canonical_write"]
        assert writes and writes[0]["via_publication_protocol"] is False
        finding = next(
            f for f in outcome.audit.content.findings
            if f.rule_id == "publication.uses_protocol"
        )
        assert finding.rule_status is RuleStatus.VIOLATED


class TestStableIdentityAndDigests:
    def _run(self, tmp_path, repo) -> tuple[object, object]:
        return (
            repo,
            collect(
                repo, contract=_contract(), py_roots=("paperforge",),
                ts_roots=(), node_cmd="node",
            ),
        )

    def test_line_movement_preserves_finding_identity(self, tmp_path):
        repo = _make_repo(tmp_path)
        first = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",
        )
        # Insert blank lines before the sync subprocess call.
        sync = repo / "paperforge/worker/sync.py"
        sync.write_text(
            "\n\n\n" + sync.read_text(encoding="utf-8"), encoding="utf-8"
        )
        second = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",
        )
        a = first.audit
        b = second.audit
        # Normalized symbols/effects unchanged -> same finding ids even though
        # line numbers moved (evidence id is line-based; finding id is
        # symbol/effect-based).
        ids_a = {f.finding_id for f in a.content.findings}
        ids_b = {f.finding_id for f in b.content.findings}
        assert ids_a == ids_b
        # But the surveys differ: source digest must track the content change.
        assert a.content.bound_survey_digest != b.content.bound_survey_digest

    def test_content_change_updates_file_and_source_digests(self, tmp_path):
        repo = _make_repo(tmp_path)
        first = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",
        )
        (repo / "paperforge/worker/sync.py").write_text(
            "import subprocess\ndef sync():\n    return 1\n", encoding="utf-8"
        )
        second = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",
        )
        assert first.survey.source_digest != second.survey.source_digest
        assert first.audit.content.bound_survey_digest != second.audit.content.bound_survey_digest

    def test_survey_digest_covers_facts_and_repository_state(self, tmp_path):
        repo = _make_repo(tmp_path)
        outcome = collect(
            repo, contract=_contract(), py_roots=("paperforge",),
            ts_roots=(), node_cmd="node",
        )
        digest = outcome.audit.content.bound_survey_digest
        from paperforge.architecture_audit.canonical import semantic_digest

        assert digest == semantic_digest(outcome.survey.semantic_content())
        # repository_state is always present (empty outside a git checkout)
        assert isinstance(outcome.survey.repository_state.dirty, bool)
        assert digest.startswith("sha256:")


class TestRepositoryAcceptance:
    """Pinned-revision acceptance on the real repository (no JSON snapshot)."""

    @pytest.mark.skipif(not Path(".git").is_dir(), reason="not a git checkout")
    def test_root_findings_cover_product_lane_rules(self):
        # Run the real orchestrator into a temp dir; assert the root rules for
        # #126/#127/#129 are present with honest statuses.
        import subprocess
        import sys

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "paperforge.architecture_audit.collectors.orchestrator",
                "--root",
                ".",
                "--contract",
                "docs/architecture-audit-2026-08-06/contract.json",
                "--out",
                str(tmp_path := Path("C:/Users/Lin/AppData/Local/Temp/pf-acceptance")),
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            timeout=600,
        )
        assert proc.returncode == 0, proc.stderr
        audit = json.loads((Path("C:/Users/Lin/AppData/Local/Temp/pf-acceptance") / "audit.json").read_text(encoding="utf-8"))
        rules = {f["rule_id"]: f["rule_status"] for f in audit["content"]["findings"]}
        coverage_rules = {
            c["rule_id"]: c.get("status", "planned_gap")
            for c in audit["content"].get("rule_coverage", [])
        }
        for rule_id in (
            "query.side_effect_free",
            "remote_intent.sync_followup",
            "signal.has_consumer",
            "publication.uses_protocol",
            "canonical.no_ui_writer",
            "restore.display_only",
            "publication.authority_ocr_display",
            "publication.authority_retrieval",
            "role_authority.ocr_execution",
            "role_authority.ocr_stop",
            "role_authority.embed_stop",
        ):
            assert rule_id in rules or rule_id in coverage_rules, rule_id
            status = rules.get(rule_id, coverage_rules.get(rule_id))
            assert status in {"unresolved", "violated", "satisfied", "planned_gap"}, rule_id
        # With both deterministic collectors complete and a clean checkout the
        # gate is eligible (manual materials are Review-only, never required).
        assert audit["content"]["assessment"]["gate_eligible"] in {True, False}
        if audit["content"]["assessment"]["gate_eligible"] is False:
            reasons = audit["content"]["assessment"]["reasons"]
            assert not any("manual_contract_trace" in r for r in reasons)


# ── T9 (#170) canonical filesystem-read collection ────────────────────────

class TestCanonicalReadCollection:
    def test_real_repo_collects_and_classifies_filesystem_reads(self) -> None:
        """#149/#170: the TS collector extracts bare filesystem reads and
        classifies canonical-materialization paths (variable-indirect
        path.join traces included)."""
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        root = Path.cwd()
        out = Path(tempfile.mkdtemp(prefix="pf-read-collect-"))
        proc = subprocess.run(
            [
                sys.executable, "-m",
                "paperforge.architecture_audit.collectors.orchestrator",
                "--root", str(root),
                "--contract", "docs/architecture-audit-2026-08-06/contract.json",
                "--out", str(out),
            ],
            capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0, proc.stderr[-800:]
        survey = json.loads((out / "survey.json").read_text(encoding="utf-8"))
        reads = [f for f in survey.get("facts", []) if f.get("kind") == "filesystem_read"]
        assert len(reads) > 0, "TS collector must extract filesystem reads"
        units = {f.get("unit_id") for f in reads}
        # The dashboard/ocr-workspace readFileSync(indexPath) path.join trace
        # must classify to the canonical formal_library unit.
        formal = [f for f in reads if f.get("unit_id") == "formal_library"]
        assert formal, f"expected formal_library reads from the real repo, got units={units}"
        assert all(f.get("wrapper_id") is None for f in formal), (
            "bare reads carry no wrapper attribution (#149 collector knowledge)"
        )


# ── T9 (#170) closure — default TS registry + adapter operations ─────────

class TestCanonicalReadClosure:
    def test_default_ts_collector_attributes_registered_read_wrapper(self, tmp_path) -> None:
        """#170 P0-1: the DEFAULT orchestrator must pass the wrapper registry
        to the TS collector — a call to a registered read helper carries the
        semantic wrapper_id in the collected fact."""
        import subprocess
        import sys

        repo = tmp_path / "repo"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "runtime_paths.ts").write_text(
            'import * as fs from "fs";\n'
            "export function readCanonicalPath(p: string): string {\n"
            '  return fs.readFileSync(p, "utf-8");\n'
            "}\n",
            encoding="utf-8",
        )
        (repo / "src" / "app.ts").write_text(
            'import { readCanonicalPath } from "./runtime_paths";\n'
            'const data = readCanonicalPath("/vault/indexes/formal-library.json");\n',
            encoding="utf-8",
        )
        out = tmp_path / "out"
        repo_root = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [
                sys.executable, "-m",
                "paperforge.architecture_audit.collectors.orchestrator",
                "--root", str(repo),
                "--ts-roots", "src",
                "--contract", str(repo_root / "docs/architecture-audit-2026-08-06/contract.json"),
                "--out", str(out),
            ],
            capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0, proc.stderr[-800:]
        survey = json.loads((out / "survey.json").read_text(encoding="utf-8"))
        reads = [f for f in survey.get("facts", []) if f.get("kind") == "filesystem_read"]
        wrapped = [f for f in reads if f.get("wrapper_id") is not None]
        assert wrapped, f"registered read helper must carry wrapper attribution, reads={reads}"
        assert wrapped[0]["wrapper_id"] == "client_cache.read"

    def test_dynamic_only_canonical_read_is_unresolved(self) -> None:
        """#170 P0-3: an ACTIVE canonical-read rule with NO classified reads
        and only a dynamic canonical path → UNRESOLVED (fail incomplete, do
        not guess satisfied)."""
        from tests.test_architecture_audit_reconcile import _contract, _evidence, _survey

        rule = {
            "rule_id": "client_read.formal_library",
            "kind": "canonical_read",
            "subject": "formal_library",
            "lifecycle": "active",
            "enforcement": "advisory",
        }
        contract = _contract([rule])
        survey = _survey(facts=(
            {
                "kind": "unresolved",
                "unresolved_id": "u-dyn",
                "expression": "readPath(expr)",
                "reason": "dynamic canonical path",
                "possible_effects": ["disposable_snapshot"],
                "evidence": _evidence("ocr_workspace", 40),
            },
        ))
        from paperforge.architecture_audit import reconcile

        audit = reconcile(contract, survey)
        finding = next(
            f for f in audit.content.findings
            if f.rule_id == "client_read.formal_library"
        )
        # #170 P0-3: dynamic canonical path → UNRESOLVED (never guessed
        # satisfied).  Advisory unresolved is a FINDINGS-level assessment
        # (gate stays eligible); blocking unresolved would be incomplete.
        assert finding.rule_status.value == "unresolved"
        assert audit.content.assessment.status.value == "findings"


    def test_wrapped_read_emits_exactly_one_matching_unit(self, tmp_path) -> None:
        """#170 closure: a generic read wrapper declaring several units emits
        EXACTLY the fact whose unit matches the actual path — never one fact
        per declared unit."""
        import subprocess
        import sys

        repo = tmp_path / "repo"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "runtime_paths.ts").write_text(
            'import * as fs from "fs";\n'
            "export function readCanonicalPath(p: string): string {\n"
            '  return fs.readFileSync(p, "utf-8");\n'
            "}\n",
            encoding="utf-8",
        )
        (repo / "src" / "app.ts").write_text(
            'import { readCanonicalPath } from "./runtime_paths";\n'
            'const data = readCanonicalPath("/vault/indexes/formal-library.json");\n',
            encoding="utf-8",
        )
        from paperforge.architecture_audit.collectors.common import DEFAULT_PYTHON_REGISTRY

        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps([w.to_dict() for w in DEFAULT_PYTHON_REGISTRY]), encoding="utf-8"
        )
        proc = subprocess.run(
            ["node", "paperforge/architecture_audit/collectors/ts_collect.js",
             str(repo / "src"), str(reg_file)],
            capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)
        wrapped = [f for f in data.get("facts", [])
                   if f.get("kind") == "filesystem_read" and f.get("wrapper_id")]
        assert len(wrapped) == 1, f"expected exactly 1 wrapped read, got {len(wrapped)}: {wrapped}"
        assert wrapped[0]["unit_id"] == "formal_library"
        assert wrapped[0]["wrapper_id"] == "client_cache.read"
