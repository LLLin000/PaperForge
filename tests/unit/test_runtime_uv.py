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


def test_pinned_uv_checksums_and_fail_closed_verification(tmp_path: Path, monkeypatch) -> None:
    import hashlib

    import pytest

    assert runtime_uv.UV_VERSION == "0.13.9"
    assert len(runtime_uv.UV_ASSET_SHA256) == 6
    for digest in runtime_uv.UV_ASSET_SHA256.values():
        assert len(digest) == 64
        assert digest == digest.lower()

    urls = runtime_uv.uv_download_urls(system="Linux", machine="x86_64")
    assert all("/releases/download/0.13.9/" in u for u in urls)
    assert all("latest" not in u for u in urls)

    # Build a valid small zip archive containing uv / uv.exe
    buf = io.BytesIO()
    exe_name = "uv.exe" if os.name == "nt" else "uv"
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(exe_name, b"trusted-uv-payload")
    good_zip = buf.getvalue()
    good_sha = hashlib.sha256(good_zip).hexdigest()

    # Checksum mismatch raises Fail-Closed without extracting
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        runtime_uv.verify_uv_archive_sha256(b"tampered", "uv-x86_64-pc-windows-msvc.zip")

    # ensure_uv skips poisoned mirror 1 and accepts verified mirror 2
    monkeypatch.setattr(runtime_uv.shutil, "which", lambda _name: None)
    asset_name, _ = runtime_uv.uv_asset_name()
    monkeypatch.setitem(runtime_uv.UV_ASSET_SHA256, asset_name, good_sha)
    if asset_name.endswith(".tar.gz"):
        import tarfile

        tbuf = io.BytesIO()
        with tarfile.open(fileobj=tbuf, mode="w:gz") as tf:
            info = tarfile.TarInfo(name=exe_name)
            data = b"trusted-uv-payload"
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        good_payload = tbuf.getvalue()
        monkeypatch.setitem(
            runtime_uv.UV_ASSET_SHA256, asset_name, hashlib.sha256(good_payload).hexdigest()
        )
    else:
        good_payload = good_zip

    responses = [b"poisoned-binary-payload", good_payload]

    class _Resp:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        runtime_uv.urllib.request,
        "urlopen",
        lambda req, timeout=45: _Resp(responses.pop(0)),
    )
    resolved = runtime_uv.ensure_uv(tmp_path, allow_download=True)
    assert resolved is not None
    assert Path(resolved).read_bytes() == b"trusted-uv-payload"
