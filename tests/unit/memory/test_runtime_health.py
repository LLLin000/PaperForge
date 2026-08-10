from __future__ import annotations

from paperforge.memory.runtime_health import (
    _check_bootstrap,
    _check_write,
    get_runtime_health,
)

from tests.conftest import canonical_test_config


def test_runtime_health_blocks_without_paperforge_json(tmp_path):
    # #142 fail-closed: missing config raises config.not_found instead of
    # operating on guessed paths (the CLI surfaces the setup/init action).
    import pytest as _pytest

    from paperforge.config import ConfigError

    vault = tmp_path / "novault"
    vault.mkdir()
    with _pytest.raises(ConfigError) as exc:
        get_runtime_health(vault)
    assert exc.value.code == "config.not_found"


def test_bootstrap_with_paperforge_json(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")
    (vault / "System" / "PaperForge").mkdir(parents=True)
    result = _check_bootstrap(vault)
    assert result["status"] == "ok"


def test_write_layer(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    from tests.conftest import canonical_test_config

    canonical_test_config(vault)
    result = _check_write(vault)
    assert result["status"] == "ok"
    assert any("writable" in e for e in result["evidence"])


def test_runtime_health_summary_has_expected_keys(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    from tests.conftest import canonical_test_config

    canonical_test_config(vault)
    health = get_runtime_health(vault)
    summary = health["summary"]
    for key in ("status", "reason", "safe_read", "safe_write", "safe_build", "safe_vector"):
        assert key in summary
    for layer in ("bootstrap", "read", "write", "index", "vector"):
        assert layer in health["layers"]
        for key in ("status", "evidence", "next_action", "repair_command"):
            assert key in health["layers"][layer]
