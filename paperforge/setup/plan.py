"""SetupPlan — orchestrates all setup steps in sequence."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from paperforge.setup import SetupStepResult
from paperforge.setup.agent import AgentInstaller
from paperforge.setup.checker import SetupChecker
from paperforge.setup.config_writer import ConfigWriter
from paperforge.setup.vault import VaultInitializer

ProgressCallback = Callable[[str], None]


class SetupPlan:
    """Orchestrate the setup lifecycle: check -> config -> vault -> deps -> agent."""

    def _emit_ndjson(self, results: list[SetupStepResult], ok: bool) -> int:
        """#137 machine stream: start/phase/item_result per step, then
        EXACTLY one terminal (result|error) carrying the PFResult."""
        from paperforge import __version__ as PF_VERSION
        from paperforge.core.errors import ErrorCode
        from paperforge.core.ndjson import (
            emit_item_result,
            emit_phase,
            emit_start,
            emit_terminal,
        )
        from paperforge.core.result import PFError, PFResult

        emit_start("foundation.setup")
        for r in results:
            emit_phase("foundation.setup", phase=r.step)
            emit_item_result(
                "foundation.setup",
                item_id=r.step,
                status="ok" if r.ok else "error",
            )
        pf = PFResult(
            ok=ok,
            command="setup",
            version=PF_VERSION,
            data={"steps": [r.to_dict() for r in results]},
            error=(
                PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="setup failed",
                )
                if not ok
                else None
            ),
        )
        emit_terminal("result" if ok else "error", "foundation.setup", pf)
        return 0 if ok else 1

    def __init__(
        self,
        vault: Path,
        config: dict | None = None,
        zotero_path: str | None = None,
        agent_type: str = "opencode",
        version: str | None = None,
        skip_checks: bool = False,
        progress_callback: ProgressCallback | None = None,
    ):
        self.vault = vault
        self.config = config or {}
        self.zotero_path = zotero_path
        self.agent_type = agent_type
        self.version = version
        self.skip_checks = skip_checks
        self.progress_callback = progress_callback

    def _log(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)

    def execute(
        self, json_output: bool = False, ndjson: bool = False
    ) -> list[SetupStepResult] | int:
        """Run all setup steps in sequence.

        Args:
            json_output: If True, return results list as JSON dict list.
            ndjson: If True, emit the #137 structured stream (start/phase/
                item_result/…/result|error + exactly-one terminal) and
                return the exit code.
            Else: return exit code (0 = success, 1 = failure).
        """
        results: list[SetupStepResult] = []

        # Step 1: Checker (skip if flag set)
        if not self.skip_checks:
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

        # Step 4: #174 / #143 — dependency extras only. The runtime package
        # is installed EXACTLY once by the bootstrap (plugin venv + ONE
        # pinned install, or pip). Setup only ENSURES the [vector] extras
        # the core features require; already present → no-op.  A duplicate
        # package install here would reinstall the just-verified runtime
        # and violate "one consent = one bootstrap install attempt".
        from paperforge.setup.runtime import ensure_runtime_dependencies

        self._log("Ensuring runtime dependencies...")
        results.append(ensure_runtime_dependencies())

        # Step 5: Agent installer
        self._log("Deploying agent config...")
        agent = AgentInstaller(self.vault, agent_type=self.agent_type)
        agent_results = agent.run_all()
        results.extend(agent_results)

        # Step 6 (#143 / #174): pointer publication — Python is the ONLY
        # writer; publication is part of lifecycle success and MUST happen
        # before any terminal success is emitted (human or machine).
        ok = all(r.ok for r in results)
        if ok:
            from paperforge.runtime_pointer import publish_pointer

            publish_pointer()
            self._log("Runtime pointer published")

        if ndjson:
            return self._emit_ndjson(results, ok)

        if json_output:
            output = [r.to_dict() for r in results]
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0 if ok else 1

        # Print summary
        ok_count = sum(1 for r in results if r.ok)
        total = len(results)
        print(f"Setup complete: {ok_count}/{total} steps passed")
        for r in results:
            status = "PASS" if r.ok else "FAIL"
            print(f"  [{status}] {r.step}: {r.message}")
            if not r.ok and r.error:
                print(f"         Error: {r.error}")

        return 0 if ok else 1
