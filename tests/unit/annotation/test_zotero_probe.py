"""Tests for Zotero SQLite snapshot/probe helpers (TDD — RED first).

Tests verify:
- Temp-copy snapshot + read-only open works
- Live DB unchanged after probe
- Snapshot cleanup on context exit
- Missing DB path -> ZoteroDatabaseError
- Missing annotation table or column -> ZoteroSchemaError with detail
- Probe discovers expected tables/columns
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from paperforge.annotation.errors import (
    AnnotationImportError,
    ZoteroDatabaseError,
    ZoteroSchemaError,
)
from paperforge.annotation.zotero_probe import (
    REQUIRED_ZOTERO_TABLES,
    fetch_zotero_item_annotations,
    open_zotero_readonly,
    probe_zotero_annotation_schema,
    zotero_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_zotero_fixture(db_path: Path) -> None:
    """Create a minimal valid Zotero-style SQLite database at ``db_path``.

    Tables match the Zotero 6/7 internal schema relevant to annotations:
    items, itemAttachments, itemAnnotations, tags, itemTags.
    Each table receives sample rows for verification.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""
            CREATE TABLE items (
                itemID INTEGER PRIMARY KEY,
                itemTypeID INTEGER NOT NULL DEFAULT 1,
                libraryID INTEGER NOT NULL DEFAULT 1,
                key TEXT NOT NULL,
                dateModified TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE itemAttachments (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                path TEXT,
                contentType TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE itemAnnotations (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                type TEXT,
                text TEXT,
                comment TEXT,
                color TEXT,
                pageLabel TEXT,
                sortIndex INTEGER,
                position TEXT,
                dateModified TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE tags (
                tagID INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE itemTags (
                itemID INTEGER NOT NULL,
                tagID INTEGER NOT NULL
            )
        """)

        # Sample data
        conn.execute(
            "INSERT INTO items (itemID, itemTypeID, libraryID, key, dateModified) "
            "VALUES (1, 1, 1, 'ABC123', '2024-06-01 12:00:00')"
        )
        conn.execute(
            "INSERT INTO itemAttachments (itemID, parentItemID, path, contentType) "
            "VALUES (2, 1, 'storage:ABC123/file.pdf', 'application/pdf')"
        )
        conn.execute(
            "INSERT INTO itemAnnotations "
            "(itemID, parentItemID, type, text, comment, color, pageLabel, "
            " sortIndex, position, dateModified) "
            "VALUES (3, 2, 'highlight', 'significant result', 'my comment', "
            "        '#ff0000', '1', 0, '{}', '2024-06-01 12:00:00')"
        )
        conn.execute(
            "INSERT INTO tags (tagID, name) VALUES (1, 'important')"
        )
        conn.execute(
            "INSERT INTO itemTags (itemID, tagID) VALUES (3, 1)"
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def zotero_fixture_path() -> Path:
    """Yield a path to a minimal valid Zotero-style SQLite database.

    The temp file is created with the full schema + sample rows and
    automatically cleaned up after the test.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    _create_zotero_fixture(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


# ---------------------------------------------------------------------------
# 1. Temp-copy + read-only open
# ---------------------------------------------------------------------------


def test_zotero_snapshot_copies_and_opens_readonly(zotero_fixture_path: Path):
    """zotero_snapshot copies the DB to a temp path; open_zotero_readonly can
    query the copy."""
    with zotero_snapshot(zotero_fixture_path) as snap:
        conn = open_zotero_readonly(snap)
        row = conn.execute(
            "SELECT key FROM items WHERE itemID = 1"
        ).fetchone()
        assert row is not None
        assert row["key"] == "ABC123"
        conn.close()


# ---------------------------------------------------------------------------
# 2. Live DB unchanged after probe
# ---------------------------------------------------------------------------


def test_live_db_unchanged_after_probe(zotero_fixture_path: Path):
    """The original Zotero DB file must remain unmodified after
    snapshot + probe operations."""
    original_size = zotero_fixture_path.stat().st_size
    with zotero_snapshot(zotero_fixture_path) as snap:
        conn = open_zotero_readonly(snap)
        probe_zotero_annotation_schema(conn)
        conn.close()
    assert zotero_fixture_path.stat().st_size == original_size, (
        "Original Zotero DB size changed after probe"
    )


# ---------------------------------------------------------------------------
# 3. Snapshot cleanup after context exit
# ---------------------------------------------------------------------------


def test_snapshot_cleaned_up_after_context(zotero_fixture_path: Path):
    """The temp snapshot file must be removed after the context manager
    exits, even on success."""
    captured: list[Path] = []
    with zotero_snapshot(zotero_fixture_path) as snap:
        captured.append(snap)
        assert snap.exists(), "Snapshot should exist inside the context"
    assert not captured[0].exists(), (
        "Snapshot file must not exist after context exit"
    )


# ---------------------------------------------------------------------------
# 4. Missing DB path -> ZoteroDatabaseError
# ---------------------------------------------------------------------------


def test_missing_db_raises_zotero_database_error():
    """A non-existent Zotero DB path must raise ZoteroDatabaseError
    from the snapshot helper."""
    with pytest.raises(ZoteroDatabaseError):
        with zotero_snapshot(Path("/nonexistent/zotero.sqlite")):
            pass


# ---------------------------------------------------------------------------
# 5. Unknown/missing schema -> ZoteroSchemaError
# ---------------------------------------------------------------------------


def test_missing_table_raises_zotero_schema_error():
    """When a required Zotero table is absent, probe must raise
    ZoteroSchemaError with the table name in the message."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE items ("
            "  itemID INTEGER PRIMARY KEY, "
            "  key TEXT, "
            "  dateModified TEXT"
            ")"
        )
        conn.commit()
        conn.close()

        with zotero_snapshot(db_path) as snap:
            conn2 = open_zotero_readonly(snap)
            with pytest.raises(ZoteroSchemaError) as excinfo:
                probe_zotero_annotation_schema(conn2)
            conn2.close()

        err_msg = str(excinfo.value)
        assert "itemAnnotations" in err_msg or "table" in err_msg.lower()
    finally:
        if db_path.exists():
            db_path.unlink()


def test_missing_column_raises_zotero_schema_error():
    """When a required column is missing from a Zotero table, probe must
    raise ZoteroSchemaError with the column name in the message."""
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE items ("
            "  itemID INTEGER PRIMARY KEY, "
            "  key TEXT, "
            "  dateModified TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE itemAttachments ("
            "  itemID INTEGER PRIMARY KEY,"
            "  parentItemID INTEGER"
            ")"
        )
        # itemAnnotations MISSING 'comment' and other required columns
        conn.execute(
            "CREATE TABLE itemAnnotations ("
            "  itemID INTEGER PRIMARY KEY,"
            "  parentItemID INTEGER,"
            "  type TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT)"
        )
        conn.execute(
            "CREATE TABLE itemTags (itemID INTEGER, tagID INTEGER)"
        )
        conn.commit()
        conn.close()

        with zotero_snapshot(db_path) as snap:
            conn2 = open_zotero_readonly(snap)
            with pytest.raises(ZoteroSchemaError) as excinfo:
                probe_zotero_annotation_schema(conn2)
            conn2.close()

        err_msg = str(excinfo.value)
        assert "comment" in err_msg or "text" in err_msg or "missing" in err_msg.lower()
    finally:
        if db_path.exists():
            db_path.unlink()


# ---------------------------------------------------------------------------
# 6. Probe discovers expected tables/columns
# ---------------------------------------------------------------------------


def test_probe_discovers_expected_tables(zotero_fixture_path: Path):
    """probe_zotero_annotation_schema returns all required tables with
    their required columns present."""
    with zotero_snapshot(zotero_fixture_path) as snap:
        conn = open_zotero_readonly(snap)
        schema = probe_zotero_annotation_schema(conn)
        conn.close()

    for table_name, required_cols in REQUIRED_ZOTERO_TABLES.items():
        assert table_name in schema, (
            f"Expected table '{table_name}' missing from probe result"
        )
        for col in required_cols:
            assert col in schema[table_name], (
                f"Expected column '{col}' in table '{table_name}' "
                f"but probe returned only: {schema[table_name]}"
            )


# ---------------------------------------------------------------------------
# 7. Error hierarchy inheritance
# ---------------------------------------------------------------------------


def test_error_hierarchy():
    """ZoteroDatabaseError and ZoteroSchemaError must subclass
    AnnotationImportError."""
    assert issubclass(ZoteroDatabaseError, AnnotationImportError)
    assert issubclass(ZoteroSchemaError, AnnotationImportError)


# ---------------------------------------------------------------------------
# 8. fetch_zotero_item_annotations helper
# ---------------------------------------------------------------------------


def test_fetch_zotero_item_annotations_returns_rows(zotero_fixture_path: Path):
    """fetch_zotero_item_annotations returns annotation rows from the
    Zotero snapshot."""
    with zotero_snapshot(zotero_fixture_path) as snap:
        conn = open_zotero_readonly(snap)
        rows = fetch_zotero_item_annotations(conn)
        conn.close()
    assert len(rows) >= 1, "Expected at least one annotation row"
    assert rows[0]["type"] == "highlight"


def test_fetch_zotero_item_annotations_filters_by_parent(zotero_fixture_path: Path):
    """fetch_zotero_item_annotations accepts a parent_item_id filter."""
    with zotero_snapshot(zotero_fixture_path) as snap:
        conn = open_zotero_readonly(snap)
        rows = fetch_zotero_item_annotations(conn, parent_item_id=2)
        conn.close()
    assert len(rows) >= 1
    for row in rows:
        assert row["parentItemID"] == 2
