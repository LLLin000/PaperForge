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
            ndjson: If True, emit the #137 structured stream — start, then
                phase/item_result per step AS IT HAPPENS (not after the
                fact), cooperative cancellation (stdin PAPERFORGE_STOP /
                SIGINT / SIGTERM → exactly-one `cancelled` terminal, rc
                130), then exactly-one result|error terminal.
            Else: return exit code (0 = success, 1 = failure).
        """
        results: list[SetupStepResult] = []
        cancelled = False

        if ndjson:
            from paperforge.core.cancellation import make_cancellation_token
            from paperforge.core.ndjson import emit_start

            emit_start("foundation.setup")
            _is_stopped, _restore = make_cancellation_token()
        else:
            _is_stopped, _restore = (lambda: False), (lambda: None)

        def _run_step(
            step_id: str, fn: Callable[[], SetupStepResult]
        ) -> SetupStepResult | None:
            nonlocal cancelled
            if _is_stopped():
                cancelled = True
                return None
            result = fn()
            results.append(result)
            if ndjson:
                from paperforge.core.ndjson import emit_item_result, emit_phase

                emit_phase("foundation.setup", phase=step_id)
                emit_item_result(
                    "foundation.setup",
                    item_id=step_id,
                    status="ok" if result.ok else "error",
                )
            return result

        # Step 1: Checker (skip if flag set)
        if not self.skip_checks:
            self._log("Checking preconditions...")
            _run_step("checker", lambda: SetupChecker(self.vault).run())

        # Step 2: Config writer
        self._log("Writing config...")
        _run_step("config_writer", lambda: ConfigWriter(self.vault).write(self.config))

        # Step 3: Vault initializer
        self._log("Initializing vault structure...")
        vault_init = VaultInitializer(self.vault, self.config)
        _run_step("vault_initializer", vault_init.create_directories)
        _run_step("vault_initializer.zotero_junction", lambda: vault_init.create_zotero_junction(self.zotero_path))

        # Step 4: #174 / #143 — dependency extras only. The runtime package
        # is installed EXACTLY once by the bootstrap (plugin venv + ONE
        # pinned install, or pip). Setup only ENSURES the [vector] extras
        # the core features require; already present → no-op.  A duplicate
        # package install here would reinstall the just-verified runtime
        # and violate "one consent = one bootstrap install attempt".
        from paperforge.setup.runtime import ensure_runtime_dependencies

        self._log("Ensuring runtime dependencies...")
        _run_step("runtime_dependencies", ensure_runtime_dependencies)

        # Step 5: Agent installer
        self._log("Deploying agent config...")
        agent = AgentInstaller(self.vault, agent_type=self.agent_type)
        for agent_result in agent.run_all():
            results.append(agent_result)
            if ndjson:
                from paperforge.core.ndjson import emit_item_result, emit_phase

                emit_phase("foundation.setup", phase=agent_result.step)
                emit_item_result(
                    "foundation.setup",
                    item_id=agent_result.step,
                    status="ok" if agent_result.ok else "error",
                )

        if cancelled:
            if ndjson:
                _restore()
            return self._emit_ndjson_terminal("cancelled", results, ok=False, rc=130)

        # Step 6 (#143 / #174): pointer publication — Python is the ONLY
        # writer; publication is part of lifecycle success and MUST happen
        # before any terminal success is emitted (human or machine).
        ok = all(r.ok for r in results)
        if ok:
            from paperforge.runtime_pointer import publish_pointer

            publish_pointer()
            self._log("Runtime pointer published")

        if ndjson:
            _restore()
            return self._emit_ndjson_terminal(
                "result" if ok else "error", results, ok=ok, rc=0 if ok else 1
            )

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

    def _emit_ndjson_terminal(
        self, event: str, results: list[SetupStepResult], ok: bool, rc: int
    ) -> int:
        """Exactly-one #137 terminal (result | error | cancelled)."""
        from paperforge import __version__ as PF_VERSION
        from paperforge.core.errors import ErrorCode
        from paperforge.core.ndjson import emit_terminal
        from paperforge.core.result import PFError, PFResult

        pf = PFResult(
            ok=ok,
            command="setup",
            version=PF_VERSION,
            data={"steps": [r.to_dict() for r in results]},
            error=(
                PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="setup failed" if event == "error" else "setup cancelled",
                )
                if event != "result"
                else None
            ),
        )
        emit_terminal(event, "foundation.setup", pf)
        return rc
