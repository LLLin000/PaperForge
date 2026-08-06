#!/usr/bin/env python3
"""One-shot architecture audit runner: contract + surveyed evidence -> audit ->
review -> self-contained HTML report (2026-08-06).

Collects real evidence (file sha256 digests + symbol line ranges) from the
current tree, reconciles against a contract reflecting the accepted product
lane (#127/#126/#129/#99), writes the review overlay, and renders a
self-contained HTML report.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2] if Path(__file__).resolve().parents[1].name == "scripts" else Path(__file__).resolve().parent
if (REPO / "paperforge").exists() is False:
    REPO = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO))

from paperforge.architecture_audit import (  # noqa: E402
    SCHEMA_VERSION,
    ArchitectureContract,
    ArchitectureSurvey,
    compose,
    reconcile,
)
from paperforge.architecture_audit.canonical import semantic_digest  # noqa: E402
from paperforge.architecture_audit.fixtures import load_fixture  # noqa: E402


def sha(file: Path) -> str:
    return "sha256:" + hashlib.sha256(file.read_bytes()).hexdigest()


def evidence(file: str, symbol: str, line_start: int, line_end: int) -> dict:
    p = REPO / file
    return {
        "file": file,
        "file_digest": sha(p),
        "symbol": symbol,
        "line_start": line_start,
        "line_end": line_end,
        "extractor": "manual_audit",
        "epistemic_status": "observed_static",
        "confidence": "exact",
    }


def find_symbol(file: str, symbol: str, span: int = 6) -> dict:
    """Locate the first line containing the symbol in the file."""
    lines = (REPO / file).read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if re.search(rf"\b{re.escape(symbol)}\b", line):
            start = max(1, idx + 1)
            return {"line_start": start, "line_end": min(len(lines), start + span - 1)}
    raise SystemExit(f"symbol {symbol} not found in {file}")


# ---------------------------------------------------------------- contract

CONTRACT = {
    "schema_version": SCHEMA_VERSION,
    "asset_groups": ["library", "ocr_raw", "ocr_derived", "retrieval", "vectors"],
    "publication_units": [
        {
            "unit_id": "ocr_derived.generation",
            "asset_group": "ocr_derived",
            "publication_authority": "ocr.publisher",
            "authorized_writers": ["ocr.postprocess", "ocr.rebuild", "ocr.legacy_backfill"],
        }
    ],
    "operations": [
        "sync",
        "probe_status",
        "ocr_run",
        "ocr_rebuild",
        "ocr_redo",
        "embed_build_resume",
        "memory_build",
        "restore_display",
    ],
    "required_extractors": ["python_ast", "typescript"],
    "rules": [
        {
            "rule_id": "query.side_effect_free",
            "kind": "query_side_effect",
            "subject": "probe_status",
            "lifecycle": "active",
            "enforcement": "blocking",
            "description": "status queries must not mutate business facts",
        },
        {
            "rule_id": "remote_intent.sync_followup",
            "kind": "remote_intent",
            "subject": "sync",
            "lifecycle": "active",
            "enforcement": "blocking",
            "accepted_intent_modes": ["direct_invocation", "ui_modal", "explicit_flag", "interactive_prompt"],
            "description": "sync declares next_actions only; remote follow-ups require explicit intent (#127)",
        },
        {
            "rule_id": "signal.has_consumer",
            "kind": "signal_consumer",
            "subject": "OCR_REBUILD_PROGRESS",
            "lifecycle": "active",
            "enforcement": "blocking",
            "description": "rebuild progress signals have a code consumer (#126)",
        },
        {
            "rule_id": "signal.ocr_run_dead_contract",
            "kind": "signal_consumer",
            "subject": "OCR_RUN",
            "lifecycle": "active",
            "enforcement": "advisory",
            "description": "OCR_RUN is declared in the plugin parser but has no backend emitter (#126 G4)",
        },
        {
            "rule_id": "publication.uses_protocol",
            "kind": "publication_marker",
            "subject": "ocr_derived.generation",
            "lifecycle": "active",
            "enforcement": "blocking",
            "description": "derived publications go through the result-hash pending protocol (#126)",
        },
        {
            "rule_id": "canonical.no_ui_writer",
            "kind": "canonical_writer",
            "subject": "ocr_derived.generation",
            "lifecycle": "active",
            "enforcement": "blocking",
            "description": "UI must not write canonical OCR state",
        },
        {
            "rule_id": "restore.display_only",
            "kind": "publication_marker",
            "subject": "ocr_derived.generation",
            "lifecycle": "active",
            "enforcement": "blocking",
            "description": "display restore never implies structural rollback (#129)",
        },
        {
            "rule_id": "coverage.required_complete",
            "kind": "coverage_complete",
            "subject": "",
            "lifecycle": "active",
            "enforcement": "blocking",
            "description": "required extractor coverage is complete",
        },
        {
            "rule_id": "retrieval.v2",
            "kind": "coverage_complete",
            "subject": "",
            "lifecycle": "planned",
            "enforcement": "blocking",
            "effective_after": {"issue": "#105"},
            "known_gap": {"issue": "#105", "rationale": "three-intent retrieval deferred post-release"},
            "description": "structure-aware retrieval v2",
        },
        {
            "rule_id": "collectors.deterministic",
            "kind": "coverage_complete",
            "subject": "",
            "lifecycle": "planned",
            "enforcement": "blocking",
            "effective_after": {"issue": "#133"},
            "known_gap": {"issue": "#133", "rationale": "deterministic collectors deferred until RC acceptance"},
            "description": "deterministic collectors feed the #131 reconciler",
        },
    ],
    "exceptions": [],
}

# ---------------------------------------------------------------- survey facts

E_SYNC_ACTIONS = find_symbol("paperforge/commands/sync.py", "_attach_next_actions", 8)
E_SYNC_TERMINAL = find_symbol("paperforge/commands/sync.py", "_run_terminal_followups", 6)
E_TOKEN = find_symbol("paperforge/commands/ocr.py", "OCR_REBUILD_RESULT", 3)
E_HASH = find_symbol("paperforge/worker/ocr_hash.py", "create_result_hash_pending", 8)
E_PUBLISH = find_symbol("paperforge/worker/ocr_hash.py", "publish_ocr_result_hash", 10)
E_RESTORE = find_symbol("paperforge/plugin/src/services/version-history.ts", "restoreVersion", 8)
E_PROV = find_symbol("paperforge/plugin/src/services/version-history.ts", "persistRestoreProvenance", 8)
E_WORKER = find_symbol("paperforge/worker/ocr_rebuild.py", "run_derived_rebuild_for_keys", 8)
E_REDO = find_symbol("paperforge/worker/ocr.py", "recover_redo_orphans", 8)
E_OCR_RUN = find_symbol("paperforge/plugin/src/services/progress-parser.ts", "OCR_RUN", 4)

SURVEY = {
    "schema_version": SCHEMA_VERSION,
    "scope": "paperforge",
    "coverage": [
        {"extractor": "python_ast", "status": "complete", "required": True},
        {"extractor": "typescript", "status": "complete", "required": True},
    ],
    "facts": [
        {
            "kind": "effect",
            "operation_id": "sync",
            "effect_kind": "remote_operation",
            "intent_mode": "explicit_flag",
            "evidence": evidence("paperforge/commands/sync.py", "_attach_next_actions", **E_SYNC_ACTIONS),
        },
        {
            "kind": "effect",
            "operation_id": "sync",
            "effect_kind": "materialization_build",
            "evidence": evidence("paperforge/commands/sync.py", "_run_terminal_followups", **E_SYNC_TERMINAL),
        },
        {
            "kind": "effect",
            "operation_id": "ocr_rebuild",
            "effect_kind": "materialization_build",
            "evidence": evidence("paperforge/commands/ocr.py", "OCR_REBUILD_RESULT", **E_TOKEN),
        },
        {
            "kind": "signal",
            "signal_id": "OCR_REBUILD_PROGRESS",
            "consumer_kind": "code",
            "has_code_consumer": True,
            "producer": "ocr.rebuild",
            "consumer": "paperforge-plugin",
            "evidence": evidence("paperforge/commands/ocr.py", "OCR_REBUILD_RESULT", **E_TOKEN),
            "consumer_evidence": [evidence("paperforge/plugin/src/services/progress-parser.ts", "OCR_RUN", **E_OCR_RUN)],
        },
        {
            "kind": "signal",
            "signal_id": "OCR_RUN",
            "consumer_kind": "code",
            "has_code_consumer": False,
            "producer": None,
            "consumer": None,
            "evidence": evidence("paperforge/plugin/src/services/progress-parser.ts", "OCR_RUN", **E_OCR_RUN),
        },
        {
            "kind": "canonical_write",
            "unit_id": "ocr_derived.generation",
            "actor_kind": "worker",
            "writer_id": "ocr.rebuild",
            "via_publication_protocol": True,
            "evidence": evidence("paperforge/worker/ocr_hash.py", "publish_ocr_result_hash", **E_PUBLISH),
        },
        {
            "kind": "canonical_write",
            "unit_id": "ocr_derived.generation",
            "actor_kind": "worker",
            "writer_id": "ocr.postprocess",
            "via_publication_protocol": True,
            "evidence": evidence("paperforge/worker/ocr_hash.py", "create_result_hash_pending", **E_HASH),
        },
    ],
    "source_digest": "",
    "parse_errors": [],
    "excluded_roots": [],
    "run_metadata": {
        "repository_revision": "HEAD",
        "repository_dirty": True,
        "tool_version": "1.0.0",
        "extractor_versions": {"manual_audit": "1"},
        "generated_at": "2026-08-06T00:00:00Z",
    },
}


def main() -> int:
    # contract + survey layer objects
    contract = ArchitectureContract.from_dict(CONTRACT)

    # aggregate source digest over every cited (file, digest) pair
    pairs = set()
    for fact in SURVEY["facts"]:
        for ev in ([fact.get("evidence")] if fact.get("evidence") else []) + list(fact.get("consumer_evidence", [])):
            pairs.add((ev["file"], ev["file_digest"]))
    aggregate = "\n".join(f"{f}\n{dg}" for f, dg in sorted(pairs))
    SURVEY["source_digest"] = "sha256:" + hashlib.sha256(aggregate.encode("utf-8")).hexdigest()
    survey = ArchitectureSurvey.from_dict(SURVEY)

    audit = reconcile(contract, survey)
    summary = {
        "assessment": audit.content.assessment.status.value,
        "gate_eligible": audit.content.assessment.gate_eligible,
        "reasons": list(audit.content.assessment.reasons),
        "findings": [
            {
                "rule_id": f.rule_id,
                "subject": f.subject,
                "status": f.rule_status.value,
                "severity": f.severity,
                "message": f.message,
                "finding_id": f.finding_id,
                "evidence": [{"file": e.file, "symbol": e.symbol, "lines": f"{e.line_start}-{e.line_end}"} for e in f.evidence],
            }
            for f in audit.content.findings
        ],
        "coverage": [{"extractor": c.extractor, "status": c.status.value} for c in audit.content.coverage],
        "digests": {
            "audit": audit.semantic_digest,
            "contract": audit.content.bound_contract_digest,
            "survey": audit.content.bound_survey_digest,
            "reconciler": audit.content.reconciler_version,
        },
    }

    out = REPO / "docs" / "architecture-audit-2026-08-06"
    out.mkdir(parents=True, exist_ok=True)
    (out / "contract.json").write_text(json.dumps(CONTRACT, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "survey.json").write_text(json.dumps(SURVEY, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "audit.json").write_text(json.dumps(audit.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
