"""Read-only document layout plan.

Phase B of the OCR post-processing upgrade. The plan explains the spatial
structure of each page (regions, containers, reading order) without touching
the production OCR output: nothing here writes artifacts, mutates blocks, or
decides final roles.

The contract lives in :mod:`paperforge.worker.layout.model`; the entry point is
:func:`paperforge.worker.layout.plan.build_layout_plan`.
"""

from .acceptance import PageAcceptance, assess_page, assess_plan
from .model import (
    BlockRef,
    Conflict,
    LayoutPlan,
    OrderDecision,
    PagePlan,
    Region,
)
from .plan import build_layout_plan, collect_block_refs

__all__ = [
    "BlockRef",
    "Conflict",
    "LayoutPlan",
    "OrderDecision",
    "PagePlan",
    "Region",
    "build_layout_plan",
    "collect_block_refs",
    "PageAcceptance",
    "assess_page",
    "assess_plan",
]
