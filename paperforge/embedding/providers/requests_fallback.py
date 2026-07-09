from __future__ import annotations

import logging
from pathlib import Path

import requests

from paperforge.embedding._config import get_api_base_url, get_api_key, get_api_model
from paperforge.embedding.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(EmbeddingProvider):
    """Requests-based fallback provider.

    Drop-in replacement for the SDK-based OpenAICompatibleProvider.
    Activated by setting VECTOR_DB_PROVIDER_TYPE=requests.
    """

    def __init__(self, vault: Path):
        self._api_key = get_api_key(vault)
        if not self._api_key:
            raise ValueError(
                "No API key configured for embedding. "
                "Set VECTOR_DB_API_KEY or OPENAI_API_KEY in .env or plugin settings."
            )
        self._model = get_api_model(vault)
        self._base_url = (get_api_base_url(vault) or "https://api.openai.com/v1").rstrip("/")
        logger.info("Embedding provider (requests fallback): model=%s, base_url=%s", self._model, self._base_url)

    def encode(self, texts: list[str]) -> list[list[float]]:
        resp = requests.post(
            f"{self._base_url}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self._model, "input": texts},
            timeout=60.0,
        )
        resp.raise_for_status()
        return [d["embedding"] for d in resp.json()["data"]]

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]
