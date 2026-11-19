"""Independent installer for the machine-wide PaperForge Python runtime.

Obsidian reads the published pointer and connects to this runtime. It never
creates environments or installs Python packages. A candidate environment is
published only after a fresh-process version and dependency check succeeds.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge import __version__
from paperforge.core.versioning import (
    MIN_COMPATIBLE_PLUGIN_VERSION,
    compute_deps_lock_hash,
    is_version_compatible,
    normalize_release_version,
)
from paperforge.runtime_pointer import pointer_dir, pointer_path, publish_pointer, read_pointer
from paperforge.runtime_uv import (
    bootstrap_uv_python,
    discover_uv,
    ensure_uv,
    uv_create_venv,
    uv_pip_install,
)

MIN_PYTHON = (3, 11)
# The `vector` extra installs exactly these; `chromadb` is the opt-in
# `legacy-vector` extra and must never be required of a managed runtime
# (the same split as paperforge.setup.runtime.VECTOR_CAPABILITY_IMPORTS).
_VECTOR_IMPORTS = ("openai", "sqlite_vec")
_PYTHON_VERSION_RE = re.compile(r"Python\s+(\d+)\.(\d+)(?:\.(\d+))?")
_normalize_release_version = normalize_release_version


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


LOCK_NAME = "install.lock"
#: A lock older than this is a crashed run (pids are not portable), not a live
#: installer; a candidate build never takes that long on a working network.
LOCK_STALE_SECONDS = 3600


@contextlib.contextmanager
def install_lock(runtime_dir: Path) -> Iterator[Path]:
    """Hold the machine-wide install lock for the duration of the block.

    The plugin can be clicked twice, or two Obsidian windows can race; a second
    installer would build a second candidate and prune the first one's result.
    """
    path = runtime_dir / LOCK_NAME
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            age = 0.0
        if age < LOCK_STALE_SECONDS:
            raise RuntimeInstallError(
                "runtime.install_in_progress",
                "Another PaperForge runtime install is already running.",
                f"lock: {path}",
            ) from None
        try:
            path.unlink()
        except OSError as exc:
            raise RuntimeInstallError(
                "runtime.install_locked",
                "A stale runtime install lock could not be cleared.",
                f"{path}: {exc}",
            ) from exc
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, f"{os.getpid()} {int(time.time())}\n".encode())
        os.close(fd)
        yield path
    finally:
        with contextlib.suppress(OSError):
            path.unlink()


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


_FALLBACK_PYPI_INDEX = "https://pypi.tuna.tsinghua.edu.cn/simple"
_FALLBACK_PYPI_HOST = "pypi.tuna.tsinghua.edu.cn"
_ALIYUN_PYPI_INDEX = "https://mirrors.aliyun.com/pypi/simple"
_ALIYUN_PYPI_HOST = "mirrors.aliyun.com"
_MIRROR_FALLBACKS = (
    (_FALLBACK_PYPI_INDEX, _FALLBACK_PYPI_HOST),
    (_ALIYUN_PYPI_INDEX, _ALIYUN_PYPI_HOST),
)


def _pip_install_command(
    venv_python: Path, spec: str, *, cwd: Path, no_deps: bool = False
) -> subprocess.CompletedProcess[str]:
    base = [str(venv_python), "-m", "pip", "install", "--default-timeout=60"]
    if no_deps:
        base.append("--no-deps")
    result = _run([*base, spec], cwd=cwd, timeout=1800)
    if (
        result.returncode != 0
        and not os.environ.get("PIP_INDEX_URL")
        and not os.environ.get("PIP_FIND_LINKS")
        and not spec.lower().endswith(".whl")
    ):
        last_mirror: subprocess.CompletedProcess[str] = result
        for index_url, trusted_host in _MIRROR_FALLBACKS:
            mirror_result = _run(
                [*base, "-i", index_url, "--trusted-host", trusted_host, spec],
                cwd=cwd,
                timeout=1800,
            )
            if mirror_result.returncode == 0:
                return mirror_result
            if mirror_result.stderr or mirror_result.stdout:
                last_mirror = mirror_result
        return last_mirror
    return result


def _pip_install(
    venv_python: Path, spec: str, *, cwd: Path
) -> subprocess.CompletedProcess[str]:
    return _pip_install_command(venv_python, spec, cwd=cwd, no_deps=False)


def _pip_install_no_deps(
    venv_python: Path, spec: str, *, cwd: Path
) -> subprocess.CompletedProcess[str]:
    return _pip_install_command(venv_python, spec, cwd=cwd, no_deps=True)


def _site_packages_dir(env_root: Path) -> Path | None:
    if os.name == "nt":
        sp = env_root / "Lib" / "site-packages"
        return sp if sp.is_dir() else None
    lib_dir = env_root / "lib"
    if not lib_dir.is_dir():
        return None
    for child in sorted(lib_dir.iterdir()):
        if child.is_dir() and child.name.startswith("python"):
            sp = child / "site-packages"
            if sp.is_dir():
                return sp
    return None


def _copy_or_hardlink(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _clone_site_packages_for_fast_patch(old_root: Path, new_root: Path) -> bool:
    """Hardlink/copy third-party packages from *old_root* into *new_root*, omitting old paperforge."""
    old_sp = _site_packages_dir(old_root)
    new_sp = _site_packages_dir(new_root)
    if old_sp is None or new_sp is None:
        return False
    entries = list(old_sp.iterdir())
    if len(entries) < 2:
        return False
    for entry in entries:
        lower = entry.name.lower()
        if lower == "paperforge" or lower.startswith("paperforge-") or lower.startswith("paperforge."):
            continue
        if lower in {"__pycache__", ".lock"}:
            continue
        target = new_sp / entry.name
        if target.exists():
            continue
        try:
            if entry.is_dir():
                shutil.copytree(entry, target, copy_function=_copy_or_hardlink)
            else:
                _copy_or_hardlink(str(entry), str(target))
        except OSError:
            return False
    return True


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
    min_engine_version: str | None = None,
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
    compat_reason = "runtime_missing"
    vector_ready = False
    pointer_version = pointer.get("paperforge_version") if pointer else None
    target_deps_hash = compute_deps_lock_hash()
    pointer_deps_hash = str(pointer.get("deps_lock_hash") or "") if pointer else ""
    if python_exists and isinstance(python_path, str):
        ok, observed, _detail = _fresh_verify(python_path, cwd=cwd)
        if ok and observed is not None:
            core_ok, core_reason = is_version_compatible(
                core_version=observed,
                expected_version=expected_version,
                min_engine_version=min_engine_version,
                plugin_version=expected_version,
                min_plugin_version=MIN_COMPATIBLE_PLUGIN_VERSION,
            )
            ptr_ok, ptr_reason = is_version_compatible(
                core_version=str(pointer_version or ""),
                expected_version=expected_version,
                min_engine_version=min_engine_version,
                plugin_version=expected_version,
                min_plugin_version=MIN_COMPATIBLE_PLUGIN_VERSION,
            )
            version_match = bool(core_ok and ptr_ok)
            compat_reason = "ok" if version_match else (core_reason if not core_ok else ptr_reason)
        else:
            compat_reason = "verify_failed"
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
        "compatible": version_match,
        "compat_reason": compat_reason,
        "min_engine_version": min_engine_version,
        "deps_lock_hash": target_deps_hash,
        "deps_lock_matches": bool(
            target_deps_hash and pointer_deps_hash and pointer_deps_hash == target_deps_hash
        ),
        "vector_ready": vector_ready,
        "system_python": discover_base_python(base_python, cwd=cwd),
        "uv_path": discover_uv(runtime_dir),
        "runtime_ready": ready,
        "runtime_state": "ready" if ready else "attention" if pointer else "missing",
        "installer": "paperforge runtime install --expected-version <version>",
    }


#: Only directories this installer created may be pruned. A bare `venv-*`
#: prefix used to be included; those belong to the old TypeScript bootstrap and
#: to users, and deleting them removed environments nobody asked us to touch.
ENV_DIR_PREFIXES = (".venv-candidate-",)
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
    min_engine_version: str | None = None,
    home: Path | None = None,
    base_python: str | None = None,
    force: bool = False,
    wheel: Path | None = None,
    allow_uv: bool = True,
) -> RuntimeInstallResult:
    """Install under the machine-wide lock.

    Two clicks (or two Obsidian windows) must not build competing candidates:
    the loser would prune the winner's environment.
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
    with install_lock(runtime_dir):
        return _install_runtime_locked(
            expected_version=expected_version,
            min_engine_version=min_engine_version,
            home=home,
            base_python=base_python,
            force=force,
            wheel=wheel,
            allow_uv=allow_uv,
        )


def _install_runtime_locked(
    *,
    expected_version: str = __version__,
    min_engine_version: str | None = None,
    home: Path | None = None,
    base_python: str | None = None,
    force: bool = False,
    wheel: Path | None = None,
    allow_uv: bool = True,
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

    uv_exe = discover_uv(runtime_dir) if allow_uv else None
    python_source = "system"
    installer_backend = "pip"

    base_python_resolved = discover_base_python(base_python, cwd=runtime_dir)
    if not base_python_resolved and allow_uv:
        uv_exe = uv_exe or ensure_uv(runtime_dir, allow_download=True)
        if uv_exe:
            managed_py = bootstrap_uv_python(uv_exe, runtime_dir, python_spec="3.12")
            if managed_py:
                base_python_resolved = managed_py
                python_source = "uv_managed"
                installer_backend = "uv"

    if not base_python_resolved:
        raise RuntimeInstallError(
            "runtime.no_python",
            "No Python 3.11+ found. Install Python, then run the PaperForge runtime installer again.",
        )
    if python_source == "system" and not _is_minimum_python(base_python_resolved, cwd=runtime_dir):
        raise RuntimeInstallError(
            "runtime.python_too_old", "The selected Python interpreter is older than 3.11.", base_python_resolved
        )

    if not force and wheel is None:
        current = inspect_runtime(
            home=home,
            expected_version=expected_version,
            min_engine_version=min_engine_version,
            base_python=base_python_resolved,
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
                base_python=base_python_resolved,
                actions_taken=["already_ready"],
            )

    target_deps_hash = compute_deps_lock_hash()
    old_pointer = read_pointer(home)
    old_root = (
        Path(str(old_pointer["environment_root"]))
        if old_pointer and old_pointer.get("environment_root")
        else None
    )
    can_fast_patch = bool(
        not force
        and wheel is None
        and target_deps_hash
        and old_pointer
        and old_pointer.get("deps_lock_hash") == target_deps_hash
        and old_root is not None
        and old_root.is_dir()
    )

    candidate = runtime_dir / f".venv-candidate-{uuid.uuid4().hex}"
    candidate_python = _managed_python(candidate)
    installed = False
    actions = [
        "candidate_created",
        "paperforge_installed",
        "runtime_verified",
        "pointer_published",
    ]
    try:
        if installer_backend == "uv" and uv_exe:
            created = uv_create_venv(uv_exe, candidate, python=base_python_resolved, runtime_dir=runtime_dir)
        else:
            created = _run([base_python_resolved, "-m", "venv", str(candidate)], cwd=runtime_dir, timeout=180)
        if created.returncode != 0 or not candidate_python.is_file():
            raise RuntimeInstallError(
                "runtime.venv_failed",
                "Failed to create the PaperForge candidate environment.",
                (created.stderr or created.stdout or "")[-500:],
            )

        norm_ver = _normalize_release_version(expected_version)
        full_spec = f"{wheel}[vector]" if wheel else f"paperforge[vector]=={norm_ver}"
        fast_patched = False

        if can_fast_patch and old_root is not None and _clone_site_packages_for_fast_patch(old_root, candidate):
            patch_spec = f"paperforge=={norm_ver}"
            if installer_backend == "uv" and uv_exe:
                patch_res = uv_pip_install(
                    uv_exe, candidate_python, patch_spec, runtime_dir=runtime_dir, no_deps=True
                )
            else:
                patch_res = _pip_install_no_deps(candidate_python, patch_spec, cwd=runtime_dir)
            if patch_res.returncode == 0:
                v_ok, obs_ver, _ = _fresh_verify(str(candidate_python), cwd=runtime_dir)
                if (
                    v_ok
                    and obs_ver is not None
                    and _normalize_release_version(obs_ver) == norm_ver
                    and _vector_imports_ok(str(candidate_python), cwd=runtime_dir)
                ):
                    fast_patched = True
                    actions.insert(1, "fast_patch_deps_reused")
            if not fast_patched:
                # Re-create pristine candidate cleanly before falling back to full install.
                _discard_candidate(candidate, runtime_dir)
                if installer_backend == "uv" and uv_exe:
                    created = uv_create_venv(
                        uv_exe, candidate, python=base_python_resolved, runtime_dir=runtime_dir
                    )
                else:
                    created = _run(
                        [base_python_resolved, "-m", "venv", str(candidate)], cwd=runtime_dir, timeout=180
                    )
                if created.returncode != 0 or not candidate_python.is_file():
                    raise RuntimeInstallError(
                        "runtime.venv_failed",
                        "Failed to create the PaperForge candidate environment.",
                        (created.stderr or created.stdout or "")[-500:],
                    )

        if not fast_patched:
            try:
                if installer_backend == "uv" and uv_exe:
                    pip = uv_pip_install(uv_exe, candidate_python, full_spec, runtime_dir=runtime_dir)
                else:
                    pip = _pip_install(candidate_python, full_spec, cwd=runtime_dir)
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
        if (
            not verified
            or observed is None
            or _normalize_release_version(observed) != norm_ver
        ):
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
            deps_lock_hash=target_deps_hash or None,
            installer_backend=installer_backend,
            python_source=python_source,
            home=home,
        )
        installed = True
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
            base_python=base_python_resolved,
            actions_taken=actions,
        )
    except RuntimeInstallError:
        raise
    except OSError as exc:
        raise RuntimeInstallError("runtime.install_failed", "Runtime installation failed.", str(exc)) from exc
    finally:
        if not installed:
            _discard_candidate(candidate, runtime_dir)
