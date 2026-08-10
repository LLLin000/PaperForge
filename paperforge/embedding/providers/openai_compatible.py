from __future__ import annotations

import logging
from pathlib import Path

import openai

from paperforge.embedding._config import (
    get_api_key,
    get_api_model,
    get_provider_type,
)
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
                "Run `paperforge auth set embedding --stdin` or supply "
                "PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT."
            )
        self._model = get_api_model(vault)
        from paperforge.embedding._config import get_effective_api_base_url

        base_url = get_effective_api_base_url(vault)
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
