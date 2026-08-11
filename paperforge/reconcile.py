"""Reconcile module (#166 / T5, #159 §3).

Three-layer observation (global desired → global substrate → per-paper
lineage) → global repair frontier first → per-paper minimal repair frontier
→ scope merging by canonical action → single next_actions channel.

PURE derivation + intent emission: no side effects, idempotent (same facts
→ same result).  Reconcile decides the OPERATION; cost/confirmation come
from the #145 registry.  No DAG engine, no retry tables, no second intents
wire.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperforge.actions.registry import emit_next_action
from paperforge.actions.types import ActionIntent, AllScope, PapersScope

# ── observation ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GlobalObservation:
    memory_substrate_ok: bool
    vector_substrate_ok: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperObservation:
    key: str
    ocr: str  # current | stale | missing | running | unknown
    retrieval: str  # current | stale | missing | unknown
    vector: str  # current | stale | missing | not_required | unknown


@dataclass(frozen=True)
class ReconcileObservation:
    global_state: GlobalObservation
    papers: tuple[PaperObservation, ...] = ()


def observe_global(vault: Path) -> GlobalObservation:
    """Global substrate vs desired state (#159 §2.1/§2.2).

    - memory substrate: memory DB present and schema current
    - vector substrate: embedding credential available (C1 seam) and the
      vector layout/state is healthy
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
        # Substrate = embedding IDENTITY availability (credential seam, C1).
        # vec0 table layout is a build PRODUCT, not a substrate premise —
        # a missing/incompatible vec0 table surfaces as per-paper vector
        # facets (missing/stale) and is repaired by embed.resume/build.
        from paperforge.credentials import CredentialKey, status as credential_status

        cred = credential_status(CredentialKey("embedding"))
        if cred.state != "available":
            vector_ok = False
            reasons.append(f"vector.credential_{cred.state}")

    return GlobalObservation(
        memory_substrate_ok=memory_ok,
        vector_substrate_ok=vector_ok,
        reasons=tuple(reasons),
    )


def observe_papers(vault: Path, keys: list[str] | None = None) -> tuple[PaperObservation, ...]:
    """Per-paper lineage facets (T1 probe read model)."""
    from paperforge.lineage import probe_lineage

    payload = probe_lineage(vault)
    papers = payload.get("papers", {})
    out: list[PaperObservation] = []
    for key, states in papers.items():
        if keys is not None and key not in set(keys):
            continue
        out.append(PaperObservation(
            key=key,
            ocr=str(states.get("ocr", "unknown")),
            retrieval=str(states.get("retrieval", "unknown")),
            vector=str(states.get("vector", "unknown")),
        ))
    return tuple(sorted(out, key=lambda p: p.key))


def observe(vault: Path, keys: list[str] | None = None) -> ReconcileObservation:
    return ReconcileObservation(
        global_state=observe_global(vault),
        papers=observe_papers(vault, keys),
    )


# ── deficit → operation (operation decided here; policy from registry) ────

# Per-paper minimal frontier: first-layer unsatisfied facets whose
# prerequisites are satisfied.  Lineage edges: ocr → retrieval → vector.
def _per_paper_intents(paper: PaperObservation) -> list[ActionIntent]:
    intents: list[ActionIntent] = []
    scope = PapersScope((paper.key,))

    # OCR is the root layer — no prerequisite.
    if paper.ocr in ("stale", "missing"):
        intents.append(ActionIntent(
            action_id="ocr.run",
            scope=scope,
            trigger_reason_code="lineage.ocr_defect",
            trigger_reason=f"OCR output for {paper.key} is {paper.ocr}",
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


# ── the seam ───────────────────────────────────────────────────────────────


def reconcile(vault: Path, keys: list[str] | None = None) -> dict[str, Any]:
    """Pure derivation + intent emission.

    Returns a machine payload with the single-channel intent projection:
      - intents: the PFResult.next_actions wire (hydrated from the registry)
      - global: substrate observation
      - per_paper: facet states + blocked_global reasons
    No side effects; idempotent.
    """
    obs = observe(vault, keys)
    global_intents: list[ActionIntent] = []
    per_paper_reasons: dict[str, list[str]] = {}
    facet_summary: dict[str, int] = {"current": 0, "stale": 0, "missing": 0, "unknown": 0}

    # Global frontier FIRST: an incompatible substrate emits exactly one
    # global intent; affected per-paper facets are blocked_global.
    if not obs.global_state.memory_substrate_ok:
        global_intents.append(ActionIntent(
            action_id="memory.build",
            scope=AllScope(),
            trigger_reason_code="substrate.memory_incompatible",
            trigger_reason="Memory substrate requires a full build",
        ))
        for paper in obs.papers:
            per_paper_reasons[paper.key] = ["blocked_global:memory_substrate"]
        return _payload(
            vault, obs, global_intents, per_paper_reasons, facet_summary, keys,
        )
    if not obs.global_state.vector_substrate_ok:
        global_intents.append(ActionIntent(
            action_id="embed.build",
            scope=AllScope(),
            trigger_reason_code="substrate.vector_incompatible",
            trigger_reason="Vector substrate requires a global build",
        ))
        for paper in obs.papers:
            per_paper_reasons[paper.key] = ["blocked_global:vector_substrate"]
        return _payload(
            vault, obs, global_intents, per_paper_reasons, facet_summary, keys,
        )

    # Minimal repair frontier: per-paper, prerequisites-satisfied first-layer
    # deficits as independent siblings.
    per_paper_intents: list[ActionIntent] = []
    for paper in obs.papers:
        for layer in ("ocr", "retrieval", "vector"):
            facet_summary[getattr(paper, layer)] = facet_summary.get(getattr(paper, layer), 0) + 1
        per_paper_intents.extend(_per_paper_intents(paper))
        # Unknown per-paper lineage alone -> NO per-paper repair intent
        # (never stale, never mass rebuild).  Reasons surface for the report.
        unknown_layers = [
            layer for layer in ("ocr", "retrieval", "vector")
            if getattr(paper, layer) == "unknown"
        ]
        if unknown_layers:
            per_paper_reasons[paper.key] = [
                f"unknown:{layer}" for layer in unknown_layers
            ]

    merged = _merge_intents(per_paper_intents)
    return _payload(vault, obs, merged, per_paper_reasons, facet_summary, keys)


def _payload(
    vault: Path,
    obs: ReconcileObservation,
    intents: list[ActionIntent],
    per_paper_reasons: dict[str, list[str]],
    facet_summary: dict[str, int],
    keys: list[str] | None,
) -> dict[str, Any]:
    """Project internal ActionIntents onto the PFResult.next_actions wire."""
    from paperforge.core.next_actions import NextAction

    wire: list[dict[str, Any]] = []
    for intent in intents:
        try:
            hydrated = emit_next_action(intent)
            wire.append(hydrated.to_dict() if isinstance(hydrated, NextAction) else {})
        except KeyError:
            # Unregistered action — never emit an unresolvable intent.
            wire.append({
                "schema_version": 1,
                "action_id": intent.action_id,
                "scope": {"kind": "papers", "keys": list(intent.scope.keys)}
                if intent.scope.kind == "papers" else {"kind": "all"},
                "reason_code": "reconcile.action_unregistered",
                "reason": f"action {intent.action_id} is not registered",
            })
    return {
        "schema_version": 1,
        "command": "reconcile",
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
        "intents": wire,
    }
