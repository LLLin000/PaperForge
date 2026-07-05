from __future__ import annotations

from pathlib import Path

from paperforge.embedding.backends.base import VectorBackend
from paperforge.embedding.backends.chroma_backend import ChromaBackend


def get_vector_backend(vault: Path) -> VectorBackend:
    """Return the default vector backend for *vault*."""
    return ChromaBackend(vault)


__all__ = [
    "ChromaBackend",
    "VectorBackend",
    "get_vector_backend",
]
