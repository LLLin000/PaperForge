"""Behavior tests for the isolated skill-deploy CLI route."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

from tests.conftest import canonical_test_config


def _payload(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    payload: object = json.loads(result.stdout)
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def test_skill_deploy_cli_preserves_and_replaces_only_managed_files(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    repo_root = Path(__file__).resolve().parents[2]
    source_skill = repo_root / "paperforge" / "skills" / "paperforge" / "SKILL.md"
    deployed_skill = vault / ".agents" / "skills" / "paperforge" / "SKILL.md"
    user_agents = vault / "AGENTS.md"
    _ = user_agents.write_text("owner instructions", encoding="utf-8")

    def invoke(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "paperforge",
                "--vault",
                str(vault),
                "skill",
                "deploy",
                *args,
                "--json",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )

    installed = invoke()
    installed_data = _payload(installed)
    assert installed.returncode == 0, installed.stderr
    assert installed_data["ok"] is True
    assert installed_data["skill_deployed"] is True
    assert deployed_skill.read_bytes() == source_skill.read_bytes()
    assert user_agents.read_text(encoding="utf-8") == "owner instructions"

    repeated = invoke()
    repeated_data = _payload(repeated)
    assert repeated.returncode == 0, repeated.stderr
    assert repeated_data["noop"] is True
    assert repeated_data["skill_deployed"] is True
    assert repeated_data["errors"] == []

    _ = deployed_skill.write_text("owner-edited skill", encoding="utf-8")
    conflict = invoke()
    conflict_data = _payload(conflict)
    assert conflict.returncode == 1
    assert conflict_data["already_exists"] is True
    assert conflict_data["skill_deployed"] is False
    errors = conflict_data["errors"]
    assert isinstance(errors, list) and errors
    assert isinstance(errors[0], str)
    assert "--overwrite" in errors[0]
    assert deployed_skill.read_text(encoding="utf-8") == "owner-edited skill"

    replaced = invoke("--overwrite")
    replaced_data = _payload(replaced)
    assert replaced.returncode == 0, replaced.stderr
    assert replaced_data["skill_deployed"] is True
    assert deployed_skill.read_bytes() == source_skill.read_bytes()
    assert user_agents.read_text(encoding="utf-8") == "owner instructions"

    escaped = invoke("--to", "../escape")
    escaped_data = _payload(escaped)
    assert escaped.returncode == 1
    assert escaped_data["ok"] is False
    errors = escaped_data["errors"]
    assert isinstance(errors, list) and errors
    assert not (tmp_path / "escape").exists()
