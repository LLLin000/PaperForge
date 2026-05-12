from __future__ import annotations

import json
import logging
from pathlib import Path

from paperforge.memory.builder import compute_hash
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import CURRENT_SCHEMA_VERSION, get_schema_version
from paperforge.worker.asset_index import read_index
from paperforge.worker.asset_state import compute_health

logger = logging.getLogger(__name__)


def get_memory_status(vault: Path) -> dict:
    """Check paperforge.db health and staleness.

    Returns a dict with: db_exists, schema_ok, fresh, count_match,
    paper_count_db, paper_count_index, needs_rebuild.
    """
    db_path = get_memory_db_path(vault)
    result = {
        "db_exists": db_path.exists(),
        "schema_ok": False,
        "fresh": False,
        "hash_match": False,
        "count_match": False,
        "paper_count_db": 0,
        "paper_count_index": 0,
        "needs_rebuild": True,
    }
    if not db_path.exists():
        return result

    conn = get_connection(db_path, read_only=True)
    try:
        stored_version = get_schema_version(conn)
        result["schema_ok"] = stored_version == CURRENT_SCHEMA_VERSION
        row = conn.execute("SELECT COUNT(*) as cnt FROM papers").fetchone()
        result["paper_count_db"] = row["cnt"] if row else 0
        stored_hash_row = conn.execute(
            "SELECT value FROM meta WHERE key = 'canonical_index_hash'"
        ).fetchone()
        stored_hash = stored_hash_row["value"] if stored_hash_row else ""
    except Exception:
        return result
    finally:
        conn.close()

    envelope = read_index(vault)
    if envelope is not None:
        # Handle legacy format (bare list)
        if isinstance(envelope, list):
            items = envelope
            paper_count = len(items)
            index_hash = compute_hash(items)
        else:
            items = envelope.get("items", [])
            paper_count = envelope.get("paper_count", 0)
            index_hash = compute_hash(items)
        result["paper_count_index"] = paper_count

        # Compare stored hash with computed hash
        result["hash_match"] = stored_hash == index_hash

        result["count_match"] = (
            result["paper_count_db"] == result["paper_count_index"]
        )

    result["fresh"] = (
        result["schema_ok"]
        and result["count_match"]
        and result.get("hash_match", False)
    )
    result["needs_rebuild"] = not result["fresh"]
    return result


def _entry_from_row(row) -> dict:
    """Reconstruct an entry dict from a papers row (sqlite3.Row)."""
    entry = {k: row[k] for k in row}
    for key in ("has_pdf", "do_ocr", "analyze"):
        if key in entry and entry[key] is not None:
            entry[key] = bool(entry[key])
    for key in ("authors_json", "collections_json"):
        if key in entry and entry[key]:
            try:
                entry[key[:-5]] = json.loads(entry[key])
                del entry[key]
            except json.JSONDecodeError:
                logger.warning(
                    "Corrupted JSON in column %s for paper %s",
                    key, entry.get("zotero_key", "?"),
                )
    return entry


def lookup_paper(conn, query: str) -> list[dict]:
    """Multi-strategy lookup. Returns list of matching paper dicts."""
    q = query.strip()

    for lookup_col in ("zotero_key", "citation_key", "doi"):
        row = conn.execute(
            f"SELECT * FROM papers WHERE LOWER({lookup_col}) = LOWER(?)",
            (q,),
        ).fetchone()
        if row:
            return [_entry_from_row(row)]

    rows = conn.execute(
        """SELECT * FROM papers
           WHERE LOWER(title) LIKE '%' || LOWER(?) || '%'
           LIMIT 20""",
        (q,),
    ).fetchall()
    if rows:
        return [_entry_from_row(r) for r in rows]

    rows = conn.execute(
        """SELECT p.* FROM papers p
           JOIN paper_aliases a ON a.paper_id = p.zotero_key
           WHERE a.alias_norm LIKE '%' || LOWER(?) || '%'
           LIMIT 20""",
        (q,),
    ).fetchall()
    return [_entry_from_row(r) for r in rows]


def get_paper_assets(conn, zotero_key: str) -> list[dict]:
    rows = conn.execute(
        "SELECT asset_type, path, exists_on_disk FROM paper_assets WHERE paper_id = ?",
        (zotero_key,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_paper_status(vault: Path, query: str) -> dict | None:
    """Full paper status lookup. Returns dict or None if not found.

    If multiple candidates found, returns a candidate list without full status.
    """
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        entries = lookup_paper(conn, query)
        if not entries:
            return None

        # Multiple candidates -> return candidate list only (no full status)
        if len(entries) > 1:
            return {
                "resolved": False,
                "candidates": [
                    {
                        "zotero_key": e.get("zotero_key"),
                        "title": e.get("title"),
                        "year": e.get("year"),
                        "citation_key": e.get("citation_key"),
                        "lifecycle": e.get("lifecycle"),
                    }
                    for e in entries
                ],
            }

        entry = entries[0]
        assets = get_paper_assets(conn, entry["zotero_key"])
        entry["health"] = compute_health(entry)
        entry["assets"] = assets
        entry["resolved"] = True

        next_step = entry.get("next_step", "")
        zk = entry.get("zotero_key", "")
        if next_step == "/pf-deep":
            entry["recommended_action"] = f"/pf-deep {zk}"
        elif next_step == "ocr":
            entry["recommended_action"] = f"paperforge ocr --key {zk}"
        elif next_step == "sync":
            entry["recommended_action"] = "paperforge sync"
        else:
            entry["recommended_action"] = None

        return entry
    finally:
        conn.close()
