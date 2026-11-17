"""paperforge.probes.help — help capability reader (P1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.probes.envelope import (build_action_primary, build_envelope, CAPABILITY_OPTIONAL, TTL_HELP, USER_STATE_DETECTION_FAILED, USER_STATE_READY)


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
            verb="setup", label="Restore help",
        ),
        ttl_seconds=TTL_HELP,
    )
