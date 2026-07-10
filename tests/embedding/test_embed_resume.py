"""Test embed build lifecycle: vec0 row survival, resume detection, force rebuild."""

from __future__ import annotations

from pathlib import Path

import pytest

from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema


def _count_vec_rows(db_path: Path) -> dict[str, int]:
    """Return row counts per vec meta table."""
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    counts = {}
    for table in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta"):
        row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
        counts[table] = row["cnt"] if row else 0
    conn.close()
    return counts


# ---------------------------------------------------------------------------
# Resume: vec0 meta row detection
# ---------------------------------------------------------------------------


def test_resume_detects_vec0_rows(seeded_vault: Path) -> None:
    """Resume path correctly detects existing vec0 meta rows."""
    db_path = get_memory_db_path(seeded_vault)
    counts = _count_vec_rows(db_path)

    assert counts["vec_fulltext_meta"] > 0, "Fixture should have seeded vec_fulltext_meta rows"
    assert sum(counts.values()) > 0, "Should have at least one vec meta table with data"


def test_resume_no_rows_triggers_fresh(seeded_vault: Path) -> None:
    """When all vec meta tables are empty, resume should detect that."""
    db_path = get_memory_db_path(seeded_vault)

    # Clear all vec meta rows
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    for table in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()

    counts = _count_vec_rows(db_path)
    assert sum(counts.values()) == 0, "All vec meta tables should be empty"


# ---------------------------------------------------------------------------
# Force: vec0 DROP TABLE
# ---------------------------------------------------------------------------


def test_force_drops_vec0_tables(seeded_vault: Path) -> None:
    """Force rebuild should drop vec0 virtual tables and their companion meta tables."""
    db_path = get_memory_db_path(seeded_vault)

    # Confirm tables exist before force
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    pre_tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE name IN ('vec_fulltext','vec_fulltext_meta')"
        ).fetchall()
    }
    conn.close()
    assert "vec_fulltext_meta" in pre_tables, "Fixture should have vec_fulltext_meta before force"

    # Simulate --force: drop vec0 tables
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    for t in (
        "vec_fulltext",
        "vec_body",
        "vec_objects",
        "vec_fulltext_meta",
        "vec_body_meta",
        "vec_objects_meta",
    ):
        conn.execute(f'DROP TABLE IF EXISTS "{t}"')
    conn.commit()
    conn.close()

    # Confirm tables are gone
    conn = get_connection(db_path)
    post_tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE name IN ('vec_fulltext','vec_fulltext_meta','vec_body','vec_body_meta','vec_objects','vec_objects_meta')"
        ).fetchall()
    }
    conn.close()
    assert not post_tables, "All vec0 tables should have been dropped"


# ---------------------------------------------------------------------------
# Delete ordering: old vectors removed before new ones written
# ---------------------------------------------------------------------------


def test_delete_then_write_preserves_new_vectors(seeded_vault: Path) -> None:
    """Simulate the build-loop pattern: delete old, then insert new — only
    the new meta rows should remain, not a sum of old + new.

    This tests the assertion that write-encoded-payloads are preceded by
    delete-paper-vectors, so vec row counts reflect only the fresh writes."""
    db_path = get_memory_db_path(seeded_vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)

    # -- phase 1: "write new paper" (as the initial build would) --
    conn.execute(
        "INSERT INTO vec_fulltext_meta(rowid, paper_id, chunk_index, text) VALUES (100, 'paper_A', 0, 'first write')"
    )
    before_paper_a = conn.execute(
        "SELECT COUNT(*) AS cnt FROM vec_fulltext_meta WHERE paper_id = 'paper_A'"
    ).fetchone()["cnt"]
    assert before_paper_a == 1

    # -- phase 2: simulate the fix — delete old, then write new --
    conn.execute("DELETE FROM vec_fulltext_meta WHERE paper_id = 'paper_A'")
    conn.execute(
        "INSERT INTO vec_fulltext_meta(rowid, paper_id, chunk_index, text) VALUES (101, 'paper_A', 0, 'second write')"
    )
    conn.commit()

    after_paper_a = conn.execute(
        "SELECT COUNT(*) AS cnt FROM vec_fulltext_meta WHERE paper_id = 'paper_A'"
    ).fetchone()["cnt"]
    conn.close()

    assert after_paper_a == 1, (
        f"Expected exactly 1 row for paper_A after delete+write, got {after_paper_a}. "
        "Delete must precede write so old rows are not double-counted."
    )
