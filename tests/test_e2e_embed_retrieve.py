"""E2E tests for the embed -> retrieve pipeline using fixture PDFs.

Tests cover the full round-trip: preparing payloads, encoding with a mocked
provider, writing to sqlite-vec vec0 tables, and retrieving via merge_retrieve.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from paperforge.embedding.builder import (
    EmbeddingPayload,
    encode_payload,
    prepare_body_payload,
    prepare_object_payload,
    write_encoded_payload,
)
from paperforge.embedding.search import merge_retrieve

# Matches the vec0 table schema (floats[1536]) in paperforge/memory/schema.py
EMBEDDING_DIM = 1536


class FixedProvider:
    """Provider that returns deterministic embeddings for any text.

    Each text's MD5 hash seeds a reproducible 1536-dim vector so the same
    query always produces the same results.  This avoids contacting any real
    embedding API while still exercising the full sqlite-vec pipeline.
    """

    def __init__(self, vault: Path | None = None):
        self.vault = vault

    def encode(self, texts: list[str]) -> list[list[float]]:
        import hashlib

        result: list[list[float]] = []
        for t in texts:
            h = hashlib.md5(t.encode()).digest()
            # Stretch 16 hashed bytes to EMBEDDING_DIM floats in [0, 1]
            vec = [((h[i % 16] + i) % 256) / 255.0 for i in range(EMBEDDING_DIM)]
            result.append(vec)
        return result

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]


@pytest.fixture
def mock_provider() -> FixedProvider:
    return FixedProvider()


@pytest.fixture(autouse=True)
def _patch_providers(mock_provider: FixedProvider):
    """Replace OpenAICompatibleProvider in builder and search modules."""
    with patch(
        "paperforge.embedding.builder.OpenAICompatibleProvider",
        return_value=mock_provider,
    ), patch(
        "paperforge.embedding.search.OpenAICompatibleProvider",
        return_value=mock_provider,
    ):
        yield


# ---------------------------------------------------------------------------
# Unit factories
# ---------------------------------------------------------------------------


def _make_body_units(paper_id: str, topic: str, n: int = 3) -> list[dict]:
    return [
        {
            "unit_id": f"{paper_id}:body:{i}:1-1",
            "paper_id": paper_id,
            "section_path": f"section{i}",
            "section_level": 1,
            "section_title": f"Section {i}",
            "unit_text": f"This is body text about {topic}, unit {i} for paper {paper_id}.",
            "unit_kind": "body",
            "part_ordinal": 0,
            "token_estimate": 10,
        }
        for i in range(1, n + 1)
    ]


def _make_object_units(paper_id: str, topic: str, n: int = 2) -> list[dict]:
    return [
        {
            "unit_id": f"{paper_id}:object:f{i}:1-1",
            "paper_id": paper_id,
            "section_path": "results",
            "object_kind": "figure",
            "object_label": f"Figure {i}",
            "caption_text": f"Caption about {topic}, figure {i}.",
            "nearby_body_text": f"Nearby text about {topic}, figure {i}.",
            "token_estimate": 15,
        }
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# Helper: embed one paper (body + object units) into the vector DB
# ---------------------------------------------------------------------------


def _embed_paper(
    vault: Path,
    paper_id: str,
    topic: str,
    *,
    mock_provider: FixedProvider | None = None,
):
    """Create body and object units, encode, and write to the vector DB."""
    body_units = _make_body_units(paper_id, topic, n=3)
    payload: EmbeddingPayload = prepare_body_payload(paper_id, body_units)
    encoded = encode_payload(vault, payload, provider=mock_provider)
    write_encoded_payload(vault, encoded)

    object_units = _make_object_units(paper_id, topic, n=2)
    payload = prepare_object_payload(paper_id, object_units)
    encoded = encode_payload(vault, payload, provider=mock_provider)
    write_encoded_payload(vault, encoded)


# ---------------------------------------------------------------------------
# Topics that loosely match each fixture paper
# ---------------------------------------------------------------------------

_TOPICS: dict[str, str] = {
    "paper_a": "machine learning clinical",
    "paper_b": "genomic sequencing cancer",
    "paper_c": "neural networks imaging",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e_fast
class TestEmbedRetrieveE2E:
    """E2E tests for embed -> retrieve pipeline."""

    def test_embed_body_units_roundtrip(
        self,
        tmp_path: Path,
        synthetic_paper_paths: list[tuple[str, Path]],
        mock_provider: FixedProvider,
    ):
        """Embed body units for fixture papers and verify retrieval returns paper_a."""
        for paper_id, _ in synthetic_paper_paths:
            _embed_paper(tmp_path, paper_id, _TOPICS[paper_id], mock_provider=mock_provider)

        results = merge_retrieve(tmp_path, "machine learning clinical", limit=10)
        assert len(results) >= 1, "Expected at least one result from the round-trip"
        paper_ids = {r["paper_id"] for r in results}
        assert "paper_a" in paper_ids, "Expected paper_a in results"

    def test_retrieve_returns_correct_sources(
        self,
        tmp_path: Path,
        synthetic_paper_paths: list[tuple[str, Path]],
        mock_provider: FixedProvider,
    ):
        """Verify retrieved results have correct source field (body_unit / object_unit)."""
        for paper_id, _ in synthetic_paper_paths:
            _embed_paper(tmp_path, paper_id, _TOPICS[paper_id], mock_provider=mock_provider)

        results = merge_retrieve(tmp_path, "machine learning clinical", limit=10)
        assert any(r["source"] == "body_unit" for r in results), (
            "Expected at least one body_unit result"
        )
        assert any(r["source"] == "object_unit" for r in results), (
            "Expected at least one object_unit result"
        )

    def test_retrieve_respects_per_paper_cap(
        self,
        tmp_path: Path,
        synthetic_paper_paths: list[tuple[str, Path]],
        mock_provider: FixedProvider,
    ):
        """Verify per-paper cap (max 2 results per paper) is respected."""
        for paper_id, _ in synthetic_paper_paths:
            _embed_paper(tmp_path, paper_id, _TOPICS[paper_id], mock_provider=mock_provider)

        results = merge_retrieve(tmp_path, "machine learning", limit=6)

        per_paper: dict[str, int] = {}
        for r in results:
            per_paper[r["paper_id"]] = per_paper.get(r["paper_id"], 0) + 1

        for pid, count in per_paper.items():
            assert count <= 2, f"Paper {pid} appears {count} times (max 2 expected)"

        assert len(results) <= 6, "Total results should not exceed the requested limit"
