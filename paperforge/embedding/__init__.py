"""Public vector API with lazy optional-dependency loading.

Health and metadata commands must not import the remote embedding client
just to inspect the local memory database. Keep the public API
stable, but load each implementation only when its symbol is used.
"""

from __future__ import annotations

from importlib import import_module

_EXPORTS: dict[str, tuple[str, str]] = {
    "delete_paper_vectors": ("paperforge.embedding.vectors", "delete_paper_vectors"),
    "delete_paper_vectors_in_conn": ("paperforge.embedding.vectors", "delete_paper_vectors_in_conn"),
    "embed_body_units": ("paperforge.embedding.builder", "embed_body_units"),
    "embed_paper": ("paperforge.embedding.builder", "embed_paper"),
    "get_body_units_for_embedding": ("paperforge.embedding.builder", "get_body_units_for_embedding"),
    "embed_object_units": ("paperforge.embedding.builder", "embed_object_units"),
    "get_object_units_for_embedding": ("paperforge.embedding.builder", "get_object_units_for_embedding"),
    "get_embed_status": ("paperforge.embedding.status", "get_embed_status"),
    "mark_vector_build_state": ("paperforge.embedding.build_state", "mark_vector_build_state"),
    "hybrid_search": ("paperforge.embedding.search", "hybrid_search"),
    "merge_retrieve": ("paperforge.embedding.search", "merge_retrieve"),
    "read_vector_build_state": ("paperforge.embedding.build_state", "read_vector_build_state"),
    "retrieve_chunks": ("paperforge.embedding.search", "retrieve_chunks"),
    "write_vector_build_state": ("paperforge.embedding.build_state", "write_vector_build_state"),
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
    "delete_paper_vectors",
    "delete_paper_vectors_in_conn",
    "embed_body_units",
    "embed_paper",
    "get_body_units_for_embedding",
    "embed_object_units",
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
