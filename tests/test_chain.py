"""Follow-up chain runner tests (#167 / T6 + closure corrective).

Inline policy (automatic-local only, everything else pending); per-
invocation dedupe by canonical (action_id, NORMALIZED scope) — [A,A,B] ≡
[B,A]; depth 0..MAX legal, depth > MAX skipped; successful-scope seam
(#167 P0-5) — per-key results feed post-publish reconcile, never the bare
requested scope; W2 settle (#167 P0-2) — dispatched actions overwrite the
last-attempt record, pending/skipped never do; strict wire scope (unknown
kind → skipped, never widened to all); cancellation at the action
boundary; O2 (failed action → no children).
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
        recorded.append(f"{request.action_id}:{sorted(set(request.scope.keys)) if request.scope.kind == 'papers' else 'all'}")
        return PFResult(ok=True, command="action run", version="t", data={"scope": request.scope.kind})
    return handler


# ── inline policy ─────────────────────────────────────────────────────────

class TestInlinePolicy:
    def test_automatic_local_inline_and_remote_pending(self, _registry, _vault, monkeypatch) -> None:
        recorded: list[str] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        _registry(_spec("test.remote", automatic=False, confirmation="required", cost="remote_possible",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain([_wire("test.local"), _wire("test.remote")], build_context(_vault))
        assert recorded == ["test.local:all"]
        statuses = {s.action_id: s.status for s in chain.steps}
        assert statuses["test.local"] == "executed"
        assert statuses["test.remote"] == "pending"
        assert [s.reason_code for s in chain.steps if s.action_id == "test.remote"] == ["chain.remote_spend"]
        assert chain.ok is True

    def test_destructive_descendant_pending(self, _registry, _vault, monkeypatch) -> None:
        recorded: list[str] = []
        _registry(_spec("test.destructive", automatic=True, confirmation="none", cost="local",
                        impact="destructive", handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain([_wire("test.destructive")], build_context(_vault))
        assert recorded == []
        assert chain.steps[0].status == "pending"
        assert chain.steps[0].reason_code == "chain.destructive"

    def test_confirmation_required_descendant_pending_even_if_automatic(
        self, _registry, _vault, monkeypatch,
    ) -> None:
        """confirmation=required always pends — automatic does not grant
        inline execution for a confirmed action (frozen #145)."""
        recorded: list[str] = []
        _registry(_spec("test.conf", automatic=True, confirmation="required", cost="local",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain([_wire("test.conf")], build_context(_vault))
        assert recorded == []
        assert chain.steps[0].reason_code == "chain.confirmation_required"


# ── dedupe ────────────────────────────────────────────────────────────────

class TestDedupe:
    def test_normalized_scope_dedupe_including_dup_keys(self, _registry, _vault, monkeypatch) -> None:
        """[A,A,B] ≡ [B,A] — canonical key uses NORMALIZED keys, so
        duplicate keys inside one scope and reordered siblings collapse."""
        recorded: list[str] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain(
            [_wire("test.local", ["A", "A", "B"]), _wire("test.local", ["B", "A"])],
            build_context(_vault),
        )
        assert recorded == ["test.local:['A', 'B']"]
        executed = [s for s in chain.steps if s.status == "executed"]
        skipped = [s for s in chain.steps if s.status == "skipped"]
        assert len(executed) == 1
        assert len(skipped) == 1
        assert skipped[0].reason_code == "chain.duplicate"


# ── depth ─────────────────────────────────────────────────────────────────

class TestDepth:
    def test_depth_4_executes_depth_5_overflows(self, _registry, _vault, monkeypatch) -> None:
        """Frozen depth contract: 0..MAX_FOLLOW_UP_DEPTH legal; depth > MAX
        rejected (#167 P1-1).  Each layer emits a DISTINCT action so dedupe
        never masks the depth gate."""
        recorded: list[str] = []
        for i in range(MAX_FOLLOW_UP_DEPTH + 2):
            _registry(_spec(f"test.step{i}", automatic=True, confirmation="none", cost="local",
                            handler=_ok_handler_factory(recorded)))
        producer_calls = {"n": 0}

        def producer(vault, keys):
            producer_calls["n"] += 1
            return PFResult(ok=True, command="reconcile", version="t",
                            next_actions=[_wire(f"test.step{producer_calls['n']}")])

        monkeypatch.setattr(chain_module, "_reconcile_producer", producer)
        chain = run_chain([_wire("test.step0")], build_context(_vault))
        depths = [s.depth for s in chain.steps]
        assert max(depths) == MAX_FOLLOW_UP_DEPTH + 1
        overflow = [s for s in chain.steps if s.reason_code == "chain.depth_overflow"]
        assert len(overflow) == 1
        assert overflow[0].depth == MAX_FOLLOW_UP_DEPTH + 1
        # depth 0..4 executed (5 actions), depth 5 skipped
        assert len(recorded) == MAX_FOLLOW_UP_DEPTH + 1


# ── successful-scope seam ─────────────────────────────────────────────────

class TestSuccessfulScope:
    def test_per_key_successful_keys_feed_post_publish_reconcile(
        self, _registry, _vault, monkeypatch,
    ) -> None:
        """#167 P0-5: request [A,B], only A succeeds → reconcile receives
        [A], never the bare requested scope."""
        seen: list[Any] = []

        def partial(ctx, request):
            return PFResult(ok=True, command="action run", version="t",
                            successful_keys=["A"])

        _registry(_spec("test.partial", automatic=True, confirmation="none", cost="local",
                        handler=partial))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: (seen.append(keys), PFResult(ok=True, command="reconcile", version="t"))[1])
        run_chain([_wire("test.partial", ["A", "B"])], build_context(_vault))
        assert seen == [["A"]]

    def test_all_or_nothing_falls_back_to_request_scope(self, _registry, _vault, monkeypatch) -> None:
        seen: list[Any] = []
        _registry(_spec("test.all", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory([])))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: (seen.append(keys), PFResult(ok=True, command="reconcile", version="t"))[1])
        run_chain([_wire("test.all", ["B", "A"])], build_context(_vault))
        assert seen == [["A", "B"]]


# ── W2 settle ─────────────────────────────────────────────────────────────

class TestW2Settle:
    def test_dispatched_success_writes_succeeded_attempt(self, _registry, _vault, monkeypatch) -> None:
        from paperforge.reconcile import read_last_attempts

        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory([])))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        run_chain([_wire("test.local")], build_context(_vault))
        attempts = read_last_attempts(_vault)
        assert attempts["test.local:all"]["outcome"] == "succeeded"

    def test_dispatched_failure_writes_failed_attempt(self, _registry, _vault, monkeypatch) -> None:
        """W2 (#167 P0-2): a FAILED dispatch settles a failed last-attempt —
        the next same-digest trigger suppresses re-emission."""
        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError
        from paperforge.reconcile import read_last_attempts

        def failing(ctx, request):
            return PFResult(ok=False, command="action run", version="t",
                            error=PFError(code=ErrorCode.INTERNAL_ERROR, message="boom"))

        _registry(_spec("test.fail", automatic=True, confirmation="none", cost="local",
                        handler=failing))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        chain = run_chain([_wire("test.fail")], build_context(_vault))
        assert chain.ok is False
        attempts = read_last_attempts(_vault)
        assert attempts["test.fail:all"]["outcome"] == "failed"

    def test_pending_intent_never_settles_an_attempt(self, _registry, _vault, monkeypatch) -> None:
        """Pre-dispatch pending (confirmation-required) is NOT a failed
        attempt — W2 only records dispatched actions."""
        from paperforge.reconcile import read_last_attempts

        _registry(_spec("test.remote", automatic=False, confirmation="required", cost="remote_possible",
                        handler=_ok_handler_factory([])))
        monkeypatch.setattr(chain_module, "_reconcile_producer",
                            lambda vault, keys: PFResult(ok=True, command="reconcile", version="t"))
        run_chain([_wire("test.remote")], build_context(_vault))
        assert read_last_attempts(_vault) == {}


# ── strict wire scope ─────────────────────────────────────────────────────

class TestStrictScope:
    def test_unknown_scope_kind_never_widens_to_all(self, _registry, _vault, monkeypatch) -> None:
        """#167 P1-2: a garbage scope kind is skipped (chain.scope_invalid),
        never widened to an all-scope execution."""
        recorded: list[str] = []
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory(recorded)))
        bad = _wire("test.local")
        bad["scope"] = {"kind": "garbage"}
        chain = run_chain([bad], build_context(_vault))
        assert recorded == []
        assert chain.steps[0].status == "skipped"
        assert chain.steps[0].reason_code == "chain.scope_invalid"


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
            run_chain([_wire("test.boom")], build_context(_vault))
        assert producer_calls["n"] == 0
        assert recorded == ["test.boom"]


# ── O2 ────────────────────────────────────────────────────────────────────

class TestO2:
    def test_failed_action_derives_no_children(self, _registry, _vault, monkeypatch) -> None:
        """O2 (#167): a failed action must not emit anything downstream —
        no successful publish → no post-publish reconcile → no embed.resume
        in executed, pending, or next_actions."""
        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError

        recorded: list[str] = []

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
        chain = run_chain([_wire("test.fail")], build_context(_vault))
        assert recorded == ["test.fail"]
        assert producer_calls["n"] == 0
        assert chain.ok is False
        all_ids = [s.action_id for s in chain.steps] + [i["action_id"] for i in chain.pending]
        assert "embed.resume" not in all_ids


# ── producer seam ─────────────────────────────────────────────────────────

class TestProducer:
    def test_producer_failure_never_fails_sync(self, _registry, _vault, monkeypatch) -> None:
        """A broken producer (exception) must not fail the chain."""
        _registry(_spec("test.local", automatic=True, confirmation="none", cost="local",
                        handler=_ok_handler_factory([])))

        def broken(vault, keys):
            raise RuntimeError("producer broken")

        monkeypatch.setattr(chain_module, "_reconcile_producer", broken)
        chain = run_chain([_wire("test.local")], build_context(_vault))
        assert chain.ok is True
