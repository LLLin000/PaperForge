"""#127 PR B — sync producer cutover: next_actions on PFResult, no hidden follow-ups."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from paperforge import __version__
from paperforge.commands import sync as sync_module
from paperforge.core.result import PFResult


def _args(**overrides: Any) -> argparse.Namespace:
    base = {
        "vault_path": Path("C:/vault"),
        "verbose": False,
        "dry_run": False,
        "selection": False,
        "index": False,
        "json": False,
        "prune": False,
        "prune_force": False,
        "rebuild_index": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _ok_result() -> PFResult:
    return PFResult(
        ok=True,
        command="sync",
        version=__version__,
        data={"papers": 3},
    )


def _patch_run(monkeypatch, result: PFResult, builds: list[int]):
    class FakeService:
        def __init__(self, vault):
            self.vault = vault

        def run(self, **kwargs):
            return result

    import paperforge.memory.builder as builder_module
    import paperforge.services.sync_service as sync_service_module

    monkeypatch.setattr(sync_service_module, "SyncService", FakeService)
    monkeypatch.setattr(sync_module, "_write_orphan_state", lambda vault, result: None)
    monkeypatch.setattr(sync_module, "migrate_paperforge_json", lambda vault: False)

    def fake_build(vault):
        builds.append(1)
        return {"papers_indexed": 3, "hash_match": True}

    monkeypatch.setattr(builder_module, "build_from_index", fake_build)


class TestJsonMode:
    def test_json_prints_single_document_with_next_actions(self, monkeypatch, capsys):
        builds: list[int] = []
        _patch_run(monkeypatch, _ok_result(), builds)
        assert sync_module.run(_args(json=True)) == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        ids = [action["action_id"] for action in payload["next_actions"]]
        assert ids == ["memory.build", "embed.resume"]
        # JSON mode never executes follow-ups
        assert builds == []

    def test_next_actions_carry_plugin_contract_fields(self, monkeypatch, capsys):
        """The plugin orchestrator parses exactly these fields — the seam
        contract between `sync --json` and next-actions-orchestrator.ts."""
        _patch_run(monkeypatch, _ok_result(), [])
        sync_module.run(_args(json=True))
        payload = json.loads(capsys.readouterr().out)
        for action in payload["next_actions"]:
            assert set(action) >= {
                "schema_version",
                "action_id",
                "scope",
                "automatic",
                "cost",
                "impact",
                "confirmation",
                "reason",
            }
            assert action["schema_version"] == 1
            assert "kind" in action["scope"]

    def test_json_embed_action_is_confirmed_remote(self, monkeypatch, capsys):
        _patch_run(monkeypatch, _ok_result(), [])
        sync_module.run(_args(json=True))
        payload = json.loads(capsys.readouterr().out)
        embed = next(a for a in payload["next_actions"] if a["action_id"] == "embed.resume")
        assert embed["automatic"] is False
        assert embed["cost"] == "remote_possible"
        assert embed["confirmation"] == "required"

    def test_json_memory_action_is_automatic_local(self, monkeypatch, capsys):
        _patch_run(monkeypatch, _ok_result(), [])
        sync_module.run(_args(json=True))
        payload = json.loads(capsys.readouterr().out)
        memory = next(a for a in payload["next_actions"] if a["action_id"] == "memory.build")
        assert memory["automatic"] is True
        assert memory["cost"] == "local"
        assert memory["confirmation"] == "none"

    def test_json_index_only_has_no_next_actions(self, monkeypatch, capsys):
        _patch_run(monkeypatch, _ok_result(), [])
        sync_module.run(_args(json=True, index=True))
        payload = json.loads(capsys.readouterr().out)
        assert payload.get("next_actions", []) == []

    def test_json_selection_only_has_no_next_actions(self, monkeypatch, capsys):
        _patch_run(monkeypatch, _ok_result(), [])
        sync_module.run(_args(json=True, selection=True))
        payload = json.loads(capsys.readouterr().out)
        assert payload.get("next_actions", []) == []


class TestTerminalMode:
    def test_text_runs_automatic_local_only(self, monkeypatch, capsys):
        builds: list[int] = []
        _patch_run(monkeypatch, _ok_result(), builds)
        assert sync_module.run(_args()) == 0
        out = capsys.readouterr().out
        # memory.build (automatic local) executed inline
        assert builds == [1]
        assert "memory: 3 papers (fast)" in out
        # embed.resume surfaced as needing confirmation, never spawned
        assert "needs confirmation" in out
        assert "embed" in out

    def test_text_failed_sync_returns_1_and_no_followups(self, monkeypatch, capsys):
        builds: list[int] = []
        result = PFResult(ok=False, command="sync", version=__version__)
        _patch_run(monkeypatch, result, builds)
        assert sync_module.run(_args()) == 1
        assert builds == []
        assert capsys.readouterr().out == ""

    def test_text_dry_run_returns_before_service(self, monkeypatch, capsys):
        calls: list[str] = []

        class NeverCalled:
            def __init__(self, vault):
                calls.append("constructed")
                self.vault = vault

        import paperforge.services.sync_service as sync_service_module

        monkeypatch.setattr(sync_service_module, "SyncService", NeverCalled)
        assert sync_module.run(_args(dry_run=True)) == 0
        assert calls == []
        assert "DRY-RUN" in capsys.readouterr().out


class TestContract:
    def test_no_fire_and_forget_spawn_remains(self):
        """The Popen embed spawn must be gone from the sync module."""
        import inspect

        source = inspect.getsource(sync_module)
        assert "subprocess.Popen" not in source
        assert "embed" in source  # only as next_action metadata/terminal notice
