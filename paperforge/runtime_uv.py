"""Portable ``uv`` bootstrap, hardlink cache, and standalone Python management.

Keeps ``uv``, managed Python interpreters, the global hardlink wheel/package
cache, and candidate virtual environments strictly under ``runtime_dir`` on the
same filesystem volume so NTFS/APFS/ext4 hardlinks succeed without copying.
"""

from __future__ import annotations

import io
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

UV_RELEASE_BASE = "https://github.com/astral-sh/uv/releases/latest/download"
UV_MIRROR_RELEASE_BASES = (
    "https://ghfast.top/https://github.com/astral-sh/uv/releases/latest/download",
)
UV_PYTHON_MIRROR_DEFAULT = "https://registry.npmmirror.com/-/binary/python-build-standalone"
UV_PYPI_INDEXES = (
    None,  # official PyPI (or env UV_INDEX_URL / PIP_INDEX_URL)
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
)


def uv_bin_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "bin"


def uv_cache_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "cache" / "uv"


def uv_python_dir(runtime_dir: Path) -> Path:
    return runtime_dir / "python"


def managed_uv_path(runtime_dir: Path) -> Path:
    exe = "uv.exe" if os.name == "nt" else "uv"
    return uv_bin_dir(runtime_dir) / exe


def uv_asset_name(
    *, system: str | None = None, machine: str | None = None
) -> tuple[str, str]:
    """Return ``(archive_filename, archive_kind)`` for the host platform."""
    sys_name = (system or platform.system()).lower()
    arch_raw = (machine or platform.machine()).lower()
    if arch_raw in {"amd64", "x86_64", "x64"}:
        arch = "x86_64"
    elif arch_raw in {"arm64", "aarch64"}:
        arch = "aarch64"
    else:
        raise RuntimeError(f"Unsupported architecture for portable uv: {arch_raw!r}")

    if sys_name == "windows":
        return f"uv-{arch}-pc-windows-msvc.zip", "zip"
    if sys_name == "darwin":
        return f"uv-{arch}-apple-darwin.tar.gz", "tar.gz"
    if sys_name == "linux":
        return f"uv-{arch}-unknown-linux-gnu.tar.gz", "tar.gz"
    raise RuntimeError(f"Unsupported OS for portable uv: {sys_name!r}")


def uv_download_urls(
    *, system: str | None = None, machine: str | None = None
) -> list[str]:
    override = os.environ.get("PAPERFORGE_UV_DOWNLOAD_URL", "").strip()
    if override:
        return [override]
    asset, _ = uv_asset_name(system=system, machine=machine)
    urls = [f"{UV_RELEASE_BASE}/{asset}"]
    for base in UV_MIRROR_RELEASE_BASES:
        urls.append(f"{base.rstrip('/')}/{asset}")
    return urls


def discover_uv(runtime_dir: Path) -> str | None:
    """Return managed ``uv`` executable path, or system ``uv`` on PATH."""
    managed = managed_uv_path(runtime_dir)
    if managed.is_file():
        return str(managed)
    on_path = shutil.which("uv")
    return on_path


def uv_env(runtime_dir: Path, *, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build sanitized subprocess env pinning uv cache & python dirs on the same volume."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["UV_CACHE_DIR"] = str(uv_cache_dir(runtime_dir))
    env["UV_PYTHON_INSTALL_DIR"] = str(uv_python_dir(runtime_dir))
    env.setdefault("UV_LINK_MODE", "hardlink")
    if extra:
        env.update(extra)
    return env


def _safe_extract_uv_binary(raw_bytes: bytes, kind: str, target_exe: Path) -> None:
    """Extract only the ``uv`` / ``uv.exe`` binary safely (no path traversal)."""
    target_name = target_exe.name.lower()
    target_exe.parent.mkdir(parents=True, exist_ok=True)
    tmp_exe = target_exe.with_suffix(target_exe.suffix + ".tmp")

    data: bytes | None = None
    if kind == "zip":
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                if Path(member.filename).name.lower() == target_name:
                    data = zf.read(member.filename)
                    break
    elif kind == "tar.gz":
        with tarfile.open(fileobj=io.BytesIO(raw_bytes), mode="r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                if Path(member.name).name.lower() == target_name:
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        data = extracted.read()
                    break
    else:
        raise ValueError(f"Unsupported archive kind: {kind!r}")

    if not data:
        raise RuntimeError(f"Archive did not contain {target_exe.name}")
    tmp_exe.write_bytes(data)
    if os.name != "nt":
        tmp_exe.chmod(0o755)
    os.replace(str(tmp_exe), str(target_exe))


def ensure_uv(runtime_dir: Path, *, allow_download: bool = True, timeout: int = 45) -> str | None:
    """Locate ``uv``, or download portable ``uv`` into ``runtime_dir/bin``."""
    existing = discover_uv(runtime_dir)
    if existing:
        return existing
    if not allow_download:
        return None
    try:
        _, kind = uv_asset_name()
        urls = uv_download_urls()
    except RuntimeError:
        return None

    target = managed_uv_path(runtime_dir)
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PaperForge-Installer/2.1"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_bytes = resp.read()
            _safe_extract_uv_binary(raw_bytes, kind, target)
            return str(target)
        except Exception:  # noqa: BLE001 — fall through to next mirror or None
            continue
    return None


def _run_uv(
    command: list[str], *, runtime_dir: Path, timeout: int = 1800, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = uv_env(runtime_dir, extra=extra_env)
    return subprocess.run(
        command,
        cwd=str(runtime_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def bootstrap_uv_python(
    uv_exe: str,
    runtime_dir: Path,
    *,
    python_spec: str = "3.12",
    run_fn=None,
) -> str | None:
    """Install standalone managed Python via ``uv`` and return its interpreter path."""
    runner = run_fn or _run_uv
    uv_python_dir(runtime_dir).mkdir(parents=True, exist_ok=True)
    res = runner([uv_exe, "python", "install", python_spec], runtime_dir=runtime_dir, timeout=600)
    if res.returncode != 0 and not os.environ.get("UV_PYTHON_INSTALL_MIRROR"):
        mirror = os.environ.get("PAPERFORGE_UV_PYTHON_MIRROR", UV_PYTHON_MIRROR_DEFAULT)
        res = runner(
            [uv_exe, "python", "install", python_spec],
            runtime_dir=runtime_dir,
            timeout=600,
            extra_env={"UV_PYTHON_INSTALL_MIRROR": mirror},
        )
    if res.returncode != 0:
        return None
    found = runner([uv_exe, "python", "find", python_spec], runtime_dir=runtime_dir, timeout=60)
    if found.returncode != 0:
        return None
    exe = (found.stdout or "").strip().splitlines()[0].strip()
    return exe or None


def uv_create_venv(
    uv_exe: str,
    candidate_dir: Path,
    *,
    python: str | None = None,
    runtime_dir: Path,
    run_fn=None,
) -> subprocess.CompletedProcess[str]:
    runner = run_fn or _run_uv
    cmd = [uv_exe, "venv", "--clear"]
    if python:
        cmd.extend(["--python", python])
    cmd.append(str(candidate_dir))
    return runner(cmd, runtime_dir=runtime_dir, timeout=180)


def uv_pip_install(
    uv_exe: str,
    candidate_python: Path,
    spec: str,
    *,
    runtime_dir: Path,
    no_deps: bool = False,
    run_fn=None,
) -> subprocess.CompletedProcess[str]:
    """Install *spec* into *candidate_python* with hardlink cache & CN mirror fallback."""
    runner = run_fn or _run_uv
    uv_cache_dir(runtime_dir).mkdir(parents=True, exist_ok=True)
    base_cmd = [uv_exe, "pip", "install", "--python", str(candidate_python)]
    if no_deps:
        base_cmd.append("--no-deps")

    if os.environ.get("PIP_INDEX_URL") or os.environ.get("PIP_FIND_LINKS") or spec.lower().endswith(".whl"):
        return runner([*base_cmd, spec], runtime_dir=runtime_dir, timeout=1800)

    last_res: subprocess.CompletedProcess[str] | None = None
    for index_url in UV_PYPI_INDEXES:
        cmd = [*base_cmd]
        if index_url:
            cmd.extend(["--index-url", index_url])
        cmd.append(spec)
        res = runner(cmd, runtime_dir=runtime_dir, timeout=1800)
        if res.returncode == 0:
            return res
        last_res = res
    assert last_res is not None
    return last_res
