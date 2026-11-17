"""paperforge.probes.ocr — OCR capability reader (P1)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION
from paperforge.probes.envelope import (_load_pf_config, build_action_primary, build_envelope, CAPABILITY_OPTIONAL, CAPABILITY_REQUIRED, SAFETY_SAFE, TTL_OCR, USER_STATE_ACTION_REQUIRED, USER_STATE_DETECTION_FAILED, USER_STATE_NOT_ENABLED, USER_STATE_READY, USER_STATE_SETUP_REQUIRED)

logger = logging.getLogger(__name__)

def probe_ocr(vault: Path, lineage: dict[str, Any] | None = None) -> dict[str, Any]:
    """Probe the OCR module using canonical maintenance rows and env config."""
    data, err = _load_pf_config(vault)
    if data is None:
        if err == "corrupt":
            return build_envelope(module="ocr", capability_state="unavailable", severity="error",
            reason_code="ocr.config_corrupt",
            reason_text="paperforge.json is corrupt — OCR cannot proceed",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="ocr.setup", verb="setup", label="Setup",
            ), ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)
        return build_envelope(module="ocr", capability_state="missing_input", severity="warning",
        reason_code="ocr.config_missing",
        reason_text="paperforge.json not found — cannot check OCR configuration",
        user_state=USER_STATE_NOT_ENABLED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.enable", verb="set_config", label="Enable OCR",
        ), ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # ── Provider reachability (notices only; readiness verdict is LAST,
    #    #161: local materialization defects outrank credential readiness) ──
    notices: list[dict[str, Any]] = []
    provider_reachable = True
    try:
        from paperforge.ocr_diagnostics import ocr_doctor
        diag = ocr_doctor(config=None, live=False)
        provider_reachable = diag.get("passed", False)
        if not provider_reachable:
            notices.append({"level": "warning",
                            "message": f"PaddleOCR API unreachable: {diag.get('error', 'unknown error')}"})
    except Exception:
        provider_reachable = False
        notices.append({"level": "warning", "message": "PaddleOCR API diagnostics unavailable"})

    # ── Canonical maintenance rows ──
    try:
        from paperforge.worker.ocr_maintenance import collect_maintenance_rows
        rows = collect_maintenance_rows(vault)
    except Exception:
        return build_envelope(module="ocr", capability_state="unknown", severity="unknown",
        reason_code="ocr.probe_failed", reason_text="OCR maintenance check failed — probe to retry",
        user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.probe", verb="probe", label="Retry",
        ),
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # #148: the envelope keeps the pipeline-version summary on every
    # rows-bearing path; the per-paper detail lives in `ocr pipeline-versions`.
    papers_on_current, papers_stale = ocr_pipeline_version_summary(vault, rows)
    _pipeline_summary = {
        "total": len(rows), "on_current": papers_on_current, "stale": papers_stale,
    }
    historical_activity = {
        "current": sum(getattr(r, "status", "") in ("done", "done_degraded") for r in rows),
        "total": len(rows),
        "unsettled": sum(getattr(r, "status", "") in ("running", "processing", "queued") for r in rows),
    }
    _build_envelope = build_envelope

    def _wrap(*args, **kwargs):
        env = _build_envelope(*args, **kwargs)
        env["pipeline_version_summary"] = _pipeline_summary
        if historical_activity["unsettled"]:
            env["historical_activity"] = historical_activity
        return env

    if not rows:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.artifacts_missing",
        reason_text="No OCR output found — run OCR to process papers",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.run", verb="run", label="Run OCR",
        ),
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Persisted provider/local records do not prove a live local worker.
    total = len(rows)
    # Papers with no OCR output (the actionable set the run action would
    # process).  Counted from the rows so the number matches the OCR list.
    pending_rows = sum(
        1 for r in rows
        if getattr(r, 'status', '') == 'pending'
        or getattr(r, 'display_action', '') == 'run_ocr'
    )
    act_state = "idle"
    act_label = None
    act_progress = None

    # ── Unified state machine (统一出统一回) ──
    # The lineage probe is the AUTHORITY for per-paper OCR state.  The old
    # maintenance health/display_action flags below are demoted to a
    # quality-only overlay: they must never conflate "OCR not finished"
    # (blocks_empty / not_started) with "OCR quality failed" — those are
    # different meanings with different next actions.
    from collections import Counter as _Counter

    _lin_states: _Counter = _Counter()
    _lin_details: _Counter = _Counter()
    try:
        if lineage is None:
            from paperforge.lineage import probe_lineage as _pl

            _lin = _pl(vault)
        else:
            _lin = lineage
        for _s in (_lin.get("papers", {}) if isinstance(_lin, dict) else {}).values():
            _lin_states[str(_s.get("ocr", "unknown"))] += 1
            _lin_details[(str((_s.get("details") or {}).get("ocr") or "none"))] += 1
    except Exception:  # noqa: BLE001 — lineage unobservable → fall back to maintenance
        pass

    _n_failed = int(_lin_states.get("failed", 0))
    _n_incomplete = int(_lin_states.get("incomplete", 0))
    _n_blocks = int(
        _lin_details.get("blocks_missing", 0)
        + _lin_details.get("blocks_empty", 0)
        + _lin_details.get("blocks_invalid", 0)
    )
    # Papers with no OCR output at all: `not_started` (nothing ran) plus
    # `raw_missing` (no raw artifacts on disk).  Reporting only not_started
    # said "1 paper" on a vault with 20 unprocessed papers.
    _n_pending = int(_lin_details.get("not_started", 0)) + int(
        _lin_details.get("raw_missing", 0)
    )
    _n_nopdf = int(_lin_details.get("no_pdf", 0))

    if _n_failed:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.failed",
        reason_text=f"OCR failed for {_n_failed} paper(s) — re-run to process",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True, user_visible_failure=True,
        user_impact="Failed OCR papers cannot be read or searched until reprocessed",
        action_primary=build_action_primary(
            action_id="ocr.run", verb="run", label="Run OCR",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if _n_incomplete:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.incomplete",
        reason_text=f"OCR structure incomplete for {_n_incomplete} paper(s) — rebuild derived artifacts",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True,
        user_impact="Incomplete OCR papers lack structural search (no body units) until derived artifacts are rebuilt",
        action_primary=build_action_primary(
            action_id="ocr.rebuild_derived", verb="run", label="Rebuild OCR derived",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if _n_blocks:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.blocks_missing",
        reason_text=f"OCR produced no usable content for {_n_blocks} paper(s) — re-run OCR",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True,
        action_primary=build_action_primary(
            action_id="ocr.run", verb="run", label="Run OCR",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if _n_pending:
        # NOT a defect: a library where some papers have not been processed
        # yet is normal and the processed papers are fully searchable.  The
        # module reports ready with an informational notice; the module
        # detail offers "Run OCR" as an ordinary action.
        _unprocessed = pending_rows or _n_pending
        _pending_notice = (
            f"{_unprocessed} of {total} papers have no OCR output yet "
            "— run OCR when you want them processed"
        )
        return _wrap(module="ocr", capability_state="ready", severity="ok",
        reason_code="ocr.pending",
        reason_text=_pending_notice,
        user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
        notices=notices + [{"level": "info", "message": _pending_notice}],
        action_primary=None,
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if _n_nopdf:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.no_pdf",
        reason_text=f"{_n_nopdf} paper(s) have no PDF source — add the file to run OCR",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)


    KNOWN_ACTIONS = frozenset({'retry_ocr', 'upgrade_legacy', 'rebuild_result', 'run_ocr', 'none'})

    has_failed = any(
        (r.status == "failed" or r.health == "red" or
         getattr(r, 'display_action', '') in ('retry_ocr', 'upgrade_legacy'))
        and getattr(r, 'display_action', '') != 'rebuild_result'
        and (getattr(r, 'can_redo', False) or getattr(r, 'display_action', '') in ('retry_ocr', 'upgrade_legacy'))
        for r in rows
    )
    has_redo = any(
        getattr(r, 'display_action', '') in ('retry_ocr', 'upgrade_legacy') or
        (not hasattr(r, 'display_action') and (
            getattr(r, 'recommended_action', '') == 'redo' or getattr(r, 'can_redo', False)
        ))
        for r in rows
    )
    has_degraded = any(
        getattr(r, 'display_action', '') == 'rebuild_result'
        for r in rows
    )
    has_unexpected = any(
        hasattr(r, 'display_severity') and r.display_severity == 'actionable'
        and hasattr(r, 'display_action') and r.display_action
        and r.display_action not in KNOWN_ACTIONS
        for r in rows
    )

    # ── Priority: redo > run > rebuild_derived > investigate ──

    # Failures → needs_action (no redo primary: redo is internal-only per #99)
    if has_failed:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.quality_failures",
        reason_text="Some OCR outputs have failed",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True, user_visible_failure=True,
        user_impact="Failed OCR papers cannot be read or searched until reprocessed",
        action_primary=None,
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Redo candidates → needs_action (no redo primary: redo is internal-only per #99)
    if has_redo:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.redo_needed",
        reason_text="Some OCR outputs need reprocessing",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True,
        action_primary=None,
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Pending rows → run action (run before rebuild/investigate)
    # Count the pending ROWS: the message used `total`, so a vault with 949
    # finished papers and 19 pending ones claimed all of them were pending.
    pending_rows = sum(
        1 for r in rows
        if getattr(r, 'status', '') == 'pending' or getattr(r, 'display_action', '') == 'run_ocr'
    )
    if pending_rows:
        _fallback_notice = (
            f"{pending_rows} of {total} papers have no OCR output yet "
            "— run OCR when you want them processed"
        )
        return _wrap(module="ocr", capability_state="ready", severity="ok",
        reason_code="ocr.pending",
        reason_text=_fallback_notice,
        user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
        notices=notices + [{"level": "info", "message": _fallback_notice}],
        action_primary=None,
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Degraded → rebuild (safe, no maintenance eligibility)
    if has_degraded:
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.artifacts_stale",
        reason_text="Derived OCR artifacts are degraded — rebuild to refresh",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.rebuild_derived",
            verb="rebuild_derived", label="Rebuild derived artifacts",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Unexpected actionable → investigate (lowest priority before provider)
    if has_unexpected:
        return _wrap(module="ocr", capability_state="limited", severity="warning",
        reason_code="ocr.unexpected_action",
        reason_text="OCR maintenance reports unexpected actions — run diagnostics",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.diagnose",
            verb="investigate", label="Run diagnostics",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Dead-end red rows with no retry/rebuild path → quality_unacceptable
    has_dead_end = any(
        (r.status == "failed" or r.health == "red")
        and getattr(r, 'display_action', 'none') in ('none', None, '')
        and not getattr(r, 'can_redo', False)
        for r in rows
    )
    if has_dead_end:
        dead_count = sum(1 for r in rows if (r.status == "failed" or r.health == "red")
                         and getattr(r, 'display_action', 'none') in ('none', None, '')
                         and not getattr(r, 'can_redo', False))
        return _wrap(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.quality_unacceptable",
        reason_text=f"OCR output is unacceptable for {dead_count} paper(s) — no automated repair available",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True, user_visible_failure=True,
        user_impact=f"{dead_count} paper(s) have unusable OCR output with no automated recovery",
        action_primary=build_action_primary(
            action_id="ocr.report_issue",
            verb="investigate", label="Report OCR issue",
            safety_class=SAFETY_SAFE, scope="selection", scope_count=dead_count,
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # ── Credential / provider readiness — LAST (#161): the API key gates
    #    whether REMOTE OCR can run; it never masks an existing canonical
    #    local materialization defect (failed/redo/pending/degraded rows). ──
    # #173/C1: presence comes from the credential authority's status — the
    # probe never retrieves the value.
    from paperforge.credentials import CredentialKey
    from paperforge.credentials import status as credential_status

    if credential_status(CredentialKey("ocr")).state != "available":
        return _wrap(module="ocr", capability_state="missing_input", severity="warning",
        reason_code="ocr.api_key_missing",
        reason_text="OCR credential missing — run `paperforge auth set ocr --stdin` or set PAPERFORGE_CREDENTIAL_OCR__DEFAULT",
        user_state=USER_STATE_NOT_ENABLED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.configure", verb="set_config", label="Configure API key",
        ), ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if not provider_reachable:
        return _wrap(module="ocr", capability_state="limited", severity="warning",
        reason_code="ocr.api_unreachable",
        reason_text="PaddleOCR API is unreachable — OCR jobs may fail. Local output remains available.",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.diagnose",
            verb="investigate", label="Run diagnostics",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # All good (summary attached by the rows-bearing envelope wrapper above).
    return _wrap(module="ocr", capability_state="ready", severity="ok",
    reason_code="ocr.ready", reason_text=f"OCR pipeline functional ({total} papers processed)",
    user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
    activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
    notices=notices, action_primary=None, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)


def ocr_pipeline_version_summary(vault: Path, rows) -> tuple[int, int]:
    from paperforge.config import paperforge_paths
    from paperforge.core.io import read_json

    # Count papers on/stale relative to the current OCR pipeline version.
    papers_on_current = 0
    papers_stale = 0
    ocr_root = paperforge_paths(vault).get("ocr")
    if ocr_root and ocr_root.exists():
        for r in rows:
            meta_path = ocr_root / r.key / "meta.json"
            if meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    paper_version = meta.get("ocr_pipeline_version")
                    if paper_version == OCR_PIPELINE_VERSION:
                        papers_on_current += 1
                    else:
                        papers_stale += 1
                except Exception:
                    # Count it as stale rather than dropping it: an unreadable
                    # meta is a paper we cannot vouch for, not a non-paper.
                    logger.warning(
                        "unreadable OCR meta for %s; counted as stale", r.key
                    )
                    papers_stale += 1
    return papers_on_current, papers_stale


def paper_pipeline_versions(vault: Path, rows) -> list[dict[str, Any]]:
    from paperforge.config import paperforge_paths
    from paperforge.core.io import read_json

    # Per-paper OCR pipeline versions — the #148 detail surface.
    per_paper: list[dict[str, Any]] = []
    ocr_root = paperforge_paths(vault).get("ocr")
    if ocr_root and ocr_root.exists():
        for r in rows:
            meta_path = ocr_root / r.key / "meta.json"
            if meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    per_paper.append({
                        "key": r.key, "title": getattr(r, "title", ""),
                        "last_pipeline_version": meta.get("ocr_pipeline_version"),
                    })
                except Exception:
                    logger.warning(
                        "unreadable OCR meta detail for %s; reporting it unknown", r.key
                    )
                    per_paper.append({
                        "key": r.key,
                        "title": getattr(r, "title", ""),
                        "last_pipeline_version": None,
                    })
    return per_paper
