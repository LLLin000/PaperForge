from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from paperforge.embedding.backends import ChromaBackend, get_vector_backend




class TestChromaBackendIdentity:
    """Identity and naming."""

    def test_chroma_backend_keeps_existing_collection_name(self, tmp_path: Path):
        backend = ChromaBackend(tmp_path)
        assert backend.collection_name == "paperforge_fulltext"

    def test_factory_returns_chroma_backend(self, tmp_path: Path):
        backend = get_vector_backend(tmp_path)
        assert isinstance(backend, ChromaBackend)
        assert backend.collection_name == "paperforge_fulltext"


class TestChromaBackendAdd:
    """Adding embeddings."""

    def test_add_passes_through_to_collection(self, chroma_backend: ChromaBackend):
        ids = ["key_0", "key_1"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        documents = ["chunk a", "chunk b"]
        metadatas = [{"paper_id": "key"}, {"paper_id": "key"}]

        chroma_backend.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        chroma_backend.collection.add.assert_called_once_with(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def test_add_wraps_hnsw_error(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.add.side_effect = RuntimeError("Error loading hnsw index")

        with pytest.raises(RuntimeError, match="ChromaDB index error"):
            chroma_backend.add(
                ids=["x"],
                embeddings=[[0.1]],
                documents=["t"],
                metadatas=[{"paper_id": "x"}],
            )

    def test_add_passes_through_other_errors(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.add.side_effect = ValueError("something else")

        with pytest.raises(ValueError, match="something else"):
            chroma_backend.add(
                ids=["x"],
                embeddings=[[0.1]],
                documents=["t"],
                metadatas=[{"paper_id": "x"}],
            )


class TestChromaBackendQuery:
    """Querying embeddings."""

    def test_query_returns_formatted_chunks(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.query.return_value = {
            "documents": [["chunk text"]],
            "metadatas": [[{"paper_id": "abc", "section": "Methods", "page_number": 3, "chunk_index": 1}]],
            "distances": [[0.15]],
        }

        results = chroma_backend.query(query_embedding=[0.1, 0.2], limit=5)

        assert len(results) == 1
        assert results[0]["paper_id"] == "abc"
        assert results[0]["section"] == "Methods"
        assert results[0]["page_number"] == 3
        assert results[0]["chunk_index"] == 1
        assert results[0]["chunk_text"] == "chunk text"
        assert results[0]["score"] == 0.85  # 1.0 - 0.15

    def test_query_with_missing_metadata_fields(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.query.return_value = {
            "documents": [["text"]],
            "metadatas": [[{"paper_id": "abc"}]],
            "distances": [[0.3]],
        }

        results = chroma_backend.query(query_embedding=[0.1], limit=5)

        assert results[0]["section"] == "Text"
        assert results[0]["page_number"] == 1
        assert results[0]["chunk_index"] == 0

    def test_query_passes_limit(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        chroma_backend.query(query_embedding=[0.1], limit=10)

        chroma_backend.collection.query.assert_called_once()
        assert chroma_backend.collection.query.call_args[1]["n_results"] == 10


class TestChromaBackendDelete:
    """Deleting paper vectors."""

    def test_delete_paper_deletes_found_ids(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.get.return_value = {"ids": ["abc_0", "abc_1"]}

        count = chroma_backend.delete_paper("abc")

        assert count == 2
        chroma_backend.collection.delete.assert_called_once_with(ids=["abc_0", "abc_1"])

    def test_delete_paper_no_ids(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.get.return_value = {"ids": []}

        count = chroma_backend.delete_paper("abc")

        assert count == 0
        chroma_backend.collection.delete.assert_not_called()

    def test_delete_paper_handles_exception(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.get.side_effect = RuntimeError("whoops")

        count = chroma_backend.delete_paper("abc")

        assert count == 0


class TestChromaBackendHealth:
    """Health check."""

    def test_health_returns_healthy(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.count.return_value = 42

        result = chroma_backend.health()

        assert result["healthy"] is True
        assert result["chunk_count"] == 42

    def test_health_returns_unhealthy(self, chroma_backend: ChromaBackend):
        chroma_backend.collection.count.side_effect = RuntimeError("corrupt index")

        result = chroma_backend.health()

        assert result["healthy"] is False
        assert result["chunk_count"] == 0
        assert "corrupt" in result.get("error", "")
        assert result.get("corrupted") is True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chroma_backend(tmp_path: Path) -> ChromaBackend:
    """Return a ChromaBackend whose client and collection are fully mocked."""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("paperforge.embedding.backends.chroma_backend.chromadb.PersistentClient", return_value=mock_client):
        backend = ChromaBackend(tmp_path)

    # Attach the mock collection for assertion convenience
    backend.collection = mock_collection
    backend.client = mock_client
    return backend
