"""Tests for annotation database path and connection helpers.

These tests mirror the pattern established in tests/unit/memory/test_schema.py
and the connection helpers defined in paperforge/memory/db.py.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


def test_get_annotations_db_path_returns_annotations_db_name():
    """get_annotations_db_path(vault) returns an absolute path named annotations.db."""
    from paperforge.annotation.db import get_annotations_db_path

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp).resolve()
        db_path = get_annotations_db_path(vault)
        assert db_path.is_absolute(), f"Expected absolute path, got {db_path}"
        assert db_path.name == "annotations.db", (
            f"Expected 'annotations.db', got '{db_path.name}'"
        )


def test_get_annotations_db_path_same_parent_as_memory_db():
    """annotations_db path shares the same parent directory as memory_db."""
    from paperforge.annotation.db import get_annotations_db_path
    from paperforge.config import paperforge_paths

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp).resolve()
        ann_path = get_annotations_db_path(vault)
        paths = paperforge_paths(vault)
        mem_path = paths["memory_db"]
        assert ann_path.parent == mem_path.parent, (
            f"annotations_db parent ({ann_path.parent}) does not match "
            f"memory_db parent ({mem_path.parent})"
        )


def test_write_connection_creates_parent_dir_and_enables_wal():
    """A write connection creates the parent directory and enables WAL journal mode."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp).resolve()
        db_path = get_annotations_db_path(vault)
        # Parent should not exist yet
        assert not db_path.parent.exists(), (
            "Precondition: parent dir should not exist before connection"
        )

        conn = get_annotations_connection(db_path)
        try:
            # Parent directory should now exist
            assert db_path.parent.exists(), (
                "Write connection should create parent directory"
            )
            # File should exist after connection
            assert db_path.exists(), (
                "Database file should exist after write connection"
            )
            # WAL mode should be enabled
            cursor = conn.execute("PRAGMA journal_mode;")
            row = cursor.fetchone()
            # After enabling WAL, the reported mode may be 'wal' or 'memory'
            # depending on the file system, but we just check it's not 'delete'
            assert row is not None
            mode = row[0].lower()
            assert mode == "wal", (
                f"Expected WAL journal mode, got '{mode}'"
            )
            # Foreign keys should be ON
            cursor = conn.execute("PRAGMA foreign_keys;")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 1, (
                f"Expected foreign_keys=ON, got {row[0]}"
            )
        finally:
            conn.close()


def test_read_only_connection_works_after_db_exists():
    """A read-only connection returns sqlite3.Row rows after the DB exists."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp).resolve()
        db_path = get_annotations_db_path(vault)

        # Create the DB with a write connection first
        write_conn = get_annotations_connection(db_path)
        write_conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)")
        write_conn.execute("INSERT INTO test (val) VALUES ('hello')")
        write_conn.commit()
        write_conn.close()

        # Now open read-only
        ro_conn = get_annotations_connection(db_path, read_only=True)
        try:
            cursor = ro_conn.execute("SELECT val FROM test WHERE id = 1")
            row = cursor.fetchone()
            # Verify sqlite3.Row interface
            assert row is not None
            assert row["val"] == "hello", (
                f"Expected 'hello', got {row['val']}"
            )
            assert isinstance(row, sqlite3.Row), (
                "Read-only connection should return sqlite3.Row rows"
            )
        finally:
            ro_conn.close()


def test_read_only_connection_raises_on_missing_db():
    """A read-only connection to a non-existent DB raises sqlite3.OperationalError."""
    from paperforge.annotation.db import get_annotations_connection

    with tempfile.TemporaryDirectory() as tmp:
        missing_path = Path(tmp) / "nonexistent" / "annotations.db"
        assert not missing_path.exists(), (
            "Precondition: database should not exist"
        )

        with pytest.raises(sqlite3.OperationalError):
            get_annotations_connection(missing_path, read_only=True)
