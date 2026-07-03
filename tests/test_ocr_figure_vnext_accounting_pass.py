from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_accounting_pass import FinalAccountingPass
from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger
from paperforge.worker.ocr_figure_vnext_types import ResourceRef


def _make_state(blocks, matches=None, unmatched_ids=None):
    """Build a FigurePipelineState with optional pre-populated matches."""
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    ledger = OwnershipLedger()
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=ledger)
    if matches:
        state.matches.extend(matches)
    if unmatched_ids:
        for uid in unmatched_ids:
            state.unresolved.append({"legend_block_id": uid})
    return state


def test_final_accounting_pass_all_matched():
    """All numbered legends matched => gap_count=0, no invariant_errors."""
    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. First caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 3, "role": "figure_caption",
         "text": "Figure 2. Second caption", "bbox": [0, 160, 200, 210]},
        {"block_id": "a1", "page": 3, "role": "figure_asset",
         "bbox": [0, 0, 200, 80]},
        {"block_id": "a2", "page": 3, "role": "figure_asset",
         "bbox": [0, 0, 200, 80]},
    ]
    matches = [
        {
            "legend_block_id": "c1",
            "page": 3,
            "asset_block_ids": ["a1"],
            "figure_number": 1,
            "figure_id": "figure_001",
            "text": "Figure 1. First caption",
        },
        {
            "legend_block_id": "c2",
            "page": 3,
            "asset_block_ids": ["a2"],
            "figure_number": 2,
            "figure_id": "figure_002",
            "text": "Figure 2. Second caption",
        },
    ]
    state = _make_state(blocks, matches=matches)

    # Claim assets in ledger so invariants pass
    state.ledger.claim_assets(
        [ResourceRef(kind="asset", page=3, block_id="a1")],
        owner=ResourceRef(kind="legend", page=3, block_id="c1"),
        reason="match",
    )
    state.ledger.claim_assets(
        [ResourceRef(kind="asset", page=3, block_id="a2")],
        owner=ResourceRef(kind="legend", page=3, block_id="c2"),
        reason="match",
    )

    report = FinalAccountingPass().run(state)

    assert state.completeness["total_numbered_legends"] == 2
    assert state.completeness["accounted_for"] == 2
    assert state.completeness["gap_count"] == 0
    assert len(state.completeness["details"]) == 2
    for d in state.completeness["details"]:
        assert d["status"] == "matched"
    assert len(report.invariant_errors) == 0


def test_final_accounting_pass_gap_detected():
    """One numbered legend absent from matches and unresolved => gap_count=1."""
    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. First caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 3, "role": "figure_caption",
         "text": "Figure 2. Second caption", "bbox": [0, 160, 200, 210]},
        {"block_id": "a1", "page": 3, "role": "figure_asset",
         "bbox": [0, 0, 200, 80]},
    ]
    # Only c1 is matched; c2 is neither matched nor in unresolved => gap
    matches = [
        {
            "legend_block_id": "c1",
            "page": 3,
            "asset_block_ids": ["a1"],
            "figure_number": 1,
            "figure_id": "figure_001",
            "text": "Figure 1. First caption",
        },
    ]
    state = _make_state(blocks, matches=matches)
    state.ledger.claim_assets(
        [ResourceRef(kind="asset", page=3, block_id="a1")],
        owner=ResourceRef(kind="legend", page=3, block_id="c1"),
        reason="match",
    )

    report = FinalAccountingPass().run(state)

    assert state.completeness["total_numbered_legends"] == 2
    assert state.completeness["accounted_for"] == 1  # only c1 matched
    assert state.completeness["gap_count"] == 1       # c2 is a gap
    details = state.completeness["details"]
    c1_detail = next(d for d in details if d["legend_block_id"] == "c1")
    c2_detail = next(d for d in details if d["legend_block_id"] == "c2")
    assert c1_detail["status"] == "matched"
    assert c2_detail["status"] == "gap"
    assert len(report.invariant_errors) == 0


def test_final_accounting_pass_invariant_violation():
    """Matched figure references an asset not owned in ledger => invariant_errors."""
    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. First caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 3, "role": "figure_asset",
         "bbox": [0, 0, 200, 80]},
    ]
    matches = [
        {
            "legend_block_id": "c1",
            "page": 3,
            "asset_block_ids": ["a1"],
            "figure_number": 1,
            "figure_id": "figure_001",
            "text": "Figure 1. First caption",
        },
    ]
    state = _make_state(blocks, matches=matches)
    # Deliberately do NOT claim a1 in the ledger => invariant violation

    report = FinalAccountingPass().run(state)

    assert len(report.invariant_errors) >= 1
    messages = " ".join(report.invariant_errors).lower()
    assert "a1" in messages
    assert "owned" in messages or "owner" in messages
