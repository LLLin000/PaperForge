"""Public vector API with lazy optional-dependency loading.

Health and metadata commands must not import the remote embedding client or
ChromaDB just to inspect the local memory database. Keep the public API
stable, but load each implementation only when its symbol is used.
"""

from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, tuple[str, str]] = {
    "delete_paper_vectors": ("paperforge.embedding._chroma", "delete_paper_vectors"),
    "delete_paper_vectors_in_conn": ("paperforge.embedding._chroma", "delete_paper_vectors_in_conn"),
    "embed_body_units": ("paperforge.embedding.builder", "embed_body_units"),
    "embed_paper": ("paperforge.embedding.builder", "embed_paper"),
    "get_body_units_for_embedding": ("paperforge.embedding.builder", "get_body_units_for_embedding"),
    "embed_object_units": ("paperforge.embedding.builder", "embed_object_units"),
    "get_object_units_for_embedding": ("paperforge.embedding.builder", "get_object_units_for_embedding"),
    "get_collection": ("paperforge.embedding._chroma", "get_collection"),
    "get_embed_status": ("paperforge.embedding.status", "get_embed_status"),
    "get_vector_db_path": ("paperforge.embedding._chroma", "get_vector_db_path"),
    "mark_vector_build_state": ("paperforge.embedding.build_state", "mark_vector_build_state"),
    "hybrid_search": ("paperforge.embedding.search", "hybrid_search"),
    "merge_retrieve": ("paperforge.embedding.search", "merge_retrieve"),
    "migrate_chroma_to_vec0": ("paperforge.embedding._chroma", "migrate_chroma_to_vec0"),
    "read_vector_build_state": ("paperforge.embedding.build_state", "read_vector_build_state"),
    "retrieve_chunks": ("paperforge.embedding.search", "retrieve_chunks"),
    "write_vector_build_state": ("paperforge.embedding.build_state", "write_vector_build_state"),
    "ChromaBackend": ("paperforge.embedding.backends", "ChromaBackend"),
    "VectorBackend": ("paperforge.embedding.backends", "VectorBackend"),
    "_preflight_check": ("paperforge.embedding.preflight", "_preflight_check"),
}


def __getattr__(name: str):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "ChromaBackend",
    "VectorBackend",
    "delete_paper_vectors",
    "embed_body_units",
    "embed_paper",
    "get_body_units_for_embedding",
    "embed_object_units",
    "get_collection",
    "get_embed_status",
    "get_object_units_for_embedding",
    "mark_vector_build_state",
    "hybrid_search",
    "merge_retrieve",
    "read_vector_build_state",
    "retrieve_chunks",
    "write_vector_build_state",
    "_preflight_check",
]
