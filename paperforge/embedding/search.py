from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding.backends import get_vector_backend
from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def retrieve_chunks(vault: Path, query: str, limit: int = 5, expand: bool = True) -> list[dict]:
    """Search chunks via API embedding. Returns list with metadata and similarity scores."""
    backend = get_vector_backend(vault)
    provider = OpenAICompatibleProvider(vault)
    query_embedding = provider.encode_single(query)

    return backend.query(query_embedding=query_embedding, limit=limit * 3 if expand else limit)
