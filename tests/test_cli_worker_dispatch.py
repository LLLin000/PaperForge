# Tests for paperforge CLI worker dispatch
# These tests prove the locked command surface without invoking real workers.

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# ----------------------------------------------------------------------
# Worker function stubs — capture calls for assertion
# ----------------------------------------------------------------------
CAPTURED_CALLS: list[tuple[str, Path]] = []


def stub_run_status(vault: Path, verbose: bool = False, json_output: bool = False) -> int:
    CAPTURED_CALLS.append(("run_status", vault))
    return 0


def stub_run_selection_sync(vault: Path, verbose: bool = False, json_output: bool = False) -> dict:
    CAPTURED_CALLS.append(("run_selection_sync", vault))
    return {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}


def stub_run_index_refresh(
    vault: Path, verbose: bool = False, rebuild_index: bool = False, json_output: bool = False
) -> dict:
    CAPTURED_CALLS.append(("run_index_refresh", vault))
    return {"updated": 0, "failed": 0, "errors": []}


def stub_run_deep_reading(vault: Path, verbose: bool = False) -> int:
    CAPTURED_CALLS.append(("run_deep_reading", vault))
    return 0


def stub_run_ocr(vault: Path, verbose: bool = False, no_progress: bool = False) -> int:
    CAPTURED_CALLS.append(("run_ocr", vault))
    return 0


# ----------------------------------------------------------------------
# Test fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def clean_captured():
    """Clear captured calls before each test."""
    CAPTURED_CALLS.clear()
    yield
    CAPTURED_CALLS.clear()


@pytest.fixture
def mock_vault(tmp_path):
    """Create a minimal mock vault with paperforge.json."""
    pf_cfg = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
    }
    (tmp_path / "paperforge.json").write_text(json.dumps(pf_cfg), encoding="utf-8")
    return tmp_path


# ----------------------------------------------------------------------
# Worker dispatch tests
# ----------------------------------------------------------------------
def test_status_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'status']) calls run_status."""
    import importlib

    import paperforge.cli as cli

    importlib.reload(cli)

    with patch.object(cli, "run_status", stub_run_status):
        argv = ["--vault", str(mock_vault), "status"]
        cli.main(argv)

    assert ("run_status", mock_vault) in CAPTURED_CALLS


def test_selection_sync_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'selection-sync']) runs SyncService (v2.1 contract)."""
    import importlib

    import paperforge.worker.sync as wsync

    importlib.reload(wsync)

    with patch.object(wsync, "run_selection_sync", stub_run_selection_sync):
        argv = ["--vault", str(mock_vault), "selection-sync"]
        import paperforge.cli as cli

        importlib.reload(cli)
        cli.main(argv)

    assert ("run_selection_sync", mock_vault) in CAPTURED_CALLS


def test_index_refresh_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'index-refresh']) runs index-only SyncService lookup."""
    # v2.1: index-refresh routes through SyncService, not directly to worker.
    # Mock the worker import that SyncService uses for the selection phase skip.
    import importlib

    import paperforge.services.sync_service as svc_mod

    importlib.reload(svc_mod)

    captured_vault = []

    def mock_run(self, verbose=False, json_output=False, selection_only=False, index_only=False):
        captured_vault.append(self.vault)
        from paperforge.core.result import PFResult

        return PFResult(ok=True, command="sync", version="1.0.0", data={})

    with patch.object(svc_mod.SyncService, "run", mock_run):
        argv = ["--vault", str(mock_vault), "index-refresh"]
        import paperforge.cli as cli

        importlib.reload(cli)
        cli.main(argv)

    assert len(captured_vault) == 1
    assert captured_vault[0] == mock_vault


def test_deep_reading_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'deep-reading']) calls run_deep_reading."""
    import importlib

    import paperforge.cli as cli

    importlib.reload(cli)

    with patch.object(cli, "run_deep_reading", stub_run_deep_reading):
        argv = ["--vault", str(mock_vault), "deep-reading"]
        cli.main(argv)

    assert ("run_deep_reading", mock_vault) in CAPTURED_CALLS


def test_ocr_run_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'ocr', 'run']) calls run_ocr."""
    import importlib

    import paperforge.cli as cli

    importlib.reload(cli)

    with patch.object(cli, "run_ocr", stub_run_ocr):
        argv = ["--vault", str(mock_vault), "ocr", "run"]
        cli.main(argv)

    assert ("run_ocr", mock_vault) in CAPTURED_CALLS


def test_ocr_alias_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'ocr']) calls run_ocr (alias for 'ocr run')."""
    import importlib

    import paperforge.cli as cli

    importlib.reload(cli)

    with patch.object(cli, "run_ocr", stub_run_ocr):
        argv = ["--vault", str(mock_vault), "ocr"]
        cli.main(argv)

    assert ("run_ocr", mock_vault) in CAPTURED_CALLS


def test_ocr_doctor_dispatch(clean_captured, mock_vault):
    """main(['--vault', vault, 'ocr', 'doctor']) calls _cmd_ocr_doctor."""
    import importlib

    import paperforge.cli as cli

    importlib.reload(cli)

    with patch.object(cli, "_cmd_ocr_doctor", lambda vault, args: 0):
        argv = ["--vault", str(mock_vault), "ocr", "doctor"]
        code = cli.main(argv)

    assert code == 0
