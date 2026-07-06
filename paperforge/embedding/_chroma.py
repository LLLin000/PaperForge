from __future__ import annotations

import logging
from pathlib import Path

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
    total = 0
    for col_name in _COLLECTION_NAMES:
        try:
            collection = get_collection(vault, name=col_name)
            results = collection.get(where={"paper_id": zotero_key})
            ids = results.get("ids", [])
            if ids:
                collection.delete(ids=ids)
            total += len(ids)
        except Exception:
            pass
    return total
