from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection, get_vector_db_path
from paperforge.embedding._config import get_api_model

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
        try:
            collection = get_collection(vault)
            chunk_count = collection.count()
        except Exception as exc:
            healthy = False
            error = str(exc)
            err_lower = str(exc).lower()
            corrupted = "hnsw" in err_lower or "corrupt" in err_lower

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
