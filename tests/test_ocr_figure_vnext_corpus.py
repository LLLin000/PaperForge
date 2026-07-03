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
