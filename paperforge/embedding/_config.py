from __future__ import annotations

import json
import os
from pathlib import Path


def _read_plugin_settings(vault: Path) -> dict:
    data_path = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    return {}


def get_api_key(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    api_key = os.environ.get("VECTOR_DB_API_KEY", "")
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        api_key = settings.get("vector_db_api_key", "")
    if not api_key:
        env_file = vault / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("VECTOR_DB_API_KEY=") or line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return api_key


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def get_api_base_url(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    return os.environ.get("VECTOR_DB_API_BASE", "") or settings.get("vector_db_api_base", "") or ""


def get_effective_api_base_url(vault: Path) -> str:
    """The endpoint the provider ACTUALLY uses — empty config means the
    OpenAI default.  Identity comparison must use this, not the raw value:
    a migration from default→custom endpoint otherwise never triggers a
    shadow rebuild and mixes old/new provider vectors (P0-1)."""
    return (get_api_base_url(vault) or DEFAULT_OPENAI_BASE_URL).rstrip("/")


def get_api_model(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    return os.environ.get("VECTOR_DB_API_MODEL", "") or settings.get("vector_db_api_model", "text-embedding-3-small")


def get_provider_type(vault: Path) -> str:
    settings = _read_plugin_settings(vault)
    return os.environ.get("VECTOR_DB_PROVIDER_TYPE", "") or settings.get("vector_db_provider_type", "") or "openai_sdk"
