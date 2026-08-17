"""M2-B (Control Plane Closure): per-paper applicability projection.

Applicability answers 'for THIS paper's current state, SHOULD this action
run?' and is strictly orthogonal to availability ('can the system run it
NOW').  It is projected from the OBSERVATION truth — probe lineage states
+ details (the materialization-judgment SSOT) — preflight NEVER
re-implements deficit tables by reading meta/raw/tree itself.
"""

from __future__ import annotations

from pathlib import Path

from paperforge.actions.types import Applicability, PaperPreflight


def _canonical_intent(action_id: str, state: dict[str, object], key: str):
    """Return the reconcile frontier intent for a per-paper action.

    Reconcile owns the first-frontier decision.  Preflight only projects that
    decision into the availability/applicability wire contract.
    """
    if action_id not in {"ocr.run", "ocr.rebuild_derived", "memory.build", "embed.resume"}:
        return None
    from paperforge.reconcile import PaperObservation, _per_paper_intents

    raw_details = state.get("details")
    details = raw_details if isinstance(raw_details, dict) else {}
    paper = PaperObservation(
        key=key,
        ocr=str(state.get("ocr") or ""),
        retrieval=str(state.get("retrieval") or ""),
        vector=str(state.get("vector") or ""),
        identities={},
        details={str(k): (str(v) if v is not None else None) for k, v in details.items()},
    )
    return next(
        (intent for intent in _per_paper_intents(paper) if intent.action_id == action_id),
        None,
    )


def _rule(
    action_id: str, state: dict[str, object], *, key: str = "<paper>"
) -> tuple[Applicability, str, str, str | None]:
    """Map one paper's observed state to the action applicability contract.

    The first-frontier ``needed`` decision is delegated to reconcile; this
    function only classifies states where that action is not the frontier.
    """
    ocr = str(state.get("ocr") or "")
    retrieval = str(state.get("retrieval") or "")
    vector = str(state.get("vector") or "")
    details = state.get("details")
    details = details if isinstance(details, dict) else {}
    ocr_detail = str(details.get("ocr") or "") or None
    vector_detail = str(details.get("vector") or "") or None

    intent = _canonical_intent(action_id, state, key)
    if intent is not None:
        return "needed", intent.trigger_reason_code, intent.trigger_reason, None

    if action_id == "ocr.run":
        if ocr_detail in ("no_pdf", "nopdf"):
            return "not_applicable", "ocr.no_pdf", "No PDF attachment — not an OCR target", None
        if ocr_detail in ("blocked", "raw_not_file", "raw_permission"):
            return "blocked", "ocr.blocked", "OCR blocked by source or filesystem state", None
        if ocr == "current":
            return "noop", "ocr.current", "OCR already current", None
        if ocr in ("incomplete", "stale"):
            return (
                "not_applicable",
                "lineage.ocr_derived_defect",
                f"OCR requires derived rebuild ({ocr_detail or ocr})",
                "ocr.rebuild_derived",
            )
        if ocr_detail == "queued":
            return "blocked", "ocr.execution_in_flight", "OCR execution is already in flight", None
        return "noop", "ocr.noop", f"OCR is {ocr}", None

    if action_id == "ocr.rebuild_derived":
        if ocr == "current":
            return "noop", "ocr.current", "OCR already current", None
        if ocr_detail in (
            "blocked",
            "raw_not_file",
            "raw_permission",
            "blocks_not_file",
            "blocks_permission",
            "tree_not_file",
            "tree_permission",
            "role_index_not_file",
            "role_index_permission",
        ):
            return "blocked", "ocr.blocked", "OCR rebuild blocked by filesystem state", None
        if ocr in ("missing", "failed") or ocr_detail in (
            "provenance_key_mismatch",
            "provenance_pdf_changed",
            "provenance_raw_mismatch",
        ):
            return (
                "not_applicable",
                "lineage.ocr_raw_defect",
                f"OCR requires remote rerun ({ocr_detail or ocr})",
                "ocr.run",
            )
        return "noop", "ocr.noop", f"OCR is {ocr}", None

    if action_id == "memory.build":
        if retrieval == "current":
            return "noop", "retrieval.current", "Retrieval already current", None
        if ocr != "current":
            return "blocked", "lineage.ocr_prereq", f"OCR is {ocr} — retrieval cannot build", None
        return "blocked", "lineage.retrieval_unobservable", f"Retrieval is {retrieval}", None

    if action_id == "embed.resume":
        if vector == "current":
            return "noop", "vector.current", "Vectors already current", None
        if vector_detail == "vector_no_content":
            return (
                "not_applicable",
                "vector.no_content",
                "No indexable content — legal terminal, never embed",
                None,
            )
        if retrieval != "current":
            return (
                "blocked",
                "lineage.retrieval_prereq",
                f"Retrieval is {retrieval} — vectors need retrieval first",
                None,
            )
        return "blocked", "lineage.vector_unobservable", f"Vectors are {vector}", None

    if action_id == "embed.build":
        if vector_detail == "vector_no_content":
            return "not_applicable", "vector.no_content", "No indexable content — legal terminal", None
        if vector in ("stale", "missing"):
            return "needed", "lineage.vector_defect", f"Vectors are {vector}", None
        if vector == "current":
            return "noop", "vector.current", "Vectors already current", None
        return "noop", "vector.noop", f"Vectors are {vector}", None

    return "noop", "action.noop", "No per-key projection defined for this action", None


def project_applicability(vault: Path, action_id: str, keys: list[str]) -> list[PaperPreflight]:
    """Per-paper applicability for one action over explicit keys, projected
    from probe lineage (read-only; never mutates meta or the provider)."""
    from paperforge.lineage import probe_lineage

    envelope = probe_lineage(vault)
    papers = envelope.get("papers", {})
    out: list[PaperPreflight] = []
    for key in keys:
        state = papers.get(key)
        if not state:
            out.append(
                PaperPreflight(
                    key=key,
                    applicability="not_applicable",
                    reason_code="paper.not_found",
                    reason="Paper not in canonical index",
                )
            )
            continue
        app, rc, reason, rec = _rule(action_id, state, key=key)
        out.append(
            PaperPreflight(
                key=key,
                applicability=app,
                reason_code=rc,
                reason=reason,
                recommended_action_id=rec,
            )
        )
    return out
