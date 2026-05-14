"""AgentInstaller — deploys paperforge skill to vault-local agent config."""

from __future__ import annotations

import shutil
from pathlib import Path

from paperforge.services.skill_deploy import AGENT_SKILL_DIRS
from paperforge.setup import SetupStepResult


class AgentInstaller:
    """Deploy paperforge skill directory to vault-local agent skills path."""

    def __init__(self, vault: Path, agent_type: str = "opencode"):
        self.vault = vault
        self.agent_type = agent_type
        self._script_dir = Path(__file__).resolve().parent.parent

    def _get_skills_dir(self) -> Path:
        """Get the vault-local target skills directory."""
        skill_dir_name = AGENT_SKILL_DIRS.get(self.agent_type, ".agents/skills")
        return self.vault / skill_dir_name

    def deploy_skills(self) -> SetupStepResult:
        """Deploy paperforge skill as a single directory."""
        source_skills = self._script_dir / "skills" / "paperforge"
        if not source_skills.exists():
            return SetupStepResult(
                step="agent_installer",
                ok=False,
                message="Skill source directory not found",
                error=f"Not found: {source_skills}",
            )

        target_dir = self._get_skills_dir() / "paperforge"
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copytree(source_skills, target_dir, dirs_exist_ok=True)
            return SetupStepResult(
                step="agent_installer",
                ok=True,
                message=f"Deployed paperforge skill to {target_dir}",
                details={"source": str(source_skills), "target": str(target_dir)},
            )
        except Exception as e:
            return SetupStepResult(
                step="agent_installer",
                ok=False,
                message="Failed to deploy skills",
                error=str(e),
            )

    def deploy_agent_config(self) -> SetupStepResult:
        """Deploy AGENTS.md to vault root."""
        source_agents = self._script_dir.parent / "AGENTS.md"
        if not source_agents.exists():
            return SetupStepResult(
                step="agent_installer",
                ok=True,
                message="No AGENTS.md to deploy",
                details={"skipped": True},
            )

        try:
            target = self.vault / "AGENTS.md"
            shutil.copy2(source_agents, target)
            return SetupStepResult(
                step="agent_installer",
                ok=True,
                message=f"Deployed AGENTS.md to {target}",
                details={"source": str(source_agents), "target": str(target)},
            )
        except Exception as e:
            return SetupStepResult(
                step="agent_installer",
                ok=False,
                message="Failed to deploy AGENTS.md",
                error=str(e),
            )

    def run_all(self) -> list[SetupStepResult]:
        """Run all deployment steps."""
        return [self.deploy_skills(), self.deploy_agent_config()]
