"""Two-process concurrency test for shared Rust + Python paperforge.json.lock."""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit

DAEMON_EXE = (
    Path(__file__).resolve().parents[2]
    / "crates"
    / "paperforge-daemon"
    / "target"
    / "release"
    / "paperforge-daemon.exe"
)


def test_rust_and_python_concurrent_config_set_preserve_updates(tmp_path: Path) -> None:
    """PF-ARCH-013: Rust NativeControlDaemon and Python CLI share paperforge.json.lock cleanly."""
    if not DAEMON_EXE.exists():
        pytest.skip("paperforge-daemon.exe release binary not built")

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    def _run_rust(val: str) -> tuple[int, str, str]:
        req = (
            json.dumps(
                {
                    "id": 1,
                    "op": "cli.run",
                    "vault": str(vault),
                    "argv": ["config", "set", "ocr_profile", val, "--json"],
                }
            )
            + "\n"
            + json.dumps({"id": 2, "op": "shutdown"})
            + "\n"
        )
        p = subprocess.run(
            [str(DAEMON_EXE), "--stdio", "--idle-timeout", "10"],
            input=req,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return p.returncode, p.stdout, p.stderr

    def _run_python(val: str) -> tuple[int, str, str]:
        p = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(vault), "config", "set", "embedding_profile", val, "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return p.returncode, p.stdout, p.stderr

    for i in range(15):
        rust_val = f"rust_p{i}"
        py_val = f"py_p{i}"
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_rust = pool.submit(_run_rust, rust_val)
            f_py = pool.submit(_run_python, py_val)
            r_rc, r_out, r_err = f_rust.result()
            p_rc, p_out, p_err = f_py.result()

        assert r_rc == 0, f"round {i} rust failed: {r_out} {r_err}"
        first_line = json.loads(r_out.splitlines()[0])
        assert first_line.get("exit_code") == 0, f"round {i} rust rpc failed: {first_line}"
        inner = json.loads(first_line["stdout"])
        assert inner.get("ok") is True, f"round {i} rust config.set failed: {inner}"
        assert p_rc == 0, f"round {i} python failed: {p_out} {p_err}"
        cfg = json.loads((vault / "paperforge.json").read_text(encoding="utf-8"))
        assert cfg["ocr_profile"] == rust_val, f"round {i} lost Rust update: {cfg}"
        assert cfg["embedding_profile"] == py_val, f"round {i} lost Python update: {cfg}"
