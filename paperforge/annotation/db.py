"""Annotation DB path resolution and connection helpers.

Follows the same pattern as paperforge/memory/db.py but for the independent
annotations.db, which is NOT rebuilt during memory layer operations.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from paperforge.config import paperforge_paths


def get_annotations_db_path(vault: Path) -> Path:
    """Return the absolute path to annotations.db, co-located with paperforge.db."""
    paths = paperforge_paths(vault)
    index_path = paths.get("index")
    if index_path is None:
        msg = "paperforge_paths did not return an 'index' key; cannot determine annotations.db location"
        raise FileNotFoundError(msg)
    return index_path.parent / "annotations.db"


def get_annotations_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection to annotations.db with WAL mode.

    Args:
        db_path: Path to annotations.db.
        read_only: If True, open in read-only mode (for queries).

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row.
    """
    if read_only:
        uri = "file:" + db_path.as_posix() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not read_only:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    return conn
