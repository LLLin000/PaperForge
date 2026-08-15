"""Reconcile module (#166 / T5, #159 §3).

Three-layer observation (global desired → global substrate → per-paper
lineage) → global repair frontier first → per-paper minimal repair frontier
→ scope merging by canonical action → single PFResult.next_actions channel.

PURE derivation + intent emission: no side effects, idempotent (same facts
→ same result).  Reconcile decides the OPERATION; cost/confirmation come
from the #145 registry.  No DAG engine, no retry history tables.

W2 not-a-retry (#158, #166 acceptance): re-emission is gated on a changed
input digest + a failed last-attempt record.  The record is overwrite-only
per canonical (action, scope) — one bounded row, no history.  The digest
covers the SEMANTIC observation that drove the intent (facet states +
lineage identities), so a stale caused by R1 is distinguishable from one
caused by R2.  `record_last_attempt` is the write side; the T6 runner calls
it when an action attempt settles.  reconcile() itself only reads.

Layer discipline (owner review 2026-08-11): materialization/substrate
≠ action availability.  Credential availability lives in ActionPreflight
(registry); it never flips substrate state and never blocks unrelated
OCR/retrieval repair.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperforge.actions.registry import emit_next_action
from paperforge.actions.types import ActionIntent, AllScope, PapersScope
from paperforge.core.result import PFResult

# ── W2 last-attempt record (overwrite-only, bounded, no history) ──────────

LAST_ATTEMPT_FILENAME = "reconcile-last-attempts.json"


def last_attempt_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths

    return paperforge_paths(vault)["paperforge"] / "state" / LAST_ATTEMPT_FILENAME


def _canonical_key(action_id: str, scope: AllScope | PapersScope) -> str:
    if scope.kind == "papers":
        return f"{action_id}:papers:{','.join(sorted(scope.keys))}"
    return f"{action_id}:all"


def read_last_attempts(vault: Path) -> dict[str, dict[str, Any]]:
    """Read the overwrite-only last-attempt record (read-only, pure)."""
    path = last_attempt_path(vault)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def record_last_attempt(
    vault: Path,
    *,
    action_id: str,
    scope: AllScope | PapersScope,
    input_digest: str,
    outcome: str,
    error_code: str = "",
) -> None:
    """Overwrite-only write of the last attempt for (action, canonical
    scope).  Never grows history.  Called by the execution side (T6 runner)
    when an attempt settles; reconcile() itself never writes."""
    attempts = read_last_attempts(vault)
    attempts[_canonical_key(action_id, scope)] = {
        "action_id": action_id,
        "scope_kind": scope.kind,
        "scope_keys": sorted(scope.keys) if scope.kind == "papers" else [],
        "input_digest": input_digest,
        "outcome": outcome,
        "error_code": error_code,
        "updated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
    path = last_attempt_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(attempts, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


# ── observation ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GlobalObservation:
    memory_substrate_ok: bool
    vector_substrate_ok: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperObservation:
    key: str
    ocr: str  # current | stale | missing | running | unknown | incomplete | failed
    retrieval: str  # current | stale | missing | unknown | incomplete
    vector: str  # current | stale | missing | not_required | unknown | incomplete
    identities: dict[str, str | None]  # internal digest material (W2)
    details: dict[str, str | None] | None = None  # fine-grained per-layer WHY


@dataclass(frozen=True)
class ReconcileObservation:
    global_state: GlobalObservation
    papers: tuple[PaperObservation, ...] = ()
    vault: Path | None = None
    orphan_count: int = 0
    orphan_keys: tuple[str, ...] = ()
    residual_count: int = 0
    residual_keys: tuple[str, ...] = ()

    def by_key(self) -> dict[str, PaperObservation]:
        return {p.key: p for p in self.papers}


def observe_global(vault: Path) -> GlobalObservation:
    """Global substrate vs desired state (#159 §2.1/§2.2).

    - memory substrate: memory DB present and schema current
    - vector substrate: DESIRED embedding identity (config) vs PUBLISHED
      substrate identity/layout (build_state + vec0 DDL) — NOT credential
      availability, which belongs to ActionPreflight (#166 P0-1)
    """
    reasons: list[str] = []
    memory_ok = True
    vector_ok = True

    from paperforge.config import paperforge_paths
    from paperforge.memory.schema import CURRENT_SCHEMA_VERSION

    db_path = paperforge_paths(vault)["paperforge"] / "indexes" / "paperforge.db"
    if not db_path.exists():
        memory_ok = False
        reasons.append("memory.db_missing")
    else:
        try:
            import sqlite3

            conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                row = conn.execute(
                    "SELECT value FROM meta WHERE key='schema_version'"
                ).fetchone()
                version = int(row[0]) if row else 0
                if version != CURRENT_SCHEMA_VERSION:
                    memory_ok = False
                    reasons.append(f"memory.schema_mismatch({version}->{CURRENT_SCHEMA_VERSION})")
            finally:
                conn.close()
        except Exception:  # noqa: BLE001
            memory_ok = False
            reasons.append("memory.unreadable")

    if not memory_ok:
        vector_ok = False
        reasons.append("vector.blocked_by_memory")
    else:
        from paperforge.embedding.substrate import assess_vector_substrate

        substrate = assess_vector_substrate(vault)
        vector_ok = substrate.compatible
        if not vector_ok:
            reasons.extend(r for r in substrate.reason_codes if r.startswith("vector."))

    return GlobalObservation(
        memory_substrate_ok=memory_ok,
        vector_substrate_ok=vector_ok,
        reasons=tuple(reasons),
    )


def observe_papers(
    vault: Path, keys: list[str] | None = None
) -> tuple[tuple[PaperObservation, ...], dict[str, object]]:
    """Per-paper lineage facets + identities (T1 probe read model).

    Also returns the library-level orphan state from the SAME probe call
    (统一出统一回): workspace papers absent from the canonical index are a
    first-class state — reconcile turns them into a library.prune intent."""
    from paperforge.lineage import probe_lineage

    payload = probe_lineage(vault)
    papers = payload.get("papers", {})
    identities = payload.get("identities", {})
    wanted = set(keys) if keys is not None else None
    out: list[PaperObservation] = []
    for key, states in papers.items():
        if wanted is not None and key not in wanted:
            continue
        out.append(PaperObservation(
            key=key,
            ocr=str(states.get("ocr", "unknown")),
            retrieval=str(states.get("retrieval", "unknown")),
            vector=str(states.get("vector", "unknown")),
            identities=dict(identities.get(key, {})),
            details=states.get("details"),
        ))
    orphan = payload.get("orphan", {}) or {}
    residuals = payload.get("residuals", {}) or {}
    return (
        tuple(sorted(out, key=lambda p: p.key)),
        {
            "count": int(orphan.get("count", 0) or 0),
            "keys": tuple(orphan.get("keys", []) or []),
        },
        {
            "count": int(residuals.get("count", 0) or 0),
            "keys": tuple(residuals.get("keys", []) or []),
        },
    )


def observe(vault: Path, keys: list[str] | None = None) -> ReconcileObservation:
    papers, orphan, residuals = observe_papers(vault, keys)
    return ReconcileObservation(
        global_state=observe_global(vault),
        papers=papers,
        vault=vault,
        orphan_count=int(orphan["count"]),
        orphan_keys=orphan["keys"],
        residual_count=int(residuals["count"]),
        residual_keys=residuals["keys"],
    )


def _facet_summary(obs: ReconcileObservation) -> dict[str, int]:
    """Derived from obs.papers FIRST — independent of global-first returns,
    so a blocked_global payload still reports the observed facets (#166
    P1-3)."""
    summary = {"current": 0, "stale": 0, "missing": 0, "unknown": 0}
    for paper in obs.papers:
        for layer in ("ocr", "retrieval", "vector"):
            state = getattr(paper, layer)
            summary[state] = summary.get(state, 0) + 1
    return summary


# ── deficit → operation (operation decided here; policy from registry) ────

# Per-paper minimal frontier: first-layer unsatisfied facets whose
# prerequisites are satisfied.  Lineage edges: ocr → retrieval → vector.
def _per_paper_intents(paper: PaperObservation) -> list[ActionIntent]:
    intents: list[ActionIntent] = []
    scope = PapersScope((paper.key,))

    # OCR is the root layer — no prerequisite.  Operation distinction
    # (#168 T7 P0-1, frozen #159 deficit table): raw/missing OCR output
    # needs the remote ocr.run; DERIVED-artifact staleness (raw blocks
    # unchanged, derived rebuild pending) is the LOCAL ocr.rebuild_derived.
    # The fine-grained state machine (probe lineage details) distinguishes
    # never-ran / queued / failed / no-pdf / ran-empty / incomplete so the
    # emitted reason names the exact meaning.
    ocr_detail = (paper.details or {}).get("ocr") if paper.details else None
    if paper.ocr == "missing":
        if ocr_detail == "queued":
            return intents  # in flight — nothing to dispatch
        if ocr_detail in ("no_pdf", "blocked"):
            # No executable OCR intent: no PDF / precondition missing.  The
            # state machine says WHY via the probe; emitting ocr.run here
            # would tell the user to run OCR that cannot succeed.
            return intents
        if ocr_detail in ("blocks_missing", "blocks_empty", "blocks_invalid"):
            intents.append(ActionIntent(
                action_id="ocr.run",
                scope=scope,
                trigger_reason_code="lineage.ocr_blocks_" + ocr_detail.split("_", 1)[1],
                trigger_reason=f"OCR for {paper.key} produced no usable blocks ({ocr_detail}) — re-run",
            ))
        else:
            intents.append(ActionIntent(
                action_id="ocr.run",
                scope=scope,
                trigger_reason_code="lineage.ocr_missing",
                trigger_reason=f"OCR output for {paper.key} is missing",
            ))
    elif paper.ocr == "failed":
        # Every failure detail keeps its own reason code (failed_legacy /
        # retryable_error / fatal_error / queued_interrupted).
        detail = ocr_detail or "failed"
        intents.append(ActionIntent(
            action_id="ocr.run",
            scope=scope,
            trigger_reason_code="lineage.ocr_" + detail,
            trigger_reason=f"OCR for {paper.key} failed ({detail}) — re-run",
        ))
    elif paper.ocr == "stale":
        intents.append(ActionIntent(
            action_id="ocr.rebuild_derived",
            scope=scope,
            trigger_reason_code="lineage.ocr_derived_stale",
            trigger_reason=f"Derived OCR artifacts for {paper.key} are stale",
        ))
    elif paper.ocr == "incomplete":
        # OCR ran but the derived structure is missing/invalid — an
        # INCOMPLETE product, distinct from a quality problem.  The fix is
        # a LOCAL derived rebuild (ocr rebuild).  Every detail keeps its
        # own reason code.
        _rc = {
            "tree_missing": "lineage.ocr_tree_missing",
            "tree_empty": "lineage.ocr_tree_empty",
            "tree_invalid": "lineage.ocr_tree_invalid",
            "role_index_missing": "lineage.ocr_role_index_missing",
            "role_index_invalid": "lineage.ocr_role_index_invalid",
            "publish_pending_stale": "lineage.ocr_publish_pending_stale",
        }.get(ocr_detail, "lineage.ocr_incomplete")
        intents.append(ActionIntent(
            action_id="ocr.rebuild_derived",
            scope=scope,
            trigger_reason_code=_rc,
            trigger_reason=f"OCR derived artifacts for {paper.key} are incomplete ({ocr_detail or 'unknown'})",
        ))
    # Retrieval depends on OCR being current.
    if paper.retrieval in ("stale", "missing") and paper.ocr == "current":
        intents.append(ActionIntent(
            action_id="memory.build",
            scope=scope,
            trigger_reason_code="lineage.retrieval_defect",
            trigger_reason=f"Retrieval units for {paper.key} are {paper.retrieval}",
        ))
    # Vector depends on retrieval being current.
    if paper.vector in ("stale", "missing") and paper.retrieval == "current":
        intents.append(ActionIntent(
            action_id="embed.resume",
            scope=scope,
            trigger_reason_code="lineage.vector_defect",
            trigger_reason=f"Vector rows for {paper.key} are {paper.vector}",
        ))
    return intents


def _merge_intents(intents: list[ActionIntent]) -> list[ActionIntent]:
    """Scope merging by canonical action: per-paper frontiers collapse into
    one intent per action_id with a merged papers scope."""
    by_action: dict[str, list[str]] = {}
    reasons: dict[str, tuple[str, str]] = {}
    for intent in intents:
        keys = by_action.setdefault(intent.action_id, [])
        if intent.scope.kind == "papers":
            keys.extend(intent.scope.keys)
        reasons[intent.action_id] = (intent.trigger_reason_code, intent.trigger_reason)

    merged: list[ActionIntent] = []
    for action_id in sorted(by_action):
        keys = sorted(set(by_action[action_id]))
        code, reason = reasons[action_id]
        merged.append(ActionIntent(
            action_id=action_id,
            scope=PapersScope(tuple(keys)) if keys else AllScope(),
            trigger_reason_code=code,
            trigger_reason=f"{reason} (merged over {len(keys)} papers)" if len(keys) > 1 else reason,
        ))
    return merged


# ── W2 input digest (semantic observation → intent) ───────────────────────

def _library_digest(vault: Path) -> str:
    """Canonical-library revision fingerprint for global digest material —
    the index's keyed content, stable regardless of file mtime."""
    from paperforge.worker.asset_index import read_index

    try:
        envelope = read_index(vault)
        items = envelope.get("items") if isinstance(envelope, dict) else (envelope or [])
        material = json.dumps(
            sorted(
                (str(it.get("zotero_key", "")), str(it.get("title", "")))
                for it in items or []
            ),
            sort_keys=True, separators=(",", ":"),
        )
    except Exception:  # noqa: BLE001
        return ""
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _intent_input_digest(obs: ReconcileObservation, intent: ActionIntent, vault: Path) -> str:
    """Digest of the SEMANTIC observation that drives this intent: facet
    states + lineage identities per paper, plus global desired-state /
    published-substrate material.  A later stale cause (R1 → R2) changes
    the identity material and therefore the digest — the W2 gate then
    re-allows emission (#167 P0-2: an all-scope digest must also move when
    the canonical library or the substrate changes)."""
    from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION

    by_key = obs.by_key()
    material: dict[str, Any] = {
        "action": intent.action_id,
        "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
    }
    if intent.scope.kind == "papers":
        papers_material: dict[str, Any] = {}
        for key in sorted(intent.scope.keys):
            paper = by_key.get(key)
            if paper is None:
                papers_material[key] = {"absent": True}
                continue
            papers_material[key] = {
                "ocr": paper.ocr,
                "ocr_identity": paper.identities.get("ocr"),
                "retrieval": paper.retrieval,
                "retrieval_identity": paper.identities.get("retrieval"),
                "vector": paper.vector,
                "vector_identity": paper.identities.get("vector"),
            }
        material["papers"] = papers_material
    else:
        material["scope"] = "all"
        material["library_digest"] = _library_digest(vault)
        material["facet_summary"] = _facet_summary(obs)
        substrate = observe_global(vault)
        material["substrate"] = {
            "memory_substrate_ok": substrate.memory_substrate_ok,
            "vector_substrate_ok": substrate.vector_substrate_ok,
        }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def semantic_attempt_digest(vault: Path, intent: dict[str, Any]) -> str:
    """Chain settle-time digest for one wire intent (W2 writer seam): the
    digest of the CURRENT semantic observation for the intent's scope —
    recorded against the last attempt so a changed observation re-allows
    emission (chain.py records it on dispatch settle, #167 P0-2)."""
    from paperforge.actions.types import scope_from_dict

    scope = scope_from_dict(intent.get("scope") or {})
    keys = list(scope.keys) if scope.kind == "papers" else None
    obs = observe(vault, keys)
    intent_obj = ActionIntent(
        action_id=str(intent.get("action_id", "")),
        scope=scope,
        trigger_reason_code="",
        trigger_reason="",
    )
    return _intent_input_digest(obs, intent_obj, vault)


def _w2_gate(
    obs: ReconcileObservation,
    intent: ActionIntent,
    last_attempts: dict[str, dict[str, Any]],
    diagnostics: list[str],
) -> bool:
    """Re-emission gate: suppress when the input digest is UNCHANGED since a
    FAILED last attempt for the same canonical (action, scope).  Digest
    changed → allow.  No record / succeeded → allow."""
    last = last_attempts.get(_canonical_key(intent.action_id, intent.scope))
    if not last:
        return False
    if last.get("outcome") != "failed":
        return False
    current_digest = _intent_input_digest(obs, intent, obs.vault)
    if last.get("input_digest") == current_digest:
        diagnostics.append(
            f"w2.suppressed:{intent.action_id}:{_canonical_key(intent.action_id, intent.scope)}"
        )
        return True
    return False


# ── the seam ───────────────────────────────────────────────────────────────


def reconcile(vault: Path, keys: list[str] | None = None) -> PFResult:
    """Pure derivation + intent emission, returned on the SINGLE
    PFResult.next_actions channel (#166 P1-1: no internal 'intents' wire).

    Global frontier first: an incompatible substrate emits exactly one
    global intent; affected per-paper facets are blocked_global.  Then the
    minimal per-paper frontier with scope merging.  Unregistered actions
    are NEVER emitted — registry parity is an invariant (test-enforced);
    a runtime miss is a structured diagnostic.
    """
    from paperforge import __version__ as PF_VERSION

    obs = observe(vault, keys)
    facet_summary = _facet_summary(obs)
    diagnostics: list[str] = []
    per_paper_reasons: dict[str, list[str]] = {}
    intents: list[ActionIntent] = []

    if not obs.global_state.memory_substrate_ok:
        intents = [ActionIntent(
            action_id="memory.build",
            scope=AllScope(),
            trigger_reason_code="substrate.memory_incompatible",
            trigger_reason="Memory substrate requires a full build",
        )]
        for paper in obs.papers:
            per_paper_reasons[paper.key] = ["blocked_global:memory_substrate"]
    elif not obs.global_state.vector_substrate_ok:
        intents = [ActionIntent(
            action_id="embed.build",
            scope=AllScope(),
            trigger_reason_code="substrate.vector_incompatible",
            trigger_reason="Vector substrate requires a global build",
        )]
        for paper in obs.papers:
            per_paper_reasons[paper.key] = ["blocked_global:vector_substrate"]
    else:
        # Minimal repair frontier: per-paper, prerequisites-satisfied
        # first-layer deficits as independent siblings.
        per_paper_intents: list[ActionIntent] = []
        for paper in obs.papers:
            per_paper_intents.extend(_per_paper_intents(paper))
            unknown_layers = [
                layer for layer in ("ocr", "retrieval", "vector")
                if getattr(paper, layer) == "unknown"
            ]
            if unknown_layers:
                per_paper_reasons[paper.key] = [
                    f"unknown:{layer}" for layer in unknown_layers
                ]
        merged = _merge_intents(per_paper_intents)
        last_attempts = read_last_attempts(vault)
        for intent in merged:
            if _w2_gate(obs, intent, last_attempts, diagnostics):
                continue
            intents.append(intent)

    # Library residuals — a first-class state, independent of the per-paper
    # frontier: papers absent from Zotero but present in ANY carrier
    # (workspace / full-text index / vectors / OCR).  One library.prune
    # clears every carrier for every residual paper.  Destructive →
    # confirmation-required; never automatic.
    if obs.residual_count > 0:
        intents.append(ActionIntent(
            action_id="library.prune",
            scope=AllScope(),
            trigger_reason_code="library.orphans_present",
            trigger_reason=(
                f"{obs.residual_count} residual paper(s) no longer in Zotero "
                f"(e.g. {obs.residual_keys[0]}) — workspace/OCR/vector/full-text "
                f"records can be removed"
            ),
        ))

    # Library orphans — legacy alias of the workspace carrier, kept for
    # compatibility with callers that still read orphan_count.
    if obs.orphan_count > 0 and obs.residual_count == 0:
        intents.append(ActionIntent(
            action_id="library.prune",
            scope=AllScope(),
            trigger_reason_code="library.orphans_present",
            trigger_reason=(
                f"{obs.orphan_count} orphan paper(s) no longer in Zotero "
                f"(e.g. {obs.orphan_keys[0]}) — workspace/OCR/vector files can be removed"
            ),
        ))

    # Project internal ActionIntents onto the single next_actions channel.
    wire: list[dict[str, Any]] = []
    for intent in intents:
        try:
            wire.append(emit_next_action(intent).to_dict())
        except KeyError:
            # Invariant broken (registry parity is test-enforced): never
            # emit a hand-written substitute — fail closed with a
            # diagnostic (#166 P1-2).
            diagnostics.append(f"reconcile.action_unregistered:{intent.action_id}")

    return PFResult(
        ok=True,
        command="reconcile",
        version=PF_VERSION,
        data={
            "schema_version": 1,
            "vault": str(vault),
            "scope": {"kind": "papers", "keys": sorted(set(keys))} if keys else {"kind": "all"},
            "global": {
                "memory_substrate_ok": obs.global_state.memory_substrate_ok,
                "vector_substrate_ok": obs.global_state.vector_substrate_ok,
                "reasons": list(obs.global_state.reasons),
            },
            "facet_summary": facet_summary,
            "per_paper": {
                key: {
                    "ocr": paper.ocr,
                    "retrieval": paper.retrieval,
                    "vector": paper.vector,
                    "reasons": per_paper_reasons.get(key, []),
                }
                for key, paper in ((p.key, p) for p in obs.papers)
            },
            "diagnostics": diagnostics,
        },
        next_actions=wire,
    )
