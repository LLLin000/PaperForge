from __future__ import annotations

from unittest.mock import patch


def test_runtime_health_command_returns_pfresult_json(tmp_path):
    from argparse import Namespace
    from paperforge.commands.runtime_health import run
    vault = tmp_path / "vault"
    vault.mkdir()
    args = Namespace(vault_path=vault, json=True)
    with patch("paperforge.commands.runtime_health.get_runtime_health") as mock:
        mock.return_value = {"summary": {"status": "ok"}, "layers": {}, "capabilities": {}}
        result_code = run(args)
        assert result_code == 0
