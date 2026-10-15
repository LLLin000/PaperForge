"""E02 — the memory database is restored from its backup, atomically and non-destructively.

Ported from the H case.  The contract asserted is the one its comment states: an
atomic swap from ``paperforge.db.backup``, the corrupt copy preserved, the backup
itself untouched, and the memory layer reporting fresh afterwards.

Two things the reader should know, both observed while porting:

* **nothing in the CLI creates ``paperforge.db.backup``.**  ``memory build`` does
  not write one (verified over repeated builds), so the backup is seeded here the
  way the H case seeds it: a copy of a known-good database.  Recovery *is*
  available without a backup - ``probe memory`` reports ``memory.db_corrupt`` with
  ``action.primary = memory.rebuild`` - but that rebuilds from source, it does not
  restore this file.
* ``memory status`` answers ``INTERNAL_ERROR: file is not a database`` (rc 1) for
  a corrupted database, while the probe reports the same condition as a structured
  state.  Recorded, not asserted: pinning it would freeze the inconsistency
  instead of asking for it.
"""

from __future__ import annotations

import pytest

from .evidence import digest

pytestmark = pytest.mark.harness

CASE_ID = "E02"
TITLE = "The memory database is restored from its backup without losing either copy"
HOST_SPEC_CASE = "restores the memory database from its backup after corruption"


def test_restore_swaps_in_the_backup(retrieval, case) -> None:
    cli = retrieval.cli
    indexes = cli.vault / "System" / "PaperForge" / "indexes"
    db = indexes / "paperforge.db"
    backup = indexes / "paperforge.db.backup"

    built = cli.json("memory", "build")
    case.check("memory build exits 0", built.returncode == 0, built.tail())
    case.check("the database exists to restore over", db.is_file(), str(db))
    case.check("no backup is created by the build", not backup.is_file(), str(backup))

    # ── 1. no backup: refuse, and leave the database exactly as it was
    before_refusal = digest(db)
    refused = cli.json("memory", "restore-backup", expect=None)
    payload = refused.payload if isinstance(refused.payload, dict) else {}
    case.check(
        "a missing backup is refused with its own code",
        ((payload.get("error") or {}).get("code")) == "PATH_NOT_FOUND",
        f"rc={refused.returncode} {refused.stdout[-200:]!r}",
    )
    case.check(
        "a refused restore leaves the database untouched",
        digest(db) == before_refusal,
        "the database changed on a refused restore",
    )

    # ── 2. a known-good backup restores over corruption
    backup.write_bytes(db.read_bytes())
    backup_digest = digest(backup)
    db.write_bytes(b"not-a-database")
    corrupt_digest = digest(db)

    restored = cli.json("memory", "restore-backup")
    case.check("restore exits 0", restored.returncode == 0, restored.tail())
    case.check(
        "the backup is left untouched",
        digest(backup) == backup_digest,
        "the backup changed during the restore",
    )

    preserved = sorted(indexes.glob("paperforge.corrupt-*.db"))
    case.check(
        "the corrupt copy is preserved for inspection",
        bool(preserved) and digest(preserved[-1]) == corrupt_digest,
        str([path.name for path in preserved]),
    )
    case.check(
        "no staging temp is left behind",
        not list(indexes.glob("paperforge.restore-*.tmp")),
        str([path.name for path in indexes.glob("paperforge.restore-*.tmp")]),
    )

    # A new process must read the restored database (this CLI call is one).
    status = cli.json("memory", "status")
    status_data = status.data if isinstance(status.data, dict) else {}
    case.check("the restored database opens", status.returncode == 0, status.tail())
    case.check(
        "the memory layer reports fresh",
        status_data.get("fresh") is True,
        str(status_data.get("fresh")),
    )
    case.check(
        "the restored database still holds the paper",
        int(status_data.get("paper_count_db") or 0) >= 1,
        str(status_data.get("paper_count_db")),
    )

    case.artifact("indexes", indexes)
