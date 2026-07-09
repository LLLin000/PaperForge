from __future__ import annotations

import json
import logging
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


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    _delete_from_chromadb(vault, zotero_key)

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)

    total = 0
    for vec_table, meta_table in _VEC_TABLE_MAP.values():
        rows = conn.execute(f"SELECT rowid FROM {meta_table} WHERE paper_id = ?", (zotero_key,)).fetchall()
        rowids = [r["rowid"] for r in rows]
        if rowids:
            placeholders = ",".join("?" for _ in rowids)
            conn.execute(f"DELETE FROM {vec_table} WHERE rowid IN ({placeholders})", rowids)
            conn.execute(f"DELETE FROM {meta_table} WHERE paper_id = ?", (zotero_key,))
        total += len(rowids)

    conn.commit()
    conn.close()
    return total


def migrate_chroma_to_vec0(vault: Path) -> int:
    """Copy vectors from existing ChromaDB to vec0 tables.

    Pure local copy — no API calls. Idempotent: skips papers already
    present in vec0 meta tables. Returns count of vectors migrated.
    """
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

            for entry in entries:
                emb = entry["embedding"]
                if hasattr(emb, "tolist"):
                    emb = emb.tolist()
                embedding_json = json.dumps(emb)
                cur = conn.execute(f"INSERT INTO {vec_table}(embedding) VALUES (?)", [embedding_json])
                rowid = cur.lastrowid
                conn.execute(
                    f"INSERT INTO {meta_table}(rowid, paper_id, chunk_index, text) VALUES (?, ?, ?, ?)",
                    [rowid, entry["paper_id"], entry["chunk_index"], entry["text"]],
                )
            conn.commit()
            total += len(entries)

    conn.close()
    return total
