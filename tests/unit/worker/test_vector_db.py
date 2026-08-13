from __future__ import annotations

import sqlite3

from paperforge.embedding.status import get_embed_status
from paperforge.memory.db import get_memory_db_path


def test_get_embed_status_treats_absent_vector_schema_as_not_built(tmp_path):
    """A memory DB with no vector tables is pristine, not corrupted."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    from tests.conftest import canonical_test_config

    canonical_test_config(vault)
    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE unrelated (x TEXT)")
    conn.commit()
    conn.close()

    status = get_embed_status(vault)

    assert status["db_exists"] is True
    assert status["vector_state"] == "not_built"
    assert status["healthy"] is True
    assert status["corrupted"] is False
    assert status["error"] == ""


def test_get_embed_status_uses_indexes_vectors_path_from_config(tmp_path):
    """DB path resolves from vault config (system_dir) — a DB placed at the
    configured location is reported as present."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"schema_version": 2, "vault_config":{"system_dir":"System"}}',
        encoding="utf-8",
    )
    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

    status = get_embed_status(vault)

    assert status["db_exists"] is True
    # No vector rows anywhere → not built, but healthy (schema queryable).
    assert status["vector_state"] == "not_built"
