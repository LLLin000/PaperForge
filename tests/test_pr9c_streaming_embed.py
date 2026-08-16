"""Tests for PR9C: Streaming Embed Pipeline.

Tests the refactored ``run()`` in ``paperforge.commands.embed``, which uses
a sliding-window ``_submit_job``/``_complete_one`` loop and a unified
``processed_count`` that advances on both skips and encodes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Import shim: embed.py may transitively access pipeline_paths
import paperforge.config
from paperforge.worker._utils import pipeline_paths as _pp

paperforge.config.pipeline_paths = _pp

from tests.conftest import canonical_test_config


@pytest.fixture(autouse=True)
def _canonical_vault_config(tmp_path: Path) -> None:
    canonical_test_config(tmp_path)

from paperforge.embedding.builder import (
    EmbeddingPayload,
    EncodedPayload,
    PaperEmbeddingJob,
    PaperEncodedBundle,
)
from paperforge.commands.embed import run


# ---------------------------------------------------------------------------
# Helper: fake bundle factory
# ---------------------------------------------------------------------------

def _make_bundle(key: str, n_chunks: int = 1) -> PaperEncodedBundle:
    """Build a minimal PaperEncodedBundle for testing."""
    return PaperEncodedBundle(
        paper_id=key,
        payloads=[
            EncodedPayload(
                collection_name="paperforge_body",
                texts=[f"text{i}"],
                ids=[f"{key}_{i}"],
                metadatas=[{"paper_id": key}],
                embeddings=[[0.1] * 256],
            )
            for i in range(n_chunks)
        ],
        chunk_count=n_chunks,
    )


# ---------------------------------------------------------------------------
# Mock harness for run()
#
# patch.multiple in Python 3.14 returns a single _patch object (not a dict),
# so we use start()/stop() and keep the mock references ourselves.
# ---------------------------------------------------------------------------

def _call_run(
    tmp_path: Path,
    papers: list[dict],
    *,
    resume: bool = False,
    force: bool = False,
    overrides: dict | None = None,
) -> tuple[int, dict]:
    """Call ``run()`` with all heavyweight dependencies mocked.

    Returns ``(return_code, mock_refs)`` where *mock_refs* is the dict of
    ``MagicMock`` instances that were injected into the module namespace.
    Assert on them after the call — call-count state persists.
    """
    args = argparse.Namespace(
        vault_path=tmp_path,
        embed_subcommand="build",
        json=False,
        resume=resume,
        force=force,
    )

    # Resume gates need a real vector-DB path to exist on disk
    mock_db_path = tmp_path / "vectordb"
    if resume:
        mock_db_path.mkdir(parents=True, exist_ok=True)

    # Build the mock dict before patching
    mock_refs: dict = {
        # Index & preflight
        "read_index": MagicMock(return_value=papers),
        "assess_embedding_preconditions": MagicMock(return_value={"ok": True}),
        # Per-entry helpers (default: legacy fulltext path)
        "_has_body_units_in_db": MagicMock(return_value=False),
        "_has_object_units_in_db": MagicMock(return_value=False),
        "progress_bar": MagicMock(side_effect=lambda x, **kw: x),
        # Round 7 (P1-2): ensure_vec_tables returns the dimension it used —
        # the verifier uses it as the expected dimension.
        "ensure_vec_tables": MagicMock(return_value=1536),
        # Resume gates
        # State bookkeeping
        "mark_vector_build_state": MagicMock(),
        "get_embed_status": MagicMock(
            return_value={
                "chunk_count": 0,
                "body_chunk_count": 0,
                "object_chunk_count": 0,
                "total_chunks": 0,
                "mode": "chroma",
                "model": "test-model",
                "db_exists": True,
                "healthy": True,
                "corrupted": False,
                "error": "",
            }
        ),
        # Payload preparation (default: return one payload per entry)
        "prepare_payloads_for_entry": MagicMock(
            side_effect=lambda _vault, key, *a, **kw: [
                EmbeddingPayload(
                    "test_col",
                    ["t"],
                    [f"{key}_id1"],
                    [{"paper_id": key}],
                )
            ]
        ),
        # Encode & write
        "encode_paper_job": MagicMock(),
        "delete_paper_vectors": MagicMock(),
        "write_encoded_payload": MagicMock(),
    }
    if overrides:
        mock_refs.update(overrides)

    # M3-A: the build core moved to the embedding SERVICE; run() (CLI)
    # owns read_index + the Obsidian preflight until M3-B.  Mock each
    # layer where it lives.
    cli_refs = {k: v for k, v in mock_refs.items() if k == "read_index"}
    service_refs = {k: v for k, v in mock_refs.items() if k != "read_index"}

    patcher = patch.multiple("paperforge.services.embedding", **service_refs)
    patcher.start()
    cli_patcher = patch.multiple("paperforge.commands.embed", **cli_refs)
    cli_patcher.start()
    try:
        rc = run(args)
    finally:
        cli_patcher.stop()
        patcher.stop()

    return rc, mock_refs


# ---------------------------------------------------------------------------
# Tests

def test_force_rebuild_initializes_existing_vector_database(tmp_path: Path) -> None:
    """Forced rebuild must use module helpers rather than function-local imports."""
    from paperforge.memory.db import get_connection, get_memory_db_path

    db_path = get_memory_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    get_connection(db_path).close()

    rc, _ = _call_run(tmp_path, [{"ocr_status": "done"}], force=True)

    assert rc == 0
# ---------------------------------------------------------------------------

class TestLineagePublish:
    """#162/T1: a forced shadow rebuild writes vector lineage rows into the
    candidate; after the atomic publish swap the new live DB carries them."""

    def test_shadow_publish_writes_vector_lineage_rows(self, tmp_path: Path) -> None:
        import json as _json

        from paperforge.lineage import compute_embedding_identity, compute_vector_identity
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema
        from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, build_paper_manifest
        from tests.conftest import canonical_test_config

        canonical_test_config(tmp_path, system_dir="System")
        db_path = get_memory_db_path(tmp_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(db_path)
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
            manifest = build_paper_manifest(
                paper_id="k1",
                ocr_result_hash="a" * 64,
                structure_tree_bytes=b"{}",
                retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
                body_units=[],
                object_units=[],
                source_paths={},
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("manifest:k1", _json.dumps(manifest)),
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')"
            )
            conn.commit()
        finally:
            conn.close()

        papers = [{"zotero_key": "k1", "ocr_status": "done", "fulltext_path": "fulltext.md"}]
        (tmp_path / "fulltext.md").write_text(
            "Some fulltext content for k1. " * 10, encoding="utf-8"
        )

        def _bundle_at_dim(_vault, job):
            bundle = _make_bundle(job.paper_id)
            # The candidate vec tables are created at the model-detected
            # dimension (1536 for the default model) — match it.
            return PaperEncodedBundle(
                paper_id=bundle.paper_id,
                payloads=[
                    EncodedPayload(
                        collection_name=p.collection_name,
                        texts=p.texts,
                        ids=p.ids,
                        metadatas=p.metadatas,
                        embeddings=[[0.1] * 1536 for _ in p.embeddings],
                    )
                    for p in bundle.payloads
                ],
                chunk_count=bundle.chunk_count,
            )

        rc, _refs = _call_run(
            tmp_path,
            papers,
            force=True,
            overrides={
                "encode_paper_job": MagicMock(side_effect=_bundle_at_dim),
            },
        )
        assert rc == 0, "shadow rebuild must succeed"

        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(str(db_path))
        try:
            row = conn.execute(
                "SELECT identity, derived_from, embedding_identity FROM lineage "
                "WHERE paper_id='k1' AND layer='vector'"
            ).fetchone()
            assert row is not None, "lineage row missing after publish"
            assert row[1] == manifest["retrieval_identity"]
            # The stored identity equals the canonical composition.
            expected = compute_vector_identity(
                retrieval_identity=manifest["retrieval_identity"],
                embedding_identity=row[2],
            )
            assert row[0] == expected
        finally:
            conn.close()


class TestProcessedCount:
    """processed_count advances for both skips and embeds."""

    def test_resume_skip_increments_processed_count(self, tmp_path):
        """Resume-mode hash match: papers are skipped and *do* advance
        processed_count without touching delete_paper_vectors."""
        papers = [
            {"zotero_key": "k1", "ocr_status": "done", "fulltext_path": "p1.pdf"},
            {"zotero_key": "k2", "ocr_status": "done", "fulltext_path": "p2.pdf"},
        ]

        # Set up paperforge.db with matching hashes so resume skips
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema
        db_path = get_memory_db_path(tmp_path)
        conn = get_connection(db_path)
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
            for key in ("k1", "k2"):
                conn.execute(
                    "INSERT INTO vec_body_meta(rowid, paper_id, body_units_hash, retrieval_policy_version) VALUES (?, ?, ?, ?)",
                    (1 if key == "k1" else 2, key, "hash_v1", "v1")
                )
                conn.execute(
                    "INSERT INTO vec_objects_meta(rowid, paper_id, object_units_hash, retrieval_policy_version) VALUES (?, ?, ?, ?)",
                    (3 if key == "k1" else 4, key, "hash_v1", "v1")
                )
            # Round 7: a library without vector_identity_version is a legacy
            # library → routed to shadow rebuild (which would defeat the
            # resume-skip under test).  Mark it current so resume semantics
            # are exercised, not the legacy-migration path.
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')"
            )
            conn.commit()
        finally:
            conn.close()

        mock_body_units = [{"some": "data"}]
        mock_obj_units = [{"some": "data"}]

        rc, refs = _call_run(
            tmp_path,
            papers,
            resume=True,
            overrides={
                "_has_body_units_in_db": MagicMock(return_value=True),
                "_has_object_units_in_db": MagicMock(return_value=True),
                "get_body_units_for_embedding": MagicMock(return_value=mock_body_units),
                "get_object_units_for_embedding": MagicMock(return_value=mock_obj_units),
                "compute_body_units_hash": MagicMock(return_value="hash_v1"),
                "compute_object_units_hash": MagicMock(return_value="hash_v1"),
                "RETRIEVAL_POLICY_VERSION": "v1",
                "encode_paper_job": MagicMock(),
                "delete_paper_vectors": MagicMock(),
                "write_encoded_payload": MagicMock(),
            },
        )

        # Both papers skipped → no encode, no delete
        refs["encode_paper_job"].assert_not_called()
        refs["delete_paper_vectors"].assert_not_called()
        assert rc == 0

    def test_no_payload_skip_increments_processed_count(self, tmp_path):
        """A paper with no payload (prepare_payloads_for_entry returns
        None) advances processed_count and does NOT enter the encode
        loop."""
        papers = [
            {"zotero_key": "k1", "ocr_status": "done", "fulltext_path": "p1.pdf"},
            {"zotero_key": "k2", "ocr_status": "done", "fulltext_path": "p2.pdf"},
        ]

        def _prep_side_effect(_vault, key, *a, **kw):
            if key == "k1":
                return None  # triggers no-payload skip path
            return [
                EmbeddingPayload(
                    "test_col",
                    ["t"],
                    [f"{key}_id1"],
                    [{"paper_id": key}],
                )
            ]

        encode_mock = MagicMock(
            side_effect=lambda _vault, job: _make_bundle(job.paper_id, n_chunks=1)
        )
        delete_mock = MagicMock()
        write_mock = MagicMock()

        rc, refs = _call_run(
            tmp_path,
            papers,
            overrides={
                "prepare_payloads_for_entry": MagicMock(
                    side_effect=_prep_side_effect
                ),
                "encode_paper_job": encode_mock,
                "delete_paper_vectors": delete_mock,
                "write_encoded_payload": write_mock,
            },
        )

        # k1 (no payload) → embed never called for k1
        assert encode_mock.call_count == 1
        # Only k2 was encoded → k2 vector deleted
        assert delete_mock.call_count == 1
        assert rc == 0


class TestEncodeFailure:
    """Encode failure causes _complete_one to return False → run() → 1."""

    def test_encode_failure_returns_1(self, tmp_path):
        """When encode_paper_job raises, run() returns 1."""
        papers = [
            {"zotero_key": "k1", "ocr_status": "done", "fulltext_path": "p1.pdf"},
        ]

        encode_mock = MagicMock(side_effect=ValueError("API error"))
        delete_mock = MagicMock()
        write_mock = MagicMock()

        rc, refs = _call_run(
            tmp_path,
            papers,
            overrides={
                "encode_paper_job": encode_mock,
                "delete_paper_vectors": delete_mock,
                "write_encoded_payload": write_mock,
            },
        )

        assert rc == 1
        # No successful embed → no delete, no write
        delete_mock.assert_not_called()
        write_mock.assert_not_called()


class TestSuccessfulFlow:
    """Happy path: all papers encode, delete/write cycle runs."""

    def test_all_succeeds_calls_delete_and_write(self, tmp_path):
        """Every paper encodes successfully → delete + write for each."""
        papers = [
            {"zotero_key": "k1", "ocr_status": "done", "fulltext_path": "p1.pdf"},
            {"zotero_key": "k2", "ocr_status": "done", "fulltext_path": "p2.pdf"},
        ]

        encode_mock = MagicMock(
            side_effect=lambda _vault, job: _make_bundle(job.paper_id, n_chunks=1)
        )
        delete_mock = MagicMock()
        write_mock = MagicMock()

        rc, refs = _call_run(
            tmp_path,
            papers,
            overrides={
                "encode_paper_job": encode_mock,
                "delete_paper_vectors": delete_mock,
                "write_encoded_payload": write_mock,
            },
        )

        assert rc == 0
        # Both paper vectors deleted
        assert delete_mock.call_count == 2
        delete_mock.assert_has_calls(
            [call(tmp_path, "k1"), call(tmp_path, "k2")], any_order=True
        )
        # Payloads written for each paper
        assert write_mock.call_count >= 2
