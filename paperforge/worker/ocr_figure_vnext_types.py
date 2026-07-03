from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ResourceRef:
    kind: Literal["legend", "asset", "group"]
    page: int | None
    block_id: str | None
    group_id: str | None = None
    figure_no: int | None = field(default=None, compare=False)
    origin: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if self.page is not None:
            object.__setattr__(self, "page", int(self.page))
        if self.block_id is not None:
            object.__setattr__(self, "block_id", str(self.block_id))
        if self.group_id is not None:
            object.__setattr__(self, "group_id", str(self.group_id))

        if self.kind == "asset" and (self.page is None or self.block_id is None):
            raise ValueError("asset ResourceRef requires page + block_id")
        if self.kind == "legend" and (self.page is None or self.block_id is None):
            raise ValueError("legend ResourceRef requires page + block_id")
        if self.kind == "group" and (self.page is None or self.group_id is None):
            raise ValueError("group ResourceRef requires page + group_id")


@dataclass(frozen=True)
class OwnershipConflict:
    resource: ResourceRef
    current_owner: ResourceRef | None
    attempted_owner: ResourceRef | None
    reason: str


@dataclass
class ClaimProposal:
    pass_name: str
    figure_no: int | None
    claim_type: Literal["match", "reserve", "block", "unresolved_cluster", "composite_parent"]
    legends: list[ResourceRef]
    assets: list[ResourceRef]
    groups: list[ResourceRef]
    confidence: float
    evidence_rank: int
    reason: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PassReport:
    pass_name: str
    proposals: list[ClaimProposal] = field(default_factory=list)
    accepted: list[ClaimProposal] = field(default_factory=list)
    rejected: list[ClaimProposal] = field(default_factory=list)
    conflicts: list[OwnershipConflict] = field(default_factory=list)
    invariant_errors: list[str] = field(default_factory=list)
