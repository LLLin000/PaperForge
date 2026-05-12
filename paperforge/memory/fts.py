from __future__ import annotations

import sqlite3


def search_papers(conn: sqlite3.Connection, query: str, limit: int = 20,
                  domain: str = "", year_from: int = 0, year_to: int = 0,
                  ocr_status: str = "", deep_status: str = "",
                  lifecycle: str = "", next_step: str = "") -> list[dict]:
    """Full-text search across papers with optional filters.

    Uses FTS5 for relevance-ranked results with optional column filters.
    """
    conditions = ["paper_fts MATCH ?"]
    params: list = [query]

    if domain:
        conditions.append("p.domain = ?")
        params.append(domain)
    if year_from:
        conditions.append("CAST(p.year AS INTEGER) >= ?")
        params.append(year_from)
    if year_to:
        conditions.append("CAST(p.year AS INTEGER) <= ?")
        params.append(year_to)
    if ocr_status:
        conditions.append("p.ocr_status = ?")
        params.append(ocr_status)
    if deep_status:
        conditions.append("p.deep_reading_status = ?")
        params.append(deep_status)
    if lifecycle:
        conditions.append("p.lifecycle = ?")
        params.append(lifecycle)
    if next_step:
        conditions.append("p.next_step = ?")
        params.append(next_step)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT p.zotero_key, p.citation_key, p.title, p.year, p.doi,
               p.first_author, p.journal, p.domain, p.lifecycle,
               p.ocr_status, p.deep_reading_status, p.next_step,
               p.abstract,
               rank
        FROM paper_fts f
        JOIN papers p ON p.zotero_key = f.zotero_key
        WHERE {where}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
