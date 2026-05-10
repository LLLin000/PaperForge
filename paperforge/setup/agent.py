"""AgentInstaller — deploys skill files and agent configs."""

from __future__ import annotations

import shutil
from pathlib import Path

from paperforge.setup import SetupStepResult


class AgentInstaller:
    """Deploy agent skill files, command files, and rules."""

    def __init__(self, vault: Path, agent_type: str = "opencode"):
        self.vault = vault
        self.agent_type = agent_type
        self._script_dir = Path(__file__).resolve().parent.parent

    def _get_skills_dir(self) -> Path:
        """Get the target skills directory based on agent type."""
        if self.agent_type == "opencode":
            base = Path.home() / ".config" / "opencode"
        elif self.agent_type == "claude":
            base = Path.home() / ".claude"
        elif self.agent_type == "codex":
            base = Path.home() / ".codex"
        else:
            base = self.vault / ".agents"
        return base / "skills"

    def deploy_skills(self) -> SetupStepResult:
        """Deploy literature-qa skill directory to agent config."""
        source_skills = self._script_dir / "skills" / "literature-qa"
        if not source_skills.exists():
            return SetupStepResult(
                step="agent_installer",
                ok=False,
                message="Skill source directory not found",
                error=f"Not found: {source_skills}",
            )

        target_dir = self._get_skills_dir() / "literature-qa"
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            if source_skills.is_dir():
                shutil.copytree(source_skills, target_dir, dirs_exist_ok=True)
            else:
                shutil.copy2(source_skills, target_dir)

            return SetupStepResult(
                step="agent_installer",
                ok=True,
                message=f"Deployed literature-qa skill to {target_dir}",
                details={"source": str(source_skills), "target": str(target_dir)},
            )
        except Exception as e:
            return SetupStepResult(
                step="agent_installer",
                ok=False,
                message="Failed to deploy skills",
                error=str(e),
            )

    def deploy_commands(self) -> SetupStepResult:
        """Deploy command files to vault agent config dir."""
        source_commands = self._script_dir / "command_files"
        if not source_commands.exists():
            return SetupStepResult(
                step="agent_installer",
                ok=True,
                message="No command files to deploy",
                details={"skipped": True},
            )

        agent_dir = self.vault / ".agents"
        target_dir = agent_dir / "command_files"
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            for f in source_commands.iterdir():
                if f.is_file():
                    shutil.copy2(f, target_dir / f.name)

            return SetupStepResult(
                step="agent_installer",
                ok=True,
                message=f"Deployed command files to {target_dir}",
                details={"source": str(source_commands), "target": str(target_dir)},
            )
        except Exception as e:
            return SetupStepResult(
                step="agent_installer",
                ok=False,
                message="Failed to deploy command files",
                error=str(e),
            )

    def deploy_agent_config(self) -> SetupStepResult:
        """Deploy AGENTS.md and other agent config files."""
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
        results = []
        results.append(self.deploy_skills())
        results.append(self.deploy_commands())
        results.append(self.deploy_agent_config())
        return results
