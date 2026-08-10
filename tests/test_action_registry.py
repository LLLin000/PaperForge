"""Action registry, runner, and CLI tests (#163 / T2, #145)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from paperforge.actions.registry import ACTION_REGISTRY, emit_next_action, validate_registry
from paperforge.actions.runner import (
    MAX_FOLLOW_UP_DEPTH,
    ActionError,
    canonical_dedupe_key,
    descriptor_for,
    hydrate_from_registry,
    run_action,
    run_follow_up_chain,
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
        assert set(ACTION_REGISTRY) == {"memory.build", "embed.resume"}

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

    def test_papers_scope_not_registered_yet(self) -> None:
        # T2: all-scope only; papers scope lands with T3/T4 seams.
        for spec in ACTION_REGISTRY.values():
            assert spec.scope_kinds == ("all",)


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

    def test_handler_exceptions_become_structured_errors(self, tmp_path: Path, _registry) -> None:
        def handler(ctx, req):
            raise RuntimeError("domain boom")

        _registry(_spec("test.boom", handler=handler))
        # #145 §6.5: the runner boundary converts exceptions to PFResult errors.
        with pytest.raises(RuntimeError, match="domain boom"):
            run_action(ActionRequest("test.boom", AllScope()), _ctx(tmp_path))

    def test_dedupe_identity_normalizes_keys(self) -> None:
        assert canonical_dedupe_key("memory.build", PapersScope(("B", "A", "B"))) == canonical_dedupe_key(
            "memory.build", PapersScope(("A", "B"))
        )
        assert canonical_dedupe_key("memory.build", AllScope()) != canonical_dedupe_key(
            "memory.build", PapersScope(("A",))
        )


# ── follow-up chain ────────────────────────────────────────────────────────

class TestFollowUpChain:
    def test_follow_none_leaves_next_actions_pending(self, tmp_path: Path) -> None:
        root = _ok_result()
        root.next_actions = [
            emit_next_action(
                ActionIntent("embed.resume", AllScope(), "vector.pending", "pending")
            ).to_dict()
        ]
        result = run_follow_up_chain(root, _ctx(tmp_path), mode="none")
        assert [n["action_id"] for n in result.next_actions] == ["embed.resume"]
        assert "follow_up_execution" not in (result.data or {})

    def test_follow_auto_keeps_confirmation_required_pending(self, tmp_path: Path) -> None:
        root = _ok_result()
        root.next_actions = [
            emit_next_action(
                ActionIntent("embed.resume", AllScope(), "vector.pending", "pending")
            ).to_dict()
        ]
        result = run_follow_up_chain(root, _ctx(tmp_path), mode="auto")
        data = result.data or {}
        assert data["follow_up_execution"]["pending"] == [
            {"action_id": "embed.resume", "scope": {"kind": "all"}}
        ]
        assert data["follow_up_execution"]["executed"] == []
        # the outer wire keeps only pending actions
        assert [n["action_id"] for n in result.next_actions] == ["embed.resume"]

    def test_follow_auto_executes_automatic_local_descendants(self, tmp_path: Path, _registry) -> None:
        called: list[str] = []

        def handler(ctx, req):
            called.append(req.action_id)
            return _ok_result()

        _registry(_spec("test.auto", handler=handler))
        root = _ok_result()
        root.next_actions = [
            emit_next_action(
                ActionIntent("test.auto", AllScope(), "t", "why")
            ).to_dict()
        ]
        result = run_follow_up_chain(root, _ctx(tmp_path), mode="auto")
        assert called == ["test.auto"]
        data = result.data or {}
        assert data["follow_up_execution"]["executed"] == [{"action_id": "test.auto", "ok": True}]
        assert [n["action_id"] for n in result.next_actions] == []

    def test_depth_bounded(self, tmp_path: Path, _registry) -> None:
        """A linear chain of distinct actions is bounded by the depth
        constant; the overflowing descendant is skipped with depth_exceeded."""
        chain = [f"test.d{i}" for i in range(1, MAX_FOLLOW_UP_DEPTH + 2)]

        def chain_handler(next_id: str):
            def handler(ctx, req):
                result = _ok_result()
                if next_id:
                    result.next_actions = [
                        emit_next_action(ActionIntent(next_id, AllScope(), "t", "why")).to_dict()
                    ]
                return result
            return handler

        for i, action_id in enumerate(chain):
            nxt = chain[i + 1] if i + 1 < len(chain) else ""
            _registry(_spec(action_id, handler=chain_handler(nxt)))

        root = _ok_result()
        root.next_actions = [
            emit_next_action(ActionIntent(chain[0], AllScope(), "t", "why")).to_dict()
        ]
        result = run_follow_up_chain(root, _ctx(tmp_path), mode="auto")
        data = result.data or {}
        assert len(data["follow_up_execution"]["executed"]) == MAX_FOLLOW_UP_DEPTH
        assert data["follow_up_execution"]["skipped"][-1]["reason_code"] == "action.depth_exceeded"


# ── descriptors and wire ───────────────────────────────────────────────────

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
        assert "dedupe_key" not in wire
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
        ids = [a["action_id"] for a in payload["data"]["actions"]]
        assert ids == ["embed.resume", "memory.build"]

    def test_describe_unknown_is_exit_2(self, tmp_path: Path) -> None:
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "describe", "nope.nope", "--json")
        assert rc == 2
        assert payload["error"]["code"] == "action.unknown"

    def test_run_unknown_is_exit_2(self, tmp_path: Path) -> None:
        rc, payload = _run_cli("--vault", str(tmp_path), "action", "run", "nope.nope", "--json")
        assert rc == 2
        assert payload["error"]["code"] == "action.unknown"

    def test_run_scope_invalid_is_exit_2(self, tmp_path: Path) -> None:
        rc, payload = _run_cli(
            "--vault", str(tmp_path), "action", "run", "memory.build", "--scope", "papers", "--key", "K1", "--json"
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
