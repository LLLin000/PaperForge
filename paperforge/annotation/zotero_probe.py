"""Zotero SQLite snapshot, read-only open, schema probe, and raw fetch helpers.

**Safety contract (SAFE-04, D-04):**
- All Zotero SQLite access goes through a temp-copy snapshot by default.
- The snapshot is opened in SQLite URI read-only mode (``mode=ro``).
- No function in this module writes to Zotero SQLite.
- The temp snapshot is removed when the context manager exits.

**Path contract (D-05, SAFE-01):**
- Functions accept explicit ``Path`` arguments.
- No hardcoded OS-specific Zotero folder paths.
"""

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from paperforge.annotation.errors import (
    ZoteroDatabaseError,
    ZoteroSchemaError,
)

# ---------------------------------------------------------------------------
# Required Zotero schema specification
# ---------------------------------------------------------------------------

REQUIRED_ZOTERO_TABLES: dict[str, set[str]] = {
    "items": {
        "itemID",
        "key",
        "dateModified",
    },
    "itemAttachments": {
        "itemID",
        "parentItemID",
    },
    "itemAnnotations": {
        "itemID",
        "parentItemID",
        "type",
        "text",
        "comment",
        "color",
        "pageLabel",
        "sortIndex",
        "position",
        "dateModified",
    },
    "tags": {
        "tagID",
        "name",
    },
    "itemTags": {
        "itemID",
        "tagID",
    },
}
"""Minimum required Zotero tables and their mandatory columns.

Additional tables and columns in the real Zotero schema are ignored during
probing — only the presence of these tables/columns is verified.
"""

# ---------------------------------------------------------------------------
# Snapshot helper
# ---------------------------------------------------------------------------


@contextmanager
def zotero_snapshot(db_path: Path) -> Iterator[Path]:
    """Context manager that copies *db_path* to a temporary file and yields
    the snapshot path.

    The temporary file is deleted when the context exits, even if an
    exception occurred inside the ``with`` block.

    Args:
        db_path: Path to the source Zotero SQLite database.

    Yields:
        Path to the temporary copy of the database.

    Raises:
        ZoteroDatabaseError: If *db_path* does not exist or is not a file.
    """
    if not db_path.exists():
        raise ZoteroDatabaseError(
            f"Zotero database not found: {db_path}",
            db_path=str(db_path),
        )
    if not db_path.is_file():
        raise ZoteroDatabaseError(
            f"Zotero database path is not a file: {db_path}",
            db_path=str(db_path),
        )

    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    snapshot_path = Path(tmp.name)
    try:
        shutil.copy2(str(db_path), str(snapshot_path))
        yield snapshot_path
    finally:
        if snapshot_path.exists():
            snapshot_path.unlink()


# ---------------------------------------------------------------------------
# Read-only opener
# ---------------------------------------------------------------------------


def open_zotero_readonly(snapshot_path: Path) -> sqlite3.Connection:
    """Open a Zotero SQLite snapshot in read-only mode.

    The connection uses:
    - SQLite URI ``mode=ro`` (prevents accidental writes at the engine level).
    - ``sqlite3.Row`` row factory for dict-like access.
    - Immutable cache mode for safety.

    Args:
        snapshot_path: Path to the (already copied) Zotero SQLite snapshot.

    Returns:
        A ``sqlite3.Connection`` configured for read-only access.

    Raises:
        ZoteroDatabaseError: If the file does not exist or is not a valid
            SQLite database.
    """
    if not snapshot_path.exists():
        raise ZoteroDatabaseError(
            f"Snapshot file not found: {snapshot_path}",
            db_path=str(snapshot_path),
        )

    uri = "file:" + snapshot_path.as_posix() + "?mode=ro&immutable=1"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        # Verify the database is readable with a fast pragma
        conn.execute("PRAGMA schema_version")
        return conn
    except sqlite3.DatabaseError as exc:
        raise ZoteroDatabaseError(
            f"Invalid or unreadable Zotero database: {exc}",
            db_path=str(snapshot_path),
            original_error=exc,
        ) from exc


# ---------------------------------------------------------------------------
# Schema probe
# ---------------------------------------------------------------------------


def probe_zotero_annotation_schema(
    conn: sqlite3.Connection,
) -> dict[str, list[str]]:
    """Validate that the connected Zotero database has all required tables
    and columns for annotation import.

    The probe checks every entry in ``REQUIRED_ZOTERO_TABLES``.  If a table
    is missing, ``ZoteroSchemaError`` is raised with the table name.  If a
    table exists but is missing a required column, ``ZoteroSchemaError`` is
    raised with both the table and column name.

    Args:
        conn: A read-only SQLite connection to the Zotero snapshot.

    Returns:
        A dict mapping each required table name to the **full** list of
        columns found in that table.  Extra columns beyond the minimum are
        included.

    Raises:
        ZoteroSchemaError: If a required table or column is absent.
    """
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    existing_tables: set[str] = {row["name"] for row in cursor.fetchall()}

    result: dict[str, list[str]] = {}

    for table_name, required_cols in REQUIRED_ZOTERO_TABLES.items():
        if table_name not in existing_tables:
            raise ZoteroSchemaError(
                f"Missing required Zotero table: '{table_name}'",
                table_name=table_name,
            )

        col_cursor = conn.execute(f"PRAGMA table_info({table_name})")
        actual_cols: set[str] = {row["name"] for row in col_cursor.fetchall()}
        missing = required_cols - actual_cols

        if missing:
            sorted_missing = sorted(missing)
            raise ZoteroSchemaError(
                f"Table '{table_name}' is missing required columns: "
                f"{sorted_missing}",
                table_name=table_name,
                column_name=sorted_missing[0],
            )

        result[table_name] = sorted(actual_cols)

    return result


# ---------------------------------------------------------------------------
# Raw annotation fetch
# ---------------------------------------------------------------------------


def fetch_zotero_item_annotations(
    conn: sqlite3.Connection,
    parent_item_id: int | None = None,
    attachment_item_id: int | None = None,
) -> list[sqlite3.Row]:
    """Fetch raw annotation rows from the Zotero ``itemAnnotations`` table.

    This is a narrow read helper that does **not** import rows into
    PaperForge.  It simply returns matched rows from the Zotero schema
    so calling code can inspect or normalize them.

    Args:
        conn: A read-only SQLite connection to the Zotero snapshot.
        parent_item_id: If given, filter to annotations whose
            ``parentItemID`` equals this value (e.g. a regular item).
        attachment_item_id: If given, filter to annotations whose
            ``itemID`` equals this value (e.g. a specific PDF attachment).

    Returns:
        A list of ``sqlite3.Row`` objects from ``itemAnnotations``, ordered
        by ``sortIndex``.
    """
    query = "SELECT * FROM itemAnnotations WHERE 1=1"
    params: list[Any] = []

    if parent_item_id is not None:
        query += " AND parentItemID = ?"
        params.append(parent_item_id)
    if attachment_item_id is not None:
        query += " AND itemID = ?"
        params.append(attachment_item_id)

    query += " ORDER BY sortIndex"
    return conn.execute(query, params).fetchall()
