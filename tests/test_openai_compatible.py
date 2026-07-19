"""Unit tests for OpenAICompatibleProvider (openai SDK path)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider


@pytest.fixture
def mock_client():
    """Patch openai.OpenAI and return the mock client instance."""
    with patch("paperforge.embedding.providers.openai_compatible.openai.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client

        embedding_response = MagicMock()
        emb1 = MagicMock()
        emb1.embedding = [0.1, 0.2, 0.3]
        emb2 = MagicMock()
        emb2.embedding = [0.4, 0.5, 0.6]
        embedding_response.data = [emb1, emb2]
        client.embeddings.create.return_value = embedding_response

        yield client


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("VECTOR_DB_API_KEY", "test-key-123")


class TestOpenAICompatibleProvider:
    def test_encode_calls_client_embeddings_create(
        self, mock_client, tmp_path: Path,
    ):
        provider = OpenAICompatibleProvider(tmp_path)
        result = provider.encode(["hello", "world"])

        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=["hello", "world"],
        )
        assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    def test_encode_single_returns_one_embedding(self, mock_client, tmp_path: Path):
        provider = OpenAICompatibleProvider(tmp_path)
        result = provider.encode_single("hello")

        assert result == [0.1, 0.2, 0.3]

    def test_timeout_and_retries_applied(self, tmp_path: Path):
        with patch("paperforge.embedding.providers.openai_compatible.openai.OpenAI") as mock_cls:
            OpenAICompatibleProvider(tmp_path)

            mock_cls.assert_called_once()
            _args, kwargs = mock_cls.call_args
            assert kwargs["timeout"] == 30.0
            assert kwargs["max_retries"] == 2

    def test_provider_type_requests_delegates_to_fallback(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("VECTOR_DB_PROVIDER_TYPE", "requests")

        with patch(
            "paperforge.embedding.providers.requests_fallback.requests.post",
        ) as mock_post:
            mock_post.return_value.json.return_value = {
                "data": [{"embedding": [0.7, 0.8, 0.9]}],
            }
            mock_post.return_value.raise_for_status = lambda: None

            provider = OpenAICompatibleProvider(tmp_path)
            result = provider.encode(["test"])

            mock_post.assert_called_once()
            assert result == [[0.7, 0.8, 0.9]]

    def test_raises_when_no_api_key(self, monkeypatch, tmp_path: Path):
        monkeypatch.delenv("VECTOR_DB_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="No API key configured"):
            OpenAICompatibleProvider(tmp_path)

    def test_accepts_custom_base_url(self, mock_client, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("VECTOR_DB_API_BASE", "https://custom.api.com/v1")

        provider = OpenAICompatibleProvider(tmp_path)
        provider.encode(["test"])

        _args, kwargs = mock_client.embeddings.create.call_args
        assert kwargs["model"] == "text-embedding-3-small"
