from __future__ import annotations

import logging
from pathlib import Path

from openai import OpenAI

from paperforge.embedding._config import get_api_base_url, get_api_key, get_api_model
from paperforge.embedding.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(EmbeddingProvider):
    def __init__(self, vault: Path):
        api_key = get_api_key(vault)
        if not api_key:
            raise ValueError(
                "No API key configured for embedding. "
                "Set VECTOR_DB_API_KEY or OPENAI_API_KEY in .env or plugin settings."
            )
        self._model = get_api_model(vault)
        base_url = get_api_base_url(vault)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        logger.info("Embedding provider: model=%s, base_url=%s", self._model, base_url or "(default OpenAI)")
        self._client = OpenAI(**kwargs)

    def encode(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [e.embedding for e in resp.data]

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]
