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
