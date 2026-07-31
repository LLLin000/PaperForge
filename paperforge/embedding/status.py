from __future__ import annotations

import json as _json
import logging
from pathlib import Path

from paperforge.embedding._config import get_api_model
from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
from paperforge.embedding.dim_detect import detect_embedding_dim
from paperforge.memory.schema import ensure_schema

logger = logging.getLogger(__name__)


def get_embed_status(vault: Path, *, probe: bool = False) -> dict:
    """Get vector DB status from sqlite-vec companion tables (live DB)."""
    return get_embed_status_for_path(vault, get_memory_db_path(vault), probe=probe)


def get_embed_status_for_path(vault: Path, db_path: Path, *, probe: bool = False) -> dict:
    exists = db_path.exists()
    chunk_count = 0
    object_chunk_count = 0
    body_chunk_count = 0
    error = ""
    healthy = True
    dimension = 0
    valid_body = 0
    valid_object = 0
    total_valid = 0
    if exists:
        conn = None
        try:
            conn = get_connection(db_path, read_only=True)
            try:
                ensure_vec_extension(conn)
            except Exception:
                pass
            row_ft = conn.execute("SELECT COUNT(*) AS cnt FROM vec_fulltext_meta").fetchone()
            chunk_count = row_ft["cnt"] if row_ft else 0
            row_body = conn.execute("SELECT COUNT(*) AS cnt FROM vec_body_meta").fetchone()
            body_chunk_count = row_body["cnt"] if row_body else 0
            row_obj = conn.execute("SELECT COUNT(*) AS cnt FROM vec_objects_meta").fetchone()
            object_chunk_count = row_obj["cnt"] if row_obj else 0
            row_vb = conn.execute("SELECT COUNT(*) FROM vec_body_meta WHERE unit_id <> ''").fetchone()
            valid_body = row_vb[0] if row_vb else 0
            row_vo = conn.execute("SELECT COUNT(*) FROM vec_objects_meta WHERE unit_id <> ''").fetchone()
            valid_object = row_vo[0] if row_vo else 0

            # Read dimension from vec0 table DDL
            try:
                row = conn.execute("SELECT sql FROM sqlite_master WHERE name='vec_body' AND type='table'").fetchone()
                if row:
                    import re
                    m = re.search(r"float\[(\d+)\]", row[0])
                    if m:
                        dimension = int(m.group(1))
            except Exception:
                pass

            # -- vec0 k-NN health probe (only when explicitly requested) --
            total_valid = valid_body + valid_object
            if probe and total_valid > 0 and dimension > 0:
                zero_vec = [0.0] * dimension
                zero_json = _json.dumps(zero_vec)
                conn.execute(
                    "SELECT 1 FROM vec_body WHERE embedding MATCH ? AND k = 1",
                    (zero_json,),
                )
        except Exception as exc:
            healthy = False
            error = str(exc)
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    model = get_api_model(vault)
    raw_total = body_chunk_count + object_chunk_count  # exclude legacy vec_fulltext_meta
    if total_valid > 0:
        vector_state = "ready"
    elif raw_total > 0:
        vector_state = "stale"
    else:
        vector_state = "not_built"

    return {
        "db_exists": exists,
        "chunk_count": chunk_count,
        "body_chunk_count": body_chunk_count,
        "object_chunk_count": object_chunk_count,
        "total_chunks": raw_total,
        "dimension": dimension,
        "model": model,
        "mode": "api",
        "healthy": healthy,
        "corrupted": not healthy,
        "error": error,
        "valid_body_chunk_count": valid_body,
        "valid_object_chunk_count": valid_object,
        "valid_total_chunks": total_valid,
        "vector_state": vector_state,
    }
