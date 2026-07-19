"""Deprecated. Import from paperforge.embedding instead."""
from __future__ import annotations

import warnings

from paperforge.embedding import (
    delete_paper_vectors,  # noqa: F401
    embed_paper,  # noqa: F401
    get_collection,  # noqa: F401
    get_embed_status,  # noqa: F401
    get_vector_db_path,  # noqa: F401
    mark_vector_build_state,  # noqa: F401
    read_vector_build_state,  # noqa: F401
    retrieve_chunks,  # noqa: F401
    write_vector_build_state,  # noqa: F401
)

warnings.warn(
    "paperforge.memory.vector_db is deprecated, use paperforge.embedding instead",
    DeprecationWarning,
    stacklevel=2,
)
