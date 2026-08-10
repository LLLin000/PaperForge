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
class ActionContext:
    vault: Path
    config: dict[str, object]  # resolved vault config values (C0 seam)
    paths: dict[str, Path]  # resolved canonical paths (C0 seam)


@dataclass(frozen=True)
class PreflightResult:
    availability: Availability
    availability_reason_code: str
    availability_reason: str
    preservation_facts: tuple[str, ...] = ()
    replacement_facts: tuple[str, ...] = ()


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
