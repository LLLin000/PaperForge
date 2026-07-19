from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from paperforge.memory.builder import compute_hash
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import CURRENT_SCHEMA_VERSION, get_schema_version
from paperforge.worker.asset_index import read_index
from paperforge.worker.asset_state import compute_health
from paperforge.query_planning import classify_signals

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
    keys = row.keys() if hasattr(row, "keys") else row
    entry = {k: row[k] for k in keys}
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


def _coverage_entry(row, *, matched_by: str, matched_title_tokens: int, title_token_total: int, matched_author: bool, matched_year: bool):
    entry = _entry_from_row(row)
    entry["matched_by"] = matched_by
    entry["matched_author"] = matched_author
    entry["matched_year"] = matched_year
    entry["matched_title_tokens"] = f"{matched_title_tokens}/{title_token_total}"
    entry["coverage_score"] = int(matched_author) + int(matched_year) + matched_title_tokens
    return entry


def _lookup_exact_identifiers(conn, signals) -> list[dict]:
    for field in ("doi", "zotero_key", "citation_key"):
        val = getattr(signals, field, None)
        if not val:
            continue
        row = conn.execute(
            f"SELECT * FROM papers WHERE LOWER({field}) = LOWER(?)",
            (val,),
        ).fetchone()
        if row:
            return [_coverage_entry(row, matched_by=field, matched_title_tokens=0, title_token_total=0, matched_author=False, matched_year=False)]
    return []


def _lookup_author_year(conn, signals) -> list[dict]:
    if not signals.author_tokens or not signals.year_tokens:
        return []
    author = signals.author_tokens[0]
    year = signals.year_tokens[0]
    rows = conn.execute(
        "SELECT * FROM papers WHERE LOWER(first_author) LIKE LOWER(?) AND year = ? LIMIT 20",
        (f"%{author}%", str(year)),
    ).fetchall()
    out = []
    for row in rows:
        matched_tokens = sum(1 for t in signals.title_like_tokens if t.lower() in (row["title"] or "").lower())
        out.append(_coverage_entry(
            row,
            matched_by="author+year",
            matched_title_tokens=matched_tokens,
            title_token_total=len(signals.title_like_tokens),
            matched_author=True,
            matched_year=True,
        ))
    return out


def _lookup_author_title(conn, signals) -> list[dict]:
    if not signals.author_tokens or not signals.title_like_tokens:
        return []
    author = signals.author_tokens[0]
    token = signals.title_like_tokens[0]
    rows = conn.execute(
        "SELECT * FROM papers WHERE LOWER(first_author) LIKE LOWER(?) AND LOWER(title) LIKE LOWER(?) LIMIT 20",
        (f"%{author}%", f"%{token}%"),
    ).fetchall()
    out = []
    for row in rows:
        matched_tokens = sum(1 for t in signals.title_like_tokens if t.lower() in (row["title"] or "").lower())
        year_match = bool(signals.year_tokens and str(signals.year_tokens[0]) == str(row["year"]))
        out.append(_coverage_entry(
            row,
            matched_by="author+title",
            matched_title_tokens=matched_tokens,
            title_token_total=len(signals.title_like_tokens),
            matched_author=True,
            matched_year=year_match,
        ))
    return out


def _lookup_year_title(conn, signals) -> list[dict]:
    if not signals.year_tokens or not signals.title_like_tokens:
        return []
    year = signals.year_tokens[0]
    token = signals.title_like_tokens[0]
    rows = conn.execute(
        "SELECT * FROM papers WHERE year = ? AND LOWER(title) LIKE LOWER(?) LIMIT 20",
        (str(year), f"%{token}%"),
    ).fetchall()
    out = []
    for row in rows:
        matched_tokens = sum(1 for t in signals.title_like_tokens if t.lower() in (row["title"] or "").lower())
        author_match = bool(signals.author_tokens and signals.author_tokens[0].lower() in (row["first_author"] or "").lower())
        out.append(_coverage_entry(
            row,
            matched_by="year+title",
            matched_title_tokens=matched_tokens,
            title_token_total=len(signals.title_like_tokens),
            matched_author=author_match,
            matched_year=True,
        ))
    return out


def _lookup_relaxed_title_subsets(conn, signals) -> list[dict]:
    if not signals.title_like_tokens:
        return []
    seen_keys: set[str] = set()
    out = []
    for token in signals.title_like_tokens:
        rows = conn.execute(
            "SELECT * FROM papers WHERE LOWER(title) LIKE LOWER(?) LIMIT 10",
            (f"%{token}%",),
        ).fetchall()
        for row in rows:
            key = row["zotero_key"]
            if key in seen_keys:
                continue
            seen_keys.add(key)
            matched_tokens = sum(1 for t in signals.title_like_tokens if t.lower() in (row["title"] or "").lower())
            author_match = bool(signals.author_tokens and signals.author_tokens[0].lower() in (row["first_author"] or "").lower())
            year_match = bool(signals.year_tokens and str(signals.year_tokens[0]) == str(row["year"]))
            out.append(_coverage_entry(
                row,
                matched_by="relaxed_title",
                matched_title_tokens=matched_tokens,
                title_token_total=len(signals.title_like_tokens),
                matched_author=author_match,
                matched_year=year_match,
            ))
    return out


def _lookup_alias(conn, query: str) -> list[dict]:
    q = query.strip()
    rows = conn.execute(
        """SELECT p.* FROM papers p
           JOIN paper_aliases a ON a.paper_id = p.zotero_key
           WHERE a.alias_norm LIKE '%' || LOWER(?) || '%'
           LIMIT 20""",
        (q,),
    ).fetchall()
    return [_coverage_entry(r, matched_by="alias", matched_title_tokens=0, title_token_total=0, matched_author=False, matched_year=False) for r in rows]


def _dedupe_and_sort_candidates(candidates: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for c in candidates:
        key = c.get("zotero_key", "")
        if key and key not in seen:
            seen.add(key)
            out.append(c)
    out.sort(key=lambda x: x.get("coverage_score", 0), reverse=True)
    return out


def lookup_paper(conn, query: str) -> list[dict]:
    signals = classify_signals(query)
    exact_candidates = _lookup_exact_identifiers(conn, signals)
    if exact_candidates:
        return exact_candidates
    candidates: list[dict] = []
    candidates.extend(_lookup_author_year(conn, signals))
    candidates.extend(_lookup_author_title(conn, signals))
    candidates.extend(_lookup_year_title(conn, signals))
    candidates.extend(_lookup_relaxed_title_subsets(conn, signals))
    candidates.extend(_lookup_alias(conn, query))
    return _dedupe_and_sort_candidates(candidates)


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
