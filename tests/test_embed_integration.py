"""Integration tests for the embed pipeline with sqlite-vec.

Tests the real encode -> write -> retrieve -> delete cycle against
sqlite-vec tables in a temporary paperforge.db, with the embedding
provider mocked to return fixed vectors.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import paperforge.config
from paperforge.worker._utils import pipeline_paths as _pp
EMBEDDING_DIM = 1536  # must match vec0 schema

paperforge.config.pipeline_paths = _pp

from paperforge.embedding.builder import (
    PaperEmbeddingJob,
    encode_payload,
    encode_paper_job,
    write_encoded_payload,
    prepare_payloads_for_entry,
    prepare_legacy_payload,
    prepare_body_payload,
    prepare_object_payload,
)
from paperforge.embedding.search import merge_retrieve
from paperforge.embedding._chroma import delete_paper_vectors




# ---------------------------------------------------------------------------
# Mock provider — deterministic fixed embeddings
# ---------------------------------------------------------------------------

class FixedProvider:
    """Provider that returns deterministic embeddings for any text."""

    def __init__(self, vault: Path | None = None):
        self.vault = vault

    def encode(self, texts: list[str]) -> list[list[float]]:
        import hashlib
        result = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            vec = [(h[i % 32] / 255.0) for i in range(EMBEDDING_DIM)]
            result.append(vec)
        return result

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]


@pytest.fixture
def mock_provider():
    return FixedProvider()


@pytest.fixture(autouse=True)
def _patch_providers(mock_provider):
    """Replace OpenAICompatibleProvider in builder and search modules."""
    with patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=mock_provider), \
         patch("paperforge.embedding.search.OpenAICompatibleProvider", return_value=mock_provider):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_body_units(paper_id: str, n: int = 2) -> list[dict]:
    return [
        {
            "unit_id": f"{paper_id}:body:n{n}:1-1:1-1",
            "paper_id": paper_id,
            "section_path": f"s{n}",
            "section_level": 1,
            "section_title": f"Section {n}",
            "unit_text": f"This is body text {n} for paper {paper_id}.",
            "unit_kind": "body",
            "part_ordinal": 0,
            "token_estimate": 10,
        }
        for n in range(1, n + 1)
    ]


def make_object_units(paper_id: str, n: int = 2) -> list[dict]:
    return [
        {
            "unit_id": f"{paper_id}:object:f{n}:1-1:1-1",
            "paper_id": paper_id,
            "section_path": "results",
            "object_kind": "figure",
            "object_label": f"Figure {n}",
            "caption_text": f"Caption for figure {n}.",
            "nearby_body_text": f"Nearby text for figure {n}.",
            "token_estimate": 15,
        }
        for n in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# Tests: basic payload preparation
# ---------------------------------------------------------------------------

class TestPayloadPrep:
    """Verify payload creation works (lightweight, not mock-dependent)."""

    def test_body_payload_has_correct_structure(self):
        units = make_body_units("p1", 2)
        payload = prepare_body_payload("p1", units)
        assert payload.collection_name == "paperforge_body"
        assert len(payload.texts) == 2
        assert payload.ids == [u["unit_id"] for u in units]
        assert all(m["unit_kind"] == "body" for m in payload.metadatas)

    def test_object_payload_joins_texts(self):
        units = make_object_units("p1", 1)
        payload = prepare_object_payload("p1", units)
        assert payload.collection_name == "paperforge_objects"
        assert "Figure 1" in payload.texts[0]
        assert "Caption for figure 1" in payload.texts[0]

    def test_legacy_payload_uses_fulltext_collection(self, tmp_path):
        chunks = [{"text": "Hello", "chunk_index": 0, "section": "intro",
                    "page_number": 1, "token_estimate": 5}]
        payload = prepare_legacy_payload("k1", chunks)
        assert payload.collection_name == "paperforge_fulltext"
        assert payload.texts == ["Hello"]


# ---------------------------------------------------------------------------
# Tests: encode -> write -> retrieve cycle with sqlite-vec
# ---------------------------------------------------------------------------

class TestEmbedRoundTrip:
    """Integration tests against sqlite-vec tables in paperforge.db."""

    def test_write_and_retrieve_body_units(self, tmp_path, mock_provider):
        """Write body units via sqlite-vec, retrieve them back."""
        key = "p1"
        units = make_body_units(key, 2)
        payload = prepare_body_payload(key, units)
        encoded = encode_payload(tmp_path, payload)
        write_encoded_payload(tmp_path, encoded)

        results = merge_retrieve(tmp_path, "body text", limit=5)
        assert len(results) >= 1
        assert results[0]["paper_id"] == key
        assert results[0]["source"] == "body_unit"

    def test_write_and_retrieve_object_units(self, tmp_path, mock_provider):
        """Write object units, retrieve them."""
        key = "p1"
        units = make_object_units(key, 2)
        payload = prepare_object_payload(key, units)
        encoded = encode_payload(tmp_path, payload)
        write_encoded_payload(tmp_path, encoded)

        results = merge_retrieve(tmp_path, "figure caption", limit=5)
        assert len(results) >= 1
        assert results[0]["source"] == "object_unit"

    def test_write_and_retrieve_legacy_chunks(self, tmp_path, mock_provider):
        """Write legacy chunks, retrieve them."""
        key = "p1"
        chunks = [
            {"text": f"Chunk {i}", "chunk_index": i, "section": "intro",
             "page_number": 1, "token_estimate": 5}
            for i in range(3)
        ]
        payload = prepare_legacy_payload(key, chunks)
        encoded = encode_payload(tmp_path, payload)
        write_encoded_payload(tmp_path, encoded)

        results = merge_retrieve(tmp_path, "Chunk", limit=5)
        assert len(results) >= 1
        assert results[0]["source"] == "legacy_chunk"

    def test_multiple_papers_retrieve_respects_per_paper_cap(self, tmp_path, mock_provider):
        """merge_retrieve caps at 2 results per paper."""
        for i in range(3):
            key = f"p{i}"
            payload = prepare_legacy_payload(key, [
                {"text": f"Paper {i} chunk", "chunk_index": 0, "section": "intro",
                 "page_number": 1, "token_estimate": 5},
                {"text": f"Paper {i} more", "chunk_index": 1, "section": "methods",
                 "page_number": 1, "token_estimate": 5},
                {"text": f"Paper {i} extra", "chunk_index": 2, "section": "results",
                 "page_number": 1, "token_estimate": 5},
            ])
            encoded = encode_payload(tmp_path, payload)
            write_encoded_payload(tmp_path, encoded)

        results = merge_retrieve(tmp_path, "Paper", limit=10)
        from collections import Counter
        counts = Counter(r["paper_id"] for r in results)
        assert all(v <= 2 for v in counts.values())

    def test_delete_paper_vectors_removes_data(self, tmp_path, mock_provider):
        """After delete, retrieval returns no results for that paper."""
        key = "p1"
        units = make_body_units(key, 1)
        payload = prepare_body_payload(key, units)
        encoded = encode_payload(tmp_path, payload)
        write_encoded_payload(tmp_path, encoded)

        assert len(merge_retrieve(tmp_path, "body", limit=5)) >= 1

        delete_paper_vectors(tmp_path, key)

        results = merge_retrieve(tmp_path, "body", limit=5)
        pid_results = [r for r in results if r["paper_id"] == key]
        assert len(pid_results) == 0

    def test_prepare_payloads_for_entry_returns_body_and_object(self, tmp_path, mock_provider):
        """prepare_payloads_for_entry returns correct payload types."""
        key = "p1"
        body_units = make_body_units(key, 1)
        object_units = make_object_units(key, 1)

        payloads = prepare_payloads_for_entry(
            tmp_path, key, has_body=True, has_object=True,
            body_units=body_units, object_units=object_units,
        )
        assert payloads is not None
        assert len(payloads) == 2
        names = [p.collection_name for p in payloads]
        assert "paperforge_body" in names
        assert "paperforge_objects" in names

    def test_encode_paper_job_processes_all_payloads(self, tmp_path, mock_provider):
        """encode_paper_job encodes all payloads for a paper."""
        key = "p1"
        body_payload = prepare_body_payload(key, make_body_units(key, 2))
        obj_payload = prepare_object_payload(key, make_object_units(key, 1))
        job = PaperEmbeddingJob(paper_id=key, payloads=[body_payload, obj_payload])

        bundle = encode_paper_job(tmp_path, job)

        assert bundle.paper_id == key
        assert bundle.chunk_count == 3  # 2 body + 1 object
        assert bundle.payloads is not None
        assert len(bundle.payloads) == 2
