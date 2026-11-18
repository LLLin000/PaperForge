"""Embedding provider factory and prerequisite checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.embedding._config import get_provider_type
from paperforge.embedding.providers.base import EmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "check_embedding_provider_prereqs",
    "resolve_embedding_provider",
]


def check_embedding_provider_prereqs(vault: Path) -> dict[str, Any]:
    """Verify transport dependencies required by the configured embedding provider."""
    provider_type = get_provider_type(vault).strip().lower() or "openai_sdk"
    if provider_type in ("openai_sdk", "openai"):
        try:
            import openai  # noqa: F401
        except ImportError:
            return {
                "ok": False,
                "error": "openai is not installed",
                "fix": 'Run: pip install "paperforge[vector]"',
            }
        return {"ok": True}
    if provider_type == "requests":
        try:
            import requests  # noqa: F401
        except ImportError:
            return {
                "ok": False,
                "error": "requests is not installed",
                "fix": "Run: pip install requests",
            }
        return {"ok": True}
    return {
        "ok": False,
        "error": f"Unsupported embedding provider type: {provider_type}",
        "fix": "Set vector_db_provider_type to 'openai_sdk' or 'requests'",
    }


def _is_default_openai_provider(cls: Any) -> bool:
    return (
        isinstance(cls, type)
        and getattr(cls, "__module__", None)
        == "paperforge.embedding.providers.openai_compatible"
        and getattr(cls, "__name__", None) == "OpenAICompatibleProvider"
    )


def resolve_embedding_provider(
    vault: Path,
    *,
    default_cls: type[EmbeddingProvider] | None = None,
) -> EmbeddingProvider:
    """Instantiate the configured embedding provider adapter for *vault*."""
    # Allow unit tests that patch module-level OpenAICompatibleProvider on fake
    # vault paths (without paperforge.json) to intercept before config resolution.
    if default_cls is not None and not _is_default_openai_provider(default_cls):
        return default_cls(vault)

    provider_type = get_provider_type(vault).strip().lower() or "openai_sdk"
    if provider_type in ("openai_sdk", "openai"):
        if default_cls is not None:
            return default_cls(vault)
        from paperforge.embedding.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )

        return OpenAICompatibleProvider(vault)
    if provider_type == "requests":
        from paperforge.embedding.providers.requests_fallback import (
            OpenAICompatibleProvider as RequestsEmbeddingProvider,
        )

        return RequestsEmbeddingProvider(vault)
    raise ValueError(f"Unsupported embedding provider type: {provider_type}")
