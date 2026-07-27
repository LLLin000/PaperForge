from __future__ import annotations

import json
import logging
from pathlib import Path

from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider
from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path

logger = logging.getLogger(__name__)

RETRIEVAL_COLLECTIONS = ["paperforge_fulltext", "paperforge_body", "paperforge_objects"]

_VEC_SOURCE_MAP = {
    "vec_body": "body",
    "vec_objects": "object",
}

_VEC_META_MAP = {
    "vec_body": "vec_body_meta",
    "vec_objects": "vec_objects_meta",
}



def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search chunks via vec0 k-NN on vec_fulltext. Returns list with metadata and similarity scores."""
    provider = OpenAICompatibleProvider(vault)
    query_embedding = provider.encode_single(query)
    n = limit * 3 if expand else limit

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=True)
    try:
        ensure_vec_extension(conn)
        q_emb_json = json.dumps(query_embedding)
        rows = conn.execute(
            """SELECT m.paper_id, m.chunk_index, m.text, v.distance
               FROM vec_fulltext v
               JOIN vec_fulltext_meta m ON v.rowid = m.rowid
               WHERE v.embedding MATCH ? AND v.k = ?""",
            (q_emb_json, n),
        ).fetchall()
    finally:
        conn.close()

    results = []
    for row in rows:
        results.append(
            {
                "paper_id": row[0],
                "section": "Text",
                "page_number": 1,
                "chunk_index": row[1],
                "chunk_text": row[2],
                "score": round(1.0 - row[3], 4),
            }
        )
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def enrich_retrieval_hit(conn, *, paper_id: str, source_kind: str, unit_id: str) -> dict:
    """Return structural coordinates for any retrieval hit.

    Used by both merge_retrieve() and hybrid_search().
    """
    enrichment: dict = {"structure_resolved": True}
    if source_kind == "body":
        row = conn.execute(
            "SELECT node_id, section_path_json, section_title, section_level, part_ordinal, unit_kind "
            "FROM body_units WHERE unit_id=? AND paper_id=?",
            (unit_id, paper_id),
        ).fetchone()
        if row:
            enrichment["node_id"] = row["node_id"]
            enrichment["structure_path"] = json.loads(row["section_path_json"]) if row["section_path_json"] else []
            enrichment["section_title"] = row["section_title"]
            enrichment["section_level"] = row["section_level"]
            enrichment["part_ordinal"] = row["part_ordinal"]
            enrichment["unit_kind"] = row["unit_kind"]
        else:
            enrichment["node_id"] = ""
            enrichment["structure_path"] = []
            enrichment["structure_resolved"] = False
    elif source_kind == "object":
        row = conn.execute(
            "SELECT node_id, section_path_json, object_kind "
            "FROM object_units WHERE unit_id=? AND paper_id=?",
            (unit_id, paper_id),
        ).fetchone()
        if row:
            enrichment["node_id"] = row["node_id"]
            enrichment["structure_path"] = json.loads(row["section_path_json"]) if row["section_path_json"] else []
            enrichment["object_kind"] = row["object_kind"]
        else:
            enrichment["node_id"] = ""
            enrichment["structure_path"] = []
            enrichment["structure_resolved"] = False

    # Read structure_version from DB manifest
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (f"manifest:{paper_id}",)).fetchone()
    if row:
        try:
            manifest = json.loads(row[0])
            enrichment["structure_version"] = str(manifest.get("ocr_result_hash", ""))
        except (TypeError, ValueError, KeyError):
            enrichment["structure_version"] = ""
    else:
        enrichment["structure_version"] = ""

    return enrichment


def merge_retrieve(vault: Path, query: str, limit: int = 5, expand: bool = True, paper_id: str | None = None) -> list[dict]:
    """Query vec0 tables, enrich with structural coordinates, dedup by unit_id."""
    provider = OpenAICompatibleProvider(vault)
    q_emb = provider.encode_single(query)
    n = limit * 2 if expand else limit

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=True)
    try:
        ensure_vec_extension(conn)
        q_emb_json = json.dumps(q_emb)

        all_results: list[dict] = []
        for vec_table, source in _VEC_SOURCE_MAP.items():
            meta_table = _VEC_META_MAP[vec_table]
            try:
                base_sql = f"""SELECT m.paper_id, m.unit_id, m.text, v.distance
                               FROM {vec_table} v
                               JOIN {meta_table} m ON v.rowid = m.rowid
                               WHERE v.embedding MATCH ? AND v.k = ? AND m.unit_id <> ''"""
                params: list = [q_emb_json, n]
                if paper_id:
                    base_sql += f""" AND v.rowid IN (
                        SELECT rowid FROM {meta_table}
                        WHERE paper_id = ? AND unit_id <> ''
                    )"""
                    params.append(paper_id)
                base_sql += " ORDER BY v.distance"
                rows = conn.execute(base_sql, params).fetchall()
            except Exception as exc:
                logger.warning("merge_retrieve: %s query failed: %s", vec_table, exc)
                continue

            for row in rows:
                all_results.append(
                    {
                        "paper_id": row[0],
                        "unit_id": row[1],
                        "section_path": "",
                        "chunk_text": row[2],
                        "score": round(1.0 - row[3], 4),
                        "source": source,
                        "object_kind": "",
                        "object_label": "",
                    }
                )

        all_results.sort(key=lambda r: r["score"], reverse=True)
        seen: set = set()
        per_paper: dict[str, int] = {}
        merged: list[dict] = []
        for r in all_results:
            dedupe_key = (r["source"], r["unit_id"])
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            pid = r["paper_id"]
            if per_paper.get(pid, 0) >= 2:
                continue
            per_paper[pid] = per_paper.get(pid, 0) + 1
            # Enrich with structural coordinates
            enrichment = enrich_retrieval_hit(conn, paper_id=pid, source_kind=r["source"], unit_id=r["unit_id"])
            r.update(enrichment)
            merged.append(r)
            if len(merged) >= limit:
                break
        return merged
    finally:
        conn.close()
def hybrid_search(vault: Path, query: str, limit: int = 10, paper_id: str | None = None) -> list[dict]:
    """Hybrid search: BM25 FTS5 + vec0 k-NN with query rewrite."""
    from paperforge.embedding.query_rewrite import expand_query as do_expand

    query_variants = do_expand(query)
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=True)
    try:
        ensure_vec_extension(conn)
        bm25_results: list[dict] = _bm25_search(conn, query_variants, limit * 2, paper_id=paper_id)
        vec_results: list[dict] = _vec_search(conn, vault, query, limit * 2, paper_id=paper_id)
        fused = _fuse_results(bm25_results, vec_results, limit)

        # Enrich fused results with structural coordinates
        for r in fused:
            enrichment = enrich_retrieval_hit(
                conn, paper_id=r.get("paper_id", ""), source_kind=r.get("source", "body"), unit_id=r.get("unit_id", "")
            )
            r.update(enrichment)

        return fused
    finally:
        conn.close()
def _bm25_search(
    conn: sqlite3.Connection, query_variants: list[str], limit: int, paper_id: str | None = None
) -> list[dict]:
    """Run BM25 (FTS5) search across body_units_fts for each query variant.

    Returns results with BM25 scores normalized to [0, 1].
    """
    seen: set[str] = set()
    results: list[dict] = []

    for qv in query_variants:
        try:
            params = [qv]
            sql = """SELECT
                    bu.unit_id,
                    bu.paper_id,
                    bu.section_path,
                    bu.section_title,
                    bu.unit_text,
                    p.title,
                    p.first_author,
                    p.year,
                    p.journal,
                    p.domain,
                    rank as bm25_raw
                   FROM body_units_fts bu_fts
                   JOIN body_units bu ON bu_fts.unit_id = bu.unit_id
                   JOIN papers p ON bu.paper_id = p.zotero_key
                   WHERE body_units_fts MATCH ?"""
            if paper_id:
                sql += " AND bu.paper_id = ?"
                params.append(paper_id)
            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        except Exception as exc:
            logger = logging.getLogger(__name__)
            logger.warning("BM25 query failed for %r: %s", qv, exc)
            continue

        for row in rows:
            key = (row["unit_id"], row["paper_id"])
            if key in seen:
                continue
            seen.add(key)

            bm25_raw = float(row["bm25_raw"])
            # Normalize: invert sign so positive = better, then squash to [0, 1]
            bm25_norm = 1.0 - (1.0 / (1.0 + abs(bm25_raw))) if bm25_raw != 0 else 0.0

            results.append(
                {
                    "unit_id": row["unit_id"],
                    "paper_id": row["paper_id"],
                    "source": "body",
                    "first_author": row["first_author"],
                    "year": row["year"],
                    "journal": row["journal"],
                    "domain": row["domain"],
                    "text": row["unit_text"],
                    "heading": row["section_title"],
                    "bm25_score": round(bm25_norm, 4),
                    "vec_score": 0.0,
                }
            )

    results.sort(key=lambda r: r["bm25_score"], reverse=True)
    return results[:limit]


def _vec_search(
    conn: sqlite3.Connection, vault: Path, query: str, limit: int, paper_id: str | None = None
) -> list[dict]:
    """Run vec0 k-NN on vec_body and vec_objects with unit_id.

    Gracefully returns empty list when vec0 extension or tables are missing.
    Supports paper-scoped filtering via rowid pre-filter.
    """
    logger = logging.getLogger(__name__)
    provider = OpenAICompatibleProvider(vault)
    q_emb = provider.encode_single(query)
    q_emb_json = json.dumps(q_emb)

    results: list[dict] = []
    for vec_table, source in _VEC_SOURCE_MAP.items():
        meta_table = _VEC_META_MAP[vec_table]
        try:
            base_sql = f"""SELECT m.paper_id, m.unit_id, m.text, v.distance
                           FROM {vec_table} v
                           JOIN {meta_table} m ON v.rowid = m.rowid
                           WHERE v.embedding MATCH ? AND v.k = ? AND m.unit_id <> ''"""
            params: list = [q_emb_json, limit]
            if paper_id:
                base_sql += f""" AND v.rowid IN (
                    SELECT rowid FROM {meta_table}
                    WHERE paper_id = ? AND unit_id <> ''
                )"""
                params.append(paper_id)
            base_sql += " ORDER BY v.distance"
            rows = conn.execute(base_sql, params).fetchall()
        except Exception as exc:
            logger.warning("vec0 query failed for %s: %s", vec_table, exc)
            continue

        for row in rows:
            vec_sim = round(1.0 - row[3], 4)
            results.append(
                {
                    "paper_id": row[0],
                    "unit_id": row[1],
                    "source": source,
                    "text": row[2] or "",
                    "vec_score": vec_sim,
                }
            )

    return results

def _fuse_results(
    bm25_results: list[dict], vec_results: list[dict], limit: int
) -> list[dict]:
    """Fuse BM25 and vec0 results with combined score.

    Fusion formula: combined = 0.3 * bm25_norm + 0.7 * vec_norm.
    Deduplicates by (source_kind, unit_id).
    """
    # Build vec lookup: (source, unit_id) -> vec_score
    vec_lookup: dict[tuple[str, str], float] = {}
    for vr in vec_results:
        key = (vr.get("source", ""), vr.get("unit_id", ""))
        if key not in vec_lookup or vr["vec_score"] > vec_lookup[key]:
            vec_lookup[key] = vr["vec_score"]

    has_vec = bool(vec_results)

    for br in bm25_results:
        bm25_norm = br["bm25_score"]
        key = ("body", br.get("unit_id", ""))

        if has_vec and key in vec_lookup:
            vec_raw = vec_lookup[key]
            vec_norm = 1.0 - (1.0 / (1.0 + vec_raw)) if vec_raw > 0 else 0.0
            br["vec_score"] = round(vec_raw, 4)
            combined = 0.3 * bm25_norm + 0.7 * vec_norm
            br["score"] = round(combined, 4)
        else:
            br["vec_score"] = 0.0
            br["score"] = round(bm25_norm, 4)

    bm25_results.sort(key=lambda r: r["score"], reverse=True)

    # Final dedup and cap by (source, unit_id)
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for r in bm25_results:
        key = ("body", r.get("unit_id", ""))
        if key in seen:
            continue
        seen.add(key)
        r["matched_terms"] = ""
        out.append(r)
        if len(out) >= limit:
            break

    # If BM25 was empty but vec had results, synthesize entries
    if not out and has_vec:
        seen_v: set[tuple[str, str]] = set()
        for vr in vec_results:
            key = (vr.get("source", ""), vr.get("unit_id", ""))
            if key in seen_v:
                continue
            seen_v.add(key)
            vec_raw = vr["vec_score"]
            vec_norm = 1.0 - (1.0 / (1.0 + vec_raw)) if vec_raw > 0 else 0.0
            out.append(
                {
                    "paper_id": vr["paper_id"],
                    "source": vr.get("source", ""),
                    "unit_id": vr.get("unit_id", ""),
                    "text": vr.get("text", ""),
                    "vec_score": round(vec_raw, 4),
                    "score": round(vec_norm, 4),
                    "matched_terms": "",
                    "heading": "",
                    "title": "",
                    "first_author": "",
                    "year": "",
                    "journal": "",
                    "domain": "",
                }
            )
            if len(out) >= limit:
                break

    return out
