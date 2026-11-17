"""Capability-probe shared envelope: constants, TTLs, schema-v2 builders.

Moved verbatim from paperforge/commands/probe.py (P1 modularization);
behavior is unchanged. Canvas for the six reader modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    *, action_id: str, verb: str, label: str,
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
    # Registered actions project safety and confirmation from the registry.
    # Probe decides *why* an action is shown; the registry alone decides
    # whether it mutates, requires consent, and can be interrupted.
    from paperforge.actions.registry import ACTION_REGISTRY, classify_action_id

    # #223: an envelope must never advertise an id nothing can execute. This
    # raises for an id that is neither registered nor declared non-registry,
    # so a new probe id fails here instead of reaching a user as a dead control.
    classify_action_id(action_id)

    spec = ACTION_REGISTRY.get(action_id)
    execution_mode = "stream" if verb == "setup" else "result"
    if spec is not None:
        safety_class = (
            SAFETY_DESTRUCTIVE
            if spec.impact == "destructive" or spec.confirmation == "required"
            else SAFETY_SAFE
        )
        interruptible = spec.interruptible
        confirmation_required = spec.confirmation == "required"
        execution_mode = spec.execution_mode
    return {
        "action_id": action_id, "verb": verb, "label": label,
        "availability": availability, "safety_class": safety_class,
        "preservation_facts": preservation_facts or [],
        "replacement_facts": replacement_facts or [],
        "interruptible": interruptible,
        "confirmation_required": confirmation_required,
        "confirmation_prompt": confirmation_prompt,
        # T8 (#169): `command` is DELETED — the plugin never consumes a
        # backend command string; action dispatch is the action client.
        "scope": scope, "scope_count": scope_count,
        "execution_mode": execution_mode,
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


def _config_is_recognized(data: dict[str, Any] | None) -> bool:
    """Recognized = current schema or legacy awaiting explicit migration."""
    return isinstance(data, dict) and len(data) > 0


def _load_pf_config(vault: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Classify canonical configuration through the #142 seam (fail-closed).

    Returns (data, error): (None, None) for missing, (None, 'corrupt') for
    corrupt/future/invalid, (resolved-values, None) for current schema.
    Legacy (migration_required) configs are reported as missing-like: migration
    is explicit and must happen before probes interpret the vault.
    """
    from paperforge.config import ConfigError, load_config, validate_config

    validation = validate_config(vault)
    if validation.state == "missing":
        return None, None
    if validation.state == "migration_required":
        return None, None
    if validation.state in ("invalid", "future_schema"):
        return None, "corrupt"
    try:
        snapshot = load_config(vault)
    except ConfigError:
        return None, "corrupt"
    return {key: cv.value for key, cv in snapshot.values.items()}, None
