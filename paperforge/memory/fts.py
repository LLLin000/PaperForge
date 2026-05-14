from __future__ import annotations

import re
import sqlite3


def tokenize_for_fts(q: str) -> str:
    """Extract alphanumeric + CJK tokens and quote for safe FTS."""
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", q)
    if not tokens:
        return q
    return " OR ".join(f'"{t}"' for t in tokens)


def search_papers(conn: sqlite3.Connection, query: str, limit: int = 20,
                  domain: str = "", year_from: int = 0, year_to: int = 0,
                  ocr_status: str = "", deep_status: str = "",
                  lifecycle: str = "", next_step: str = "") -> list[dict]:
    """Full-text search with safe fallback for special characters."""

    filter_conditions = []
    filter_params = []

    if domain:
        filter_conditions.append("p.domain = ?")
        filter_params.append(domain)
    if year_from:
        filter_conditions.append("CAST(p.year AS INTEGER) >= ?")
        filter_params.append(year_from)
    if year_to:
        filter_conditions.append("CAST(p.year AS INTEGER) <= ?")
        filter_params.append(year_to)
    if ocr_status:
        filter_conditions.append("p.ocr_status = ?")
        filter_params.append(ocr_status)
    if deep_status:
        filter_conditions.append("p.deep_reading_status = ?")
        filter_params.append(deep_status)
    if lifecycle:
        filter_conditions.append("p.lifecycle = ?")
        filter_params.append(lifecycle)
    if next_step:
        filter_conditions.append("p.next_step = ?")
        filter_params.append(next_step)

    filter_clause = (" AND " + " AND ".join(filter_conditions)) if filter_conditions else ""

    # Level 1: Raw FTS
    try:
        return _fts_query(conn, query, filter_clause, filter_params, limit)
    except sqlite3.OperationalError:
        pass

    # Level 2: Quoted token FTS
    token_query = tokenize_for_fts(query)
    if token_query != query:
        try:
            return _fts_query(conn, token_query, filter_clause, filter_params, limit)
        except sqlite3.OperationalError:
            pass

    # Level 3: LIKE fallback
    return _like_query(conn, query, filter_clause, filter_params, limit)


def _fts_query(conn, query, filter_clause, filter_params, limit):
    sql = f"""
        SELECT p.zotero_key, p.citation_key, p.title, p.year, p.doi,
               p.first_author, p.journal, p.domain, p.lifecycle,
               p.ocr_status, p.deep_reading_status, p.next_step,
               substr(p.abstract, 1, 300) as abstract,
               rank
        FROM paper_fts f
        JOIN papers p ON p.rowid = f.rowid
        WHERE paper_fts MATCH ?{filter_clause}
        ORDER BY rank
        LIMIT ?
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, [query] + filter_params + [limit]).fetchall()
    return [dict(r) for r in rows]


def _like_query(conn, query, filter_clause, filter_params, limit):
    like_param = f"%{query}%"
    sql = f"""
        SELECT p.zotero_key, p.citation_key, p.title, p.year, p.doi,
               p.first_author, p.journal, p.domain, p.lifecycle,
               p.ocr_status, p.deep_reading_status, p.next_step,
               substr(p.abstract, 1, 300) as abstract,
               0 as rank
        FROM papers p
        WHERE (p.title LIKE ? OR p.abstract LIKE ? OR p.doi LIKE ? OR p.citation_key LIKE ?){filter_clause}
        ORDER BY p.year DESC
        LIMIT ?
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, [like_param, like_param, like_param, like_param] + filter_params + [limit]).fetchall()
    return [dict(r) for r in rows]
