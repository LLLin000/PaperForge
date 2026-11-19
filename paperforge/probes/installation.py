"""paperforge.probes.installation — installation capability reader (P1)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from paperforge import __version__ as PAPERFORGE_VERSION
from paperforge.core.versioning import (
    MIN_COMPATIBLE_PLUGIN_VERSION,
    is_version_compatible,
    normalize_release_version,
)
from paperforge.probes.envelope import (build_action_primary, build_envelope, CAPABILITY_REQUIRED, MIN_PYTHON, SAFETY_DESTRUCTIVE, TTL_INSTALLATION, USER_STATE_ACTION_REQUIRED, USER_STATE_READY)


def probe_installation(
    vault: Path,
    expected_version: str | None = None,
    *,
    min_engine_version: str | None = None,
) -> dict[str, Any]:
    """Probe the Python Core only; Vault configuration belongs to probe_library."""
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
                verb="update",
                label="Update Python",
                confirmation_required=False,
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    compat_ok, compat_reason = is_version_compatible(
        core_version=PAPERFORGE_VERSION,
        expected_version=expected_version,
        min_engine_version=min_engine_version,
        plugin_version=expected_version,
        min_plugin_version=MIN_COMPATIBLE_PLUGIN_VERSION,
    )
    if not compat_ok:
        if compat_reason == "plugin_below_min_plugin":
            return build_envelope(
                module="installation", capability_state="needs_action", severity="warning",
                reason_code="installation.version_mismatch",
                reason_text=(
                    f"Obsidian plugin {expected_version} is older than minimum compatible "
                    f"version {MIN_COMPATIBLE_PLUGIN_VERSION} required by PaperForge {PAPERFORGE_VERSION}"
                ),
                user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
                action_primary=build_action_primary(
                    action_id="foundation.update",
                    verb="update",
                    label="Update PaperForge",
                ),
                ttl_seconds=TTL_INSTALLATION,
            )
        return build_envelope(
            module="installation", capability_state="needs_action", severity="warning",
            reason_code="installation.version_mismatch",
            reason_text=(
                f"PaperForge {PAPERFORGE_VERSION} requires >= {min_engine_version}"
                if min_engine_version
                else f"PaperForge {PAPERFORGE_VERSION} does not match plugin {expected_version}"
            ),
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            action_primary=build_action_primary(
                action_id="foundation.update",
                verb="update",
                label="Update PaperForge",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    from paperforge.runtime_pointer import read_pointer

    pointer = read_pointer()
    if pointer is None:
        return build_envelope(
            module="installation", capability_state="needs_action", severity="warning",
            reason_code="installation.runtime_pointer_missing",
            reason_text="PaperForge is installed, but no valid runtime pointer is published",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            user_impact="Run setup to publish the executable PaperForge runtime",
            action_primary=build_action_primary(
                action_id="foundation.setup", verb="setup", label="Complete Setup",
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    ptr_version = str(pointer.get("paperforge_version", "") or "")
    ptr_ok, _ = is_version_compatible(
        core_version=ptr_version,
        expected_version=PAPERFORGE_VERSION if not min_engine_version else None,
        min_engine_version=min_engine_version,
    )
    if not ptr_ok:
        return build_envelope(
            module="installation", capability_state="needs_action", severity="warning",
            reason_code="installation.runtime_pointer_stale",
            reason_text=(
                f"Published runtime version {pointer['paperforge_version']} is older than minimum {min_engine_version}"
                if min_engine_version
                else (
                    "Published runtime version "
                    f"{pointer['paperforge_version']} does not match PaperForge {PAPERFORGE_VERSION}"
                )
            ),
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            user_impact="Update the published PaperForge runtime before using it",
            action_primary=build_action_primary(
                action_id="foundation.update", verb="update", label="Update PaperForge",
                safety_class=SAFETY_DESTRUCTIVE, confirmation_required=True,
                confirmation_prompt=(
                    "Update PaperForge\n\n"
                    "Download and install the latest PaperForge version. "
                    "This changes the installed runtime."
                ),
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    if not Path(pointer["python_path"]).is_file():
        return build_envelope(
            module="installation", capability_state="needs_action", severity="warning",
            reason_code="installation.runtime_executable_missing",
            reason_text="Published runtime pointer targets a missing Python executable",
            user_state=USER_STATE_ACTION_REQUIRED, capability_kind=CAPABILITY_REQUIRED,
            user_impact="Repair the PaperForge runtime before using it",
            action_primary=build_action_primary(
                action_id="foundation.update", verb="update", label="Repair Runtime",
                confirmation_required=False,
            ),
            ttl_seconds=TTL_INSTALLATION,
        )

    return build_envelope(
        module="installation", capability_state="ready", severity="ok",
        reason_code="installation.ready",
        reason_text="PaperForge Core is installed and version-matched",
        user_state=USER_STATE_READY, capability_kind=CAPABILITY_REQUIRED,
        action_primary=None, ttl_seconds=TTL_INSTALLATION,
    )
