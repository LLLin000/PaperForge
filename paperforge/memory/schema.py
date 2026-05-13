from __future__ import annotations

import sqlite3

CURRENT_SCHEMA_VERSION = 1

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

ALL_TABLES = ["paper_fts", "papers", "paper_assets", "paper_aliases", "meta", "paper_events"]


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they don't exist."""
    conn.execute(CREATE_META)
    conn.execute(CREATE_PAPERS)
    conn.execute(CREATE_ASSETS)
    conn.execute(CREATE_ALIASES)
    conn.execute(CREATE_PAPER_FTS)
    conn.execute(CREATE_EVENTS)
    for idx_sql in INDEX_SQL:
        conn.execute(idx_sql)
    for idx_sql in EVENT_INDEX_SQL:
        conn.execute(idx_sql)
    for trigger_sql in FTS_TRIGGERS:
        conn.execute(trigger_sql)
    conn.commit()


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all Memory Layer tables (for rebuild)."""
    for table in ALL_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table};")
    conn.commit()


def clear_fts(conn: sqlite3.Connection) -> None:
    """Delete all FTS index entries (before rebuild)."""
    conn.execute("DELETE FROM paper_fts;")
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
