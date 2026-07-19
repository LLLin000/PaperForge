from __future__ import annotations

import json
import logging
from pathlib import Path

from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider
from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path

logger = logging.getLogger(__name__)

RETRIEVAL_COLLECTIONS = ["paperforge_fulltext", "paperforge_body", "paperforge_objects"]

# vec0 table name -> source label
_VEC_SOURCE_MAP = {
    "vec_fulltext": "legacy_chunk",
    "vec_body": "body_unit",
    "vec_objects": "object_unit",
}

# vec0 table name -> companion meta table name
_VEC_META_MAP = {
    "vec_fulltext": "vec_fulltext_meta",
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


def merge_retrieve(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Query all vec0 tables, merge with unit-level dedup and per-paper cap."""
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
                rows = conn.execute(
                    f"""SELECT m.paper_id, m.chunk_index, m.text, v.distance
                        FROM {vec_table} v
                        JOIN {meta_table} m ON v.rowid = m.rowid
                        WHERE v.embedding MATCH ? AND v.k = ?""",
                    (q_emb_json, n),
                ).fetchall()
            except Exception as exc:
                logger.warning("merge_retrieve: %s query failed: %s", vec_table, exc)
                continue

            for row in rows:
                all_results.append(
                    {
                        "paper_id": row[0],
                        "section_path": "",
                        "chunk_text": row[2],
                        "score": round(1.0 - row[3], 4),
                        "source": source,
                        "unit_id": row[1],
                        "object_kind": "",
                        "object_label": "",
                    }
                )

        all_results.sort(key=lambda r: r["score"], reverse=True)
        seen: set = set()
        per_paper: dict[str, int] = {}
        merged: list[dict] = []
        for r in all_results:
            dedupe_key = (
                (r["source"], r["unit_id"]) if r.get("unit_id") else (r["source"], r["paper_id"], hash(r["chunk_text"]))
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            pid = r["paper_id"]
            if per_paper.get(pid, 0) >= 2:
                continue
            per_paper[pid] = per_paper.get(pid, 0) + 1
            merged.append(r)
            if len(merged) >= limit:
                break
        return merged
    finally:
        conn.close()


def hybrid_search(vault: Path, query: str, limit: int = 10) -> list[dict]:
    """Hybrid search: BM25 FTS5 + vec0 k-NN with query rewrite.

    Runs on body_units_fts (BM25) and vec_body/vec_objects (k-NN),
    fuses scores (0.3 BM25 + 0.7 vec), and returns deduplicated results
    with text snippets and source types.

    Falls back to BM25-only when vec0 tables are unavailable or empty.
    """
    logger = logging.getLogger(__name__)
    from paperforge.embedding.query_rewrite import expand_query as do_expand

    query_variants = do_expand(query)
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=True)
    try:
        ensure_vec_extension(conn)

        # ── Step 2: BM25 FTS5 ──────────────────────────────────────────
        bm25_results: list[dict] = _bm25_search(conn, query_variants, limit * 2)

        # ── Step 3: vec0 k-NN  ─────────────────────────────────────────
        vec_results: list[dict] = _vec_search(conn, vault, query, limit * 2)

        # ── Step 4: Score fusion ────────────────────────────────────────
        fused = _fuse_results(bm25_results, vec_results, limit)

        return fused
    finally:
        conn.close()


def _bm25_search(
    conn: sqlite3.Connection, query_variants: list[str], limit: int
) -> list[dict]:
    """Run BM25 (FTS5) search across body_units_fts for each query variant.

    Returns results with BM25 scores normalized to [0, 1].
    """
    seen: set[str] = set()
    results: list[dict] = []

    for qv in query_variants:
        try:
            rows = conn.execute(
                """SELECT
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
                   WHERE body_units_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (qv, limit),
            ).fetchall()
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
                    "title": row["title"],
                    "first_author": row["first_author"],
                    "year": row["year"],
                    "journal": row["journal"],
                    "domain": row["domain"],
                    "source": "body_unit",
                    "text": row["unit_text"],
                    "heading": row["section_title"],
                    "bm25_score": round(bm25_norm, 4),
                    "vec_score": 0.0,
                }
            )

    results.sort(key=lambda r: r["bm25_score"], reverse=True)
    return results[:limit]


def _vec_search(
    conn: sqlite3.Connection, vault: Path, query: str, limit: int
) -> list[dict]:
    """Run vec0 k-NN on vec_body and vec_objects.

    Gracefully returns empty list when vec0 extension or tables are missing.
    """
    logger = logging.getLogger(__name__)
    provider = OpenAICompatibleProvider(vault)
    q_emb = provider.encode_single(query)
    q_emb_json = json.dumps(q_emb)

    results: list[dict] = []
    for vec_table, source in _VEC_SOURCE_MAP.items():
        if vec_table not in ("vec_body", "vec_objects"):
            continue
        meta_table = _VEC_META_MAP[vec_table]
        try:
            rows = conn.execute(
                f"""SELECT m.paper_id, m.chunk_index, m.text, v.distance
                    FROM {vec_table} v
                    JOIN {meta_table} m ON v.rowid = m.rowid
                    WHERE v.embedding MATCH ? AND v.k = ?""",
                (q_emb_json, limit),
            ).fetchall()
        except Exception as exc:
            logger.warning("vec0 query failed for %s: %s", vec_table, exc)
            continue

        for row in rows:
            vec_sim = round(1.0 - row[3], 4)  # convert distance to similarity
            results.append(
                {
                    "paper_id": row[0],
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
    When vec0 is unavailable, uses BM25 scores directly.

    Returns list deduplicated by (paper_id, text) with combined score.
    """
    # Build vec lookup: (paper_id, text) -> vec_score
    vec_lookup: dict[tuple[str, str], float] = {}
    for vr in vec_results:
        key = (vr["paper_id"], vr["text"])
        # Keep the highest vec score per unique paper_id+text
        if key not in vec_lookup or vr["vec_score"] > vec_lookup[key]:
            vec_lookup[key] = vr["vec_score"]

    has_vec = bool(vec_results)

    for br in bm25_results:
        bm25_norm = br["bm25_score"]
        key = (br["paper_id"], br.get("text", ""))

        if has_vec and key in vec_lookup:
            vec_raw = vec_lookup[key]
            # Normalize vec score similarly
            vec_norm = 1.0 - (1.0 / (1.0 + vec_raw)) if vec_raw > 0 else 0.0
            br["vec_score"] = round(vec_raw, 4)
            combined = 0.3 * bm25_norm + 0.7 * vec_norm
            br["score"] = round(combined, 4)
        else:
            # No vec data for this item — use BM25 alone
            br["vec_score"] = 0.0
            br["score"] = round(bm25_norm, 4)

    # Sort by combined score descending
    bm25_results.sort(key=lambda r: r["score"], reverse=True)

    # Final dedup and cap
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for r in bm25_results:
        key = (r["paper_id"], r.get("text", ""))
        if key in seen:
            continue
        seen.add(key)
        # Include matched terms hint
        r["matched_terms"] = ""
        out.append(r)
        if len(out) >= limit:
            break

    # If BM25 was empty but vec had results, synthesize entries
    if not out and has_vec:
        seen_text: set[tuple[str, str]] = set()
        for vr in vec_results:
            key = (vr["paper_id"], vr.get("text", ""))
            if key in seen_text:
                continue
            seen_text.add(key)
            vec_raw = vr["vec_score"]
            vec_norm = 1.0 - (1.0 / (1.0 + vec_raw)) if vec_raw > 0 else 0.0
            out.append(
                {
                    "paper_id": vr["paper_id"],
                    "source": vr["source"],
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
