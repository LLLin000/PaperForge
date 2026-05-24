"""Annotation CRUD, search, and export operations against annotations.db.

Part of the "lightweight embedded service" layer — pure DB operations,
no CLI or network concerns.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Columns that can be safely patched by users
PATCHABLE_COLUMNS = {"comment", "color", "tags_json", "selected_text"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Mutation ──


def mark_deleted(conn, annotation_id: str) -> None:
    """Soft-delete an annotation by id."""
    conn.execute(
        "UPDATE annotations SET deleted_at = ?, updated_at = ? WHERE id = ? AND deleted_at IS NULL",
        (_now(), _now(), annotation_id),
    )


def hard_delete(conn, annotation_id: str) -> None:
    """Permanently delete an annotation by id."""
    conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))


# ── CRUD ──


def create_annotation(
    conn,
    paper_id: str,
    annotation_type: str,
    page_index: int | None = None,
    page_label: str = "",
    selected_text: str = "",
    comment: str = "",
    color: str = "#ffd400",
    sort_index: str = "",
    position_json: dict | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Create a new PaperForge-local annotation."""
    now = _now()
    aid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO annotations (
            id, paper_id, type, page_index, page_label,
            selected_text, comment, color, sort_index,
            tags_json, position_json, source, sync_state,
            is_readonly, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'paperforge', 'local', 0, ?, ?)""",
        (
            aid,
            paper_id,
            annotation_type,
            page_index,
            page_label,
            selected_text,
            comment,
            color,
            sort_index,
            json.dumps(tags or [], ensure_ascii=False),
            json.dumps(position_json or {}, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    return get_annotation(conn, aid)


def patch_annotation(
    conn,
    annotation_id: str,
    **kwargs: Any,
) -> dict:
    """Patch editable fields on an annotation.

    Raises ValueError if the annotation is readonly or not found.
    """
    existing = get_annotation(conn, annotation_id)
    if existing is None:
        raise ValueError(f"Annotation not found: {annotation_id}")
    if existing.get("is_readonly"):
        raise ValueError(f"Cannot edit readonly annotation: {annotation_id}")

    updates = {k: v for k, v in kwargs.items() if k in PATCHABLE_COLUMNS and v is not None}
    if not updates:
        return existing

    updates["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [annotation_id]
    conn.execute(f"UPDATE annotations SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return get_annotation(conn, annotation_id)


def delete_annotation(conn, annotation_id: str) -> None:
    """Soft-delete an annotation by id. Raises ValueError if not found."""
    existing = get_annotation(conn, annotation_id)
    if existing is None:
        raise ValueError(f"Annotation not found: {annotation_id}")
    mark_deleted(conn, annotation_id)
    conn.commit()


# ── Queries ──


def get_annotation(conn, annotation_id: str) -> dict | None:
    """Fetch a single annotation by id. Returns None if not found."""
    row = conn.execute(
        "SELECT * FROM annotations WHERE id = ?", (annotation_id,)
    ).fetchone()
    return dict(row) if row else None


def list_annotations(
    conn,
    paper_id: str = "",
    page_index: int | None = None,
    annotation_type: str = "",
    limit: int = 100,
) -> list[dict]:
    """List annotations, optionally filtered."""
    clauses = ["deleted_at IS NULL"]
    params: list[Any] = []

    if paper_id:
        clauses.append("paper_id = ?")
        params.append(paper_id)
    if page_index is not None:
        clauses.append("page_index = ?")
        params.append(page_index)
    if annotation_type:
        clauses.append("type = ?")
        params.append(annotation_type)

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT * FROM annotations WHERE {where} ORDER BY sort_index LIMIT ?",
        [*params, limit],
    ).fetchall()
    return [dict(r) for r in rows]


# ── Export ──


def export_annotations_json(
    conn,
    paper_id: str = "",
    limit: int = 1000,
) -> str:
    """Export annotations for a paper as a JSON string."""
    anns = list_annotations(conn, paper_id=paper_id, limit=limit)

    def _clean(a: dict) -> dict:
        return {k: v for k, v in a.items() if k not in ("id",)}

    return json.dumps([_clean(a) for a in anns], ensure_ascii=False, indent=2)


def export_annotations_markdown(
    conn,
    paper_id: str = "",
    limit: int = 1000,
) -> str:
    """Export annotations for a paper as formatted Markdown."""
    anns = list_annotations(conn, paper_id=paper_id, limit=limit)
    lines = [f"# Annotations for {paper_id}\n"]

    for i, ann in enumerate(anns, 1):
        lines.append(f"## {i}. {ann['type'].title()}")
        if ann.get("page_label") or ann.get("page_index") is not None:
            pl = ann["page_label"] or str(ann["page_index"] + 1)
            lines.append(f"**Page:** {pl}")
        if ann.get("selected_text"):
            lines.append(f"\n> {ann['selected_text']}")
        if ann.get("comment"):
            lines.append(f"\n{ann['comment']}")
        if ann.get("color"):
            lines.append(f"\n*Color: {ann['color']}*")
        lines.append("")

    return "\n".join(lines)
