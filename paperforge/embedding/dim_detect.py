"""Detect embedding dimension from the configured model at runtime."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_DETECTED_DIM: Optional[int] = None


def detect_embedding_dim(vault: Path) -> int:
    """Call the embedding API once to determine the output dimension.

    Result is cached globally for the process lifetime.
    """
    global _DETECTED_DIM
    if _DETECTED_DIM is not None:
        return _DETECTED_DIM

    provider = OpenAICompatibleProvider(vault)
    test_vec = provider.encode_single("dimension detection probe")
    dim = len(test_vec)
    logger.info("Detected embedding dimension: %d (model: %s)", dim, getattr(provider, "model", "unknown"))
    _DETECTED_DIM = dim
    return dim


def ensure_vec_tables(conn, vault: Path) -> None:
    """Drop and recreate vec0 virtual tables to match the model's dimension.

    Safe to call multiple times — only recreates when dimension differs.
    """
    from paperforge.memory.db import ensure_vec_extension

    ensure_vec_extension(conn)

    # Detect required dimension
    required_dim = detect_embedding_dim(vault)

    # Check existing vec0 tables
    existing_dim: Optional[int] = None
    try:
        # vec0 stores dimension in the table metadata — read via pragma
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name='vec_body' AND type='table'").fetchone()
        if row:
            import re
            m = re.search(r"float\[(\d+)\]", row[0])
            if m:
                existing_dim = int(m.group(1))
    except Exception:
        pass

    if existing_dim == required_dim:
        return  # already correct

    # Drop and recreate with correct dimension
    for name in ("vec_fulltext", "vec_body", "vec_objects"):
        try:
            conn.execute(f"DROP TABLE IF EXISTS \"{name}\"")
        except Exception:
            pass
        ddl = f"CREATE VIRTUAL TABLE IF NOT EXISTS \"{name}\" USING vec0(embedding float[{required_dim}]);"
        conn.execute(ddl)

    logger.info("Recreated vec0 tables with dimension %d", required_dim)
