"""Tests for LocatorBridgePass.

Three scenarios:
1. Full legend on page N, locator on page N+1 with unowned assets above it
   → bridge match created.
2. Locator with no matching full legend on the previous page
   → no match.
3. Locator + full legend, but assets already claimed by earlier match
   → no bridge match.
"""

from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_locator_pass import LocatorBridgePass
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger
from paperforge.worker.ocr_figure_vnext_types import ResourceRef


def test_locator_bridge_connects_full_legend_to_visual_group():
    """Full legend on page 4, locator on page 5 with unowned assets above it."""
    full_text = (
        "Figure 5. Detailed description of the experimental setup showing "
        "the differentiation protocol for mesenchymal stem cells. "
        "Cells were cultured in osteogenic medium supplemented with "
        "dexamethasone, ascorbic acid, and beta-glycerophosphate for 21 days. "
        "Osteogenic differentiation was confirmed by Alizarin Red S staining."
    )
    blocks = [
        # Full legend on page 4
        {
            "block_id": "l5",
            "page": 4,
            "role": "figure_caption",
            "text": full_text,
            "bbox": [0, 100, 500, 200],
        },
        # Assets on page 5 above locator
        {
            "block_id": "a1",
            "page": 5,
            "role": "figure_asset",
            "text": "",
            "bbox": [0, 0, 200, 80],
            "raw_label": "image",
        },
        {
            "block_id": "a2",
            "page": 5,
            "role": "figure_asset",
            "text": "",
            "bbox": [0, 85, 200, 160],
            "raw_label": "image",
        },
        # Locator on page 5
        {
            "block_id": "loc1",
            "page": 5,
            "role": "figure_caption",
            "text": "Fig. 5 (See legend on previous page.)",
            "bbox": [0, 200, 300, 230],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    # The locator must be detected
    assert len(index.locator_candidates) == 1

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = LocatorBridgePass().run(state)

    assert len(report.accepted) == 1, f"Expected 1 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 1

    match = state.matches[0]
    assert match["settlement_type"] == "previous_page_legend_locator"
    assert match["legend_block_id"] == "l5"
    assert "loc1" in match.get("bridge_block_ids", []), (
        f"bridge_block_ids should contain loc1, got {match.get('bridge_block_ids')}"
    )
    assert "previous_page_locator_match" in match.get("flags", []), (
        f"flags should contain previous_page_locator_match, got {match.get('flags')}"
    )

    matched_bids = {a["block_id"] for a in match.get("matched_assets", [])}
    assert matched_bids == {"a1", "a2"}, f"Expected assets a1,a2, got {matched_bids}"

    # confidence and evidence_rank per spec
    assert match["confidence"] == 0.5
    assert match["match_score"]["score"] == 0.5


def test_locator_bridge_skips_when_no_full_legend_on_previous_page():
    """Locator on page 5 for figure 5, but Figure 5 legend is on page 3 not page 4."""
    blocks = [
        # Figure 5 legend on page 3 (not page 4)
        {
            "block_id": "l5",
            "page": 3,
            "role": "figure_caption",
            "text": (
                "Figure 5. Detailed description of the experimental setup "
                "showing the differentiation protocol for mesenchymal stem "
                "cells cultured in osteogenic medium for twenty one days."
            ),
            "bbox": [0, 100, 500, 200],
        },
        # Asset on locator page
        {
            "block_id": "a1",
            "page": 5,
            "role": "figure_asset",
            "text": "",
            "bbox": [0, 0, 200, 80],
            "raw_label": "image",
        },
        # Locator
        {
            "block_id": "loc1",
            "page": 5,
            "role": "figure_caption",
            "text": "Fig. 5 (See legend on previous page.)",
            "bbox": [0, 200, 300, 230],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    assert len(index.locator_candidates) == 1

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = LocatorBridgePass().run(state)

    assert len(report.accepted) == 0, (
        f"Expected 0 accepted when no legend on prev page, got {len(report.accepted)}"
    )
    assert len(state.matches) == 0


def test_locator_bridge_skips_when_assets_already_owned():
    """Assets on locator page already claimed by another match."""
    full_text = (
        "Figure 5. Detailed description of the experimental setup showing "
        "the differentiation protocol for mesenchymal stem cells. "
        "Cells were cultured in osteogenic medium supplemented with "
        "dexamethasone, ascorbic acid, and beta-glycerophosphate for 21 days. "
        "Osteogenic differentiation was confirmed by Alizarin Red S staining."
    )
    blocks = [
        # Full legend on page 4
        {
            "block_id": "l5",
            "page": 4,
            "role": "figure_caption",
            "text": full_text,
            "bbox": [0, 100, 500, 200],
        },
        # Assets on locator page
        {
            "block_id": "a1",
            "page": 5,
            "role": "figure_asset",
            "text": "",
            "bbox": [0, 0, 200, 80],
            "raw_label": "image",
        },
        {
            "block_id": "a2",
            "page": 5,
            "role": "figure_asset",
            "text": "",
            "bbox": [0, 85, 200, 160],
            "raw_label": "image",
        },
        # Locator
        {
            "block_id": "loc1",
            "page": 5,
            "role": "figure_caption",
            "text": "Fig. 5 (See legend on previous page.)",
            "bbox": [0, 200, 300, 230],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)

    assert len(index.locator_candidates) == 1

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    # Pre-claim the assets so the bridge pass cannot claim them
    pre_owner = ResourceRef(kind="legend", page=4, block_id="prev_owner")
    state.ledger.claim_assets(
        [
            ResourceRef(kind="asset", page=5, block_id="a1"),
            ResourceRef(kind="asset", page=5, block_id="a2"),
        ],
        owner=pre_owner,
        reason="pre_claimed",
    )

    report = LocatorBridgePass().run(state)

    assert len(report.accepted) == 0, (
        f"Expected 0 accepted when assets pre-owned, got {len(report.accepted)}"
    )
    assert len(state.matches) == 0
