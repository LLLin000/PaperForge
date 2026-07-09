from __future__ import annotations

import logging
from pathlib import Path

from paperforge.embedding._config import get_api_model
from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema

logger = logging.getLogger(__name__)


def get_embed_status(vault: Path) -> dict:
    """Get vector DB status from sqlite-vec companion tables."""
    db_path = get_memory_db_path(vault)
    exists = db_path.exists()
    chunk_count = 0
    object_chunk_count = 0
    body_chunk_count = 0
    error = ""
    healthy = True
    if exists:
        try:
            conn = get_connection(db_path, read_only=True)
            try:
                ensure_vec_extension(conn)
                ensure_schema(conn)
                row_ft = conn.execute("SELECT COUNT(*) AS cnt FROM vec_fulltext_meta").fetchone()
                chunk_count = row_ft["cnt"] if row_ft else 0
                row_body = conn.execute("SELECT COUNT(*) AS cnt FROM vec_body_meta").fetchone()
                body_chunk_count = row_body["cnt"] if row_body else 0
                row_obj = conn.execute("SELECT COUNT(*) AS cnt FROM vec_objects_meta").fetchone()
                object_chunk_count = row_obj["cnt"] if row_obj else 0
            except Exception as exc:
                healthy = False
                error = str(exc)
            finally:
                conn.close()
        except Exception as exc:
            healthy = False
            error = str(exc)

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
        "corrupted": not healthy,
        "error": error,
    }
