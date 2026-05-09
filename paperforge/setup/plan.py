"""SetupPlan — orchestrates all setup steps in sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from paperforge.setup import SetupStepResult
from paperforge.setup.checker import SetupChecker
from paperforge.setup.config_writer import ConfigWriter
from paperforge.setup.vault import VaultInitializer
from paperforge.setup.runtime import RuntimeInstaller
from paperforge.setup.agent import AgentInstaller

ProgressCallback = Callable[[str], None]


class SetupPlan:
    """Orchestrate the setup lifecycle: check -> config -> vault -> install -> agent."""

    def __init__(
        self,
        vault: Path,
        config: dict | None = None,
        env_values: dict[str, str] | None = None,
        zotero_path: str | None = None,
        agent_type: str = "opencode",
        version: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ):
        self.vault = vault
        self.config = config or {}
        self.env_values = env_values or {}
        self.zotero_path = zotero_path
        self.agent_type = agent_type
        self.version = version
        self.progress_callback = progress_callback

    def _log(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)

    def execute(self, json_output: bool = False) -> list[SetupStepResult] | int:
        """Run all setup steps in sequence.

        Args:
            json_output: If True, return results list as JSON string.
                        If False, return exit code (0 = success, 1 = failure).
        """
        results: list[SetupStepResult] = []

        # Step 1: Checker
        self._log("Checking preconditions...")
        checker = SetupChecker(self.vault)
        results.append(checker.run())

        # Step 2: Config writer
        self._log("Writing config...")
        writer = ConfigWriter(self.vault)
        results.append(writer.write(self.config))

        # Step 3: Vault initializer
        self._log("Initializing vault structure...")
        vault_init = VaultInitializer(self.vault, self.config)
        results.append(vault_init.create_directories())
        results.append(vault_init.create_zotero_junction(self.zotero_path))
        results.append(vault_init.merge_env(self.env_values))

        # Step 4: Runtime installer
        self._log("Installing runtime...")
        installer = RuntimeInstaller(self.vault, version=self.version, progress_callback=self._log)
        results.append(installer.install())

        # Step 5: Agent installer
        self._log("Deploying agent config...")
        agent = AgentInstaller(self.vault, agent_type=self.agent_type)
        agent_results = agent.run_all()
        results.extend(agent_results)

        if json_output:
            output = [r.to_dict() for r in results]
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0

        # Print summary
        ok_count = sum(1 for r in results if r.ok)
        total = len(results)
        print(f"Setup complete: {ok_count}/{total} steps passed")
        for r in results:
            status = "PASS" if r.ok else "FAIL"
            print(f"  [{status}] {r.step}: {r.message}")
            if not r.ok and r.error:
                print(f"         Error: {r.error}")

        return 0 if all(r.ok for r in results) else 1
