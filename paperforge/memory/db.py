from __future__ import annotations

import sqlite3
from pathlib import Path

from paperforge.config import paperforge_paths


def get_memory_db_path(vault: Path) -> Path:
    """Return the absolute path to paperforge.db."""
    paths = paperforge_paths(vault)
    index_path = paths.get("index")
    if not index_path:
        raise FileNotFoundError("index path not configured")
    return index_path.parent / "paperforge.db"


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


def ensure_vec_extension(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension if available.

    Enables vec0 virtual table support for vector similarity search.
    Gracefully no-ops when the extension is not installed.

    Supports Python 3.12/3.13 (conn.load) and 3.14+ (conn.load_extension).
    """
    try:
        conn.enable_load_extension(True)

        # Python 3.12/3.13 API — searches system library path
        try:
            conn.load("vec0")
            return
        except AttributeError:
            pass  # conn.load removed in Python 3.14

        # Python 3.14+ — use sqlite_vec convenience wrapper or direct path
        try:
            from sqlite_vec import loadable_path

            conn.load_extension(str(loadable_path()))
        except ImportError:
            conn.load_extension("vec0")
    except (sqlite3.OperationalError, AttributeError):
        pass  # extension not available
    finally:
        try:
            conn.enable_load_extension(False)
        except AttributeError:
            pass
