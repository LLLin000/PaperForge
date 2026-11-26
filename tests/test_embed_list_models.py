from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from paperforge.commands.embed import run as run_embed
from paperforge.embedding.status import _is_embedding_model_id, list_embedding_models


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args) -> bool:
        return False


def test_is_embedding_model_id_filters_chat_models() -> None:
    assert _is_embedding_model_id("BAAI/bge-m3") is True
    assert _is_embedding_model_id("text-embedding-3-small") is True
    assert _is_embedding_model_id("nomic-embed-text:latest") is True
    assert _is_embedding_model_id("gpt-4o") is False
    assert _is_embedding_model_id("qwen3:8b") is False


def test_list_embedding_models_ollama_parses_tags(tmp_path: Path) -> None:
    payload = {
        "models": [
            {"name": "bge-m3:latest"},
            {"name": "qwen3:8b"},
            {"name": "nomic-embed-text:latest"},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
        out = list_embedding_models(tmp_path, base_url="http://127.0.0.1:11434/v1")

    assert out["source"] == "ollama"
    assert out["reachable"] is True
    assert out["embedding_models"] == ["bge-m3:latest", "nomic-embed-text:latest"]


def test_list_embedding_models_ollama_offline_returns_gracefully(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        out = list_embedding_models(tmp_path, base_url="http://localhost:11434/v1")

    assert out["source"] == "ollama"
    assert out["reachable"] is False
    assert out["embedding_models"] == []


def test_list_embedding_models_openai_compatible_filters_candidates(tmp_path: Path) -> None:
    payload = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "Pro/BAAI/bge-m3"},
            {"id": "text-embedding-3-small"},
            {"id": "deepseek-chat"},
        ]
    }
    with (
        patch("urllib.request.urlopen", return_value=_FakeResponse(payload)),
        patch("paperforge.embedding._config.get_api_key", return_value="sk-test"),
    ):
        out = list_embedding_models(tmp_path, base_url="https://custom.example/v1/embeddings/")

    assert out["source"] == "openai_compatible"
    assert out["base_url"] == "https://custom.example/v1"
    assert out["reachable"] is True
    assert out["embedding_models"] == ["Pro/BAAI/bge-m3", "text-embedding-3-small"]


def test_cli_embed_list_models_emits_pf_result(tmp_path: Path, capsys) -> None:
    args = SimpleNamespace(
        vault_path=tmp_path,
        embed_subcommand="list-models",
        base_url="http://127.0.0.1:11434/v1",
        json=True,
    )
    fake = {
        "source": "ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "reachable": True,
        "models": ["bge-m3:latest"],
        "embedding_models": ["bge-m3:latest"],
    }
    with patch("paperforge.embedding.status.list_embedding_models", return_value=fake):
        rc = run_embed(args)

    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["ok"] is True
    assert doc["command"] == "embed list-models"
    assert doc["data"]["embedding_models"] == ["bge-m3:latest"]
