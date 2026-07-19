"""Seed a minimal vault with memory DB and vec0 meta rows for embed resume tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema


@pytest.fixture
def seeded_vault(tmp_path: Path) -> Path:
    """Build a minimal vault with memory DB populated with fake vec0 meta rows."""
    vault = tmp_path / "testvault"
    vault.mkdir(parents=True)

    # Minimal config so paperforge paths resolve
    (vault / "System" / "PaperForge").mkdir(parents=True)
    cfg = {
        "exporter_dir": "System/PaperForge/exporter",
        "zotero_storage": "System/PaperForge/storage",
        "memory_db": "System/PaperForge/memory/paperforge.db",
    }
    (vault / "paperforge.json").write_text(json.dumps(cfg), encoding="utf-8")

    # Create memory DB with vec0 schema
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)

    # Insert a fake row into vec_fulltext_meta so resume finds "existing data"
    conn.execute(
        "INSERT INTO vec_fulltext_meta(rowid, paper_id, chunk_index, text) VALUES (1, 'test_paper', 0, 'hello world')"
    )
    conn.commit()
    conn.close()

    return vault
