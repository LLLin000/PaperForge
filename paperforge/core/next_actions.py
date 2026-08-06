"""Typed next-action contract for PaperForge commands (#127).

A `NextAction` describes one follow-up a command may need, with orthogonal
cost/impact/confirmation axes so executors never have to guess policy:

- `cost`: `local` | `remote_possible` (API cost)
- `impact`: `read_only` | `mutating` | `destructive`
- `confirmation`: `none` | `required`

Invariants (enforced by `validate_next_actions`):

- `remote_possible` or `impact=destructive` ⇒ `automatic=false`
- `remote_possible` or `impact=destructive` ⇒ `confirmation=required`
- `scope.kind="all"` must carry no keys; `scope.kind="papers"` requires keys
  (an empty keys list must never mean "all papers")
- every `action_id` must be registered; unknown ids fail closed
- `schema_version` must match

The registry carries metadata only (defaults + reason guidance). Executable
argv mapping lives in the plugin's fixed allowlist; the backend never ships
command strings to executors.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

NEXT_ACTIONS_SCHEMA_VERSION = 1

COST_LOCAL = "local"
COST_REMOTE = "remote_possible"
IMPACT_READ_ONLY = "read_only"
IMPACT_MUTATING = "mutating"
IMPACT_DESTRUCTIVE = "destructive"
CONFIRM_NONE = "none"
CONFIRM_REQUIRED = "required"

_ALLOWED_COSTS = (COST_LOCAL, COST_REMOTE)
_ALLOWED_IMPACTS = (IMPACT_READ_ONLY, IMPACT_MUTATING, IMPACT_DESTRUCTIVE)
_ALLOWED_CONFIRMATIONS = (CONFIRM_NONE, CONFIRM_REQUIRED)


@dataclass(frozen=True)
class NextActionSpec:
    """Registry metadata for one known action. Never carries argv."""

    cost: str
    impact: str
    automatic: bool
    description: str = ""


# Registry: the authoritative set of follow-up action ids the backend may emit.
# The plugin keeps its own fixed argv allowlist; this table exists so producers
# and validators share one source of truth for metadata.
ACTION_REGISTRY: Mapping[str, NextActionSpec] = {
    "memory.build": NextActionSpec(
        cost=COST_LOCAL,
        impact=IMPACT_MUTATING,
        automatic=True,
        description="rebuild the local memory index after library changes",
    ),
    "embed.resume": NextActionSpec(
        cost=COST_REMOTE,
        impact=IMPACT_MUTATING,
        automatic=False,
        description="resume vector embedding for changed papers (may call a paid API)",
    ),
}


@dataclass(frozen=True)
class NextActionScope:
    kind: str
    keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind}
        if self.keys:
            out["keys"] = list(self.keys)
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> NextActionScope:
        return cls(kind=data["kind"], keys=tuple(data.get("keys", [])))


@dataclass(frozen=True)
class NextAction:
    action_id: str
    scope: NextActionScope
    automatic: bool
    cost: str
    impact: str
    confirmation: str
    reason: str
    schema_version: int = NEXT_ACTIONS_SCHEMA_VERSION
    dedupe_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "action_id": self.action_id,
            "scope": self.scope.to_dict(),
            "automatic": self.automatic,
            "cost": self.cost,
            "impact": self.impact,
            "confirmation": self.confirmation,
            "reason": self.reason,
        }
        if self.dedupe_key:
            out["dedupe_key"] = self.dedupe_key
        return out

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> NextAction:
        return cls(
            schema_version=data.get("schema_version", NEXT_ACTIONS_SCHEMA_VERSION),
            action_id=data["action_id"],
            scope=NextActionScope.from_dict(data["scope"]),
            automatic=data["automatic"],
            cost=data["cost"],
            impact=data["impact"],
            confirmation=data["confirmation"],
            reason=data.get("reason", ""),
            dedupe_key=data.get("dedupe_key", ""),
        )


def build_next_action(
    action_id: str,
    *,
    reason: str,
    scope: NextActionScope | None = None,
    automatic: bool | None = None,
    cost: str | None = None,
    impact: str | None = None,
    confirmation: str | None = None,
) -> NextAction:
    """Build an action from registry defaults plus explicit overrides.

    `confirmation` derives from the effective cost/impact when not given:
    remote or destructive ⇒ `required`, otherwise `none`.
    Raises ValueError for unknown action ids or invalid overrides.
    """
    spec = ACTION_REGISTRY.get(action_id)
    if spec is None:
        raise ValueError(f"unknown next action id: {action_id!r}")
    effective_automatic = spec.automatic if automatic is None else automatic
    effective_cost = spec.cost if cost is None else cost
    effective_impact = spec.impact if impact is None else impact
    if confirmation is None:
        confirmation = (
            CONFIRM_REQUIRED
            if effective_cost == COST_REMOTE or effective_impact == IMPACT_DESTRUCTIVE
            else CONFIRM_NONE
        )
    action = NextAction(
        action_id=action_id,
        scope=scope if scope is not None else NextActionScope(kind="all"),
        automatic=effective_automatic,
        cost=effective_cost,
        impact=effective_impact,
        confirmation=confirmation,
        reason=reason,
        dedupe_key=action_id,
    )
    problems = validate_next_actions((action,))
    if problems:
        raise ValueError("invalid next action: " + "; ".join(problems))
    return action


def validate_next_action(action: NextAction) -> list[str]:
    """Return invariant violations for one action; empty list = valid."""
    problems: list[str] = []
    if action.schema_version != NEXT_ACTIONS_SCHEMA_VERSION:
        problems.append(f"{action.action_id}: unsupported schema_version {action.schema_version}")
    if action.action_id not in ACTION_REGISTRY:
        problems.append(f"{action.action_id}: unknown action_id (fail closed)")
    if action.cost not in _ALLOWED_COSTS:
        problems.append(f"{action.action_id}: invalid cost {action.cost!r}")
    if action.impact not in _ALLOWED_IMPACTS:
        problems.append(f"{action.action_id}: invalid impact {action.impact!r}")
    if action.confirmation not in _ALLOWED_CONFIRMATIONS:
        problems.append(f"{action.action_id}: invalid confirmation {action.confirmation!r}")
    if action.scope.kind == "papers" and not action.scope.keys:
        problems.append(
            f"{action.action_id}: papers scope with empty keys must not mean all papers"
        )
    if action.scope.kind == "all" and action.scope.keys:
        problems.append(f"{action.action_id}: all scope must not carry keys")
    if action.scope.kind not in ("all", "papers"):
        problems.append(f"{action.action_id}: invalid scope kind {action.scope.kind!r}")
    if not action.reason.strip():
        problems.append(f"{action.action_id}: reason must not be empty")
    risky = action.cost == COST_REMOTE or action.impact == IMPACT_DESTRUCTIVE
    if risky and action.automatic:
        problems.append(
            f"{action.action_id}: remote/destructive action must not be automatic"
        )
    if risky and action.confirmation != CONFIRM_REQUIRED:
        problems.append(
            f"{action.action_id}: remote/destructive action requires confirmation"
        )
    return problems


def validate_next_actions(actions: tuple[NextAction, ...]) -> list[str]:
    """Validate a batch; duplicate dedupe_keys are also rejected."""
    problems: list[str] = []
    seen: set[str] = set()
    for action in actions:
        problems.extend(validate_next_action(action))
        key = action.dedupe_key or action.action_id
        if key in seen:
            problems.append(f"{action.action_id}: duplicate dedupe_key {key!r}")
        seen.add(key)
    return problems


def next_actions_to_dicts(actions: tuple[NextAction, ...]) -> list[dict[str, Any]]:
    return [action.to_dict() for action in actions]


def next_actions_from_dicts(payloads: list[Mapping[str, Any]]) -> tuple[NextAction, ...]:
    return tuple(NextAction.from_dict(payload) for payload in payloads)


def validate_next_actions_payload(payloads: list[Mapping[str, Any]]) -> list[str]:
    """Validate raw dict payloads (the PFResult wire shape)."""
    return validate_next_actions(next_actions_from_dicts(payloads))


def automatic_local_actions(actions: tuple[NextAction, ...]) -> tuple[NextAction, ...]:
    """The subset an executor may run without confirmation."""
    return tuple(
        action
        for action in actions
        if action.automatic and action.cost == COST_LOCAL and action.impact != IMPACT_DESTRUCTIVE
    )


def remote_or_destructive_actions(actions: tuple[NextAction, ...]) -> tuple[NextAction, ...]:
    """The subset that must be confirmed before execution."""
    return tuple(
        action
        for action in actions
        if action.cost == COST_REMOTE or action.impact == IMPACT_DESTRUCTIVE
    )
