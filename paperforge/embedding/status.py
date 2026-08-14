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
    """Get vector DB status from sqlite-vec companion tables.

    RC UX Seam (single source): observes the EFFECTIVE carrier (shadow
    candidate when it holds rows, else live) so status agrees with
    substrate/reconcile during an interrupted or in-flight shadow build.
    """
    from paperforge.embedding.substrate import effective_vector_db

    return get_embed_status_for_path(vault, effective_vector_db(vault), probe=probe)


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
            from paperforge.memory.db import open_live_reader

            reader = open_live_reader(vault, db_path)
            conn = reader.__enter__()
            vec_tables = {"vec_fulltext", "vec_body", "vec_objects"}
            meta_tables = {
                "vec_fulltext_meta",
                "vec_body_meta",
                "vec_objects_meta",
            }
            present_tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            meta_rows = sum(
                conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in meta_tables & present_tables
            )
            if vec_tables & present_tables or meta_rows:
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

                # A partially present vector layout is damaged. A memory DB
                # with no vector tables is simply not built yet.
                from paperforge.embedding.dim_detect import inspect_vector_layout

                layout = inspect_vector_layout(conn)
                if not layout.compatible or not layout.tables_complete:
                    healthy = False
                    error = layout.reason

                try:
                    row = conn.execute(
                        "SELECT sql FROM sqlite_master WHERE name='vec_body' AND type='table'"
                    ).fetchone()
                    if row:
                        import re

                        match = re.search(r"float\[(\d+)\]", row[0])
                        if match:
                            dimension = int(match.group(1))
                except Exception:
                    pass

                total_valid = valid_body + valid_object
                if probe and total_valid > 0 and dimension > 0:
                    zero_json = _json.dumps([0.0] * dimension)
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
            try:
                reader.__exit__(None, None, None)
            except Exception:
                pass

    model = get_api_model(vault)
    raw_total = body_chunk_count + object_chunk_count  # exclude legacy vec_fulltext_meta

    # RC UX Seam: `vector_state` must reflect the PUBLISHED identity, not
    # just row counts.  A live DB holding vectors built under an OLD
    # model/endpoint (e.g. before a config switch to Qwen@siliconflow) is
    # NOT searchable with the current config — reporting ready there made
    # the vector UI claim "已建立索引并可搜索" while reconcile/probe said
    # the substrate is incompatible.  Both sources must agree.
    identity_mismatch = False
    try:
        from paperforge.embedding.substrate import assess_vector_substrate

        substrate = assess_vector_substrate(vault, db_path=db_path)
        identity_mismatch = substrate.identity_changed
    except Exception:  # noqa: BLE001
        identity_mismatch = False

    if identity_mismatch:
        vector_state = "stale"
    elif total_valid > 0:
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
        "identity_changed": identity_mismatch,
    }
