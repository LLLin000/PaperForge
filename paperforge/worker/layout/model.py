"""Data model of the read-only layout plan.

Design rules:

- Everything is derived from block geometry. The input list order is recorded
  once (`BlockRef.raw_index`) as evidence and never used for structure, so a
  shuffled input list yields the same plan.
- Block identity inside a plan is `BlockRef.uid`, assigned from a stable
  geometric sort. `(page, block_id)` repeats in real OCR output, so it cannot
  be the key.
- Coordinates are in the OCR layer's pixel space (the same space as block
  `bbox`), not PDF points.
- The model carries evidence strings and confidences, not just answers: the
  plan is meant to be reviewed, and a consumer is expected to HOLD when the
  confidence is low instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PLAN_VERSION = 1

# Region kinds
REGION_FULL_WIDTH = "full_width"
REGION_COLUMN = "column"
REGION_CONTAINER = "container"
REGION_MARGIN = "margin"  # running headers, folios, journal furniture

# Order decision relations
RELATION_BEFORE = "before"
RELATION_HOLD = "hold"

# Conflict kinds
CONFLICT_CROSS_COLUMN_JUMP = "cross_column_jump"
CONFLICT_ORDER_INVERSION = "order_inversion"
CONFLICT_OVERLAPPING_MEMBERSHIP = "overlapping_membership"
CONFLICT_CONTAINER_LEAK = "container_leak"
CONFLICT_MISSING_GEOMETRY = "missing_geometry"
CONFLICT_AMBIGUOUS_COLUMN = "ambiguous_column"

SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_HOLD = "hold"


@dataclass(frozen=True)
class BlockRef:
    """One OCR block, reduced to what layout reasoning needs."""

    uid: str
    page: int
    block_id: str
    bbox: tuple[float, float, float, float] | None
    raw_index: int
    role: str | None
    text_len: int
    page_width: float
    page_height: float

    @property
    def is_wide(self) -> bool:
        if self.bbox is None or self.page_width <= 0:
            return False
        return (self.bbox[2] - self.bbox[0]) >= self.page_width * 0.75

    @property
    def center_x(self) -> float | None:
        if self.bbox is None:
            return None
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def center_y(self) -> float | None:
        if self.bbox is None:
            return None
        return (self.bbox[1] + self.bbox[3]) / 2


@dataclass(frozen=True)
class Region:
    """A spatial region on one page.

    `kind` is one of `full_width`, `column`, `container`. `members` holds
    `BlockRef.uid` values in reading order inside the region. `parent_id`
    points at the enclosing region for container members, so a container's
    member blocks are not double-owned by a column.
    """

    region_id: str
    page: int
    kind: str
    x_left: float
    x_right: float
    y_top: float
    y_bottom: float
    members: tuple[str, ...]
    parent_id: str | None
    confidence: float
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class OrderDecision:
    """One pairwise statement about reading order."""

    before: str
    after: str
    relation: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class Conflict:
    """A detected layout inconsistency. `severity == hold` means unresolved."""

    conflict_id: str
    page: int
    kind: str
    severity: str
    blocks: tuple[str, ...]
    detail: str


@dataclass
class PagePlan:
    page: int
    width: float
    height: float
    regions: list[Region] = field(default_factory=list)
    order: list[str] = field(default_factory=list)
    holds: list[str] = field(default_factory=list)
    decisions: list[OrderDecision] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)


@dataclass
class LayoutPlan:
    version: int = PLAN_VERSION
    pages: list[PagePlan] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def region_by_id(self, region_id: str) -> Region | None:
        for page in self.pages:
            for region in page.regions:
                if region.region_id == region_id:
                    return region
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "stats": self.stats,
            "pages": [
                {
                    "page": page.page,
                    "width": page.width,
                    "height": page.height,
                    "regions": [
                        {
                            "region_id": region.region_id,
                            "page": region.page,
                            "kind": region.kind,
                            "x_left": region.x_left,
                            "x_right": region.x_right,
                            "y_top": region.y_top,
                            "y_bottom": region.y_bottom,
                            "members": list(region.members),
                            "parent_id": region.parent_id,
                            "confidence": region.confidence,
                            "evidence": list(region.evidence),
                        }
                        for region in page.regions
                    ],
                    "order": list(page.order),
                    "holds": list(page.holds),
                    "decisions": [
                        {
                            "before": decision.before,
                            "after": decision.after,
                            "relation": decision.relation,
                            "confidence": decision.confidence,
                            "reason": decision.reason,
                        }
                        for decision in page.decisions
                    ],
                    "conflicts": [
                        {
                            "conflict_id": conflict.conflict_id,
                            "page": conflict.page,
                            "kind": conflict.kind,
                            "severity": conflict.severity,
                            "blocks": list(conflict.blocks),
                            "detail": conflict.detail,
                        }
                        for conflict in page.conflicts
                    ],
                }
                for page in self.pages
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LayoutPlan:
        pages: list[PagePlan] = []
        for raw_page in payload.get("pages", []):
            pages.append(
                PagePlan(
                    page=int(raw_page.get("page", 0)),
                    width=float(raw_page.get("width", 0.0)),
                    height=float(raw_page.get("height", 0.0)),
                    regions=[
                        Region(
                            region_id=raw_region["region_id"],
                            page=int(raw_region.get("page", 0)),
                            kind=raw_region["kind"],
                            x_left=float(raw_region.get("x_left", 0.0)),
                            x_right=float(raw_region.get("x_right", 0.0)),
                            y_top=float(raw_region.get("y_top", 0.0)),
                            y_bottom=float(raw_region.get("y_bottom", 0.0)),
                            members=tuple(raw_region.get("members", ())),
                            parent_id=raw_region.get("parent_id"),
                            confidence=float(raw_region.get("confidence", 0.0)),
                            evidence=tuple(raw_region.get("evidence", ())),
                        )
                        for raw_region in raw_page.get("regions", [])
                    ],
                    order=list(raw_page.get("order", [])),
                    holds=list(raw_page.get("holds", [])),
                    decisions=[
                        OrderDecision(
                            before=raw_decision["before"],
                            after=raw_decision["after"],
                            relation=raw_decision["relation"],
                            confidence=float(raw_decision.get("confidence", 0.0)),
                            reason=raw_decision.get("reason", ""),
                        )
                        for raw_decision in raw_page.get("decisions", [])
                    ],
                    conflicts=[
                        Conflict(
                            conflict_id=raw_conflict["conflict_id"],
                            page=int(raw_conflict.get("page", 0)),
                            kind=raw_conflict["kind"],
                            severity=raw_conflict.get("severity", SEVERITY_WARN),
                            blocks=tuple(raw_conflict.get("blocks", ())),
                            detail=raw_conflict.get("detail", ""),
                        )
                        for raw_conflict in raw_page.get("conflicts", [])
                    ],
                )
            )
        return cls(
            version=int(payload.get("version", PLAN_VERSION)),
            pages=pages,
            stats=dict(payload.get("stats", {})),
        )
