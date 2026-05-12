from __future__ import annotations

import tempfile
from pathlib import Path

from paperforge.memory.schema import (
    ALL_TABLES,
    ensure_schema,
    drop_all_tables,
    get_schema_version,
    CURRENT_SCHEMA_VERSION,
)
from paperforge.memory.db import get_connection


def test_ensure_schema_creates_all_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        for table in ALL_TABLES:
            assert table in tables, f"Missing table: {table}"
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_drop_all_tables_clears_all():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    conn = None
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        drop_all_tables(conn)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        app_tables = {t for t in tables if t in ALL_TABLES}
        assert app_tables == set()
    finally:
        if conn:
            conn.close()
        db_path.unlink(missing_ok=True)


def test_get_schema_version_returns_zero_when_no_meta():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        assert get_schema_version(conn) == 0
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_get_schema_version_returns_stored_value():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '1')"
        )
        conn.commit()
        assert get_schema_version(conn) == 1
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_schema_version_mismatch_triggers_rebuild_semantics():
    """When stored version != CURRENT, get_schema_version returns a different int."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '99')"
        )
        conn.commit()
        stored = get_schema_version(conn)
        assert stored != CURRENT_SCHEMA_VERSION
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)
