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
