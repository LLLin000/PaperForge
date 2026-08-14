"""Test ChromaDB → vec0 migration, idempotency, and prune clean-up from both backends."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import canonical_test_config

# ── helpers ─────────────────────────────────────────────────────────────────


def _make_minimal_vault(tmp_path: Path) -> Path:
    """Create a vault with just enough config for paperforge_paths()."""
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(
        vault,
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        control_dir="LiteratureControl",
        base_dir="05_Bases",
        skill_dir=".opencode/skills",
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


def test_migrate_skips_dimension_mismatch(tmp_path):
    """Vectors from a different embedding model (dimension != vec0 DDL) must
    be SKIPPED with a warning — vec0 rejects mismatched inserts and a lucky
    dimension collision would search in a meaningless semantic space."""
    vault = _make_minimal_vault(tmp_path)
    _seed_chromadb(
        vault,
        [
            {
                "collection": "paperforge_fulltext",
                "ids": ["paperforge_fulltext:OLD_0"],
                "embeddings": [[0.1] * 1024],  # old model, 1024-dim
                "documents": ["old chunk"],
                "metadatas": [{"paper_id": "OLD", "chunk_index": 0}],
            },
        ],
    )
    from paperforge.embedding._chroma import migrate_chroma_to_vec0

    count = migrate_chroma_to_vec0(vault)
    assert count == 0, "dimension-mismatched vectors must not migrate"
    assert _count_meta_rows(vault, "vec_fulltext_meta") == 0
    # No legacy lineage written for a skipped paper.
    from paperforge.memory.db import get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(vault))
    row = conn.execute(
        "SELECT 1 FROM lineage WHERE paper_id='OLD' AND layer='vector'"
    ).fetchone()
    conn.close()
    assert row is None


def test_migrated_legacy_fulltext_is_current_when_identity_matches(tmp_path):
    """Migrated full-text vectors get legacy lineage; the probe reports the
    paper's vector state as CURRENT when the embedding config is unchanged
    (same model/dimension ⇒ query encodes into the same space ⇒ searchable)."""
    vault = _make_minimal_vault(tmp_path)
    _seed_chromadb(
        vault,
        [
            {
                "collection": "paperforge_fulltext",
                "ids": ["paperforge_fulltext:LEGACY_0"],
                "embeddings": [[0.1] * 1536],
                "documents": ["legacy chunk"],
                "metadatas": [{"paper_id": "LEGACY", "chunk_index": 0}],
            },
        ],
    )
    from paperforge.embedding._chroma import migrate_chroma_to_vec0
    from paperforge.lineage import probe_lineage

    # Register LEGACY in the probe's paper universe (no index in this
    # minimal vault — an OCR dir suffices for _paper_keys).
    (vault / '99_System' / 'PaperForge' / 'ocr' / 'LEGACY').mkdir(parents=True, exist_ok=True)

    count = migrate_chroma_to_vec0(vault)
    assert count == 1
    payload = probe_lineage(vault)
    assert payload["papers"]["LEGACY"]["vector"] == "current", (
        "legacy fulltext + unchanged config must be searchable (gate passes)"
    )
    assert payload["papers"]["LEGACY"]["retrieval"] == "missing", (
        "legacy products have no manifest — retrieval layer intentionally absent"
    )
    assert payload["papers"]["LEGACY"]["ocr"] == "missing"


def test_migrated_legacy_fulltext_stale_after_config_change(tmp_path):
    """If the embedding config changes after migration (model/dim), the
    migrated vectors are STALE — a query under the new config would run in a
    different semantic space (or dimension-mismatch).  Probe must say stale
    so the reader gate drops them and the UI offers a rebuild."""
    vault = _make_minimal_vault(tmp_path)
    _seed_chromadb(
        vault,
        [
            {
                "collection": "paperforge_fulltext",
                "ids": ["paperforge_fulltext:LEG2_0"],
                "embeddings": [[0.1] * 1536],
                "documents": ["legacy chunk"],
                "metadatas": [{"paper_id": "LEG2", "chunk_index": 0}],
            },
        ],
    )
    (vault / "99_System" / "PaperForge" / "ocr" / "LEG2").mkdir(parents=True, exist_ok=True)
    from paperforge.embedding._chroma import migrate_chroma_to_vec0
    from paperforge.lineage import probe_lineage

    assert migrate_chroma_to_vec0(vault) == 1
    assert probe_lineage(vault)["papers"]["LEG2"]["vector"] == "current"

    # Simulate an embedding-config change: the DDL is rebuilt at a different
    # dimension (as a new model's build would do).
    from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension

    conn = get_connection(get_memory_db_path(vault))
    ensure_vec_extension(conn)
    # Rebuild ALL vec tables at the new dimension, as a new-model build would.
    for t in ("vec_fulltext", "vec_body", "vec_objects"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.execute(f"CREATE VIRTUAL TABLE {t} USING vec0(embedding float[1024])")
    conn.commit()
    conn.close()

    payload = probe_lineage(vault)
    assert payload["papers"]["LEG2"]["vector"] == "stale", (
        "migrated legacy vectors must go stale when the embedding config changes"
    )
