from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

import pytest

from paperforge import runtime_installer
from paperforge.runtime_pointer import pointer_dir, publish_pointer, read_pointer


def _fake_venv_run(
    command: list[str], *, cwd: Path | None = None, timeout: int = 300
) -> subprocess.CompletedProcess[str]:
    del timeout
    if command[-1] == "--version":
        return subprocess.CompletedProcess(command, 0, "Python 3.12.4\n", "")
    if command[1:3] == ["-m", "venv"]:
        venv_dir = Path(command[-1])
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True, exist_ok=True)
        python.write_bytes(b"test interpreter")
        return subprocess.CompletedProcess(command, 0, "", "")
    raise AssertionError(f"unexpected child process: {command!r}")


def _old_pointer(home: Path) -> dict[str, object]:
    old_python = (home / "old-runtime" / ("python.exe" if os.name == "nt" else "bin/python")).resolve()
    old_root = old_python.parent.parent if os.name != "nt" else old_python.parent
    publish_pointer(
        python_path=str(old_python),
        environment_root=str(old_root),
        paperforge_version="1.0.0",
        home=home,
    )
    return read_pointer(home=home) or {}


def test_install_runtime_publishes_only_after_candidate_verifies(tmp_path: Path, monkeypatch) -> None:
    verified = {"version": False, "vector": False}
    pip_calls: list[tuple[str, Path]] = []
    real_publish = runtime_installer.publish_pointer

    monkeypatch.setattr(runtime_installer, "_run", _fake_venv_run)
    monkeypatch.setattr(
        runtime_installer,
        "_pip_install",
        lambda python, spec, *, cwd: pip_calls.append((spec, cwd))
        or subprocess.CompletedProcess([str(python)], 0, "", ""),
    )

    def verify_version(
        python: str, *, cwd: Path | None = None
    ) -> tuple[bool, str | None, str | None]:
        verified["version"] = True
        return True, "1.5.15", None

    def verify_vector(python: str, *, cwd: Path | None = None) -> bool:
        verified["vector"] = True
        return True

    def publish_after_verification(**kwargs):
        assert verified == {"version": True, "vector": True}
        return real_publish(**kwargs)

    monkeypatch.setattr(runtime_installer, "_fresh_verify", verify_version)
    monkeypatch.setattr(runtime_installer, "_vector_imports_ok", verify_vector)
    monkeypatch.setattr(runtime_installer, "publish_pointer", publish_after_verification)

    result = runtime_installer.install_runtime(
        expected_version="1.5.15", home=tmp_path, base_python="python-test"
    )

    pointer = read_pointer(home=tmp_path)
    assert result.ok is True
    assert pointer is not None
    assert pointer["paperforge_version"] == "1.5.15"
    assert Path(pointer["python_path"]).is_file()
    assert Path(pointer["environment_root"]).is_dir()
    assert pointer["python_path"] != str(Path(sys.executable).resolve())
    assert pip_calls == [("paperforge[vector]==1.5.15", pointer_dir(tmp_path))]


def test_failed_install_keeps_old_pointer_and_removes_candidate(tmp_path: Path, monkeypatch) -> None:
    old_pointer = _old_pointer(tmp_path)
    candidate_dirs: list[Path] = []

    def create_candidate(
        command: list[str], *, cwd: Path | None = None, timeout: int = 300
    ) -> subprocess.CompletedProcess[str]:
        result = _fake_venv_run(command, cwd=cwd, timeout=timeout)
        if command[1:3] == ["-m", "venv"]:
            candidate_dirs.append(Path(command[-1]))
        return result

    monkeypatch.setattr(runtime_installer, "_run", create_candidate)
    monkeypatch.setattr(
        runtime_installer,
        "_pip_install",
        lambda python, spec, *, cwd: subprocess.CompletedProcess(
            [str(python)], 1, "", "dependency download failed"
        ),
    )

    with pytest.raises(runtime_installer.RuntimeInstallError) as exc_info:
        runtime_installer.install_runtime(
            expected_version="1.5.15", home=tmp_path, base_python="python-test"
        )

    assert exc_info.value.code == "runtime.pip_failed"
    assert read_pointer(home=tmp_path) == old_pointer
    assert len(candidate_dirs) == 1
    assert not candidate_dirs[0].exists()
def test_vault_setup_never_publishes_or_installs_runtime(tmp_path: Path, monkeypatch) -> None:
    from paperforge.setup import SetupStepResult
    from paperforge.setup import plan as plan_mod

    monkeypatch.setattr(
        "paperforge.setup.runtime.check_runtime_dependencies",
        lambda: SetupStepResult(
            step="runtime_dependencies", ok=True, message="runtime dependencies present"
        ),
    )
    monkeypatch.setattr(
        "paperforge.runtime_pointer.publish_pointer",
        lambda **kwargs: pytest.fail("vault setup must not publish the runtime pointer"),
    )
    monkeypatch.setattr(
        plan_mod,
        "AgentInstaller",
        lambda vault, agent_type="opencode": type(
            "Agent", (), {"steps": lambda self: iter(())}
        )(),
    )

    result = plan_mod.SetupPlan(
        tmp_path,
        config={"system_dir": "System", "resources_dir": "Resources"},
        skip_checks=True,
    ).execute()

    assert result == 0
def test_runtime_status_runs_without_a_vault_or_pipeline(tmp_path: Path, monkeypatch, capsys) -> None:
    from paperforge import cli

    monkeypatch.setattr(
        runtime_installer,
        "inspect_runtime",
        lambda **kwargs: {
            "runtime_ready": False,
            "runtime_state": "attention",
            "pointer_path": str(tmp_path / "pointer.json"),
            "paperforge_version": None,
        },
    )
    monkeypatch.setattr(
        cli, "resolve_vault", lambda **kwargs: pytest.fail("runtime status must not resolve a vault")
    )
    monkeypatch.setattr(
        cli, "_resolve_pipeline", lambda: pytest.fail("runtime status must not resolve pipeline modules")
    )

    assert cli._run_cli(["runtime", "status", "--json"]) == 0
    assert '"runtime_state": "attention"' in capsys.readouterr().out


def _installable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runtime_installer, "_run", _fake_venv_run)
    monkeypatch.setattr(
        runtime_installer,
        "_pip_install",
        lambda python, spec, *, cwd: subprocess.CompletedProcess([str(python)], 0, "", ""),
    )
    monkeypatch.setattr(
        runtime_installer,
        "_fresh_verify",
        lambda python, *, cwd=None: (True, "1.5.15", None),
    )
    monkeypatch.setattr(runtime_installer, "_vector_imports_ok", lambda python, *, cwd=None: True)


def test_update_prunes_old_environments_but_keeps_one_previous(tmp_path: Path, monkeypatch) -> None:
    _installable(tmp_path, monkeypatch)
    runtime_dir = pointer_dir(tmp_path)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    older = runtime_dir / "venv-1.0.0-aaaa"
    previous = runtime_dir / "venv-1.4.0-bbbb"
    for index, env in enumerate((older, previous)):
        env.mkdir()
        (env / "Scripts").mkdir()
        marker = env / "marker"
        marker.write_text("x", encoding="utf-8")
        os.utime(marker, (index + 1, index + 1))

    result = runtime_installer.install_runtime(
        expected_version="1.5.15", home=tmp_path, base_python="python-test", force=True
    )

    assert result.ok is True
    assert any(a.startswith("environments_pruned:") for a in result.actions_taken)
    assert not older.exists(), "oldest environment should be pruned"
    assert previous.exists(), "the newest previous environment is kept"
    current = Path(result.environment_root)
    assert current.exists()


def test_prune_never_touches_the_published_environment(tmp_path: Path, monkeypatch) -> None:
    _installable(tmp_path, monkeypatch)
    runtime_dir = pointer_dir(tmp_path)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    published = runtime_dir / "venv-current"
    (published / "Scripts").mkdir(parents=True)
    publish_pointer(
        python_path=str(published / "Scripts" / "python.exe"),
        environment_root=str(published),
        paperforge_version="1.5.15",
        home=tmp_path,
    )

    runtime_installer.install_runtime(
        expected_version="1.5.15", home=tmp_path, base_python="python-test", force=True
    )

    assert published.exists()


def test_interrupt_during_install_removes_candidate_and_keeps_pointer(tmp_path: Path, monkeypatch) -> None:
    old_pointer = _old_pointer(tmp_path)
    monkeypatch.setattr(runtime_installer, "_run", _fake_venv_run)

    def interrupted(python, spec, *, cwd):
        raise KeyboardInterrupt

    monkeypatch.setattr(runtime_installer, "_pip_install", interrupted)

    with pytest.raises(KeyboardInterrupt):
        runtime_installer.install_runtime(
            expected_version="1.5.15", home=tmp_path, base_python="python-test"
        )

    assert read_pointer(home=tmp_path) == old_pointer
    leftovers = [p for p in pointer_dir(tmp_path).iterdir() if p.name.startswith(".venv-candidate-")]
    assert leftovers == []
