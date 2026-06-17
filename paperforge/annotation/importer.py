"""Scoped Zotero annotation import into PaperForge annotations.db.

**SAFE-04 contract:**
The importer writes ONLY to PaperForge's ``annotations.db``.  It reads from
a read-only Zotero SQLite connection (snapshot) and never writes to Zotero.

**D-02 / D-03 — Paper-scoped stale reconciliation:**
Stale marking is limited to rows matching all of:
- ``paper_id``
- ``source = 'zotero'``
- ``source_library_id``
- ``source_parent_key``
- ``source_attachment_key``

This prevents one paper's import from affecting unrelated annotation state.

**D-07 — Read-only rows:**
All imported Zotero rows have ``is_readonly = 1``.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.annotation.errors import AnnotationImportError
from paperforge.annotation.schema import ensure_schema
from paperforge.annotation.zotero_normalize import normalize_zotero_annotation
from paperforge.annotation.zotero_probe import fetch_zotero_item_annotations


# ---------------------------------------------------------------------------
# Import result — stable count fields for CLI JSON
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    """Aggregate counts from a single import call.

    Fields are designed to map directly to CLI ``--json`` output keys.
    The ``total`` property is computed from the five category fields.
    """

    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    stale: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return (
            self.inserted
            + self.updated
            + self.unchanged
            + self.stale
            + self.skipped
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    """ISO-8601 UTC timestamp (second precision)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _str(val: Any) -> str:
    """Safely convert a value to string, treating None as empty string."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    return str(val)


def _enrich_annotation(
    zotero_conn: sqlite3.Connection,
    raw_row: dict[str, Any],
    library_id: int,
    attachment_item_key: str,
    parent_item_key: str,
) -> dict[str, Any]:
    """Resolve identity fields and tags for a raw itemAnnotations row.

    Adds the following keys to a copy of *raw_row*:
    - ``library_id`` (int, from caller)
    - ``annotation_key`` (str, from ``items.key`` via itemID)
    - ``attachment_key`` (str, from caller)
    - ``parent_key`` (str, from caller)
    - ``tags`` (list[str], from ``itemTags`` + ``tags`` JOIN)

    Args:
        zotero_conn: Read-only Zotero snapshot connection.
        raw_row: A single row from ``itemAnnotations`` (dict-like).
        library_id: Zotero library ID.
        attachment_item_key: Attachment key string.
        parent_item_key: Parent item key string.

    Returns:
        Enriched dict ready for ``normalize_zotero_annotation``.
    """
    ann_item_id = raw_row["itemID"]

    # Resolve the annotation's own key from items table
    item_row = zotero_conn.execute(
        "SELECT key FROM items WHERE itemID = ?", (ann_item_id,)
    ).fetchone()
    annotation_key = _str(item_row["key"] if item_row else "")

    # Resolve tags via itemTags + tags JOIN
    tag_rows = zotero_conn.execute(
        "SELECT t.name FROM tags t "
        "JOIN itemTags it ON t.tagID = it.tagID "
        "WHERE it.itemID = ? ORDER BY t.name",
        (ann_item_id,),
    ).fetchall()
    tags = [r["name"] for r in tag_rows]

    enriched = dict(raw_row)
    enriched["library_id"] = library_id
    enriched["annotation_key"] = annotation_key
    enriched["attachment_key"] = attachment_item_key
    enriched["parent_key"] = parent_item_key
    enriched["tags"] = tags
    return enriched


def _upsert_annotation(
    db_conn: sqlite3.Connection,
    ann: Any,  # NormalizedAnnotation (duck-typed to avoid import cycles)
    result: ImportResult,
) -> None:
    """Insert or update a single normalized annotation.

    Preserves ``created_at`` on update; refreshes ``updated_at``.
    Sets ``deleted_at = NULL`` when a previously stale row reappears.

    Mutates *result* counts in place.
    """
    existing = db_conn.execute(
        "SELECT * FROM annotations WHERE id = ?", (ann.id,)
    ).fetchone()

    if existing is None:
        # -- New row -------------------------------------------------------
        db_conn.execute(
            """INSERT INTO annotations (
                id, paper_id, source,
                source_library_id, source_annotation_key,
                source_attachment_key, source_parent_key,
                source_version, source_modified_at,
                type, page_index, page_label,
                selected_text, comment, color,
                sort_index, tags_json, position_json, selector_json,
                sync_state, is_readonly,
                created_at, updated_at, deleted_at
            ) VALUES (?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?)""",
            (
                ann.id,
                ann.paper_id,
                ann.source,
                ann.source_library_id,
                ann.source_annotation_key,
                ann.source_attachment_key,
                ann.source_parent_key,
                ann.source_version,
                ann.source_modified_at,
                ann.type,
                ann.page_index,
                ann.page_label,
                ann.selected_text,
                ann.comment,
                ann.color,
                ann.sort_index,
                ann.tags_json,
                ann.position_json,
                ann.selector_json,
                ann.sync_state,
                ann.is_readonly,
                ann.created_at,
                ann.updated_at,
                ann.deleted_at,
            ),
        )
        result.inserted += 1
        return

    # -- Existing row — check if content changed ---------------------------
    _CONTENT_FIELDS = [
        ("source_modified_at", ann.source_modified_at),
        ("type", ann.type),
        ("page_index", ann.page_index),
        ("page_label", ann.page_label),
        ("selected_text", ann.selected_text),
        ("comment", ann.comment),
        ("color", ann.color),
        ("sort_index", ann.sort_index),
        ("tags_json", ann.tags_json),
        ("position_json", ann.position_json),
        ("selector_json", ann.selector_json),
    ]

    content_changed = False
    for col, new_val in _CONTENT_FIELDS:
        old_val = existing[col]
        # Normalize comparison: None == "" for TEXT columns
        if old_val != new_val and _str(old_val) != _str(new_val):
            content_changed = True
            break

    was_stale = existing["deleted_at"] is not None
    if not content_changed and not was_stale:
        result.unchanged += 1
        return

    # -- Update content and/or restore from stale --------------------------
    now = _now_utc()
    db_conn.execute(
        """UPDATE annotations SET
            source_modified_at = ?,
            type = ?, page_index = ?, page_label = ?,
            selected_text = ?, comment = ?, color = ?, sort_index = ?,
            tags_json = ?, position_json = ?, selector_json = ?,
            sync_state = ?, is_readonly = ?,
            updated_at = ?, deleted_at = ?
        WHERE id = ?""",
        (
            ann.source_modified_at,
            ann.type,
            ann.page_index,
            ann.page_label,
            ann.selected_text,
            ann.comment,
            ann.color,
            ann.sort_index,
            ann.tags_json,
            ann.position_json,
            ann.selector_json,
            ann.sync_state,
            ann.is_readonly,
            now,
            None,  # deleted_at = NULL (un-stale if it was stale)
            ann.id,
        ),
    )
    result.updated += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def import_zotero_annotations_for_paper(
    zotero_conn: sqlite3.Connection,
    annotations_db_path: Path,
    paper_id: str,
    library_id: int,
    parent_item_id: int,
    parent_item_key: str,
    attachment_item_id: int,
    attachment_item_key: str,
) -> ImportResult:
    """Import Zotero annotations for a single paper into PaperForge.

    Workflow
    --------
    1. Calls ``ensure_schema`` on ``annotations.db``.
    2. Fetches raw annotation rows from the Zotero snapshot for the given
       *attachment_item_id*.
    3. Enriches each row with identity fields (annotation key, tags) via
       Zotero ``items``, ``itemTags``, and ``tags`` tables.
    4. Normalizes each enriched row via ``normalize_zotero_annotation``.
    5. Upserts into ``annotations`` — inserts new rows, updates changed
       rows (preserving ``created_at``, refreshing ``updated_at``).
    6. Marks stale (soft-deletes) any Zotero-sourced rows in the paper
       scope that were NOT in this import.  Stale scope is bounded by
       ``paper_id``, ``source='zotero'``, ``source_library_id``,
       ``source_parent_key``, and ``source_attachment_key``.
    7. Never touches rows with ``source != 'zotero'`` or rows outside the
       paper/library/parent/attachment scope.

    Safety
    ------
    - Writes ONLY to *annotations_db_path* — never to *zotero_conn*.
    - Local PaperForge rows (``source = 'paperforge'``) are never updated,
      stale-marked, or deleted.
    - Imported Zotero rows are marked ``is_readonly = 1``.

    Args:
        zotero_conn: Read-only SQLite connection to a Zotero snapshot.
        annotations_db_path: Path to PaperForge's ``annotations.db``.
        paper_id: PaperForge paper identifier.
        library_id: Zotero library ID (int).
        parent_item_id: Zotero parent item ID (``items.itemID``).
        parent_item_key: Zotero parent item key (``items.key``).
        attachment_item_id: Zotero PDF attachment item ID.
        attachment_item_key: Zotero PDF attachment key (``items.key``).

    Returns:
        ImportResult with per-category counts for CLI ``--json``.
    """
    result = ImportResult()

    db_conn = sqlite3.connect(str(annotations_db_path))
    db_conn.row_factory = sqlite3.Row
    try:
        ensure_schema(db_conn)

        # -- Step 2: Fetch raw Zotero annotation rows ---------------------
        raw_rows = fetch_zotero_item_annotations(
            zotero_conn, parent_item_id=attachment_item_id
        )

        # -- Step 3+4: Enrich + normalize ---------------------------------
        imported_ids: list[str] = []
        for raw_row in raw_rows:
            try:
                enriched = _enrich_annotation(
                    zotero_conn,
                    raw_row,
                    library_id,
                    attachment_item_key,
                    parent_item_key,
                )
                normalized = normalize_zotero_annotation(enriched, paper_id)
            except AnnotationImportError:
                result.skipped += 1
                continue

            # -- Step 5: Upsert -------------------------------------------
            _upsert_annotation(db_conn, normalized, result)
            imported_ids.append(normalized.id)

        # -- Step 6: Stale reconciliation (scope-limited) -----------------
        if imported_ids:
            placeholder_list = ",".join("?" for _ in imported_ids)
            now = _now_utc()
            cursor = db_conn.execute(
                f"""UPDATE annotations SET
                        deleted_at = ?,
                        updated_at = ?
                    WHERE paper_id = ?
                      AND source = 'zotero'
                      AND source_library_id = ?
                      AND source_parent_key = ?
                      AND source_attachment_key = ?
                      AND deleted_at IS NULL
                      AND id NOT IN ({placeholder_list})""",
                (
                    now,
                    now,
                    paper_id,
                    _str(library_id),
                    parent_item_key,
                    attachment_item_key,
                    *imported_ids,
                ),
            )
            result.stale = cursor.rowcount

        db_conn.commit()
    finally:
        db_conn.close()

    return result
