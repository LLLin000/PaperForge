from __future__ import annotations

import json
from pathlib import Path

from paperforge.commands import retrieve as retrieve_command
from paperforge.commands import search as search_command


class _Args:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.query = "Lin 2024 Electrical Stimulation"
        self.json = True
        self.limit = 10
        self.domain = None
        self.year_from = None
        self.year_to = None
        self.ocr = None
        self.deep = None
        self.lifecycle = None
        self.next_step = None
        self.expand = True


class _Conn:
    def close(self) -> None:
        return None


def test_search_zero_results_emits_query_diagnostic(monkeypatch, tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "paperforge.db"
    db_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(search_command, "get_memory_db_path", lambda vault: db_path)
    monkeypatch.setattr(search_command, "get_connection", lambda db_path, read_only=True: _Conn())
    monkeypatch.setattr(search_command, "search_papers", lambda *args, **kwargs: [])

    args = _Args(tmp_path)
    assert search_command.run(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["count"] == 0
    assert "query_diagnostic" in payload["data"]
    assert payload["warnings"]


def test_retrieve_unavailable_emits_suggested_modes(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr("paperforge.embedding.get_embed_status", lambda vault: {"healthy": True, "chunk_count": 0, "db_exists": False, "error": ""})

    args = _Args(tmp_path)
    args.query = "galvanotaxis"
    assert retrieve_command.run(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["data"]["interactive_fallback_required"] is True
    assert payload["data"]["suggested_modes"]


def test_retrieve_low_confidence_hits_emit_warning(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr("paperforge.embedding.get_embed_status", lambda vault: {"healthy": True, "chunk_count": 5, "db_exists": True, "error": ""})
    monkeypatch.setattr(retrieve_command, "retrieve_chunks", lambda vault, query, limit=5, expand=True: [
        {"paper_id": "AAA11111", "chunk_text": "[Figure]", "score": 0.58},
        {"paper_id": "AAA11111", "chunk_text": "### Keywords", "score": 0.57},
        {"paper_id": "AAA11111", "chunk_text": "None.", "score": 0.56},
    ])
    monkeypatch.setattr(retrieve_command, "get_memory_db_path", lambda vault: tmp_path / "missing.db")

    args = _Args(tmp_path)
    args.query = "unlikelynonexistenttermxyz"
    assert retrieve_command.run(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["warnings"]
    assert payload["data"]["query_diagnostic"]["interactive_fallback_required"] is True
