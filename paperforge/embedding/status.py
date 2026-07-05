from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_vector_db_path
from paperforge.embedding._config import get_api_model
from paperforge.embedding.backends import get_vector_backend

logger = logging.getLogger(__name__)

def _module_available(name: str) -> bool:
    """Check whether *name* can be imported without side effects."""
    import importlib

    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def get_available_backends() -> dict[str, dict]:
    """Return a dict of known backends with installation and selection status."""
    return {
        "chroma": {
            "installed": True,
            "selected": True,
            "supports_hybrid": False,
            "supports_multimodal": False,
        },
        "lancedb": {
            "installed": _module_available("lancedb"),
            "selected": False,
            "supports_hybrid": True,
            "supports_multimodal": True,
        },
    }



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
