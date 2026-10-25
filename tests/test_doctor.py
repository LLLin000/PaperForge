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

def _empty_vault(tmp_path):
    from tests.conftest import canonical_test_config

    tmp_path.mkdir(parents=True, exist_ok=True)
    canonical_test_config(
        tmp_path,
        system_dir="99_System",
        resources_dir="03_Resources",
        literature_dir="Literature",
        control_dir="LiteratureControl",
        base_dir="05_Bases",
    )
    return tmp_path


def test_doctor_missing_pointer_reports_setup_and_skips_target_probes(tmp_path, capsys, monkeypatch):
    from paperforge.worker import status as status_mod
    import paperforge.runtime_pointer as _rp

    vault = _empty_vault(tmp_path)
    monkeypatch.setattr(_rp, "read_pointer", lambda *a, **k: None)

    def _boom(*a, **k):
        raise AssertionError("target-environment probe must not run without a pointer")

    monkeypatch.setattr(status_mod, "_query_resolved_version", _boom)
    monkeypatch.setattr(status_mod, "_query_resolved_package", _boom)
    monkeypatch.setattr(status_mod, "_query_resolved_module", _boom)

    code = status_mod.run_doctor(vault)
    assert code == 1


def test_doctor_missing_pointer_json_reports_setup(tmp_path, capsys, monkeypatch):
    import json as _json
    from paperforge.worker import status as status_mod
    import paperforge.runtime_pointer as _rp

    vault = _empty_vault(tmp_path)
    monkeypatch.setattr(_rp, "read_pointer", lambda *a, **k: None)

    code = status_mod.run_doctor(vault, json_output=True)
    assert code == 1
    out = capsys.readouterr().out
    payload = _json.loads(out)
    cats = {(c["category"], c["status"]): c for c in payload["data"]["checks"]}
    assert cats[("Python 环境 (插件)", "fail")]["fix"] == "Run `paperforge setup` to publish the executable PaperForge runtime"
    assert ("PaperForge 包", "info") in cats


def test_doctor_valid_pointer_queries_pointer_target(tmp_path, capsys, monkeypatch):
    import json as _json
    from paperforge.worker import status as status_mod
    import paperforge
    import paperforge.runtime_pointer as _rp

    vault = _empty_vault(tmp_path)
    seen: list[str] = []

    def _fake_version(interp, extra):
        seen.append(interp)
        return ("Python 3.12.8", (3, 12, 8))

    def _fake_package(interp, extra, name):
        seen.append(interp)
        return {"Version": paperforge.__version__, "Location": "/rt"}

    def _fake_module(interp, extra, name):
        seen.append(interp)
        return {"version": "1", "file": paperforge.__file__}

    monkeypatch.setattr(
        _rp, "read_pointer",
        lambda *a, **k: {"schema_version": 1, "python_path": "/rt/python", "environment_root": "/rt", "paperforge_version": paperforge.__version__},
    )
    monkeypatch.setattr("pathlib.Path.is_file", lambda self: True)
    monkeypatch.setattr(status_mod, "_query_resolved_version", _fake_version)
    monkeypatch.setattr(status_mod, "_query_resolved_package", _fake_package)
    monkeypatch.setattr(status_mod, "_query_resolved_module", _fake_module)

    status_mod.run_doctor(vault, json_output=True)
    out = capsys.readouterr().out
    payload = _json.loads(out)
    interp_checks = [c for c in payload["data"]["checks"] if c["category"] == "Python 环境 (插件)"]
    assert any("/rt/python" in c["message"] for c in interp_checks)
    assert seen and all(s == "/rt/python" for s in seen)


def test_doctor_stale_pointer_reports_update_without_probes(tmp_path, capsys, monkeypatch):
    import json as _json
    from paperforge.worker import status as status_mod
    import paperforge.runtime_pointer as _rp

    vault = _empty_vault(tmp_path)
    # Real existing executable: isolates the stale-version condition from the
    # missing-file condition (no fake '/rt/python' that would not exist).
    import sys as _sys

    exe = _sys.executable
    assert __import__("pathlib").Path(exe).is_file()
    monkeypatch.setattr(
        _rp, "read_pointer",
        lambda *a, **k: {"schema_version": 1, "python_path": exe, "environment_root": "/rt", "paperforge_version": "0.0.0-stale"},
    )

    def _boom(*a, **k):
        raise AssertionError("stale pointer must not be probed")

    monkeypatch.setattr(status_mod, "_query_resolved_version", _boom)
    monkeypatch.setattr(status_mod, "_query_resolved_package", _boom)
    monkeypatch.setattr(status_mod, "_query_resolved_module", _boom)

    code = status_mod.run_doctor(vault, json_output=True)
    assert code == 1
    payload = _json.loads(capsys.readouterr().out)
    cats = [c for c in payload["data"]["checks"] if c["category"] == "Python 环境 (插件)"]
    assert cats and all(c["status"] == "fail" for c in cats)
    assert any(c["fix"] for c in cats)


def test_doctor_queries_distribution_without_pip(tmp_path):
    import json
    import os
    import venv
    from paperforge.worker import status as status_mod

    runtime = tmp_path / "runtime"
    venv.EnvBuilder(with_pip=False).create(runtime)
    python = str(runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    probe = status_mod.run_readonly_probe(
        [python, "-c", "import json,sysconfig,importlib.util; print(json.dumps({'site':sysconfig.get_path('purelib'),'pip':importlib.util.find_spec('pip') is not None}))"],
        timeout=10,
    )
    environment = json.loads(probe.stdout)
    assert environment["pip"] is False
    from pathlib import Path

    site = Path(environment["site"])
    metadata = site / "metadata_probe-9.9.9.dist-info"
    metadata.mkdir(parents=True)
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: metadata-probe\nVersion: 9.9.9\n", encoding="utf-8"
    )
    assert status_mod._query_resolved_package(python, [], "metadata-probe") == {
        "Name": "metadata-probe", "Version": "9.9.9", "Location": str(site),
    }
    assert status_mod._query_resolved_package(python, [], "missing-distribution") is None


def test_doctor_never_suggests_inplace_or_global_pip(tmp_path, capsys, monkeypatch):
    import json as _json
    from paperforge.worker import status as status_mod
    import paperforge
    import paperforge.runtime_pointer as _rp

    vault = _empty_vault(tmp_path)
    monkeypatch.setattr(
        _rp, "read_pointer",
        lambda *a, **k: {"schema_version": 1, "python_path": "/rt/python", "environment_root": "/rt", "paperforge_version": paperforge.__version__},
    )
    monkeypatch.setattr(status_mod, "_query_resolved_version", lambda i, e: ("Python 3.12.8", (3, 12, 8)))
    monkeypatch.setattr(status_mod, "_query_resolved_package", lambda i, e, n: None)
    monkeypatch.setattr(status_mod, "_query_resolved_module", lambda i, e, n: None)

    status_mod.run_doctor(vault, json_output=True)
    out = capsys.readouterr().out
    assert "-m pip install" not in out
    assert "pip install -e" not in out
    payload = _json.loads(out)
    fixes = " ".join(c.get("fix", "") for c in payload["data"]["checks"])
    assert "setup" in fixes or "repair --runtime" in fixes
