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

    older = runtime_dir / ".venv-candidate-1.0.0-aaaa"
    previous = runtime_dir / ".venv-candidate-1.4.0-bbbb"
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
    published = runtime_dir / ".venv-candidate-current"
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

# ── install concurrency and prune scope (2026-11-06) ────────────────────────

def test_install_lock_blocks_a_second_installer(tmp_path):
    """Two clicks must not build competing candidates."""
    from paperforge.runtime_installer import install_lock

    with install_lock(tmp_path):
        with pytest.raises(Exception) as excinfo:
            with install_lock(tmp_path):
                pass
    assert "already running" in str(excinfo.value).lower()
    # Released on the way out of the context manager.
    with install_lock(tmp_path):
        pass


def test_install_lock_recovers_a_stale_lock(tmp_path):
    import os
    import time

    from paperforge.runtime_installer import LOCK_NAME, install_lock

    path = tmp_path / LOCK_NAME
    path.write_text("999999 0\n", encoding="utf-8")
    old = time.time() - 7200
    os.utime(path, (old, old))
    with install_lock(tmp_path):
        pass
    assert not path.exists()


def test_prune_never_deletes_a_foreign_environment(tmp_path):
    """`venv-*` belongs to the old TypeScript bootstrap or to the user."""
    import os

    from paperforge.runtime_installer import _prune_environments

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    ours_old = runtime_dir / ".venv-candidate-old"
    ours_new = runtime_dir / ".venv-candidate-new"
    foreign = runtime_dir / "venv-user-owned"
    for d in (ours_old, ours_new, foreign):
        d.mkdir()
    for i, d in enumerate((ours_old, ours_new, foreign)):
        os.utime(d, (1_600_000_000 + i, 1_600_000_000 + i))

    removed = _prune_environments(runtime_dir, ours_new, keep_previous=0)

    assert removed == 1
    assert not ours_old.exists()
    assert ours_new.exists()
    assert foreign.exists(), "prune must never touch a directory it did not create"


def test_pip_install_falls_back_to_pypi_mirror_on_failure(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if "-i" in command:
            return subprocess.CompletedProcess(command, 0, "ok mirror", "")
        return subprocess.CompletedProcess(command, 1, "", "connection timeout")

    monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    monkeypatch.delenv("PIP_FIND_LINKS", raising=False)
    monkeypatch.setattr(runtime_installer, "_run", fake_run)

    result = runtime_installer._pip_install(tmp_path / "python", "paperforge[vector]==2.0.0", cwd=tmp_path)

    assert result.returncode == 0
    assert len(calls) == 2
    assert "-i" not in calls[0]
    assert runtime_installer._FALLBACK_PYPI_INDEX in calls[1]


def test_pip_install_falls_back_to_aliyun_after_tuna_fails(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if runtime_installer._ALIYUN_PYPI_INDEX in command:
            return subprocess.CompletedProcess(command, 0, "ok aliyun", "")
        return subprocess.CompletedProcess(command, 1, "", "mirror timeout")

    monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    monkeypatch.delenv("PIP_FIND_LINKS", raising=False)
    monkeypatch.setattr(runtime_installer, "_run", fake_run)

    result = runtime_installer._pip_install(tmp_path / "python", "paperforge[vector]==2.0.0", cwd=tmp_path)

    assert result.returncode == 0
    assert len(calls) == 3
    assert runtime_installer._FALLBACK_PYPI_INDEX in calls[1]
    assert runtime_installer._ALIYUN_PYPI_INDEX in calls[2]


def test_install_runtime_fast_patches_when_deps_lock_hash_matches(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = pointer_dir(tmp_path)
    old_env = runtime_dir / ".venv-candidate-old"
    if os.name == "nt":
        old_py = old_env / "Scripts" / "python.exe"
        old_sp = old_env / "Lib" / "site-packages"
    else:
        old_py = old_env / "bin" / "python"
        old_sp = old_env / "lib" / "python3.12" / "site-packages"
    old_py.parent.mkdir(parents=True, exist_ok=True)
    old_py.write_bytes(b"old-py")
    (old_sp / "openai").mkdir(parents=True, exist_ok=True)
    (old_sp / "openai" / "__init__.py").write_text("# cached", encoding="utf-8")
    (old_sp / "sqlite_vec").mkdir(parents=True, exist_ok=True)
    (old_sp / "sqlite_vec" / "__init__.py").write_text("# cached", encoding="utf-8")
    (old_sp / "paperforge").mkdir(parents=True, exist_ok=True)
    (old_sp / "paperforge" / "__init__.py").write_text("__version__ = '2.0.0'", encoding="utf-8")

    deps_hash = runtime_installer.compute_deps_lock_hash()
    publish_pointer(
        python_path=str(old_py),
        environment_root=str(old_env),
        paperforge_version="2.0.0",
        deps_lock_hash=deps_hash,
        home=tmp_path,
    )

    def fake_venv(command: list[str], *, cwd: Path | None = None, timeout: int = 300):
        del cwd, timeout
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "Python 3.12.4\n", "")
        if command[1:3] == ["-m", "venv"]:
            venv_dir = Path(command[-1])
            py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            sp = venv_dir / ("Lib/site-packages" if os.name == "nt" else "lib/python3.12/site-packages")
            py.parent.mkdir(parents=True, exist_ok=True)
            sp.mkdir(parents=True, exist_ok=True)
            py.write_bytes(b"new-py")
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected command: {command!r}")

    no_deps_specs: list[str] = []
    full_pip_specs: list[str] = []
    monkeypatch.setattr(runtime_installer, "_run", fake_venv)
    monkeypatch.setattr(
        runtime_installer,
        "_pip_install_no_deps",
        lambda py, spec, *, cwd: no_deps_specs.append(spec) or subprocess.CompletedProcess([str(py)], 0, "", ""),
    )
    monkeypatch.setattr(
        runtime_installer,
        "_pip_install",
        lambda py, spec, *, cwd: full_pip_specs.append(spec) or subprocess.CompletedProcess([str(py)], 0, "", ""),
    )
    monkeypatch.setattr(
        runtime_installer,
        "_fresh_verify",
        lambda py, *, cwd=None: (True, "2.1.0", None),
    )
    monkeypatch.setattr(runtime_installer, "_vector_imports_ok", lambda py, *, cwd=None: True)

    res = runtime_installer.install_runtime(
        expected_version="2.1.0", home=tmp_path, base_python="python-test"
    )
    assert res.ok is True
    assert no_deps_specs == ["paperforge==2.1.0"]
    assert full_pip_specs == []
    assert "fast_patch_deps_reused" in res.actions_taken
    new_root = Path(res.environment_root)
    new_sp = new_root / ("Lib/site-packages" if os.name == "nt" else "lib/python3.12/site-packages")
    assert (new_sp / "openai" / "__init__.py").is_file()
    assert not (new_sp / "paperforge" / "__init__.py").exists()

    # Decoupled min_engine_version accepts newer plugin patches
    status = runtime_installer.inspect_runtime(
        home=tmp_path, expected_version="2.1.4", min_engine_version="2.1.0", base_python="python-test"
    )
    assert status["runtime_ready"] is True
    assert status["compatible"] is True
    assert status["deps_lock_matches"] is True


def test_install_runtime_bootstraps_via_uv_when_no_system_python(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = pointer_dir(tmp_path)
    managed_py = runtime_dir / "python" / "cpython-3.12" / ("python.exe" if os.name == "nt" else "bin/python3")
    managed_py.parent.mkdir(parents=True, exist_ok=True)
    managed_py.write_bytes(b"uv-py")

    monkeypatch.setattr(runtime_installer, "discover_base_python", lambda *a, **kw: None)
    monkeypatch.setattr(runtime_installer, "discover_uv", lambda *a, **kw: None)
    monkeypatch.setattr(runtime_installer, "ensure_uv", lambda *a, **kw: "uv-test")
    monkeypatch.setattr(runtime_installer, "bootstrap_uv_python", lambda *a, **kw: str(managed_py))

    def fake_uv_venv(uv_exe: str, candidate_dir: Path, *, python=None, runtime_dir: Path, run_fn=None):
        py = candidate_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_bytes(b"venv-py")
        return subprocess.CompletedProcess([uv_exe], 0, "", "")

    uv_specs: list[str] = []
    monkeypatch.setattr(runtime_installer, "uv_create_venv", fake_uv_venv)
    monkeypatch.setattr(
        runtime_installer,
        "uv_pip_install",
        lambda uv_exe, py, spec, *, runtime_dir, no_deps=False, run_fn=None: uv_specs.append(spec)
        or subprocess.CompletedProcess([uv_exe], 0, "", ""),
    )
    monkeypatch.setattr(runtime_installer, "_fresh_verify", lambda py, *, cwd=None: (True, "2.1.0", None))
    monkeypatch.setattr(runtime_installer, "_vector_imports_ok", lambda py, *, cwd=None: True)

    res = runtime_installer.install_runtime(expected_version="2.1.0", home=tmp_path)
    assert res.ok is True
    assert uv_specs == ["paperforge[vector]==2.1.0"]
    ptr = read_pointer(home=tmp_path)
    assert ptr is not None
    assert ptr.get("installer_backend") == "uv"
    assert ptr.get("python_source") == "uv_managed"


def test_pip_mirror_fallback_enforces_tls_no_trusted_host(tmp_path: Path, monkeypatch) -> None:
    recorded_cmds: list[list[str]] = []

    def _fake_run(cmd, *, cwd, timeout):
        recorded_cmds.append(list(cmd))
        return subprocess.CompletedProcess(list(cmd), 1, "", "err")

    monkeypatch.setattr(runtime_installer, "_run", _fake_run)
    monkeypatch.delenv("PIP_INDEX_URL", raising=False)
    monkeypatch.delenv("PIP_FIND_LINKS", raising=False)
    runtime_installer._pip_install_command(tmp_path / "python", "paperforge==2.0.7", cwd=tmp_path)
    assert len(recorded_cmds) >= 2
    assert all("--trusted-host" not in cmd for cmd in recorded_cmds)

