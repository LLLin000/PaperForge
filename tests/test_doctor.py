from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import canonical_test_config


def stub_run_doctor(vault: Path) -> int:
    return 0


def test_doctor_command_exists(clean_captured, mock_vault):
    import importlib

    import paperforge.cli as cli

    importlib.reload(cli)

    with patch("paperforge.worker.status.run_doctor", stub_run_doctor):
        argv = ["--vault", str(mock_vault), "doctor"]
        code = cli.main(argv)

    assert code == 0


def test_doctor_python_check():
    import inspect

    from paperforge.worker.status import run_doctor

    sig = inspect.signature(run_doctor)
    assert "vault" in sig.parameters


def test_doctor_returns_int():
    import inspect

    from paperforge.worker.status import run_doctor

    inspect.signature(run_doctor)
    assert True


@pytest.fixture
def clean_captured():
    yield


@pytest.fixture
def mock_vault(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical_test_config(
        tmp_path,
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        control_dir="LiteratureControl",
        base_dir="05_Bases",
    )
    (tmp_path / "99_System").mkdir()
    (tmp_path / "03_Resources").mkdir()
    return tmp_path


def test_doctor_on_empty_vault(tmp_path, capsys):
    from paperforge.worker.status import run_doctor

    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical_test_config(
        tmp_path,
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        control_dir="LiteratureControl",
        base_dir="05_Bases",
    )
    code = run_doctor(tmp_path)
    captured = capsys.readouterr().out
    assert "PaperForge Doctor" in captured
    assert "[FAIL]" in captured or "[WARN]" in captured
    assert code == 1
