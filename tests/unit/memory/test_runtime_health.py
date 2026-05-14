from __future__ import annotations

from pathlib import Path
import json

from paperforge.memory.runtime_health import (
    get_runtime_health,
    _check_bootstrap,
    _check_write,
)


def test_runtime_health_blocks_without_paperforge_json(tmp_path):
    vault = tmp_path / "novault"
    vault.mkdir()
    health = get_runtime_health(vault)
    assert health["summary"]["status"] == "blocked"
    assert health["layers"]["bootstrap"]["status"] == "blocked"
    assert health["capabilities"]["paper_context"] == False


def test_bootstrap_with_paperforge_json(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    pf_json = vault / "paperforge.json"
    pf_json.write_text(json.dumps({"system_dir": "System"}), encoding="utf-8")
    (vault / "System" / "PaperForge").mkdir(parents=True)
    result = _check_bootstrap(vault)
    assert result["status"] == "ok"


def test_write_layer(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    result = _check_write(vault)
    assert result["status"] == "ok"
    assert any("writable" in e for e in result["evidence"])


def test_runtime_health_summary_has_expected_keys(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    health = get_runtime_health(vault)
    summary = health["summary"]
    for key in ("status", "reason", "safe_read", "safe_write", "safe_build", "safe_vector"):
        assert key in summary
    for layer in ("bootstrap", "read", "write", "index", "vector"):
        assert layer in health["layers"]
        for key in ("status", "evidence", "next_action", "repair_command"):
            assert key in health["layers"][layer]
