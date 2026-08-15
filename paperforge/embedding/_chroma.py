from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema

_VEC_TABLE_MAP = {
    "paperforge_fulltext": ("vec_fulltext", "vec_fulltext_meta"),
    "paperforge_body": ("vec_body", "vec_body_meta"),
    "paperforge_objects": ("vec_objects", "vec_objects_meta"),
}

logger = logging.getLogger(__name__)


_COLLECTION_NAMES = ["paperforge_fulltext", "paperforge_body", "paperforge_objects"]


def get_vector_db_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths

    paths = paperforge_paths(vault)
    return (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent / "vectors"


def _get_chroma():
    import chromadb

    return chromadb


def get_collection(vault: Path, name: str = "paperforge_fulltext"):
    chroma = _get_chroma()
    db_path = get_vector_db_path(vault)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chroma.PersistentClient(path=str(db_path))
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def _delete_from_chromadb(vault: Path, zotero_key: str) -> None:
    """Delete vectors for a paper from ChromaDB collections if it exists."""
    try:
        import chromadb

        chroma_dir = get_vector_db_path(vault)
        if not chroma_dir.exists():
            return
        client = chromadb.PersistentClient(path=str(chroma_dir))
        for coll_name in _COLLECTION_NAMES:
            try:
                coll = client.get_collection(name=coll_name)
                coll.delete(where={"paper_id": zotero_key})
            except Exception:
                pass
    except ImportError:
        pass


def delete_paper_vectors_in_conn(conn: sqlite3.Connection, key: str) -> int:
    """Delete vec0 rows and meta rows for *key*. No commit/rollback/close.

    Safe to call from within an outer transaction — the caller owns the
    transaction boundary.  Returns count of vector rows deleted.
    """
    total = 0
    for vec_table, meta_table in _VEC_TABLE_MAP.values():
        rows = conn.execute(
            f"SELECT rowid FROM {meta_table} WHERE paper_id = ?", (key,)
        ).fetchall()
        rowids = [r["rowid"] for r in rows]
        if rowids:
            placeholders = ",".join("?" for _ in rowids)
            conn.execute(
                f"DELETE FROM {vec_table} WHERE rowid IN ({placeholders})", rowids
            )
            conn.execute(f"DELETE FROM {meta_table} WHERE paper_id = ?", (key,))
        total += len(rowids)
    return total


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    """Delete a paper's vectors under the global writer lock (P0-4).

    A shadow publish swaps the whole live DB — an unlocked delete could be
    overwritten by the publish or race the snapshot.
    """
    from paperforge.memory.db import WriterLock

    with WriterLock(vault):
        return _delete_paper_vectors_locked(vault, zotero_key)


def _delete_paper_vectors_locked(vault: Path, zotero_key: str) -> int:
    """Locked body: caller owns the WriterLock.

    Multi-verification before deleting a vector row — never delete a row
    that is not provably owned by *zotero_key*:
    1. rowids come from ``meta WHERE paper_id = ?`` (ownership by
       construction);
    2. each rowid is re-verified against its meta row owner immediately
       before the vec0 DELETE (guards a corrupted/misaligned meta rowid
       that could otherwise delete another paper's vector);
    3. the vec0 DELETE rowcount must equal the expected rowid count, else
       the whole delete is rolled back (partial deletion never commits).
    """
    _delete_from_chromadb(vault, zotero_key)

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)

    total = 0
    try:
        for vec_table, meta_table in _VEC_TABLE_MAP.values():
            rows = conn.execute(
                f"SELECT rowid FROM {meta_table} WHERE paper_id = ?", (zotero_key,)
            ).fetchall()
            rowids = [r["rowid"] for r in rows]
            if not rowids:
                continue
            # Verification 2: every rowid must still be owned by this paper.
            verified: list[int] = []
            for rowid in rowids:
                owner = conn.execute(
                    f"SELECT paper_id FROM {meta_table} WHERE rowid = ?", (rowid,)
                ).fetchone()
                if owner is not None and owner["paper_id"] == zotero_key:
                    verified.append(rowid)
                else:
                    logger.warning(
                        "vec delete: rowid %s in %s not owned by %s — skipped",
                        rowid, meta_table, zotero_key,
                    )
            if not verified:
                continue
            placeholders = ",".join("?" for _ in verified)
            cur = conn.execute(
                f"DELETE FROM {vec_table} WHERE rowid IN ({placeholders})", verified
            )
            # Verification 3: full deletion or rollback — a partial delete
            # (e.g. missing vec0 row) must never commit silently.
            if cur.rowcount != len(verified):
                raise RuntimeError(
                    f"vec delete partial: {cur.rowcount}/{len(verified)} rows "
                    f"removed from {vec_table} for {zotero_key}"
                )
            conn.execute(
                f"DELETE FROM {meta_table} WHERE paper_id = ?", (zotero_key,)
            )
            total += len(verified)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return total


def migrate_chroma_to_vec0(vault: Path) -> int:
    """Copy vectors from existing ChromaDB to vec0 tables under the global
    writer lock (P0-4) — a shadow publish must not overwrite the migration.

    Pure local copy — no API calls. Idempotent: skips papers already
    present in vec0 meta tables. Returns count of vectors migrated.
    """
    from paperforge.memory.db import WriterLock

    with WriterLock(vault):
        return _migrate_chroma_to_vec0_locked(vault)


def _migrate_chroma_to_vec0_locked(vault: Path) -> int:
    """Locked body: caller owns the WriterLock."""
    chroma_dir = get_vector_db_path(vault)
    if not chroma_dir.exists():
        return 0

    try:
        import chromadb  # noqa: F811
    except ImportError:
        logger.info("chromadb not installed, cannot migrate")
        return 0

    try:
        client = chromadb.PersistentClient(path=str(chroma_dir))
    except Exception as exc:
        logger.warning("failed to open ChromaDB at %s: %s", chroma_dir, exc)
        return 0

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)

    # vec0 tables declare their dimension in the DDL (current model's).
    # Migrated vectors must match it exactly — anything else is a different
    # embedding model (skip + report, never force into a mismatched table).
    try:
        ddl = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='vec_fulltext'"
        ).fetchone()
        import re as _re

        _m = _re.search(r"float\[(\d+)\]", ddl[0] or "") if ddl and ddl[0] else None
        vec_dimension = int(_m.group(1)) if _m else 0
    except Exception:  # noqa: BLE001
        vec_dimension = 0

    _migrated_fulltext_papers: set[str] = set()

    total = 0
    for chroma_name, (vec_table, meta_table) in _VEC_TABLE_MAP.items():
        try:
            coll = client.get_collection(name=chroma_name)
        except Exception:
            logger.debug("ChromaDB collection %s not found, skipping", chroma_name)
            continue

        data = coll.get(include=["embeddings", "documents", "metadatas"])
        ids = data.get("ids", [])
        if not ids:
            continue

        embeddings = data["embeddings"] if data.get("embeddings") is not None else []
        documents = data["documents"] if data.get("documents") is not None else []
        metadatas = data["metadatas"] if data.get("metadatas") is not None else []

        # Group by paper_id for idempotency check
        entries_by_paper: dict[str, list[dict]] = {}
        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            if isinstance(meta, dict):
                paper_id = meta.get("paper_id", "")
            else:
                paper_id = ""

            if not paper_id:
                # Fallback: extract from ChromaDB id like "paperforge_fulltext:KEY_0"
                parts = doc_id.split(":", 1)
                if len(parts) > 1:
                    paper_id = parts[1].rsplit("_", 1)[0]

            if not paper_id:
                continue

            if paper_id not in entries_by_paper:
                entries_by_paper[paper_id] = []
            entries_by_paper[paper_id].append(
                {
                    "embedding": embeddings[i] if embeddings is not None and i < len(embeddings) else [],
                    "text": documents[i] if documents is not None and i < len(documents) else "",
                    "chunk_index": meta.get("chunk_index", i) if isinstance(meta, dict) else i,
                    "paper_id": paper_id,
                }
            )

        for paper_id, entries in entries_by_paper.items():
            existing = conn.execute(
                f"SELECT 1 FROM {meta_table} WHERE paper_id = ? LIMIT 1", (paper_id,)
            ).fetchone()
            if existing:
                continue

            # Dimension guard: vec0 tables declare a fixed dimension (the
            # current model's).  A migrated vector from a DIFFERENT
            # embedding model would be rejected by vec0 (Dimension mismatch)
            # or — if the dimensions collided by luck — would match in a
            # meaningless semantic space.  Skip those papers and report
            # them; they need a rebuild, not a copy.
            skipped_dim: list[str] = []
            insertable = []
            for entry in entries:
                emb = entry["embedding"]
                if hasattr(emb, "tolist"):
                    emb = emb.tolist()
                if len(emb) != vec_dimension:
                    skipped_dim.append(paper_id)
                    continue
                insertable.append((emb, entry))
            if skipped_dim:
                logger.warning(
                    "migrate: %s paper(s) have vectors with dimension != %d "
                    "(different embedding model) — skipped, rebuild required",
                    len(set(skipped_dim)), vec_dimension,
                )
            for emb, entry in insertable:
                embedding_json = json.dumps(emb)
                cur = conn.execute(f"INSERT INTO {vec_table}(embedding) VALUES (?)", [embedding_json])
                rowid = cur.lastrowid
                conn.execute(
                    f"INSERT INTO {meta_table}(rowid, paper_id, chunk_index, text) VALUES (?, ?, ?, ?)",
                    [rowid, entry["paper_id"], entry["chunk_index"], entry["text"]],
                )
            if insertable:
                conn.commit()
                total += len(insertable)
                if vec_table == "vec_fulltext":
                    _migrated_fulltext_papers.update(
                        p for _, e in insertable if (p := e["paper_id"])
                    )

    # Legacy lineage: migrated full-text vectors are searchable ONLY while
    # the embedding config is unchanged (identity match — same model/dim →
    # the query encodes into the same space).  Writing the row with the
    # CURRENT endpoint/model + the MIGRATED dimension makes probe's identity
    # comparison the compatibility oracle: match ⇒ gate passes, change ⇒
    # stale ⇒ rebuild.
    if _migrated_fulltext_papers:
        from paperforge.embedding._config import (
            get_api_model,
            get_effective_api_base_url,
        )
        from paperforge.lineage import write_legacy_fulltext_lineage

        write_legacy_fulltext_lineage(
            conn,
            vault,
            endpoint=get_effective_api_base_url(vault),
            model=get_api_model(vault),
            dimension=vec_dimension,
            paper_ids=_migrated_fulltext_papers,
        )
        conn.commit()

    conn.close()
    return total
