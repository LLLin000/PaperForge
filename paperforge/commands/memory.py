from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.builder import build_from_index
from paperforge.memory.query import get_memory_status



def _restore_backup(vault: Path) -> PFResult:
    """Restore paperforge.db from a validated backup.

    Backup is staged to a temporary file then atomically installed via os.replace.
    The current DB (if any) is copied to a timestamped corrupt-* snapshot before replacement.
    The backup file is never modified — it remains in place.

    Steps:
    1. Validate backup with context-managed PRAGMA integrity_check
    2. Copy current DB to timestamped .corrupt-* snapshot (if exists)
    3. Copy backup to a unique same-directory temp file
    4. Atomic os.replace(temp, db_path)
    5. On any failure, current DB and backup remain unchanged; clean temp.
    """
    import os
    import shutil
    import sqlite3
    import time

    from paperforge.memory.db import get_memory_db_path

    db_path = get_memory_db_path(vault)
    backup_path = db_path.with_suffix(db_path.suffix + ".backup")

    if not backup_path.exists():
        return PFResult(
            ok=False,
            command="memory restore-backup",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message=f"No backup found at {backup_path}",
            ),
        )

    # ── Validate backup integrity (read-only, explicit close to release Windows locks) ──
    try:
        backup_uri = "file:" + backup_path.as_posix() + "?mode=ro"
        conn = sqlite3.connect(backup_uri, uri=True)
        row = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if not row or row[0] != "ok":
            return PFResult(
                ok=False,
                command="memory restore-backup",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Backup integrity check failed: {row[0] if row else 'no result'}",
                ),
            )
    except sqlite3.Error as e:
        return PFResult(
            ok=False,
            command="memory restore-backup",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Cannot validate backup: {e}",
            ),
        )

    # ── Staging: unique timestamp ──
    ts = time.strftime("%Y%m%dT%H%M%S")
    ns = str(int(time.time_ns() % 1_000_000_000)).zfill(9)  # ponytail: nanosecond suffix for uniqueness

    # ── Preserve current DB via copy (never move) ──
    corrupt_path = None
    if db_path.exists():
        corrupt_path = db_path.with_name(f"paperforge.corrupt-{ts}-{ns}.db")
        try:
            shutil.copy2(str(db_path), str(corrupt_path))
        except OSError as e:
            return PFResult(
                ok=False,
                command="memory restore-backup",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to preserve current database: {e}",
                ),
            )

    # ── Copy backup to unique same-directory temp ──
    temp_path = db_path.with_name(f"paperforge.restore-{ts}-{ns}.tmp")
    try:
        shutil.copy2(str(backup_path), str(temp_path))
        # ponytail: copy2 already flushes; atomic replace is the real guarantee
    except OSError as e:
        # Clean temp on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        return PFResult(
            ok=False,
            command="memory restore-backup",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to stage backup: {e}",
            ),
        )

    # ── Atomic replace temp → db_path ──
    try:
        os.replace(str(temp_path), str(db_path))
    except OSError as e:
        # Clean temp on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        return PFResult(
            ok=False,
            command="memory restore-backup",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to restore backup: {e}",
            ),
        )

    return PFResult(
        ok=True,
        command="memory restore-backup",
        version=PF_VERSION,
        data={
            "action": "restore_backup",
            "preserved_as": str(corrupt_path) if corrupt_path else None,
        },
    )


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
            from paperforge.memory.db import get_connection, get_memory_db_path
            from paperforge.memory.schema import get_schema_version
            from paperforge.memory.state_snapshot import write_memory_runtime
            _last_full_build = ""
            _schema_ver = None
            _fts_ok = False
            _db_p = get_memory_db_path(vault)
            if _db_p.exists():
                conn2 = get_connection(_db_p, read_only=True)
                _row = conn2.execute(
                    "SELECT value FROM meta WHERE key = 'last_full_build'"
                ).fetchone()
                _last_full_build = _row["value"] if _row else ""
                _schema_ver = get_schema_version(conn2)
                try:
                    conn2.execute("SELECT zotero_key FROM papers_fts LIMIT 1")
                    _fts_ok = True
                except Exception:
                    _fts_ok = False
                conn2.close()
            write_memory_runtime(vault, status)
            data = {
                **status,
                "last_full_build": _last_full_build,
                "schema_version": _schema_ver,
                "fts_ok": _fts_ok,
            }
            result = PFResult(
                ok=True,
                command="memory status",
                version=PF_VERSION,
                data=data,
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
                for k, v in (result.data or {}).items():
                    print(f"{k}: {v}")
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    if sub_cmd == "restore-backup":
        result = _restore_backup(vault)
        if args.json:
            print(result.to_json())
        else:
            if result.ok:
                data = result.data or {}
                print("Memory database restored from verified backup.")
                if data.get("preserved_as"):
                    print(f"Corrupted database preserved as: {data['preserved_as']}")
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    print(f"Unknown memory subcommand: {sub_cmd}", file=sys.stderr)
    return 1
