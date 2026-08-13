"""RC UX Seam: embed status must agree with the substrate authority.

vector_state must NOT be "ready" merely because rows exist — the live DB
may hold vectors built under an OLD identity (model/endpoint) while config
points elsewhere.  embed status, probe memory, and reconcile all read the
SAME assess_vector_substrate; this test locks that single source.
"""

from __future__ import annotations

import json
import sqlite3

from tests.embedding.conftest import ensure_vec_extension, get_connection, get_memory_db_path
from tests.embedding.conftest import ensure_schema


def _seed_identity(conn: sqlite3.Connection, *, model: str, endpoint: str, version: int) -> None:
    conn.execute("DELETE FROM build_state")
    rows = {
        "model": model,
        "vector_provider_endpoint": endpoint,
        "vector_identity_version": str(version),
        "status": "completed",
    }
    for k, v in rows.items():
        conn.execute("INSERT OR REPLACE INTO build_state(key, value) VALUES (?, ?)", (k, v))
    conn.commit()


def test_embed_status_reports_stale_when_identity_mismatch(
    seeded_vault, monkeypatch
) -> None:
    """Live rows exist but were built under text-embedding-3-small@openai
    while config now targets Qwen@siliconflow → vector_state must be stale,
    never ready."""
    from paperforge.embedding.status import get_embed_status_for_path

    vault = seeded_vault
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO vec_fulltext_meta(rowid, paper_id, chunk_index, text) VALUES (2, 'p2', 0, 'x')"
    )
    cur = conn.execute(
        "INSERT INTO vec_body(embedding) VALUES (?)",
        [json.dumps([0.1] * 1536)],
    )
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, unit_id) VALUES (?, 'p2', 'u2')",
        (cur.lastrowid,),
    )
    _seed_identity(
        conn,
        model="text-embedding-3-small",
        endpoint="https://api.openai.com/v1",
        version=0,
    )
    conn.close()

    # Point config at the NEW identity (Qwen@siliconflow).  substrate
    # imports get_api_model/get_effective_api_base_url from _config at call
    # time, so patch those (not the status-module copies).
    monkeypatch.setattr(
        "paperforge.embedding._config.get_api_model",
        lambda vault: "Qwen/Qwen3-Embedding-4B",
    )
    monkeypatch.setattr(
        "paperforge.embedding._config.get_effective_api_base_url",
        lambda vault: "https://api.siliconflow.cn/v1",
    )

    status = get_embed_status_for_path(vault, db_path)
    assert status["vector_state"] == "stale"
    assert status["identity_changed"] is True


def test_embed_status_reports_ready_when_identity_matches(
    seeded_vault, monkeypatch
) -> None:
    """Rows built under the SAME identity as config → ready is honest."""
    from paperforge.embedding.status import get_embed_status_for_path

    vault = seeded_vault
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO vec_fulltext_meta(rowid, paper_id, chunk_index, text) VALUES (3, 'p3', 0, 'y')"
    )
    cur = conn.execute(
        "INSERT INTO vec_body(embedding) VALUES (?)",
        [json.dumps([0.1] * 1536)],
    )
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, unit_id) VALUES (?, 'p3', 'u3')",
        (cur.lastrowid,),
    )
    _seed_identity(
        conn,
        model="Qwen/Qwen3-Embedding-4B",
        endpoint="https://api.siliconflow.cn/v1",
        version=1,
    )
    conn.close()

    monkeypatch.setattr(
        "paperforge.embedding._config.get_api_model",
        lambda vault: "Qwen/Qwen3-Embedding-4B",
    )
    monkeypatch.setattr(
        "paperforge.embedding._config.get_effective_api_base_url",
        lambda vault: "https://api.siliconflow.cn/v1",
    )

    status = get_embed_status_for_path(vault, db_path)
    assert status["vector_state"] == "ready"
    assert status["identity_changed"] is False
