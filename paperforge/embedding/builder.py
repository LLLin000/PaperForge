from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding.backends import get_vector_backend
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def embed_paper(vault: Path, zotero_key: str, chunks: list[dict]) -> int:
    """Embed chunks for one paper using API and insert into vector DB. Returns count."""
    backend = get_vector_backend(vault)
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
    backend.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(chunks)
