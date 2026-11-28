"""The sync command attaches phase timing to its JSON data (diagnostics).

Pins the contract that `paperforge sync --json` carries `data.timing`
(stderr-only lines stay out of stdout) without needing a full sync fixture.
"""

from __future__ import annotations

import argparse
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from tests.conftest import canonical_test_config

from paperforge.core import timing
from paperforge.core.result import PFResult


def test_sync_attaches_phase_timing_to_json_data(tmp_path: Path, monkeypatch) -> None:
    from paperforge.commands import sync as sync_cmd

    canonical_test_config(tmp_path, system_dir=".paperforge")

    class FakeService:
        def __init__(self, vault: Path) -> None:
            self.vault = vault

        def run(self, **kwargs) -> PFResult:
            with timing.phase("sync.selection"):
                pass
            with timing.phase("sync.build_index"):
                pass
            return PFResult(
                ok=True, command="sync", version="0.0.0", data={"papers": 1}
            )

    monkeypatch.setattr(
        "paperforge.services.sync_service.SyncService", FakeService
    )
    args = argparse.Namespace(
        vault_path=tmp_path,
        vault=str(tmp_path),
        verbose=False,
        dry_run=False,
        selection=False,
        index=False,
        json=True,
        prune=False,
        prune_force=False,
        rebuild_index=False,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = sync_cmd.run(args)
    assert rc == 0
    payload = json.loads(buf.getvalue())
    t = payload["data"]["timing"]
    assert t["sync.service"] >= 0.0
    assert t["sync.selection"] >= 0.0
    assert t["sync.build_index"] >= 0.0
    assert t["total_ms"] >= 0.0
    # existing data keys survive
    assert payload["data"]["papers"] == 1


def test_sync_json_returns_pfresult_when_phase2_export_reload_fails(
    tmp_path: Path, monkeypatch
) -> None:
    from paperforge.commands import sync as sync_cmd
    from paperforge.config import paperforge_paths
    from paperforge.core.errors import ErrorCode

    canonical_test_config(tmp_path, system_dir=".paperforge")
    export_path = paperforge_paths(tmp_path)["exports"] / "test.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(
        json.dumps({"items": [{"key": "TEST001", "title": "Synthetic"}]}),
        encoding="utf-8",
    )

    def corrupt_export_after_selection(_vault, **_kwargs):
        export_path.write_text("{invalid-json", encoding="utf-8")
        return {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    monkeypatch.setattr(
        "paperforge.worker.sync.run_selection_sync",
        corrupt_export_after_selection,
    )
    monkeypatch.setattr(
        "paperforge.worker._domain.load_domain_config",
        lambda _paths: {"domains": [{"export_file": "test.json", "domain": "test"}]},
    )
    monkeypatch.setattr(
        "paperforge.worker.base_views.ensure_base_views", lambda *_args: None
    )
    monkeypatch.setattr(
        "paperforge.worker.sync.migrate_to_workspace", lambda *_args: None
    )
    monkeypatch.setattr(
        "paperforge.worker.asset_index.build_index", lambda *_args, **_kwargs: 0
    )
    monkeypatch.setattr(sync_cmd, "_write_orphan_state", lambda *_args: None)
    monkeypatch.setattr(
        sync_cmd, "_cleanup_legacy_snapshot_files", lambda *_args: None
    )

    args = argparse.Namespace(
        vault_path=tmp_path,
        verbose=False,
        dry_run=False,
        selection=False,
        index=False,
        json=True,
        prune=False,
        prune_force=False,
        rebuild_index=False,
    )
    output = io.StringIO()
    with redirect_stdout(output):
        rc = sync_cmd.run(args)

    payload = json.loads(output.getvalue())
    assert rc == 1
    assert payload["ok"] is False
    assert payload["error"]["code"] == ErrorCode.SYNC_FAILED.value
    assert payload["error"]["details"]["phase"] == "service"
    assert payload["error"]["details"]["exception_type"] == "JSONDecodeError"
