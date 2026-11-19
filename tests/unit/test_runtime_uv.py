"""Unit tests for portable uv discovery, archive extraction safety, and mirror layout."""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from paperforge import runtime_uv


def test_uv_asset_name_and_env_layout(tmp_path: Path, monkeypatch) -> None:
    assert runtime_uv.uv_asset_name(system="Windows", machine="AMD64") == (
        "uv-x86_64-pc-windows-msvc.zip",
        "zip",
    )
    assert runtime_uv.uv_asset_name(system="Darwin", machine="arm64") == (
        "uv-aarch64-apple-darwin.tar.gz",
        "tar.gz",
    )
    assert runtime_uv.uv_asset_name(system="Linux", machine="x86_64") == (
        "uv-x86_64-unknown-linux-gnu.tar.gz",
        "tar.gz",
    )

    monkeypatch.setenv("PYTHONPATH", "/bad/global/lib")
    monkeypatch.setenv("PYTHONHOME", "/bad/home")
    env = runtime_uv.uv_env(tmp_path)
    assert "PYTHONPATH" not in env
    assert "PYTHONHOME" not in env
    assert Path(env["UV_CACHE_DIR"]) == runtime_uv.uv_cache_dir(tmp_path)
    assert Path(env["UV_PYTHON_INSTALL_DIR"]) == runtime_uv.uv_python_dir(tmp_path)
    assert env["UV_LINK_MODE"] == "hardlink"


def test_safe_extract_uv_binary_extracts_exact_executable_from_zip(tmp_path: Path) -> None:
    buf = io.BytesIO()
    target_name = "uv.exe" if os.name == "nt" else "uv"
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil.txt", b"should-never-be-written")
        zf.writestr(f"nested/{target_name}", b"uv-binary-bytes")

    dest = runtime_uv.managed_uv_path(tmp_path)
    runtime_uv._safe_extract_uv_binary(buf.getvalue(), "zip", dest)

    assert dest.read_bytes() == b"uv-binary-bytes"
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path.parent / "evil.txt").exists()
