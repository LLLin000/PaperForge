"""paperforge.commands.probe — Capability probe command (Issue #76, contract #69).

Emits direct schema-v1 capability envelopes (not PFResult-wrapped) for the
Obsidian plugin's six-module control center. Only Installation and Help have
real probes in this tracer; the remaining four modules (Library, OCR, Memory,
Maintenance) are explicit unknown placeholders.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1
TTL_INSTALLATION = 3600
TTL_HELP = 3600
MIN_PYTHON = (3, 11)
LEGACY_PATH_KEYS = frozenset({
    "system_dir", "resources_dir", "literature_dir",
    "base_dir", "control_dir", "skill_dir", "command_dir",
})

SUPPORTED_MODULES = frozenset({"installation", "help"})


# ---------------------------------------------------------------------------
# Envelope builder
# ---------------------------------------------------------------------------

def _utcnow_z() -> str:
    """Return current UTC time as ISO 8601 with Z suffix (e.g. 2026-07-15T12:34:56Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_action_primary(
    *,
    verb: str,
    label: str,
    command: str,
    destructive: bool = False,
    destructive_scope: str | None = None,
    destructive_effect: str | None = None,
    confirmation_required: bool = False,
    confirmation_prompt: str | None = None,
    scope: str = "module",
    scope_count: int = 1,
) -> dict[str, Any]:
    """Build a full action.primary dict per #69 contract fields."""
    return {
        "verb": verb,
        "label": label,
        "destructive": destructive,
        "destructive_scope": destructive_scope,
        "destructive_effect": destructive_effect,
        "confirmation_required": confirmation_required,
        "confirmation_prompt": confirmation_prompt,
        "command": command,
        "scope": scope,
        "scope_count": scope_count,
    }


def build_envelope(
    *,
    module: str,
    capability_state: str,
    severity: str,
    reason_code: str,
    reason_text: str,
    action_primary: dict[str, Any] | None = None,
    activity_state: str = "idle",
    activity_label: str | None = None,
    activity_progress: float | None = None,
    ttl_seconds: int = 3600,
    notices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a schema-v1 capability envelope.

    Required fields per #69 contract:
    schema_version, module, capability_state, activity_state, activity_label,
    activity_progress, severity, reason{code,text}, action{primary}, notices,
    updated_at, ttl_seconds.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "module": module,
        "capability_state": capability_state,
        "activity_state": activity_state,
        "activity_label": activity_label,
        "activity_progress": activity_progress,
        "severity": severity,
        "reason": {
            "code": reason_code,
            "text": reason_text,
        },
        "action": {"primary": action_primary},
        "notices": notices or [],
        "updated_at": _utcnow_z(),
        "ttl_seconds": ttl_seconds,
    }


# ---------------------------------------------------------------------------
# Config validation helper
# ---------------------------------------------------------------------------

def _is_recognizable_config(data: Any) -> bool:
    """Return True if *data* looks like a recognizable PaperForge config.

    Accepts:
    - dict with a ``vault_config`` key (v2 format)
    - dict with at least one legacy path key (pre-migration format)

    Rejects:
    - non-dict types (list, str, number, bool)
    - empty dict ``{}``
    - dict with keys but neither ``vault_config`` nor any legacy path key
    """
    if not isinstance(data, dict) or len(data) == 0:
        return False
    if "vault_config" in data:
        return True
    return any(k in data for k in LEGACY_PATH_KEYS)


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def probe_installation(vault: Path) -> dict[str, Any]:
    """Probe the Installation module.

    Read-only probe that checks:
    1. paperforge.json exists
    2. paperforge.json is valid and recognizable config
    3. Current Python >= 3.11
    4. Everything OK → ready

    Does NOT search for ambient Python, spawn interpreters, or instantiate
    SetupPlan (that is #77's domain).
    """
    pf_json = vault / "paperforge.json"

    # 1. Missing config
    if not pf_json.exists():
        return build_envelope(
            module="installation",
            capability_state="missing_input",
            severity="warning",
            reason_code="installation.config_missing",
            reason_text="paperforge.json not found in vault",
            action_primary=build_action_primary(
                verb="set_config",
                label="Set config",
                command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    # 2. Parse JSON
    try:
        data = json.loads(pf_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return build_envelope(
            module="installation",
            capability_state="unavailable",
            severity="error",
            reason_code="installation.config_corrupt",
            reason_text="paperforge.json is corrupt or invalid",
            action_primary=build_action_primary(
                verb="setup",
                label="Setup",
                command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    # 2b. Validate config shape — list, primitive, empty, or unrecognized
    if not _is_recognizable_config(data):
        return build_envelope(
            module="installation",
            capability_state="unavailable",
            severity="error",
            reason_code="installation.config_corrupt",
            reason_text="paperforge.json has unrecognizable structure",
            action_primary=build_action_primary(
                verb="setup",
                label="Setup",
                command="paperforge setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    # 3. Python version check
    py_version = sys.version_info[:2]
    if py_version < MIN_PYTHON:
        return build_envelope(
            module="installation",
            capability_state="limited",
            severity="warning",
            reason_code="installation.python_version_unsupported",
            reason_text=(
                f"Python {py_version[0]}.{py_version[1]} < "
                f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
            ),
            action_primary=build_action_primary(
                verb="update",
                label="Update Python",
                command="",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    # 4. All good
    return build_envelope(
        module="installation",
        capability_state="ready",
        severity="ok",
        reason_code="installation.ready",
        reason_text="PaperForge is installed and configured",
        action_primary=None,
        ttl_seconds=TTL_INSTALLATION,
    )


def probe_help(vault: Path) -> dict[str, Any]:  # noqa: ARG001
    """Probe the Help module.

    Checks whether the packaged PaperForge help/skill source exists so that
    first-run help can be ready immediately.
    """
    skills_dir = Path(__file__).resolve().parent.parent / "skills" / "paperforge"
    skill_md = skills_dir / "SKILL.md"

    if skill_md.exists():
        return build_envelope(
            module="help",
            capability_state="ready",
            severity="ok",
            reason_code="help.ready",
            reason_text="Help and skill documentation available",
            action_primary=None,
            ttl_seconds=TTL_HELP,
        )

    return build_envelope(
        module="help",
        capability_state="limited",
        severity="warning",
        reason_code="help.docs_missing",
        reason_text="Packaged help source not found",
        action_primary=build_action_primary(
            verb="setup",
            label="Restore help",
            command="paperforge setup",
        ),
        ttl_seconds=TTL_HELP,
    )


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def run(args: Any) -> int:
    """Dispatch a probe command and print the envelope.

    Called from paperforge.cli.main().
    """
    vault: Path = args.vault_path
    module: str = args.probe_module

    if module == "installation":
        envelope = probe_installation(vault)
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
