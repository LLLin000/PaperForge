from __future__ import annotations

from unittest.mock import patch
from pathlib import Path

from paperforge.commands.embed import run
from paperforge.memory.vector_db import write_vector_build_state, read_vector_build_state


def test_embed_stop_returns_ok_when_no_active_job(tmp_path):
    from argparse import Namespace
    vault = tmp_path / "vault"
    vault.mkdir()
    args = Namespace(vault_path=vault, embed_subcommand="stop", json=True)
    result_code = run(args)
    assert result_code == 0


def test_embed_status_includes_build_state(tmp_path):
    from argparse import Namespace
    vault = tmp_path / "vault"
    vault.mkdir()
    write_vector_build_state(vault, {"status": "running", "current": 3, "total": 10})
    args = Namespace(vault_path=vault, embed_subcommand="status", json=True)
    with patch("paperforge.commands.embed.get_embed_status") as mock_status:
        mock_status.return_value = {"db_exists": True, "chunk_count": 0, "model": "test", "mode": "local"}
        with patch("paperforge.commands.embed.read_vector_build_state") as mock_read:
            mock_read.return_value = {"status": "running", "current": 3, "total": 10}
            result_code = run(args)
            assert result_code == 0
