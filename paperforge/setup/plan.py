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

    def _step_outcome(
        self,
        r: SetupStepResult | None,
        results: list[SetupStepResult],
        *,
        ndjson: bool,
        json_output: bool,
    ) -> int | None:
        """Uniform step gate: None -> cancelled (rc130); not ok -> fail fast
        (rc1, zero further mutation, no pointer publish).  Returns None to
        continue."""
        if r is None:  # cooperative cancellation observed
            if ndjson:
                return self._emit_ndjson_terminal("cancelled", results, ok=False, rc=130)
            return 130
        if not r.ok:
            return self._finish(results, False, ndjson=ndjson, json_output=json_output)
        return None

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
            check_result = _run_step("checker", lambda: SetupChecker(self.vault).run())
            _gate = self._step_outcome(check_result, results, ndjson=ndjson, json_output=json_output)
            if _gate is not None:
                return _gate

        # Step 2: Config writer
        self._log("Writing config...")
        cfg_result = _run_step("config_writer", lambda: ConfigWriter(self.vault).write(self.config))
        _gate = self._step_outcome(cfg_result, results, ndjson=ndjson, json_output=json_output)
        if _gate is not None:
            return _gate

        # Step 3: Vault initializer — layout comes from the SINGLE resolver
        # (resolve_paths), never from per-module defaults.
        self._log("Initializing vault structure...")
        from paperforge.config import resolve_paths

        try:
            _layout = resolve_paths(self.vault)
        except Exception as exc:  # noqa: BLE001 — fail closed, no mutation
            results.append(
                SetupStepResult(
                    step="vault_initializer",
                    ok=False,
                    message="Cannot resolve canonical layout",
                    error=str(exc),
                )
            )
            return self._finish(results, False, ndjson=ndjson, json_output=json_output)
        vault_init = VaultInitializer(self.vault, _layout)
        v_result = _run_step("vault_initializer", vault_init.create_directories)
        _gate = self._step_outcome(v_result, results, ndjson=ndjson, json_output=json_output)
        if _gate is not None:
            return _gate
        z_result = _run_step(
            "vault_initializer.zotero_junction",
            lambda: vault_init.create_zotero_junction(self.zotero_path),
        )
        _gate = self._step_outcome(z_result, results, ndjson=ndjson, json_output=json_output)
        if _gate is not None:
            return _gate

        # Step 4: #174 / #143 — dependency extras only. The runtime package
        # is installed EXACTLY once by the bootstrap (plugin venv + ONE
        # pinned install, or pip). Setup only ENSURES the [vector] extras
        # the core features require; already present → no-op.  A duplicate
        # package install here would reinstall the just-verified runtime
        # and violate "one consent = one bootstrap install attempt".
        from paperforge.setup.runtime import ensure_runtime_dependencies

        self._log("Ensuring runtime dependencies...")
        dep_result = _run_step("runtime_dependencies", ensure_runtime_dependencies)
        _gate = self._step_outcome(dep_result, results, ndjson=ndjson, json_output=json_output)
        if _gate is not None:
            return _gate

        # Step 5: Agent installer — platform comes from the canonical config
        # (written above), never from a CLI default; omitted --agent keeps
        # the existing platform and deploys to ITS skill dir.
        self._log("Deploying agent config...")
        from paperforge.config import load_config

        try:
            _snap = load_config(self.vault)
            _effective_agent = str(_snap.values["agent_platform"].value)
        except Exception:  # noqa: BLE001 — fail closed to the explicit value
            _effective_agent = self.agent_type or "opencode"
        agent = AgentInstaller(self.vault, agent_type=_effective_agent)
        for agent_step in agent.steps():
            # RC UX Seam P0: cooperative cancellation must be checked
            # BETWEEN agent sub-steps — a SIGTERM during agent deployment
            # only sets the flag; without this gate the loop would finish
            # and publish the pointer anyway.
            if _is_stopped():
                cancelled = True
                break
            agent_result = agent_step()
            results.append(agent_result)
            if ndjson:
                from paperforge.core.ndjson import emit_item_result, emit_phase

                emit_phase("foundation.setup", phase=agent_result.step)
                emit_item_result(
                    "foundation.setup",
                    item_id=agent_result.step,
                    status="ok" if agent_result.ok else "error",
                )
            # Fail fast between agent sub-steps: a failed sub-step stops the
            # remaining deployment (zero further mutation).
            _gate = self._step_outcome(agent_result, results, ndjson=ndjson, json_output=json_output)
            if _gate is not None:
                return _gate

        if cancelled or _is_stopped():
            # The last gate: even if cancellation arrived after the agent
            # loop finished (or mid publish), never publish the pointer on
            # a cancelled setup.
            cancelled = True
            if ndjson:
                _restore()
            return self._emit_ndjson_terminal("cancelled", results, ok=False, rc=130)

        return self._finish(results, cancelled, ndjson=ndjson, json_output=json_output)

    def _finish(
        self,
        results: list[SetupStepResult],
        cancelled: bool,
        *,
        ndjson: bool,
        json_output: bool,
    ) -> int:
        """Shared terminal: publish pointer only when every executed step
        passed, then emit the single result/error terminal."""
        # Step 6 (#143 / #174): pointer publication — Python is the ONLY
        # writer; publication is part of lifecycle success and MUST happen
        # before any terminal success is emitted (human or machine).
        ok = all(r.ok for r in results) and not cancelled
        if ok:
            from paperforge.runtime_pointer import publish_pointer

            publish_pointer()
            self._log("Runtime pointer published")

        if ndjson:
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
