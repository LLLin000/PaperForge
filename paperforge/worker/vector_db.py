"""Deprecated. Import from paperforge.embedding instead."""
from __future__ import annotations

import warnings

from paperforge.embedding.preflight import _preflight_check  # noqa: F401
from paperforge.embedding.status import get_embed_status  # noqa: F401

warnings.warn(
    "paperforge.worker.vector_db is deprecated, use paperforge.embedding instead",
    DeprecationWarning,
    stacklevel=2,
)
