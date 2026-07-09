from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 6  # Bump from 5: add hash/policy cols to vec companion meta tables

CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_PAPERS = """
CREATE TABLE IF NOT EXISTS papers (
    zotero_key           TEXT PRIMARY KEY,
    citation_key         TEXT NOT NULL DEFAULT '',
    title                TEXT NOT NULL,
    year                 TEXT,
    doi                  TEXT,
    pmid                 TEXT,
    journal              TEXT,
    first_author         TEXT,
    authors_json         TEXT,
    abstract             TEXT,
    domain               TEXT,
    collection_path      TEXT,
    collections_json     TEXT,
    has_pdf              INTEGER NOT NULL DEFAULT 0,
    do_ocr               INTEGER,
    analyze              INTEGER,
    ocr_status           TEXT,
    deep_reading_status  TEXT,
    ocr_job_id           TEXT,
    impact_factor        REAL,
    lifecycle            TEXT,
    maturity_level       INTEGER,
    maturity_name        TEXT,
    next_step            TEXT,
    pdf_path             TEXT,
    note_path            TEXT,
    main_note_path       TEXT,
    paper_root           TEXT,
    fulltext_path        TEXT,
    ocr_md_path          TEXT,
    ocr_json_path        TEXT,
    ai_path              TEXT,
    deep_reading_md_path TEXT,
    updated_at           TEXT
);
"""

CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS paper_assets (
    paper_id       TEXT NOT NULL,
    asset_type     TEXT NOT NULL,
    path           TEXT NOT NULL,
    exists_on_disk INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (paper_id, asset_type),
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

CREATE_ALIASES = """
CREATE TABLE IF NOT EXISTS paper_aliases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id   TEXT NOT NULL,
    alias      TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);",
    "CREATE INDEX IF NOT EXISTS idx_papers_citation_key ON papers(citation_key);",
    "CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers(domain);",
    "CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);",
    "CREATE INDEX IF NOT EXISTS idx_papers_ocr_status ON papers(ocr_status);",
    "CREATE INDEX IF NOT EXISTS idx_papers_deep_status ON papers(deep_reading_status);",
    "CREATE INDEX IF NOT EXISTS idx_papers_lifecycle ON papers(lifecycle);",
    "CREATE INDEX IF NOT EXISTS idx_papers_next_step ON papers(next_step);",
]

CREATE_PAPER_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS paper_fts USING fts5(
    zotero_key,
    citation_key,
    title,
    first_author,
    authors_json,
    abstract,
    journal,
    domain,
    collection_path,
    collections_json,
    content='papers',
    content_rowid='rowid'
);
"""

PAPERS_AI_TRIGGER = """CREATE TRIGGER IF NOT EXISTS papers_ai AFTER INSERT ON papers BEGIN
    INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
    VALUES (new.rowid, new.zotero_key, new.citation_key, new.title, new.first_author, new.authors_json, new.abstract, new.journal, new.domain, new.collection_path, new.collections_json);
END;"""

FTS_TRIGGERS = [
    PAPERS_AI_TRIGGER,
    """CREATE TRIGGER IF NOT EXISTS papers_ad AFTER DELETE ON papers BEGIN
        INSERT INTO paper_fts(paper_fts, rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
        VALUES ('delete', old.rowid, old.zotero_key, old.citation_key, old.title, old.first_author, old.authors_json, old.abstract, old.journal, old.domain, old.collection_path, old.collections_json);
    END;""",
    """CREATE TRIGGER IF NOT EXISTS papers_au AFTER UPDATE ON papers BEGIN
        INSERT INTO paper_fts(paper_fts, rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
        VALUES ('delete', old.rowid, old.zotero_key, old.citation_key, old.title, old.first_author, old.authors_json, old.abstract, old.journal, old.domain, old.collection_path, old.collections_json);
        INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author, authors_json, abstract, journal, domain, collection_path, collections_json)
        VALUES (new.rowid, new.zotero_key, new.citation_key, new.title, new.first_author, new.authors_json, new.abstract, new.journal, new.domain, new.collection_path, new.collections_json);
    END;""",
]

CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS paper_events (
    event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id     TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    payload_json TEXT,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

EVENT_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_events_paper ON paper_events(paper_id);",
    "CREATE INDEX IF NOT EXISTS idx_events_type ON paper_events(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_events_time ON paper_events(created_at);",
]

CREATE_READING_LOG = """
CREATE TABLE IF NOT EXISTS reading_log (
    id          TEXT PRIMARY KEY,
    paper_id    TEXT NOT NULL,
    project     TEXT DEFAULT '',
    section     TEXT NOT NULL,
    excerpt     TEXT NOT NULL,
    context     TEXT DEFAULT '',
    usage       TEXT NOT NULL,
    note        TEXT DEFAULT '',
    tags_json   TEXT DEFAULT '[]',
    created_at  TEXT NOT NULL,
    agent       TEXT DEFAULT '',
    verified    INTEGER DEFAULT 0,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

CREATE_PROJECT_LOG = """
CREATE TABLE IF NOT EXISTS project_log (
    id                  TEXT PRIMARY KEY,
    project             TEXT NOT NULL,
    date                TEXT NOT NULL,
    type                TEXT NOT NULL,
    title               TEXT NOT NULL,
    decisions_json      TEXT DEFAULT '[]',
    detours_json        TEXT DEFAULT '[]',
    reusable_json       TEXT DEFAULT '[]',
    todos_json          TEXT DEFAULT '[]',
    related_papers_json TEXT DEFAULT '[]',
    tags_json           TEXT DEFAULT '[]',
    created_at          TEXT NOT NULL,
    agent               TEXT DEFAULT ''
);
"""

CREATE_BODY_UNITS = """
CREATE TABLE IF NOT EXISTS body_units (
    unit_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    section_path TEXT NOT NULL,
    section_path_json TEXT NOT NULL DEFAULT '[]',
    section_level INTEGER NOT NULL DEFAULT 0,
    section_title TEXT NOT NULL DEFAULT '',
    unit_text TEXT NOT NULL,
    unit_kind TEXT NOT NULL DEFAULT 'body',
    part_ordinal INTEGER NOT NULL DEFAULT 0,
    page_span_json TEXT NOT NULL,
    block_span_json TEXT NOT NULL,
    token_estimate INTEGER NOT NULL,
    indexable INTEGER NOT NULL,
    veto_reason TEXT NOT NULL,
    quality_hints_json TEXT NOT NULL
);
"""

CREATE_BODY_UNITS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS body_units_fts USING fts5(
    unit_id,
    paper_id,
    section_path,
    unit_text,
    content='body_units',
    content_rowid='rowid'
);
"""

CREATE_OBJECT_UNITS = """
CREATE TABLE IF NOT EXISTS object_units (
    unit_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    section_path TEXT NOT NULL,
    object_kind TEXT NOT NULL,
    object_label TEXT NOT NULL,
    caption_text TEXT NOT NULL,
    nearby_body_text TEXT NOT NULL DEFAULT '',
    page_span_json TEXT NOT NULL,
    block_span_json TEXT NOT NULL,
    token_estimate INTEGER NOT NULL DEFAULT 0,
    indexable INTEGER NOT NULL DEFAULT 1,
    veto_reason TEXT NOT NULL DEFAULT '',
    quality_hints_json TEXT NOT NULL DEFAULT '[]'
);
"""

CREATE_VEC_FULLTEXT = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_fulltext USING vec0(embedding float[1536]);
"""

CREATE_VEC_BODY = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_body USING vec0(embedding float[1536]);
"""

CREATE_VEC_OBJECTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_objects USING vec0(embedding float[1536]);
"""

CREATE_VEC_FULLTEXT_META = """
CREATE TABLE IF NOT EXISTS vec_fulltext_meta (
  rowid INTEGER PRIMARY KEY,
  paper_id TEXT NOT NULL,
  chunk_index INTEGER,
  text TEXT
);
"""

CREATE_VEC_BODY_META = """
CREATE TABLE IF NOT EXISTS vec_body_meta (
  rowid INTEGER PRIMARY KEY,
  paper_id TEXT NOT NULL,
  chunk_index INTEGER,
  text TEXT,
  body_units_hash TEXT,
  retrieval_policy_version TEXT
);
"""
CREATE_VEC_OBJECTS_META = """
CREATE TABLE IF NOT EXISTS vec_objects_meta (
  rowid INTEGER PRIMARY KEY,
  paper_id TEXT NOT NULL,
  chunk_index INTEGER,
  text TEXT,
  object_units_hash TEXT,
  retrieval_policy_version TEXT
);
"""

CREATE_BUILD_STATE = """
CREATE TABLE IF NOT EXISTS build_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


ALL_TABLES = [
    "body_units",
    "body_units_fts",
    "object_units",
    "paper_fts",
    "reading_log",
    "project_log",
    "paper_events",
    "paper_assets",
    "paper_aliases",
    "papers",
    "meta",
    "vec_fulltext_meta",
    "vec_body_meta",
    "vec_objects_meta",
    "build_state",
]
VEC_TABLES = ["vec_fulltext", "vec_body", "vec_objects"]


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they don't exist."""
    conn.execute(CREATE_META)
    conn.execute(CREATE_PAPERS)
    conn.execute(CREATE_ASSETS)
    conn.execute(CREATE_ALIASES)
    conn.execute(CREATE_PAPER_FTS)
    conn.execute(CREATE_EVENTS)
    conn.execute(CREATE_READING_LOG)
    conn.execute(CREATE_PROJECT_LOG)

    # Migration: derived tables are rebuildable, drop and recreate when shape changes
    current_version = get_schema_version(conn)
    if current_version < 3:
        logger.info("Migrating schema v%s -> v3: rebuilding body_units, body_units_fts, object_units", current_version)
        for table in ("body_units", "body_units_fts", "object_units"):
            conn.execute(f"DROP TABLE IF EXISTS {table};")
    if current_version < 4:
        logger.info("Migrating schema v%s -> v4: adding body_units columns", current_version)
        for col_sql in [
            "ALTER TABLE body_units ADD COLUMN section_path_json TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE body_units ADD COLUMN section_level INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE body_units ADD COLUMN section_title TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE body_units ADD COLUMN part_ordinal INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                conn.execute(col_sql)
            except Exception:
                pass  # column may already exist

    if current_version < 5:
        logger.info(
            "Migrating schema v%s -> v5: adding vec0 vector tables, companion meta, and build_state", current_version
        )
        try:
            conn.execute(CREATE_VEC_FULLTEXT)
            conn.execute(CREATE_VEC_BODY)
            conn.execute(CREATE_VEC_OBJECTS)
        except sqlite3.OperationalError:
            logger.warning("sqlite-vec extension not available, skipping vector virtual tables")
        conn.execute(CREATE_VEC_FULLTEXT_META)
        conn.execute(CREATE_VEC_BODY_META)
        conn.execute(CREATE_VEC_OBJECTS_META)
        conn.execute(CREATE_BUILD_STATE)

    if current_version < 6:
        logger.info(
            "Migrating schema v%s -> v6: adding hash/policy columns to vec companion meta tables", current_version
        )
        for col_sql in [
            "ALTER TABLE vec_body_meta ADD COLUMN body_units_hash TEXT",
            "ALTER TABLE vec_body_meta ADD COLUMN retrieval_policy_version TEXT",
            "ALTER TABLE vec_objects_meta ADD COLUMN object_units_hash TEXT",
            "ALTER TABLE vec_objects_meta ADD COLUMN retrieval_policy_version TEXT",
        ]:
            try:
                conn.execute(col_sql)
            except Exception:
                pass  # column may already exist

    conn.execute(CREATE_BODY_UNITS)
    conn.execute(CREATE_BODY_UNITS_FTS)
    conn.execute(CREATE_OBJECT_UNITS)
    for idx_sql in INDEX_SQL:
        conn.execute(idx_sql)
    for idx_sql in EVENT_INDEX_SQL:
        conn.execute(idx_sql)
    for trigger_sql in FTS_TRIGGERS:
        conn.execute(trigger_sql)

    _set_schema_version(conn, CURRENT_SCHEMA_VERSION)
    conn.commit()


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all Memory Layer tables (for rebuild)."""
    for table in ALL_TABLES + VEC_TABLES:
        logger.info("Dropping table: %s", table)
        conn.execute(f"DROP TABLE IF EXISTS {table};")
    conn.commit()


def clear_fts(conn: sqlite3.Connection) -> None:
    """Delete all FTS index entries (before rebuild)."""
    conn.execute("DELETE FROM paper_fts;")
    conn.execute("DELETE FROM body_units_fts;")
    conn.commit()


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the stored schema version from meta table, or 0 if not found."""
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        return 0


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    """Write the schema version into the meta table."""
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(version),),
    )
