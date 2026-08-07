#!/usr/bin/env python3
"""Architecture audit runner v2 (2026-08-06, post-review).

Fixes over v1:
- real revision SHA + dirty state (no more `HEAD`)
- honest coverage: manual_contract_trace=complete; python_ast/typescript_compiler
  = unavailable (collectors land in #133) -> assessment incomplete, gate false
- full publication-unit model (library/ocr_raw/ocr_derived/ocr_display/
  retrieval/vectors)
- test-backed evidence marked via extractor (e.g. "test:test_ocr_hash_contract")
- a real ArchitectureReview overlay (maintainer annotations live there, never
  in the deterministic view)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from paperforge.architecture_audit import (  # noqa: E402
    SCHEMA_VERSION,
    ArchitectureContract,
    ArchitectureReview,
    ArchitectureSurvey,
    compose,
    reconcile,
    validate_review,
)


def sha(file: str) -> str:
    return "sha256:" + hashlib.sha256((REPO / file).read_bytes()).hexdigest()


def git_rev() -> tuple[str, bool]:
    rev = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=REPO).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=REPO).stdout.strip())
    return rev, dirty


def find_symbol(file: str, symbol: str, span: int = 8) -> tuple[int, int]:
    lines = (REPO / file).read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines):
        if re.search(rf"\b{re.escape(symbol)}\b", line):
            return max(1, idx + 1), min(len(lines), idx + span)
    raise SystemExit(f"symbol {symbol} not found in {file}")


def evidence(file: str, symbol: str, span: int = 8, extractor: str = "manual_audit") -> dict:
    start, end = find_symbol(file, symbol, span)
    return {
        "file": file,
        "file_digest": sha(file),
        "symbol": symbol,
        "line_start": start,
        "line_end": end,
        "extractor": extractor,
        "epistemic_status": "observed_static",
        "confidence": "exact",
    }


def evidence_callsite(
    file: str,
    exact_text: str,
    symbol: str,
    enclosing: str | None = None,
    span: int = 1,
    extractor: str = "test:test_ocr_hash_contract",
) -> dict:
    """Locate a writer callsite by its exact source text (never hardcoded
    line numbers). Unique match required: missing text fails the build,
    ambiguous matches require an enclosing symbol and still fail otherwise."""
    lines = (REPO / file).read_text(encoding="utf-8").splitlines()
    matches = [idx for idx, line in enumerate(lines) if exact_text in line]
    if enclosing is not None:
        enc_start, enc_end = find_symbol(file, enclosing, span=max(len(lines), 1))
        matches = [idx for idx in matches if enc_start - 1 <= idx < enc_end]
    if not matches:
        raise SystemExit(f"callsite {exact_text!r} not found in {file}")
    if len(matches) > 1:
        detail = ", ".join(str(idx + 1) for idx in matches)
        raise SystemExit(f"callsite {exact_text!r} not unique in {file}: lines {detail}")
    start = matches[0] + 1
    return {
        "file": file,
        "file_digest": sha(file),
        "symbol": symbol,
        "line_start": start,
        "line_end": start + span - 1,
        "extractor": extractor,
        "epistemic_status": "observed_static",
        "confidence": "exact",
    }


# ---------------------------------------------------------------- contract

PUBLICATION_UNITS = [
    {"unit_id": "library.formal_note", "asset_group": "library",
     "publication_authority": "sync.publisher", "authorized_writers": ["sync.writer"]},
    {"unit_id": "library.formal_index", "asset_group": "library",
     "publication_authority": "index.publisher", "authorized_writers": ["asset_index.writer"]},
    {"unit_id": "ocr_raw.provider_result", "asset_group": "ocr_raw",
     "publication_authority": "ocr.publisher", "authorized_writers": ["ocr.provider"]},
    {"unit_id": "ocr_derived.generation", "asset_group": "ocr_derived",
     "publication_authority": "ocr.publisher",
     "authorized_writers": ["ocr.postprocess", "ocr.rebuild", "ocr.legacy_backfill"]},
    {"unit_id": "ocr_display.fulltext", "asset_group": "ocr_derived",
     "publication_authority": "version_history.authority",
     "authorized_writers": ["version_history.restore"]},
    {"unit_id": "retrieval.units", "asset_group": "retrieval",
     "publication_authority": "memory.publisher", "authorized_writers": ["memory.builder"]},
    {"unit_id": "retrieval.fts", "asset_group": "retrieval",
     "publication_authority": "memory.publisher", "authorized_writers": ["memory.builder"]},
    {"unit_id": "vectors.candidate_generation", "asset_group": "vectors",
     "publication_authority": "embed.publisher", "authorized_writers": ["embed.builder"]},
    {"unit_id": "vectors.live_generation", "asset_group": "vectors",
     "publication_authority": "embed.publisher", "authorized_writers": ["embed.publisher"]},
]

CONTRACT = {
    "schema_version": SCHEMA_VERSION,
    "asset_groups": ["library", "ocr_raw", "ocr_derived", "retrieval", "vectors"],
    "publication_units": PUBLICATION_UNITS,
    "operations": [
        "sync", "probe_status", "ocr_run", "ocr_rebuild", "ocr_redo",
        "embed_build_resume", "memory_build", "restore_display",
    ],
    "required_extractors": ["manual_contract_trace", "python_ast", "typescript_compiler"],
    "rules": [
        {
            "rule_id": "query.side_effect_free", "kind": "query_side_effect",
            "subject": "probe_status", "lifecycle": "active", "enforcement": "blocking",
            "description": "status queries must not mutate business facts",
        },
        {
            "rule_id": "remote_intent.sync_followup", "kind": "remote_intent",
            "subject": "sync", "lifecycle": "active", "enforcement": "blocking",
            "accepted_intent_modes": ["direct_invocation", "ui_modal", "explicit_flag", "interactive_prompt"],
            "description": "sync declares next_actions only; remote follow-ups require explicit intent (#127)",
        },
        {
            "rule_id": "signal.has_consumer", "kind": "signal_consumer",
            "subject": "OCR_REBUILD_PROGRESS", "lifecycle": "active", "enforcement": "blocking",
            "description": "rebuild progress signals have a code consumer (#126)",
        },
        {
            "rule_id": "publication.uses_protocol", "kind": "publication_marker",
            "subject": "ocr_derived.generation", "lifecycle": "active", "enforcement": "blocking",
            "description": "derived publications go through the result-hash pending protocol (#126)",
        },
        {
            "rule_id": "canonical.no_ui_writer", "kind": "canonical_writer",
            "subject": "ocr_derived.generation", "lifecycle": "active", "enforcement": "blocking",
            "description": "UI must not write canonical OCR state",
        },
        {
            "rule_id": "restore.display_only", "kind": "canonical_writer",
            "subject": "ocr_display.fulltext", "lifecycle": "active", "enforcement": "blocking",
            "description": "restore writes ONLY ocr_display.fulltext (render/fulltext.md) via the version-history service; never blocks/tree/role-index/units/vectors; records provenance and drift (#129)",
        },
        {
            "rule_id": "publication.authority_ocr_display", "kind": "publication_authority",
            "subject": "ocr_display.fulltext", "lifecycle": "active", "enforcement": "blocking",
            "description": "display fulltext has exactly one publication authority (version_history.authority)",
        },
        {
            "rule_id": "publication.authority_retrieval", "kind": "publication_authority",
            "subject": "retrieval.units", "lifecycle": "active", "enforcement": "blocking",
            "description": "retrieval units have exactly one publication authority (memory.publisher)",
        },
        {
            "rule_id": "coverage.required_complete", "kind": "coverage_complete",
            "subject": "", "lifecycle": "active", "enforcement": "blocking",
            "description": "required extractor coverage is complete",
        },
        {
            "rule_id": "retrieval.v2", "kind": "coverage_complete",
            "subject": "", "lifecycle": "planned", "enforcement": "blocking",
            "effective_after": {"issue": "#105"},
            "known_gap": {"issue": "#105", "rationale": "three-intent retrieval deferred post-release"},
            "description": "structure-aware retrieval v2",
        },
        {
            "rule_id": "collectors.deterministic", "kind": "coverage_complete",
            "subject": "", "lifecycle": "planned", "enforcement": "blocking",
            "effective_after": {"issue": "#133"},
            "known_gap": {"issue": "#133", "rationale": "deterministic collectors deferred until RC acceptance"},
            "description": "deterministic collectors feed the #131 reconciler",
        },
    ],
    "exceptions": [],
}

# ---------------------------------------------------------------- survey facts

SYNC_ACTIONS = find_symbol("paperforge/commands/sync.py", "_attach_next_actions")
SYNC_TERMINAL = find_symbol("paperforge/commands/sync.py", "_run_terminal_followups")
TOKEN = find_symbol("paperforge/commands/ocr.py", "OCR_REBUILD_RESULT")
PENDING = find_symbol("paperforge/worker/ocr_hash.py", "create_result_hash_pending")
PUBLISH = find_symbol("paperforge/worker/ocr_hash.py", "publish_ocr_result_hash")
RESTORE = find_symbol("paperforge/plugin/src/services/version-history.ts", "restoreVersion")
PROVENANCE = find_symbol("paperforge/plugin/src/services/version-history.ts", "persistRestoreProvenance")
REDO = find_symbol("paperforge/worker/ocr.py", "recover_redo_orphans")

SURVEY = {
    "schema_version": SCHEMA_VERSION,
    "scope": "paperforge",
    "coverage": [
        {"extractor": "manual_contract_trace", "status": "complete",
         "diagnostics": ()},
        {"extractor": "python_ast", "status": "unavailable",
         "diagnostics": ("#133 collector not implemented; manual trace only",)},
        {"extractor": "typescript_compiler", "status": "unavailable",
         "diagnostics": ("#133 collector not implemented; manual trace only",)},
    ],
    "facts": [
        {
            "kind": "effect", "operation_id": "sync", "effect_kind": "materialization_build",
            "evidence": evidence("paperforge/commands/sync.py", "_run_terminal_followups", extractor="test:test_sync_next_actions"),
        },
        {
            "kind": "effect", "operation_id": "ocr_rebuild", "effect_kind": "materialization_build",
            "evidence": evidence("paperforge/commands/ocr.py", "OCR_REBUILD_RESULT", extractor="test:test_ocr_progress_contracts"),
        },
        {
            "kind": "signal", "signal_id": "OCR_REBUILD_PROGRESS",
            "consumer_kind": "code", "has_code_consumer": True,
            "producer": "ocr.rebuild", "consumer": "paperforge-plugin",
            "evidence": evidence("paperforge/commands/ocr.py", "OCR_REBUILD_RESULT", extractor="test:test_ocr_progress_contracts"),
            "consumer_evidence": [evidence("paperforge/plugin/src/services/progress-parser.ts", "OCR_REBUILD", extractor="test:progress-parser")],
        },
        {
            "kind": "canonical_write", "unit_id": "ocr_derived.generation",
            "actor_kind": "worker", "writer_id": "ocr.rebuild", "via_publication_protocol": True,
            "evidence": evidence_callsite("paperforge/worker/ocr_rebuild.py",
                         "create_result_hash_pending(paper_root)",
                         "create_result_hash_pending(paper_root)"),
        },
        {
            "kind": "canonical_write", "unit_id": "ocr_derived.generation",
            "actor_kind": "worker", "writer_id": "ocr.rebuild", "via_publication_protocol": True,
            "evidence": evidence_callsite("paperforge/worker/ocr_rebuild.py",
                         "publish_ocr_result_hash(paper_root)",
                         "publish_ocr_result_hash(paper_root)",
                         span=2),
        },
        {
            "kind": "canonical_write", "unit_id": "ocr_derived.generation",
            "actor_kind": "worker", "writer_id": "ocr.postprocess", "via_publication_protocol": True,
            "evidence": evidence_callsite("paperforge/worker/ocr.py",
                         "create_result_hash_pending(ocr_root)",
                         "create_result_hash_pending(ocr_root)"),
        },
        {
            "kind": "canonical_write", "unit_id": "ocr_derived.generation",
            "actor_kind": "worker", "writer_id": "ocr.postprocess", "via_publication_protocol": True,
            "evidence": evidence_callsite("paperforge/worker/ocr.py",
                         "publish_ocr_result_hash(ocr_root)",
                         "publish_ocr_result_hash(ocr_root)",
                         span=2),
        },
        {
            "kind": "canonical_write", "unit_id": "ocr_display.fulltext",
            "actor_kind": "worker", "writer_id": "version_history.restore", "via_publication_protocol": True,
            "evidence": evidence("paperforge/plugin/src/services/version-history.ts", "restoreVersion", extractor="test:version-restore-semantics"),
        },
        {
            "kind": "canonical_write", "unit_id": "ocr_display.fulltext",
            "actor_kind": "worker", "writer_id": "version_history.restore", "via_publication_protocol": True,
            "evidence": evidence("paperforge/plugin/src/services/version-history.ts", "persistRestoreProvenance", extractor="test:version-restore-semantics"),
        },
        {
            "kind": "effect", "operation_id": "ocr_redo", "effect_kind": "materialization_build",
            "evidence": evidence("paperforge/worker/ocr.py", "recover_redo_orphans", extractor="test:test_redo_orphan_recovery"),
        },
    ],
    "source_digest": "",
    "parse_errors": [],
    "excluded_roots": [],
    "repository_state": {
        "revision": "pending",
        "dirty": True,
        "dirty_diff_digest": "pending",
    },
    "run_metadata": {
        "tool_version": "1.0.0",
        "extractor_versions": {"manual_contract_trace": "1", "python_ast": "unavailable", "typescript_compiler": "unavailable"},
        "generated_at": "2026-08-06T00:00:00Z",
    },
}

# ---------------------------------------------------------------- review overlay

REVIEW = {
    "schema_version": SCHEMA_VERSION,
    "reviewer_type": "maintainer_annotation",
    "contract_digest": "bound",
    "survey_digest": "bound",
    "audit_digest": "bound",
    "reconciler_version": "bound",
    "adjudications": [],
    "semantic_findings": [
        {
            "finding_id": "review:ocr_run_removed",
            "message": "OCR_RUN 死契约已移除（progress-parser 不再声明该前缀）；确认当前无后端发射方，删除是安全清理",
            "epistemic_status": "inferred",
        },
        {
            "finding_id": "review:coverage_honest",
            "message": "本报告证据为人工/测试支撑（extractor 标注 source）；python_ast/typescript_compiler 收集器在 #133 前标记 unavailable，gate 不可用是刻意保守",
            "epistemic_status": "inferred",
        },
        {
            "finding_id": "review:transaction_evidence_gap",
            "message": "事务/Stop/崩溃恢复等 blocking 性质仅有单元测试支撑（observed_static + test extractor），尚无 observed_runtime 事实；建议在 #133 阶段补充集成观测",
            "epistemic_status": "inferred",
        },
    ],
    "evidence_requests": [
        {
            "request_id": "req:unit_authority_facts",
            "subject": "publication_authority",
            "question": "为 library/ocr_raw/retrieval/vectors 各发布单元记录 unit-authority 观察事实（collector 或显式清单）",
        },
        {
            "request_id": "req:runtime_transaction_evidence",
            "subject": "ocr_derived.generation",
            "question": "故障注入/集成测试证明：中途失败 pending 保留、memory 跳过、旧 units/vectors 不清除（observed_runtime）",
        },
    ],
    "rationale": "维护者注解层：确定性 findings 之外的语义判断（已修复项、覆盖边界、证据缺口）全部收口在本 overlay，不进入 View 的 deterministic 投影",
    "run_metadata": {"model": "manual-maintainer-annotation", "created_at": "2026-08-06T00:00:00Z"},
}


# M5: adjudication rationale must match the finding's rule family.
ADJUDICATION_RATIONALES = {
    "query.side_effect_free": "probe/status callsites have not been fully enumerated by a collector (#133); current effect facts cannot prove the query is side-effect free",
    "remote_intent": "remote follow-up execution/confirmation chain is not fully enumerated; declaration facts do not prove intent on execution",
    "signal.": "signal producers/consumers are not fully enumerated; partial observations cannot prove all signals are consumed",
    "publication.uses_protocol": "publication writer callsites are not fully enumerated (postprocess/rebuild/backfill/memory); helper presence does not prove every writer obeys the protocol",
    "canonical.": "UI-writer absence cannot be proven while callsites are not fully enumerated",
    "restore.": "display-only write scope cannot be proven while TypeScript callsites are not fully enumerated",
    "publication.authority": "unit authority facts are not yet observed — a collector (#133) or explicit unit-authority fact is required before this edge can be judged",
    "coverage.": "required extractor coverage is incomplete; gate cannot open",
}


def adjudication_rationale(rule_id: str) -> str:
    for family, rationale in ADJUDICATION_RATIONALES.items():
        if rule_id.startswith(family):
            return rationale
    return "coverage incomplete: cannot enumerate all callsites; evidence required before judgement"


def main() -> int:
    rev, dirty = git_rev()
    diff_digest = ""
    if dirty:
        diff = subprocess.run(["git", "diff"], capture_output=True, text=True, cwd=REPO).stdout
        diff_digest = "sha256:" + hashlib.sha256(diff.encode("utf-8")).hexdigest()
    SURVEY["repository_state"] = {
        "revision": rev,
        "dirty": dirty,
        "dirty_diff_digest": diff_digest,
    }

    pairs = set()
    for fact in SURVEY["facts"]:
        for ev in ([fact.get("evidence")] if fact.get("evidence") else []) + list(fact.get("consumer_evidence", [])):
            pairs.add((ev["file"], ev["file_digest"]))
    aggregate = "\n".join(f"{f}\n{dg}" for f, dg in sorted(pairs))
    SURVEY["source_digest"] = "sha256:" + hashlib.sha256(aggregate.encode("utf-8")).hexdigest()

    contract = ArchitectureContract.from_dict(CONTRACT)
    survey = ArchitectureSurvey.from_dict(SURVEY)
    audit = reconcile(contract, survey)

    # review overlay bound to the real digests
    review_payload = dict(REVIEW)
    review_payload["contract_digest"] = audit.content.bound_contract_digest
    review_payload["survey_digest"] = audit.content.bound_survey_digest
    review_payload["audit_digest"] = audit.semantic_digest
    review_payload["reconciler_version"] = audit.content.reconciler_version
    unresolved = [f for f in audit.content.findings if f.rule_status.value == "unresolved"]
    adjudications = []
    for f in unresolved:
        adjudications.append({
            "finding_id": f.finding_id,
            "adjudication": "needs_evidence",
            "rationale": adjudication_rationale(f.rule_id),
            "epistemic_status": "unresolved",
        })
    review_payload["adjudications"] = adjudications
    review = ArchitectureReview.from_dict(review_payload)
    validate_review(review, audit)
    view = compose(audit, review)

    summary = {
        "revision": rev,
        "dirty": dirty,
        "assessment": audit.content.assessment.status.value,
        "gate_eligible": audit.content.assessment.gate_eligible,
        "reasons": list(audit.content.assessment.reasons),
        "findings": [
            {
                "rule_id": f.rule_id, "subject": f.subject,
                "status": f.rule_status.value, "severity": f.severity,
                "message": f.message, "finding_id": f.finding_id,
                "evidence": [{"file": e.file, "symbol": e.symbol, "lines": f"{e.line_start}-{e.line_end}", "extractor": e.extractor} for e in f.evidence],
            }
            for f in audit.content.findings
        ],
        "coverage": [{"extractor": c.extractor, "status": c.status.value, "required": c.required} for c in audit.content.coverage],
        "digests": {
            "audit": audit.semantic_digest,
            "contract": audit.content.bound_contract_digest,
            "survey": audit.content.bound_survey_digest,
            "review": view.review_digest,
            "reconciler": audit.content.reconciler_version,
        },
        "review": {
            "reviewer_type": review.reviewer_type,
            "adjudications": [a.to_dict() for a in review.adjudications],
            "semantic_findings": [s.to_dict() for s in review.semantic_findings],
            "evidence_requests": [r.to_dict() for r in review.evidence_requests],
            "rationale": review.rationale,
        },
    }

    # M4: step-level trace manifest — every step carries its own evidence ids,
    # null references are forbidden (a missing id makes the step unresolved),
    # and the aggregate status is derived from the steps.
    ev_pool = {}
    for fact in survey.facts:
        for ev in ([fact.evidence] if getattr(fact, "evidence", None) else []) + list(getattr(fact, "consumer_evidence", ()) or []):
            ev_pool[ev.symbol] = ev.evidence_id

    def step(step_id: str, description: str, evidence_symbols: list[str]) -> dict:
        ids = []
        for symbol in evidence_symbols:
            eid = ev_pool.get(symbol)
            if eid is None:
                raise SystemExit(f"trace step {step_id}: evidence symbol {symbol!r} not resolvable")
            ids.append(eid)
        return {
            "step_id": step_id,
            "description": description,
            "status": "observed" if ids else "unresolved",
            "evidence_ids": ids,
        }

    traces = [
        {
            "name": "sync → memory → embed",
            "steps": [
                step("sync.1", "CLI sync (direct invocation)", []),
                step("sync.2", "svc.run(): zotero sync + index", []),
                step("sync.3", "terminal runner executes automatic-local memory.build", ["_run_terminal_followups"]),
                step("sync.4", "plugin confirmation for embed.resume (remote)", []),
            ],
        },
        {
            "name": "ocr rebuild → publication → memory",
            "steps": [
                step("rebuild.1", "ocr rebuild (keys/--all)", []),
                step("rebuild.2", "START/PROGRESS/RESULT/DONE tokens per key", ["OCR_REBUILD_RESULT"]),
                step("rebuild.3", "result-hash.pending created before mutation", ["create_result_hash_pending(paper_root)"]),
                step("rebuild.4", "publish + clear on verified success (commit point)", ["publish_ocr_result_hash(paper_root)"]),
                step("rebuild.5", "memory build on successKeys>0 · confirmed embed resume", []),
            ],
        },
        {
            "name": "version restore (display only)",
            "steps": [
                step("restore.1", "restore 恢复展示全文文本 + confirmation", []),
                step("restore.2", "copy versions/<label>/fulltext.md → render/ only", ["restoreVersion"]),
                step("restore.3", "provenance + drift override (DRIFTED if older)", ["persistRestoreProvenance"]),
            ],
        },
        {
            "name": "redo (internal only)",
            "steps": [
                step("redo.1", "CLI ocr redo (maintainers)", []),
                step("redo.2", "transaction snapshot → mutate → validate → commit/rollback", []),
                step("redo.3", "crash-orphan recovery from paperforge-redo-*", ["recover_redo_orphans"]),
                step("redo.4", "no user-facing entry (ribbon/command/probe/maintenance)", []),
            ],
        },
    ]
    for tr in traces:
        statuses = {s["status"] for s in tr["steps"]}
        if "violated" in statuses:
            tr["status"] = "violated"
        elif "unresolved" in statuses:
            tr["status"] = "partial"
        else:
            tr["status"] = "ok"
    (HERE / "traces.json").write_text(json.dumps(traces, indent=2, ensure_ascii=False), encoding="utf-8")

    HERE.mkdir(parents=True, exist_ok=True)
    for name, payload in [("contract", CONTRACT), ("survey", survey.to_dict()), ("audit", audit.to_dict()),
                          ("review", review.to_dict()), ("view", view.to_dict()), ("summary", summary)]:
        (HERE / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
