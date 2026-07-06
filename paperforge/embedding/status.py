from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._chroma import get_collection, get_vector_db_path
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
    """Get vector DB status across both collections."""
    db_path = get_vector_db_path(vault)
    exists = db_path.exists()
    chunk_count = 0
    object_chunk_count = 0
    body_chunk_count = 0
    error = ""
    corrupted = False
    healthy = True
    if exists:
        # Count paperforge_fulltext
        try:
            col = get_collection(vault, name="paperforge_fulltext")
            chunk_count = col.count()
        except Exception:
            pass
        # Count paperforge_body
        try:
            col_body = get_collection(vault, name="paperforge_body")
            body_chunk_count = col_body.count()
        except Exception:
            pass
        # Count paperforge_objects
        try:
            col_o = get_collection(vault, name="paperforge_objects")
            object_chunk_count = col_o.count()
        except Exception:
            pass
        # Backend health (checks primary collection)
        backend = get_vector_backend(vault)
        health = backend.health()
        healthy = health["healthy"]
        error = health.get("error", "")
        corrupted = health.get("corrupted", False)

    model = get_api_model(vault)


    return {
        "db_exists": exists,
        "chunk_count": chunk_count,
        "body_chunk_count": body_chunk_count,
        "object_chunk_count": object_chunk_count,
        "total_chunks": chunk_count + body_chunk_count + object_chunk_count,
        "model": model,
        "mode": "api",
        "healthy": healthy,
        "corrupted": corrupted,
        "error": error,
    }
