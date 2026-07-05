from __future__ import annotations

import logging
from pathlib import Path

import chromadb

from paperforge.embedding._chroma import get_vector_db_path

logger = logging.getLogger(__name__)


class ChromaBackend:
    """ChromaDB-based vector backend.

    Preserves the existing ``paperforge_fulltext`` collection behaviour.
    """

    collection_name = "paperforge_fulltext"

    def __init__(self, vault: Path) -> None:
        db_path = get_vector_db_path(vault)
        db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            err = str(exc).lower()
            if "hnsw" in err or "compaction" in err or "segment" in err:
                raise RuntimeError(
                    f"ChromaDB index error (possibly corrupted). "
                    f"Run 'paperforge embed build --force' to rebuild from scratch. "
                    f"Original error: {exc}"
                ) from exc
            raise

    def query(
        self, *, query_embedding: list[float], limit: int
    ) -> list[dict]:
        raw = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        chunks: list[dict] = []
        for doc, meta, dist in zip(
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
        ):
            chunks.append(
                {
                    "paper_id": meta["paper_id"],
                    "section": meta.get("section", "Text"),
                    "page_number": meta.get("page_number", 1),
                    "chunk_index": meta.get("chunk_index", 0),
                    "chunk_text": doc,
                    "score": round(1.0 - dist, 4),
                }
            )
        return chunks

    def delete_paper(self, paper_id: str) -> int:
        try:
            results = self.collection.get(where={"paper_id": paper_id})
            ids = results.get("ids", [])
            if ids:
                self.collection.delete(ids=ids)
            return len(ids)
        except Exception:
            return 0

    def health(self) -> dict:
        try:
            chunk_count = self.collection.count()
            return {"healthy": True, "chunk_count": chunk_count}
        except Exception as exc:
            err_lower = str(exc).lower()
            return {
                "healthy": False,
                "chunk_count": 0,
                "error": str(exc),
                "corrupted": "hnsw" in err_lower or "corrupt" in err_lower,
            }
