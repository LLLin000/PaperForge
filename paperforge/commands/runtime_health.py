from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.runtime_health import get_runtime_health


def _normalize_health_for_cli(vault: Path, health: dict) -> dict:
    """Normalize runtime-health output so missing logs/ on a writable vault is not a false-positive write block
    and never emits bash-only ``mkdir -p "$logs_dir"`` repair commands on Windows."""
    from paperforge.config import fallback_paperforge_dir, paperforge_paths
    from paperforge.worker.fs_probe import probe_writable

    layers = health.get("layers", {})
    summary = health.get("summary", {})
    capabilities = health.get("capabilities", {})

    # Replace bash-only mkdir -p repair suggestion with cross-platform CLI command.
    read_layer = layers.get("read")
    if isinstance(read_layer, dict) and "mkdir -p" in str(read_layer.get("repair_command") or ""):
        read_layer["repair_command"] = "paperforge sync"
        read_layer["next_action"] = "Run paperforge sync to initialize logs directory"

    write_layer = layers.get("write")
    if isinstance(write_layer, dict) and write_layer.get("status") == "blocked":
        paths = paperforge_paths(vault)
        pf_root = Path(paths.get("paperforge", fallback_paperforge_dir(vault)))
        logs_dir = pf_root / "logs"
        if not logs_dir.exists():
            parent = pf_root if pf_root.is_dir() else Path(vault)
            if probe_writable(parent):
                layers["write"] = {
                    "status": "ok",
                    "evidence": [f"Parent directory writable ({parent}); logs/ can be created on demand"],
                    "next_action": "",
                    "repair_command": "",
                }
                summary["safe_write"] = True
                capabilities["reading_log_write"] = True
                capabilities["project_log_write"] = True
                # Re-derive overall summary status/reason without the false write-blocked signal.
                reasons = [
                    r
                    for r in str(summary.get("reason") or "").split("; ")
                    if r and r not in ("Write layer degraded", "Read and write both blocked", "All systems operational")
                ]
                boot_s = layers.get("bootstrap", {}).get("status", "ok")
                read_s = layers.get("read", {}).get("status", "ok")
                idx_s = layers.get("index", {}).get("status", "ok")
                vec_s = layers.get("vector", {}).get("status", "ok")
                if boot_s == "blocked":
                    summary["status"] = "blocked"
                elif any(s in ("degraded", "blocked") for s in (read_s, idx_s, vec_s)):
                    summary["status"] = "degraded"
                else:
                    summary["status"] = "ok"
                    reasons = ["All systems operational"]
                summary["reason"] = "; ".join(reasons)

    return health


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    try:
        health = _normalize_health_for_cli(Path(vault), get_runtime_health(vault))
        result = PFResult(ok=True, command="runtime-health", version=PF_VERSION, data=health)
    except Exception as exc:  # noqa: BLE001 — JSON transport boundary
        result = PFResult(
            ok=False,
            command="runtime-health",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"{type(exc).__name__}: {exc}",
                suggestions=["Run `paperforge repair --runtime --json` and retry."],
            ),
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    if args.json:
        print(result.to_json())
    else:
        s = health["summary"]
        print(f"Status: {s['status']}")
        print(f"Reason: {s['reason']}")
        print(f"  safe_read:   {s['safe_read']}")
        print(f"  safe_write:  {s['safe_write']}")
        print(f"  safe_build:  {s['safe_build']}")
        print(f"  safe_vector: {s['safe_vector']}")
        for layer_name, layer in health["layers"].items():
            if layer_name == "bootstrap":
                continue
            status = layer["status"]
            print(f"  [{layer_name}] {status}")
            if layer["next_action"]:
                print(f"           next: {layer['next_action']}")
        print(f"Vector job: {health['layers']['vector'].get('job', {}).get('status', 'n/a')}")

    return 0
