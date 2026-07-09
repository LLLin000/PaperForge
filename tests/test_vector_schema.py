from __future__ import annotations

import sqlite3

from paperforge.memory.schema import (
    ALL_TABLES,
    CURRENT_SCHEMA_VERSION,
    ensure_schema,
    get_schema_version,
)


def _vec_available(conn: sqlite3.Connection) -> bool:
    """Return True if sqlite-vec extension can be loaded."""
    try:
        conn.enable_load_extension(True)
        conn.load("vec0")
        conn.enable_load_extension(False)
        return True
    except (sqlite3.OperationalError, AttributeError):
        return False


def test_ensure_schema_creates_vec_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in cursor.fetchall()}

    # Companion tables + build_state always created (plain tables)
    assert "vec_fulltext_meta" in tables
    assert "vec_body_meta" in tables
    assert "vec_objects_meta" in tables
    assert "build_state" in tables

    # Vec0 virtual tables only created when extension is available
    if _vec_available(conn):
        assert "vec_fulltext" in tables
        assert "vec_body" in tables
        assert "vec_objects" in tables
    else:
        assert "vec_fulltext" not in tables
        assert "vec_body" not in tables
        assert "vec_objects" not in tables
    conn.close()


def test_vec_tables_are_virtual():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    if not _vec_available(conn):
        conn.close()
        return  # Skip virtual-table check when extension not loaded

    cursor = conn.execute(
        "SELECT name, type FROM sqlite_master WHERE type='virtual' ORDER BY name"
    )
    virtual_tables = {row["name"] for row in cursor.fetchall()}
    assert "vec_fulltext" in virtual_tables
    assert "vec_body" in virtual_tables
    assert "vec_objects" in virtual_tables
    conn.close()


def test_build_state_table_exists():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='build_state'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_schema_creation_is_idempotent():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    ensure_schema(conn)  # second call must not raise
    conn.close()


def test_schema_version_is_6():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    assert get_schema_version(conn) == 6
    assert CURRENT_SCHEMA_VERSION == 6
    conn.close()
