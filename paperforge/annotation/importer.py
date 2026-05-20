"""Annotation import/reconciliation logic.

Transforms raw Zotero probe data into PaperForge's annotation schema and
reconciles with existing rows using stable upsert semantics.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

PAPERFORGE_LOCAL_SOURCES = {"paperforge"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probe_to_row(
    ann: dict,
    source: str,
    now: str,
) -> dict[str, Any]:
    """Convert a normalized probe annotation dict into a DB row."""
    paper_id = ann.get("parentItemKey", "")
    zotero_key = ann.get("annotationKey", "")
    zotero_attachment_key = ann.get("attachmentKey", "")
    pdf_path = ann.get("attachment_path", "")
    version = ann.get("version", 0)
    modified = ann.get("dateModified", "")

    return {
        "id": zotero_key or str(uuid.uuid4()),
        "paper_id": paper_id,
        "zotero_library_id": ann.get("libraryID"),
        "zotero_item_id": None,
        "zotero_key": zotero_key,
        "zotero_attachment_key": zotero_attachment_key,
        "pdf_path": pdf_path,
        "pdf_hash": "",
        "type": ann.get("annotationType", ""),
        "page_index": ann.get("position", {}).get("pageIndex"),
        "page_label": ann.get("pageLabel", ""),
        "selected_text": ann.get("selectedText", ""),
        "comment": ann.get("comment", ""),
        "color": ann.get("color", ""),
        "sort_index": ann.get("sortIndex", ""),
        "tags_json": json.dumps(ann.get("tags", []), ensure_ascii=False),
        "position_json": json.dumps(ann.get("position", {}), ensure_ascii=False),
        "selector_json": "{}",
        "source": source,
        "source_key": zotero_key,
        "source_version": version,
        "source_modified_at": modified,
        "sync_state": "zotero_synced" if source != "paperforge" else "local",
        "is_readonly": 1 if source != "paperforge" else 0,
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }


UPSERT_SQL = """
INSERT INTO annotations (
    id,
    paper_id,
    zotero_library_id,
    zotero_item_id,
    zotero_key,
    zotero_attachment_key,
    pdf_path,
    pdf_hash,
    type,
    page_index,
    page_label,
    selected_text,
    comment,
    color,
    sort_index,
    tags_json,
    position_json,
    selector_json,
    source,
    source_key,
    source_version,
    source_modified_at,
    sync_state,
    is_readonly,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    :id,
    :paper_id,
    :zotero_library_id,
    :zotero_item_id,
    :zotero_key,
    :zotero_attachment_key,
    :pdf_path,
    :pdf_hash,
    :type,
    :page_index,
    :page_label,
    :selected_text,
    :comment,
    :color,
    :sort_index,
    :tags_json,
    :position_json,
    :selector_json,
    :source,
    :source_key,
    :source_version,
    :source_modified_at,
    :sync_state,
    :is_readonly,
    :created_at,
    :updated_at,
    :deleted_at
) ON CONFLICT(id) DO UPDATE SET
    paper_id           = excluded.paper_id,
    zotero_library_id  = excluded.zotero_library_id,
    zotero_key         = excluded.zotero_key,
    zotero_attachment_key = excluded.zotero_attachment_key,
    pdf_path           = excluded.pdf_path,
    type               = excluded.type,
    page_index         = excluded.page_index,
    page_label         = excluded.page_label,
    selected_text      = excluded.selected_text,
    comment            = excluded.comment,
    color              = excluded.color,
    sort_index         = excluded.sort_index,
    tags_json          = excluded.tags_json,
    position_json      = excluded.position_json,
    source_version     = excluded.source_version,
    source_modified_at = excluded.source_modified_at,
    updated_at         = excluded.updated_at,
    deleted_at         = excluded.deleted_at
"""


def _import_annotations(
    conn,
    annotations: list[dict],
    source: str,
) -> dict:
    """Core import logic. Returns {imported, updated, deleted}."""
    now = _now()
    stats = {"imported": 0, "updated": 0, "deleted": 0}

    incoming_keys = set()

    for ann in annotations:
        row = _probe_to_row(ann, source, now)
        zk = row["zotero_key"]
        incoming_keys.add(zk)

        # Check if row already exists by id (zotero_key for imported annotations)
        existing = conn.execute(
            "SELECT source_version, sync_state FROM annotations WHERE id = ?",
            (row["id"],),
        ).fetchone()

        if existing is None:
            conn.execute(UPSERT_SQL, row)
            stats["imported"] += 1
        elif existing["source_version"] != row["source_version"]:
            conn.execute(UPSERT_SQL, row)
            stats["updated"] += 1
        else:
            stats["updated"] += 0  # unchanged

    conn.commit()

    # Soft-delete stale rows that are no longer in the source's current set
    # Only applies to zotero_db source annotations
    if source != "paperforge" and incoming_keys:
        stale_rows = conn.execute(
            """SELECT id, sync_state FROM annotations
               WHERE source = ?
                 AND source_key NOT IN ({})
                 AND deleted_at IS NULL""".format(
                ",".join("?" for _ in incoming_keys)
            ),
            [source, *incoming_keys],
        ).fetchall()

        for stale in stale_rows:
            from paperforge.annotation.service import mark_deleted

            mark_deleted(conn, stale["id"])
            stats["deleted"] += 1

        conn.commit()

    return stats


def run_import(
    conn,
    annotations: list[dict],
    source: str,
) -> dict:
    """Import annotations from a probe result into annotations.db.

    Args:
        conn: Writable connection to annotations.db.
        annotations: List of normalized annotation dicts from probe.py.
        source: Source identifier, e.g. "zotero_db".

    Returns:
        Dict with keys: imported, updated, deleted.
    """
    return _import_annotations(conn, annotations, source)
