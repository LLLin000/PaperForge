from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path

from paperforge.embedding.providers import resolve_embedding_provider
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider
from paperforge.memory.db import (
    ensure_vec_extension,
    get_connection,
    get_memory_db_path,
    open_live_reader,
)

logger = logging.getLogger(__name__)

RETRIEVAL_COLLECTIONS = ["paperforge_fulltext", "paperforge_body", "paperforge_objects"]

_VEC_SOURCE_MAP = {
    "vec_body": "body",
    "vec_objects": "object",
}

# ── Object label normalization ───────────────────────────────────────────

_OBJECT_LABEL_RE = re.compile(
    r"\b(?:(?:Extended\s+Data|Supplementary)\s+)?"
    r"(?:Figure|Fig\.?|Table)\s+"
    r"(?:S?\d+[A-Za-z]?|[IVXLCDM]+)\b",
    re.IGNORECASE,
)

def normalize_object_label(stored_label: str, caption: str) -> str:
    """Normalize internal figure/table labels to display labels from caption."""
    if not stored_label.startswith(("figure:p", "table:p")):
        return stored_label
    if not caption:
        return stored_label
    match = _OBJECT_LABEL_RE.search(caption)
    return match.group(0) if match else stored_label

_VEC_META_MAP = {
    "vec_body": "vec_body_meta",
    "vec_objects": "vec_objects_meta",
}


def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search chunks via vec0 k-NN on vec_fulltext. Returns list with metadata and similarity scores."""
    provider = resolve_embedding_provider(vault, default_cls=OpenAICompatibleProvider)
    query_embedding = provider.encode_single(query)
    n = limit * 3 if expand else limit
    db_path = get_memory_db_path(vault)
    with open_live_reader(vault, db_path) as conn:
        ensure_vec_extension(conn)
        q_emb_json = json.dumps(query_embedding)
        rows = conn.execute(
            """SELECT m.paper_id, m.chunk_index, m.text, v.distance
               FROM vec_fulltext v
               JOIN vec_fulltext_meta m ON v.rowid = m.rowid
               WHERE v.embedding MATCH ? AND v.k = ?""",
            (q_emb_json, n),
        ).fetchall()

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
    enrichment: dict = {"structure_resolved": False}
    if source_kind == "body":
        row = conn.execute(
            "SELECT node_id, section_path_json, section_title, section_level, part_ordinal, unit_kind "
            "FROM body_units WHERE unit_id=? AND paper_id=?",
            (unit_id, paper_id),
        ).fetchone()
        if row:
            node_id = row["node_id"] or ""
            enrichment["node_id"] = node_id
            enrichment["structure_path"] = json.loads(row["section_path_json"]) if row["section_path_json"] else []
            enrichment["section_title"] = row["section_title"]
            enrichment["section_level"] = row["section_level"]
            enrichment["part_ordinal"] = row["part_ordinal"]
            enrichment["unit_kind"] = row["unit_kind"]
            enrichment["structure_resolved"] = bool(node_id)
        else:
            enrichment["node_id"] = ""
            enrichment["structure_path"] = []
    elif source_kind == "object":
        row = conn.execute(
            "SELECT node_id, section_path_json, object_kind, "
            "       object_label, caption_text, page_span_json "
            "FROM object_units WHERE unit_id=? AND paper_id=?",
            (unit_id, paper_id),
        ).fetchone()
        if row:
            node_id = row["node_id"] or ""
            enrichment["node_id"] = node_id
            enrichment["structure_path"] = json.loads(row["section_path_json"]) if row["section_path_json"] else []
            enrichment["object_kind"] = row["object_kind"]

            # Normalize object_label: internal keys like "figure:p6:17" -> extract from caption
            enrichment["object_label"] = normalize_object_label(
                row["object_label"] or "",
                row["caption_text"] or "",
            )
            enrichment["caption_text"] = row["caption_text"] or ""

            # page_span: suppress [0, 0] (unresolved)
            try:
                ps = json.loads(row["page_span_json"]) if row["page_span_json"] else []
                enrichment["page_span"] = ps if ps != [0, 0] else []
            except (json.JSONDecodeError, TypeError):
                enrichment["page_span"] = []
            enrichment["structure_resolved"] = bool(node_id)
        else:
            enrichment["node_id"] = ""
            enrichment["structure_path"] = []
    else:
        enrichment["node_id"] = ""
        enrichment["structure_path"] = []

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
    """Query vec0 tables, enrich with structural coordinates, dedup by unit_id.
    #159 §6: results pass the reader gate (vector lineage current only)."""
    provider = resolve_embedding_provider(vault, default_cls=OpenAICompatibleProvider)
    q_emb = provider.encode_single(query)
    n = limit * 2 if expand else limit

    db_path = get_memory_db_path(vault)
    with open_live_reader(vault, db_path) as conn:
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
def hybrid_search(vault: Path, query: str, limit: int = 10, paper_id: str | None = None) -> list[dict]:
    """Hybrid search: BM25 FTS5 + vec0 k-NN with query rewrite.

    Vector failures (no API key, stale embeddings) degrade gracefully
    to BM25-only — never crash.
    """
    from paperforge.embedding.query_rewrite import expand_query as do_expand

    query_variants = do_expand(query)
    # P1-3: encode the query BEFORE taking the reader lock — a slow provider
    # call must not hold .read.lock (it stalls other queries and can exceed
    # the publish barrier's 10s timeout).
    try:
        query_embedding = resolve_embedding_provider(
            vault, default_cls=OpenAICompatibleProvider
        ).encode_single(query)
    except Exception:
        query_embedding = None
    db_path = get_memory_db_path(vault)
    with open_live_reader(vault, db_path) as conn:
        ensure_vec_extension(conn)
        bm25_results: list[dict] = _bm25_search(conn, query_variants, limit * 2, paper_id=paper_id)
        try:
            vec_results: list[dict] = _vec_search(
                conn, vault, query, limit * 2, paper_id=paper_id,
                query_embedding=query_embedding,
            )
        except Exception:
            vec_results = []

        fused = _fuse_results(bm25_results, vec_results, limit)

        # Hydrate paper metadata & heading for vector-only hits in batch
        missing_meta_pids = sorted({
            str(r.get("paper_id") or "")
            for r in fused
            if r.get("paper_id") and not (r.get("title") and r.get("first_author"))
        })
        if missing_meta_pids:
            ph = ",".join("?" for _ in missing_meta_pids)
            prows = conn.execute(
                f"SELECT zotero_key, title, first_author, year, journal, domain FROM papers WHERE zotero_key IN ({ph})",
                missing_meta_pids,
            ).fetchall()
            pmap = {row["zotero_key"]: row for row in prows}
            for r in fused:
                prow = pmap.get(r.get("paper_id", ""))
                if prow is not None:
                    for fld in ("title", "first_author", "year", "journal", "domain"):
                        if not r.get(fld):
                            r[fld] = prow[fld] or ""

        body_uids = [
            str(r["unit_id"])
            for r in fused
            if r.get("unit_id") and not r.get("heading") and r.get("source", "body") == "body"
        ]
        if body_uids:
            ph = ",".join("?" for _ in body_uids)
            brows = conn.execute(
                f"SELECT unit_id, section_title, section_path FROM body_units WHERE unit_id IN ({ph})",
                body_uids,
            ).fetchall()
            bmap = {row["unit_id"]: (row["section_title"] or row["section_path"] or "") for row in brows}
            for r in fused:
                if not r.get("heading") and r.get("unit_id") in bmap:
                    r["heading"] = bmap[r["unit_id"]]

        obj_uids = [
            str(r["unit_id"])
            for r in fused
            if r.get("unit_id") and not r.get("heading") and r.get("source") == "object"
        ]
        if obj_uids:
            ph = ",".join("?" for _ in obj_uids)
            orows = conn.execute(
                f"SELECT unit_id, object_label FROM object_units WHERE unit_id IN ({ph})",
                obj_uids,
            ).fetchall()
            omap = {row["unit_id"]: (row["object_label"] or "") for row in orows}
            for r in fused:
                if not r.get("heading") and r.get("unit_id") in omap:
                    r["heading"] = omap[r["unit_id"]]

        # Enrich fused results with structural coordinates
        for r in fused:
            enrichment = enrich_retrieval_hit(
                conn, paper_id=r.get("paper_id", ""), source_kind=r.get("source", "body"), unit_id=r.get("unit_id", "")
            )
            r.update(enrichment)
            if not r.get("title"):
                r["title"] = str(r.get("paper_id") or "")

        return fused
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
    conn: sqlite3.Connection, vault: Path, query: str, limit: int, paper_id: str | None = None,
    *, query_embedding: list[float] | None = None,
) -> list[dict]:
    """Run vec0 k-NN on vec_body and vec_objects with unit_id.

    ``query_embedding`` should be computed OUTSIDE the reader lock (P1-3):
    a slow provider call must not hold the .read.lock and stall publish or
    other queries.  Gracefully returns empty list when vec0 extension or
    tables are missing.  Supports paper-scoped filtering via rowid
    pre-filter.
    """
    logger = logging.getLogger(__name__)
    if query_embedding is None:
        provider = resolve_embedding_provider(vault, default_cls=OpenAICompatibleProvider)
        query_embedding = provider.encode_single(query)
    q_emb_json = json.dumps(query_embedding)

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

def _canon_source(src: object) -> str:
    s = str(src or "").strip()
    if s in ("", "body", "body_unit"):
        return "body"
    return s


def _fuse_results(
    bm25_results: list[dict], vec_results: list[dict], limit: int
) -> list[dict]:
    """Fuse full union of BM25 and vec0 results with combined score.

    Fusion formula:
    - matched in both: 0.3 * bm25_norm + 0.7 * vec_norm
    - bm25-only: bm25_norm
    - vec-only: 0.7 * vec_norm (when bm25 present) or vec_norm (when bm25 empty)
    Deduplicates by (canonical_source, unit_id).
    """
    vec_lookup: dict[tuple[str, str], float] = {}
    for vr in vec_results:
        uid = str(vr.get("unit_id") or "")
        if not uid:
            continue
        key = (_canon_source(vr.get("source")), uid)
        if key not in vec_lookup or vr["vec_score"] > vec_lookup[key]:
            vec_lookup[key] = vr["vec_score"]

    has_vec = bool(vec_results)
    has_bm25 = bool(bm25_results)

    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for idx, br in enumerate(bm25_results):
        uid = str(br.get("unit_id") or "")
        src = _canon_source(br.get("source"))
        dedupe_key = (src, uid) if uid else ("__bm25_anon__", str(idx))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        bm25_norm = float(br.get("bm25_score", 0.0))
        lookup_key = (src, uid)
        if has_vec and uid and lookup_key in vec_lookup:
            vec_raw = float(vec_lookup[lookup_key])
            vec_norm = 1.0 - (1.0 / (1.0 + vec_raw)) if vec_raw > 0 else 0.0
            br["vec_score"] = round(vec_raw, 4)
            br["score"] = round(0.3 * bm25_norm + 0.7 * vec_norm, 4)
        else:
            br["vec_score"] = 0.0
            br["score"] = round(bm25_norm, 4)
        br.setdefault("matched_terms", "")
        candidates.append(br)

    # Full union: include ALL unmatched vector hits (both body and object)
    if has_vec:
        for idx, vr in enumerate(vec_results):
            uid = str(vr.get("unit_id") or "")
            src = _canon_source(vr.get("source"))
            raw_src = str(vr.get("source") or src)
            dedupe_key = (src, uid) if uid else ("__vec_anon__", str(idx))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            vec_raw = float(vr.get("vec_score", 0.0))
            vec_norm = 1.0 - (1.0 / (1.0 + vec_raw)) if vec_raw > 0 else 0.0
            combined = 0.7 * vec_norm if has_bm25 else vec_norm
            candidates.append(
                {
                    "paper_id": vr["paper_id"],
                    "source": raw_src,
                    "unit_id": uid,
                    "text": vr.get("text", ""),
                    "bm25_score": 0.0,
                    "vec_score": round(vec_raw, 4),
                    "score": round(combined, 4),
                    "matched_terms": "",
                    "heading": vr.get("heading", ""),
                    "title": vr.get("title", ""),
                    "first_author": vr.get("first_author", ""),
                    "year": vr.get("year", ""),
                    "journal": vr.get("journal", ""),
                    "domain": vr.get("domain", ""),
                }
            )

    candidates.sort(
        key=lambda r: (float(r.get("score", 0.0)), float(r.get("vec_score", 0.0))),
        reverse=True,
    )
    return candidates[:limit]
