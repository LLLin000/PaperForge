"""Tests for the read-only Zotero SQLite annotation probe."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest


def _build_minimal_zotero_db(path: Path) -> None:
    """Create a minimal Zotero-style SQLite database with annotations for testing."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")

    # Minimal schema subset needed by the probe
    conn.executescript("""
        CREATE TABLE libraries (libraryID INTEGER PRIMARY KEY, type TEXT, editable INT, filesEditable INT, version INT, storageVersion INT, lastSync INT, archived INT, isAdmin INT);
        INSERT INTO libraries VALUES (1, 'user', 1, 1, 1, 0, 0, 0, 0);

        CREATE TABLE items (itemID INTEGER PRIMARY KEY, itemTypeID INT NOT NULL, dateAdded TEXT, dateModified TEXT, clientDateModified TEXT, libraryID INT NOT NULL, key TEXT NOT NULL, version INT DEFAULT 0, synced INT DEFAULT 0);
        INSERT INTO items VALUES (1, 1, '2025-01-01', '2025-01-02', '2025-01-01', 1, 'PAPER001', 5, 1);
        INSERT INTO items VALUES (2, 2, '2025-01-01', '2025-01-02', '2025-01-01', 1, 'ATTACH01', 5, 1);
        INSERT INTO items VALUES (3, 3, '2025-01-02', '2025-01-03', '2025-01-02', 1, 'ANNOT001', 3, 1);
        INSERT INTO items VALUES (4, 3, '2025-01-02', '2025-01-03', '2025-01-02', 1, 'ANNOT002', 2, 1);
        INSERT INTO items VALUES (5, 3, '2025-01-03', '2025-01-04', '2025-01-03', 1, 'ANNOT003', 1, 1);

        CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT);
        INSERT INTO itemTypes VALUES (1, 'journalArticle');
        INSERT INTO itemTypes VALUES (2, 'attachment');
        INSERT INTO itemTypes VALUES (3, 'annotation');

        CREATE TABLE itemAttachments (itemID INTEGER PRIMARY KEY, parentItemID INT, linkMode INT, contentType TEXT, path TEXT);
        INSERT INTO itemAttachments VALUES (2, 1, 0, 'application/pdf', 'storage:ATTACH01/paper.pdf');

        CREATE TABLE itemAnnotations (itemID INTEGER PRIMARY KEY, parentItemID INT NOT NULL, type INTEGER NOT NULL, authorName TEXT, text TEXT, comment TEXT, color TEXT, pageLabel TEXT, sortIndex TEXT NOT NULL, position TEXT NOT NULL, isExternal INT NOT NULL);
        INSERT INTO itemAnnotations VALUES (3, 2, 1, '', 'Deep learning methods are effective for image segmentation.', 'Important finding', '#ffd400', '3', '00002|000000|00000', '{"pageIndex":2,"rects":[[72,520,540,536],[72,504,540,520]]}', 0);
        INSERT INTO itemAnnotations VALUES (4, 2, 5, '', 'The primary limitation is the need for large datasets.', 'Related work section', '#ff6666', '12', '00011|000000|00000', '{"pageIndex":11,"rects":[[72,480,540,496]]}', 0);
        INSERT INTO itemAnnotations VALUES (5, 2, 2, '', '', '<p>Key figure explaining U-Net architecture.</p>', '#2ea8e5', '7', '00006|000000|00000', '{"pageIndex":6,"rects":[[420,360,540,400]]}', 0);

        CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        INSERT INTO tags VALUES (1, 'deep_learning');
        INSERT INTO tags VALUES (2, 'methods');

        CREATE TABLE itemTags (itemID INT NOT NULL, tagID INT NOT NULL, type INT NOT NULL, PRIMARY KEY (itemID, tagID));
        INSERT INTO itemTags VALUES (3, 1, 0);
        INSERT INTO itemTags VALUES (3, 2, 0);
    """)
    conn.commit()
    conn.close()


@pytest.fixture
def zotero_db_path() -> Path:
    path = Path(tempfile.mktemp(suffix=".sqlite"))
    _build_minimal_zotero_db(path)
    return path


class TestProbeNormalization:
    """Tests for annotation type mapping, position parsing, and tag aggregation."""

    def test_type_integer_mapped_to_string(self, zotero_db_path):
        from paperforge.annotation.probe import (
            fetch_annotations,
            open_readonly,
        )

        conn = open_readonly(zotero_db_path)
        try:
            anns = fetch_annotations(conn, limit=10)
            types = {a["annotationType"] for a in anns}
            assert "highlight" in types
            assert "underline" in types
            assert "note" in types
        finally:
            conn.close()

    def test_position_json_is_parsed(self, zotero_db_path):
        from paperforge.annotation.probe import (
            fetch_annotations,
            open_readonly,
        )

        conn = open_readonly(zotero_db_path)
        try:
            anns = fetch_annotations(conn, limit=10)
            highlight = next(a for a in anns if a["annotationType"] == "highlight")
            assert "pageIndex" in highlight["position"]
            assert "rects" in highlight["position"]
            assert len(highlight["position"]["rects"]) == 2
        finally:
            conn.close()

    def test_tags_aggregated_correctly(self, zotero_db_path):
        from paperforge.annotation.probe import (
            fetch_annotations,
            open_readonly,
        )

        conn = open_readonly(zotero_db_path)
        try:
            anns = fetch_annotations(conn, limit=10)
            highlight = next(a for a in anns if a["annotationType"] == "highlight")
            assert "deep_learning" in highlight["tags"]
            assert "methods" in highlight["tags"]
            # note annotation has no tags
            note_ann = next(a for a in anns if a["annotationType"] == "note")
            assert note_ann["tags"] == []
        finally:
            conn.close()

    def test_readonly_connection_works(self, zotero_db_path):
        """Confirm open_readonly opens with mode=ro."""
        from paperforge.annotation.probe import open_readonly

        conn = open_readonly(zotero_db_path)
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM items").fetchone()
            assert row["cnt"] == 5
        finally:
            conn.close()

    def test_normalized_output_shape(self, zotero_db_path):
        """Verify the dict shape matches what the importer expects."""
        from paperforge.annotation.probe import (
            fetch_annotations,
            open_readonly,
        )

        conn = open_readonly(zotero_db_path)
        try:
            anns = fetch_annotations(conn, limit=10)
            assert len(anns) == 3
            for ann in anns:
                assert "libraryID" in ann
                assert "annotationKey" in ann
                assert "annotationType" in ann
                assert "selectedText" in ann
                assert "comment" in ann
                assert "color" in ann
                assert "sortIndex" in ann
                assert "position" in ann
                assert "tags" in ann
                assert "parentItemKey" in ann
                assert "attachmentKey" in ann
        finally:
            conn.close()
