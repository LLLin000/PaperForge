from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_vector_db_path
from paperforge.embedding._config import get_api_model
from paperforge.embedding.backends import get_vector_backend

logger = logging.getLogger(__name__)


def get_embed_status(vault: Path) -> dict:
    """Get vector DB status. API-only mode.

    Returns dict with keys: db_exists, chunk_count, model, mode, healthy, error, corrupted.
    """
    db_path = get_vector_db_path(vault)
    exists = db_path.exists()
    chunk_count = 0
    healthy = True
    error = ""
    corrupted = False
    if exists:
        backend = get_vector_backend(vault)
        health = backend.health()
        healthy = health["healthy"]
        chunk_count = health.get("chunk_count", 0)
        error = health.get("error", "")
        corrupted = health.get("corrupted", False)

    model = get_api_model(vault)

    return {
        "db_exists": exists,
        "chunk_count": chunk_count,
        "model": model,
        "mode": "api",
        "healthy": healthy,
        "corrupted": corrupted,
        "error": error,
    }
