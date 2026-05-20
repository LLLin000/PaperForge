"""Tests for annotation DB path, connection helpers, and schema lifecycle."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


def test_db_path_resolves_under_indexes(tmp_path: Path) -> None:
    """annotations.db should co-locate with paperforge.db under System/PaperForge/indexes/."""
    from paperforge.annotation.db import get_annotations_db_path

    db_path = get_annotations_db_path(tmp_path)
    rel = db_path.relative_to(tmp_path).as_posix()
    assert "System" in rel or "PaperForge" in rel or "indexes" in rel
    assert db_path.name == "annotations.db"


def test_readwrite_connection_has_wal(tmp_path: Path) -> None:
    """Read/write connection should enable WAL journal mode."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection

    db_path = get_annotations_db_path(tmp_path)
    conn = get_annotations_connection(db_path, read_only=False)
    try:
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal == "wal"
    finally:
        conn.close()


def test_readonly_connection_works(tmp_path: Path) -> None:
    """A read-only connection should be openable with URI mode=ro."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection

    db_path = get_annotations_db_path(tmp_path)
    # First create the DB via a regular connection
    get_annotations_connection(db_path, read_only=False).close()

    ro_conn = get_annotations_connection(db_path, read_only=True)
    try:
        row = ro_conn.execute("SELECT 1 AS ok").fetchone()
        assert row["ok"] == 1
    finally:
        ro_conn.close()


# ── Schema lifecycle tests ──


def test_ensure_schema_creates_tables(tmp_path: Path) -> None:
    """ensure_schema() should create meta, annotations, annotations_fts, sync_queue."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection
    from paperforge.annotation.schema import ensure_schema

    db_path = get_annotations_db_path(tmp_path)
    conn = get_annotations_connection(db_path, read_only=False)
    try:
        ensure_schema(conn)

        # Verify tables exist
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "meta" in tables, f"meta table missing; tables={tables}"
        assert "annotations" in tables, f"annotations table missing; tables={tables}"
        assert "sync_queue" in tables, f"sync_queue table missing; tables={tables}"

        # Verify FTS table exists (type varies by SQLite version)
        fts_row = conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'annotations_fts'"
        ).fetchone()
        assert fts_row is not None, "annotations_fts not found in sqlite_master"
    finally:
        conn.close()


def test_schema_version_stored_as_1(tmp_path: Path) -> None:
    """Schema version in meta table should be 1 after ensure_schema()."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection
    from paperforge.annotation.schema import ensure_schema, get_schema_version

    db_path = get_annotations_db_path(tmp_path)
    conn = get_annotations_connection(db_path, read_only=False)
    try:
        ensure_schema(conn)
        version = get_schema_version(conn)
        assert version == 1
    finally:
        conn.close()


def test_ensure_schema_is_idempotent(tmp_path: Path) -> None:
    """Calling ensure_schema() twice should not raise or drop data."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection
    from paperforge.annotation.schema import ensure_schema, get_schema_version

    db_path = get_annotations_db_path(tmp_path)
    conn = get_annotations_connection(db_path, read_only=False)
    try:
        ensure_schema(conn)  # first call
        v1 = get_schema_version(conn)
        ensure_schema(conn)  # second call
        v2 = get_schema_version(conn)
        assert v1 == v2 == 1
    finally:
        conn.close()
