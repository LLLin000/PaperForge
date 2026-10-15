"""E05 — a legacy ChromaDB substrate migrates into sqlite-vec; no store is a no-op.

Ported from the H case.  Its oracle is the migrated row count *and* the database
itself: the case opens ``paperforge.db`` with the stdlib and requires the vec0
shadow tables to hold rows, so the migration cannot pass by reporting success.

This case needs the optional ``legacy-vector`` runtime (chromadb).  Job P installs
``.[test,vector,legacy-vector]`` - the same extras the full-suite job uses - so the
assertion is deterministic instead of branching on an absent dependency, which would
be a skip in disguise (R2).
"""

from __future__ import annotations

import json
import shutil
import sqlite3

import pytest

from .evidence import REPO_ROOT

pytestmark = pytest.mark.harness

CASE_ID = "E05"
TITLE = "A legacy ChromaDB substrate migrates into sqlite-vec"
HOST_SPEC_CASE = "migrates a legacy ChromaDB substrate into sqlite-vec"

FIXTURE = REPO_ROOT / "tests" / "sandbox" / "legacy-chroma"


def _vec_row_count(db: str) -> int:
    """Rows across every vec0 shadow table (stdlib sqlite3; no extension needed)."""
    con = sqlite3.connect(db)
    try:
        tables = [
            str(row[0])
            for row in con.execute(
                "select name from sqlite_master where type='table' and name like 'vec%_rowids'"
            )
        ]
        total = 0
        for table in tables:
            total += int(con.execute(f"select count(*) from '{table}'").fetchone()[0])
        return total
    finally:
        con.close()


def test_legacy_chroma_migrates(cli, vault, case) -> None:
    vectors = vault / "System" / "PaperForge" / "indexes" / "vectors"
    db = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"

    case.check("the legacy fixture exists", FIXTURE.is_dir(), str(FIXTURE))
    if not FIXTURE.is_dir():
        return

    empty = cli.json("embed", "migrate")
    case.check("migrate without a store exits 0", empty.returncode == 0, empty.tail())
    case.check(
        "no legacy store is a no-op",
        int((empty.data or {}).get("migrated") or 0) == 0,
        json.dumps(empty.data or {})[:200],
    )

    shutil.copytree(FIXTURE, vectors, dirs_exist_ok=True)
    migrated = cli.json("embed", "migrate")
    case.check("migrate exits 0", migrated.returncode == 0, migrated.tail())
    cases = int((migrated.data or {}).get("migrated") or 0)
    case.check("the legacy substrate was migrated", cases >= 1, json.dumps(migrated.data or {})[:200])

    case.check(
        "the legacy store is left in place",
        (vectors / "chroma.sqlite3").is_file(),
        "the legacy store disappeared during migration",
    )

    rows = _vec_row_count(str(db)) if db.is_file() else 0
    case.check(
        "the migrated vectors are readable in the vec0 store",
        rows >= 1,
        f"vec*_rowids rows = {rows} (reported migrated={cases})",
    )

    case.artifact("indexes", vault / "System" / "PaperForge" / "indexes")
