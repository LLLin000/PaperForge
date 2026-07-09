"""Test ChromaDB → vec0 migration, idempotency, and prune clean-up from both backends."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ── helpers ─────────────────────────────────────────────────────────────────


def _make_minimal_vault(tmp_path: Path) -> Path:
    """Create a vault with just enough config for paperforge_paths()."""
    vault = tmp_path / "vault"
    vault.mkdir()
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "system_dir": "99_System",
                "resources_dir": "03_Resources",
                "literature_dir": "Literature",
                "control_dir": "LiteratureControl",
                "base_dir": "05_Bases",
                "skill_dir": ".opencode/skills",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Ensure memory-db parent dir exists (used by get_vector_db_path)
    (vault / "99_System" / "PaperForge" / "indexes").mkdir(parents=True, exist_ok=True)
    return vault


def _seed_chromadb(vault: Path, vectors: list[dict]) -> None:
    """Populate a ChromaDB at the vault's vector path with test data."""
    import chromadb

    from paperforge.embedding._chroma import get_vector_db_path

    db_path = get_vector_db_path(vault)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))

    for group in vectors:
        coll = client.get_or_create_collection(name=group["collection"])
        coll.add(ids=group["ids"], embeddings=group["embeddings"], documents=group["documents"], metadatas=group["metadatas"])


def _count_meta_rows(vault: Path, meta_table: str) -> int:
    """Return row count in a vec0 companion meta table."""
    from paperforge.memory.db import get_connection, get_memory_db_path

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {meta_table}").fetchone()
    conn.close()
    return row["cnt"] if row else 0


# ── tests ────────────────────────────────────────────────────────────────────


def test_migrate_chroma_to_vec0(tmp_path):
    """Migrate vectors from ChromaDB → vec0 and verify data fidelity."""
    vault = _make_minimal_vault(tmp_path)

    # Seed ChromaDB with two papers across three collections
    _seed_chromadb(
        vault,
        [
            {
                "collection": "paperforge_fulltext",
                "ids": ["paperforge_fulltext:PAPER_A_0", "paperforge_fulltext:PAPER_A_1"],
                "embeddings": [[0.1] * 1536, [0.2] * 1536],
                "documents": ["chunk A0", "chunk A1"],
                "metadatas": [{"paper_id": "PAPER_A", "chunk_index": 0}, {"paper_id": "PAPER_A", "chunk_index": 1}],
            },
            {
                "collection": "paperforge_body",
                "ids": ["paperforge_body:PAPER_A_0"],
                "embeddings": [[0.3] * 1536],
                "documents": ["body A0"],
                "metadatas": [{"paper_id": "PAPER_A", "chunk_index": 0}],
            },
            {
                "collection": "paperforge_objects",
                "ids": ["paperforge_objects:PAPER_B_0", "paperforge_objects:PAPER_B_1"],
                "embeddings": [[0.4] * 1536, [0.5] * 1536],
                "documents": ["object B0", "object B1"],
                "metadatas": [
                    {"paper_id": "PAPER_B", "chunk_index": 0},
                    {"paper_id": "PAPER_B", "chunk_index": 1},
                ],
            },
        ],
    )

    from paperforge.embedding._chroma import migrate_chroma_to_vec0

    # Act
    count = migrate_chroma_to_vec0(vault)

    # Assert total count
    assert count == 5  # 2 fulltext + 1 body + 2 objects

    # Verify each meta table
    assert _count_meta_rows(vault, "vec_fulltext_meta") == 2
    assert _count_meta_rows(vault, "vec_body_meta") == 1
    assert _count_meta_rows(vault, "vec_objects_meta") == 2

    # Verify data integrity
    from paperforge.memory.db import get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(vault))
    rows = conn.execute("SELECT paper_id, chunk_index, text FROM vec_fulltext_meta ORDER BY chunk_index").fetchall()
    assert [(r["paper_id"], r["chunk_index"], r["text"]) for r in rows] == [
        ("PAPER_A", 0, "chunk A0"),
        ("PAPER_A", 1, "chunk A1"),
    ]
    rows = conn.execute("SELECT paper_id, chunk_index, text FROM vec_body_meta ORDER BY chunk_index").fetchall()
    assert [(r["paper_id"], r["chunk_index"], r["text"]) for r in rows] == [
        ("PAPER_A", 0, "body A0"),
    ]
    rows = conn.execute("SELECT paper_id, chunk_index, text FROM vec_objects_meta ORDER BY chunk_index").fetchall()
    assert [(r["paper_id"], r["chunk_index"], r["text"]) for r in rows] == [
        ("PAPER_B", 0, "object B0"),
        ("PAPER_B", 1, "object B1"),
    ]
    conn.close()


def test_idempotent_migration(tmp_path):
    """Running migration twice must not duplicate entries."""
    vault = _make_minimal_vault(tmp_path)

    _seed_chromadb(
        vault,
        [
            {
                "collection": "paperforge_fulltext",
                "ids": ["paperforge_fulltext:PAPER_C_0"],
                "embeddings": [[0.6] * 1536],
                "documents": ["chunk C0"],
                "metadatas": [{"paper_id": "PAPER_C", "chunk_index": 0}],
            },
        ],
    )

    from paperforge.embedding._chroma import migrate_chroma_to_vec0

    # First run
    first = migrate_chroma_to_vec0(vault)
    assert first == 1

    # Second run — no error, count 0 (no new vectors)
    second = migrate_chroma_to_vec0(vault)
    assert second == 0

    # Still exactly 1 row
    assert _count_meta_rows(vault, "vec_fulltext_meta") == 1


def test_migrate_no_chromadb_dir(tmp_path):
    """No-op when no ChromaDB directory exists."""
    vault = _make_minimal_vault(tmp_path)

    from paperforge.embedding._chroma import migrate_chroma_to_vec0

    count = migrate_chroma_to_vec0(vault)
    assert count == 0


def test_migrate_empty_collection(tmp_path):
    """No-op when ChromaDB exists but collection is empty."""
    vault = _make_minimal_vault(tmp_path)

    import chromadb

    from paperforge.embedding._chroma import get_vector_db_path

    db_path = get_vector_db_path(vault)
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    client.get_or_create_collection(name="paperforge_fulltext")

    from paperforge.embedding._chroma import migrate_chroma_to_vec0

    count = migrate_chroma_to_vec0(vault)
    assert count == 0


def test_prune_deletes_from_both_backends(tmp_path):
    """delete_paper_vectors removes vectors from ChromaDB AND vec0 tables."""
    vault = _make_minimal_vault(tmp_path)

    # Seed ChromaDB
    _seed_chromadb(
        vault,
        [
            {
                "collection": "paperforge_fulltext",
                "ids": ["paperforge_fulltext:PAPER_D_0", "paperforge_fulltext:PAPER_D_1"],
                "embeddings": [[0.7] * 1536, [0.8] * 1536],
                "documents": ["chunk D0", "chunk D1"],
                "metadatas": [{"paper_id": "PAPER_D", "chunk_index": 0}, {"paper_id": "PAPER_D", "chunk_index": 1}],
            },
            {
                "collection": "paperforge_body",
                "ids": ["paperforge_body:PAPER_D_0"],
                "embeddings": [[0.9] * 1536],
                "documents": ["body D0"],
                "metadatas": [{"paper_id": "PAPER_D", "chunk_index": 0}],
            },
        ],
    )

    from paperforge.embedding._chroma import delete_paper_vectors, migrate_chroma_to_vec0

    # Migrate first so vec0 has the data
    migrate_chroma_to_vec0(vault)
    assert _count_meta_rows(vault, "vec_fulltext_meta") == 2
    assert _count_meta_rows(vault, "vec_body_meta") == 1

    # Verify ChromaDB has data before prune
    chroma_dir = _get_chroma_dir(vault)
    import chromadb

    chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
    coll_ft = chroma_client.get_collection(name="paperforge_fulltext")
    assert len(coll_ft.get()["ids"]) == 2

    # Act: delete vectors for PAPER_D
    n = delete_paper_vectors(vault, "PAPER_D")
    assert n == 3  # 2 fulltext + 1 body

    # Assert vec0 tables are empty for this paper
    assert _count_meta_rows(vault, "vec_fulltext_meta") == 0
    assert _count_meta_rows(vault, "vec_body_meta") == 0

    # Assert ChromaDB is also empty for this paper
    coll_ft = chroma_client.get_collection(name="paperforge_fulltext")
    assert coll_ft.get()["ids"] == []
    coll_body = chroma_client.get_collection(name="paperforge_body")
    assert coll_body.get()["ids"] == []


# ── helpers ──────────────────────────────────────────────────────────────────


def _get_chroma_dir(vault: Path) -> Path:
    from paperforge.embedding._chroma import get_vector_db_path

    return get_vector_db_path(vault)
