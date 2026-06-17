"""Tests for the annotation database schema lifecycle (TDD — RED first).

Tests verify:
- ``ensure_schema`` creates all expected tables.
- ``get_schema_version`` returns 0 / ANNOTATION_SCHEMA_VERSION.
- ``ensure_schema`` is idempotent and preserves existing rows.
- The ``annotations`` table exposes all required columns.
- FTS triggers correctly index ``selected_text`` / ``comment``.
"""

from __future__ import annotations

import sqlite3

import pytest

from paperforge.annotation.schema import (
    ANNOTATION_SCHEMA_VERSION,
    ANNOTATION_TABLES,
    ensure_schema,
    get_schema_version,
)


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------


def test_ensure_schema_creates_all_tables():
    """ensure_schema creates meta, annotations, sync_queue, and annotations_fts."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        for table in ANNOTATION_TABLES:
            assert table in tables, f"Missing table: {table}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------


def test_get_schema_version_zero_on_empty_db():
    """Before any meta table exists, get_schema_version returns 0."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        assert get_schema_version(conn) == 0
    finally:
        conn.close()


def test_get_schema_version_after_ensure_schema():
    """After ensure_schema, get_schema_version returns ANNOTATION_SCHEMA_VERSION."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        version = get_schema_version(conn)
        assert version == ANNOTATION_SCHEMA_VERSION, (
            f"Expected version {ANNOTATION_SCHEMA_VERSION}, got {version}"
        )
    finally:
        conn.close()


def test_get_schema_version_returns_zero_when_meta_table_missing_column():
    """If the meta table exists but schema_version key is missing, return 0."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.commit()
        # meta table exists but no schema_version row
        assert get_schema_version(conn) == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_ensure_schema_idempotent_preserves_rows():
    """Calling ensure_schema twice does not drop existing annotation rows."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)

        # Insert a row
        now = "2024-06-01T00:00:00"
        conn.execute(
            "INSERT INTO annotations (id, paper_id, type, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("ann_test1", "paper_001", "highlight", now, now),
        )
        conn.commit()

        # Call ensure_schema again
        ensure_schema(conn)

        # Row must still exist
        cursor = conn.execute(
            "SELECT COUNT(*) AS cnt FROM annotations WHERE id = 'ann_test1'"
        )
        assert cursor.fetchone()["cnt"] == 1
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Column completeness
# ---------------------------------------------------------------------------


def test_annotations_table_has_all_required_columns():
    """Check that every required column exists in the annotations table."""
    required_columns = {
        "id",
        "paper_id",
        "source",
        "source_library_id",
        "source_annotation_key",
        "source_attachment_key",
        "source_parent_key",
        "source_version",
        "source_modified_at",
        "type",
        "page_index",
        "page_label",
        "selected_text",
        "comment",
        "color",
        "sort_index",
        "tags_json",
        "position_json",
        "selector_json",
        "sync_state",
        "is_readonly",
        "created_at",
        "updated_at",
        "deleted_at",
    }

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        cursor = conn.execute("PRAGMA table_info(annotations)")
        actual = {row["name"] for row in cursor.fetchall()}
        missing = required_columns - actual
        assert not missing, f"Missing columns in annotations table: {missing}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# FTS triggers
# ---------------------------------------------------------------------------


def test_fts_trigger_indexes_selected_text_on_insert():
    """Inserting an annotation should populate annotations_fts for selected_text."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        now = "2024-06-01T00:00:00"
        conn.execute(
            "INSERT INTO annotations (id, paper_id, type, selected_text, comment, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("ann_fts1", "p1", "highlight", "bone mineral density improved", "key result", now, now),
        )
        conn.commit()

        cursor = conn.execute(
            "SELECT rowid FROM annotations_fts WHERE annotations_fts MATCH ?",
            ("mineral",),
        )
        rows = cursor.fetchall()
        assert len(rows) > 0, "FTS should find 'mineral' in selected_text"
    finally:
        conn.close()


def test_fts_trigger_indexes_comment_on_insert():
    """Inserting an annotation should populate annotations_fts for comment."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        now = "2024-06-01T00:00:00"
        conn.execute(
            "INSERT INTO annotations (id, paper_id, type, selected_text, comment, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("ann_fts2", "p1", "note", "some text", "important finding", now, now),
        )
        conn.commit()

        cursor = conn.execute(
            "SELECT rowid FROM annotations_fts WHERE annotations_fts MATCH ?",
            ("finding",),
        )
        rows = cursor.fetchall()
        assert len(rows) > 0, "FTS should find 'finding' in comment"
    finally:
        conn.close()


def test_fts_syncs_on_update():
    """Updating selected_text should be reflected in FTS."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        now = "2024-06-01T00:00:00"
        conn.execute(
            "INSERT INTO annotations (id, paper_id, type, selected_text, comment, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("ann_fts3", "p1", "highlight", "old result", "comment", now, now),
        )
        conn.commit()

        # Update
        later = "2024-06-02T00:00:00"
        conn.execute(
            "UPDATE annotations SET selected_text = ?, updated_at = ? WHERE id = ?",
            ("new significant finding", later, "ann_fts3"),
        )
        conn.commit()

        # Old text should no longer be in FTS (or at least new text is findable)
        cursor = conn.execute(
            "SELECT rowid FROM annotations_fts WHERE annotations_fts MATCH ?",
            ("significant",),
        )
        rows = cursor.fetchall()
        assert len(rows) > 0, "FTS should find 'significant' after update"
    finally:
        conn.close()


def test_fts_removes_on_delete():
    """Deleting an annotation should remove it from FTS."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        now = "2024-06-01T00:00:00"
        conn.execute(
            "INSERT INTO annotations (id, paper_id, type, selected_text, comment, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("ann_fts4", "p1", "highlight", "temporary text", "temp comment", now, now),
        )
        conn.commit()

        # Confirm it's in FTS
        cursor = conn.execute(
            "SELECT rowid FROM annotations_fts WHERE annotations_fts MATCH ?",
            ("temporary",),
        )
        assert len(cursor.fetchall()) > 0, "Precondition: text should be in FTS"

        # Delete
        conn.execute("DELETE FROM annotations WHERE id = 'ann_fts4'")
        conn.commit()

        # Should no longer be findable
        cursor = conn.execute(
            "SELECT rowid FROM annotations_fts WHERE annotations_fts MATCH ?",
            ("temporary",),
        )
        assert len(cursor.fetchall()) == 0, "FTS should not find deleted text"
    finally:
        conn.close()
