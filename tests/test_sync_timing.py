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

    canonical_test_config(tmp_path)

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
