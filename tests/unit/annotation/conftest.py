"""Shared fixture helpers for annotation unit tests.

Provides runtime-generated Zotero SQLite databases and annotations.db
fixtures used across multiple test modules.

TEST-01: Generated fixtures include parent papers, PDF attachments, and
multiple annotation rows with tags and position JSON.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from paperforge.annotation.schema import ensure_schema

# ---------------------------------------------------------------------------
# Constants: shared item IDs for cross-test reference
# ---------------------------------------------------------------------------

# Flow-test paper A (libraryID=1, parent_key=PAPER_A, attachment_key=ATTACH_A1)
PAPER_A_LIBRARY = 1
PAPER_A_PARENT_KEY = "PAPER_A"
PAPER_A_ATTACH_KEY = "ATTACH_A1"
PAPER_A_PARENT_ITEM_ID = 1
PAPER_A_ATTACH_ITEM_ID = 2
ANNOT_A1_KEY = "ANNOT_A1"
ANNOT_A2_KEY = "ANNOT_A2"

# Flow-test paper B (libraryID=2, parent_key=PAPER_B, attachment_key=ATTACH_B1)
PAPER_B_LIBRARY = 2
PAPER_B_PARENT_KEY = "PAPER_B"
PAPER_B_ATTACH_KEY = "ATTACH_B1"
PAPER_B_PARENT_ITEM_ID = 10
PAPER_B_ATTACH_ITEM_ID = 11
ANNOT_B1_KEY = "ANNOT_B1"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def open_ann(db_path: Path) -> sqlite3.Connection:
    """Open annotations.db with Row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Fixture builders: minimal Zotero-style SQLite databases
# ---------------------------------------------------------------------------


def build_zotero_two_paper(db_path: Path) -> None:
    """Create a minimal Zotero-style SQLite with two papers.

    Paper A (libraryID=1):
      parent item (itemID=1, key=PAPER_A)
      └── attachment (itemID=2, key=ATTACH_A1)
            ├── annotation (itemID=3, key=ANNOT_A1) — highlight, page 1, tagged
            └── annotation (itemID=4, key=ANNOT_A2) — note, page 2

    Paper B (libraryID=2):
      parent item (itemID=10, key=PAPER_B)
      └── attachment (itemID=11, key=ATTACH_B1)
            └── annotation (itemID=12, key=ANNOT_B1) — underline, page 3
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE items (
                itemID INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                libraryID INTEGER NOT NULL DEFAULT 1,
                dateModified TEXT
            );
            CREATE TABLE itemAttachments (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                path TEXT,
                contentType TEXT
            );
            CREATE TABLE itemAnnotations (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                type TEXT, text TEXT, comment TEXT, color TEXT,
                pageLabel TEXT, sortIndex INTEGER, position TEXT,
                dateModified TEXT
            );
            CREATE TABLE tags (
                tagID INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE itemTags (
                itemID INTEGER NOT NULL,
                tagID INTEGER NOT NULL
            );

            -- Paper A: parent, attachment, annotations
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (1, 'PAPER_A', 1, '2024-07-01');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (2, 'ATTACH_A1', 1, '2024-07-01');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (3, 'ANNOT_A1', 1, '2024-07-01T10:00:00Z');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (4, 'ANNOT_A2', 1, '2024-07-01T11:00:00Z');

            -- Paper B: parent, attachment, annotation
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (10, 'PAPER_B', 2, '2024-07-02');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (11, 'ATTACH_B1', 2, '2024-07-02');
            INSERT INTO items (itemID, key, libraryID, dateModified)
            VALUES (12, 'ANNOT_B1', 2, '2024-07-02T12:00:00Z');

            -- Attachments
            INSERT INTO itemAttachments (itemID, parentItemID, path, contentType)
            VALUES (2, 1, 'storage:ATTACH_A1/file.pdf', 'application/pdf');
            INSERT INTO itemAttachments (itemID, parentItemID, path, contentType)
            VALUES (11, 10, 'storage:ATTACH_B1/file.pdf', 'application/pdf');

            -- Annotations for Paper A / ATTACH_A1
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (3, 2, 'highlight',
                    'first significant result',
                    'this is the key finding',
                    '#ffd400',
                    '1', 0,
                    '{"x":0.1,"y":0.2,"w":0.8,"h":0.05}',
                    '2024-07-01T10:00:00Z');

            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (4, 2, 'note',
                    'another observation',
                    'supplementary note',
                    '#ff6666',
                    '2', 1,
                    '{"x":0.3,"y":0.4,"w":0.5,"h":0.1}',
                    '2024-07-01T11:00:00Z');

            -- Annotation for Paper B / ATTACH_B1
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (12, 11, 'underline',
                    'methodology detail',
                    'check this method',
                    '#00ff00',
                    '3', 0,
                    '{"x":0.5,"y":0.6,"w":0.3,"h":0.02}',
                    '2024-07-02T12:00:00Z');

            -- Tags: ANNOT_A1 gets "important" tag
            INSERT INTO tags (tagID, name) VALUES (1, 'important');
            INSERT INTO tags (tagID, name) VALUES (2, 'methodology');
            INSERT INTO itemTags (itemID, tagID) VALUES (3, 1);
        """)
        conn.commit()
    finally:
        conn.close()


def build_zotero_unknown_schema(db_path: Path) -> None:
    """Create a SQLite file with no Zotero annotation tables.

    Simulates a database with an unknown/unsupported schema version.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE some_other_table (id INTEGER PRIMARY KEY, val TEXT)"
        )
        conn.commit()
    finally:
        conn.close()


def build_zotero_fixture_full(db_path: Path) -> None:
    """Create a Zotero-style SQLite with sample rows for import scenarios.

    Layout:
      PAPER001 (itemID=1, libraryID=1)
        └── ATTACH01 (itemID=2, parentItemID=1)
              ├── ANNT001 (itemID=3) – highlight, page 1, tagged "important"
              └── ANNT002 (itemID=4) – note,      page 2
        └── ATTACH02 (itemID=5, parentItemID=1) – different attachment
              └── ANNT003 (itemID=6) – highlight, page 1
      PAPER002 (itemID=7, libraryID=2) – different library
        └── ATTACH03 (itemID=8, parentItemID=7)
              └── ANNT004 (itemID=9) – highlight, page 1
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE items (
                itemID INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                libraryID INTEGER NOT NULL DEFAULT 1,
                dateModified TEXT
            );
            CREATE TABLE itemAttachments (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL
            );
            CREATE TABLE itemAnnotations (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                type TEXT, text TEXT, comment TEXT, color TEXT,
                pageLabel TEXT, sortIndex INTEGER, position TEXT, dateModified TEXT
            );
            CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE itemTags (itemID INTEGER NOT NULL, tagID INTEGER NOT NULL);

            -- paper items
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (1, 'PAPER001', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (7, 'PAPER002', 2, '2024-06-01');

            -- attachment items
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (2, 'ATTACH01', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (5, 'ATTACH02', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (8, 'ATTACH03', 2, '2024-06-01');

            -- annotation items
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (3, 'ANNT001', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (4, 'ANNT002', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (6, 'ANNT003', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (9, 'ANNT004', 2, '2024-06-01');

            -- attachments
            INSERT INTO itemAttachments (itemID, parentItemID) VALUES (2, 1);
            INSERT INTO itemAttachments (itemID, parentItemID) VALUES (5, 1);
            INSERT INTO itemAttachments (itemID, parentItemID) VALUES (8, 7);

            -- annotations on ATTACH01 (paper1)
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (3, 2, 'highlight', 'significant result', 'my comment', '#ffd400',
                    '1', 0, '{"x":0.1}', '2024-06-01');

            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (4, 2, 'note', 'another observation', 'note content', '#ff6666',
                    '2', 1, '{"x":0.2}', '2024-06-01');

            -- annotation on ATTACH02 (paper1, different attachment)
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (6, 5, 'highlight', 'different attachment', 'diff comment', '#ffd400',
                    '1', 0, '{}', '2024-06-01');

            -- annotation on ATTACH03 (paper2, different library)
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (9, 8, 'highlight', 'library 2 annotation', 'lib2 comment', '#00ff00',
                    '1', 0, '{}', '2024-06-01');

            -- tags
            INSERT INTO tags (tagID, name) VALUES (1, 'important');
            INSERT INTO itemTags (itemID, tagID) VALUES (3, 1);
        """)
        conn.commit()
    finally:
        conn.close()


def build_zotero_fixture_reduced(db_path: Path) -> None:
    """Like build_zotero_fixture_full but missing ANNT002 (itemID=4).

    Used to trigger stale detection: after importing from the full fixture,
    re-importing from the reduced fixture should mark ANNT002 as stale.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("""
            CREATE TABLE items (
                itemID INTEGER PRIMARY KEY,
                key TEXT NOT NULL,
                libraryID INTEGER NOT NULL DEFAULT 1,
                dateModified TEXT
            );
            CREATE TABLE itemAttachments (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL
            );
            CREATE TABLE itemAnnotations (
                itemID INTEGER PRIMARY KEY,
                parentItemID INTEGER NOT NULL,
                type TEXT, text TEXT, comment TEXT, color TEXT,
                pageLabel TEXT, sortIndex INTEGER, position TEXT, dateModified TEXT
            );
            CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE itemTags (itemID INTEGER NOT NULL, tagID INTEGER NOT NULL);

            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (1, 'PAPER001', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (7, 'PAPER002', 2, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (2, 'ATTACH01', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (5, 'ATTACH02', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (8, 'ATTACH03', 2, '2024-06-01');
            -- ANNT001 present, ANNT002 is MISSING
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (3, 'ANNT001', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (6, 'ANNT003', 1, '2024-06-01');
            INSERT INTO items (itemID, key, libraryID, dateModified) VALUES (9, 'ANNT004', 2, '2024-06-01');

            INSERT INTO itemAttachments (itemID, parentItemID) VALUES (2, 1);
            INSERT INTO itemAttachments (itemID, parentItemID) VALUES (5, 1);
            INSERT INTO itemAttachments (itemID, parentItemID) VALUES (8, 7);

            -- Only ANNT001 on ATTACH01 (ANNT002 is absent)
            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (3, 2, 'highlight', 'significant result', 'my comment', '#ffd400',
                    '1', 0, '{"x":0.1}', '2024-06-01');

            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (6, 5, 'highlight', 'different attachment', 'diff comment', '#ffd400',
                    '1', 0, '{}', '2024-06-01');

            INSERT INTO itemAnnotations
                (itemID, parentItemID, type, text, comment, color,
                 pageLabel, sortIndex, position, dateModified)
            VALUES (9, 8, 'highlight', 'library 2 annotation', 'lib2 comment', '#00ff00',
                    '1', 0, '{}', '2024-06-01');

            INSERT INTO tags (tagID, name) VALUES (1, 'important');
            INSERT INTO itemTags (itemID, tagID) VALUES (3, 1);
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Temp-file fixtures (auto-cleanup)
# ---------------------------------------------------------------------------


def _temp_db(suffix: str = ".sqlite") -> Path:
    """Create a temporary file path that will be cleaned up."""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    return Path(tmp.name)


@pytest.fixture
def zotero_two_paper_path() -> Path:
    """Create a Zotero-style SQLite with two papers (flow-test layout)."""
    db_path = _temp_db()
    build_zotero_two_paper(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def zotero_unknown_schema_path() -> Path:
    """Create a SQLite file with no Zotero annotation tables."""
    db_path = _temp_db()
    build_zotero_unknown_schema(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def zotero_full_path() -> Path:
    """Create a full Zotero fixture database (importer-test layout)."""
    db_path = _temp_db()
    build_zotero_fixture_full(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def zotero_reduced_path() -> Path:
    """Create a reduced Zotero fixture (missing ANNT002, for stale tests)."""
    db_path = _temp_db()
    build_zotero_fixture_reduced(db_path)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def ann_db_path() -> Path:
    """Create an empty annotations.db with schema applied."""
    db_path = _temp_db(suffix=".annotations.db")
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)
    finally:
        conn.close()
    yield db_path
    if db_path.exists():
        db_path.unlink()
