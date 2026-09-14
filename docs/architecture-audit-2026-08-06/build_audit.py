#!/usr/bin/env python3
"""Generate the architecture contract and current collector-backed report.

`CONTRACT` is the reviewed policy source. The deterministic Survey is always
collected from the live repository by the #133 orchestrator; this script does
not carry a second hand-written fact inventory.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from paperforge.architecture_audit import (  # noqa: E402
    SCHEMA_VERSION,
    ArchitectureContract,
    ArchitectureReview,
    canonical_json,
    compose,
    validate_review,
)

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
        # Operation ids are module stems (collectors/common.py:operation_id_of).
        # `probe_status` was a historical alias for a file that is probe.py, so
        # the rule below could never receive a fact; the read/report surfaces
        # are declared by the stem the collector actually binds (#220).
        "sync", "probe", "status", "dashboard", "runtime_health",
        "ocr_redo", "memory_build", "restore_display",
        {
            "operation_id": "ocr_run",
            "authorities": [
                {"role": "execution", "authority_id": "backend.ocr.executor", "observers": ["plugin.ocr_process_controller"]},
                {"role": "stop", "authority_id": "plugin.ocr_process_controller", "delegated_executors": ["cli.cooperative_stop"]},
            ],
        },
        {
            "operation_id": "ocr_rebuild",
            "authorities": [
                {"role": "execution", "authority_id": "backend.ocr.executor", "observers": ["plugin.ocr_process_controller"]},
                {"role": "stop", "authority_id": "plugin.ocr_process_controller", "delegated_executors": ["cli.cooperative_stop"]},
            ],
        },
        {
            "operation_id": "embed_build_resume",
            "authorities": [
                {"role": "execution", "authority_id": "backend.embed.executor"},
                {"role": "lifecycle_state", "authority_id": "plugin.embed_build_controller"},
                {"role": "stop", "authority_id": "plugin.embed_build_controller"},
            ],
        },
    ],
    # Manual materials (maintainer annotations, golden traces) live in the
    # ArchitectureReview overlay — they are no longer a deterministic Survey
    # input, so they must not gate the deterministic audit.
    "required_extractors": ["python_ast", "typescript_compiler"],
    "rules": [
        {
            "rule_id": "role_authority.ocr_execution", "kind": "role_authority",
            "subject": "ocr_run", "authority_role": "execution",
            "lifecycle": "active", "enforcement": "blocking",
            "description": "OCR run/re-build execution has exactly one authority (backend executor); the plugin controller is an observer",
        },
        {
            "rule_id": "role_authority.ocr_stop", "kind": "role_authority",
            "subject": "ocr_rebuild", "authority_role": "stop",
            "lifecycle": "active", "enforcement": "blocking",
            "description": "Cooperative stop has exactly one authority (plugin controller) with a delegated backend executor",
        },
        {
            "rule_id": "role_authority.embed_stop", "kind": "role_authority",
            "subject": "embed_build_resume", "authority_role": "stop",
            "lifecycle": "active", "enforcement": "blocking",
            "description": "Embed build stop has exactly one authority (plugin controller)",
        },
        {
            "rule_id": "query.side_effect_free.probe", "kind": "query_side_effect",
            "subject": "probe", "lifecycle": "active", "enforcement": "blocking",
            "description": "the capability probe is an observation surface and must not mutate business facts",
        },
        {
            "rule_id": "query.side_effect_free.status", "kind": "query_side_effect",
            "subject": "status", "lifecycle": "active", "enforcement": "blocking",
            "description": "the status report must not mutate business facts",
        },
        {
            "rule_id": "query.side_effect_free.dashboard", "kind": "query_side_effect",
            "subject": "dashboard", "lifecycle": "active", "enforcement": "blocking",
            "description": "the dashboard aggregate must not mutate business facts",
        },
        {
            "rule_id": "query.side_effect_free.runtime_health", "kind": "query_side_effect",
            "subject": "runtime_health", "lifecycle": "active", "enforcement": "blocking",
            "description": "the runtime health check must not mutate business facts",
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
            "subject": "", "lifecycle": "active", "enforcement": "blocking",
            "effective_after": {"issue": "#133", "commit": "815dc615"},
            "description": "deterministic collectors feed the #131 reconciler (#133 accepted 2026-08-07)",
        },
    ],
    "exceptions": [],
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
            "message": "Survey 由 #133 确定性收集器生成（python_ast + typescript_compiler）；人工材料（golden trace、maintainer annotation）归入 ArchitectureReview overlay，不再作为 deterministic 输入",
            "epistemic_status": "inferred",
        },
        {
            "finding_id": "review:transaction_evidence_gap",
            "message": "事务/Stop/崩溃恢复等 blocking 性质仅有单元测试支撑（observed_static + test extractor），尚无 observed_runtime 事实；建议后续补充集成观测/故障注入",
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
            "request_id": "req:operation_authority_facts",
            "subject": "role_authority",
            "question": "为 ocr_run/ocr_rebuild/embed_build_resume 记录 execution/lifecycle_state/stop 权威观察事实（controller 单 owner + 无第二 UI 入口的集成确认）",
        },
        {
            "request_id": "req:runtime_transaction_evidence",
            "subject": "ocr_derived.generation",
            "question": "故障注入/集成测试证明：中途失败 pending 保留、memory 跳过、旧 units/vectors 不清除（observed_runtime）",
        },
    ],
    "rationale": "维护者注解层：确定性 findings 之外的语义判断（已修复项、覆盖边界、证据缺口）全部收口在本 overlay，不进入 View 的 deterministic 投影",
    "run_metadata": {"model": "manual-maintainer-annotation", "created_at": datetime.now(timezone.utc).isoformat()},
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


def _assert_contract_artifact_matches(expected: dict, artifact_path: Path) -> None:
    """Fail `--check` when the committed policy projection is stale."""
    try:
        actual = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read committed contract artifact {artifact_path}: {exc}") from exc
    if canonical_json(actual) != canonical_json(expected):
        raise SystemExit(
            f"committed contract artifact {artifact_path} does not match CONTRACT; "
            "regenerate it with build_audit.py"
        )


def main(*, write_outputs: bool = True) -> int:
    # Survey is produced by the #133 deterministic collectors (Python AST
    # + TypeScript compiler), not hand-written facts. The maintainer overlay
    # (REVIEW) stays the only hand-authored layer — bound to the real digests.
    from paperforge.architecture_audit.collectors.orchestrator import collect

    contract = ArchitectureContract.from_dict(CONTRACT)
    if not write_outputs:
        _assert_contract_artifact_matches(CONTRACT, HERE / "contract.json")
    outcome = collect(
        REPO,
        contract=contract,
        py_roots=("paperforge",),
        ts_roots=("paperforge/plugin/src",),
        node_cmd="node",
    )
    survey = outcome.survey
    audit = outcome.audit
    if survey is None or audit is None:
        raise SystemExit("collector did not produce a Survey and Audit")
    rev = survey.repository_state.revision
    dirty = survey.repository_state.dirty

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
    # and the aggregate status is derived from the steps. Evidence ids come
    # from the collector survey; wrapper steps resolve via wrapper_hits.
    ev_pool: dict[str, str] = {}
    for fact in survey.facts:
        for ev in ([fact.evidence] if getattr(fact, "evidence", None) else []) + list(getattr(fact, "consumer_evidence", ()) or []):
            ev_pool[f"{ev.file}:{ev.line_start}"] = ev.evidence_id
    wrapper_ev: dict[str, str] = {}
    for hit in outcome.wrapper_hits:
        key = f"{hit['file']}:{hit['line']}"
        if key in ev_pool:
            wrapper_ev.setdefault(hit["qualified_name"], ev_pool[key])

    def step(step_id: str, description: str, evidence_refs: list[str]) -> dict:
        ids = []
        for ref in evidence_refs:
            eid = wrapper_ev.get(ref) or ev_pool.get(ref)
            if eid is None:
                raise SystemExit(f"trace step {step_id}: evidence ref {ref!r} not resolvable")
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
                step("sync.3", "sync derives and runs the generic follow-up chain", ["sync._reconcile_and_attach"]),
                step("sync.4", "plugin confirmation for embed.resume (remote)", []),
            ],
        },
        {
            "name": "ocr rebuild → publication → memory",
            "steps": [
                step("rebuild.1", "ocr rebuild (keys/--all)", []),
                step("rebuild.2", "START/PROGRESS/RESULT/DONE tokens per key", []),
                step("rebuild.3", "result-hash.pending created before mutation", ["ocr_hash.create_result_hash_pending"]),
                step("rebuild.4", "publish + clear on verified success (commit point)", ["ocr_hash.publish_ocr_result_hash"]),
                step("rebuild.5", "memory build on successKeys>0 · confirmed embed resume", []),
            ],
        },
        {
            "name": "version restore (display only)",
            "steps": [
                step("restore.1", "restore 恢复展示全文文本 + confirmation", []),
                step("restore.2", "copy versions/<label>/fulltext.md → render/ only", []),
                step("restore.3", "provenance + drift override (DRIFTED if older)", []),
            ],
        },
        {
            "name": "redo (internal only)",
            "steps": [
                step("redo.1", "CLI ocr redo (maintainers)", []),
                step("redo.2", "transaction snapshot → mutate → validate → commit/rollback", []),
                step("redo.3", "crash-orphan recovery from paperforge-redo-*", ["ocr.recover_redo_orphans"]),
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

    if write_outputs:
        (HERE / "traces.json").write_text(
            json.dumps(traces, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        HERE.mkdir(parents=True, exist_ok=True)
        for name, payload in [
            ("contract", CONTRACT),
            ("survey", survey.to_dict()),
            ("audit", audit.to_dict()),
            ("review", review.to_dict()),
            ("view", view.to_dict()),
            ("summary", summary),
        ]:
            (HERE / f"{name}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="collect and validate without rewriting generated artifacts",
    )
    raise SystemExit(main(write_outputs=not parser.parse_args().check))
