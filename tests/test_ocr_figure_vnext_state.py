"""Ownership ledger and pipeline state tests for vnext figure contracts."""

from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_types import ClaimProposal, ResourceRef
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_ledger_rejects_double_ownership_for_same_asset_and_records_conflict() -> None:
    ledger = OwnershipLedger()
    asset = ResourceRef(kind="asset", page=3, block_id="42")
    legend_a = ResourceRef(kind="legend", page=3, block_id="77", figure_no=1)
    legend_b = ResourceRef(kind="legend", page=3, block_id="78", figure_no=2)

    ledger.claim_assets([asset], owner=legend_a, reason="same_page_primary")
    conflict = ledger.try_claim_assets([asset], owner=legend_b, reason="conflicting_match")

    assert conflict is not None
    assert conflict.resource == asset
    assert conflict.current_owner == legend_a
    assert any(entry["action"] == "conflict" for entry in ledger.snapshot())


def test_pipeline_state_accept_match_records_diagnostic() -> None:
    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())
    proposal = ClaimProposal(
        pass_name="primary_same_page",
        figure_no=1,
        claim_type="match",
        legends=[ResourceRef(kind="legend", page=1, block_id="c1", figure_no=1)],
        assets=[ResourceRef(kind="asset", page=1, block_id="a1")],
        groups=[],
        confidence=0.9,
        evidence_rank=1,
        reason="same_page_primary",
        diagnostics={"evidence": ["test"]},
    )

    state.accept_match(proposal, {"figure_id": "Figure 1"})

    assert state.matches == [{"figure_id": "Figure 1"}]
    assert state.diagnostics[-1]["event"] == "match_accepted"
