"""#265 P1: the host probe reports vault-path metadata without changing the
user-profile semantics it already had."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "host-probe.ps1"


def probe(tmp_path: Path, *extra: str) -> dict:
    out = tmp_path / "host-profile.json"
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-OutFile",
            str(out),
            *extra,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return json.loads(out.read_text(encoding="utf-8-sig"))


@pytest.mark.skipif(sys.platform != "win32", reason="host probe is Windows-only")
def test_vault_fields_are_null_when_not_measured(tmp_path: Path) -> None:
    payload = probe(tmp_path)
    machine = payload["machine"]
    assert machine["vault_path_measured"] is None
    assert machine["vault_path_len_chars"] is None
    assert machine["vault_path_non_ascii"] is None
    assert machine["vault_path_has_space"] is None
    # backward compatibility: the pre-existing user-profile fields are untouched
    assert isinstance(machine["path_has_space"], bool)
    assert isinstance(machine["username_ascii"], bool)
    assert machine["user_profile_non_ascii"] == (not machine["username_ascii"])


@pytest.mark.skipif(sys.platform != "win32", reason="host probe is Windows-only")
def test_vault_fields_measure_the_vault_path(tmp_path: Path) -> None:
    vault = tmp_path / "\u56fe \u4e66 \u9986" / ("deep-" * 40)
    payload = probe(tmp_path, "-Vault", str(vault))
    machine = payload["machine"]
    assert machine["vault_path_measured"] == str(vault)
    assert machine["vault_path_len_chars"] == len(str(vault))
    assert machine["vault_path_non_ascii"] is True
    assert machine["vault_path_has_space"] is True
