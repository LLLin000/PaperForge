from __future__ import annotations

from paperforge.memory.context import get_agent_context
from tests.conftest import canonical_test_config


def test_get_agent_context_returns_none_when_no_db(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    assert get_agent_context(vault) is None
