from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def embed_paper(vault: Path, zotero_key: str, chunks: list[dict]) -> int:
    """Embed chunks for one paper using API and insert into ChromaDB. Returns count."""
    collection = get_collection(vault)
    provider = OpenAICompatibleProvider(vault)

    texts = [c["text"] for c in chunks]
    ids = [f"{zotero_key}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "paper_id": zotero_key,
            "section": c["section"],
            "page_number": c["page_number"],
            "chunk_index": c["chunk_index"],
            "token_estimate": c["token_estimate"],
        }
        for c in chunks
    ]

    embeddings = provider.encode(texts)
    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
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
    return len(chunks)
