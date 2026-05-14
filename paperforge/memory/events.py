from __future__ import annotations

import json
from pathlib import Path

from paperforge.memory.db import get_connection, get_memory_db_path


def write_reading_note(vault: Path, paper_id: str, section: str,
                       excerpt: str, usage: str = "", note: str = "",
                       context: str = "", project: str = "",
                       tags: list[str] | None = None) -> bool:
    """DEPRECATED: Wraps append_reading_note(). Use permanent.py directly.

    Kept for backward compatibility. Does NOT write to paper_events anymore.
    """
    from paperforge.memory.permanent import append_reading_note
    result = append_reading_note(
        vault, paper_id, section, excerpt,
        usage=usage, context=context, note=note,
        project=project, tags=tags,
    )
    return bool(result.get("ok"))


def export_reading_log(vault: Path, since: str = "", limit: int = 50) -> list[dict]:
    """Export reading notes from JSONL (source of truth)."""
    from paperforge.memory.permanent import read_all_reading_notes
    
    notes = read_all_reading_notes(vault)
    
    # Optionally enrich with papers metadata from DB
    db_path = get_memory_db_path(vault)
    paper_cache = {}
    if db_path.exists():
        conn = get_connection(db_path, read_only=True)
        try:
            rows = conn.execute(
                "SELECT zotero_key, citation_key, title, year, first_author FROM papers"
            ).fetchall()
            for r in rows:
                paper_cache[r["zotero_key"]] = dict(r)
        finally:
            conn.close()
    
    results = []
    for n in notes:
        created = n.get("created_at", "")
        if since and created < since:
            continue
        pid = n.get("paper_id", "")
        meta = paper_cache.get(pid, {})
        results.append({
            "created_at": created,
            "paper_id": pid,
            "citation_key": meta.get("citation_key", ""),
            "title": meta.get("title", ""),
            "year": meta.get("year", ""),
            "first_author": meta.get("first_author", ""),
            "section": n.get("section", ""),
            "excerpt": n.get("excerpt", ""),
            "usage": n.get("usage", ""),
            "note": n.get("note", ""),
        })
    
    # Sort DESC by created_at, apply limit
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results[:limit]


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
