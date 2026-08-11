"""Follow-up chain runner tests (#167 / T6, #159 §5).

Per-invocation dedupe (normalized keys), constant depth, auto-mode inline
for automatic-local only, confirmed parent never confirms a child,
cancellation at the next action boundary, O2 (failed action → no children),
single-producer reconcile seam.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from paperforge.actions import chain as chain_module
from paperforge.actions.chain import MAX_FOLLOW_UP_DEPTH, run_chain
from paperforge.actions.runner import build_context
from paperforge.actions.types import ActionSpec, PreflightResult
from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.core.result import PFResult

from tests.conftest import canonical_test_config


def _wire(action_id: str, keys: list[str] | None = None) -> dict:
    scope = {"kind": "papers", "keys": keys} if keys is not None else {"kind": "all"}
    return {"schema_version": 1, "action_id": action_id, "scope": scope, "automatic": False,
            "cost": "local", "impact": "mutating", "confirmation": "required", "reason": "test"}


def _available_preflight(ctx, req) -> PreflightResult:
    return PreflightResult(
        availability="available",
        availability_reason_code="action.available",
        availability_reason="ok",
    )


def _spec(action_id: str, *, automatic=True, confirmation="none", cost="local",
          impact="mutating", handler) -> ActionSpec:
    return ActionSpec(
        action_id=action_id,
        label_code="action.test",
        description_code="action.test.description",
        handler=handler,
        preflight=_available_preflight,
        scope_kinds=("all", "papers"),
        cost=cost,
        impact=impact,
        confirmation=confirmation,
        automatic=automatic,
        interruptible=True,
    )


@pytest.fixture
def _registry(monkeypatch):
    """Test-only actions registered for the duration of the test."""
    added: list[str] = []

    def _register(spec: ActionSpec) -> str:
        ACTION_REGISTRY[spec.action_id] = spec  # type: ignore[index]
        added.append(spec.action_id)
        return spec.action_id

    yield _register
    for action_id in added:
        del ACTION_REGISTRY[action_id]  # type: ignore[arg-type]


@pytest.fixture
def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="99_System")
    return vault


def _ok_handler_factory(recorded: list[str]):
    def handler(ctx, request):
        recorded.append(f"{request.action_id}:{sorted(request.scope.keys) if request.scope.kind == 'papers' else 'all'}")
        return PFResult(ok=True, command="action run", version="t", data={"scope": request.scope.kind})
    return handler


# ── auto-mode inline policy ───────────────────────────────────────────────

class TestAutoInline:
    def test_automatic_local_inline_and_remote_pending(self, _registry, _vault, monkeypatch) -> None:
        recorded: list[str] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        _registry(_spec("test.remote", automatic=False, confirmation="required", cost="remote_possible",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain(
            [_wire("test.local"), _wire("test.remote")],
            build_context(_vault), follow="auto",
        )
        assert recorded == ["test.local:all"]
        statuses = {s.action_id: s.status for s in chain.steps}
        assert statuses["test.local"] == "executed"
        assert statuses["test.remote"] == "pending"
        assert [s.reason_code for s in chain.steps if s.action_id == "test.remote"] == ["chain.remote_spend"]
        assert chain.ok is True

    def test_follow_none_runs_nothing_but_root(self, _registry, _vault, monkeypatch) -> None:
        recorded: list[str] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        _registry(_spec("test.child", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(
                                ok=True, command="reconcile", version="t",
                                next_actions=[_wire("test.child")]))
        # root executes; the derived child with follow=none stays pending
        chain = run_chain([_wire("test.local")], build_context(_vault), follow="none")
        assert recorded == ["test.local:all"]
        assert len(chain.steps) == 2
        assert chain.steps[1].status == "pending"
        assert chain.steps[1].reason_code == "chain.follow_disabled"

    def test_destructive_descendant_pending(self, _registry, _vault, monkeypatch) -> None:
        recorded: list[str] = []
        _registry(_spec("test.destructive", automatic=True, confirmation="none", cost="local",
                        impact="destructive", handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain([_wire("test.destructive")], build_context(_vault), follow="auto")
        assert recorded == []
        assert chain.steps[0].status == "pending"
        assert chain.steps[0].reason_code == "chain.destructive"


# ── dedupe ────────────────────────────────────────────────────────────────

class TestDedupe:
    def test_normalized_scope_dedupe(self, _registry, _vault, monkeypatch) -> None:
        """[A,B] ≡ [B,A] — same canonical action+scope runs once."""
        recorded: list[str] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain(
            [_wire("test.local", ["A", "B"]), _wire("test.local", ["B", "A"])],
            build_context(_vault), follow="auto",
        )
        assert recorded == ["test.local:['A', 'B']"]
        executed = [s for s in chain.steps if s.status == "executed"]
        skipped = [s for s in chain.steps if s.status == "skipped"]
        assert len(executed) == 1
        assert len(skipped) == 1
        assert skipped[0].reason_code == "chain.duplicate"


# ── depth ─────────────────────────────────────────────────────────────────

class TestDepth:
    def test_depth_overflow_reported_skipped(self, _registry, _vault, monkeypatch) -> None:
        """A producer that keeps emitting children must stop at the depth
        cap; deeper intents are skipped with chain.depth_overflow.  Each
        layer emits a DISTINCT action so dedupe never masks the depth gate."""
        recorded: list[str] = []
        for i in range(MAX_FOLLOW_UP_DEPTH + 1):
            _registry(_spec(f"test.step{i}", automatic=True, confirmation="none", cost="local",
                            handler=_ok_handler_factory(recorded)))
        producer_calls = {"n": 0}

        def producer(vault, keys):
            producer_calls["n"] += 1
            # Keep deriving one distinct child per success, forever.
            n = producer_calls["n"]
            return PFResult(ok=True, command="reconcile", version="t",
                            next_actions=[_wire(f"test.step{n}")])

        monkeypatch.setattr(chain_module, "_reconcile_producer", producer)
        chain = run_chain([_wire("test.step0")], build_context(_vault), follow="auto")
        depths = [s.depth for s in chain.steps]
        assert max(depths) == MAX_FOLLOW_UP_DEPTH
        overflow = [s for s in chain.steps if s.reason_code == "chain.depth_overflow"]
        assert len(overflow) == 1
        assert overflow[0].depth == MAX_FOLLOW_UP_DEPTH
        # root + children up to MAX-1 executed; MAX skipped
        assert len(recorded) == MAX_FOLLOW_UP_DEPTH


# ── confirmation boundary ────────────────────────────────────────────────

class TestConfirmation:
    def test_confirmed_parent_never_confirms_child(self, _registry, _vault, monkeypatch) -> None:
        """Root confirmed with --confirm runs; a confirmation-required child
        is pending and its handler is NEVER invoked."""
        recorded: list[str] = []
        _registry(_spec("test.parent", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        _registry(_spec("test.child", automatic=False, confirmation="required", cost="remote_possible",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(
            chain_module, "_reconcile_producer",
            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t",
                                         next_actions=[_wire("test.child")]),
        )
        chain = run_chain([_wire("test.parent")], build_context(_vault),
                          follow="auto", confirmed_action_id="test.parent")
        assert recorded == ["test.parent:all"]
        child = [s for s in chain.steps if s.action_id == "test.child"][0]
        assert child.status == "pending"
        assert child.reason_code == "chain.remote_spend"
        assert chain.pending == [_wire("test.child")]


# ── cancellation ──────────────────────────────────────────────────────────

class TestCancellation:
    def test_keyboard_interrupt_halts_at_boundary(self, _registry, _vault, monkeypatch) -> None:
        """Cancellation propagates out of the chain — no further layer is
        derived, and the transcript stops at the interrupted step."""
        recorded: list[str] = []

        def exploding(ctx, request):
            recorded.append(request.action_id)
            raise KeyboardInterrupt

        _registry(_spec("test.boom", automatic=True, confirmation="none", cost="local",
                        handler=exploding))
        _registry(_spec("test.after", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        producer_calls = {"n": 0}

        def producer(vault, keys):
            producer_calls["n"] += 1
            return PFResult(ok=True, command="reconcile", version="t",
                            next_actions=[_wire("test.after")])

        monkeypatch.setattr(chain_module, "_reconcile_producer", producer)
        with pytest.raises(KeyboardInterrupt):
            run_chain([_wire("test.boom")], build_context(_vault), follow="auto")
        # producer never derived children after the interrupt
        assert producer_calls["n"] == 0
        assert recorded == ["test.boom"]


# ── O2: failed action produces no children ────────────────────────────────

class TestO2:
    def test_failed_action_derives_no_children(self, _registry, _vault, monkeypatch) -> None:
        """O2 (#167): a failed action must not emit anything downstream —
        no successful publish → no post-publish reconcile → no embed.resume
        in executed, pending, or next_actions."""
        recorded: list[str] = []

        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError

        def failing(ctx, request):
            recorded.append(request.action_id)
            return PFResult(ok=False, command="action run", version="t",
                            error=PFError(code=ErrorCode.INTERNAL_ERROR,
                                          message="forced failure"))

        _registry(_spec("test.fail", automatic=True, confirmation="none", cost="local",
                        handler=failing))
        producer_calls = {"n": 0}

        def producer(vault, keys):
            producer_calls["n"] += 1
            return PFResult(ok=True, command="reconcile", version="t",
                            next_actions=[_wire("embed.resume")])

        monkeypatch.setattr(chain_module, "_reconcile_producer", producer)
        chain = run_chain([_wire("test.fail")], build_context(_vault), follow="auto")
        assert recorded == ["test.fail"]
        assert producer_calls["n"] == 0
        assert chain.ok is False
        all_ids = [s.action_id for s in chain.steps] + [i["action_id"] for i in chain.pending]
        assert "embed.resume" not in all_ids


# ── single producer seam ──────────────────────────────────────────────────

class TestProducer:
    def test_successful_keys_flow_to_reconcile(self, _registry, _vault, monkeypatch) -> None:
        """The post-publish reconcile receives the successful scope keys."""
        seen: list[Any] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory([])))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: (seen.append(keys), PFResult(ok=True, command="reconcile", version="t"))[1])
        run_chain([_wire("test.local", ["B", "A"])], build_context(_vault), follow="auto")
        assert seen == [["A", "B"]]

    def test_producer_failure_never_fails_sync(self, _registry, _vault, monkeypatch) -> None:
        """A broken producer (exception) must not fail the chain."""
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory([])))

        def broken(vault, keys):
            raise RuntimeError("producer broken")

        monkeypatch.setattr(chain_module, "_reconcile_producer", broken)
        chain = run_chain([_wire("test.local")], build_context(_vault), follow="auto")
        assert chain.ok is True
