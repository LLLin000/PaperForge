"""Annotation CRUD and search/export operations against annotations.db.

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


# ── Queries ──


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
