"""Database path and connection helpers for annotations.db.

Pattern follows ``paperforge/memory/db.py`` exactly:
- ``get_annotations_db_path(vault)`` resolves through ``paperforge_paths(vault)``
- ``get_annotations_connection(db_path, read_only)`` mirrors ``get_connection``
  from the memory module: creates parent dirs for writes, uses ``sqlite3.Row``
  row factory, enables WAL and foreign keys for write connections, and
  supports read-only URI connections.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from paperforge.config import paperforge_paths


def get_annotations_db_path(vault: Path) -> Path:
    """Return the absolute path to annotations.db.

    The path is resolved through ``paperforge_paths(vault)["annotations_db"]``.
    """
    paths = paperforge_paths(vault)
    db_path = paths.get("annotations_db")
    if not db_path:
        raise FileNotFoundError("annotations_db path not configured")
    return db_path


def get_annotations_connection(
    db_path: Path, read_only: bool = False
) -> sqlite3.Connection:
    """Open a SQLite connection to annotations.db with WAL mode.

    Args:
        db_path: Path to annotations.db.
        read_only: If True, open in read-only mode (for queries).

    Returns:
        A ``sqlite3.Connection`` with ``row_factory`` set to ``sqlite3.Row``.

    Raises:
        sqlite3.OperationalError: If ``read_only=True`` and the database file
            does not exist.
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
