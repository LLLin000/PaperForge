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
    """#221: the probe must not create what it inspects.

    A reporting command that creates the logs directory both mutates the
    canonical tree and hides the fact that the directory was missing, so a
    missing directory is reported, not repaired.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    from tests.conftest import canonical_test_config

    canonical_test_config(vault)

    missing = _check_write(vault)
    assert missing["status"] == "blocked"
    assert not (vault / "System" / "PaperForge" / "logs").exists(), (
        "the write probe created the directory it was inspecting"
    )

    (vault / "System" / "PaperForge" / "logs").mkdir(parents=True)
    present = _check_write(vault)
    assert present["status"] == "ok"
    assert any("writable" in e for e in present["evidence"])


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


def test_runtime_identity_identifies_the_serving_artifact(tmp_path):
    """Acceptance evidence must be able to name the artifact that answered.

    A version alone cannot distinguish a worktree source from an installed
    copy, so `runtime` reports the interpreter and the package path. The e2e
    H-layer records this (W01, #194); without it a run claiming to test this
    checkout could be served by a different one.
    """
    import sys
    from pathlib import Path as _Path

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")

    health = get_runtime_health(vault)
    runtime = health["runtime"]

    import paperforge

    package_path = _Path(runtime["package_path"])
    assert package_path.name == "paperforge"
    assert package_path.is_dir()
    # The reported path must be the package that answered, not a stale name.
    assert (package_path / "__init__.py").is_file()
    assert runtime["package_version"] == paperforge.__version__
    assert runtime["interpreter"] == sys.executable
    assert runtime["python_version"]
