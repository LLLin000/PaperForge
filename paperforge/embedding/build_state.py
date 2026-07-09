from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from paperforge.config import paperforge_paths
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema


def _default_state() -> dict:
    return {
        "status": "idle",
        "current": 0,
        "total": 0,
        "paper_id": "",
        "last_update": "",
        "started_at": "",
        "finished_at": "",
        "resume_supported": True,
        "mode": "api",
        "model": "text-embedding-3-small",
        "message": "",
        "pid": 0,
    }


def _fallback_state() -> dict:
    return {"status": "idle", "current": 0, "total": 0, "paper_id": ""}


def get_vector_build_state_path(vault: Path) -> Path:
    """DEPRECATED: Build state is now stored in the build_state table in paperforge.db.

    This function is kept for backward compatibility only.
    """
    paths = paperforge_paths(vault)
    index_dir = (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent
    return index_dir / "vector-build-state.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_state_conn(vault: Path) -> sqlite3.Connection:
    """Open a read-write SQLite connection to paperforge.db and ensure schema."""
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=False)
    ensure_schema(conn)
    return conn


def _dict_to_build_state(conn: sqlite3.Connection, state: dict) -> None:
    """Upsert every key-value pair from *state* into the build_state table.

    Non-string values are JSON-serialised so the schema's TEXT column can
    store them.  Strings are stored verbatim.
    """
    for key, value in state.items():
        if not isinstance(value, str):
            value = json.dumps(value)
        conn.execute(
            "INSERT OR REPLACE INTO build_state(key, value, updated_at) "
            "VALUES (?, ?, datetime('now'))",
            (key, value),
        )
    conn.commit()


def _build_state_to_dict(conn: sqlite3.Connection) -> dict | None:
    """Read all rows from the build_state table into a plain dict.

    JSON-deserialisable values are parsed back to their Python types.
    Returns ``None`` when the table is empty.
    """
    rows = conn.execute("SELECT key, value FROM build_state").fetchall()
    if not rows:
        return None
    state = {}
    for key, value in rows:
        try:
            state[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            state[key] = value
    return state


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_vector_build_state(vault: Path) -> dict:
    """Read the current vector build state from the build_state table.

    Returns :func:`_default_state` when the database file or table does not
    exist yet.  Merges persisted values on top of the defaults so that any
    missing keys are still present in the returned dict.
    """
    try:
        db_path = get_memory_db_path(vault)
        if not db_path.exists():
            return _default_state()
        conn = get_connection(db_path, read_only=True)
    except (FileNotFoundError, sqlite3.OperationalError):
        return _default_state()

    try:
        rows = conn.execute("SELECT key, value FROM build_state").fetchall()
    except sqlite3.OperationalError:
        return _default_state()
    finally:
        conn.close()

    if not rows:
        return _default_state()

    state: dict = {}
    for key, value in rows:
        try:
            state[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            state[key] = value

    defaults = _default_state()
    defaults.update(state)
    return defaults


def write_vector_build_state(vault: Path, state: dict) -> None:
    """Persist *state* to the build_state table.

    Every key-value pair in *state* is upserted.  Existing keys not present
    in *state* are **not** removed.
    """
    conn = _build_state_conn(vault)
    try:
        _dict_to_build_state(conn, state)
    finally:
        conn.close()


def mark_vector_build_state(vault: Path, **fields) -> dict:
    """Read the current state, apply **fields*, write it back, and return the
    merged dict.

    This is the convenience equivalent of::

        state = read_vector_build_state(vault)
        state.update(fields)
        write_vector_build_state(vault, state)
        return state
    """
    state = read_vector_build_state(vault)
    state.update(fields)
    write_vector_build_state(vault, state)
    return state
