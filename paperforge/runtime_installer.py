"""Independent installer for the machine-wide PaperForge Python runtime.

Obsidian reads the published pointer and connects to this runtime. It never
creates environments or installs Python packages. A candidate environment is
published only after a fresh-process version and dependency check succeeds.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge import __version__
from paperforge.runtime_pointer import pointer_dir, pointer_path, publish_pointer, read_pointer

MIN_PYTHON = (3, 11)
# The `vector` extra installs exactly these; `chromadb` is the opt-in
# `legacy-vector` extra and must never be required of a managed runtime
# (the same split as paperforge.setup.runtime.VECTOR_CAPABILITY_IMPORTS).
_VECTOR_IMPORTS = ("openai", "sqlite_vec")
_PYTHON_VERSION_RE = re.compile(r"Python\s+(\d+)\.(\d+)(?:\.(\d+))?")


class RuntimeInstallError(Exception):
    def __init__(self, code: str, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    def to_dict(self) -> dict[str, Any]:
        return {"ok": False, "code": self.code, "error": self.message, "detail": self.detail}


@dataclass(frozen=True)
class RuntimeInstallResult:
    ok: bool
    code: str
    message: str
    python_path: str = ""
    environment_root: str = ""
    paperforge_version: str = ""
    base_python: str = ""
    actions_taken: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "code": self.code,
            "message": self.message,
            "python_path": self.python_path,
            "environment_root": self.environment_root,
            "paperforge_version": self.paperforge_version,
            "base_python": self.base_python,
            "actions_taken": list(self.actions_taken),
        }


def parse_python_version(output: str) -> tuple[int, ...] | None:
    match = _PYTHON_VERSION_RE.search(output)
    if not match:
        return None
    return tuple(int(part) for part in match.groups() if part is not None)


def _run(
    command: list[str], *, cwd: Path, timeout: int = 300
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def _probe_version(python: str, *, cwd: Path) -> tuple[int, ...] | None:
    try:
        result = _run([python, "--version"], cwd=cwd, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return parse_python_version((result.stdout or "") + (result.stderr or ""))


def _is_minimum_python(python: str, *, cwd: Path) -> bool:
    version = _probe_version(python, cwd=cwd)
    return version is not None and version >= MIN_PYTHON


def _managed_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _pip_install(
    venv_python: Path, spec: str, *, cwd: Path
) -> subprocess.CompletedProcess[str]:
    return _run([str(venv_python), "-m", "pip", "install", spec], cwd=cwd, timeout=1800)


def _fresh_verify(python: str, *, cwd: Path) -> tuple[bool, str | None, str | None]:
    try:
        result = _run(
            [python, "-I", "-c", "import paperforge; print(paperforge.__version__)"],
            cwd=cwd,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, None, str(exc)
    version = (result.stdout or "").strip()
    if result.returncode != 0:
        return False, version or None, (result.stderr or "").strip()[-300:]
    return True, version, None


def _vector_imports_ok(python: str, *, cwd: Path) -> bool:
    probe = "import " + ", ".join(_VECTOR_IMPORTS)
    try:
        result = _run([python, "-I", "-c", probe], cwd=cwd, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _base_interpreter_candidates(preferred: str | None) -> list[str]:
    candidates = [preferred] if preferred else []
    candidates.append(sys.executable)
    candidates.extend(["py", "python"] if os.name == "nt" else ["python3", "python"])
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        key = candidate.lower() if os.name == "nt" else candidate
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def discover_base_python(preferred: str | None = None, *, cwd: Path | None = None) -> str | None:
    probe_cwd = cwd or Path.home()
    for candidate in _base_interpreter_candidates(preferred):
        if _is_minimum_python(candidate, cwd=probe_cwd):
            return candidate
    return None


def _runtime_cwd(home: Path | None = None) -> Path:
    runtime_dir = pointer_dir(home)
    return runtime_dir if runtime_dir.is_dir() else Path.home()


def inspect_runtime(
    *,
    home: Path | None = None,
    expected_version: str = __version__,
    base_python: str | None = None,
) -> dict[str, Any]:
    """Inspect the active pointer and its target without modifying either."""
    runtime_dir = pointer_dir(home)
    cwd = _runtime_cwd(home)
    pointer = read_pointer(home)
    python_path = pointer.get("python_path") if pointer else None
    python_exists = bool(python_path and Path(python_path).is_file())
    observed: str | None = None
    version_match = False
    vector_ready = False
    pointer_version = pointer.get("paperforge_version") if pointer else None
    if python_exists and isinstance(python_path, str):
        ok, observed, _detail = _fresh_verify(python_path, cwd=cwd)
        version_match = bool(
            ok and observed == expected_version and pointer_version == expected_version
        )
        vector_ready = _vector_imports_ok(python_path, cwd=cwd) if ok else False

    ready = bool(pointer and python_exists and version_match and vector_ready)
    return {
        "runtime_dir": str(runtime_dir),
        "pointer_path": str(pointer_path(home)),
        "pointer": pointer,
        "pointer_version": pointer_version,
        "python_path": python_path,
        "python_exists": python_exists,
        "paperforge_version": observed,
        "version_matches_expected": version_match,
        "vector_ready": vector_ready,
        "system_python": discover_base_python(base_python, cwd=cwd),
        "runtime_ready": ready,
        "runtime_state": "ready" if ready else "attention" if pointer else "missing",
        "installer": "paperforge runtime install --expected-version <version>",
    }


ENV_DIR_PREFIXES = (".venv-candidate-", "venv-")
"""Directory names this installer owns inside the runtime root."""


def _managed_dir(target: Path, runtime_dir: Path) -> Path | None:
    """Resolved *target* when it is an installer-owned environment dir."""
    try:
        root = runtime_dir.resolve()
        resolved = target.resolve()
    except OSError:
        return None
    if root not in resolved.parents:
        return None
    if not resolved.name.startswith(ENV_DIR_PREFIXES):
        return None
    return resolved


def _remove_environment(target: Path, runtime_dir: Path) -> bool:
    """Delete one installer-owned environment; never a silent sweep."""
    resolved = _managed_dir(target, runtime_dir)
    if resolved is None:
        return False
    try:
        shutil.rmtree(resolved)
    except FileNotFoundError:
        return False
    except OSError:
        # Windows keeps handles inside a running venv; leave it for a later run.
        return False
    return True


def _prune_environments(
    runtime_dir: Path, current: Path, keep_previous: int = 1
) -> int:
    """Keep the published environment and the newest previous one.

    Repeated updates otherwise accumulate a full venv (~400 MB) each. A
    directory that cannot be removed (live process, permissions) is left in
    place rather than forced.
    """
    current_resolved = _managed_dir(current, runtime_dir)
    previous: list[tuple[float, Path]] = []
    try:
        entries = list(runtime_dir.iterdir())
    except OSError:
        return 0
    for entry in entries:
        if not entry.is_dir() or not entry.name.startswith(ENV_DIR_PREFIXES):
            continue
        resolved = _managed_dir(entry, runtime_dir)
        if resolved is None or resolved == current_resolved:
            continue
        try:
            previous.append((entry.stat().st_mtime, entry))
        except OSError:
            continue
    previous.sort(reverse=True)
    removed = 0
    for _, stale in previous[keep_previous:]:
        if _remove_environment(stale, runtime_dir):
            removed += 1
    return removed


def _discard_candidate(candidate: Path, runtime_dir: Path) -> None:
    """Remove a failed candidate environment (never a blanket delete)."""
    _remove_environment(candidate, runtime_dir)


def install_runtime(
    *,
    expected_version: str = __version__,
    home: Path | None = None,
    base_python: str | None = None,
    force: bool = False,
    wheel: Path | None = None,
) -> RuntimeInstallResult:
    """Install and verify a candidate runtime, then atomically publish it.

    The active environment is never modified in place. Failed candidates are
    removed; the previously published pointer and environment remain usable.
    """
    runtime_dir = pointer_dir(home)
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeInstallError(
            "runtime.directory_failed",
            "Cannot create the managed PaperForge runtime directory.",
            str(exc),
        ) from exc

    if wheel is not None:
        wheel = wheel.expanduser().resolve()
        if wheel.suffix.lower() != ".whl" or not wheel.is_file():
            raise RuntimeInstallError(
                "runtime.wheel_invalid", "The supplied wheel must be an existing .whl file.", str(wheel)
            )
        force = True

    base_python = discover_base_python(base_python, cwd=runtime_dir)
    if not base_python:
        raise RuntimeInstallError(
            "runtime.no_python",
            "No Python 3.11+ found. Install Python, then run the PaperForge runtime installer again.",
        )
    if not _is_minimum_python(base_python, cwd=runtime_dir):
        raise RuntimeInstallError(
            "runtime.python_too_old", "The selected Python interpreter is older than 3.11.", base_python
        )

    if not force and wheel is None:
        current = inspect_runtime(
            home=home, expected_version=expected_version, base_python=base_python
        )
        if current["runtime_ready"]:
            pointer = current["pointer"]
            return RuntimeInstallResult(
                ok=True,
                code="runtime.ready",
                message="PaperForge runtime is already installed and verified.",
                python_path=str(current["python_path"]),
                environment_root=str(pointer["environment_root"]),
                paperforge_version=str(current["paperforge_version"]),
                base_python=base_python,
                actions_taken=["already_ready"],
            )

    candidate = runtime_dir / f".venv-candidate-{uuid.uuid4().hex}"
    candidate_python = _managed_python(candidate)
    installed = False
    try:
        created = _run([base_python, "-m", "venv", str(candidate)], cwd=runtime_dir, timeout=180)
        if created.returncode != 0 or not candidate_python.is_file():
            raise RuntimeInstallError(
                "runtime.venv_failed",
                "Failed to create the PaperForge candidate environment.",
                (created.stderr or created.stdout or "")[-500:],
            )

        spec = f"{wheel}[vector]" if wheel else f"paperforge[vector]=={expected_version}"
        try:
            pip = _pip_install(candidate_python, spec, cwd=runtime_dir)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeInstallError(
                "runtime.pip_failed",
                "Failed to run pip in the candidate runtime.",
                str(exc),
            ) from exc
        if pip.returncode != 0:
            raise RuntimeInstallError(
                "runtime.pip_failed",
                "Failed to install PaperForge into the candidate runtime.",
                (pip.stderr or pip.stdout or "")[-800:],
            )

        verified, observed, detail = _fresh_verify(str(candidate_python), cwd=runtime_dir)
        if not verified or observed is None or observed != expected_version:
            raise RuntimeInstallError(
                "runtime.verify_failed",
                "The candidate runtime did not report the expected PaperForge version.",
                f"observed={observed!r} expected={expected_version!r} {detail or ''}".strip(),
            )
        if not _vector_imports_ok(str(candidate_python), cwd=runtime_dir):
            raise RuntimeInstallError(
                "runtime.vector_missing",
                "The PaperForge vector dependencies are not importable in the candidate runtime.",
                ",".join(_VECTOR_IMPORTS),
            )

        publish_pointer(
            python_path=str(candidate_python.resolve()),
            environment_root=str(candidate.resolve()),
            paperforge_version=observed,
            home=home,
        )
        installed = True
        actions = [
            "candidate_created",
            "paperforge_installed",
            "runtime_verified",
            "pointer_published",
        ]
        pruned = _prune_environments(runtime_dir, candidate)
        if pruned:
            actions.append(f"environments_pruned:{pruned}")
        return RuntimeInstallResult(
            ok=True,
            code="runtime.ready",
            message="PaperForge runtime installed and verified.",
            python_path=str(candidate_python.resolve()),
            environment_root=str(candidate.resolve()),
            paperforge_version=observed,
            base_python=base_python,
            actions_taken=actions,
        )
    except RuntimeInstallError:
        raise
    except OSError as exc:
        raise RuntimeInstallError("runtime.install_failed", "Runtime installation failed.", str(exc)) from exc
    finally:
        if not installed:
            _discard_candidate(candidate, runtime_dir)
