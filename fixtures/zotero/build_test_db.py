"""Build a minimal Zotero SQLite fixture for annotation import testing.

Usage: python fixtures/zotero/build_test_db.py [--output PATH]

Default output: fixtures/zotero/test_annotations.sqlite (alongside this script)
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def build_test_db(path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=OFF")

    conn.executescript("""
        CREATE TABLE libraries (
            libraryID INTEGER PRIMARY KEY, type TEXT, editable INT,
            filesEditable INT, version INT, storageVersion INT,
            lastSync INT, archived INT, isAdmin INT
        );
        INSERT INTO libraries VALUES (1, 'user', 1, 1, 1, 0, 0, 0, 0);

        CREATE TABLE items (
            itemID INTEGER PRIMARY KEY, itemTypeID INT NOT NULL,
            dateAdded TEXT, dateModified TEXT, clientDateModified TEXT,
            libraryID INT NOT NULL, key TEXT NOT NULL,
            version INT DEFAULT 0, synced INT DEFAULT 0
        );
        -- Top-level paper
        INSERT INTO items VALUES (1, 1, '2025-01-01', '2025-01-02', '2025-01-01', 1, 'PAPER001', 5, 1);
        -- PDF attachment
        INSERT INTO items VALUES (2, 2, '2025-01-01', '2025-01-02', '2025-01-01', 1, 'ATTACH01', 5, 1);
        -- Annotations
        INSERT INTO items VALUES (3, 3, '2025-01-02', '2025-01-03', '2025-01-02', 1, 'ANNOT001', 3, 1);
        INSERT INTO items VALUES (4, 3, '2025-01-02', '2025-01-03', '2025-01-02', 1, 'ANNOT002', 2, 1);
        INSERT INTO items VALUES (5, 3, '2025-01-03', '2025-01-04', '2025-01-03', 1, 'ANNOT003', 1, 1);

        CREATE TABLE itemTypes (itemTypeID INTEGER PRIMARY KEY, typeName TEXT);
        INSERT INTO itemTypes VALUES (1, 'journalArticle');
        INSERT INTO itemTypes VALUES (2, 'attachment');
        INSERT INTO itemTypes VALUES (3, 'annotation');

        CREATE TABLE itemAttachments (
            itemID INTEGER PRIMARY KEY, parentItemID INT,
            linkMode INT, contentType TEXT, path TEXT
        );
        INSERT INTO itemAttachments VALUES (2, 1, 0, 'application/pdf', 'storage:ATTACH01/paper.pdf');

        CREATE TABLE itemAnnotations (
            itemID INTEGER PRIMARY KEY, parentItemID INT NOT NULL,
            type INTEGER NOT NULL, authorName TEXT, text TEXT, comment TEXT,
            color TEXT, pageLabel TEXT, sortIndex TEXT NOT NULL,
            position TEXT NOT NULL, isExternal INT NOT NULL
        );
        -- highlight
        INSERT INTO itemAnnotations VALUES (3, 2, 1, '',
            'Deep learning methods are effective for image segmentation.',
            'Important finding', '#ffd400', '3',
            '00002|000000|00000',
            '{"pageIndex":2,"rects":[[72,520,540,536],[72,504,540,520]]}', 0);
        -- underline
        INSERT INTO itemAnnotations VALUES (4, 2, 5, '',
            'The primary limitation is the need for large annotated datasets.',
            'Related work section', '#ff6666', '12',
            '00011|000000|00000',
            '{"pageIndex":11,"rects":[[72,480,540,496]]}', 0);
        -- note
        INSERT INTO itemAnnotations VALUES (5, 2, 2, '', '',
            '<p>Key figure explaining U-Net architecture.</p>', '#2ea8e5', '7',
            '00006|000000|00000',
            '{"pageIndex":6,"rects":[[420,360,540,400]]}', 0);

        CREATE TABLE tags (tagID INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        INSERT INTO tags VALUES (1, 'deep_learning');
        INSERT INTO tags VALUES (2, 'methods');

        CREATE TABLE itemTags (
            itemID INT NOT NULL, tagID INT NOT NULL, type INT NOT NULL,
            PRIMARY KEY (itemID, tagID)
        );
        INSERT INTO itemTags VALUES (3, 1, 0);
        INSERT INTO itemTags VALUES (3, 2, 0);
    """)
    conn.commit()
    conn.close()
    print(f"Built test fixture at {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or (Path(__file__).resolve().parent / "test_annotations.sqlite")
    build_test_db(output)
