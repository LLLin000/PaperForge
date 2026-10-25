"""Wire DTOs for the next_actions v1 contract (#127).

The ONLY policy/scope/confirmation authority is
`paperforge.actions.registry` (ACTION_REGISTRY + NON_REGISTRY_ACTIONS +
classify_action_id + validate_registry/validate_action_vocabulary). Nothing
in this module decides which ids exist, what they cost, or whether they need
confirmation; producers and validators must not import policy from here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

NEXT_ACTIONS_SCHEMA_VERSION = 1


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
