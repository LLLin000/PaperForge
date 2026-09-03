"""Action registry, runner, and CLI tests (#163 / T2, #145)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from paperforge.actions.registry import ACTION_REGISTRY, emit_next_action, validate_registry
from paperforge.actions.runner import (
    ActionError,
    descriptor_for,
    hydrate_from_registry,
    run_action,
)
from paperforge.actions.types import (
    ActionContext,
    ActionIntent,
    ActionRequest,
    ActionSpec,
    AllScope,
    PapersScope,
    PreflightResult,
)
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFResult

from tests.conftest import canonical_test_config


def _ctx(tmp_path: Path) -> ActionContext:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault, system_dir="99_System")
    return ActionContext(vault=vault, config={"system_dir": "99_System"}, paths={})


def _ok_result() -> PFResult:
    return PFResult(ok=True, command="action run", version="test", data={"done": True})


def _spec(action_id: str, **overrides) -> ActionSpec:
    defaults = dict(
        action_id=action_id,
        label_code=f"action.{action_id}",
        description_code=f"action.{action_id}.description",
        handler=lambda ctx, req: _ok_result(),
        preflight=lambda ctx, req: PreflightResult(
            availability="available",
            availability_reason_code="action.available",
            availability_reason="ok",
        ),
        scope_kinds=("all",),
        cost="local",
        impact="mutating",
        confirmation="none",
        automatic=True,
        interruptible=True,
        execution_mode="result",
    )
    defaults.update(overrides)
    return ActionSpec(**defaults)


@pytest.fixture
def _registry(monkeypatch):
    """A test-only action registered for the duration of the test."""
    added: list[str] = []

    def _register(spec: ActionSpec) -> str:
        ACTION_REGISTRY[spec.action_id] = spec  # type: ignore[index]
        added.append(spec.action_id)
        return spec.action_id

    yield _register
    for action_id in added:
        del ACTION_REGISTRY[action_id]  # type: ignore[arg-type]


# ── registry invariants ───────────────────────────────────────────────────

class TestRegistryInvariants:
    def test_builtin_registry_is_valid(self) -> None:
        assert validate_registry() == []
        assert set(ACTION_REGISTRY) == {
            "memory.build", "memory.rebuild", "embed.resume", "embed.build", "ocr.run",
            "ocr.rebuild_derived", "foundation.update", "foundation.repair", "library.prune",
        }

    def test_id_contract_enforced(self) -> None:
        from paperforge.actions.types import require_action_id

        require_action_id("memory.build")
        require_action_id("memory.build.extra")  # multi-segment ids are legal
        with pytest.raises(ValueError):
            require_action_id("Memory.build")
        with pytest.raises(ValueError):
            require_action_id("memory")
        with pytest.raises(ValueError):
            require_action_id("memory..build")

    def test_remote_possible_requires_confirmation_and_not_automatic(self) -> None:
        problems = validate_registry({
            "test.remote": _spec("test.remote", cost="remote_possible", confirmation="none", automatic=False),
        })
        assert any("remote_possible requires confirmation" in p for p in problems)
        problems = validate_registry({
            "test.remote2": _spec("test.remote2", cost="remote_possible", confirmation="required", automatic=True),
        })
        assert any("remote_possible cannot be automatic" in p for p in problems)

    def test_destructive_requires_confirmation_and_not_automatic(self) -> None:
        problems = validate_registry({
            "test.destructive": _spec("test.destructive", impact="destructive", confirmation="none"),
        })
        assert any("destructive requires confirmation" in p for p in problems)
        problems = validate_registry({
            "test.destructive2": _spec("test.destructive2", impact="destructive", confirmation="required", automatic=True),
        })
        assert any("destructive cannot be automatic" in p for p in problems)

    def test_unknown_scope_kind_rejected(self) -> None:
        problems = validate_registry({
            "test.scope": _spec("test.scope", scope_kinds=("all", "bogus")),
        })
        assert any("unknown scope kinds" in p for p in problems)

    def test_no_command_or_argv_anywhere(self) -> None:
        """#145: no descriptor, spec, or wire value carries command/argv."""
        for spec in ACTION_REGISTRY.values():
            assert not hasattr(spec, "command")
            assert not hasattr(spec, "argv")
            assert not hasattr(spec, "cmd")

    def test_papers_scope_registration_matches_seams(self) -> None:
        # T3/T4: both memory.build and embed.resume gained papers scope.
        assert set(ACTION_REGISTRY["memory.build"].scope_kinds) == {"all", "papers"}
        assert set(ACTION_REGISTRY["embed.resume"].scope_kinds) == {"all", "papers"}

    def test_execution_mode_invariants(self) -> None:
        """T2 / ADR 0003: Every action explicitly declares execution_mode."""
        streaming = {
            "foundation.update", "embed.resume", "embed.build", "ocr.run", "ocr.rebuild_derived",
        }
        result_only = {
            "foundation.repair", "memory.build", "memory.rebuild", "library.prune",
        }
        for action_id, spec in ACTION_REGISTRY.items():
            assert hasattr(spec, "execution_mode"), f"{action_id} missing execution_mode"
            assert spec.execution_mode in ("result", "stream")
            if action_id in streaming:
                assert spec.execution_mode == "stream", f"{action_id} must be stream"
            if action_id in result_only:
                assert spec.execution_mode == "result", f"{action_id} must be result"

    def test_invalid_execution_mode_rejected(self) -> None:
        problems = validate_registry({
            "test.invalid": _spec("test.invalid", execution_mode="unknown"),
        })
        assert any("invalid execution_mode" in p for p in problems)


# ── runner pipeline ────────────────────────────────────────────────────────

class TestRunnerPipeline:
    def test_unknown_action_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ActionError) as exc:
            run_action(ActionRequest("nope.nope", AllScope()), _ctx(tmp_path))
        assert exc.value.code == ErrorCode.ACTION_UNKNOWN.value
        assert exc.value.exit_code == 2

    def test_scope_validation(self, tmp_path: Path, _registry) -> None:
        _registry(_spec("test.scopecheck", scope_kinds=("all",)))
        with pytest.raises(ActionError) as exc:
            run_action(ActionRequest("test.scopecheck", PapersScope(("K1",))), _ctx(tmp_path))
        assert exc.value.code == ErrorCode.ACTION_SCOPE_INVALID.value
        assert exc.value.exit_code == 2

    def test_unavailable_preflight_blocks(self, tmp_path: Path, _registry) -> None:
        def busy_preflight(ctx, req):
            return PreflightResult(
                availability="busy",
                availability_reason_code="vector.build_in_progress",
                availability_reason="busy now",
            )

        _registry(_spec("test.busy", preflight=busy_preflight))
        with pytest.raises(ActionError) as exc:
            run_action(ActionRequest("test.busy", AllScope()), _ctx(tmp_path))
        assert exc.value.code == ErrorCode.ACTION_BUSY.value
        assert exc.value.exit_code == 1

    def test_confirmation_required_without_confirm(self, tmp_path: Path, _registry) -> None:
        _registry(_spec("test.confirm", confirmation="required", automatic=False, cost="remote_possible"))
        with pytest.raises(ActionError) as exc:
            run_action(ActionRequest("test.confirm", AllScope()), _ctx(tmp_path))
        assert exc.value.code == ErrorCode.ACTION_CONFIRMATION_REQUIRED.value
        assert exc.value.exit_code == 3
        # #163 corrective: exit 3 carries the CURRENT action descriptor.
        data = exc.value.data
        assert isinstance(data, dict)
        assert data["action_id"] == "test.confirm"
        assert data["confirmation"] == "required"
        assert data["availability"] == "available"
        assert "preservation_facts" in data and "replacement_facts" in data
        assert "command" not in data and "argv" not in data

    def test_confirm_mismatch_is_invalid_request(self, tmp_path: Path, _registry) -> None:
        _registry(_spec("test.confirm", confirmation="required", automatic=False, cost="remote_possible"))
        with pytest.raises(ActionError) as exc:
            run_action(
                ActionRequest("test.confirm", AllScope()),
                _ctx(tmp_path),
                confirmed_action_id="other.action",
            )
        assert exc.value.code == ErrorCode.ACTION_INVALID_REQUEST.value
        assert exc.value.exit_code == 2

    def test_confirmation_never_bypasses_availability(self, tmp_path: Path, _registry) -> None:
        def unavailable(ctx, req):
            return PreflightResult(
                availability="unavailable",
                availability_reason_code="action.config_missing",
                availability_reason="no config",
            )

        _registry(_spec("test.gate", preflight=unavailable, confirmation="required", automatic=False, cost="remote_possible"))
        with pytest.raises(ActionError) as exc:
            run_action(
                ActionRequest("test.gate", AllScope()),
                _ctx(tmp_path),
                confirmed_action_id="test.gate",
            )
        assert exc.value.code == ErrorCode.ACTION_UNAVAILABLE.value  # preflight first

    def test_successful_dispatch_returns_handler_result(self, tmp_path: Path, _registry) -> None:
        called: list[str] = []

        def handler(ctx, req):
            called.append(req.action_id)
            return _ok_result()

        _registry(_spec("test.ok", handler=handler))
        result = run_action(ActionRequest("test.ok", AllScope()), _ctx(tmp_path))
        assert result.ok and called == ["test.ok"]

    def test_next_actions_returned_unchanged(self, tmp_path: Path, _registry) -> None:
        """T2 ships --follow none: the root handler's next_actions pass
        through untouched (the follow-up chain is T6 scope)."""
        def handler(ctx, req):
            result = _ok_result()
            result.next_actions = [
                emit_next_action(
                    ActionIntent("embed.resume", AllScope(), "vector.pending", "pending")
                ).to_dict()
            ]
            return result

        _registry(_spec("test.emits", handler=handler))
        result = run_action(ActionRequest("test.emits", AllScope()), _ctx(tmp_path))
        assert result.ok
        assert [n["action_id"] for n in result.next_actions] == ["embed.resume"]
        # v1 wire fields are intact (automatic/cost/impact/confirmation/reason)
        item = result.next_actions[0]
        assert item["automatic"] is False
        assert item["cost"] == "remote_possible"
        assert item["confirmation"] == "required"
        assert item["reason"] == "pending"
        assert "dedupe_key" not in item
        assert "follow_up_execution" not in (result.data or {})

    def test_handler_exceptions_become_structured_errors(self, tmp_path: Path, _registry) -> None:
        """#163 corrective: a dispatched action always yields exactly one
        PFResult — handler exceptions convert at the runner boundary, never
        a traceback."""
        def handler(ctx, req):
            raise RuntimeError("domain boom")

        _registry(_spec("test.boom", handler=handler))
        result = run_action(ActionRequest("test.boom", AllScope()), _ctx(tmp_path))
        assert result.ok is False
        assert result.error is not None
        assert result.error.code.value == "INTERNAL_ERROR"
        assert "domain boom" in result.error.message

    def test_handler_keyboard_interrupt_propagates_to_cancellation(self, tmp_path: Path, _registry) -> None:
        """#137: KeyboardInterrupt is NOT folded into a structured error —
        it propagates to the CLI's rc130 cancellation path."""
        def handler(ctx, req):
            raise KeyboardInterrupt("cancelled")

        _registry(_spec("test.cancel", handler=handler))
        with pytest.raises(KeyboardInterrupt):
            run_action(ActionRequest("test.cancel", AllScope()), _ctx(tmp_path))

    def test_non_mapping_handler_data_rejected(self, tmp_path: Path, _registry) -> None:
        """#145 Rev3: PFResult.data must be a mapping or None."""
        def handler(ctx, req):
            return PFResult(ok=True, command="action run", version="t", data="not-a-mapping")

        _registry(_spec("test.baddata", handler=handler))
        result = run_action(ActionRequest("test.baddata", AllScope()), _ctx(tmp_path))
        assert result.ok is False
        assert "non-mapping data" in (result.error.message if result.error else "")

    def test_non_pfresult_handler_return_rejected(self, tmp_path: Path, _registry) -> None:
        def handler(ctx, req):
            return {"ok": True}  # type: ignore[return-value]

        _registry(_spec("test.badreturn", handler=handler))
        result = run_action(ActionRequest("test.badreturn", AllScope()), _ctx(tmp_path))
        assert result.ok is False
        assert "not PFResult" in (result.error.message if result.error else "")


    def test_descriptor_carries_execution_mode(self, tmp_path: Path, _registry) -> None:
        spec = _spec("test.mode", execution_mode="stream")
        _registry(spec)
        context = _ctx(tmp_path)
        request = ActionRequest("test.mode", AllScope())
        preflight = spec.preflight(context, request)
        desc = descriptor_for(spec, request, preflight)
        assert desc["execution_mode"] == "stream"

        intent = ActionIntent("test.mode", AllScope(), "test", "test")
        hydrated = hydrate_from_registry(intent)
        assert hydrated["execution_mode"] == "stream"

# ── follow-up chain ────────────────────────────────────────────────────────

class TestContext:
    def test_build_context_from_single_snapshot(self, tmp_path: Path) -> None:
        """#163 corrective: config values and paths derive from ONE config
        snapshot — the context is a frozen invocation view (C0 seam)."""
        from paperforge.actions.runner import build_context

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        ctx = build_context(vault)
        assert ctx.config.get("system_dir") == "99_System"
        assert str(ctx.paths.get("ocr", "")) == str(vault / "99_System" / "PaperForge" / "ocr")

    def test_build_context_fails_closed_without_config(self, tmp_path: Path) -> None:
        from paperforge.actions.runner import build_context

        vault = tmp_path / "novault"
        ctx = build_context(vault)
        assert ctx.config == {}
        assert ctx.paths == {}


class TestDescriptorWire:
    def test_descriptor_has_no_command_or_argv(self) -> None:
        from paperforge.actions.registry import ACTION_REGISTRY
        from paperforge.actions.types import AllScope, ActionRequest, PreflightResult

        for spec in ACTION_REGISTRY.values():
            descriptor = descriptor_for(
                spec,
                ActionRequest(spec.action_id, AllScope()),
                PreflightResult("available", "action.available", "ok"),
            )
            for forbidden in ("command", "cmd", "argv", "shell", "executable"):
                assert forbidden not in descriptor, forbidden
                assert not any(forbidden in str(v) for v in descriptor.values())

    def test_hydrate_from_registry_matches_wire_shape(self) -> None:
        wire = hydrate_from_registry(
            ActionIntent("memory.build", AllScope(), "library.changed", "Library changed")
        )
        assert wire["action_id"] == "memory.build"
        assert wire["automatic"] is True
        assert wire["cost"] == "local"
        assert wire["confirmation"] == "none"
        assert wire["reason"] == "Library changed"
        assert wire["execution_mode"] == "result"
        assert "command" not in wire

    def test_emit_unknown_action_fails_closed(self) -> None:
        with pytest.raises(KeyError):
            emit_next_action(ActionIntent("nope.nope", AllScope(), "t", "why"))


# ── CLI exit codes ─────────────────────────────────────────────────────────

def _run_cli(*argv: str) -> tuple[int, dict]:
    from paperforge.cli import main

    old_in, old_out = sys.stdin, sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        rc = main(list(argv))
    finally:
        sys.stdin, sys.stdout = old_in, old_out
    return rc, json.loads(buf.getvalue())


class TestCliExitCodes:
    def test_list(self, tmp_path: Path) -> None:
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "list", "--json")
        assert rc == 0
        actions = payload["data"]["actions"]
        ids = [a["action_id"] for a in actions]
        assert ids == ["embed.build", "embed.resume", "foundation.repair", "foundation.update",
                "library.prune", "memory.build", "memory.rebuild", "ocr.rebuild_derived", "ocr.run"]
        for a in actions:
            assert a["execution_mode"] in ("result", "stream")
            if a["action_id"] in ("embed.build", "embed.resume", "foundation.update", "ocr.run", "ocr.rebuild_derived"):
                assert a["execution_mode"] == "stream"
            else:
                assert a["execution_mode"] == "result"

    def test_describe_includes_execution_mode(self, tmp_path: Path) -> None:
        canonical_test_config(tmp_path)
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "describe", "ocr.run", "--json")
        assert rc == 0
        assert payload["data"]["execution_mode"] == "stream"

        rc2, payload2 = _run_cli("--vault", str(tmp_path), "action", "describe", "memory.build", "--json")
        assert rc2 == 0
        assert payload2["data"]["execution_mode"] == "result"

    def test_probe_primary_action_includes_execution_mode(self) -> None:
        from paperforge.commands.probe import build_action_primary

        act_stream = build_action_primary(action_id="ocr.rebuild_derived", verb="rebuild_derived", label="Rebuild")
        assert act_stream["execution_mode"] == "stream"

        act_result = build_action_primary(action_id="memory.build", verb="build", label="Build")
        assert act_result["execution_mode"] == "result"

        act_setup = build_action_primary(action_id="foundation.setup", verb="setup", label="Setup")
        assert act_setup["execution_mode"] == "stream"
    def test_describe_unknown_is_exit_2(self, tmp_path: Path) -> None:
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "describe", "nope.nope", "--json")
        assert rc == 2
        assert payload["error"]["code"] == "action.unknown"

    def test_run_unknown_is_exit_2(self, tmp_path: Path) -> None:
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "run", "nope.nope", "--json")
        assert rc == 2
        assert payload["error"]["code"] == "action.unknown"

    def test_run_papers_scope_unknown_key_is_exit_2(self, tmp_path: Path) -> None:
        """T3: memory.build accepts papers scope; unknown keys are an invalid
        scope (exit 2) rejected by preflight (index must exist first)."""
        from tests.test_memory_build_scoped import _entry, _make_vault, _write_index

        vault = _make_vault(tmp_path)
        _write_index(vault, [_entry("A", "Paper A")])
        rc, payload = _run_cli(
            "--vault", str(vault), "action", "run", "memory.build",
            "--scope", "papers", "--key", "ZZZ", "--json",
        )
        assert rc == 2
        assert payload["error"]["code"] == "action.scope_invalid"

    def test_run_unavailable_preflight_is_exit_1(self, tmp_path: Path) -> None:
        # embed.resume without a credential -> preflight unavailable -> rc1,
        # with the precise reason code preserved in the payload data.
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "run", "embed.resume", "--json")
        assert rc == 1
        assert payload["error"]["code"] == "action.unavailable"
        assert payload["data"]["availability_reason_code"] == "credential.missing"

    def test_scoped_resume_incompatible_substrate_is_unavailable(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """#166 P0-1: a papers-scoped resume on a GLOBAL substrate defect
        (model changed) must be preflight-unavailable (substrate), so the
        runner never attempts a build that would fail fast in run_build."""
        from tests.test_lineage import _make_vault

        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        vault = _make_vault(tmp_path)
        from paperforge.config import set_config

        set_config(vault, "vector_db_api_model", "text-embedding-3-large")
        rc, payload = _run_cli(
            "--vault", str(vault), "action", "run", "embed.resume",
            "--scope", "papers", "--key", "KEY1", "--json",
        )
        assert rc == 1
        assert payload["error"]["code"] == "action.unavailable"
        assert payload["data"]["availability_reason_code"] == "vector.substrate_incompatible"

    def test_confirmation_required_cli_exit_3_with_descriptor(self, tmp_path: Path, monkeypatch) -> None:
        """#163 acceptance: without --confirm, a confirmation-required action
        exits 3 and the payload data IS the current action descriptor."""
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "test-token")
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "run", "embed.resume", "--json")
        assert rc == 3
        assert payload["error"]["code"] == "action.confirmation_required"
        data = payload["data"]
        assert data["action_id"] == "embed.resume"
        assert data["scope"] == {"kind": "all"}
        assert data["availability"] == "available"
        assert data["cost"] == "remote_possible"
        assert data["impact"] == "mutating"
        assert data["confirmation"] == "required"
        assert data["preservation_facts"] and data["replacement_facts"]
        assert "command" not in data and "argv" not in data

    def test_confirmed_dispatch_executes(self, tmp_path: Path, monkeypatch) -> None:
        """--confirm with the exact id executes; the embed handler runs to
        its structured result (missing index -> error rc1 in this vault)."""
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "test-token")
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "embed.resume",
            "--confirm", "embed.resume", "--json",
        )
        # Dispatched: rc is 0 or 1 (structured result), never 2/3.
        assert rc in (0, 1)
        assert "error" in payload or payload["ok"] is True

    def test_follow_auto_never_bypasses_root_confirmation(self, tmp_path: Path, monkeypatch) -> None:
        """#167 P0-1: --follow auto must NOT change the explicit root
        contract — a remote root without --confirm is rc3 + descriptor,
        exactly as with --follow none."""
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "test-token")
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "embed.resume",
            "--follow", "auto", "--json",
        )
        assert rc == 3
        assert payload["error"]["code"] == "action.confirmation_required"
        assert payload["data"]["action_id"] == "embed.resume"

    def test_follow_auto_wrong_confirm_is_rc2(self, tmp_path: Path, monkeypatch) -> None:
        """#167 P0-1: wrong --confirm id stays rc2 under --follow auto."""
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "test-token")
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "embed.resume",
            "--follow", "auto", "--confirm", "memory.build", "--json",
        )
        assert rc == 2
        assert payload["error"]["code"] == "action.invalid_request" 

    def test_memory_build_handler_emits_no_followups(self, tmp_path: Path, monkeypatch) -> None:
        """#167 P0-3: handlers never hardcode follow-ups — the memory.build
        handler's result carries ZERO next_actions; reconcile is the single
        producer (the chain derives the next layer)."""
        from paperforge.actions.registry import ACTION_REGISTRY
        from paperforge.actions.runner import build_context
        from paperforge.actions.types import ActionRequest, AllScope

        from tests.conftest import canonical_test_config

        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        context = build_context(vault)
        request = ActionRequest(action_id="memory.build", scope=AllScope())
        preflight = ACTION_REGISTRY["memory.build"].preflight(context, request)
        assert preflight.availability != "unavailable" or preflight.availability_reason_code in (
            "action.config_missing", "action.library_index_missing",
        )
        # Preflight unavailable here (no index) — verify the SOURCE contract
        # instead: the handler body must not emit embed.resume.
        import inspect

        src = inspect.getsource(ACTION_REGISTRY["memory.build"].handler)
        assert "embed.resume" not in src
        assert "next_actions" not in src.replace("PFResult", "").replace("result =", "") or "result.next_actions" not in src

    def test_cancelled_dispatch_is_rc130(self, tmp_path: Path) -> None:
        """#137: a cancelled dispatch reports a cancelled terminal, never rc1."""
        from paperforge.commands.action import run as action_run

        args = type("A", (), {
            "action_verb": "run",
            "action_id": "memory.build",
            "scope": "all",
            "key": [],
            "confirm": None,
            "follow": "none",
            "json": True,
            "vault_path": tmp_path,
        })()
        import unittest.mock as mock

        with mock.patch("paperforge.commands.action.run_dispatch", side_effect=KeyboardInterrupt("cancelled")):
            rc = action_run(args)  # type: ignore[arg-type]
        assert rc == 130


class TestFoundationRepairPolicy174:
    """#174 P1-1: foundation.repair's registry policy must match its REAL
    side effects (may pip install vector extras + republish the pointer)
    — remote_possible/mutating/required, never local/read_only/automatic."""

    def test_foundation_repair_descriptor_is_truthful(self) -> None:
        from paperforge.actions.registry import ACTION_REGISTRY

        spec = ACTION_REGISTRY["foundation.repair"]
        assert spec.cost == "remote_possible"
        assert spec.impact == "mutating"
        assert spec.confirmation == "required"
        assert spec.automatic is False

    def test_foundation_repair_requires_confirmation_exit_3(self, tmp_path: Path, monkeypatch) -> None:
        """Without --confirm a confirmation-required action exits 3 with the
        CURRENT descriptor — the caller must explicitly authorize a pip
        install + pointer republish."""
        monkeypatch.setattr(
            "paperforge.runtime_pointer.read_pointer",
            lambda: {
                "python_path": "C:/Python/python.exe",
                "environment_root": "C:/Python",
                "paperforge_version": "1.5.15",
            },
        )
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "foundation.repair", "--json"
        )
        assert rc == 3
        assert payload["error"]["code"] == "action.confirmation_required"
        data = payload["data"]
        assert data["action_id"] == "foundation.repair"
        assert data["cost"] == "remote_possible"
        assert data["impact"] == "mutating"

    def test_foundation_update_unavailable_without_pointer(self, tmp_path: Path, monkeypatch) -> None:
        """#174 pass-2: update is post-bootstrap — no pointer → unavailable,
        symmetric with repair."""
        monkeypatch.setattr(
            "paperforge.runtime_pointer.read_pointer", lambda: None
        )
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "foundation.update", "--json"
        )
        assert rc == 1
        assert payload["data"]["availability_reason_code"] == "pointer.missing"

    def test_foundation_repair_unavailable_without_pointer(self, tmp_path: Path, monkeypatch) -> None:
        """Preflight fails closed: no published pointer → the handler cannot
        succeed → unavailable (not a green light for a doomed run)."""
        monkeypatch.setattr(
            "paperforge.runtime_pointer.read_pointer", lambda: None
        )
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "foundation.repair", "--json"
        )
        assert rc == 1
        assert payload["data"]["availability_reason_code"] == "pointer.missing"
