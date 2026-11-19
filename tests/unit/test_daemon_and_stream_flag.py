"""Unit tests for `paperforge daemon --stdio` and explicit `--stream` CLI flags."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from paperforge.cli import build_parser
from paperforge.commands import auth as auth_cmd
from paperforge.commands.daemon import serve_stdio
from paperforge.config import bootstrap_config

pytestmark = pytest.mark.unit


def test_daemon_stdio_inprocess_rpc_secrets_and_error_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    bootstrap_config(vault)

    stored: list[tuple[str, str, str, bool]] = []
    monkeypatch.setattr(
        auth_cmd,
        "credential_store",
        lambda key, secret, replace=False: stored.append(
            (key.kind, key.profile, secret, bool(replace))
        ),
    )
    monkeypatch.setattr(
        auth_cmd,
        "credential_status",
        lambda _key: SimpleNamespace(
            state="present",
            source="keyring",
            backend="mock",
            remediation_code=None,
        ),
    )

    requests = "\n".join(
        [
            json.dumps({"id": 1, "op": "ping"}),
            json.dumps({"id": 2, "vault": str(vault), "argv": ["config", "paths", "--json"]}),
            json.dumps(
                {
                    "id": 3,
                    "vault": str(vault),
                    "argv": ["auth", "set", "ocr", "--stdin", "--replace", "--json"],
                    "stdin": "tok_secret_123\n",
                }
            ),
            json.dumps(
                {
                    "id": 4,
                    "vault": str(vault),
                    "argv": ["action", "describe", "no.such.action", "--json"],
                }
            ),
            json.dumps({"id": 5, "vault": str(vault), "argv": ["daemon", "--stdio"]}),
            json.dumps({"id": 6, "op": "shutdown"}),
            json.dumps({"id": 7, "op": "ping"}),  # never reached after shutdown
        ]
    ) + "\n"

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(requests))
    monkeypatch.setattr(sys, "stdout", out_buf)
    monkeypatch.setattr(sys, "stderr", err_buf)

    rc = serve_stdio(idle_timeout=0)
    assert rc == 0

    responses = [json.loads(line) for line in out_buf.getvalue().splitlines() if line.strip()]
    assert [r["id"] for r in responses] == [1, 2, 3, 4, 5, 6]

    assert responses[0]["exit_code"] == 0
    assert responses[0]["stdout"] == "pong"

    assert responses[1]["exit_code"] == 0
    paths_env = json.loads(responses[1]["stdout"])
    assert paths_env["ok"] is True

    assert responses[2]["exit_code"] == 0
    assert stored == [("ocr", "default", "tok_secret_123", True)]
    auth_env = json.loads(responses[2]["stdout"])
    assert auth_env["ok"] is True

    assert responses[3]["exit_code"] == 2
    assert responses[4]["exit_code"] == 2
    assert "Nested daemon" in responses[4]["stderr"]
    assert responses[5]["exit_code"] == 0


def test_daemon_stdio_subprocess_roundtrip(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    bootstrap_config(vault)

    payload = (
        json.dumps({"id": 10, "vault": str(vault), "argv": ["config", "paths", "--json"]})
        + "\n"
        + json.dumps({"id": 11, "vault": str(vault), "argv": ["probe", "installation", "--json"]})
        + "\n"
    )
    proc = subprocess.run(
        [sys.executable, "-m", "paperforge", "daemon", "--stdio", "--idle-timeout", "30"],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(tmp_path),
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr

    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert [line["id"] for line in lines] == [10, 11]
    assert lines[0]["exit_code"] == 0
    assert json.loads(lines[0]["stdout"])["ok"] is True
    assert lines[1]["exit_code"] == 0
    assert json.loads(lines[1]["stdout"])["module"] == "installation"


def test_cli_stream_flag_accepted_across_streaming_commands() -> None:
    parser = build_parser()
    cases = [
        ["ocr", "--stream"],
        ["ocr", "run", "--stream"],
        ["ocr", "redo", "K1", "--stream"],
        ["ocr", "rebuild", "K1", "--stream"],
        ["embed", "build", "--stream", "--json"],
        ["action", "run", "ocr.rebuild_derived", "--scope", "all", "--stream"],
        ["setup", "--stream"],
    ]
    for argv in cases:
        ns = parser.parse_args(argv)
        assert getattr(ns, "stream", False) is True, f"--stream missing for {argv!r}"


def test_daemon_stdio_resets_timing_and_advances_state_seq(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from paperforge.core import timing
    from paperforge.services.state_signal import read_state_seq

    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    bootstrap_config(vault)
    ws = vault / "Resources" / "Literature" / "Ortho" / "DMEM001 - Test"
    ws.mkdir(parents=True)
    indexes = vault / ".paperforge" / "indexes"
    indexes.mkdir(parents=True)
    (indexes / "formal-library.json").write_text(
        json.dumps(
            {
                "version": 1,
                "items": [{"zotero_key": "DMEM001", "paper_root": "Resources/Literature/Ortho/DMEM001 - Test/"}],
            }
        ),
        encoding="utf-8",
    )

    with timing.phase("stale.leak.phase"):
        pass
    assert "stale.leak.phase" in timing.summary()

    requests = "\n".join(
        [
            json.dumps(
                {
                    "id": 1,
                    "vault": str(vault),
                    "argv": ["memory-card", "refine", "DMEM001", "--facet", "idea_logic", "--content", "Via daemon", "--json"],
                }
            ),
            json.dumps({"id": 2, "vault": str(vault), "argv": ["config", "paths", "--json"]}),
            json.dumps({"id": 3, "op": "shutdown"}),
        ]
    ) + "\n"

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(requests))
    monkeypatch.setattr(sys, "stdout", out_buf)
    monkeypatch.setattr(sys, "stderr", err_buf)

    assert serve_stdio(idle_timeout=0) == 0
    responses = [json.loads(line) for line in out_buf.getvalue().splitlines() if line.strip()]
    assert responses[0]["exit_code"] == 0
    assert json.loads(responses[0]["stdout"])["ok"] is True
    assert responses[1]["exit_code"] == 0
    assert "stale.leak.phase" not in timing.summary()

    seq = read_state_seq(vault)
    assert seq["seq"] == 1
    assert seq["reason"] == "memory_card.refine"
    assert seq["changed_keys"] == ["DMEM001"]
