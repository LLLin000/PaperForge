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
        force=False,
    )

    # Resume gates need a real vector-DB path to exist on disk
    mock_db_path = tmp_path / "vectordb"
    if resume:
        mock_db_path.mkdir(parents=True, exist_ok=True)

    # Build the mock dict before patching
    mock_refs: dict = {
        # Index & preflight
        "read_index": MagicMock(return_value=papers),
        "_preflight_check": MagicMock(return_value={"ok": True}),
        # Per-entry helpers (default: legacy fulltext path)
        "_has_body_units_in_db": MagicMock(return_value=False),
        "_has_object_units_in_db": MagicMock(return_value=False),
        "progress_bar": MagicMock(side_effect=lambda x, **kw: x),
        # Resume gates
        "get_vector_db_path": MagicMock(return_value=mock_db_path),
        "read_vector_build_state": MagicMock(return_value={"status": "idle"}),
        "_assert_collections_healthy": MagicMock(return_value=(True, "")),
        # State bookkeeping
        "mark_vector_build_state": MagicMock(),
        "write_vector_runtime": MagicMock(),
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

    patcher = patch.multiple("paperforge.commands.embed", **mock_refs)
    patcher.start()
    try:
        rc = run(args)
    finally:
        patcher.stop()

    return rc, mock_refs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProcessedCount:
    """processed_count advances for both skips and embeds."""

    def test_resume_skip_increments_processed_count(self, tmp_path):
        """Resume-mode hash match: papers are skipped and *do* advance
        processed_count without touching delete_paper_vectors."""
        papers = [
            {"zotero_key": "k1", "ocr_status": "done", "fulltext_path": "p1.pdf"},
            {"zotero_key": "k2", "ocr_status": "done", "fulltext_path": "p2.pdf"},
        ]

        # Simulate matching body & object hashes so resume skips
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1"],
            "metadatas": [
                {
                    "body_units_hash": "hash_v1",
                    "object_units_hash": "hash_v1",
                    "retrieval_policy_version": "v1",
                }
            ],
        }

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
                "get_collection": MagicMock(return_value=mock_collection),
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
