"""Read-only probe into Zotero SQLite for annotation data.

This module opens Zotero's zotero.sqlite in read-only mode and extracts
normalized annotation data. It NEVER writes to any Zotero-owned file.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

ANNOTATION_TYPE_MAP = {
    1: "highlight",
    2: "note",
    3: "image",
    4: "ink",
    5: "underline",
    6: "text",
}

FETCH_ANNOTATIONS_SQL = """
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

    parent.key AS parent_item_key
FROM itemAnnotations ia
JOIN items i ON i.itemID = ia.itemID
LEFT JOIN itemAttachments ia_att ON ia_att.itemID = ia.parentItemID
LEFT JOIN items att ON att.itemID = ia.parentItemID
LEFT JOIN items parent ON parent.itemID = ia_att.parentItemID
ORDER BY ia.sortIndex
"""

FETCH_TAGS_SQL = """
SELECT it.itemID, t.name
FROM itemTags it
JOIN tags t ON t.tagID = it.tagID
WHERE it.itemID IN (%s)
"""


def copy_db_to_temp(zotero_db: Path) -> Path:
    """Copy zotero.sqlite to a temp file to avoid locks and inconsistent reads.

    The caller is responsible for cleaning up the temp directory.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="pf_zotero_"))
    dest = tmp_dir / "zotero_copy.sqlite"
    shutil.copy2(str(zotero_db), str(dest))
    logger.info("Copied %s to %s", zotero_db, dest)
    return dest


def open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open a Zotero SQLite database in read-only mode.

    Uses URI ``mode=ro`` to enforce read-only access.
    """
    uri = "file:" + db_path.as_posix() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_tags(conn: sqlite3.Connection, item_ids: list[int]) -> dict[int, list[str]]:
    """Fetch tags for the given item IDs. Returns {itemID: [tag_name, ...]}."""
    if not item_ids:
        return {}
    placeholders = ",".join("?" for _ in item_ids)
    rows = conn.execute(FETCH_TAGS_SQL % placeholders, item_ids).fetchall()
    result: dict[int, list[str]] = {iid: [] for iid in item_ids}
    for row in rows:
        result.setdefault(row["itemID"], []).append(row["name"])
    return result


def normalize_annotation_row(row: sqlite3.Row, tags: list[str]) -> dict:
    """Convert a raw Zotero annotation row into a normalized dict."""
    ann_type_int = row["annotation_type"]
    ann_type_str = ANNOTATION_TYPE_MAP.get(ann_type_int, f"unknown_{ann_type_int}")

    position = {}
    raw_pos = row["position_json"]
    if raw_pos:
        try:
            position = json.loads(raw_pos)
        except json.JSONDecodeError:
            position = {"_parse_error": True, "_raw_preview": raw_pos[:200]}

    return {
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


def fetch_annotations(
    conn: sqlite3.Connection, limit: int = 100
) -> list[dict]:
    """Fetch annotations from Zotero SQLite with tags.

    Args:
        conn: Read-only connection to zotero.sqlite.
        limit: Maximum number of annotation items to return.

    Returns:
        List of normalized annotation dicts.
    """
    rows = conn.execute(FETCH_ANNOTATIONS_SQL + " LIMIT ?", (limit,)).fetchall()
    if not rows:
        return []

    item_ids = [r["itemID"] for r in rows]
    tags_map = _fetch_tags(conn, item_ids)

    return [normalize_annotation_row(r, tags_map.get(r["itemID"], [])) for r in rows]


def probe(
    conn: sqlite3.Connection,
    limit: int = 20,
) -> dict:
    """Full probe: fetch annotations and report metadata.

    Returns a dict with ``ok``, ``probe``, and ``annotations`` keys.
    """
    annotations = fetch_annotations(conn, limit=limit)
    return {
        "ok": True,
        "probe": {
            "annotation_count": len(annotations),
        },
        "annotations": annotations,
    }
