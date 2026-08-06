"""paperforge.commands.probe — Capability probe command (Issue #76, #78, #84).

Emits schema-v2 capability envelopes for the Obsidian plugin's control center.
Probes use canonical sources: paperforge_paths, load_vault_config,
get_memory_status, collect_maintenance_rows.

#84: Added action_id, availability, safety_class, preservation_facts,
replacement_facts, interruptible to actions; user_state, capability_kind,
maintenance_eligible, user_visible_failure, user_impact to envelopes.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from paperforge import __version__ as PAPERFORGE_VERSION
from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 2
TTL_INSTALLATION = 3600
TTL_LIBRARY = 300
TTL_OCR = 60
TTL_MEMORY = 300
TTL_HELP = 3600
TTL_MAINTENANCE = 60
MIN_PYTHON = (3, 11)
LEGACY_PATH_KEYS = frozenset({
    "system_dir", "resources_dir", "literature_dir",
    "base_dir", "control_dir", "skill_dir", "command_dir",
})

SUPPORTED_MODULES = frozenset({"installation", "library", "ocr", "memory", "help", "maintenance"})
MAINTENANCE_CONSTITUENT_MODULES = ("installation", "library", "ocr", "memory", "help")

# Six user-facing states (PRD §2.3)
USER_STATE_CHECKING = "checking"
USER_STATE_READY = "ready"
USER_STATE_NOT_ENABLED = "not_enabled"
USER_STATE_SETUP_REQUIRED = "setup_required"
USER_STATE_ACTION_REQUIRED = "action_required"
USER_STATE_DETECTION_FAILED = "detection_failed"

VALID_USER_STATES: frozenset[str] = frozenset({
    USER_STATE_CHECKING, USER_STATE_READY, USER_STATE_NOT_ENABLED,
    USER_STATE_SETUP_REQUIRED, USER_STATE_ACTION_REQUIRED, USER_STATE_DETECTION_FAILED,
})

CAPABILITY_REQUIRED = "required"
CAPABILITY_OPTIONAL = "optional"

SAFETY_SAFE = "safe"
SAFETY_DESTRUCTIVE = "destructive"
SAFETY_IRREVERSIBLE = "irreversible"

VALID_SAFETY_CLASSES: frozenset[str] = frozenset({
    SAFETY_SAFE, SAFETY_DESTRUCTIVE, SAFETY_IRREVERSIBLE,
})


def _utcnow_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_action_primary(
    *, action_id: str, verb: str, label: str, command: str,
    availability: str = "available",
    safety_class: str = SAFETY_SAFE,
    preservation_facts: list[str] | None = None,
    replacement_facts: list[str] | None = None,
    interruptible: bool = True,
    confirmation_required: bool = False,
    confirmation_prompt: str | None = None,
    scope: str = "module", scope_count: int = 1,
) -> dict[str, Any]:
    """Build a capability action with stable metadata (#84).

    action_id: stable backend ID (e.g. "foundation.setup", "ocr.redo").
    availability: "available" | "unavailable" | "busy".
    safety_class: "safe" | "destructive" | "irreversible".
    preservation_facts: what source/user data remains preserved.
    replacement_facts: what derived output will be replaced.
    interruptible: whether the action can be safely stopped.
    """
    return {
        "action_id": action_id, "verb": verb, "label": label,
        "availability": availability, "safety_class": safety_class,
        "preservation_facts": preservation_facts or [],
        "replacement_facts": replacement_facts or [],
        "interruptible": interruptible,
        "confirmation_required": confirmation_required,
        "confirmation_prompt": confirmation_prompt,
        "command": command, "scope": scope, "scope_count": scope_count,
    }


def build_envelope(
    *, module: str, capability_state: str, severity: str,
    reason_code: str, reason_text: str,
    user_state: str,
    capability_kind: str = CAPABILITY_REQUIRED,
    maintenance_eligible: bool = False,
    action_primary: dict[str, Any] | None = None,
    user_visible_failure: bool = False,
    user_impact: str | None = None,
    activity_state: str = "idle", activity_label: str | None = None,
    activity_progress: dict[str, int] | None = None, ttl_seconds: int = 3600,
    notices: list[dict[str, Any]] | None = None,
    pipeline_version: str | None = None,
) -> dict[str, Any]:
    """Build a capability envelope (#84).

    user_state: one of the six user-facing states (§2.3).
    capability_kind: "required" | "optional" — drives baseline/maintenance rules.
    maintenance_eligible: true only for blocking/failed/corrupt/risky issues.
    user_visible_failure: true only when a policy-defined unusable result exists.
    user_impact: plain-language impact for the user, separate from reason_text.
    pipeline_version: aggregate pipeline version for update detection.
    """
    return {
        "schema_version": SCHEMA_VERSION, "module": module,
        "capability_state": capability_state, "activity_state": activity_state,
        "activity_label": activity_label, "activity_progress": activity_progress,
        "severity": severity, "reason": {"code": reason_code, "text": reason_text},
        "action": {"primary": action_primary}, "notices": notices or [],
        "user_state": user_state, "capability_kind": capability_kind,
        "maintenance_eligible": maintenance_eligible,
        "user_visible_failure": user_visible_failure,
        "user_impact": user_impact,
        "updated_at": _utcnow_z(), "ttl_seconds": ttl_seconds,
        "pipeline_version": pipeline_version,
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

def probe_installation(vault: Path, expected_version: str | None = None) -> dict[str, Any]:
    pf_json = vault / "paperforge.json"

    if not pf_json.exists():
        return build_envelope(
            module="installation", capability_state="missing_input", severity="warning",
            reason_code="installation.config_missing",
            reason_text="paperforge.json not found in vault",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="foundation.setup",
                verb="setup", label="Install PaperForge", command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    try:
        data = json.loads(pf_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return build_envelope(
            module="installation", capability_state="unavailable", severity="error",
            reason_code="installation.config_corrupt",
            reason_text="paperforge.json is corrupt or invalid",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="foundation.setup",
                verb="setup", label="Repair Installation", command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    if not _is_recognizable_config(data):
        return build_envelope(
            module="installation", capability_state="unavailable", severity="error",
            reason_code="installation.config_corrupt",
            reason_text="paperforge.json has unrecognizable structure",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="foundation.setup",
                verb="setup", label="Repair Installation", command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    py_version = sys.version_info[:2]
    if py_version < MIN_PYTHON:
        return build_envelope(
            module="installation", capability_state="limited", severity="warning",
            reason_code="installation.python_version_unsupported",
            reason_text=f"Python {py_version[0]}.{py_version[1]} < {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            user_impact="OCR and processing will not work with this Python version",
            action_primary=build_action_primary(
                action_id="foundation.update_python",
                verb="update", label="Update Python", command="",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    if expected_version and PAPERFORGE_VERSION != expected_version:
        return build_envelope(
            module="installation", capability_state="needs_action", severity="warning",
            reason_code="installation.version_mismatch",
            reason_text=f"PaperForge {PAPERFORGE_VERSION} does not match plugin {expected_version}",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="foundation.setup", verb="setup", label="Update PaperForge",
                command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    return build_envelope(
        module="installation", capability_state="ready", severity="ok",
        reason_code="installation.ready",
        reason_text="PaperForge is installed and configured",
        user_state=USER_STATE_READY, capability_kind=CAPABILITY_REQUIRED,
        action_primary=None, ttl_seconds=TTL_INSTALLATION,
    )


def probe_help(vault: Path) -> dict[str, Any]:  # noqa: ARG001
    skills_dir = Path(__file__).resolve().parent.parent / "skills" / "paperforge"
    skill_md = skills_dir / "SKILL.md"

    if skill_md.exists():
        return build_envelope(
            module="help", capability_state="ready", severity="ok",
            reason_code="help.ready", reason_text="Help and skill documentation available",
            user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=None, ttl_seconds=TTL_HELP,
        )
    return build_envelope(
        module="help", capability_state="limited", severity="warning",
        reason_code="help.docs_missing", reason_text="Packaged help source not found",
        user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="help.restore",
            verb="setup", label="Restore help", command="paperforge setup",
        ),
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
                user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                maintenance_eligible=True,
                action_primary=build_action_primary(
                    action_id="library.setup", verb="setup", label="Setup", command="paperforge setup",
                ),
                ttl_seconds=TTL_LIBRARY,
            )
        return build_envelope(
            module="library", capability_state="missing_input", severity="warning",
            reason_code="library.config_missing",
            reason_text="paperforge.json not found — cannot check library configuration",
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.setup", verb="set_config", label="Set config", command="paperforge setup",
            ),
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
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.configure", verb="set_config", label="Configure Zotero",
                command="paperforge setup",
            ),
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
            user_state=USER_STATE_SETUP_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="library.configure", verb="set_config", label="Configure Zotero",
                command="paperforge setup",
            ),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Sync failure probe: backend-owned envelope after failed manual sync ──
    if last_operation_exit_code and last_operation_exit_code != 0:
        return build_envelope(
            module="library", capability_state="needs_action", severity="error",
            reason_code="library.sync_failed",
            reason_text=f"Library sync failed (exit code {last_operation_exit_code}) — re-run or check logs",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            maintenance_eligible=True,
            action_primary=build_action_primary(
                action_id="library.sync", verb="sync", label="Sync library", command="paperforge sync",
            ),
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
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.sync", verb="sync", label="Sync library", command="paperforge sync",
            ),
            ttl_seconds=TTL_LIBRARY,
        )

    # ── Index freshness: canonical export hash (Issue #78) ──
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
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                    action_primary=build_action_primary(
                        action_id="library.sync", verb="sync", label="Sync library", command="paperforge sync",
                    ),
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
                    from paperforge.memory.db import open_live_reader

                    with open_live_reader(vault, db_path) as conn:
                        row = conn.execute("SELECT value FROM meta WHERE key = 'canonical_index_hash'").fetchone()
                        db_stored = row[0] if row else ""
                        if db_stored and db_stored != index_hash:
                            notices.append({"level": "warning", "message": "DB canonical_index_hash is out of sync with index"})
            except Exception:
                pass
            # Export hash valid and index healthy → ready
            return build_envelope(
                module="library", capability_state="ready", severity="ok",
                reason_code="library.ready",
                reason_text=f"Library synced and index is fresh ({paper_count} papers)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_REQUIRED,
                notices=notices, action_primary=None, ttl_seconds=TTL_LIBRARY,
            )
        elif envelope is not None:
            # Legacy list format
            return build_envelope(
                module="library", capability_state="needs_action", severity="warning",
                reason_code="library.index_legacy",
                reason_text="Canonical index is in legacy format — run sync to migrate",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                maintenance_eligible=True,
                action_primary=build_action_primary(
                    action_id="library.sync", verb="sync", label="Sync library", command="paperforge sync",
                ),
                ttl_seconds=TTL_LIBRARY,
            )
        else:
            return build_envelope(
                module="library", capability_state="needs_action", severity="warning",
                reason_code="library.index_missing", reason_text="Canonical index is empty — run sync",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                action_primary=build_action_primary(
                    action_id="library.sync", verb="sync", label="Sync library", command="paperforge sync",
                ),
                ttl_seconds=TTL_LIBRARY,
            )
    except Exception:
        # Validation exception → never fall through to ready; report unknown
        return build_envelope(
            module="library", capability_state="unknown", severity="unknown",
            reason_code="library.index_validation_failed",
            reason_text="Library index validation failed — probe to retry",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="library.probe", verb="probe", label="Retry", command="probe library",
            ),
            ttl_seconds=TTL_LIBRARY,
        )


def probe_ocr(vault: Path) -> dict[str, Any]:
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
                action_id="ocr.setup", verb="setup", label="Setup", command="paperforge setup",
            ), ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)
        return build_envelope(module="ocr", capability_state="missing_input", severity="warning",
        reason_code="ocr.config_missing",
        reason_text="paperforge.json not found — cannot check OCR configuration",
        user_state=USER_STATE_NOT_ENABLED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.enable", verb="set_config", label="Enable OCR", command="paperforge setup",
        ), ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # ── API key / env check — canonical _resolve_paddleocr_token ──
    from paperforge.worker.ocr import _resolve_paddleocr_token
    token = _resolve_paddleocr_token(vault)

    if not token:
        return build_envelope(module="ocr", capability_state="missing_input", severity="warning",
        reason_code="ocr.api_key_missing",
        reason_text="PADDLEOCR_API_TOKEN not found in environment — configure API key",
        user_state=USER_STATE_NOT_ENABLED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.configure", verb="set_config", label="Configure API key",
            command="paperforge setup",
        ), ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # ── Provider reachability via ocr_doctor(config=None, live=False) ──
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
            action_id="ocr.probe", verb="probe", label="Retry", command="probe ocr",
        ),
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if not rows:
        return build_envelope(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.artifacts_missing",
        reason_text="No OCR output found — run OCR to process papers",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.run", verb="run", label="Run OCR", command="paperforge ocr run",
        ),
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # ── Running/active rows → activity overlay (Issue #78 fix) ──
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
        return build_envelope(module="ocr", capability_state="needs_action", severity="warning",
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
        return build_envelope(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.redo_needed",
        reason_text="Some OCR outputs need reprocessing",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True,
        action_primary=None,
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Pending rows → run action (run before rebuild/investigate)
    has_pending = any(
        getattr(r, 'status', '') == 'pending' or getattr(r, 'display_action', '') == 'run_ocr'
        for r in rows
    )
    if has_pending:
        return build_envelope(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.pending",
        reason_text=f"OCR is pending for {total} papers — run to process",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.run",
            verb="run", label="Run OCR", command="paperforge ocr run",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Degraded → rebuild (safe, no maintenance eligibility)
    if has_degraded:
        return build_envelope(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.artifacts_stale",
        reason_text="Derived OCR artifacts are degraded — rebuild to refresh",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.rebuild_derived",
            verb="rebuild_derived", label="Rebuild derived artifacts",
            command="paperforge ocr rebuild --all",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # Unexpected actionable → investigate (lowest priority before provider)
    if has_unexpected:
        return build_envelope(module="ocr", capability_state="limited", severity="warning",
        reason_code="ocr.unexpected_action",
        reason_text="OCR maintenance reports unexpected actions — run diagnostics",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.diagnose",
            verb="investigate", label="Run diagnostics", command="paperforge ocr doctor",
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
        return build_envelope(module="ocr", capability_state="needs_action", severity="warning",
        reason_code="ocr.quality_unacceptable",
        reason_text=f"OCR output is unacceptable for {dead_count} paper(s) — no automated repair available",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        maintenance_eligible=True, user_visible_failure=True,
        user_impact=f"{dead_count} paper(s) have unusable OCR output with no automated recovery",
        action_primary=build_action_primary(
            action_id="ocr.report_issue",
            verb="investigate", label="Report OCR issue", command="paperforge ocr issue-draft",
            safety_class=SAFETY_SAFE, scope="selection", scope_count=dead_count,
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    if not provider_reachable:
        return build_envelope(module="ocr", capability_state="limited", severity="warning",
        reason_code="ocr.api_unreachable",
        reason_text="PaddleOCR API is unreachable — OCR jobs may fail. Local output remains available.",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
        action_primary=build_action_primary(
            action_id="ocr.diagnose",
            verb="investigate", label="Run diagnostics", command="paperforge ocr doctor",
        ),
        activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
        notices=notices, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)

    # ── Per-paper pipeline version comparison ──
    from paperforge.worker._utils import pipeline_paths
    from paperforge.core.io import read_json

    ocr_root = pipeline_paths(vault).get("ocr")
    papers_on_current = 0
    papers_stale = 0
    per_paper_versions: list[dict[str, Any]] = []
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
                    per_paper_versions.append({
                        "key": r.key, "title": getattr(r, "title", ""),
                        "last_pipeline_version": paper_version,
                    })
                except Exception:
                    pass

    # All good
    envelope = build_envelope(module="ocr", capability_state="ready", severity="ok",
    reason_code="ocr.ready", reason_text=f"OCR pipeline functional ({total} papers processed)",
    user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
    activity_state=act_state, activity_label=act_label, activity_progress=act_progress,
    notices=notices, action_primary=None, ttl_seconds=TTL_OCR, pipeline_version=OCR_PIPELINE_VERSION)
    envelope["pipeline_version_summary"] = {
        "total": len(rows), "on_current": papers_on_current, "stale": papers_stale,
    }
    envelope["per_paper_pipeline_version"] = per_paper_versions
    return envelope


def probe_memory(vault: Path) -> dict[str, Any]:
    """Probe the Memory module.

    Decision tree (resolved by grilling 2026-07-23):
    1. Module disabled → not_enabled
    2. No paperforge.db → build memory
    3. Schema mismatch → rebuild / restore
    4. Index stale → rebuild index
    5. build_state routes the vector backend:
       a. completed → ready (+ API key notice if missing)
       b. running  → ready + activity
       c. failed   → rebuild vector
       d. absent   → check ChromaDB → upgrade, or build vector
    """
    # ── Gate 0: disabled module ──────────────────────────────────────────
    settings_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if settings_path.exists():
        try:
            import json
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if not settings.get("features", {}).get("vector_db", False):
                return build_envelope(
                    module="memory", capability_state="not_configured", severity="ok",
                    reason_code="memory.disabled", reason_text="Smart Retrieval is not enabled",
                    user_state=USER_STATE_NOT_ENABLED, capability_kind=CAPABILITY_OPTIONAL,
                    action_primary=build_action_primary(
                        action_id="memory.enable", verb="set_config",
                        label="Enable Smart Retrieval", command="paperforge setup",
                    ),
                    ttl_seconds=TTL_MEMORY,
                )
        except Exception:
            pass  # fall through to DB-based probe

    # ── Gates 1-4: DB-based checks ────────────────────────────────────
    try:
        from paperforge.memory.query import get_memory_status
        from paperforge.memory.schema import CURRENT_SCHEMA_VERSION as _CURRENT_SCHEMA
        status = get_memory_status(vault)
    except Exception:
        return build_envelope(
            module="memory", capability_state="unknown", severity="unknown",
            reason_code="memory.probe_failed", reason_text="Memory status check failed — probe to retry",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.probe", verb="probe", label="Retry", command="probe memory",
            ),
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
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.build", verb="run", label="Build memory",
                command="paperforge memory build",
            ),
            ttl_seconds=TTL_MEMORY,
        )

    # Schema check failed
    if not schema_ok:
        if paper_count_db > 0:
            # DB has papers but old schema → needs rebuild
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.migration_needed",
                reason_text="Memory database schema version is outdated — rebuild to update",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                maintenance_eligible=True,
                action_primary=build_action_primary(
                    action_id="memory.rebuild",
                    verb="rebuild_index", label="Rebuild database", command="paperforge memory build",
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
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                maintenance_eligible=True,
                user_impact="Search and retrieval are unavailable until the database is restored",
                action_primary=build_action_primary(
                    action_id="memory.restore_backup",
                    verb="restore_backup", label="Restore from backup",
                    command="paperforge memory restore-backup",
                    safety_class=SAFETY_DESTRUCTIVE,
                    replacement_facts=["Current corrupted database"],
                    preservation_facts=["Corrupted database saved as timestamped snapshot"],
                    confirmation_required=True,
                    confirmation_prompt="This will replace the memory database with the backup copy. The corrupted database will be preserved. Proceed?",
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )
        return build_envelope(
            module="memory", capability_state="unavailable", severity="error",
            reason_code="memory.db_corrupt",
            reason_text="Memory database is corrupted or uninitialized — rebuild required (source data preserved)",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            maintenance_eligible=True,
            user_impact="Search and retrieval are unavailable until the database is rebuilt",
            action_primary=build_action_primary(
                action_id="memory.rebuild",
                verb="run", label="Rebuild memory", command="paperforge memory build",
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

    # Stale: schema OK but index hash doesn't match
    if not fresh:
        return build_envelope(
            module="memory", capability_state="needs_action", severity="warning",
            reason_code="memory.index_stale",
            reason_text=f"Memory index needs rebuild (DB: {paper_count_db} papers, Index: {paper_count_index} papers)",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.rebuild",
                verb="rebuild_index", label="Rebuild index", command="paperforge memory build",
            ),
            ttl_seconds=TTL_MEMORY,
        )

    # ── Vector backend health via build_state ────────────────────────────
    notices: list[dict[str, Any]] = []
    try:
        from paperforge.embedding.build_state import read_vector_build_state

        build_state = read_vector_build_state(vault)
        bs_status = build_state.get("status", "idle")

        # Gate 5a: completed → ready
        if bs_status == "completed":
            # #119: the vector stack (openai + sqlite-vec) is a hard runtime
            # requirement for Build Index / Retrieve — a healthy-looking DB
            # with missing deps must NOT report ready.
            _dep_missing: list[str] = []
            try:
                import openai  # noqa: F401
            except ImportError:
                _dep_missing.append("openai")
            try:
                import sqlite_vec  # noqa: F401
            except ImportError:
                _dep_missing.append("sqlite_vec")
            if _dep_missing:
                return build_envelope(
                    module="memory", capability_state="needs_action", severity="warning",
                    reason_code="memory.dependencies_missing",
                    reason_text=f"Smart Retrieval deps missing: {', '.join(_dep_missing)} — reinstall with paperforge[vector]",
                    user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                    notices=[{"kind": "warning", "text": f"Missing: {', '.join(_dep_missing)}. Reinstall the runtime with paperforge[vector]."}],
                    action_primary=build_action_primary(
                        action_id="memory.install_vector_deps", verb="install",
                        label="Install Smart Retrieval dependencies",
                        command="paperforge setup",
                    ),
                    ttl_seconds=TTL_MEMORY,
                )
            # Quick API key presence check (no API call, just config)
            from paperforge.embedding._config import get_api_key

            if not get_api_key(vault):
                notices.append({
                    "kind": "warning",
                    "text": "API key not configured — search works, but the next rebuild needs one",
                })
            return build_envelope(
                module="memory", capability_state="ready", severity="ok",
                reason_code="memory.ready",
                reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
                notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5b: running → ready + activity
        if bs_status == "running":
            act_label = f"Building vector index ({build_state.get('current', 0)}/{build_state.get('total', 0)})"
            act_progress = {
                "current": build_state.get("current", 0),
                "total": build_state.get("total", 0),
            }
            return build_envelope(
                module="memory", capability_state="ready", severity="ok",
                reason_code="memory.ready",
                reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
                activity_state="running", activity_label=act_label,
                activity_progress=act_progress,
                notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5c: failed → rebuild
        if bs_status == "failed":
            msg = build_state.get("message", "unknown error")
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.vector_build_failed",
                reason_text=f"Last vector build failed: {msg}. Existing vectors are still usable.",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                action_primary=build_action_primary(
                    action_id="memory.rebuild_vector",
                    verb="rebuild_index", label="Rebuild vector index",
                    command="paperforge embed build --force",
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )

        # Gate 5d: build_state absent (idle / never built / 1.5.15)
        # Check if vec0 already has data (build_state may have been lost)
        from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path, open_live_reader

        db_path = get_memory_db_path(vault)
        vec0_has_data = False
        if db_path.exists():
            try:
                with open_live_reader(vault, db_path) as conn:
                    ensure_vec_extension(conn)
                    row = conn.execute("SELECT COUNT(*) AS cnt FROM vec_body_meta LIMIT 1").fetchone()
                    vec0_has_data = bool(row and row["cnt"] > 0)
            except Exception:
                pass

        if vec0_has_data:
            # vec0 has data — build_state was lost, treat as ready
            return build_envelope(
                module="memory", capability_state="ready", severity="ok",
                reason_code="memory.ready",
                reason_text=f"Memory database healthy ({paper_count_db} papers, {paper_count_index} indexed)",
                user_state=USER_STATE_READY, capability_kind=CAPABILITY_OPTIONAL,
                notices=notices, action_primary=None, ttl_seconds=TTL_MEMORY,
            )

        # Check ChromaDB presence for 1.5.15 upgrade path
        from paperforge.embedding._chroma import get_vector_db_path as _get_chroma_path

        chroma_path = _get_chroma_path(vault) / "chroma.sqlite3"
        if chroma_path.exists():
            return build_envelope(
                module="memory", capability_state="needs_action", severity="warning",
                reason_code="memory.backend_upgrade_available",
                reason_text="Smart Retrieval uses the ChromaDB backend. A newer sqlite-vec backend is available — rebuild to switch.",
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
                action_primary=build_action_primary(
                    action_id="memory.upgrade_backend",
                    verb="rebuild_index", label="Rebuild index",
                    command="paperforge embed build --force",
                    safety_class=SAFETY_DESTRUCTIVE,
                    confirmation_required=True,
                    confirmation_prompt=(
                        "Smart Retrieval backend upgrade\n\n"
                        "What will happen\n"
                        "• The current ChromaDB index is backed up to paperforge.pre-rebuild-{timestamp}.db\n"
                        "• A fresh sqlite-vec index is built from your existing paper data\n"
                        "• Your embedding API is called once per paper to create new vectors\n"
                        "• After completion, PaperForge switches to the new backend automatically\n\n"
                        "What is at risk\n"
                        "• Embedding API charges: papers × your provider's rate\n"
                        "• Search will not work while the rebuild runs\n"
                        "• If the rebuild fails, PaperForge restores the backup automatically "
                        "and your current ChromaDB index remains usable\n\n"
                        "What stays untouched\n"
                        "• Your notes, PDFs, and OCR fulltext\n"
                        "• Your existing ChromaDB data (preserved in the vectors/ directory)\n"
                        "• Your memory database structure and paper metadata"
                    ),
                ),
                notices=notices, ttl_seconds=TTL_MEMORY,
            )

        # No vec0 data, no ChromaDB — never built vectors
        return build_envelope(
            module="memory", capability_state="needs_action", severity="warning",
            reason_code="memory.index_stale",
            reason_text="Vector index has not been built — rebuild to enable semantic search",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.rebuild_vector",
                verb="rebuild_index", label="Build vector index",
                command="paperforge embed build --force",
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

    except Exception:
        return build_envelope(
            module="memory", capability_state="unknown", severity="unknown",
            reason_code="memory.vector_probe_failed",
            reason_text="Vector index health check failed — probe to retry",
            user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_OPTIONAL,
            action_primary=build_action_primary(
                action_id="memory.probe", verb="probe", label="Retry", command="probe memory",
            ),
            notices=notices, ttl_seconds=TTL_MEMORY,
        )

# ---------------------------------------------------------------------------
# Maintenance projection (Issue #80)
# ---------------------------------------------------------------------------

def _worst_severity(severities: list[str]) -> str:
    """Return the worst severity from a list. Ordinal: ok=0, unknown=1, warning=2, error=3."""
    order = {"ok": 0, "unknown": 1, "warning": 2, "error": 3}
    return max(severities, key=lambda s: order.get(s, 0), default="ok")


def probe_maintenance(vault: Path) -> dict[str, Any]:
    """Derive a Maintenance projection from the five constituent modules (#84).

    Maintenance now filters by backend-owned maintenance_eligible flag.
    Only modules with blocking, failed, corrupt, or materially risky conditions
    enter Maintenance. Optional not-enabled capabilities are excluded.
    """
    probes = {
        "installation": probe_installation,
        "library": probe_library,
        "ocr": probe_ocr,
        "memory": probe_memory,
        "help": probe_help,
    }

    items: list[dict[str, Any]] = []
    for mod_name, probe_fn in probes.items():
        try:
            env = probe_fn(vault)
        except Exception:
            env = build_envelope(
                module=mod_name, capability_state="unknown", severity="unknown",
                reason_code=f"{mod_name}.probe_failed",
                reason_text=f"{mod_name} probe failed — try again",
                user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_REQUIRED,
                action_primary=build_action_primary(
                    action_id=f"{mod_name}.probe",
                    verb="probe", label="Retry", command=f"probe {mod_name}",
                ),
                ttl_seconds=60,
            )

        # #84: maintenance_eligible backend-owned filter
        is_eligible = env.get("maintenance_eligible", False)
        if not is_eligible:
            continue

        items.append({
            "module": mod_name,
            "capability_state": env["capability_state"],
            "severity": env["severity"],
            "activity_state": env["activity_state"],
            "activity_label": env.get("activity_label"),
            "activity_progress": env.get("activity_progress"),
            "reason_code": env["reason"]["code"],
            "reason_text": env["reason"]["text"],
            "action": env["action"]["primary"],
            "user_state": env.get("user_state"),
            "user_impact": env.get("user_impact"),
            "maintenance_eligible": True,
        })

    if len(items) == 0:
        envelope = build_envelope(
            module="maintenance", capability_state="ready", severity="ok",
            reason_code="maintenance.no_items",
            reason_text="All modules are ready — no maintenance needed",
            user_state=USER_STATE_READY, capability_kind=CAPABILITY_REQUIRED,
            action_primary=None, ttl_seconds=TTL_MAINTENANCE,
        )
        envelope["items"] = []
        return envelope

    severities = [item["severity"] for item in items]
    worst = _worst_severity(severities)
    item_count = len(items)

    envelope = build_envelope(
        module="maintenance", capability_state="needs_action", severity=worst,
        reason_code="maintenance.items_present",
        reason_text=f"{item_count} module(s) need attention",
        user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
        maintenance_eligible=True,
        user_impact=f"{item_count} problem(s) require action to restore full PaperForge functionality",
        action_primary=None, ttl_seconds=TTL_MAINTENANCE,
    )
    envelope["items"] = items
    return envelope


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def run(args: Any) -> int:
    vault: Path = args.vault_path
    module: str = args.probe_module

    if module == "installation":
        envelope = probe_installation(vault, expected_version=getattr(args, "expected_version", None))
    elif module == "library":
        last_code: int | None = getattr(args, "last_operation_exit_code", None)
        envelope = probe_library(vault, last_operation_exit_code=last_code)
    elif module == "ocr":
        envelope = probe_ocr(vault)
    elif module == "memory":
        envelope = probe_memory(vault)
    elif module == "help":
        envelope = probe_help(vault)
    elif module == "maintenance":
        envelope = probe_maintenance(vault)
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
