from __future__ import annotations

from paperforge.embedding._chroma import (
    delete_paper_vectors,
    get_collection,
    get_vector_db_path,
)
from paperforge.embedding.backends import (
    ChromaBackend,
    VectorBackend,
    get_vector_backend,
)
from paperforge.embedding.build_state import (
    get_vector_build_state_path,
    mark_vector_build_state,
    read_vector_build_state,
    write_vector_build_state,
)
from paperforge.embedding.builder import embed_body_units, embed_paper, get_body_units_for_embedding, get_object_units_for_embedding, embed_object_units
from paperforge.embedding.preflight import _preflight_check
from paperforge.embedding.search import merge_retrieve, retrieve_chunks
from paperforge.embedding.status import get_embed_status

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
    "get_vector_backend",
    "get_vector_build_state_path",
    "get_vector_db_path",
    "mark_vector_build_state",
    "merge_retrieve",
    "read_vector_build_state",
    "retrieve_chunks",
    "write_vector_build_state",
    "_preflight_check",
]
