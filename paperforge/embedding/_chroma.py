from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_vector_db_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    return (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent / "vectors"


def _get_chroma():
    import chromadb
    return chromadb


def get_collection(vault: Path):
    chroma = _get_chroma()
    db_path = get_vector_db_path(vault)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chroma.PersistentClient(path=str(db_path))
    try:
        return client.get_or_create_collection(
            name="paperforge_fulltext",
            metadata={"hnsw:space": "cosine"},
        )
    except Exception:
        client.delete_collection("paperforge_fulltext")
        return client.create_collection(
            name="paperforge_fulltext",
            metadata={"hnsw:space": "cosine"},
        )


def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    collection = get_collection(vault)
    try:
        results = collection.get(where={"paper_id": zotero_key})
        ids = results.get("ids", [])
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0
