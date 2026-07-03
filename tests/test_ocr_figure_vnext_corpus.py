from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus


def test_corpus_keeps_raw_facts_and_no_candidate_groups():
    blocks = [
        {"block_id": "1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption"},
        {"block_id": "2", "page": 1, "role": "figure_asset", "bbox": [0, 0, 10, 10]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    assert [b["block_id"] for b in corpus.raw_legends] == ["1"]
    assert [b["block_id"] for b in corpus.raw_assets] == ["2"]
    assert corpus.page_width == 1200


def test_candidate_index_holds_derived_hypotheses_not_raw_facts():
    blocks = [
        {"block_id": "1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption"},
        {"block_id": "2", "page": 1, "role": "figure_asset", "bbox": [0, 0, 10, 10]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert len(index.formal_legends) == 1
    assert hasattr(index, "candidate_groups")
    assert corpus.raw_legends[0]["block_id"] == "1"
    assert index.bundle_source_legend_ids == set()
