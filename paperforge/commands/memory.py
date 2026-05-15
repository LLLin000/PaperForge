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
            # Write memory-runtime-state.json snapshot (JS-First Memory State)
            try:
                from paperforge.memory.state_snapshot import write_memory_runtime
                from paperforge.memory.db import get_memory_db_path, get_connection
                from paperforge.memory.schema import get_schema_version
                _last_full_build = ""
                _schema_ver_db = 0
                _fts_ok = False
                _db_p = get_memory_db_path(vault)
                if _db_p.exists():
                    conn2 = get_connection(_db_p, read_only=True)
                    _row = conn2.execute(
                        "SELECT value FROM meta WHERE key = 'last_full_build_at'"
                    ).fetchone()
                    if _row:
                        _last_full_build = _row["value"]
                    _schema_ver_db = get_schema_version(conn2)
                    _fts_row = conn2.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='paper_fts'"
                    ).fetchone()
                    _fts_ok = _fts_row is not None
                    conn2.close()
                write_memory_runtime(
                    vault,
                    paper_count_db=status["paper_count_db"],
                    paper_count_index=status["paper_count_index"],
                    fresh=status["fresh"],
                    needs_rebuild=status["needs_rebuild"],
                    last_full_build_at=_last_full_build,
                    schema_version_db=_schema_ver_db,
                    fts_ready=_fts_ok,
                )
            except Exception:
                pass
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
