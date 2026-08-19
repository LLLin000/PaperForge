"""``paperforge read`` — canonical local-read CLI (#189).

Thin adapter: parse args -> service -> single PFResult.  The service owns
canonical resolution, path handling, and literal matching; this module
never extracts paths or constructs extraction commands.
"""

from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.services.local_read import read_paper_local

VALID_SOURCES = ("auto", "fulltext", "pdf")


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    key = args.key
    find = args.find
    source = args.source

    if source not in VALID_SOURCES:
        result = PFResult(
            ok=False,
            command="read",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.ACTION_SCOPE_INVALID,
                message=f"invalid --source {source!r}: choose from {', '.join(VALID_SOURCES)}",
            ),
        )
        _emit(result, args.json)
        return 2

    try:
        payload = read_paper_local(vault, key, find, source=source)
    except Exception as exc:  # noqa: BLE001 — boundary converts to structured error
        result = PFResult(
            ok=False,
            command="read",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        _emit(result, args.json)
        return 1

    if payload["status"] == "no_readable_source":
        result = PFResult(
            ok=False,
            command="read",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message="no readable source (paper not found, or no valid fulltext/PDF)",
            ),
            data={"status": "no_readable_source", "matches": []},
        )
        _emit(result, args.json)
        return 1

    result = PFResult(
        ok=True,
        command="read",
        version=PF_VERSION,
        data=payload,
    )
    _emit(result, args.json)
    return 0


def _emit(result: PFResult, json_output: bool) -> None:
    if json_output:
        print(result.to_json())
    elif result.ok:
        data = result.data or {}
        status = data.get("status", "")
        print(f"read: {status}")
        for m in data.get("matches", []):
            where = (
                f"line {m['line']}"
                if m.get("line") is not None
                else f"page {m['page']}"
            )
            print(f"  [{m['source']} {where}] {m['text'][:300]}")
    else:
        print(f"Error: {result.error.message if result.error else 'unknown'}", file=sys.stderr)
