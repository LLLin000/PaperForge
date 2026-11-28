"""Tests for SyncService.prune() integration."""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from paperforge.services.sync_service import SyncService

from tests.conftest import canonical_test_config


@pytest.fixture(autouse=True)
def _canonical_vault_config(tmp_path: Path) -> None:
    canonical_test_config(tmp_path)


class TestSyncServicePruneMethod:
    """SyncService.prune() — delegates to worker module."""

    def test_prune_calls_worker_module(self, tmp_path: Path) -> None:
        svc = SyncService(tmp_path)
        fresh_index = {"schema_version": "3", "items": []}

        with patch("paperforge.worker.prune.prune_orphan_papers") as mock_fn:
            mock_fn.return_value = {"preview": [], "deleted": [], "counts": {}}
            result = svc.prune({}, fresh_index=fresh_index, dry_run=True)

        mock_fn.assert_called_once()
        assert result["deleted"] == []

    def test_prune_dry_run_passed_through(self, tmp_path: Path) -> None:
        svc = SyncService(tmp_path)
        fresh_index = {"schema_version": "3", "items": []}

        with patch("paperforge.worker.prune.prune_orphan_papers") as mock_fn:
            mock_fn.return_value = {"preview": [{"key": "k1"}], "deleted": [], "counts": {}}
            result = svc.prune({}, fresh_index=fresh_index, dry_run=True)

        mock_fn.assert_called_once()
        _, kwargs = mock_fn.call_args
        assert kwargs.get("dry_run") is True

    def test_prune_passes_zotero_keys(self, tmp_path: Path) -> None:
        """Zotero is the authority: the caller passes the LIVE export key
        set (fresh_keys); prune never re-reads the index snapshot (which
        would falsely orphan a freshly added Zotero paper)."""
        svc = SyncService(tmp_path)
        fake_keys = {"KEY1", "KEY2"}

        with patch("paperforge.worker.asset_index.read_index") as mock_read:
            with patch("paperforge.worker.prune.prune_orphan_papers") as mock_fn:
                mock_fn.return_value = {"preview": [], "deleted": [], "counts": {}}
                svc.prune({}, fresh_index=None, fresh_keys=fake_keys, dry_run=True)

        mock_read.assert_not_called()
        mock_fn.assert_called_once()
        _, kwargs = mock_fn.call_args
        assert kwargs.get("fresh_keys") == fake_keys


class TestSyncServiceRunPrune:
    """SyncService.run() with prune/prune_force flags."""

    def _make_svc(self, tmp_path: Path) -> SyncService:
        vault = tmp_path
        vault.mkdir(parents=True, exist_ok=True)
        canonical_test_config(
            vault,
            system_dir=".paperforge",
            resources_dir="Resources",
            literature_dir="Resources/Literature",
        )
        (vault / ".paperforge" / "exports").mkdir(parents=True)
        (vault / ".paperforge" / "indexes").mkdir(parents=True)
        (vault / "Resources" / "Literature").mkdir(parents=True)
        return SyncService(vault)

    def test_run_with_prune_force_calls_prune_twice(self, tmp_path: Path) -> None:
        svc = self._make_svc(tmp_path)
        svc.paths = {
            "literature": tmp_path / "Resources" / "Literature",
            "exports": tmp_path / ".paperforge" / "exports",
            "index": tmp_path / ".paperforge" / "indexes",
            "system_dir": tmp_path / ".paperforge",
        }

        with patch.object(svc, "prune") as mock_prune:
            mock_prune.return_value = {"preview": [], "deleted": [], "counts": {}}
            with ExitStack() as stack:
                stack.enter_context(patch.object(svc, "resolve_paths", return_value=svc.paths))
                stack.enter_context(patch("paperforge.worker.sync.load_export_rows", return_value=[]))
                stack.enter_context(patch("paperforge.worker._domain.load_domain_config"))
                stack.enter_context(patch("paperforge.worker.base_views.ensure_base_views"))
                stack.enter_context(patch("paperforge.config.load_vault_config"))
                stack.enter_context(patch("paperforge.worker.sync.migrate_to_workspace"))
                stack.enter_context(patch("paperforge.worker.asset_index.build_index", return_value=0))
                stack.enter_context(patch("paperforge.worker.asset_index.read_index", return_value={"schema_version": "3", "items": []}))
                svc.run(prune=True, prune_force=True)

        # prune always runs dry-run; prune_force triggers a second call for actual delete
        assert mock_prune.call_count == 2
        assert mock_prune.call_args_list[0][1]["dry_run"] is True
        assert mock_prune.call_args_list[1][1]["dry_run"] is False

    def test_run_without_prune_calls_dry_run_only(self, tmp_path: Path) -> None:
        svc = self._make_svc(tmp_path)
        svc.paths = {
            "literature": tmp_path / "Resources" / "Literature",
            "exports": tmp_path / ".paperforge" / "exports",
            "index": tmp_path / ".paperforge" / "indexes",
            "system_dir": tmp_path / ".paperforge",
        }

        with patch.object(svc, "prune") as mock_prune:
            mock_prune.return_value = {"preview": [], "deleted": [], "counts": {}}
            with ExitStack() as stack:
                stack.enter_context(patch.object(svc, "resolve_paths", return_value=svc.paths))
                stack.enter_context(patch("paperforge.worker.sync.load_export_rows", return_value=[]))
                stack.enter_context(patch("paperforge.worker._domain.load_domain_config"))
                stack.enter_context(patch("paperforge.worker.base_views.ensure_base_views"))
                stack.enter_context(patch("paperforge.config.load_vault_config"))
                stack.enter_context(patch("paperforge.worker.sync.migrate_to_workspace"))
                stack.enter_context(patch("paperforge.worker.asset_index.build_index", return_value=0))
                stack.enter_context(patch("paperforge.worker.asset_index.read_index", return_value={"schema_version": "3", "items": []}))
                svc.run()

        # prune always runs once (dry-run) to collect orphan data for the result
        mock_prune.assert_called_once()
        assert mock_prune.call_args[1]["dry_run"] is True

    def test_prune_refuses_empty_zotero_keys_on_source_error(self, tmp_path: Path) -> None:
        """PF-MIG-001: prune_orphan_papers must refuse to prune when Zotero key set is empty or source failed."""
        from paperforge.worker.prune import prune_orphan_papers

        ws = tmp_path / "Resources" / "Literature" / "Ortho" / "ZOT00001 - Keep Me"
        ws.mkdir(parents=True)
        (ws / "ZOT00001.md").write_text("---\nzotero_key: ZOT00001\n---\n", encoding="utf-8")

        res_empty = prune_orphan_papers(tmp_path, fresh_keys=set(), dry_run=False)
        assert res_empty["preview"] == []
        assert res_empty["deleted"] == []
        assert res_empty.get("blocked_reason") == "empty_or_incomplete_zotero_keys"
        assert ws.exists()

        res_err = prune_orphan_papers(
            tmp_path, fresh_index={"items": []}, dry_run=False, source_ok=False
        )
        assert res_err["deleted"] == []
        assert ws.exists()
