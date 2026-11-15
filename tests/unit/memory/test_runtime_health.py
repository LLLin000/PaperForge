from __future__ import annotations

from paperforge.memory.runtime_health import (
    _check_bootstrap,
    _check_vector,
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


def test_vector_health_degrades_when_dependency_import_fails(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    settings_path = vault / ".obsidian" / "plugins" / "paperforge"
    settings_path.mkdir(parents=True)
    (settings_path / "data.json").write_text(
        '{"features": {"vector_db": true}}',
        encoding="utf-8",
    )

    import builtins

    real_import = builtins.__import__

    def broken_import(name, *args, **kwargs):
        if name == "openai":
            raise ModuleNotFoundError("missing openai response tool")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)
    result = _check_vector(vault)

    assert result["status"] == "degraded"
    assert "Vector runtime unavailable" in result["evidence"][0]
    assert result["repair_command"] == "paperforge repair --runtime --json"


def test_runtime_health_command_returns_json_on_unexpected_failure(tmp_path, monkeypatch, capsys):
    import json
    from argparse import Namespace

    from paperforge.commands import runtime_health as command

    monkeypatch.setattr(
        command,
        "get_runtime_health",
        lambda _vault: (_ for _ in ()).throw(RuntimeError("diagnostic failure")),
    )
    rc = command.run(Namespace(vault_path=tmp_path, json=True))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert "diagnostic failure" in payload["error"]["message"]
def test_vector_disabled_reports_enabled_false_and_no_retrieval(tmp_path):
    """Disabled toggle is healthy-optional-disabled, not a retrieval capability.

    Regression for the demonstrated projection bug: with
    ``features.vector_db`` unset/false, ``safe_vector`` and
    ``capabilities.vector_retrieve`` must be False while the layer keeps
    the existing ``ok`` status (overall statuses unchanged).
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    health = get_runtime_health(vault)
    assert health["layers"]["vector"]["status"] == "ok"
    assert health["layers"]["vector"]["enabled"] is False
    # Overall summary status is owned by other layers in a bare tmp vault;
    # this regression only pins the vector capability projection.
    assert health["summary"]["safe_vector"] is False
    assert health["capabilities"]["vector_retrieve"] is False


def test_vector_enabled_but_unready_stays_degraded_and_unavailable(tmp_path):
    """Enabled toggle with no index must stay degraded and unavailable."""
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    settings_path = vault / ".obsidian" / "plugins" / "paperforge"
    settings_path.mkdir(parents=True)
    (settings_path / "data.json").write_text(
        '{"features": {"vector_db": true}}',
        encoding="utf-8",
    )

    health = get_runtime_health(vault)

    assert health["layers"]["vector"]["status"] == "degraded"
    assert health["layers"]["vector"]["enabled"] is True
    assert health["summary"]["safe_vector"] is False
    assert health["capabilities"]["vector_retrieve"] is False
def test_vector_enabled_and_ready_reports_available(tmp_path):
    """Enabled toggle + completed local build state must read available.

    Uses only the existing local build-state carrier (no provider call):
    ``completed`` short-circuits before any vec0/Chroma probe.
    """
    from paperforge.embedding.build_state import mark_vector_build_state

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    settings_path = vault / ".obsidian" / "plugins" / "paperforge"
    settings_path.mkdir(parents=True)
    (settings_path / "data.json").write_text(
        '{"features": {"vector_db": true}}',
        encoding="utf-8",
    )
    mark_vector_build_state(vault, status="completed")

    health = get_runtime_health(vault)

    assert health["layers"]["vector"]["status"] == "ok"
    assert health["layers"]["vector"]["enabled"] is True
    assert health["summary"]["safe_vector"] is True
    assert health["capabilities"]["vector_retrieve"] is True
