"""T6 (#167) sync cutover — frozen-contract tests.

The superseded sibling-emission semantics (sync hardcoding
memory.build+embed.resume into next_actions) are REPLACED by:

    sync completes external source detection + canonical library sync
    → reconcile(all) (single producer; NEVER changed_keys-only)
    → generic follow-up chain runner (auto mode: automatic-local inline,
      remote/destructive/confirmation-required pending)

O2: forced memory.build failure → no successful publish → no post-publish
reconcile → no embed.resume anywhere (emitted, pending, or next_actions).
"""

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


def _wire(action_id: str, keys: list[str] | None = None) -> dict:
    scope = {"kind": "papers", "keys": keys} if keys is not None else {"kind": "all"}
    return {"schema_version": 1, "action_id": action_id, "scope": scope, "automatic": False,
            "cost": "remote_possible", "impact": "mutating", "confirmation": "required",
            "reason": "reconcile"}


def _patch_run(monkeypatch, result: PFResult) -> None:
    """Fake SyncService returning *result*; isolate helpers that touch the FS."""

    class FakeService:
        def __init__(self, vault):
            self.vault = vault

        def run(self, **kwargs):
            return result

    import paperforge.services.sync_service as sync_service_module

    monkeypatch.setattr(sync_service_module, "SyncService", FakeService)
    monkeypatch.setattr(sync_module, "_write_orphan_state", lambda vault, result: None)
    monkeypatch.setattr(sync_module, "_cleanup_legacy_snapshot_files", lambda vault: None)


def _patch_reconcile(monkeypatch, result: PFResult) -> None:
    """Reconcile is the single producer — its next_actions are the only
    intents the runner ever sees."""
    monkeypatch.setattr(sync_module, "reconcile", lambda vault, keys=None: result)


class TestJsonMode:
    def test_json_attaches_reconcile_intents_only(self, monkeypatch, capsys) -> None:
        """next_actions == exactly what reconcile emitted; no hardcoded
        sibling emission, no embed.resume unless reconcile says so."""
        _patch_run(monkeypatch, _ok_result())
        _patch_reconcile(monkeypatch, PFResult(
            ok=True, command="reconcile", version=__version__,
            data={}, next_actions=[_wire("memory.build")],
        ))
        assert sync_module.run(_args(json=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        ids = [action["action_id"] for action in payload["next_actions"]]
        assert ids == ["memory.build"]

    def test_json_mode_never_executes_followups(self, monkeypatch, capsys) -> None:
        builds: list[int] = []
        import paperforge.memory.builder as builder_module

        def fake_build(vault, keys=None):
            builds.append(1)
            return {"papers_indexed": 3, "hash_match": True}

        monkeypatch.setattr(builder_module, "build_for_keys", fake_build)
        _patch_run(monkeypatch, _ok_result())
        _patch_reconcile(monkeypatch, PFResult(
            ok=True, command="reconcile", version=__version__,
            data={}, next_actions=[_wire("memory.build")],
        ))
        sync_module.run(_args(json=True))
        capsys.readouterr()
        assert builds == []

    def test_json_index_only_has_no_next_actions(self, monkeypatch, capsys) -> None:
        _patch_run(monkeypatch, _ok_result())
        monkeypatch.setattr(sync_module, "reconcile",
                            lambda vault, keys=None: (_ for _ in ()).throw(AssertionError("must not run")))
        assert sync_module.run(_args(json=True, index=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload.get("next_actions", []) == []

    def test_json_selection_only_has_no_next_actions(self, monkeypatch, capsys) -> None:
        _patch_run(monkeypatch, _ok_result())
        monkeypatch.setattr(sync_module, "reconcile",
                            lambda vault, keys=None: (_ for _ in ()).throw(AssertionError("must not run")))
        assert sync_module.run(_args(json=True, selection=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload.get("next_actions", []) == []


class TestTerminalMode:
    def test_text_runs_automatic_local_inline_and_pends_remote(
        self, tmp_path, monkeypatch, capsys,
    ) -> None:
        """The shared runner executes memory.build (automatic local) inline
        and leaves embed.resume pending with a confirmation notice — no
        command-specific branch.  The real preflight needs canonical config
        + a library index, so the test uses a real config and a stubbed
        index."""
        from tests.conftest import canonical_test_config

        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        builds: list[int] = []
        import paperforge.memory.builder as builder_module
        import paperforge.worker.asset_index as asset_index_module

        def fake_build(vault, keys=None):
            builds.append(1)
            return {"papers_indexed": 3, "hash_match": True}

        monkeypatch.setattr(builder_module, "build_for_keys", fake_build)
        monkeypatch.setattr(asset_index_module, "read_index",
                            lambda vault: {"items": [{"zotero_key": "A"}]})
        _patch_run(monkeypatch, _ok_result())
        _patch_reconcile(monkeypatch, PFResult(
            ok=True, command="reconcile", version=__version__, data={},
            next_actions=[_wire("memory.build"), _wire("embed.resume")],
        ))
        assert sync_module.run(_args(vault_path=vault)) == 0
        out = capsys.readouterr().out
        assert builds == [1]
        assert "ok: memory.build" in out
        assert "embed.resume" in out
        assert "needs confirmation" in out

    def test_text_failed_sync_returns_1_and_no_reconcile(self, monkeypatch, capsys) -> None:
        builds: list[int] = []
        import paperforge.memory.builder as builder_module

        def fake_build(vault, keys=None):
            builds.append(1)
            return {"papers_indexed": 3, "hash_match": True}

        monkeypatch.setattr(builder_module, "build_for_keys", fake_build)
        result = PFResult(ok=False, command="sync", version=__version__)
        _patch_run(monkeypatch, result)
        monkeypatch.setattr(sync_module, "reconcile",
                            lambda vault, keys=None: (_ for _ in ()).throw(AssertionError("must not run")))
        assert sync_module.run(_args()) == 1
        assert builds == []
        assert capsys.readouterr().out == ""

    def test_text_dry_run_returns_before_service(self, monkeypatch, capsys) -> None:
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


class TestO2:
    def test_forced_memory_build_failure_leaks_no_embed_resume(
        self, monkeypatch, capsys,
    ) -> None:
        """O2: memory.build fails → no successful publish → no post-publish
        reconcile → embed.resume appears NOWHERE (executed, pending, or
        next_actions of the emitted result)."""
        import paperforge.memory.builder as builder_module

        def failing_build(vault, keys=None):
            raise FileNotFoundError("forced memory build failure")

        monkeypatch.setattr(builder_module, "build_for_keys", failing_build)
        _patch_run(monkeypatch, _ok_result())
        _patch_reconcile(monkeypatch, PFResult(
            ok=True, command="reconcile", version=__version__, data={},
            next_actions=[_wire("memory.build")],
        ))
        assert sync_module.run(_args(json=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        ids = [a["action_id"] for a in payload["next_actions"]]
        assert "embed.resume" not in ids

    def test_reconcile_all_never_changed_keys_only(self, monkeypatch, capsys) -> None:
        """The cutover calls reconcile(all) — chain breaks must recover even
        when the source is unchanged (#159 §4)."""
        seen: list[Any] = []
        _patch_run(monkeypatch, _ok_result())

        def fake_reconcile(vault, keys=None):
            seen.append(keys)
            return PFResult(ok=True, command="reconcile", version=__version__, data={})

        monkeypatch.setattr(sync_module, "reconcile", fake_reconcile)
        assert sync_module.run(_args()) == 0
        capsys.readouterr()
        assert seen == [None], "reconcile(all) must be the sync cutover trigger"


class TestContract:
    def test_no_fire_and_forget_spawn_remains(self) -> None:
        """The Popen embed spawn AND the hardcoded terminal follow-up branch
        are gone from the sync module."""
        import inspect

        source = inspect.getsource(sync_module)
        assert "subprocess.Popen" not in source
        assert "_run_terminal_followups" not in source
        assert "_run_memory_build" not in source
        assert "_attach_next_actions" not in source
