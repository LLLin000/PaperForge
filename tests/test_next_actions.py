"""#127 — NextAction schema invariants and PFResult round-trip."""
from __future__ import annotations

import pytest

from paperforge.core.next_actions import (
    CONFIRM_REQUIRED,
    COST_REMOTE,
    IMPACT_DESTRUCTIVE,
    NextAction,
    NextActionScope,
    automatic_local_actions,
    build_next_action,
    next_actions_from_dicts,
    next_actions_to_dicts,
    remote_or_destructive_actions,
    validate_next_action,
    validate_next_actions_payload,
)


def _memory_action(**overrides) -> NextAction:
    return build_next_action(
        "memory.build", **{"reason": "library index changed", **overrides}
    )


def _embed_action(**overrides) -> NextAction:
    return build_next_action(
        "embed.resume", **{"reason": "changed papers need vectors", **overrides}
    )


class TestBuildAndRoundTrip:
    def test_build_from_registry_defaults(self):
        action = _memory_action()
        assert action.automatic is True
        assert action.cost == "local"
        assert action.impact == "mutating"
        assert action.confirmation == "none"
        assert action.dedupe_key == "memory.build"

    def test_embed_defaults_are_non_automatic_confirmed(self):
        action = _embed_action()
        assert action.automatic is False
        assert action.cost == COST_REMOTE
        assert action.confirmation == CONFIRM_REQUIRED

    def test_dict_round_trip(self):
        action = _embed_action(scope=NextActionScope(kind="papers", keys=("ABC123",)))
        restored = next_actions_from_dicts(next_actions_to_dicts((action,)))[0]
        assert restored == action

    def test_unknown_action_id_rejected(self):
        with pytest.raises(ValueError, match="unknown next action id"):
            build_next_action("shell.exec", reason="x")

    def test_invalid_override_raises_at_build(self):
        """Producers must fail closed at the seam: a remote action forced to
        automatic, or a papers scope with empty keys, is rejected."""
        with pytest.raises(ValueError, match="must not be automatic"):
            build_next_action("embed.resume", reason="x", automatic=True)
        with pytest.raises(ValueError, match="must not mean all papers"):
            build_next_action("memory.build", reason="x", scope=NextActionScope(kind="papers"))

    def test_pfresult_payload_validation(self):
        action = _embed_action()
        payloads = [a.to_dict() for a in (action,)]
        assert validate_next_actions_payload(payloads) == []


def _raw_action(action_id: str = "memory.build", **overrides) -> NextAction:
    """Construct an action directly (bypasses build-time validation) to test
    the validator itself."""
    from paperforge.core.next_actions import ACTION_REGISTRY

    spec = ACTION_REGISTRY[action_id]
    fields = {
        "action_id": action_id,
        "scope": NextActionScope(kind="all"),
        "automatic": spec.automatic,
        "cost": spec.cost,
        "impact": spec.impact,
        "confirmation": "required" if spec.cost == COST_REMOTE else "none",
        "reason": "test",
    }
    fields.update(overrides)
    return NextAction(**fields)


class TestInvariants:
    def test_remote_automatic_rejected(self):
        action = _raw_action("embed.resume", automatic=True)
        assert any("must not be automatic" in p for p in validate_next_action(action))

    def test_remote_without_confirmation_rejected(self):
        action = _raw_action("embed.resume", confirmation="none")
        assert any("requires confirmation" in p for p in validate_next_action(action))

    def test_destructive_automatic_rejected(self):
        action = _raw_action(impact=IMPACT_DESTRUCTIVE)
        assert any("must not be automatic" in p for p in validate_next_action(action))

    def test_papers_scope_empty_keys_rejected(self):
        action = _raw_action(scope=NextActionScope(kind="papers"))
        assert any("must not mean all papers" in p for p in validate_next_action(action))

    def test_all_scope_with_keys_rejected(self):
        action = _raw_action(scope=NextActionScope(kind="all", keys=("X",)))
        assert any("must not carry keys" in p for p in validate_next_action(action))

    def test_unknown_schema_version_fails_closed(self):
        action = _memory_action()
        action = NextAction(
            schema_version=999,
            action_id=action.action_id,
            scope=action.scope,
            automatic=action.automatic,
            cost=action.cost,
            impact=action.impact,
            confirmation=action.confirmation,
            reason=action.reason,
        )
        assert any("unsupported schema_version" in p for p in validate_next_action(action))

    def test_duplicate_dedupe_key_rejected(self):
        a = _memory_action()
        b = _memory_action(reason="another reason")
        assert any("duplicate dedupe_key" in p for p in validate_next_actions_payload(
            [a.to_dict(), b.to_dict()]
        ))

    def test_empty_reason_rejected(self):
        action = _raw_action(reason="  ")
        assert any("reason" in p for p in validate_next_action(action))


class TestSelection:
    def test_automatic_local_subset(self):
        actions = (_memory_action(), _embed_action())
        local = automatic_local_actions(actions)
        assert [a.action_id for a in local] == ["memory.build"]

    def test_remote_subset(self):
        actions = (_memory_action(), _embed_action())
        risky = remote_or_destructive_actions(actions)
        assert [a.action_id for a in risky] == ["embed.resume"]

    def test_local_mutating_not_risky(self):
        actions = (_memory_action(),)
        assert remote_or_destructive_actions(actions) == ()
