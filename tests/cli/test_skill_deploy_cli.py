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


def test_skill_sync_auto_updates_unmodified_and_preserves_customized(tmp_path: Path, monkeypatch) -> None:
    from paperforge.services.skill_deploy import (
        _skill_tree_digest,
        _write_skill_state,
        deploy_skills,
        sync_skills_if_unmodified,
    )

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    # Initial deploy writes shipped digest ledger
    deployed = deploy_skills(vault)
    assert deployed["skill_deployed"] is True
    dst_skill = vault / ".agents" / "skills" / "paperforge" / "SKILL.md"
    assert sync_skills_if_unmodified(vault)["status"] == "up_to_date"

    # Simulate an older untouched official skill version on disk (hash == recorded)
    dst_skill.write_text("# older official release", encoding="utf-8")
    _write_skill_state(vault, ".agents/skills", _skill_tree_digest(dst_skill.parent))
    synced = sync_skills_if_unmodified(vault)
    assert synced["status"] == "updated"
    assert synced["synced"] is True
    assert "# older official release" not in dst_skill.read_text(encoding="utf-8")

    # User customizes the deployed skill -> must be preserved, never overwritten
    dst_skill.write_text("# user custom skill notes", encoding="utf-8")
    preserved = sync_skills_if_unmodified(vault)
    assert preserved["status"] == "customized_preserved"
    assert preserved["synced"] is False
    assert dst_skill.read_text(encoding="utf-8") == "# user custom skill notes"

    # CLI route `paperforge skill sync --json` works cleanly too
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), "skill", "sync", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "customized_preserved"


def test_atomic_skill_replace_preserves_prior_skill_on_stage_failure(
    tmp_path: Path, monkeypatch
) -> None:
    from paperforge.services import skill_deploy

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    first = skill_deploy.deploy_skills(vault)
    assert first["skill_deployed"] is True
    dst_skill = vault / ".agents" / "skills" / "paperforge"
    (dst_skill / "SKILL.md").write_text("# working prior skill", encoding="utf-8")

    # Simulate copy failure while staging replacement — prior skill must remain untouched
    def _boom_copy(src, dst, **kwargs):
        Path(dst).mkdir(parents=True, exist_ok=True)
        (Path(dst) / "partial.txt").write_text("incomplete", encoding="utf-8")
        raise OSError("disk error during skill stage")

    monkeypatch.setattr(skill_deploy.shutil, "copytree", _boom_copy)
    failed = skill_deploy.deploy_skills(vault, overwrite=True)
    assert failed["skill_deployed"] is False
    assert failed["errors"]
    assert (dst_skill / "SKILL.md").read_text(encoding="utf-8") == "# working prior skill"
    assert not any(p.name.startswith(".paperforge-skill-") for p in dst_skill.parent.iterdir())
