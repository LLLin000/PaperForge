"""Reservation contract tests for vnext cross-page figure pipeline."""

from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_types import ClaimProposal, ResourceRef
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_ledger_can_reserve_group_without_claiming_assets() -> None:
    ledger = OwnershipLedger()
    group = ResourceRef(kind="group", page=2, block_id=None, group_id="g2")

    ledger.reserve_group(group, reason="cross_page_candidate")

    assert ledger.can_claim_group(group) is False
    assert any(entry["action"] == "reserve_group" for entry in ledger.snapshot())


def test_pipeline_state_accept_reservation_records_diagnostic() -> None:
    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())
    proposal = ClaimProposal(
        pass_name="cross_page_reservation",
        figure_no=4,
        claim_type="reserve",
        legends=[ResourceRef(kind="legend", page=1, block_id="l1", figure_no=4)],
        assets=[],
        groups=[ResourceRef(kind="group", page=2, block_id=None, group_id="g2")],
        confidence=0.7,
        evidence_rank=2,
        reason="forward_cross_page_candidate",
        diagnostics={"evidence": ["page_gap"]},
    )

    state.accept_reservation(proposal)

    assert state.diagnostics[-1]["event"] == "reservation_accepted"
