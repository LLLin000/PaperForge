from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.result import PFResult
from paperforge.memory.runtime_health import get_runtime_health
from paperforge.memory.state_snapshot import write_runtime_health


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    health = get_runtime_health(vault)
    result = PFResult(ok=True, command="runtime-health", version=PF_VERSION, data=health)

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

    write_runtime_health(vault, result.data if result.ok else {"summary": {"status": "error"}})

    return 0
