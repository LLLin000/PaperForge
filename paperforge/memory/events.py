from __future__ import annotations

import json
from pathlib import Path

from paperforge.memory.db import get_connection, get_memory_db_path


def write_reading_note(vault: Path, paper_id: str, section: str,
                       excerpt: str, usage: str = "", note: str = "",
                       context: str = "", project: str = "",
                       tags: list[str] | None = None) -> bool:
    """Record a reading note in paper_events."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False

    payload = {
        "section": section,
        "excerpt": excerpt,
        "usage": usage,
        "note": note,
        "context": context,
        "project": project,
        "tags": tags or [],
    }
    conn = get_connection(db_path, read_only=False)
    try:
        conn.execute(
            """INSERT INTO paper_events (paper_id, event_type, payload_json)
               VALUES (?, 'reading_note', ?)""",
            (paper_id, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def export_reading_log(vault: Path, since: str = "", limit: int = 50) -> list[dict]:
    """Export reading notes as a list of dicts, ordered by created_at DESC."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return []

    conn = get_connection(db_path, read_only=True)
    try:
        query = """
            SELECT e.created_at, e.paper_id, e.payload_json,
                   p.citation_key, p.title, p.year, p.first_author
            FROM paper_events e
            JOIN papers p ON p.zotero_key = e.paper_id
            WHERE e.event_type = 'reading_note'
        """
        params = []
        if since:
            query += " AND e.created_at >= ?"
            params.append(since)
        query += " ORDER BY e.created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            results.append({
                "created_at": row["created_at"],
                "paper_id": row["paper_id"],
                "citation_key": row["citation_key"],
                "title": row["title"],
                "year": row["year"],
                "first_author": row["first_author"],
                "section": payload.get("section", ""),
                "excerpt": payload.get("excerpt", ""),
                "usage": payload.get("usage", ""),
                "note": payload.get("note", ""),
            })
        return results
    finally:
        conn.close()


def write_correction_note(vault: Path, paper_id: str, original_id: str,
                          correction: str, reason: str = "") -> bool:
    """Record a correction note for a prior reading_note event."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False

    payload = {
        "original_id": original_id,
        "correction": correction,
        "reason": reason,
    }
    conn = get_connection(db_path, read_only=False)
    try:
        conn.execute(
            """INSERT INTO paper_events (paper_id, event_type, payload_json)
               VALUES (?, 'correction_note', ?)""",
            (paper_id, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
