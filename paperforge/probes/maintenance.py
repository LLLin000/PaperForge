"""paperforge.probes.maintenance — fan-out dispatcher and maintenance projection (P1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.probes.envelope import (build_action_primary, build_envelope, CAPABILITY_REQUIRED, TTL_MAINTENANCE, USER_STATE_ACTION_REQUIRED, USER_STATE_DETECTION_FAILED, USER_STATE_READY)

from paperforge.probes.help import probe_help
from paperforge.probes.installation import probe_installation
from paperforge.probes.library import probe_library
from paperforge.probes.memory import probe_memory
from paperforge.probes.ocr import probe_ocr


PROBE_ORDER = ("installation", "library", "ocr", "memory", "help")


def _worst_severity(severities: list[str]) -> str:
    """Return the worst severity from a list. Ordinal: ok=0, unknown=1, warning=2, error=3."""
    order = {"ok": 0, "unknown": 1, "warning": 2, "error": 3}
    return max(severities, key=lambda s: order.get(s, 0), default="ok")


def _probe_base_modules(
    vault: Path,
    lineage: dict[str, Any] | None = None,
    installation_expected_version: str | None = None,
) -> dict[str, dict[str, Any]]:
    """#140: fixed dispatcher — each base reader runs exactly once, in
    PROBE_ORDER, sequentially. An unexpected reader exception becomes that
    module's valid detection_failed envelope; the aggregate never aborts."""
    probes = {
        "installation": probe_installation,
        "library": probe_library,
        "ocr": probe_ocr,
        "memory": probe_memory,
        "help": probe_help,
    }
    modules: dict[str, dict[str, Any]] = {}
    for mod_name in PROBE_ORDER:
        probe_fn = probes[mod_name]
        try:
            if mod_name == "ocr":
                try:
                    modules[mod_name] = probe_fn(vault, lineage=lineage)
                except TypeError:
                    modules[mod_name] = probe_fn(vault)
            elif mod_name == "installation":
                if installation_expected_version is None:
                    modules[mod_name] = probe_fn(vault)
                else:
                    modules[mod_name] = probe_fn(
                        vault, expected_version=installation_expected_version
                    )
            else:
                modules[mod_name] = probe_fn(vault)
        except Exception:
            modules[mod_name] = build_envelope(
                module=mod_name, capability_state="unknown", severity="unknown",
                reason_code=f"{mod_name}.probe_failed",
                reason_text=f"{mod_name} probe failed — try again",
                user_state=USER_STATE_DETECTION_FAILED, capability_kind=CAPABILITY_REQUIRED,
                action_primary=build_action_primary(
                    action_id=f"{mod_name}.probe",
                    verb="probe", label="Retry",
                ),
                ttl_seconds=60,
            )
    return modules


def derive_maintenance(
    modules: dict[str, dict[str, Any]], vault: Path | None = None,
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """#140: pure projection of the base envelopes — maintenance NEVER
    re-probes canonical sources. Only backend-owned maintenance_eligible
    envelopes enter; optional not-enabled capabilities are excluded."""
    items: list[dict[str, Any]] = []
    for mod_name in PROBE_ORDER:
        env = modules[mod_name]

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

    return _derive_maintenance_tail(items, vault, lineage=lineage)


def _derive_maintenance_tail(
    items: list[dict[str, Any]], vault: Path | None = None,
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Envelope construction shared by the pure projection and the
    standalone `probe maintenance` fan-out."""
    if len(items) == 0:
        envelope = build_envelope(
            module="maintenance", capability_state="ready", severity="ok",
            reason_code="maintenance.no_items",
            reason_text="No maintenance items — check each module state for readiness",
            user_state=USER_STATE_READY, capability_kind=CAPABILITY_REQUIRED,
            action_primary=None, ttl_seconds=TTL_MAINTENANCE,
        )
        envelope["items"] = []
    else:
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
    if vault is not None:
        try:
            if (
                lineage is not None
                and isinstance(lineage, dict)
                and isinstance(lineage.get("orphan"), dict)
            ):
                envelope["orphan"] = lineage["orphan"]
                # resids already included in snapshot; ensure envelope reflects
                # the residual count consistently (compatibility shape).
            else:
                from paperforge import lineage

                envelope["orphan"] = lineage._detect_orphans(vault)
        except Exception:  # noqa: BLE001
            envelope["orphan"] = {"count": 0, "keys": []}
    return envelope


def probe_maintenance(vault: Path) -> dict[str, Any]:
    """Standalone maintenance probe — same fan-out and projection as
    probe_all (#140): five base readers, then the pure projection."""
    try:
        from paperforge.lineage import probe_lineage as _pl

        lineage_snapshot = _pl(vault)
    except Exception:  # noqa: BLE001
        lineage_snapshot = None
    return derive_maintenance(_probe_base_modules(vault, lineage=lineage_snapshot), vault, lineage=lineage_snapshot)
