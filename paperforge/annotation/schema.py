"""Annotation database schema — independent from memory layer paperforge.db.

Schema version 1 creates:
  - meta            version tracking
  - annotations     normalized annotation table
  - annotations_fts FTS5 virtual table for full-text search
  - sync_queue      future write-back operation queue

This DB is never dropped during paperforge memory rebuild.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

ANNOTATIONS_SCHEMA_VERSION = 1

CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_ANNOTATIONS = """
CREATE TABLE IF NOT EXISTS annotations (
    id                  TEXT PRIMARY KEY,
    paper_id            TEXT NOT NULL,

    zotero_library_id   INTEGER,
    zotero_item_id      INTEGER,
    zotero_key          TEXT DEFAULT '',
    zotero_attachment_key TEXT DEFAULT '',

    pdf_path            TEXT DEFAULT '',
    pdf_hash            TEXT DEFAULT '',

    type                TEXT NOT NULL,
    page_index          INTEGER,
    page_label          TEXT DEFAULT '',

    selected_text       TEXT DEFAULT '',
    comment             TEXT DEFAULT '',
    color               TEXT DEFAULT '',
    sort_index          TEXT DEFAULT '',
    tags_json           TEXT DEFAULT '[]',

    position_json       TEXT DEFAULT '{}',
    selector_json       TEXT DEFAULT '{}',

    source              TEXT NOT NULL DEFAULT 'paperforge',
    source_key          TEXT DEFAULT '',
    source_version      INTEGER,
    source_modified_at  TEXT DEFAULT '',

    sync_state          TEXT NOT NULL DEFAULT 'local',
    is_readonly         INTEGER NOT NULL DEFAULT 0,

    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    deleted_at          TEXT
);
"""

ANNOTATION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_annotations_paper ON annotations(paper_id);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_sync_state ON annotations(sync_state);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_source ON annotations(source);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_page ON annotations(paper_id, page_index);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_zotero_key ON annotations(zotero_key);",
    "CREATE INDEX IF NOT EXISTS idx_annotations_deleted ON annotations(deleted_at) WHERE deleted_at IS NOT NULL;",
]

CREATE_ANNOTATIONS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS annotations_fts USING fts5(
    paper_id,
    selected_text,
    comment,
    tags_json,
    content='annotations',
    content_rowid='rowid'
);
"""

FTS_TRIGGERS = [
    """CREATE TRIGGER IF NOT EXISTS annotations_ai AFTER INSERT ON annotations BEGIN
    INSERT INTO annotations_fts(rowid, paper_id, selected_text, comment, tags_json)
    VALUES (new.rowid, new.paper_id, new.selected_text, new.comment, new.tags_json);
END;""",
    """CREATE TRIGGER IF NOT EXISTS annotations_ad AFTER DELETE ON annotations BEGIN
    INSERT INTO annotations_fts(annotations_fts, rowid, paper_id, selected_text, comment, tags_json)
    VALUES ('delete', old.rowid, old.paper_id, old.selected_text, old.comment, old.tags_json);
END;""",
    """CREATE TRIGGER IF NOT EXISTS annotations_au AFTER UPDATE ON annotations BEGIN
    INSERT INTO annotations_fts(annotations_fts, rowid, paper_id, selected_text, comment, tags_json)
    VALUES ('delete', old.rowid, old.paper_id, old.selected_text, old.comment, old.tags_json);
    INSERT INTO annotations_fts(rowid, paper_id, selected_text, comment, tags_json)
    VALUES (new.rowid, new.paper_id, new.selected_text, new.comment, new.tags_json);
END;""",
]

CREATE_SYNC_QUEUE = """
CREATE TABLE IF NOT EXISTS sync_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    annotation_id   TEXT NOT NULL,
    operation       TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    retry_count     INTEGER DEFAULT 0,
    last_error      TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (annotation_id) REFERENCES annotations(id)
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables, indexes, FTS, and triggers if they don't exist."""
    conn.execute(CREATE_META)
    conn.execute(CREATE_ANNOTATIONS)
    for idx_sql in ANNOTATION_INDEXES:
        conn.execute(idx_sql)
    conn.execute(CREATE_ANNOTATIONS_FTS)
    for trigger_sql in FTS_TRIGGERS:
        conn.execute(trigger_sql)
    conn.execute(CREATE_SYNC_QUEUE)

    # Ensure version is recorded
    version = get_schema_version(conn)
    if version == 0:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(ANNOTATIONS_SCHEMA_VERSION),),
        )
    conn.commit()


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the stored schema version from meta table, or 0 if not found."""
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        return 0
