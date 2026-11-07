"""Production acceptance gate for the read-only layout plan (Phase C0).

The plan explains a page. This module decides whether a *consumer* may use that
explanation instead of the current OCR order — and it says no by default.

Contract
--------
`assess_page(plan, page, blocks, *, min_confidence=0.85) -> PageAcceptance`

- `status`: `ACCEPT` | `HOLD` | `REJECT`.
- `accepted_order`: uid sequence, only when `status == ACCEPT`.
- `fallback_reason`: one machine-readable reason (`REJECT`/`HOLD`) or `None`.
- `source_mapping`: uid → index in the passed `blocks` list, verified against
  the plan's fingerprint of that block.
- `held_blocks`: uids whose position must not be taken from the plan.
- `evidence`: counts and thresholds the decision used.

Rules
-----
`REJECT` (the plan cannot describe this input at all):
- plan version unknown;
- the uid set does not match the blocks passed in;
- a uid has no fingerprint in the plan, or its fingerprint differs from the
  block at `source_mapping[uid]` (block inserted/removed/edited after planning);
- a block is claimed by two regions.

`HOLD` (the plan describes the page, but not confidently enough to take over):
- any `hold`-severity conflict on the page (gutter block, missing geometry,
  overlapping membership, container leak);
- any decision in the body path that is `hold`, or `before` below
  `min_confidence`;
- any block outside the margin regions that has no decision touching it.

`ACCEPT` otherwise: every body decision is `before` with confidence at least
`min_confidence` (default 0.80 — same-region and band-boundary evidence; a
0.70 column hand-off is exactly the uncertain part), and no conflict claims
uncertainty.

Margins are page furniture: they are excluded from the acceptance threshold
but kept at the end of `accepted_order`, so a consumer that applies the order
does not lose them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import (
    CONFLICT_AMBIGUOUS_COLUMN,
    CONFLICT_CONTAINER_LEAK,
    CONFLICT_MISSING_GEOMETRY,
    CONFLICT_OVERLAPPING_MEMBERSHIP,
    PLAN_VERSION,
    REGION_MARGIN,
    RELATION_BEFORE,
    RELATION_HOLD,
    SEVERITY_HOLD,
    LayoutPlan,
    PagePlan,
)
from .plan import collect_block_refs

STATUS_ACCEPT = "ACCEPT"
STATUS_HOLD = "HOLD"
STATUS_REJECT = "REJECT"

DEFAULT_MIN_CONFIDENCE = 0.80

# Conflicts that make the page's order untrustworthy, whatever their severity.
_ORDER_BLOCKING_CONFLICTS = frozenset(
    {
        CONFLICT_AMBIGUOUS_COLUMN,
        CONFLICT_MISSING_GEOMETRY,
        CONFLICT_OVERLAPPING_MEMBERSHIP,
        CONFLICT_CONTAINER_LEAK,
    }
)


@dataclass
class PageAcceptance:
    page: int
    status: str
    accepted_order: list[str] | None = None
    fallback_reason: str | None = None
    source_mapping: dict[str, int] = field(default_factory=dict)
    held_blocks: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.status == STATUS_ACCEPT

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "status": self.status,
            "accepted_order": list(self.accepted_order) if self.accepted_order is not None else None,
            "fallback_reason": self.fallback_reason,
            "source_mapping": dict(sorted(self.source_mapping.items())),
            "held_blocks": list(self.held_blocks),
            "evidence": self.evidence,
        }


def _uid_regions(page: PagePlan) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for region in page.regions:
        for uid in region.members:
            owners.setdefault(uid, []).append(region.region_id)
    return owners


def assess_page(
    plan: LayoutPlan,
    page: PagePlan,
    blocks: list[dict[str, Any]],
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> PageAcceptance:
    """Decide whether `page`'s plan order may replace the current order."""
    evidence: dict[str, Any] = {"min_confidence": min_confidence, "plan_version": plan.version}

    if plan.version != PLAN_VERSION:
        return PageAcceptance(page.page, STATUS_REJECT, fallback_reason="unknown_plan_version", evidence=evidence)

    refs = collect_block_refs(blocks)
    refs_on_page = [ref for ref in refs if ref.page == page.page]
    expected = {ref.uid: ref for ref in refs_on_page}
    planned = set(page.order) | {uid for region in page.regions for uid in region.members}
    evidence["blocks"] = len(expected)
    evidence["planned_uids"] = len(planned)

    if not expected:
        return PageAcceptance(page.page, STATUS_REJECT, fallback_reason="page_not_in_input", evidence=evidence)
    if planned != set(expected):
        evidence["unexpected_uids"] = len(planned - set(expected))
        evidence["missing_uids"] = len(set(expected) - planned)
        return PageAcceptance(page.page, STATUS_REJECT, fallback_reason="uid_set_mismatch", evidence=evidence)

    # Coverage as a set is not enough: `order` is what a consumer applies, so it
    # must be a strict permutation of the page's blocks — one entry each.
    if (
        len(page.order) != len(expected)
        or len(set(page.order)) != len(expected)
        or set(page.order) != set(expected)
    ):
        evidence["order_length"] = len(page.order)
        evidence["order_unique"] = len(set(page.order))
        return PageAcceptance(
            page.page, STATUS_REJECT, fallback_reason="order_not_a_permutation", evidence=evidence
        )

    owners = _uid_regions(page)
    duplicated = sorted(uid for uid, regions in owners.items() if len(regions) > 1)
    if duplicated:
        evidence["duplicated_uids"] = duplicated[:5]
        return PageAcceptance(page.page, STATUS_REJECT, fallback_reason="duplicate_membership", evidence=evidence)

    mapping: dict[str, int] = {}
    for uid, ref in expected.items():
        if ref.raw_index >= len(blocks):
            return PageAcceptance(
                page.page, STATUS_REJECT, fallback_reason="source_index_out_of_range", evidence=evidence
            )
        stored = plan.identities.get(uid)
        if not stored:
            return PageAcceptance(page.page, STATUS_REJECT, fallback_reason="missing_identity", evidence=evidence)
        if stored != ref.fingerprint:
            evidence["identity_mismatch_uid"] = uid
            return PageAcceptance(page.page, STATUS_REJECT, fallback_reason="identity_mismatch", evidence=evidence)
        mapping[uid] = ref.raw_index

    # ---- HOLD conditions ----
    held: list[str] = list(page.holds)

    blocking_conflicts = [
        conflict
        for conflict in page.conflicts
        if conflict.kind in _ORDER_BLOCKING_CONFLICTS or conflict.severity == SEVERITY_HOLD
    ]
    for conflict in blocking_conflicts:
        held.extend(uid for uid in conflict.blocks if uid not in held)
    evidence["blocking_conflicts"] = sorted({conflict.kind for conflict in blocking_conflicts})

    margin_uids = {uid for region in page.regions if region.kind == REGION_MARGIN for uid in region.members}
    low_confidence_pairs = 0
    hold_pairs = 0
    body_decisions = 0
    decided: set[str] = set()
    for decision in page.decisions:
        decided.update((decision.before, decision.after))
        if decision.before in margin_uids or decision.after in margin_uids:
            continue
        body_decisions += 1
        if decision.relation == RELATION_HOLD:
            hold_pairs += 1
            for uid in (decision.before, decision.after):
                if uid not in held:
                    held.append(uid)
        elif decision.relation == RELATION_BEFORE and decision.confidence < min_confidence:
            low_confidence_pairs += 1
            for uid in (decision.before, decision.after):
                if uid not in held:
                    held.append(uid)

    undecided = sorted(uid for uid in expected if uid not in decided and uid not in margin_uids)
    evidence.update(
        {
            "body_decisions": body_decisions,
            "hold_pairs": hold_pairs,
            "low_confidence_pairs": low_confidence_pairs,
            "margin_blocks": len(margin_uids),
            "undecided_blocks": len(undecided),
        }
    )
    held.extend(uid for uid in undecided if uid not in held)

    if blocking_conflicts:
        reason = "hold_conflict"
    elif hold_pairs:
        reason = "hold_decision"
    elif low_confidence_pairs:
        reason = "low_confidence"
    elif undecided:
        reason = "undecided_blocks"
    else:
        reason = None

    if reason:
        return PageAcceptance(
            page.page,
            STATUS_HOLD,
            fallback_reason=reason,
            source_mapping=mapping,
            held_blocks=held,
            evidence=evidence,
        )

    return PageAcceptance(
        page.page,
        STATUS_ACCEPT,
        accepted_order=list(page.order),
        source_mapping=mapping,
        evidence=evidence,
    )


def assess_plan(
    plan: LayoutPlan,
    blocks: list[dict[str, Any]],
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> list[PageAcceptance]:
    """Assess every page of `plan` against the blocks it is meant to reorder."""
    return [assess_page(plan, page, blocks, min_confidence=min_confidence) for page in plan.pages]
