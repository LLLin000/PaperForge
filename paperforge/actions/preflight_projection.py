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


def _rule(action_id: str, state: dict[str, object]) -> tuple[Applicability, str, str, str | None]:
    """Map one paper's OBSERVED state to (applicability, reason_code,
    reason, recommended_action_id).  State keys come from probe lineage
    (ocr/retrieval/vector + details.*), which is the materialization SSOT.
    """
    ocr = str(state.get("ocr") or "")
    retrieval = str(state.get("retrieval") or "")
    vector = str(state.get("vector") or "")
    details = state.get("details")
    details = details if isinstance(details, dict) else {}
    ocr_detail = str(details.get("ocr") or "") or None
    vector_detail = str(details.get("vector") or "") or None

    if action_id == "ocr.run":
        if ocr_detail in ("no_pdf", "nopdf"):
            return "not_applicable", "ocr.no_pdf", "No PDF attachment — not an OCR target", None
        if ocr == "current":
            return "noop", "ocr.current", "OCR already current", None
        if ocr_detail == "provenance_pdf_changed":
            return "needed", "lineage.ocr_pdf_changed", "Attachment replaced — re-OCR against current PDF", None
        if ocr_detail == "blocked":
            return "blocked", "ocr.blocked", "OCR blocked (e.g. canonical PDF missing)", None
        if ocr in ("missing", "failed", "incomplete", "stale"):
            return "needed", "lineage.ocr_defect", f"OCR is {ocr} ({ocr_detail or 'unknown'})", None
        return "noop", "ocr.noop", f"OCR is {ocr}", None

    if action_id == "ocr.rebuild_derived":
        if ocr == "incomplete":
            return "needed", "lineage.ocr_incomplete", f"Derived artifacts incomplete ({ocr_detail})", None
        if ocr == "current":
            return "noop", "ocr.current", "OCR already current", None
        if ocr in ("missing", "failed"):
            return (
                "not_applicable",
                "lineage.ocr_raw_defect",
                f"Raw OCR defective ({ocr}) — ocr.run, not rebuild",
                "ocr.run",
            )
        return "noop", "ocr.noop", f"OCR is {ocr}", None

    if action_id == "memory.build":
        if retrieval in ("missing", "stale") and ocr == "current":
            return "needed", "lineage.retrieval_defect", f"Retrieval units are {retrieval}", None
        if retrieval == "current":
            return "noop", "retrieval.current", "Retrieval already current", None
        if ocr != "current":
            return (
                "blocked",
                "lineage.ocr_prereq",
                f"OCR is {ocr} — retrieval cannot build",
                None,
            )
        return "noop", "retrieval.noop", f"Retrieval is {retrieval}", None

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
        if vector in ("missing", "stale"):
            return (
                "needed",
                "lineage.vector_defect",
                f"Vectors are {vector} ({vector_detail or 'unknown'})",
                None,
            )
        return "noop", "vector.noop", f"Vectors are {vector}", None

    if action_id == "embed.build":
        # global substrate action — per-key projection still useful to
        # report which papers actually need embedding.
        if vector in ("stale", "missing") and vector_detail != "vector_no_content":
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
        app, rc, reason, rec = _rule(action_id, state)
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
