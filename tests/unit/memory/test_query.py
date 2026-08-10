from __future__ import annotations

from paperforge.memory.query import get_memory_status
from tests.conftest import canonical_test_config


def test_get_memory_status_returns_needs_rebuild_when_no_db(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    result = get_memory_status(vault)
    assert result["db_exists"] is False
    assert result["needs_rebuild"] is True
