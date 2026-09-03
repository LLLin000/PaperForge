"""Action registry types (#163 / T2, #145 §4)."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

from paperforge.core.result import PFResult

ACTION_ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")

Cost = Literal["local", "remote_possible"]
Impact = Literal["read_only", "mutating", "destructive"]
Confirmation = Literal["none", "required"]
Availability = Literal["available", "unavailable", "busy"]
Applicability = Literal["needed", "noop", "blocked", "not_applicable"]
ExecutionMode = Literal["result", "stream"]


@dataclass(frozen=True)
class AllScope:
    kind: Literal["all"] = "all"


@dataclass(frozen=True)
class PapersScope:
    keys: tuple[str, ...]
    kind: Literal["papers"] = "papers"

    def normalized(self) -> "PapersScope":
        """Deduplicated, stable-sorted keys — the dedupe identity form."""
        return PapersScope(tuple(sorted(set(self.keys))))


ActionScope = Union[AllScope, PapersScope]


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    scope: ActionScope


@dataclass(frozen=True)
class ActionExecutionHooks:
    """Runtime-only mechanics supplied by the streaming transport."""

    is_stopped: Callable[[], bool] | None = None
    phase: Callable[[str], None] | None = None
    progress: Callable[[int, int | None, str | None], None] | None = None
    item_result: Callable[[str, str], None] | None = None


@dataclass(frozen=True)
class ActionContext:
    vault: Path
    config: dict[str, object]  # resolved vault config values (C0 seam)
    paths: dict[str, Path]  # resolved canonical paths (C0 seam)
    execution_hooks: ActionExecutionHooks | None = None

@dataclass(frozen=True)
class PaperPreflight:
    """M2 (Control Plane Closure): per-paper applicability projection.

    Strictly orthogonal to Availability: availability asks 'can the system
    run this action NOW'; applicability asks 'for THIS paper's current
    state, SHOULD it run'.  Projected from observation/frontier truth
    (probe lineage + reconcile), never a second materialization judgment.
    """

    key: str
    applicability: Applicability
    reason_code: str
    reason: str
    recommended_action_id: str | None = None
    execution_id: str | None = None


@dataclass(frozen=True)
class PreflightResult:
    availability: Availability
    availability_reason_code: str
    availability_reason: str
    per_key: tuple[PaperPreflight, ...] = ()
    preservation_facts: tuple[str, ...] = ()
    replacement_facts: tuple[str, ...] = ()

    def summary(self) -> dict[str, int]:
        """Per-paper applicability counts — DERIVED from per_key, never a
        second truth.  Empty per_key (all-scope action) → empty summary."""
        counts: dict[str, int] = {"needed": 0, "noop": 0, "blocked": 0, "not_applicable": 0}
        for p in self.per_key:
            counts[p.applicability] = counts.get(p.applicability, 0) + 1
        return counts


@dataclass(frozen=True)
class ActionIntent:
    """Emission-time intent — WHY the action was suggested.  Carries no
    effect facts; availability and effects come from preflight at run time
    (#145 §3.3)."""

    action_id: str
    scope: ActionScope
    trigger_reason_code: str
    trigger_reason: str


ActionHandler = Callable[[ActionContext, ActionRequest], PFResult]
ActionPreflight = Callable[[ActionContext, ActionRequest], PreflightResult]


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    label_code: str
    description_code: str
    handler: ActionHandler
    preflight: ActionPreflight
    scope_kinds: tuple[str, ...]
    cost: Cost
    impact: Impact
    confirmation: Confirmation
    automatic: bool
    interruptible: bool
    execution_mode: ExecutionMode = "result"


def scope_to_dict(scope: ActionScope) -> dict[str, object]:
    out: dict[str, object] = {"kind": scope.kind}
    if scope.kind == "papers":
        out["keys"] = list(scope.keys)
    return out


def scope_from_dict(data: dict[str, object]) -> ActionScope:
    kind = data.get("kind")
    if kind == "all":
        return AllScope()
    if kind == "papers":
        keys = tuple(str(k) for k in data.get("keys", []))
        return PapersScope(keys)
    raise ValueError(f"unknown scope kind: {kind!r}")


def require_action_id(action_id: str) -> None:
    """Registry identifier contract; raises ValueError on violation."""
    if not ACTION_ID_RE.fullmatch(action_id):
        raise ValueError(f"invalid action id: {action_id!r}")


def validate_action_id(action_id: str) -> bool:
    try:
        require_action_id(action_id)
        return True
    except ValueError:
        return False
