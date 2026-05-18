from __future__ import annotations

from argparse import Namespace
from unittest.mock import patch

from paperforge.commands.retrieve import run


def test_retrieve_reports_corrupted_vector_index(tmp_path, capsys):
    vault = tmp_path / "vault"
    vault.mkdir()
    args = Namespace(vault_path=vault, query="acl", limit=5, expand=True, json=False)

    with patch("paperforge.embedding.get_embed_status") as mock_status:
        mock_status.return_value = {
            "db_exists": True,
            "chunk_count": 0,
            "model": "test-model",
            "mode": "api",
            "healthy": False,
            "error": "Error loading hnsw index",
        }
        result_code = run(args)

    captured = capsys.readouterr()
    assert result_code == 1
    assert "Vector index is unreadable" in captured.err
    assert "rebuild" in captured.err.lower()
