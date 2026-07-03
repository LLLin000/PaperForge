"""Tests for vnext figure corpus (facts) and candidate index (hypotheses)."""

from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import (
    FigureCandidateIndex,
    FigureCorpus,
)


def test_corpus_keeps_raw_facts_and_no_candidate_groups() -> None:
    blocks = [
        {
            "block_id": "1",
            "page": 1,
            "role": "figure_caption",
            "text": "Figure 1. Caption",
        },
        {
            "block_id": "2",
            "page": 1,
            "role": "figure_asset",
            "bbox": [0, 0, 10, 10],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    assert [b["block_id"] for b in corpus.raw_legends] == ["1"]
    assert [b["block_id"] for b in corpus.raw_assets] == ["2"]
    assert corpus.page_width == 1200


def test_candidate_index_holds_derived_hypotheses_not_raw_facts() -> None:
    blocks = [
        {
            "block_id": "1",
            "page": 1,
            "role": "figure_caption",
            "text": "Figure 1. Caption",
        },
        {
            "block_id": "2",
            "page": 1,
            "role": "figure_asset",
            "bbox": [0, 0, 10, 10],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert len(index.formal_legends) == 1
    assert hasattr(index, "candidate_groups")
    assert corpus.raw_legends[0]["block_id"] == "1"
    assert index.bundle_source_legend_ids == set()


def test_rejected_legends_excluded_from_candidate_group_semantics() -> None:
    blocks = [
        {
            "block_id": "1",
            "page": 1,
            "role": "figure_caption",
            "text": "Figure 1. Caption",
            "bbox": [100, 100, 500, 120],
        },
        {
            "block_id": "2",
            "page": 1,
            "role": "figure_caption",
            "text": "",
            "bbox": [100, 130, 500, 150],
        },
        {
            "block_id": "3",
            "page": 1,
            "role": "figure_asset",
            "bbox": [100, 200, 400, 400],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    assert len(corpus.raw_legends) == 2  # both captions in raw pipeline
    index = FigureCandidateIndex.from_corpus(corpus)
    assert len(index.formal_legends) == 1  # only non-empty text
    assert len(index.rejected_legends) == 1  # empty text rejected
    assert len(index.candidate_groups) >= 1
    for group in index.candidate_groups:
        if group.get("page") == 1:
            assert group.get("page_legend_count") == 1, (
                f"Expected page_legend_count=1 (formal legends only), got {group.get('page_legend_count')}"
            )


def test_candidate_index_populates_sidecar_candidates_for_narrow_caption_page() -> None:
    """Three narrow numbered captions on one page → sidecar_candidates has that page."""
    blocks = [
        # Three narrow formal legends on page 5 — width=200, aligned at x-center=200
        {
            "block_id": "leg1",
            "page": 5,
            "role": "figure_caption",
            "text": "Figure 1. A caption",
            "bbox": [100, 100, 300, 120],
        },
        {
            "block_id": "leg2",
            "page": 5,
            "role": "figure_caption",
            "text": "Figure 2. Another caption",
            "bbox": [100, 130, 300, 150],
        },
        {
            "block_id": "leg3",
            "page": 5,
            "role": "figure_caption",
            "text": "Figure 3. Yet another caption",
            "bbox": [100, 160, 300, 180],
        },
        # One asset on page 5 so page has assets
        {
            "block_id": "ast1",
            "page": 5,
            "role": "figure_asset",
            "bbox": [0, 200, 400, 500],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert 5 in index.sidecar_candidates
    assert len(index.sidecar_candidates[5]) >= 2


def test_candidate_index_populates_bundle_source_legend_ids() -> None:
    """Three numbered legends on a page with zero assets → bundle source ids populated."""
    blocks = [
        # Three numbered legends on page 3 — no assets on page 3
        {
            "block_id": "leg1",
            "page": 3,
            "role": "figure_caption",
            "text": "Figure 1. Caption A",
            "bbox": [100, 100, 500, 120],
        },
        {
            "block_id": "leg2",
            "page": 3,
            "role": "figure_caption",
            "text": "Figure 2. Caption B",
            "bbox": [100, 130, 500, 150],
        },
        {
            "block_id": "leg3",
            "page": 3,
            "role": "figure_caption",
            "text": "Figure 3. Caption C",
            "bbox": [100, 160, 500, 180],
        },
        # Assets on other pages
        {
            "block_id": "ast1",
            "page": 4,
            "role": "figure_asset",
            "bbox": [0, 0, 400, 300],
        },
        {
            "block_id": "ast2",
            "page": 5,
            "role": "figure_asset",
            "bbox": [0, 0, 400, 300],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert len(index.bundle_source_legend_ids) >= 3


def test_candidate_index_sidecar_candidates_empty_for_wide_captions() -> None:
    """Wide captions (width > 720 on page_width=1200) → no sidecar candidates."""
    blocks = [
        # Three wide captions on page 5 — width=1000 > 720
        {
            "block_id": "leg1",
            "page": 5,
            "role": "figure_caption",
            "text": "Figure 1. Widest caption",
            "bbox": [0, 100, 1000, 120],
        },
        {
            "block_id": "leg2",
            "page": 5,
            "role": "figure_caption",
            "text": "Figure 2. Also wide",
            "bbox": [0, 130, 1000, 150],
        },
        {
            "block_id": "leg3",
            "page": 5,
            "role": "figure_caption",
            "text": "Figure 3. Still wide",
            "bbox": [0, 160, 1000, 180],
        },
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert index.sidecar_candidates == {}
