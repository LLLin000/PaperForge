from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.runtime_health import get_runtime_health


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    try:
        health = get_runtime_health(vault)
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
