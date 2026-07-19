"""paperforge.commands.probe — Capability probe command (Issue #76, #78, contract #69).

Emits direct schema-v1 capability envelopes (not PFResult-wrapped) for the
Obsidian plugin's six-module control center. Probes use canonical sources:
paperforge_paths, load_vault_config, get_memory_status, collect_maintenance_rows.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1
TTL_INSTALLATION = 3600
TTL_LIBRARY = 300
TTL_OCR = 60
TTL_MEMORY = 300
TTL_HELP = 3600
MIN_PYTHON = (3, 11)
LEGACY_PATH_KEYS = frozenset({
    "system_dir", "resources_dir", "literature_dir",
    "base_dir", "control_dir", "skill_dir", "command_dir",
})

SUPPORTED_MODULES = frozenset({"installation", "library", "ocr", "memory", "help"})


# ---------------------------------------------------------------------------
# Envelope builder
# ---------------------------------------------------------------------------

def _utcnow_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_action_primary(
    *, verb: str, label: str, command: str,
    destructive: bool = False, destructive_scope: str | None = None,
    destructive_effect: str | None = None, confirmation_required: bool = False,
    confirmation_prompt: str | None = None, scope: str = "module", scope_count: int = 1,
) -> dict[str, Any]:
    return {
        "verb": verb, "label": label, "destructive": destructive,
        "destructive_scope": destructive_scope, "destructive_effect": destructive_effect,
        "confirmation_required": confirmation_required, "confirmation_prompt": confirmation_prompt,
        "command": command, "scope": scope, "scope_count": scope_count,
    }


def build_envelope(
    *, module: str, capability_state: str, severity: str,
    reason_code: str, reason_text: str,
    action_primary: dict[str, Any] | None = None,
    activity_state: str = "idle", activity_label: str | None = None,
    activity_progress: dict[str, int] | None = None, ttl_seconds: int = 3600,
    notices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "module": module,
        "capability_state": capability_state, "activity_state": activity_state,
        "activity_label": activity_label, "activity_progress": activity_progress,
        "severity": severity, "reason": {"code": reason_code, "text": reason_text},
        "action": {"primary": action_primary}, "notices": notices or [],
        "updated_at": _utcnow_z(), "ttl_seconds": ttl_seconds,
    }


# ---------------------------------------------------------------------------
# Config validation helper
# ---------------------------------------------------------------------------

def _is_recognizable_config(data: Any) -> bool:
    if not isinstance(data, dict) or len(data) == 0:
        return False
    if "vault_config" in data:
        return True
    return any(k in data for k in LEGACY_PATH_KEYS)


def _load_pf_config(vault: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read paperforge.json. Returns (data, error) tuple.
    data=None, error=None → file does not exist.
    data=None, error='corrupt' → file exists but is invalid.
    data=dict, error=None → valid config.
    """
    pf_json = vault / "paperforge.json"
    if not pf_json.exists():
        return None, None
    try:
        raw = pf_json.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None, "corrupt"
    if not _is_recognizable_config(data):
        return None, "corrupt"
    return data, None


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def probe_installation(vault: Path) -> dict[str, Any]:
    pf_json = vault / "paperforge.json"

    if not pf_json.exists():
        return build_envelope(
            module="installation", capability_state="missing_input", severity="warning",
            reason_code="installation.config_missing", reason_text="paperforge.json not found in vault",
            action_primary=build_action_primary(verb="set_config", label="Set config", command="paperforge setup"),
            ttl_seconds=TTL_INSTALLATION,
        )

    try:
        data = json.loads(pf_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return build_envelope(
            module="installation", capability_state="unavailable", severity="error",
            reason_code="installation.config_corrupt", reason_text="paperforge.json is corrupt or invalid",
            action_primary=build_action_primary(verb="setup", label="Setup", command="paperforge setup"),
            ttl_seconds=TTL_INSTALLATION,
        )

    if not _is_recognizable_config(data):
        return build_envelope(
            module="installation", capability_state="unavailable", severity="error",
            reason_code="installation.config_corrupt", reason_text="paperforge.json has unrecognizable structure",
            action_primary=build_action_primary(verb="setup", label="Setup", command="paperforge setup"),
            ttl_seconds=TTL_INSTALLATION,
        )

    py_version = sys.version_info[:2]
    if py_version < MIN_PYTHON:
        return build_envelope(
            module="installation", capability_state="limited", severity="warning",
            reason_code="installation.python_version_unsupported",
            reason_text=f"Python {py_version[0]}.{py_version[1]} < {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
            action_primary=build_action_primary(verb="update", label="Update Python", command=""),
            ttl_seconds=TTL_INSTALLATION,
        )

    return build_envelope(
        module="installation", capability_state="ready", severity="ok",
        reason_code="installation.ready", reason_text="PaperForge is installed and configured",
        action_primary=None, ttl_seconds=TTL_INSTALLATION,
    )


def probe_help(vault: Path) -> dict[str, Any]:  # noqa: ARG001
    skills_dir = Path(__file__).resolve().parent.parent / "skills" / "paperforge"
    skill_md = skills_dir / "SKILL.md"

    if skill_md.exists():
        return build_envelope(
            module="help", capability_state="ready", severity="ok",
            reason_code="help.ready", reason_text="Help and skill documentation available",
            action_primary=None, ttl_seconds=TTL_HELP,
        )
    return build_envelope(
        module="help", capability_state="limited", severity="warning",
        reason_code="help.docs_missing", reason_text="Packaged help source not found",
        action_primary=build_action_primary(verb="setup", label="Restore help", command="paperforge setup"),
        ttl_seconds=TTL_HELP,
    )


def probe_library(vault: Path, last_operation_exit_code: int | None = None) -> dict[str, Any]:
    """Probe the Library module using canonical sources.

    When last_operation_exit_code is non-zero, the probe reports a sync failure
    envelope after validating config/path, skipping index freshness checks.
    """
    data, err = _load_pf_config(vault)
    if data is None:
        if err == "corrupt":
            return build_envelope(
                module="library", capability_state="unavailable", severity="error",
                reason_code="library.config_corrupt",
                reason_text="paperforge.json is corrupt — library sync cannot proceed",
                action_primary=build_action_primary(verb="setup", label="Setup", command="paperforge setup"),
                ttl_seconds=TTL_LIBRARY,
            )
        return build_envelope(
            module="library", capability_state="missing_input", severity="warning",
            reason_code="library.config_missing",
            reason_text="paperforge.json not found — cannot check library configuration",
            action_primary=build_action_primary(verb="set_config", label="Set config", command="paperforge setup"),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── zotero_data_dir check ──
    vault_cfg = data.get("vault_config", {}) if isinstance(data.get("vault_config"), dict) else {}
    zotero_dir = vault_cfg.get("zotero_data_dir") or data.get("zotero_data_dir", "")
    zotero_dir = (zotero_dir or "").strip()

    if not zotero_dir:
        return build_envelope(
            module="library", capability_state="missing_input", severity="warning",
            reason_code="library.zotero_missing", reason_text="Zotero data directory not configured",
            action_primary=build_action_primary(verb="set_config", label="Configure Zotero", command="paperforge setup"),
            ttl_seconds=TTL_LIBRARY,
        )

    zotero_path = Path(zotero_dir)
    if not zotero_path.is_absolute():
        zotero_path = (vault / zotero_dir).resolve()
    if not zotero_path.exists():
        return build_envelope(
            module="library", capability_state="missing_input", severity="error",
            reason_code="library.zotero_not_found",
            reason_text=f"Zotero data directory not found: {zotero_dir}",
            action_primary=build_action_primary(verb="set_config", label="Configure Zotero", command="paperforge setup"),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Sync failure probe: backend-owned envelope after failed manual sync ──
    if last_operation_exit_code and last_operation_exit_code != 0:
        return build_envelope(
            module="library", capability_state="needs_action", severity="error",
            reason_code="library.sync_failed",
            reason_text=f"Library sync failed (exit code {last_operation_exit_code}) — re-run or check logs",
            action_primary=build_action_primary(verb="sync", label="Sync library", command="paperforge sync"),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Canonical index check via paperforge_paths ──
    from paperforge.config import paperforge_paths
    from paperforge.memory.db import get_memory_db_path
    paths = paperforge_paths(vault)
    index_path = paths.get("index")  # canonical formal-library.json

    if index_path is None or not index_path.exists():
        return build_envelope(
            module="library", capability_state="needs_action", severity="warning",
            reason_code="library.index_missing", reason_text="Canonical index has not been built — run sync",
            action_primary=build_action_primary(verb="sync", label="Sync library", command="paperforge sync"),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Index freshness: canonical export hash (Issue #78) ──
    # real asset_index.build_envelope writes "export_hash", not "canonical_index_hash"
    notices: list[dict[str, Any]] = []
    try:
        from paperforge.worker.asset_index import read_index, _compute_export_hash
        envelope = read_index(vault)
        if envelope is not None and isinstance(envelope, dict):
            stored_hash = envelope.get("export_hash", "")
            current_hash = _compute_export_hash(paths)
            paper_count = envelope.get("paper_count", 0)

            if not stored_hash or stored_hash != current_hash:
                return build_envelope(
                    module="library", capability_state="needs_action", severity="warning",
                    reason_code="library.index_stale",
                    reason_text=f"Library index is stale ({paper_count} papers — export files changed since last sync)",
                    action_primary=build_action_primary(verb="sync", label="Sync library", command="paperforge sync"),
                    ttl_seconds=TTL_LIBRARY,
                )

            # Cross-validate DB canonical_index_hash
            try:
                import sqlite3 as _sqlite3
                items = envelope.get("items", [])
                from paperforge.memory.builder import compute_hash
                index_hash = compute_hash(items)
                db_path = get_memory_db_path(vault)
                if db_path.exists():
                    conn = _sqlite3.connect(str(db_path))
                    try:
                        row = conn.execute("SELECT value FROM meta WHERE key = 'canonical_index_hash'").fetchone()
                        db_stored = row[0] if row else ""
                        if db_stored and db_stored != index_hash:
                            notices.append({"level": "warning", "message": "DB canonical_index_hash is out of sync with index"})
                    except Exception:
                        pass
                    finally:
                        conn.close()
            except Exception:
                pass
            # Export hash valid and index healthy → ready
            return build_envelope(
                module="library", capability_state="ready", severity="ok",
                reason_code="library.ready",
                reason_text=f"Library synced and index is fresh ({paper_count} papers)",
                notices=notices, action_primary=None, ttl_seconds=TTL_LIBRARY,
            )
        elif envelope is not None:
            # Legacy list format
            return build_envelope(
                module="library", capability_state="needs_action", severity="warning",
                reason_code="library.index_legacy", reason_text="Canonical index is in legacy format — run sync to migrate",
                action_primary=build_action_primary(verb="sync", label="Sync library", command="paperforge sync"),
                ttl_seconds=TTL_LIBRARY,
            )
        else:
            return build_envelope(
                module="library", capability_state="needs_action", severity="warning",
                reason_code="library.index_missing", reason_text="Canonical index is empty — run sync",
                action_primary=build_action_primary(verb="sync", label="Sync library", command="paperforge sync"),
                ttl_seconds=TTL_LIBRARY,
            )
    except Exception:
        # Validation exception → never fall through to ready; report unknown
        return build_envelope(
            module="library", capability_state="unknown", severity="unknown",
            reason_code="library.index_validation_failed",
            reason_text="Library index validation failed — probe to retry",
            action_primary=build_action_primary(verb="probe", label="Re-check", command="probe library"),
            ttl_seconds=TTL_LIBRARY,
        )


def probe_ocr(vault: Path) -> dict[str, Any]:
    """Probe the OCR module using canonical maintenance rows and env config."""
    data, err = _load_pf_config(vault)
    if data is None:
        if err == "corrupt":
            return build_envelope(
                module="ocr", capability_state="unavailable", severity="error",
                reason_code="ocr.config_corrupt", reason_text="paperforge.json is corrupt — OCR cannot proceed",
                action_primary=build_action_primary(verb="setup", label="Setup", command="paperforge setup"),
                ttl_seconds=TTL_OCR,
            )
        return build_envelope(
            module="ocr", capability_state="missing_input", severity="warning",
            reason_code="ocr.config_missing", reason_text="paperforge.json not found — cannot check OCR configuration",
            action_primary=build_action_primary(verb="set_config", label="Set config", command="paperforge setup"),
            ttl_seconds=TTL_OCR,
        )

    # ── API key / env check — canonical _resolve_paddleocr_token ──
    from paperforge.worker.ocr import _resolve_paddleocr_token
    token = _resolve_paddleocr_token(vault)

    if not token:
        return build_envelope(
            module="ocr", capability_state="missing_input", severity="warning",
            reason_code="ocr.api_key_missing",
            reason_text="PADDLEOCR_API_TOKEN not found in environment — configure API key",
            action_primary=build_action_primary(verb="set_config", label="Configure API key", command="paperforge setup"),
            ttl_seconds=TTL_OCR,
        )

    # ── Provider reachability via ocr_doctor(config=None, live=False) ──
    notices: list[dict[str, Any]] = []
    provider_reachable = True
    try:
        from paperforge.ocr_diagnostics import ocr_doctor
        diag = ocr_doctor(config=None, live=False)
        provider_reachable = diag.get("passed", False)
        if not provider_reachable:
            notices.append({"level": "warning", "message": f"PaddleOCR API unreachable: {diag.get('error', 'unknown error')}"})
    except Exception:
        provider_reachable = False
        notices.append({"level": "warning", "message": "PaddleOCR API diagnostics unavailable"})

    # ── Canonical maintenance rows ──
    try:
        from paperforge.worker.ocr_maintenance import collect_maintenance_rows
        rows = collect_maintenance_rows(vault)
    except Exception:
        return build_envelope(
            module="ocr", capability_state="unknown", severity="unknown",
            reason_code="ocr.probe_failed", reason_text="OCR maintenance check failed — probe to retry",
            action_primary=build_action_primary(verb="probe", label="Probe", command="probe ocr"),
            notices=notices, ttl_seconds=TTL_OCR,
        )

    if not rows:
        return build_envelope(
            module="ocr", capability_state="needs_action", severity="warning",
            reason_code="ocr.artifacts_missing", reason_text="No OCR output found — run OCR to process papers",
            action_primary=build_action_primary(verb="run", label="Run OCR", command="paperforge ocr run"),
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # ── Running/active rows → activity overlay (Issue #78 fix) ──
    # Detect statuses running|processing|queued, emit activity_state='running',
    # label and {current,total} progress while preserving independently computed
    # availability/severity/reason/action.
    # current = terminal/completed rows (done family), not queued/running/processing
    TERMINAL_STATUSES = frozenset({'done', 'done_degraded'})
    ACTIVE_STATUSES = frozenset({'running', 'processing', 'queued'})
    running_rows = [r for r in rows if getattr(r, 'status', '') in ACTIVE_STATUSES]
    completed_count = sum(1 for r in rows if getattr(r, 'status', '') in TERMINAL_STATUSES)
    total = len(rows)
    act_state = "running" if running_rows else "idle"
    if running_rows:
        act_label = f"OCR processing ({completed_count}/{total})"
        act_progress = {"current": completed_count, "total": total}
    else:
        act_label = None
        act_progress = None

    # ── Determine state from maintenance rows using canonical display_action ──
    # Known display_action values: retry_ocr, upgrade_legacy, rebuild_result, none, run_ocr
    # derive redo only from retry_ocr|upgrade_legacy (legacy can_redo fallback only when display_action is absent)
    # rebuild from rebuild_result
    # unexpected actionable only when display_severity=='actionable' and action is not known
    KNOWN_ACTIONS = frozenset({'retry_ocr', 'upgrade_legacy', 'rebuild_result', 'run_ocr', 'none'})

    # has_failed: status=failed, health=red, or explicit redo display_action.
    # Contract: display_action='rebuild_result' must never become redo even when health is red.
    has_failed = any(
        (r.status == "failed" or r.health == "red" or
         getattr(r, 'display_action', '') in ('retry_ocr', 'upgrade_legacy'))
        and getattr(r, 'display_action', '') != 'rebuild_result'
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

    # Failures → needs_action with redo
    if has_failed:
        return build_envelope(
            module="ocr", capability_state="needs_action", severity="warning",
            reason_code="ocr.quality_failures",
            reason_text="Some OCR outputs have failed — redo required",
            action_primary=build_action_primary(
                verb="redo", label="Redo OCR", command="paperforge ocr redo",
                destructive=True, destructive_scope="selection",
                destructive_effect="Deletes existing OCR derived artifacts for failed papers and re-runs OCR from raw images. Raw images and PDFs are preserved.",
                confirmation_required=True,
                confirmation_prompt="This will delete existing OCR output for failed papers and re-run OCR. This cannot be undone. Proceed?",
            ),
            activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # Redo candidates → needs_action
    if has_redo:
        return build_envelope(
            module="ocr", capability_state="needs_action", severity="warning",
            reason_code="ocr.redo_needed",
            reason_text="Some OCR outputs need redo — re-run from raw images",
            action_primary=build_action_primary(
                verb="redo", label="Redo OCR", command="paperforge ocr redo",
                destructive=True, destructive_scope="selection",
                destructive_effect="Deletes existing OCR derived artifacts for selected papers and re-runs OCR from raw images. Raw images and PDFs are preserved.",
                confirmation_required=True,
                confirmation_prompt="This will delete existing OCR output for selected papers and re-run OCR. This cannot be undone. Proceed?",
            ),
            activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # Pending rows → run action (run before rebuild/investigate)
    # Exclude queued/running — those are already captured as activity
    has_pending = any(
        getattr(r, 'status', '') == 'pending' or getattr(r, 'display_action', '') == 'run_ocr'
        for r in rows
    )
    if has_pending:
        return build_envelope(
            module="ocr", capability_state="needs_action", severity="warning",
            reason_code="ocr.pending",
            reason_text=f"OCR is pending for {total} papers — run to process",
            action_primary=build_action_primary(
                verb="run", label="Run OCR", command="paperforge ocr run",
            ),
            activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # Degraded → needs_action with rebuild
    if has_degraded:
        return build_envelope(
            module="ocr", capability_state="needs_action", severity="warning",
            reason_code="ocr.artifacts_stale",
            reason_text="Derived OCR artifacts are degraded — rebuild to refresh",
            action_primary=build_action_primary(
                verb="rebuild_derived", label="Rebuild derived artifacts",
                command="paperforge ocr rebuild --all",
                destructive=False,
            ),
            activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # Unexpected actionable → investigate (lowest priority before provider)
    if has_unexpected:
        return build_envelope(
            module="ocr", capability_state="limited", severity="warning",
            reason_code="ocr.unexpected_action",
            reason_text="OCR maintenance reports unexpected actions — run diagnostics",
            action_primary=build_action_primary(
                verb="investigate", label="Run diagnostics", command="paperforge ocr doctor",
            ),
            activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # Provider unreachable → limited + investigate (last resort before ready)
    if not provider_reachable:
        return build_envelope(
            module="ocr", capability_state="limited", severity="warning",
            reason_code="ocr.api_unreachable",
            reason_text="PaddleOCR API is unreachable — OCR jobs may fail. Local output remains available.",
            action_primary=build_action_primary(
                verb="investigate", label="Run diagnostics", command="paperforge ocr doctor",
            ),
            activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
            notices=notices, ttl_seconds=TTL_OCR,
        )

    # All good — ready only when no failures/redo/pending/degraded/unexpected and provider reachable
    return build_envelope(
        module="ocr", capability_state="ready", severity="ok",
        reason_code="ocr.ready", reason_text=f"OCR pipeline functional ({total} papers processed)",
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, action_primary=None, ttl_seconds=TTL_OCR,
    )


def probe_memory(vault: Path) -> dict[str, Any]:
    """Probe the Memory module using canonical get_memory_status."""
    try:
        from paperforge.memory.query import get_memory_status
        from paperforge.memory.schema import CURRENT_SCHEMA_VERSION as _CURRENT_SCHEMA
        status = get_memory_status(vault)
    except Exception:
        return build_envelope(
            module="memory", capability_state="unknown", severity="unknown",
            reason_code="memory.probe_failed", reason_text="Memory status check failed — probe to retry",
            action_primary=build_action_primary(verb="probe", label="Re-check", command="probe memory"),
            ttl_seconds=TTL_MEMORY,
        )

    db_exists: bool = status.get("db_exists", False)
    schema_ok: bool = status.get("schema_ok", False)
    fresh: bool = status.get("fresh", False)
    paper_count_db: int = status.get("paper_count_db", 0)
    paper_count_index: int = status.get("paper_count_index", 0)

    if not db_exists:
        return build_envelope(
            module="memory", capability_state="needs_action", severity="warning",
            reason_code="memory.db_missing", reason_text="Memory database has not been built yet",
            action_primary=build_action_primary(verb="run", label="Build memory", command="paperforge memory build"),
            ttl_seconds=TTL_MEMORY,
        )

    # Schema check failed
    if not schema_ok:
        if paper_count_db > 0:
            # DB has papers but old schema → needs rebuild (CLI memory only has build/status)
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.migration_needed",
                reason_text="Memory database schema version is outdated — rebuild to update",
                action_primary=build_action_primary(
                    verb="rebuild_index", label="Rebuild database", command="paperforge memory build",
                    destructive=False,
                ),
                ttl_seconds=TTL_MEMORY,
            )
        # DB exists but empty/unreadable — rebuild or restore from backup
        from paperforge.config import paperforge_paths
        paths = paperforge_paths(vault)
        backup_exists = (paths["paperforge"] / "indexes" / "paperforge.db.backup").exists()
        notices: list[dict[str, Any]] = []
        if backup_exists:
            return build_envelope(
                module="memory", capability_state="unavailable", severity="error",
                reason_code="memory.db_corrupt",
                reason_text="Memory database is corrupted — a verified backup is available for restore",
                action_primary=build_action_primary(
                    verb="restore_backup", label="Restore from backup", command="paperforge memory restore-backup",
                    destructive=True, destructive_scope="module",
                    destructive_effect="Replaces the current corrupted database with the verified backup. The corrupted database will be preserved as a timestamped snapshot.",
                    confirmation_required=True,
                    confirmation_prompt="This will replace the memory database with the backup copy. The corrupted database will be preserved. Proceed?",
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )
        return build_envelope(
            module="memory", capability_state="unavailable", severity="error",
            reason_code="memory.db_corrupt",
            reason_text="Memory database is corrupted or uninitialized — rebuild required (source data preserved)",
            action_primary=build_action_primary(
                verb="run", label="Rebuild memory", command="paperforge memory build",
                destructive=False,
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

    # Stale: schema OK but index hash doesn't match
    if not fresh:
        return build_envelope(
            module="memory", capability_state="needs_action", severity="warning",
            reason_code="memory.index_stale",
            reason_text=f"Memory index needs rebuild (DB: {paper_count_db} papers, Index: {paper_count_index} papers)",
            action_primary=build_action_primary(
                verb="rebuild_index", label="Rebuild index", command="paperforge memory build",
                destructive=False,
            ),
            ttl_seconds=TTL_MEMORY,
        )
    # ── Vector index health via get_embed_status ──
    notices: list[dict[str, Any]] = []
    try:
        from paperforge.embedding.status import get_embed_status
        embed_status = get_embed_status(vault)
        vector_healthy = embed_status.get("healthy", False) and embed_status.get("total_chunks", 0) > 0
        if not vector_healthy and paper_count_db > 0:
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.index_stale",
                reason_text="Vector index is missing or corrupted — rebuild to enable semantic search",
                action_primary=build_action_primary(
                    verb="rebuild_index", label="Build vector index",
                    command="paperforge embed build --force",
                    destructive=False,
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )
    except Exception:
        # Vector check exception → never ready; report unknown
        return build_envelope(
            module="memory", capability_state="unknown", severity="unknown",
            reason_code="memory.vector_probe_failed",
            reason_text="Vector index health check failed — probe to retry",
            action_primary=build_action_primary(verb="probe", label="Re-check", command="probe memory"),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

    # DB healthy and vector index present → ready
    return build_envelope(
        module="memory", capability_state="ready", severity="ok",
        reason_code="memory.ready",
        reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
        notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
    )


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def run(args: Any) -> int:
    vault: Path = args.vault_path
    module: str = args.probe_module

    if module == "installation":
        envelope = probe_installation(vault)
    elif module == "library":
        last_code: int | None = getattr(args, "last_operation_exit_code", None)
        envelope = probe_library(vault, last_operation_exit_code=last_code)
    elif module == "ocr":
        envelope = probe_ocr(vault)
    elif module == "memory":
        envelope = probe_memory(vault)
    elif module == "help":
        envelope = probe_help(vault)
    else:
        print(f"Error: unsupported probe module '{module}'", file=sys.stderr)
        return 1

    json_output: bool = getattr(args, "json", False)
    if json_output:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
    else:
        state = envelope["capability_state"]
        reason = envelope["reason"]["text"]
        print(f"[{module}] {state}: {reason}")

    return 0
