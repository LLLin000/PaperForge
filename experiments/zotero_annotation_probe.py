#!/usr/bin/env python3
"""
Zotero Annotation Probe — read-only SQLite parser for Zotero annotations.

Usage:
    python experiments/zotero_annotation_probe.py --zotero-db "<path-to-zotero.sqlite>" [--limit 20]

Outputs unified JSON annotations to stdout. Never writes to Zotero SQLite.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


ANNOTATION_TYPE_MAP = {
    1: "highlight",
    2: "note",
    3: "image",
    4: "ink",
    5: "underline",
    6: "text",
}


def copy_db_to_temp(zotero_db: Path) -> Path:
    """Copy zotero.sqlite to a temp file to avoid locks and inconsistent reads."""
    tmp = Path(tempfile.mkdtemp()) / "zotero_copy.sqlite"
    shutil.copy2(str(zotero_db), str(tmp))
    return tmp


def open_readonly(db_path: Path) -> sqlite3.Connection:
    uri = "file:" + db_path.as_posix() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def probe_schema(conn: sqlite3.Connection) -> dict:
    """Return detected table schemas for verification."""
    tables = {}
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    for row in cursor.fetchall():
        tables[row["name"]] = True
    return tables


def fetch_annotations(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """Fetch annotations and their parent attachment info."""
    query = """
    SELECT
        ia.itemID,
        ia.parentItemID,
        ia.type AS annotation_type,
        ia.authorName,
        ia.text AS annotation_text,
        ia.comment AS annotation_comment,
        ia.color AS annotation_color,
        ia.pageLabel,
        ia.sortIndex,
        ia.position AS position_json,
        ia.isExternal,

        i.key AS annotation_key,
        i.libraryID,
        i.dateAdded,
        i.dateModified,
        i.version,

        att.key AS attachment_key,
        ia_att.path AS attachment_path,
        ia_att.linkMode AS attachment_link_mode,
        ia_att.contentType AS attachment_content_type,

        parent.key AS parent_item_key
    FROM itemAnnotations ia
    JOIN items i ON i.itemID = ia.itemID
    LEFT JOIN itemAttachments ia_att ON ia_att.itemID = ia.parentItemID
    LEFT JOIN items att ON att.itemID = ia.parentItemID
    LEFT JOIN items parent ON parent.itemID = ia_att.parentItemID
    LIMIT ?
    """
    rows = conn.execute(query, (limit,)).fetchall()

    results = []
    for row in rows:
        ann_type_int = row["annotation_type"]
        ann_type_str = ANNOTATION_TYPE_MAP.get(ann_type_int, f"unknown_{ann_type_int}")

        position = {}
        raw_pos = row["position_json"]
        if raw_pos:
            try:
                position = json.loads(raw_pos)
            except json.JSONDecodeError:
                position = {"_parse_error": True, "_raw_preview": raw_pos[:200]}

        # Fetch tags for this annotation
        tags = []
        try:
            tag_rows = conn.execute(
                """SELECT t.name
                   FROM itemTags it
                   JOIN tags t ON t.tagID = it.tagID
                   WHERE it.itemID = ?""",
                (row["itemID"],),
            ).fetchall()
            tags = [t["name"] for t in tag_rows]
        except Exception:
            pass

        entry = {
            "libraryID": row["libraryID"],
            "annotationKey": row["annotation_key"],
            "annotationTypeInt": ann_type_int,
            "annotationType": ann_type_str,
            "attachmentKey": row["attachment_key"],
            "parentItemKey": row["parent_item_key"],
            "isExternal": bool(row["isExternal"]),
            "selectedText": row["annotation_text"] or "",
            "comment": row["annotation_comment"] or "",
            "color": row["annotation_color"] or "#ffd400",
            "pageLabel": row["pageLabel"] or "",
            "sortIndex": row["sortIndex"] or "",
            "position": position,
            "tags": tags,
            "authorName": row["authorName"] or "",
            "dateAdded": row["dateAdded"] or "",
            "dateModified": row["dateModified"] or "",
            "version": row["version"] or 0,
            "attachment_path": row["attachment_path"] or "",
            "attachment_link_mode": row["attachment_link_mode"],
        }

        results.append(entry)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Read-only Zotero annotation probe"
    )
    parser.add_argument(
        "--zotero-db",
        required=True,
        help="Path to zotero.sqlite",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max annotations to return",
    )
    parser.add_argument(
        "--copy-db",
        action="store_true",
        default=True,
        help="Copy DB to temp before reading (default: True)",
    )
    parser.add_argument(
        "--no-copy",
        action="store_true",
        help="Skip DB copy (read directly, risky if Zotero is running)",
    )
    args = parser.parse_args()

    zotero_db = Path(args.zotero_db).expanduser().resolve()
    if not zotero_db.exists():
        print(json.dumps({
            "ok": False,
            "error": f"File not found: {zotero_db}",
        }, ensure_ascii=False))
        sys.exit(1)

    probe_path = zotero_db
    cleanup_path = None

    if not args.no_copy:
        try:
            probe_path = copy_db_to_temp(zotero_db)
            cleanup_path = probe_path.parent
        except Exception as e:
            print(json.dumps({
                "ok": False,
                "error": f"Failed to copy DB: {e}",
            }, ensure_ascii=False))
            sys.exit(1)

    try:
        conn = open_readonly(probe_path)

        tables = probe_schema(conn)
        if "itemAnnotations" not in tables:
            print(json.dumps({
                "ok": False,
                "error": "itemAnnotations table not found — not a valid Zotero SQLite?",
                "detected_tables": list(tables.keys()),
            }, ensure_ascii=False))
            sys.exit(1)

        annotations = fetch_annotations(conn, limit=args.limit)

        output = {
            "ok": True,
            "probe": {
                "zotero_db": str(zotero_db),
                "tables_found": list(tables.keys()),
                "annotation_count": len(annotations),
                "schema_version_detected": "itemAnnotations v125+",
            },
            "annotations": annotations,
        }

        print(json.dumps(output, ensure_ascii=False, indent=2))

    except sqlite3.DatabaseError as e:
        print(json.dumps({
            "ok": False,
            "error": f"SQLite error: {e}",
        }, ensure_ascii=False))
        sys.exit(1)
    finally:
        conn.close()
        if cleanup_path and cleanup_path.exists():
            shutil.rmtree(cleanup_path, ignore_errors=True)


if __name__ == "__main__":
    main()
