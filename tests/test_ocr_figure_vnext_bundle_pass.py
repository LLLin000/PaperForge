from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_bundle_pass import LegendBundlePass
from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_legend_bundle_pass_matches_captions_to_subsequent_asset_pages():
    """Page 3 has 3 captions (Figure 1/2/3) and zero assets;
    pages 4/5/6 each have 1 unclaimed asset, no body/table blocks."""
    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. Caption one", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 3, "role": "figure_caption",
         "text": "Figure 2. Caption two", "bbox": [0, 160, 200, 210]},
        {"block_id": "c3", "page": 3, "role": "figure_caption",
         "text": "Figure 3. Caption three", "bbox": [0, 220, 200, 270]},
        # Pages 4, 5, 6: each one asset, no body/table blocks
        {"block_id": "a1", "page": 4, "role": "figure_asset",
         "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "a3", "page": 6, "role": "figure_asset",
         "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "f1", "page": 1, "role": "paper_title",
         "text": "A paper", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = LegendBundlePass().run(state)

    assert len(report.accepted) == 3, f"expected 3 accepted, got {len(report.accepted)}"
    for proposal in report.accepted:
        assert proposal.claim_type == "match"
        assert proposal.confidence == 0.3
        assert proposal.evidence_rank == 4

    assert len(state.matches) == 3
    for m in state.matches:
        assert m["settlement_type"] == "legend_bundle"
        assert "legend_bundle_match" in m["flags"]

    # Captions matched to pages 4, 5, 6 in order
    match_pages = [m["page"] for m in state.matches]
    assert match_pages == [4, 5, 6], f"expected [4, 5, 6], got {match_pages}"

    # Each match has the correct figure number
    figure_numbers = [m["figure_number"] for m in state.matches]
    assert figure_numbers == [1, 2, 3], f"expected [1, 2, 3], got {figure_numbers}"


def test_legend_bundle_pass_requires_minimum_three_captions():
    """Page with only 2 captions should not trigger bundle matching."""
    blocks = [
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. Caption one", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 3, "role": "figure_caption",
         "text": "Figure 2. Caption two", "bbox": [0, 160, 200, 210]},
        {"block_id": "a1", "page": 4, "role": "figure_asset",
         "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "f1", "page": 1, "role": "paper_title",
         "text": "A paper", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = LegendBundlePass().run(state)

    assert len(report.accepted) == 0, f"expected 0 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 0, f"expected 0 matches, got {len(state.matches)}"


def test_legend_bundle_pass_skips_when_intervening_pages_have_body_text():
    """Captions on page 3, assets on page 5, but page 4 has body_paragraph blocks.
    Bundle matching should be blocked by intervening body text."""
    blocks = [
        # Page 3: three captions, no assets
        {"block_id": "c1", "page": 3, "role": "figure_caption",
         "text": "Figure 1. Caption one", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 3, "role": "figure_caption",
         "text": "Figure 2. Caption two", "bbox": [0, 160, 200, 210]},
        {"block_id": "c3", "page": 3, "role": "figure_caption",
         "text": "Figure 3. Caption three", "bbox": [0, 220, 200, 270]},
        # Assets on page 5 (enough for 3 captions)
        {"block_id": "a1", "page": 5, "role": "figure_asset",
         "bbox": [0, 0, 200, 90], "raw_label": "image"},
        {"block_id": "a2", "page": 5, "role": "figure_asset",
         "bbox": [0, 100, 200, 180], "raw_label": "image"},
        {"block_id": "a3", "page": 5, "role": "figure_asset",
         "bbox": [0, 200, 200, 280], "raw_label": "image"},
        # Intervening page 4 has body_paragraph
        {"block_id": "b1", "page": 4, "role": "body_paragraph",
         "text": "Body text here that blocks bundle matching.",
         "bbox": [0, 0, 500, 50]},
        {"block_id": "f1", "page": 1, "role": "paper_title",
         "text": "A paper", "bbox": [0, 0, 500, 50]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = LegendBundlePass().run(state)

    assert len(report.accepted) == 0, f"expected 0 accepted, got {len(report.accepted)}"
    assert len(state.matches) == 0, f"expected 0 matches, got {len(state.matches)}"
