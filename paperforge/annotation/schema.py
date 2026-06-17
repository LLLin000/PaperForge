"""Annotation database schema and lifecycle management.

This module defines the independent annotation database schema, completely
separate from the memory layer (``paperforge.memory.schema``).  The schema
version is tracked in its own ``meta`` table and is intentionally independent
of ``CURRENT_SCHEMA_VERSION``.

Schema version 1 provides:
- ``meta`` — key-value store for schema version metadata.
- ``annotations`` — the core annotation table with source-agnostic columns.
- ``annotations_fts`` — FTS5 virtual table for full-text search of
  ``selected_text`` and ``comment``.
- ``sync_queue`` — placeholder for future write-back (no write-back logic).
"""

from __future__ import annotations

import sqlite3

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema version — independent from the memory layer
# ---------------------------------------------------------------------------

ANNOTATION_SCHEMA_VERSION = 1
"""Current annotation schema version (independent of memory schema)."""

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_ANNOTATIONS = """
CREATE TABLE IF NOT EXISTS annotations (
    id                    TEXT PRIMARY KEY,
    paper_id              TEXT NOT NULL,
    source                TEXT NOT NULL DEFAULT 'paperforge',
    source_library_id     TEXT DEFAULT '',
    source_annotation_key TEXT DEFAULT '',
    source_attachment_key TEXT DEFAULT '',
    source_parent_key     TEXT DEFAULT '',
    source_version        INTEGER,
    source_modified_at    TEXT DEFAULT '',
    type                  TEXT NOT NULL,
    page_index            INTEGER,
    page_label            TEXT DEFAULT '',
    selected_text         TEXT DEFAULT '',
    comment               TEXT DEFAULT '',
    color                 TEXT DEFAULT '',
    sort_index            TEXT DEFAULT '',
    tags_json             TEXT DEFAULT '[]',
    position_json         TEXT DEFAULT '{}',
    selector_json         TEXT DEFAULT '{}',
    sync_state            TEXT NOT NULL DEFAULT 'local',
    is_readonly           INTEGER NOT NULL DEFAULT 0,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    deleted_at            TEXT
);
"""

CREATE_ANNOTATIONS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS annotations_fts USING fts5(
    selected_text,
    comment,
    content='annotations',
    content_rowid='rowid'
);
"""

CREATE_SYNC_QUEUE = """
CREATE TABLE IF NOT EXISTS sync_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    annotation_id TEXT NOT NULL,
    operation   TEXT NOT NULL,
    payload_json TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    synced_at   TEXT
);
"""
# NOTE: sync_queue is a PLACEHOLDER only. No write-back logic is implemented.
# Future phases will add write-back behavior using this table.

# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

ANNOTATION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_annotations_paper ON annotations(paper_id);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_source ON annotations(source);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_page ON annotations(page_index);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_sync ON annotations(sync_state);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_deleted ON annotations(deleted_at);",
]

# ---------------------------------------------------------------------------
# FTS triggers
# ---------------------------------------------------------------------------

FTS_TRIGGERS = [
    """CREATE TRIGGER IF NOT EXISTS annotations_ai AFTER INSERT ON annotations BEGIN
        INSERT INTO annotations_fts(rowid, selected_text, comment)
        VALUES (new.rowid, new.selected_text, new.comment);
    END;""",
    """CREATE TRIGGER IF NOT EXISTS annotations_ad AFTER DELETE ON annotations BEGIN
        INSERT INTO annotations_fts(annotations_fts, rowid, selected_text, comment)
        VALUES ('delete', old.rowid, old.selected_text, old.comment);
    END;""",
    """CREATE TRIGGER IF NOT EXISTS annotations_au AFTER UPDATE ON annotations BEGIN
        INSERT INTO annotations_fts(annotations_fts, rowid, selected_text, comment)
        VALUES ('delete', old.rowid, old.selected_text, old.comment);
        INSERT INTO annotations_fts(rowid, selected_text, comment)
        VALUES (new.rowid, new.selected_text, new.comment);
    END;""",
]

# ---------------------------------------------------------------------------
# Table inventory
# ---------------------------------------------------------------------------

ANNOTATION_TABLES = [
    "annotations_fts",
    "sync_queue",
    "annotations",
    "meta",
]

# ---------------------------------------------------------------------------
# Schema lifecycle
# ---------------------------------------------------------------------------


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create all annotation tables, indexes, triggers, and schema version.

    This function is **idempotent** — calling it multiple times is safe and
    will not drop existing rows.

    Args:
        conn: A writable SQLite connection to the annotation database.
    """
    # Tables
    conn.execute(CREATE_META)
    conn.execute(CREATE_ANNOTATIONS)
    conn.execute(CREATE_ANNOTATIONS_FTS)
    conn.execute(CREATE_SYNC_QUEUE)

    # Indexes
    for idx in ANNOTATION_INDEXES:
        conn.execute(idx)

    # FTS triggers
    for trigger in FTS_TRIGGERS:
        conn.execute(trigger)

    # Schema version — insert only when absent (idempotent)
    conn.execute(
        "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(ANNOTATION_SCHEMA_VERSION),),
    )

    conn.commit()


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the stored annotation schema version from the meta table.

    Returns:
        The stored schema version as an integer, or ``0`` if the meta table
        does not exist or the ``schema_version`` key is missing.
    """
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        return 0
