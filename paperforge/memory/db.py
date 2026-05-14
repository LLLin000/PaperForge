from __future__ import annotations

import sqlite3
from pathlib import Path

from paperforge.config import paperforge_paths


def get_memory_db_path(vault: Path) -> Path:
    """Return the absolute path to paperforge.db."""
    paths = paperforge_paths(vault)
    db_path = paths.get("memory_db")
    if not db_path:
        raise FileNotFoundError("memory_db path not configured")
    return db_path


def get_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection to paperforge.db with WAL mode.

    Args:
        db_path: Path to paperforge.db.
        read_only: If True, open in read-only mode (for queries).
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
