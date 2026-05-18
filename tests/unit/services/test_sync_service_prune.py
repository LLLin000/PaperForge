"""Tests for SyncService.prune() integration."""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from paperforge.services.sync_service import SyncService


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

    def test_prune_auto_reads_index(self, tmp_path: Path) -> None:
        svc = SyncService(tmp_path)
        fake_index = {"schema_version": "3", "items": []}

        with patch("paperforge.worker.asset_index.read_index", return_value=fake_index) as mock_read:
            with patch("paperforge.worker.prune.prune_orphan_papers") as mock_fn:
                mock_fn.return_value = {"preview": [], "deleted": [], "counts": {}}
                svc.prune({}, fresh_index=None, dry_run=True)

        mock_read.assert_called_once()
        mock_fn.assert_called_once()


class TestSyncServiceRunPrune:
    """SyncService.run() with prune/prune_force flags."""

    def _make_svc(self, tmp_path: Path) -> SyncService:
        vault = tmp_path
        (vault / "paperforge.json").write_text(
            '{"system_dir": "System", "resources_dir": "Resources", "literature_dir": "Resources/Literature"}'
        )
        (vault / "System" / "PaperForge" / "exports").mkdir(parents=True)
        (vault / "System" / "PaperForge" / "indexes").mkdir(parents=True)
        (vault / "Resources" / "Literature").mkdir(parents=True)
        return SyncService(vault)

    def test_run_with_prune_force_calls_prune_twice(self, tmp_path: Path) -> None:
        svc = self._make_svc(tmp_path)
        svc.paths = {
            "literature": tmp_path / "Resources" / "Literature",
            "exports": tmp_path / "System" / "PaperForge" / "exports",
            "index": tmp_path / "System" / "PaperForge" / "indexes",
            "system_dir": tmp_path / "System",
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
            "exports": tmp_path / "System" / "PaperForge" / "exports",
            "index": tmp_path / "System" / "PaperForge" / "indexes",
            "system_dir": tmp_path / "System",
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
