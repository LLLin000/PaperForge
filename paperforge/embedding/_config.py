"""Embedding configuration — consumed exclusively through the #142 config seam.

No plugin ``data.json`` reads and no ``.env`` file reads: provider/model/base
come from the canonical paperforge.json + process environment via
``load_config``; API keys come from the process environment only (the #138 /
C1 credential provider owns durable secrets).

Fail-closed: a missing/invalid configuration raises ConfigError — the CLI
already refuses to run domain commands on guessed paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from paperforge.config import ConfigError, load_config

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _snapshot_values(vault: Path) -> dict[str, str | bool]:
    try:
        snapshot = load_config(vault)
    except ConfigError:
        raise
    return {key: cv.value for key, cv in snapshot.values.items()}


def get_api_key(vault: Path) -> str:
    """Resolve the embedding API key from the #138 credential authority
    (#173/C1): explicit canonical env → keyring.  Legacy plugin-data.json,
    .env and legacy env-name fallbacks are removed.
    """
    from paperforge.credentials import MISSING, CredentialError, CredentialKey, resolve

    try:
        return resolve(CredentialKey("embedding"))
    except CredentialError as exc:
        if exc.code == MISSING:
            return ""
        raise


def get_api_base_url(vault: Path) -> str:
    values = _snapshot_values(vault)
    return str(values.get("vector_db_api_base", "") or "")


def get_effective_api_base_url(vault: Path) -> str:
    """The endpoint the provider ACTUALLY uses — empty config means the
    OpenAI default.  Identity comparison must use this, not the raw value."""
    return (get_api_base_url(vault) or DEFAULT_OPENAI_BASE_URL).rstrip("/")


def get_api_model(vault: Path) -> str:
    values = _snapshot_values(vault)
    return str(values.get("vector_db_api_model", "") or "text-embedding-3-small")


def get_provider_type(vault: Path) -> str:
    values = _snapshot_values(vault)
    return str(values.get("vector_db_provider_type", "") or "openai_sdk")
