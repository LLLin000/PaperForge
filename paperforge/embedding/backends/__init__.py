"""Vector backend exports.

``ChromaBackend`` needs the opt-in ``[legacy-vector]`` extra, so it is
imported lazily; the package itself stays importable without ChromaDB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from paperforge.embedding.backends.base import VectorBackend

if TYPE_CHECKING:  # pragma: no cover - typing only
    from paperforge.embedding.backends.chroma_backend import ChromaBackend


__all__ = [
    "ChromaBackend",
    "VectorBackend",
]


def __getattr__(name: str):
    if name == "ChromaBackend":
        try:
            from paperforge.embedding.backends.chroma_backend import ChromaBackend
        except ImportError as exc:  # legacy extra not installed
            raise ImportError(
                'ChromaBackend needs the opt-in legacy extra: pip install "paperforge[vector,legacy-vector]"'
            ) from exc
        globals()[name] = ChromaBackend
        return ChromaBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
