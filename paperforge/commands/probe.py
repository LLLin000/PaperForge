"""paperforge.commands.probe — Capability probe command (Issue #76, #78, #84).

Emits schema-v2 capability envelopes for the Obsidian plugin's control center.
Probes use canonical sources: paperforge_paths, load_vault_config,
get_memory_status, collect_maintenance_rows.

#84: Added action_id, availability, safety_class, preservation_facts,
replacement_facts, interruptible to actions; user_state, capability_kind,
maintenance_eligible, user_visible_failure, user_impact to envelopes.

P1 modularization: the six readers live in paperforge/probes/* and the
fan-out/maintenance projection in paperforge/probes/maintenance.py. This
module re-exports the required compatibility names and retains CLI dispatch
(`run`, `_run_probe_all`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from paperforge.probes import envelope as _envelope
from paperforge.probes import maintenance as _maintenance
from paperforge.probes.envelope import SCHEMA_VERSION, build_action_primary
from paperforge.probes.help import probe_help
from paperforge.probes.installation import probe_installation
from paperforge.probes.library import probe_library
from paperforge.probes.maintenance import derive_maintenance, probe_maintenance
from paperforge.probes.memory import probe_memory
from paperforge.probes.ocr import paper_pipeline_versions, probe_ocr


def _run_probe_all(vault: Path, *, json_output: bool, expected_version: str | None = None) -> int:
    """#140/#148: probe all reads each base capability exactly once,
    derives the maintenance projection from those exact envelopes (zero
    re-probe), and returns the six-module envelope map. A failing probe
    degrades to its own detection_failed envelope; never aborts.
    The plugin's expected package version gates installation readiness so
    the RC4 pointer is never reported ready under an rc5 bundle."""
    import json as _json

    try:
        from paperforge.lineage import probe_lineage as _pl

        lineage_snapshot = _pl(vault)
    except Exception:  # noqa: BLE001
        lineage_snapshot = None
    modules = _maintenance._probe_base_modules(
        vault, lineage=lineage_snapshot, installation_expected_version=expected_version
    )
    modules["maintenance"] = derive_maintenance(modules, vault, lineage=lineage_snapshot)
    aggregate = {
        "schema_version": SCHEMA_VERSION,
        "module": "all",
        "updated_at": _envelope._utcnow_z(),
        "modules": modules,
    }
    if json_output:
        print(_json.dumps(aggregate, indent=2, ensure_ascii=False))
    else:
        for mod_name, env in modules.items():
            print(f"[{mod_name}] {env['capability_state']}: {env['reason']['text']}")
    return 0


def run(args: Any) -> int:
    vault: Path = args.vault_path
    module: str = args.probe_module

    if module == "all":
        return _run_probe_all(
            vault,
            json_output=bool(getattr(args, "json", False)),
            expected_version=getattr(args, "expected_version", None),
        )

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
    elif module == "lineage":
        from paperforge.lineage import probe_lineage

        payload = probe_lineage(vault)
        json_output = bool(getattr(args, "json", False))
        if json_output:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            state = payload.get("capability_state", "unknown")
            reason = (payload.get("reason") or {}).get("text", "")
            print(f"[lineage] {state}: {reason}")
        return 0
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
