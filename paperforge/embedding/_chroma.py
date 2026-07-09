from __future__ import annotations

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


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
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
