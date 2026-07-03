from __future__ import annotations

from paperforge.worker.ocr_figure_vnext_composite_pass import CompositeParentPass
from paperforge.worker.ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def _cgroup(group_id: str, page: int, *asset_ids: str) -> dict:
    """Build a synthetic candidate group dict."""
    return {
        "group_id": group_id,
        "page": page,
        "asset_block_ids": list(asset_ids),
        "media_blocks": [{"block_id": aid} for aid in asset_ids],
        "group_type": "multi_asset" if len(asset_ids) > 1 else "single_asset",
        "cluster_bbox": [0, 0, 100, 100],
    }


def _composite_parent(
    group_id: str, page: int, child_group_ids: list[str], confidence: float = 0.85,
    subtype: str = "composite",
) -> dict:
    """Build a synthetic composite parent candidate dict."""
    return {
        "group_id": group_id,
        "page": page,
        "child_group_ids": list(child_group_ids),
        "asset_block_ids": [],
        "cluster_bbox": [0, 0, 200, 200],
        "parent_confidence": confidence,
        "parent_subtype": subtype,
    }


def _make_index(
    legends: list[dict],
    candidate_groups: list[dict],
    composite_parents: list[dict],
    *,
    page_width: float = 1200,
) -> tuple[FigureCorpus, FigureCandidateIndex]:
    """Build a FigureCorpus + FigureCandidateIndex from synthetic data.

    Assets are auto-extracted from blocks that have role="figure_asset".
    """
    assets = [
        b for b in legends if b.get("role") == "figure_asset"
    ]
    blocks = list(legends)
    for g in candidate_groups:
        for aid in g.get("asset_block_ids", []):
            if not any(b.get("block_id") == aid for b in blocks):
                blocks.append({
                    "block_id": aid,
                    "page": g.get("page", 1),
                    "role": "figure_asset",
                    "bbox": [0, 0, 100, 100],
                })
    formal_legends = [b for b in legends if b.get("role") in {"figure_caption", "figure_caption_candidate"}]
    corpus = FigureCorpus.from_blocks(blocks, page_width=page_width)
    index = FigureCandidateIndex(
        formal_legends=formal_legends,
        held_legends=[],
        rejected_legends=[b for b in legends if b not in formal_legends],
        deduped_legends=formal_legends,
        candidate_groups=candidate_groups,
        competing_caption_pages={
            int(b.get("page")) for b in formal_legends
            if b.get("page") is not None
        },
        sidecar_candidates={},
        bundle_source_legend_ids=set(),
        locator_candidates=[],
        composite_parent_candidates=composite_parents,
    )
    return corpus, index


def test_composite_parent_happy_path():
    """2x2 grid of assets + 1 numbered caption on same page -> composite parent match."""
    legends = [
        {"block_id": "c1", "page": 1, "role": "figure_caption",
         "text": "Figure 1. Caption", "bbox": [0, 500, 300, 550]},
    ]
    candidate_groups = [
        _cgroup("g1", 1, "a1", "a2"),
        _cgroup("g2", 1, "a3", "a4"),
    ]
    composite_parents = [
        _composite_parent("cp1", 1, ["g1", "g2"], confidence=0.85),
    ]
    corpus, index = _make_index(legends, candidate_groups, composite_parents)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = CompositeParentPass().run(state)

    assert len(report.accepted) == 1, "expected one accepted proposal"
    assert report.accepted[0].claim_type == "composite_parent"
    assert len(state.matches) == 1
    match = state.matches[0]
    assert match["settlement_type"] == "composite_parent"
    assert match["flags"] == ["composite_parent_match"]
    assert match["figure_number"] == 1
    assert set(match["asset_block_ids"]) == {"a1", "a2", "a3", "a4"}
    assert match["confidence"] == 0.85


def test_composite_parent_competing_captions_skipped():
    """Two numbered legends on same page -> competing caption veto -> no match."""
    legends = [
        {"block_id": "c1", "page": 1, "role": "figure_caption",
         "text": "Figure 1. First", "bbox": [0, 500, 300, 550]},
        {"block_id": "c2", "page": 1, "role": "figure_caption",
         "text": "Figure 2. Second", "bbox": [0, 560, 300, 610]},
    ]
    candidate_groups = [
        _cgroup("g1", 1, "a1", "a2"),
        _cgroup("g2", 1, "a3", "a4"),
    ]
    composite_parents = [
        _composite_parent("cp1", 1, ["g1", "g2"], confidence=0.85),
    ]
    corpus, index = _make_index(legends, candidate_groups, composite_parents)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = CompositeParentPass().run(state)

    assert len(report.accepted) == 0, "expected no accepted with competing captions"
    assert len(state.matches) == 0


def test_composite_parent_insufficient_child_groups_skipped():
    """Composite parent with only 1 child group and not dense_composite -> skip."""
    legends = [
        {"block_id": "c1", "page": 1, "role": "figure_caption",
         "text": "Figure 1. Caption", "bbox": [0, 500, 300, 550]},
    ]
    candidate_groups = [
        _cgroup("g1", 1, "a1", "a2"),
    ]
    composite_parents = [
        _composite_parent("cp1", 1, ["g1"], confidence=0.85, subtype="composite"),
    ]
    corpus, index = _make_index(legends, candidate_groups, composite_parents)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = CompositeParentPass().run(state)

    assert len(report.accepted) == 0, "expected no accepted with 1 child group"
    assert len(state.matches) == 0


def test_composite_parent_low_confidence_skipped():
    """Composite parent with confidence below 0.60 -> skip."""
    legends = [
        {"block_id": "c1", "page": 1, "role": "figure_caption",
         "text": "Figure 1. Caption", "bbox": [0, 500, 300, 550]},
    ]
    candidate_groups = [
        _cgroup("g1", 1, "a1", "a2"),
        _cgroup("g2", 1, "a3", "a4"),
    ]
    composite_parents = [
        _composite_parent("cp1", 1, ["g1", "g2"], confidence=0.50),
    ]
    corpus, index = _make_index(legends, candidate_groups, composite_parents)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = CompositeParentPass().run(state)

    assert len(report.accepted) == 0, "expected no accepted with low confidence"
    assert len(state.matches) == 0


def test_composite_parent_skips_already_matched_legend():
    """Legend already in state.matches -> skip composite pass for it."""
    legends = [
        {"block_id": "c1", "page": 1, "role": "figure_caption",
         "text": "Figure 1. Caption", "bbox": [0, 500, 300, 550]},
    ]
    candidate_groups = [
        _cgroup("g1", 1, "a1", "a2"),
        _cgroup("g2", 1, "a3", "a4"),
    ]
    composite_parents = [
        _composite_parent("cp1", 1, ["g1", "g2"], confidence=0.85),
    ]
    corpus, index = _make_index(legends, candidate_groups, composite_parents)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    # Pre-seed a match for this legend
    state.matches.append({
        "legend_block_id": "c1",
        "settlement_type": "same_page",
        "figure_number": 1,
    })

    report = CompositeParentPass().run(state)

    assert len(report.accepted) == 0, "expected no accepted for already-matched legend"
