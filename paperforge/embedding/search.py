from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search chunks via API embedding. Returns list with metadata and similarity scores."""
    collection = get_collection(vault)
    provider = OpenAICompatibleProvider(vault)
    query_embedding = provider.encode_single(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=limit * 3 if expand else limit,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        chunks.append({
            "paper_id": meta["paper_id"],
            "section": meta.get("section", "Text"),
            "page_number": meta.get("page_number", 1),
            "chunk_index": meta.get("chunk_index", 0),
            "chunk_text": doc,
            "score": round(1.0 - dist, 4),
        })

    return chunks
