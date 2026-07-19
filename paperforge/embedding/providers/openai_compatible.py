from __future__ import annotations

import logging
from pathlib import Path

import openai

from paperforge.embedding._config import get_api_base_url, get_api_key, get_api_model, get_provider_type
from paperforge.embedding.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(EmbeddingProvider):
    def __init__(self, vault: Path):
        provider_type = get_provider_type(vault)
        if provider_type == "requests":
            from paperforge.embedding.providers.requests_fallback import OpenAICompatibleProvider as Fallback

            self._delegate = Fallback(vault)
            return

        api_key = get_api_key(vault)
        if not api_key:
            raise ValueError(
                "No API key configured for embedding. "
                "Set VECTOR_DB_API_KEY or OPENAI_API_KEY in .env or plugin settings."
            )
        self._model = get_api_model(vault)
        base_url = (get_api_base_url(vault) or "https://api.openai.com/v1").rstrip("/")
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0,
            max_retries=2,
        )
        logger.info("Embedding provider: model=%s, base_url=%s", self._model, base_url)

    def encode(self, texts: list[str]) -> list[list[float]]:
        if hasattr(self, "_delegate"):
            return self._delegate.encode(texts)
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in response.data]

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]
