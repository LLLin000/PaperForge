from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.builder import build_from_index
from paperforge.memory.query import get_memory_status


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub_cmd = args.memory_subcommand

    if sub_cmd == "build":
        try:
            counts = build_from_index(vault)
            result = PFResult(
                ok=True,
                command="memory build",
                version=PF_VERSION,
                data=counts,
            )
        except FileNotFoundError:
            result = PFResult(
                ok=False,
                command="memory build",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.PATH_NOT_FOUND,
                    message="Canonical index not found. Run paperforge sync --rebuild-index.",
                ),
                next_actions=[
                    {
                        "command": "paperforge sync --rebuild-index",
                        "reason": "Generate formal-library.json first",
                    }
                ],
            )
        except Exception as exc:
            result = PFResult(
                ok=False,
                command="memory build",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(exc),
                ),
            )
        if args.json:
            print(result.to_json())
        else:
            if result.ok:
                print(f"Memory built: {result.data}")
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    if sub_cmd == "status":
        try:
            status = get_memory_status(vault)
            result = PFResult(
                ok=True,
                command="memory status",
                version=PF_VERSION,
                data=status,
            )
        except Exception as exc:
            result = PFResult(
                ok=False,
                command="memory status",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(exc),
                ),
            )
        if args.json:
            print(result.to_json())
        else:
            if result.ok:
                for k, v in status.items():
                    print(f"  {k}: {v}")
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    print(f"Unknown memory subcommand: {sub_cmd}", file=sys.stderr)
    return 1
