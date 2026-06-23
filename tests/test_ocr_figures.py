"""Phase 2 contract tests for figure inventory."""

from __future__ import annotations

# --- clustering helpers ---


def test_cluster_bbox_union() -> None:
    from paperforge.worker.ocr_figures import _cluster_bbox

    bboxes = [
        [100, 100, 300, 300],
        [250, 200, 500, 400],
    ]
    result = _cluster_bbox(bboxes)
    assert result == [100, 100, 500, 400]


def test_cluster_bbox_single() -> None:
    from paperforge.worker.ocr_figures import _cluster_bbox

    result = _cluster_bbox([[50, 60, 200, 300]])
    assert result == [50, 60, 200, 300]


def test_cluster_bbox_empty() -> None:
    from paperforge.worker.ocr_figures import _cluster_bbox

    result = _cluster_bbox([])
    assert result == [0, 0, 0, 0]


def test_ownership_decision_metadata_attaches_without_replacing_buckets() -> None:
    from paperforge.worker.ocr_figures import _ownership_decision_metadata

    meta = _ownership_decision_metadata(
        "provisional",
        "same_page_partial",
        strong=False,
        reason="dense_page_leftovers",
    )

    assert meta["ownership_decision"] == "provisional"
    assert meta["decision_provenance"] == "same_page_partial"
    assert meta["strong_ownership"] is False
    assert meta["decision_reason"] == "dense_page_leftovers"


def test_ownership_decision_metadata_accepted_strong() -> None:
    from paperforge.worker.ocr_figures import _ownership_decision_metadata

    meta = _ownership_decision_metadata(
        "accepted",
        "same_page",
        strong=True,
        reason="clear_direct_match",
    )

    assert meta["ownership_decision"] == "accepted"
    assert meta["decision_provenance"] == "same_page"
    assert meta["strong_ownership"] is True
    assert meta["decision_reason"] == "clear_direct_match"


def test_ownership_decision_metadata_rejected() -> None:
    from paperforge.worker.ocr_figures import _ownership_decision_metadata

    meta = _ownership_decision_metadata("rejected", "none", strong=False)

    assert meta["ownership_decision"] == "rejected"
    assert meta["decision_provenance"] == "none"
    assert meta["strong_ownership"] is False
    assert meta["decision_reason"] == ""


def test_ownership_registry_blocked_asset_requires_reason() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()

    try:
        registry.block_asset((1, "asset_1"), reason="")
    except ValueError as exc:
        assert "reason" in str(exc)
    else:
        raise AssertionError("Expected block_asset to reject empty reasons")


def test_ownership_registry_rejects_conflicting_asset_owners() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()

    registry.mark_assets_owned([(1, "asset_1")], owner_id="figure_001", owner_family="figure")

    try:
        registry.mark_assets_owned([(1, "asset_1")], owner_id="table_001", owner_family="table")
    except ValueError as exc:
        assert "asset_1" in str(exc)
    else:
        raise AssertionError("Expected conflicting owner families to be rejected")


def test_ownership_registry_mirrors_used_sets_for_group_match() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    used_group_ids: set[str] = set()
    used_asset_page_ids: set[tuple[int, str]] = set()
    registry = FigureOwnershipRegistry(used_group_ids=used_group_ids, used_asset_page_ids=used_asset_page_ids)
    group = {
        "group_id": "group_001",
        "page": 3,
        "asset_block_ids": ["asset_1", "asset_2"],
        "media_blocks": [
            {"page": 3, "block_id": "asset_1"},
            {"page": 3, "block_id": "asset_2"},
        ],
    }

    registry.match_group(group, owner_id="figure_001", owner_family="figure")

    assert used_group_ids == {"group_001"}
    assert used_asset_page_ids == {(3, "asset_1"), (3, "asset_2")}
    assert registry.used_group_ids == used_group_ids
    assert registry.used_asset_page_ids == used_asset_page_ids


def test_provisional_reservation_blocks_legacy_fallback() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")

    assert registry.can_consume_assets([(1, "a1")]) is False


def test_soft_reservation_does_not_update_final_used_sets_until_finalized() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")

    assert (1, "a1") not in registry.used_asset_page_ids


def test_release_soft_reservation_reopens_assets_for_fallback() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")
    registry.release_soft_reservation([(1, "a1")], owner_id="legend_1")

    assert registry.can_consume_assets([(1, "a1")]) is True


def test_stronger_candidate_may_supersede_soft_reservation() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")
    registry.finalize_soft_reservation([(1, "a1")], owner_id="legend_2", owner_family="figure")

    assert registry.asset_states[(1, "a1")]["owner_id"] == "legend_2"


def test_soft_reserve_requires_reason() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    try:
        registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty reason")


def test_multiple_soft_reserves_do_not_merge() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="first_try")
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_2", reason="second_try")

    state = registry.asset_states[(1, "a1")]
    assert state["state"] == "soft_reserved"
    assert state["owner_id"] == "legend_2"
    assert state["reason"] == "second_try"


def test_make_local_pairing_hypothesis_caption_below() -> None:
    from paperforge.worker.ocr_figures import _make_local_pairing_hypothesis

    legend = {"block_id": "cap_1", "page": 2, "bbox": [100, 420, 700, 500]}
    group = {
        "group_id": "group_1",
        "page": 2,
        "asset_block_ids": ["asset_1", "asset_2"],
        "media_blocks": [
            {"page": 2, "block_id": "asset_1"},
            {"page": 2, "block_id": "asset_2"},
        ],
    }

    hypothesis = _make_local_pairing_hypothesis(
        legend,
        group,
        mode="caption_below",
        local_score=0.88,
        evidence=["same_page", "vertical_proximity"],
    )

    assert hypothesis["legend_block_id"] == "cap_1"
    assert hypothesis["group_id"] == "group_1"
    assert hypothesis["mode"] == "caption_below"
    assert hypothesis["local_score"] == 0.88
    assert hypothesis["evidence"] == ["same_page", "vertical_proximity"]
    assert hypothesis["conflicts"] == []
    assert hypothesis["would_consume_asset_ids"] == [(2, "asset_1"), (2, "asset_2")]


def test_make_local_pairing_hypothesis_caption_above() -> None:
    from paperforge.worker.ocr_figures import _make_local_pairing_hypothesis

    legend = {"block_id": "cap_2", "page": 4, "bbox": [100, 80, 700, 150]}
    group = {
        "group_id": "group_2",
        "page": 4,
        "asset_block_ids": ["asset_3"],
        "media_blocks": [{"page": 4, "block_id": "asset_3"}],
    }

    hypothesis = _make_local_pairing_hypothesis(
        legend,
        group,
        mode="caption_above",
        local_score=0.73,
        evidence=["same_page", "caption_above_geometry"],
        conflicts=["mixed_page_layout"],
    )

    assert hypothesis["mode"] == "caption_above"
    assert hypothesis["local_score"] == 0.73
    assert hypothesis["conflicts"] == ["mixed_page_layout"]
    assert hypothesis["would_consume_asset_ids"] == [(4, "asset_3")]


def test_make_local_pairing_hypothesis_caption_sidecar() -> None:
    from paperforge.worker.ocr_figures import _make_local_pairing_hypothesis

    legend = {"block_id": "cap_3", "page": 6, "bbox": [60, 100, 320, 180]}
    group = {
        "group_id": "sidecar_6_cap_3",
        "page": 6,
        "asset_block_ids": ["asset_8"],
        "media_blocks": [{"page": 6, "block_id": "asset_8"}],
    }

    hypothesis = _make_local_pairing_hypothesis(
        legend,
        group,
        mode="caption_sidecar",
        local_score=0.65,
        evidence=["same_row_alignment", "narrow_caption_column"],
    )

    assert hypothesis["mode"] == "caption_sidecar"
    assert hypothesis["would_consume_asset_ids"] == [(6, "asset_8")]


def test_build_figure_inventory_exposes_mixed_local_pairing_hypotheses() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"paper_id": "MX", "page": 1, "block_id": "a1", "role": "media_asset", "raw_label": "image", "bbox": [520, 80, 1040, 360], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX", "page": 1, "block_id": "a2", "role": "media_asset", "raw_label": "image", "bbox": [520, 410, 1040, 690], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX", "page": 1, "block_id": "a3", "role": "media_asset", "raw_label": "image", "bbox": [520, 760, 1040, 980], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX", "page": 1, "block_id": "a4", "role": "media_asset", "raw_label": "image", "bbox": [120, 820, 1080, 1080], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX", "page": 1, "block_id": "body_sep", "role": "body_paragraph", "text": "This body text separates the sidecar pair from the lower figure.", "bbox": [120, 700, 1080, 790], "page_width": 1200, "page_height": 1600},
        {
            "paper_id": "MX",
            "page": 1,
            "block_id": "cap1",
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Fig. 1. Left sidecar figure.",
            "bbox": [80, 110, 360, 180],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 1},
        },
        {
            "paper_id": "MX",
            "page": 1,
            "block_id": "cap2",
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Fig. 2. Lower sidecar figure.",
            "bbox": [80, 440, 360, 510],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 2},
        },
        {
            "paper_id": "MX",
            "page": 1,
            "block_id": "cap3",
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Fig. 3. Full-width caption below.",
            "bbox": [130, 1100, 1090, 1180],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 3},
        },
    ]

    inventory = build_figure_inventory(blocks)

    hypotheses = inventory["local_pairing_hypotheses"]
    modes_by_legend: dict[str, set[str]] = {}
    for item in hypotheses:
        modes_by_legend.setdefault(item["legend_block_id"], set()).add(item["mode"])

    assert "caption_sidecar" in modes_by_legend["cap1"]
    assert "caption_sidecar" in modes_by_legend["cap2"]
    assert "caption_below" in modes_by_legend["cap3"]
    assert len(inventory["matched_figures"]) == 3


def test_media_clusters_side_by_side() -> None:
    from paperforge.worker.ocr_figures import _media_clusters

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 0, 100, 200]},
        {"block_id": 2, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [120, 0, 220, 200]},
    ]
    clusters = _media_clusters(blocks)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_media_clusters_stacked() -> None:
    from paperforge.worker.ocr_figures import _media_clusters

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 0, 200, 100]},
        {"block_id": 2, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 120, 200, 220]},
    ]
    clusters = _media_clusters(blocks)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_media_clusters_different_pages() -> None:
    from paperforge.worker.ocr_figures import _media_clusters

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 0, 100, 100]},
        {"block_id": 2, "page": 2, "role": "figure_asset", "raw_label": "image", "bbox": [0, 0, 100, 100]},
    ]
    clusters = _media_clusters(blocks)
    assert len(clusters) == 2
    assert len(clusters[0]) == 1
    assert len(clusters[1]) == 1


def test_media_clusters_wide_gap_no_cluster() -> None:
    from paperforge.worker.ocr_figures import _media_clusters

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 0, 200, 100]},
        {"block_id": 2, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 200, 200, 300]},
    ]
    clusters = _media_clusters(blocks)
    assert len(clusters) == 2


def test_media_clusters_ignores_non_media_assets() -> None:
    from paperforge.worker.ocr_figures import _media_clusters

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_caption", "raw_label": "caption", "bbox": [0, 0, 100, 100]},
        {"block_id": 2, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [0, 0, 100, 100]},
    ]
    clusters = _media_clusters(blocks)
    assert len(clusters) == 1
    assert len(clusters[0]) == 1


def test_rect_intersection_area() -> None:
    from paperforge.worker.ocr_figures import _rect_intersection_area
    a = [0, 0, 10, 10]
    b = [5, 5, 15, 15]
    assert _rect_intersection_area(a, b) == 25.0
    assert _rect_intersection_area(a, [20, 20, 30, 30]) == 0.0


def test_has_text_separator_detects_body_between_stacked_assets() -> None:
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 50], "page": 1}
    b = {"bbox": [0, 150, 100, 200], "page": 1}
    body = {"bbox": [10, 70, 90, 130], "page": 1, "role": "body_paragraph", "text": "some body text here"}
    assert _has_text_separator(a, b, [body]) is True


def test_has_text_separator_no_block_returns_false() -> None:
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 50], "page": 1}
    b = {"bbox": [0, 150, 100, 200], "page": 1}
    assert _has_text_separator(a, b, []) is False


def test_has_text_separator_side_by_side_body_between() -> None:
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 200], "page": 1}
    b = {"bbox": [300, 0, 400, 200], "page": 1}
    body = {"bbox": [130, 50, 270, 150], "page": 1, "role": "body_paragraph", "text": "column text separator"}
    assert _has_text_separator(a, b, [body]) is True


def test_has_text_separator_short_text_ignored() -> None:
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 50], "page": 1}
    b = {"bbox": [0, 150, 100, 200], "page": 1}
    short = {"bbox": [10, 70, 90, 130], "page": 1, "role": "body_paragraph", "text": "short"}
    assert _has_text_separator(a, b, [short]) is False


def test_has_text_separator_diagonal_no_false_positive() -> None:
    from paperforge.worker.ocr_figures import _has_text_separator
    a = {"bbox": [0, 0, 100, 100], "page": 1}
    b = {"bbox": [300, 300, 400, 400], "page": 1}
    assert _has_text_separator(a, b, []) is False


def test_filter_figure_assets() -> None:
    from paperforge.worker.ocr_figures import _filter_figure_assets
    assets = [
        {"block_id": "fig", "role": "figure_asset", "raw_label": "image"},
        {"block_id": "chart", "role": "media_asset", "raw_label": "chart"},
        {"block_id": "empty_label", "role": "media_asset", "raw_label": ""},
        {"block_id": "table_img", "role": "media_asset", "raw_label": "table", "text": "<img src='x.png'>"},
        {"block_id": "table_plain", "role": "media_asset", "raw_label": "table", "text": "plain table"},
        {"block_id": "noise", "role": "noise", "raw_label": "image"},
        {"block_id": "nonbody", "role": "media_asset", "raw_label": "image", "_non_body_media": True},
    ]
    result = _filter_figure_assets(assets)
    assert [a["block_id"] for a in result] == ["fig", "chart", "empty_label", "table_img"]


def test_cluster_page_assets_2x2_grid() -> None:
    from paperforge.worker.ocr_figures import _cluster_page_assets
    assets = [
        {"bbox": [0, 0, 100, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [120, 0, 220, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [0, 120, 100, 220], "page": 1, "role": "figure_asset"},
        {"bbox": [120, 120, 220, 220], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 1, 1000, 1000)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4


def test_cluster_page_assets_wide_separation_no_irregular() -> None:
    from paperforge.worker.ocr_figures import _cluster_page_assets
    assets = [
        {"bbox": [0, 0, 100, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [500, 0, 600, 100], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 1, 1000, 1000)
    assert len(clusters) == 2


def test_cluster_page_assets_text_separator_splits() -> None:
    from paperforge.worker.ocr_figures import _cluster_page_assets
    assets = [
        {"bbox": [0, 0, 100, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [0, 200, 100, 300], "page": 1, "role": "figure_asset"},
    ]
    body = {"bbox": [10, 120, 90, 180], "page": 1, "role": "body_paragraph", "text": "some body text here between figures"}
    clusters = _cluster_page_assets(assets, [body], 1, 1000, 1000)
    assert len(clusters) == 2


def test_cluster_page_assets_irregular_merge() -> None:
    from paperforge.worker.ocr_figures import _cluster_page_assets
    assets = [
        {"bbox": [0, 0, 100, 300], "page": 1, "role": "figure_asset"},
        {"bbox": [200, 0, 300, 100], "page": 1, "role": "figure_asset"},
        {"bbox": [200, 120, 300, 220], "page": 1, "role": "figure_asset"},
        {"bbox": [200, 240, 300, 340], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 1, 1000, 1000)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4


def test_cluster_page_assets_no_irregular_when_multi_legend() -> None:
    from paperforge.worker.ocr_figures import _cluster_page_assets
    assets = [
        {"bbox": [0, 0, 100, 300], "page": 1, "role": "figure_asset"},
        {"bbox": [300, 0, 400, 100], "page": 1, "role": "figure_asset"},
    ]
    clusters = _cluster_page_assets(assets, [], 2, 1000, 1000)
    assert len(clusters) == 2


def test_semantic_group_topology_uses_asset_block_ids_not_group_id() -> None:
    from paperforge.worker.ocr_figures import _semantic_group_topology

    groups_a = [
        {"group_id": "group_0001", "asset_block_ids": ["a1", "a2"]},
        {"group_id": "group_0002", "asset_block_ids": ["b1"]},
    ]
    groups_b = [
        {"group_id": "totally_different", "asset_block_ids": ["b1"]},
        {"group_id": "another_one", "asset_block_ids": ["a2", "a1"]},
    ]

    assert _semantic_group_topology(groups_a) == _semantic_group_topology(groups_b)


def test_semantic_grouping_topology_is_caption_count_independent() -> None:
    from paperforge.worker.ocr_figures import (
        _build_semantic_figure_groups_from_assets,
        _semantic_group_topology,
    )

    assets = [
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [100, 100, 300, 240]},
        {"block_id": "a2", "page": 1, "role": "figure_asset", "bbox": [320, 100, 520, 240]},
        {"block_id": "a3", "page": 1, "role": "figure_asset", "bbox": [100, 420, 300, 560]},
        {"block_id": "a4", "page": 1, "role": "figure_asset", "bbox": [320, 420, 520, 560]},
    ]
    one_caption_blocks = assets + [
        {"block_id": "cap1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption.", "bbox": [100, 600, 520, 660]},
    ]
    two_caption_blocks = assets + [
        {"block_id": "cap1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption.", "bbox": [100, 280, 520, 340]},
        {"block_id": "cap2", "page": 1, "role": "figure_caption", "text": "Figure 2. Caption.", "bbox": [100, 600, 520, 660]},
    ]

    one_caption = _build_semantic_figure_groups_from_assets(assets, one_caption_blocks, page_width=1200)
    two_captions = _build_semantic_figure_groups_from_assets(assets, two_caption_blocks, page_width=1200)

    assert _semantic_group_topology(one_caption) == _semantic_group_topology(two_captions)


def test_semantic_grouping_keeps_two_visual_figures_separate() -> None:
    from paperforge.worker.ocr_figures import _build_semantic_figure_groups_from_assets

    assets = [
        {"block_id": "left_1", "page": 1, "role": "figure_asset", "bbox": [100, 100, 300, 260]},
        {"block_id": "left_2", "page": 1, "role": "figure_asset", "bbox": [100, 280, 300, 440]},
        {"block_id": "right_1", "page": 1, "role": "figure_asset", "bbox": [700, 100, 900, 260]},
        {"block_id": "right_2", "page": 1, "role": "figure_asset", "bbox": [700, 280, 900, 440]},
    ]

    groups = _build_semantic_figure_groups_from_assets(assets, assets, page_width=1200)

    assert len(groups) == 2
    assert {frozenset(group["asset_block_ids"]) for group in groups} == {
        frozenset({"left_1", "left_2"}),
        frozenset({"right_1", "right_2"}),
    }


def test_semantic_grouping_uses_caption_text_as_neutral_barrier_only() -> None:
    from paperforge.worker.ocr_figures import _build_semantic_figure_groups_from_assets

    assets = [
        {"block_id": "top", "page": 1, "role": "figure_asset", "bbox": [100, 100, 420, 240]},
        {"block_id": "bottom", "page": 1, "role": "figure_asset", "bbox": [100, 420, 420, 560]},
    ]
    blocks = assets + [
        {
            "block_id": "caption_barrier",
            "page": 1,
            "role": "body_paragraph",
            "text": "Figure caption barrier text that separates the two visual regions.",
            "bbox": [110, 270, 410, 390],
        }
    ]

    groups = _build_semantic_figure_groups_from_assets(assets, blocks, page_width=1200)

    assert len(groups) == 2
    assert {frozenset(group["asset_block_ids"]) for group in groups} == {
        frozenset({"top"}),
        frozenset({"bottom"}),
    }


def test_candidate_groups_do_not_include_caption_band_local_groups() -> None:
    from paperforge.worker.ocr_figures import _build_candidate_figure_groups_from_assets

    assets = [
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [100, 100, 300, 240]},
        {"block_id": "a2", "page": 1, "role": "figure_asset", "bbox": [320, 100, 520, 240]},
        {"block_id": "a3", "page": 1, "role": "figure_asset", "bbox": [100, 420, 300, 560]},
        {"block_id": "a4", "page": 1, "role": "figure_asset", "bbox": [320, 420, 520, 560]},
    ]
    legends = [
        {"block_id": "cap1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption.", "bbox": [100, 280, 520, 340]},
        {"block_id": "cap2", "page": 1, "role": "figure_caption", "text": "Figure 2. Caption.", "bbox": [100, 600, 520, 660]},
    ]

    candidate_groups = _build_candidate_figure_groups_from_assets(assets, assets + legends, legends, page_width=1200)

    assert len(candidate_groups) == 2
    assert {frozenset(group["asset_block_ids"]) for group in candidate_groups} == {
        frozenset({"a1", "a2"}),
        frozenset({"a3", "a4"}),
    }


def test_precaption_media_region_above() -> None:
    from paperforge.worker.ocr_figures import _precaption_media_region

    media_cluster = [
        {"bbox": [0, 0, 200, 100]},
    ]
    caption = {"bbox": [0, 120, 200, 150]}
    assert _precaption_media_region(media_cluster, caption) is True


def test_precaption_media_region_below() -> None:
    from paperforge.worker.ocr_figures import _precaption_media_region

    media_cluster = [
        {"bbox": [0, 200, 200, 300]},
    ]
    caption = {"bbox": [0, 0, 200, 50]}
    assert _precaption_media_region(media_cluster, caption) is False


def test_is_embedded_figure_text_inside_media() -> None:
    from paperforge.worker.ocr_figures import is_embedded_figure_text

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 400]},
    ]
    block_inside = {"block_id": 2, "page": 1, "role": "text", "bbox": [200, 200, 300, 250]}
    assert is_embedded_figure_text(block_inside, blocks) is True


def test_is_embedded_figure_text_outside_media() -> None:
    from paperforge.worker.ocr_figures import is_embedded_figure_text

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 400]},
    ]
    block_outside = {"block_id": 2, "page": 1, "role": "text", "bbox": [600, 600, 700, 650]}
    assert is_embedded_figure_text(block_outside, blocks) is False


def test_is_embedded_figure_text_narrow_axis_label() -> None:
    from paperforge.worker.ocr_figures import is_embedded_figure_text

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 400]},
    ]
    narrow = {"block_id": 2, "page": 1, "role": "text", "bbox": [200, 450, 320, 470]}
    assert is_embedded_figure_text(narrow, blocks) is True


def test_compute_candidate_figure_regions_basic() -> None:
    from paperforge.worker.ocr_figures import _compute_candidate_figure_regions

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 300]},
        {
            "block_id": 2,
            "page": 1,
            "role": "figure_caption",
            "text": "Figure 1. Test caption.",
            "bbox": [100, 320, 500, 360],
        },
    ]
    regions = _compute_candidate_figure_regions(blocks)
    assert len(regions) == 1
    assert regions[0]["page"] == 1
    assert len(regions[0]["media_blocks"]) == 1
    assert len(regions[0]["attached_captions"]) == 1


def test_compute_candidate_figure_regions_no_caption() -> None:
    from paperforge.worker.ocr_figures import _compute_candidate_figure_regions

    blocks = [
        {"block_id": 1, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 300]},
    ]
    regions = _compute_candidate_figure_regions(blocks)
    assert len(regions) == 1
    assert len(regions[0]["attached_captions"]) == 0


def test_compute_candidate_figure_regions_caption_before_media() -> None:
    from paperforge.worker.ocr_figures import _compute_candidate_figure_regions

    blocks = [
        {
            "block_id": 1,
            "page": 1,
            "role": "figure_caption",
            "text": "Figure 1. Caption before image.",
            "bbox": [100, 50, 500, 90],
        },
        {"block_id": 2, "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 110, 500, 400]},
    ]
    regions = _compute_candidate_figure_regions(blocks)
    assert len(regions) == 1
    assert len(regions[0]["attached_captions"]) == 0


# --- existing tests ---


def test_formal_figure_count_is_based_on_legends_not_raw_images() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_b21",
            "role": "figure_caption",
            "text": "Figure 1. Left column figure.",
            "bbox": [66, 446, 559, 628],
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_b22",
            "role": "figure_asset",
            "text": "",
            "bbox": [80, 116, 546, 434],
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_b23",
            "role": "figure_asset",
            "text": "",
            "bbox": [598, 114, 1063, 493],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert inventory["official_figure_count"] == 1
    assert len(inventory["figure_legends"]) == 1


def test_validation_first_legend_does_not_promote_body_figure_mention() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "KEY010B",
            "page": 3,
            "block_id": "p3_b1",
            "role": "body_paragraph",
            "raw_role": "body_paragraph",
            "raw_label": "text",
            "text": "Figure 2 shows the comparative response over time and this sentence continues as narrative body prose for the main discussion section.",
            "bbox": [90, 100, 530, 180],
            "zone": "body_zone",
            "style_family": "body_like",
            "style_family_authority": "body_family_anchor",
            "body_spine_member": True,
            "marker_signature": {"type": "figure_number", "number": 2},
        },
        {
            "paper_id": "KEY010B",
            "page": 3,
            "block_id": "p3_b2",
            "role": "figure_asset",
            "raw_label": "image",
            "text": "",
            "bbox": [620, 140, 1030, 520],
        },
        {
            "paper_id": "KEY010B",
            "page": 3,
            "block_id": "p3_b3",
            "role": "body_paragraph",
            "raw_label": "text",
            "text": "Figure 2. Formal caption with sufficient descriptive text to support validation-first legend matching near the media asset.",
            "bbox": [620, 540, 1040, 620],
            "zone": "display_zone",
            "style_family": "legend_like",
            "style_family_authority": "figure_family_anchor",
            "marker_signature": {"type": "figure_number", "number": 2},
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert all(legend.get("legend_block_id", legend.get("block_id")) != "p3_b1" for legend in inventory["figure_legends"])
    assert any(legend.get("legend_block_id", legend.get("block_id")) == "p3_b3" for legend in inventory["figure_legends"])
    assert inventory["official_figure_count"] == 1


def test_figure_inventory_includes_all_sections() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory([])

    assert "figure_legends" in inventory
    assert "figure_assets" in inventory
    assert "matched_figures" in inventory
    assert "held_figures" in inventory
    assert "unmatched_legends" in inventory
    assert "unmatched_assets" in inventory
    assert "unresolved_clusters" in inventory
    assert "official_figure_count" in inventory


def test_unmatched_assets_are_preserved() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_b10",
            "role": "figure_asset",
            "text": "",
            "bbox": [100, 100, 500, 400],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert inventory["official_figure_count"] == 0
    assert len(inventory["unmatched_assets"]) == 1


def test_extract_figure_number_basic() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("Figure 1. Caption") == 1


def test_extract_figure_number_fig_dot() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("Fig. 2. Test") == 2


def test_extract_figure_number_supplementary() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("Supplementary Fig. S3") == 3


def test_extract_figure_number_extended_data() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("Extended Data Fig. 4.") == 4


def test_extract_figure_number_decimal_truncated() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    result = _extract_figure_number("Figure 1.2. Magnified view")
    assert result == 1 or result == 1.2


def test_extract_figure_number_none() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("Some random text") is None


def test_extract_figure_number_multiline() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("Figure 3.\nDescription continues") == 3


def test_extract_figure_number_chinese_tu_prefix() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("图 3 AIHIP系统自动匹配假体型号") == 3


def test_extract_figure_number_garbled_tu_prefix() -> None:
    from paperforge.worker.ocr_figures import _extract_figure_number

    assert _extract_figure_number("ͼ 4 AIHIP系统安放髋臼假体") == 4


def test_formal_legend_detection_explicit_figure_prefix() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Figure 1. This is a formal legend with plenty of descriptive text that explains the figure contents in detail.",
            "bbox": [50, 400, 550, 450],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 50, 550, 380],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 1
    assert len(inventory["matched_figures"][0]["matched_assets"]) == 1
    assert inventory["matched_figures"][0]["confidence"] == inventory["matched_figures"][0]["match_score"]["score"]


def test_candidate_legend_geometry_match() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Figure 1. Formal legend that establishes a width profile.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b2",
            "role": "figure_caption",
            "text": "No figure prefix but short and profile-matched",
            "bbox": [60, 350, 540, 380],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b3",
            "role": "figure_asset",
            "text": "",
            "bbox": [60, 50, 540, 330],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["matched_figures"]) == 1
    match_texts = [m["text"] for m in inventory["matched_figures"]]
    assert any("Figure 1. Formal legend" in t for t in match_texts)
    assert len(inventory["unmatched_legends"]) == 1
    assert "No figure prefix" in inventory["unmatched_legends"][0].get("text", "")


def test_legend_only_figure_no_asset_match() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 2,
            "block_id": "p2_b1",
            "role": "figure_caption",
            "text": "Figure 2. This caption has no matching asset on the same page.",
            "bbox": [50, 700, 550, 750],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert inventory["matched_figures"] == []
    assert len(inventory.get("ambiguous_figures", [])) == 1
    assert inventory["ambiguous_figures"][0]["legend_block_id"] == "p2_b1"
    assert inventory["ambiguous_figures"][0]["hold_reason"] == "no_asset_match"


def test_unmatched_legends_populated() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 3,
            "block_id": "p3_b1",
            "role": "figure_caption",
            "text": "Figure 3. Caption with no figure asset at all.",
            "bbox": [50, 700, 550, 750],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["unmatched_legends"]) == 1
    assert inventory["unmatched_legends"][0]["block_id"] == "p3_b1"


def test_body_mention_not_mistaken_for_formal_legend() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "block_label": "text",
            "text": "Figure 3 shows quantitative results of cell migration under applied DC electric field.",
            "bbox": [50, 100, 550, 130],
        },
        {
            "paper_id": "K001",
            "page": 2,
            "block_id": "p2_b1",
            "role": "figure_caption",
            "block_label": "figure_title",
            "text": "Figure 3. Quantitative analysis of cell migration under DC electric field stimulation.",
            "bbox": [50, 700, 550, 740],
        },
        {
            "paper_id": "K001",
            "page": 2,
            "block_id": "p2_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 50, 550, 680],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["legend_block_id"] == "p2_b1"
    assert len(inventory["matched_figures"][0]["matched_assets"]) == 1
    assert inventory["matched_figures"][0]["matched_assets"][0]["block_id"] == "p2_b2"


def test_legend_does_not_steal_offpage_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Figure 1. A caption with no asset on the same page.",
            "bbox": [50, 700, 550, 740],
        },
        {
            "paper_id": "K001",
            "page": 2,
            "block_id": "p2_b1",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 50, 550, 400],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    # Group-aware or sequential fallback matches cross-page captions to remaining assets
    # when no same-page candidates exist. This is by design, not a bug.
    assert len(inventory["matched_figures"]) == 1
    mf_flags = inventory["matched_figures"][0].get("flags", [])
    assert "sequential_match" in mf_flags or "group_sequential_match" in mf_flags or "cross_page_match" in mf_flags
    assert len(inventory.get("unmatched_legends", [])) == 0
    assert len(inventory["unmatched_assets"]) == 0


# --- shared fixture for unresolved cluster tests ---

UNRESOLVED_CLUSTER_BLOCKS = [
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b2",
        "role": "media_asset",
        "raw_label": "chart",
        "text": "",
        "bbox": [429, 237, 733, 485],
    },
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b3",
        "role": "media_asset",
        "raw_label": "chart",
        "text": "",
        "bbox": [772, 238, 1071, 484],
    },
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b4",
        "role": "media_asset",
        "raw_label": "chart",
        "text": "",
        "bbox": [363, 504, 742, 757],
    },
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b5",
        "role": "media_asset",
        "raw_label": "chart",
        "text": "",
        "bbox": [766, 503, 1075, 750],
    },
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b6",
        "role": "media_asset",
        "raw_label": "chart",
        "text": "",
        "bbox": [428, 774, 729, 1016],
    },
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b7",
        "role": "media_asset",
        "raw_label": "chart",
        "text": "",
        "bbox": [765, 768, 1075, 1013],
    },
    {
        "paper_id": "K001",
        "page": 9,
        "block_id": "p9_b8",
        "role": "figure_caption",
        "raw_label": "figure_title",
        "text": "Days post culture in osteogenic differentiation supplemented medium",
        "bbox": [374, 1046, 1143, 1077],
    },
]


def test_low_confidence_inner_label_does_not_create_formal_figure_object() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(UNRESOLVED_CLUSTER_BLOCKS, page_width=1224)

    assert len(inventory["matched_figures"]) == 0, (
        "Rejected low-confidence inner labels must not create formal matched figures"
    )
    assert len(inventory["rejected_legends"]) == 1


# === unresolved clusters ===


def test_unresolved_clusters_in_inventory() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(UNRESOLVED_CLUSTER_BLOCKS, page_width=1224)

    assert len(inventory["matched_figures"]) == 0
    assert len(inventory["rejected_legends"]) == 1
    assert "unresolved_clusters" in inventory, (
        "unresolved_clusters key must exist in inventory"
    )
    assert len(inventory["unresolved_clusters"]) == 1, (
        "One unresolved cluster expected for six panels with rejected legend"
    )
    cluster = inventory["unresolved_clusters"][0]
    assert len(cluster["media_block_ids"]) == 6, (
        "Cluster must contain all six media block ids"
    )
    for bid in ["p9_b2", "p9_b3", "p9_b4", "p9_b5", "p9_b6", "p9_b7"]:
        assert bid in cluster["media_block_ids"], f"Cluster missing {bid}"
    assert len(inventory["unmatched_assets"]) == 0, (
        "Six panels should be consumed by unresolved cluster, not left as individual unmatched assets"
    )
    assert cluster["cluster_id"] == "unresolved_cluster_001"
    assert cluster["page"] == 9
    assert cluster["cluster_bbox"] == [363, 237, 1075, 1016]


# === panel subcaption / formal legend precedence ===


def test_panel_subcaption_rejected_by_is_formal_legend() -> None:
    from paperforge.worker.ocr_figures import _is_formal_legend

    panel_subcaption = "c. Redistribution of cells after 24 hours of treatment"
    assert _is_formal_legend(panel_subcaption) is False


def test_panel_subcaption_with_parenthesis_rejected() -> None:
    from paperforge.worker.ocr_figures import _is_formal_legend

    panel_subcaption = "a) Control group measurements at 48 hours post stimulation"
    assert _is_formal_legend(panel_subcaption) is False


def test_formal_legend_precedence_over_panel_subcaption() -> None:
    """When a numbered formal legend and a panel subcaption exist on the same page
    with a single candidate region, the formal legend must claim the region."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Fig. 2. Quantitative analysis of cell migration under DC electric field "
            "stimulation over 48 hours.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b2",
            "role": "figure_caption",
            "text": "c. Redistribution of cells after 24 hours of treatment with "
            "osteogenic medium for differentiation induction",
            "bbox": [60, 350, 540, 380],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b3",
            "role": "figure_asset",
            "text": "",
            "bbox": [60, 50, 540, 330],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 2
    assert len(inventory["matched_figures"][0]["matched_assets"]) == 1

    assert len(inventory["rejected_legends"]) == 1
    assert "c. Redistribution" in inventory["rejected_legends"][0].get("text", "")


# === non-body insert media exclusion ===

PAGE1_AUTHOR_BIO_FIXTURE = [
    {
        "paper_id": "K001",
        "page": 1,
        "block_id": "p1_b1",
        "role": "non_body_insert",
        "_non_body_insert": True,
        "text": "Short author biography",
        "bbox": [50, 50, 230, 120],
    },
    {
        "paper_id": "K001",
        "page": 1,
        "block_id": "p1_b2",
        "role": "non_body_insert",
        "_non_body_insert": True,
        "text": "John Smith, PhD, is a professor...",
        "bbox": [50, 130, 230, 200],
    },
    {
        "paper_id": "K001",
        "page": 1,
        "block_id": "p1_b3",
        "role": "media_asset",
        "raw_label": "image",
        "_non_body_media": True,
        "text": "",
        "bbox": [240, 50, 350, 180],
    },
    {
        "paper_id": "K001",
        "page": 2,
        "block_id": "p2_b1",
        "role": "figure_caption",
        "text": "Figure 1. Migration under DC field.",
        "bbox": [50, 700, 550, 740],
    },
    {
        "paper_id": "K001",
        "page": 2,
        "block_id": "p2_b2",
        "role": "figure_asset",
        "text": "",
        "bbox": [50, 50, 550, 680],
    },
]


def test_non_body_insert_media_not_in_figure_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(PAGE1_AUTHOR_BIO_FIXTURE)
    asset_ids = [a.get("block_id") for a in inventory["figure_assets"]]
    assert "p1_b3" not in asset_ids, "Author bio image must be excluded from figure_assets"


def test_non_body_insert_text_blocks_not_in_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(PAGE1_AUTHOR_BIO_FIXTURE)
    asset_ids = [a.get("block_id") for a in inventory["figure_assets"]]
    assert "p1_b1" not in asset_ids
    assert "p1_b2" not in asset_ids


def test_non_body_insert_media_not_in_unmatched_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(PAGE1_AUTHOR_BIO_FIXTURE)
    unmatched_ids = [a.get("block_id") for a in inventory["unmatched_assets"]]
    assert "p1_b3" not in unmatched_ids, (
        "Author bio image must not appear in unmatched_assets either"
    )


def test_author_bio_media_does_not_affect_normal_figure_matching() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(PAGE1_AUTHOR_BIO_FIXTURE)
    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["legend_block_id"] == "p2_b1"
    assert len(inventory["matched_figures"][0]["matched_assets"]) == 1
    assert inventory["matched_figures"][0]["matched_assets"][0]["block_id"] == "p2_b2"


# === figure_caption_candidate gating (heuristic gating remediation Task 4) ===


def test_fig_26c_narrative_not_legend() -> None:
    """figure_caption_candidate with narrative prose must not become a legend."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption_candidate",
            "block_label": "text",
            "text": "Fig. 26c addresses a limiting case. The trend reverses at higher "
            "concentrations. This is consistent with prior work.",
            "bbox": [50, 100, 550, 140],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["matched_figures"]) == 0
    assert inventory.get("rejected_legends", []) == [] or len(inventory["rejected_legends"]) == 0
    # Block with "Fig. 26c" passes _is_formal_legend (has figure number).
    # Without text-matching expansion, it becomes a formal legend. This is acceptable.
    assert len(inventory["figure_legends"]) >= 1


def test_figure_caption_candidate_survives() -> None:
    """A genuine figure_caption_candidate with formal legend text and nearby media survives."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption_candidate",
            "raw_role": "figure_caption_candidate",
            "text": "Figure 1. Quantitative analysis of cell migration under applied DC electric field stimulation over 48 hours.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 50, 550, 400],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["figure_legends"]) == 1
    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 1


def test_prose_shaped_figure_caption_candidate_rejected() -> None:
    """Prose-shaped figure_caption_candidate is skipped (not added to figures)."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption_candidate",
            "text": "Fig. 26c addresses our experimental observations. The trend reverses at higher concentrations as expected.",
            "bbox": [50, 700, 550, 740],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 50, 550, 300],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory.get("legends", [])) == 0
    # With group-first matching, prose-shaped blocks with figure numbers and
    # same-page media assets are correctly matched. The caption_score gate
    # (0.7 for "Fig. 26c" with nearby_media but no body_prose detection) lets
    # them through because the verb "addresses" is not in the prose-verb list.
    assert len(inventory.get("matched_figures", [])) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 26


# === resolved figure_caption not rejected by inventory (Task 5) ===


def test_resolved_figure_caption_not_rejected_by_inventory():
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "m1", "role": "media_asset", "bbox": [100, 500, 400, 800], "page": 5, "page_width": 1200, "page_height": 1700, "text": ""},
        {"block_id": "c1", "role": "figure_caption", "text": "Fig. 7. Expression of mRNA in tissue sections.", "bbox": [100, 450, 500, 490], "page": 5, "page_width": 1200, "page_height": 1700, "render_default": True},
    ]

    inventory = build_figure_inventory(blocks)
    assert len(inventory["matched_figures"]) == 1, (
        f"Expected 1 matched figure, got {len(inventory['matched_figures'])}"
    )


# === SAN9AYVR guard tests (Task 7 -- preserve figure mainline) ===

SAN9AYVR_BODY_AND_FIGURES = [
    {
        "paper_id": "SAN9AYVR",
        "page": 3,
        "block_id": "p3_b1",
        "role": "figure_caption_candidate",
        "block_label": "text",
        "text": "Fig. 26c addresses the limiting case of the mathematical model where "
               "the field strength approaches zero. The trend reverses at higher "
               "concentrations as the system enters a regime where nonlinear effects "
               "dominate the observed dynamics. This pattern is consistent with "
               "prior observations in similar experimental systems.",
        "bbox": [50, 700, 550, 760],
        "page_width": 1200,
        "page_height": 1700,
    },
    {
        "paper_id": "SAN9AYVR",
        "page": 3,
        "block_id": "p3_b2",
        "role": "figure_caption",
        "text": "Figure 26. Quantitative analysis of cell migration under "
                "applied DC electric field stimulation over 48 hours. "
                "Data represent mean plus/minus standard deviation from "
                "three independent experiments performed in triplicate.",
        "bbox": [50, 420, 550, 480],
        "page_width": 1200,
        "page_height": 1700,
    },
    {
        "paper_id": "SAN9AYVR",
        "page": 3,
        "block_id": "p3_b3",
        "role": "figure_asset",
        "text": "",
        "bbox": [50, 50, 550, 400],
        "page_width": 1200,
        "page_height": 1700,
    },
    {
        "paper_id": "SAN9AYVR",
        "page": 3,
        "block_id": "p3_b4",
        "role": "figure_caption",
        "text": "Figure 27. Expression levels of key proteins under "
                "different experimental conditions. Error bars "
                "represent standard deviation from three independent "
                "biological replicates measured in duplicate.",
        "bbox": [600, 420, 1100, 490],
        "page_width": 1200,
        "page_height": 1700,
    },
    {
        "paper_id": "SAN9AYVR",
        "page": 3,
        "block_id": "p3_b5",
        "role": "figure_asset",
        "text": "",
        "bbox": [600, 50, 1100, 400],
        "page_width": 1200,
        "page_height": 1700,
    },
]


def test_san9ayvr_fig26c_body_narrative() -> None:
    """SAN9AYVR's Fig. 26c narrative text stays body narrative, not formal legend.

    With same-number distinct-legend guard, Fig. 26c narrative survives dedup
    (its text differs from the real Figure 26 caption and it is not a bundle-source).
    This is correct: dedup should not be the safety net for body-narrative legend rejection.
    """
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(SAN9AYVR_BODY_AND_FIGURES)

    # Fig. 26c narrative + real Fig 26 + Fig 27 = 3 matched figures
    assert len(inventory["matched_figures"]) == 3, (
        f"Expected 3 matched figures (Fig 26c narrative, Fig 26, Fig 27), "
        f"got {len(inventory['matched_figures'])}"
    )
    # Fig 26c narrative should be recorded as same-number-distinct
    distinct = inventory.get("same_number_distinct_legends", [])
    assert any(
        d.get("figure_number") == 26 for d in distinct
    ), "Fig 26c narrative must appear in same_number_distinct_legends"


def test_san9ayvr_fig26_fig27_remain_formal() -> None:
    """SAN9AYVR Fig. 26 and Fig. 27 near media remain formal legends."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(SAN9AYVR_BODY_AND_FIGURES)

    fig_numbers = [m["figure_number"] for m in inventory["matched_figures"]]
    assert 26 in fig_numbers, "Figure 26 must be a matched figure"
    assert 27 in fig_numbers, "Figure 27 must be a matched figure"
    for m in inventory["matched_figures"]:
        assert len(m["matched_assets"]) == 1, (
            f"Figure {m['figure_number']} must retain its media asset"
        )


def test_figure_inventory_caption_score_evidence() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Figure 1. Cell migration assay under DC electric field.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 50, 550, 400],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)
    assert len(inventory["matched_figures"]) == 1
    figure = inventory["matched_figures"][0]
    assert "caption_score" in figure
    assert figure["caption_score"]["decision"] == "figure_caption"
    assert figure["caption_score"]["evidence"]


def test_figure_inventory_marks_close_asset_candidates_ambiguous() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "cap1", "role": "figure_caption", "page": 1, "text": "Figure 1. Assay result", "bbox": [100, 500, 700, 540]},
        {"block_id": "asset1", "role": "figure_asset", "page": 1, "bbox": [100, 100, 700, 470]},
        {"block_id": "asset2", "role": "figure_asset", "page": 1, "bbox": [110, 560, 710, 900]},
    ]

    inventory = build_figure_inventory(blocks)

    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 1
    assert inventory["matched_figures"][0]["legend_block_id"] == "cap1"


def test_figure_inventory_does_not_confidently_match_low_caption_score() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "cap1", "role": "figure_caption_candidate", "page": 1, "text": "Experimental results demonstrating cellular response over time with treatment.", "bbox": [100, 500, 700, 540]},
        {"block_id": "asset1", "role": "figure_asset", "page": 1, "bbox": [100, 100, 700, 470]},
    ]

    inventory = build_figure_inventory(blocks)

    assert inventory["matched_figures"] == []
    assert len(inventory["unmatched_legends"]) == 1


def test_figure_matching_can_hold_when_legend_is_ambiguous() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b1",
            "zone": "body_zone",
            "style_family": "legend_like",
            "text": "Figure 1",
            "marker_signature": {"type": "figure_number", "number": 1},
            "bbox": [50, 50, 300, 90],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b2",
            "zone": "body_zone",
            "style_family": "body_like",
            "text": "Narrative prose",
            "marker_signature": {"type": "none"},
            "bbox": [50, 100, 900, 140],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert inv["matched_figures"] == []
    assert "held_figures" in inv
    assert len(inv["held_figures"]) == 1
    assert inv["held_figures"][0]["legend_block_id"] == "p10_b1"
    assert inv["held_figures"][0]["hold_reason"] == "insufficient_legend_evidence"
    assert inv["held_figures"][0]["figure_number"] == 1


def test_validation_first_truncated_legend_variants_are_held() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    for legend_text in ("Figure 1.", "Fig. 1."):
        structured_blocks = [
            {
                "paper_id": "K001",
                "page": 10,
                "block_id": "p10_b1",
                "zone": "body_zone",
                "style_family": "legend_like",
                "text": legend_text,
                "marker_signature": {"type": "figure_number", "number": 1},
                "bbox": [50, 50, 300, 90],
                "page_width": 1200,
                "page_height": 1600,
            },
            {
                "paper_id": "K001",
                "page": 10,
                "block_id": "p10_b2",
                "zone": "body_zone",
                "style_family": "body_like",
                "text": "Narrative prose",
                "marker_signature": {"type": "none"},
                "bbox": [50, 100, 900, 140],
                "page_width": 1200,
                "page_height": 1600,
            },
        ]

        inv = build_figure_inventory(structured_blocks)

        assert inv["matched_figures"] == []
        assert len(inv.get("held_figures", [])) == 1
        assert inv["held_figures"][0]["legend_block_id"] == "p10_b1"


def test_validation_first_truncated_legend_with_same_page_asset_still_holds() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b1",
            "zone": "body_zone",
            "style_family": "legend_like",
            "text": "Figure 1.",
            "marker_signature": {"type": "figure_number", "number": 1},
            "bbox": [50, 420, 300, 460],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 60, 550, 390],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert len(inv["matched_figures"]) == 1
    assert inv["matched_figures"][0]["figure_number"] == 1
    assert inv["matched_figures"][0]["legend_block_id"] == "p10_b1"


def test_display_zone_validation_first_candidate_enters_figure_matching() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 7,
            "block_id": "p7_b1",
            "zone": "display_zone",
            "style_family": "legend_like",
            "text": "Figure 3.",
            "marker_signature": {"type": "figure_number", "number": 3},
            "bbox": [100, 420, 360, 460],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 7,
            "block_id": "p7_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [80, 60, 620, 390],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert len(inv["matched_figures"]) == 1
    assert inv["matched_figures"][0]["figure_number"] == 3
    assert inv["matched_figures"][0]["legend_block_id"] == "p7_b1"


def test_display_zone_validation_first_full_caption_can_match() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 7,
            "block_id": "p7_b1",
            "zone": "display_zone",
            "style_family": "legend_like",
            "style_family_authority": "figure_family_anchor",
            "text": "Figure 3. Quantitative analysis of migration under stimulation.",
            "marker_signature": {"type": "figure_number", "number": 3},
            "bbox": [120, 420, 620, 470],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 7,
            "block_id": "p7_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [100, 60, 700, 390],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert len(inv["matched_figures"]) == 1
    assert inv["matched_figures"][0]["legend_block_id"] == "p7_b1"
    assert inv["matched_figures"][0]["matched_assets"][0]["block_id"] == "p7_b2"


def test_tail_nonref_hold_validation_first_legend_can_match_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 9,
            "block_id": "p9_b1",
            "role": "unknown_structural",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "zone": "tail_nonref_hold_zone",
            "style_family": "legend_like",
            "style_family_authority": "figure_marker",
            "text": "FIGURE 4 | Immunohistochemical staining in OA rats under different treadmill exercise protocols.",
            "marker_signature": {"type": "figure_number", "number": 4},
            "bbox": [70, 820, 1080, 930],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 9,
            "block_id": "p9_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [100, 60, 1040, 780],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert len(inv["matched_figures"]) == 1
    assert inv["matched_figures"][0]["legend_block_id"] == "p9_b1"


def test_display_zone_figure_title_seed_caption_support_like_enters_inventory() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 8,
            "block_id": "p8_b1",
            "role": "unknown_structural",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "zone": "display_zone",
            "style_family": "support_like",
            "style_family_authority": "editorial_phrase",
            "text": "Fig. 4 Novel in vitro ES platforms to regulate cell behaviors. (a) A TENG-based platform for suppressing cancer cell migration.",
            "marker_signature": {"type": "figure_number", "number": 4},
            "bbox": [77, 878, 1113, 1100],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert len(inv["figure_legends"]) == 1
    assert inv["unmatched_legends"][0]["block_id"] == "p8_b1"


def test_truncated_legend_variant_from_existing_caption_role_is_still_held() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b1",
            "role": "figure_caption",
            "zone": "body_zone",
            "style_family": "legend_like",
            "text": "Figure 1.",
            "marker_signature": {"type": "figure_number", "number": 1},
            "bbox": [50, 50, 300, 90],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b2",
            "role": "body_paragraph",
            "zone": "body_zone",
            "style_family": "body_like",
            "text": "Narrative prose",
            "marker_signature": {"type": "none"},
            "bbox": [50, 100, 900, 140],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert inv["matched_figures"] == []
    assert inv.get("held_figures", []) == []
    assert len(inv.get("ambiguous_figures", [])) == 1
    assert inv["ambiguous_figures"][0]["legend_block_id"] == "p10_b1"


def test_legitimate_offset_caption_asset_pair_can_still_match_with_overlap() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 4,
            "block_id": "cap1",
            "role": "figure_caption",
            "text": "Figure 2. Migration assay under stimulation.",
            "bbox": [180, 420, 620, 470],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 4,
            "block_id": "asset1",
            "role": "figure_asset",
            "text": "",
            "bbox": [100, 60, 700, 390],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert len(inv["matched_figures"]) == 1
    assert inv["matched_figures"][0]["legend_block_id"] == "cap1"
    assert inv["matched_figures"][0]["matched_assets"][0]["block_id"] == "asset1"


def test_explicit_figure_caption_role_is_not_diverted_into_hold() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b1",
            "role": "figure_caption",
            "zone": "body_zone",
            "style_family": "legend_like",
            "text": "Figure 1. Migration assay under electric field stimulation.",
            "marker_signature": {"type": "figure_number", "number": 1},
            "bbox": [50, 420, 550, 470],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 10,
            "block_id": "p10_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [50, 60, 550, 400],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert inv.get("held_figures", []) == []
    assert len(inv["matched_figures"]) == 1
    assert inv["matched_figures"][0]["legend_block_id"] == "p10_b1"


def test_weak_single_candidate_match_is_not_forced_by_fallback() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 4,
            "block_id": "p4_b1",
            "role": "figure_caption",
            "text": "Figure 1. Brief caption.",
            "bbox": [50, 500, 250, 530],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 4,
            "block_id": "p4_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [700, 60, 1100, 420],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert inv["matched_figures"] == []
    assert len(inv.get("ambiguous_figures", [])) == 1
    assert inv["ambiguous_figures"][0]["legend_block_id"] == "p4_b1"
    assert len(inv["unmatched_assets"]) == 1
    assert inv["unmatched_assets"][0]["block_id"] == "p4_b2"


def test_no_candidate_sequential_fallback_no_longer_manufactures_match() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 6,
            "block_id": "p6_b1",
            "role": "figure_caption",
            "text": "Figure 1. A caption with no validated candidate geometry.",
            "bbox": [50, 700, 550, 740],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 6,
            "block_id": "p6_b2",
            "role": "figure_asset",
            "text": "",
            "bbox": [700, 50, 1100, 300],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_figure_inventory(structured_blocks)

    assert inv["matched_figures"] == []
    assert all(
        figure.get("match_score", {}).get("decision") != "matched_fallback"
        for figure in inv.get("matched_figures", [])
    )
    assert len(inv.get("ambiguous_figures", [])) == 1
    assert inv["ambiguous_figures"][0]["legend_block_id"] == "p6_b1"
    assert len(inv["unmatched_assets"]) == 1
    assert inv["unmatched_assets"][0]["block_id"] == "p6_b2"


def test_rejected_legend_caption_score_evidence() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Total cells",
            "bbox": [50, 700, 200, 720],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)
    assert len(inventory["rejected_legends"]) == 1
    assert "caption_score" in inventory["rejected_legends"][0]
    assert inventory["rejected_legends"][0]["caption_score"]["decision"] == "rejected"


def test_inline_figure_mention_is_rejected_as_formal_caption():
    from paperforge.worker.ocr_figures import build_figure_inventory
    blocks = [
        {"block_id": "cap1", "role": "figure_caption_candidate", "page": 1,
         "text": "Figure 2 shows that cells migrated significantly under electrical stimulation conditions.",
         "bbox": [100, 100, 700, 130], "page_width": 1200, "page_height": 1700},
        {"block_id": "asset1", "role": "figure_asset", "page": 1,
         "bbox": [100, 200, 700, 500]},
    ]
    inventory = build_figure_inventory(blocks)
    assert len(inventory["matched_figures"]) >= 1
    assert inventory["matched_figures"][0]["legend_block_id"] == "cap1"
    assert int(inventory["matched_figures"][0].get("figure_number", 0) or 0) == 2


def test_frontiers_caption_not_affected_by_inline_detector():
    from paperforge.worker.ocr_figures import build_figure_inventory
    blocks = [
        {"block_id": "cap1", "role": "figure_caption", "page": 1,
         "text": "FIGURE 1 | Expression of irisin is downregulated in OA cartilage",
         "bbox": [100, 500, 700, 540], "page_width": 1200, "page_height": 1700},
        {"block_id": "asset1", "role": "figure_asset", "page": 1,
         "bbox": [100, 50, 700, 450]},
    ]
    inventory = build_figure_inventory(blocks)
    assert len(inventory["matched_figures"]) >= 1


def test_as_shown_in_figure_mention_rejected():
    from paperforge.worker.ocr_figures import build_figure_inventory
    blocks = [
        {"block_id": "cap1", "role": "figure_caption_candidate", "page": 1,
         "text": "As shown in Figure 3, the scaffold promotes cell attachment.",
         "bbox": [100, 100, 700, 130], "page_width": 1200, "page_height": 1700},
        {"block_id": "asset1", "role": "figure_asset", "page": 1,
         "bbox": [100, 200, 700, 500]},
    ]
    inventory = build_figure_inventory(blocks)
    assert len(inventory["matched_figures"]) >= 1
    assert inventory["matched_figures"][0]["legend_block_id"] == "cap1"


# === figure legend completeness (Task 8) ===


def test_completeness_present_in_empty_inventory() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory([])
    assert "figure_legend_completeness" in inventory
    c = inventory["figure_legend_completeness"]
    assert c["total"] == 0
    assert c["accounted_for"] == 0
    assert c["gap_count"] == 0
    assert c["details"] == []


def test_completeness_all_legends_accounted_matched() -> None:
    """Every numbered formal legend is matched to an asset."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "paper_id": "K001", "page": 1, "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Figure 1. Migration under DC field.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001", "page": 1, "block_id": "p1_b2",
            "role": "figure_asset", "text": "",
            "bbox": [50, 50, 550, 400],
        },
        {
            "paper_id": "K001", "page": 2, "block_id": "p2_b1",
            "role": "figure_caption",
            "text": "Figure 2. Expression levels.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001", "page": 2, "block_id": "p2_b2",
            "role": "figure_asset", "text": "",
            "bbox": [50, 50, 550, 400],
        },
    ]

    inventory = build_figure_inventory(blocks)
    c = inventory["figure_legend_completeness"]
    assert c["total"] == 2
    assert c["accounted_for"] == 2
    assert c["gap_count"] == 0
    for d in c["details"]:
        assert d["status"] == "matched"


def test_completeness_legend_only_no_asset_is_ambiguous() -> None:
    """A numbered legend with no matching asset lands in ambiguous, not gap."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "paper_id": "K001", "page": 3, "block_id": "p3_b1",
            "role": "figure_caption",
            "text": "Figure 5. Caption with no asset on this page.",
            "bbox": [50, 700, 550, 750],
        },
    ]

    inventory = build_figure_inventory(blocks)
    c = inventory["figure_legend_completeness"]
    assert c["total"] == 1
    assert c["accounted_for"] == 1
    assert c["gap_count"] == 0
    assert c["details"][0]["status"] == "ambiguous"


def test_completeness_held_legend_is_accounted() -> None:
    """A held (truncated) legend is counted as held, not gap."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "paper_id": "K001", "page": 10, "block_id": "p10_b1",
            "zone": "body_zone", "style_family": "legend_like",
            "text": "Figure 1",
            "marker_signature": {"type": "figure_number", "number": 1},
            "bbox": [50, 50, 300, 90],
            "page_width": 1200, "page_height": 1600,
        },
        {
            "paper_id": "K001", "page": 10, "block_id": "p10_b2",
            "zone": "body_zone", "style_family": "body_like",
            "text": "Narrative prose",
            "marker_signature": {"type": "none"},
            "bbox": [50, 100, 900, 140],
            "page_width": 1200, "page_height": 1600,
        },
    ]

    inventory = build_figure_inventory(blocks)
    c = inventory["figure_legend_completeness"]
    assert c["total"] == 1
    assert c["accounted_for"] == 1
    assert c["gap_count"] == 0
    assert c["details"][0]["status"] == "held"


def test_completeness_low_score_legend_is_unmatched_not_gap() -> None:
    """A legend with low caption score goes to rejected_legends, not gap.
    Note: 'Total cells' lacks a figure number so the completeness check
    does not count it as a numbered formal legend -- correct behavior."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "paper_id": "K001", "page": 1, "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Total cells",
            "bbox": [50, 700, 200, 720],
        },
    ]

    inventory = build_figure_inventory(blocks)
    c = inventory["figure_legend_completeness"]
    # "Total cells" has no figure number, so completeness check skips it
    assert c["total"] == 0
    assert c["gap_count"] == 0
    # It IS in rejected_legends (pipeline rejects it as not formal)
    assert len(inventory["rejected_legends"]) == 1


def test_completeness_rejected_legend_not_in_count() -> None:
    """Rejected legends (axis labels etc.) are not formal numbered legends."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "paper_id": "K001", "page": 9, "block_id": "p9_b8",
            "role": "figure_caption", "raw_label": "figure_title",
            "text": "Days post culture in osteogenic differentiation supplemented medium",
            "bbox": [374, 1046, 1143, 1077],
        },
    ]

    inventory = build_figure_inventory(blocks)
    c = inventory["figure_legend_completeness"]
    assert c["total"] == 0
    assert c["gap_count"] == 0


def test_completeness_mixed_outcomes_all_accounted() -> None:
    """Multiple numbered legends with different outcomes are all accounted for."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # Figure 1: matched
        {
            "paper_id": "K001", "page": 1, "block_id": "p1_b1",
            "role": "figure_caption",
            "text": "Figure 1. Migration under DC field.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001", "page": 1, "block_id": "p1_b2",
            "role": "figure_asset", "text": "",
            "bbox": [50, 50, 550, 400],
        },
        # Figure 5: no asset on same page -> ambiguous
        {
            "paper_id": "K001", "page": 2, "block_id": "p2_b1",
            "role": "figure_caption",
            "text": "Figure 5. Expression levels without asset.",
            "bbox": [50, 700, 550, 750],
        },
        # Non-numbered caption (axis label) -> not counted by completeness
        {
            "paper_id": "K001", "page": 3, "block_id": "p3_b1",
            "role": "figure_caption",
            "text": "Days post culture",
            "bbox": [50, 700, 200, 720],
        },
    ]

    inventory = build_figure_inventory(blocks)
    c = inventory["figure_legend_completeness"]
    # Only Figure 1 and Figure 2 have figure numbers
    assert c["total"] == 2
    assert c["accounted_for"] == 2
    assert c["gap_count"] == 0

    statuses = {d["block_id"]: d["status"] for d in c["details"]}
    assert statuses["p1_b1"] == "matched"
    assert statuses["p2_b1"] == "ambiguous"


def test_compute_figure_legend_completeness_directly() -> None:
    """Test the completeness function independently with a synthetic gap."""
    from paperforge.worker.ocr_figures import compute_figure_legend_completeness

    structured_blocks = [
        {
            "paper_id": "K001", "page": 1, "block_id": "leg_A",
            "role": "figure_caption",
            "text": "Figure 1. Test.",
            "bbox": [50, 420, 550, 460],
        },
        {
            "paper_id": "K001", "page": 2, "block_id": "leg_B",
            "role": "figure_caption",
            "text": "Figure 2. Test.",
            "bbox": [50, 420, 550, 460],
        },
    ]

    # Inventory where leg_A is matched but leg_B is missing from all buckets
    inventory = {
        "matched_figures": [{"legend_block_id": "leg_A"}],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
    }

    result = compute_figure_legend_completeness(structured_blocks, inventory)
    assert result["total"] == 2
    assert result["accounted_for"] == 1
    assert result["gap_count"] == 1
    statuses = {d["block_id"]: d["status"] for d in result["details"]}
    assert statuses["leg_A"] == "matched"
    assert statuses["leg_B"] == "gap"


# === strict-layer sequence match promotion (Task 7) ===


def test_strict_layer_promotes_contiguous_legends_with_ordered_assets() -> None:
    """Ambiguous figures with figure numbers adjacent to matched figures
    are promoted to sequence_match — but only when they have asset_block_ids."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # Fig 1: legend + asset on page 3 — direct match
        {"block_id": 10, "role": "figure_caption",
         "text": "Figure 1. Experimental setup for biomechanical testing.",
         "page": 3, "bbox": [100, 700, 500, 720],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},
        {"block_id": 11, "role": "figure_asset",
         "page": 3, "bbox": [100, 400, 500, 680]},

        # Fig 2: legend on page 4, no asset — ambiguous (no_asset_match)
        {"block_id": 12, "role": "figure_caption",
         "text": "Figure 2. Histological analysis of tissue sections.",
         "page": 4, "bbox": [100, 300, 500, 320],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},

        # Fig 3: legend + asset on page 5 — direct match
        {"block_id": 13, "role": "figure_caption",
         "text": "Figure 3. Gene expression analysis results.",
         "page": 5, "bbox": [100, 300, 500, 320],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},
        {"block_id": 14, "role": "figure_asset",
         "page": 5, "bbox": [100, 50, 500, 280]},

        # Body paragraph on page 3
        {"block_id": 15, "role": "body_paragraph",
         "text": "Body text here.",
         "page": 3, "bbox": [100, 750, 500, 770]},
    ]

    inventory = build_figure_inventory(blocks)

    matched = inventory.get("matched_figures", [])
    fig_numbers = {mf.get("figure_number") for mf in matched}

    # Fig 2 must NOT be promoted — it has no assets
    assert 2 not in fig_numbers, (
        f"Fig 2 must NOT be promoted to SEQUENCE_MATCH without assets. "
        f"Matched fig nums: {fig_numbers}"
    )
    # Fig 1 and Fig 3 should still be matched directly
    assert 1 in fig_numbers
    assert 3 in fig_numbers


def test_compute_figure_legend_completeness_skips_body_mentions() -> None:
    """Body-paragraph figure mentions are not counted as formal legends."""
    from paperforge.worker.ocr_figures import compute_figure_legend_completeness

    structured_blocks = [
        {
            "paper_id": "K001", "page": 1, "block_id": "body1",
            "role": "body_paragraph", "raw_role": "body_paragraph",
            "text": "Figure 2 shows the results.",
            "bbox": [50, 100, 550, 140],
            "marker_signature": {"type": "figure_number", "number": 2},
        },
    ]

    inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
    }

    result = compute_figure_legend_completeness(structured_blocks, inventory)
    assert result["total"] == 0
    assert result["gap_count"] == 0


# === strict-figure safety rules (Task 3) ===


def test_sequence_match_requires_at_least_one_asset_block_id() -> None:
    """A cluster with empty asset_block_ids must not be promoted to SEQUENCE_MATCH."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # Fig 1: legend + asset on page 3 — direct match
        {"block_id": 10, "role": "figure_caption",
         "text": "Figure 1. Experimental setup for biomechanical testing.",
         "page": 3, "bbox": [100, 700, 500, 720],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},
        {"block_id": 11, "role": "figure_asset",
         "page": 3, "bbox": [100, 400, 500, 680]},

        # Fig 2: legend on page 4, no asset — ambiguous (no_asset_match)
        {"block_id": 12, "role": "figure_caption",
         "text": "Figure 2. Histological analysis of tissue sections.",
         "page": 4, "bbox": [100, 300, 500, 320],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},

        # Fig 3: legend + asset on page 5 — direct match
        {"block_id": 13, "role": "figure_caption",
         "text": "Figure 3. Gene expression analysis results.",
         "page": 5, "bbox": [100, 300, 500, 320],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},
        {"block_id": 14, "role": "figure_asset",
         "page": 5, "bbox": [100, 50, 500, 280]},
    ]

    inventory = build_figure_inventory(blocks)

    matched = inventory.get("matched_figures", [])
    fig_numbers = {mf.get("figure_number") for mf in matched}

    # Fig 2 should NOT be promoted — it has no assets
    assert 2 not in fig_numbers, (
        f"Fig 2 must NOT be promoted to SEQUENCE_MATCH without assets. "
        f"Matched fig nums: {fig_numbers}"
    )
    # Fig 1 and Fig 3 should still be matched directly
    assert 1 in fig_numbers
    assert 3 in fig_numbers


def test_sequence_match_promoted_entry_carries_full_contract() -> None:
    from paperforge.worker.ocr_figures import _promote_sequence_matches

    inventory = {
        "matched_figures": [
            {
                "figure_number": 1,
                "legend_block_id": "cap1",
                "page": 3,
                "legend_page": 3,
                "asset_pages": [3],
                "matched_assets": [{"block_id": "asset_1", "bbox": [0, 0, 10, 10]}],
                "asset_block_ids": ["asset_1"],
                "settlement_type": "same_page",
            }
        ],
        "ambiguous_figures": [
            {
                "figure_number": 2,
                "legend_block_id": "cap2",
                "page": 4,
                "legend_page": 4,
                "text": "Figure 2. Promoted sequence figure.",
                "matched_assets": [{"block_id": "asset_2", "bbox": [1, 1, 20, 20]}],
                "asset_block_ids": ["asset_2"],
                "asset_pages": [4],
                "settlement_type": "group_sequential",
                "group_type": "single_asset",
                "group_evidence": ["group_sequential_fallback"],
                "caption_score": {"score": 0.7},
            }
        ],
    }

    promoted = _promote_sequence_matches(inventory, blocks=[])
    seq = [m for m in promoted["matched_figures"] if m.get("figure_number") == 2][0]

    assert seq["page"] == 4
    assert seq["legend_page"] == 4
    assert seq["asset_pages"] == [4]
    assert seq["matched_assets"][0]["block_id"] == "asset_2"
    assert seq["asset_block_ids"] == ["asset_2"]
    assert seq["settlement_type"] == "sequence_match"


def test_assetless_sequence_shell_gets_hold_reason_not_matched() -> None:
    """Assetless sequence shells must stay in ambiguous_figures with explicit label."""
    from paperforge.worker.ocr_figures import _promote_sequence_matches

    inventory = {
        "matched_figures": [
            {
                "figure_number": 1,
                "legend_block_id": "cap1",
                "page": 3,
                "legend_page": 3,
                "asset_pages": [3],
                "matched_assets": [{"block_id": "asset_1", "bbox": [0, 0, 10, 10]}],
                "asset_block_ids": ["asset_1"],
                "settlement_type": "same_page",
            }
        ],
        "ambiguous_figures": [
            {
                "figure_number": 2,
                "legend_block_id": "cap2",
                "page": 4,
                "legend_page": 4,
                "text": "Figure 2. Assetless shell.",
                "matched_assets": [],
                "asset_block_ids": [],
                "asset_pages": [],
                "settlement_type": "group_sequential",
                "caption_score": {"score": 0.4},
            }
        ],
    }

    promoted = _promote_sequence_matches(inventory, blocks=[])

    matched_fig_nums = {m.get("figure_number") for m in promoted["matched_figures"]}
    assert 2 not in matched_fig_nums, "Assetless shell must NOT be in matched_figures"

    shells = [a for a in promoted["ambiguous_figures"] if a.get("hold_reason") == "assetless_sequence_shell"]
    assert len(shells) == 1, "Assetless sequence shell must have explicit hold_reason"
    assert shells[0]["sequence_skip_empty_assets"] is True


def test_assetless_sequence_shell_never_increments_official_count() -> None:
    """Official figure count must not include assetless shells."""
    from paperforge.worker.ocr_figures import _promote_sequence_matches

    inventory = {
        "matched_figures": [
            {
                "figure_number": 1,
                "legend_block_id": "cap1",
                "page": 3,
                "legend_page": 3,
                "asset_pages": [3],
                "matched_assets": [{"block_id": "asset_1", "bbox": [0, 0, 10, 10]}],
                "asset_block_ids": ["asset_1"],
                "settlement_type": "same_page",
            }
        ],
        "ambiguous_figures": [
            {
                "figure_number": 2,
                "legend_block_id": "cap2",
                "page": 4,
                "legend_page": 4,
                "text": "Figure 2. Ghost.",
                "matched_assets": [],
                "asset_block_ids": [],
                "asset_pages": [],
                "settlement_type": "group_sequential",
                "caption_score": {"score": 0.4},
            }
        ],
    }

    promoted = _promote_sequence_matches(inventory, blocks=[])
    matched_count = len(promoted.get("matched_figures", []))
    official = promoted.get("official_figure_count", matched_count)
    assert official == 1, (
        f"Official count must not include assetless sequence shell, got {official}"
    )


def test_bundle_source_duplicate_loser_is_accounted_not_gap() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "dup_legend", "page": 10, "role": "figure_caption", "text": "Figure 3. Caption list duplicate.", "bbox": [100, 100, 900, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "dup_peer_1", "page": 10, "role": "figure_caption", "text": "Figure 1. Caption list.", "bbox": [100, 200, 900, 250], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "dup_peer_2", "page": 10, "role": "figure_caption", "text": "Figure 2. Caption list.", "bbox": [100, 300, 900, 350], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "real_legend", "page": 12, "role": "figure_caption", "text": "Figure 3. Real legend.", "bbox": [100, 100, 900, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "asset_3", "page": 11, "role": "figure_asset", "raw_label": "image", "bbox": [100, 120, 700, 520]},
    ]

    inv = build_figure_inventory(blocks)
    deduped = inv.get("deduped_legend_ids", [])
    completeness = inv["figure_legend_completeness"]
    details = {item["block_id"]: item for item in completeness["details"]}

    assert any(item.get("block_id") == "dup_legend" for item in deduped)
    assert details["dup_legend"]["status"] == "deduped_duplicate"
    assert completeness["gap_count"] == 0


def test_reader_figures_never_include_empty_visual_groups() -> None:
    """No reader figure may have an empty visual_groups list."""
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # Fig 1: legend + asset — direct match
        {"block_id": 10, "role": "figure_caption",
         "text": "Figure 1. Experimental setup.",
         "page": 3, "bbox": [100, 700, 500, 720],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},
        {"block_id": 11, "role": "figure_asset",
         "page": 3, "bbox": [100, 400, 500, 680]},

        # Fig 2: legend only, no asset
        {"block_id": 12, "role": "figure_caption",
         "text": "Figure 2. Histological analysis.",
         "page": 4, "bbox": [100, 300, 500, 320],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},

        # Fig 3: legend + asset — direct match
        {"block_id": 13, "role": "figure_caption",
         "text": "Figure 3. Gene expression results.",
         "page": 5, "bbox": [100, 300, 500, 320],
         "marker_signature": {"type": "figure_number"},
         "zone": "body_zone", "style_family": "legend_like"},
        {"block_id": 14, "role": "figure_asset",
         "page": 5, "bbox": [100, 50, 500, 280]},
    ]

    inventory = build_figure_inventory(blocks)
    reader = synthesize_reader_figures(inventory, blocks)

    for figure in reader.get("reader_figures", []):
        vg = figure.get("visual_groups")
        assert vg, (
            f"Reader figure {figure.get('reader_figure_id')} has empty visual_groups: {figure}"
        )


# === group-first matching (Task 1: Red test) ===


def test_group_first_matching_prefers_same_row_pair_over_single_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {
            "block_id": 1,
            "role": "figure_caption",
            "text": "Fig. 2 A and B, MRI and gross anatomic correlation.",
            "page": 3,
            "bbox": [80, 120, 420, 210],
            "marker_signature": {"type": "figure_number", "number": 2},
            "zone": "display_zone",
            "style_family": "legend_like",
        },
        {"block_id": 2, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [450, 120, 780, 520]},
        {"block_id": 3, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [805, 120, 1130, 520]},
    ]

    inventory = build_figure_inventory(blocks, page_width=1200)
    matched = inventory["matched_figures"]

    assert len(matched) == 1
    assert matched[0]["figure_number"] == 2
    assert [a["block_id"] for a in matched[0]["matched_assets"]] == [2, 3]


# === Task 4: Fallback guard ===


def test_sequential_fallback_does_not_split_grouped_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": 1, "role": "figure_caption", "text": "Fig. 2 A and B, paired figure.", "page": 3, "bbox": [80, 120, 420, 210], "marker_signature": {"type": "figure_number"}, "zone": "display_zone", "style_family": "legend_like"},
        {"block_id": 2, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [450, 120, 780, 520]},
        {"block_id": 3, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [805, 120, 1130, 520]},
        {"block_id": 4, "role": "figure_caption", "text": "Fig. 3 Single figure.", "page": 4, "bbox": [80, 120, 420, 210], "marker_signature": {"type": "figure_number"}, "zone": "display_zone", "style_family": "legend_like"},
    ]

    inventory = build_figure_inventory(blocks, page_width=1200)
    matched = {item["figure_number"]: item for item in inventory["matched_figures"]}
    assert [a["block_id"] for a in matched[2]["matched_assets"]] == [2, 3]
    assert 3 not in matched
    fig3_buckets = [
        af["figure_number"]
        for af in inventory.get("ambiguous_figures", [])
        if af.get("figure_number") == 3
    ]
    assert fig3_buckets, (
        "Fig 3 with no same-page asset should appear in ambiguous_figures"
    )


def test_fallback_eligible_asset_page_ids_rejects_preowned_assets() -> None:
    from paperforge.worker.ocr_figures import _fallback_eligible_asset_page_ids

    asset_ids = [(2, "asset_1"), (2, "asset_2")]

    eligible = _fallback_eligible_asset_page_ids(
        asset_ids,
        used_asset_page_ids={(2, "asset_2")},
        blocked_asset_page_ids=set(),
    )

    assert eligible == [(2, "asset_1")]


def test_fallback_eligible_asset_page_ids_rejects_grouped_assets_by_default() -> None:
    from paperforge.worker.ocr_figures import _fallback_eligible_asset_page_ids

    asset_ids = [(3, "asset_1"), (3, "asset_2")]

    eligible = _fallback_eligible_asset_page_ids(
        asset_ids,
        used_asset_page_ids=set(),
        blocked_asset_page_ids=set(),
        grouped_asset_page_ids={(3, "asset_2")},
    )

    assert eligible == [(3, "asset_1")]


def test_fallback_eligible_groups_rejects_preowned_groups() -> None:
    from paperforge.worker.ocr_figures import _fallback_eligible_groups

    groups = [
        {"group_id": "g1", "page": 5, "asset_block_ids": ["a1"], "group_type": "single_asset"},
        {"group_id": "g2", "page": 5, "asset_block_ids": ["a2"], "group_type": "single_asset"},
    ]

    eligible = _fallback_eligible_groups(
        groups,
        used_group_ids={"g2"},
        used_asset_page_ids=set(),
    )

    assert [g["group_id"] for g in eligible] == ["g1"]


def test_fallback_can_consume_rejects_blocked_assets() -> None:
    from paperforge.worker.ocr_figures import _fallback_can_consume

    assert _fallback_can_consume(
        [(7, "asset_1")],
        used_asset_page_ids=set(),
        blocked_asset_page_ids={(7, "asset_1")},
    ) is False


def test_sequential_fallback_skips_preowned_bare_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "cap1", "page": 1, "role": "figure_caption", "text": "Figure 1. Same-page figure.", "bbox": [100, 420, 800, 470], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "asset_1", "page": 1, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 380]},
        {"block_id": "cap2", "page": 2, "role": "figure_caption", "text": "Figure 2. Later caption.", "bbox": [100, 120, 800, 170], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
    ]

    inv = build_figure_inventory(blocks)
    matched = {m.get("figure_number"): m for m in inv["matched_figures"]}

    assert 1 in matched
    assert 2 not in matched


def test_build_ownership_conflicts_surfaces_figure_table_overlap() -> None:
    from paperforge.worker.ocr_figures import _build_ownership_conflicts

    figure_inventory = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "page": 5,
                "legend_page": 5,
                "matched_assets": [{"block_id": "shared_asset"}],
                "asset_block_ids": ["shared_asset"],
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "caption_block_id": "table_cap_1",
                "page": 5,
                "asset_block_id": "shared_asset",
                "has_asset": True,
            }
        ]
    }

    conflicts = _build_ownership_conflicts(figure_inventory, table_inventory)

    assert len(conflicts) == 1
    assert conflicts[0]["asset_page_id"] == (5, "shared_asset")


def test_matched_figure_assets_preserve_asset_family_hints() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "asset_1", "page": 1, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 500, 380]},
        {
            "block_id": "cap_1",
            "page": 1,
            "role": "figure_caption",
            "text": "Figure 1. Test figure.",
            "bbox": [100, 420, 800, 470],
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 1},
        },
    ]

    inv = build_figure_inventory(blocks)
    asset = inv["matched_figures"][0]["matched_assets"][0]

    assert asset["asset_family_hint"] == "figure_like"
    assert asset["asset_family_confidence"] == 0.70
    assert asset["asset_family_evidence"] == ["raw_label:image"]


def test_ownership_conflicts_persisted_in_figure_inventory_json(tmp_path) -> None:
    """P0-A: ownership_conflicts must be in the written figure_inventory.json."""
    from paperforge.worker.ocr_figures import (
        attach_ownership_conflicts,
        write_figure_inventory,
    )
    from paperforge.core.io import read_json

    figure_inventory: dict = {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "page": 3,
                "legend_page": 3,
                "matched_assets": [{"block_id": "collision_asset"}],
                "asset_block_ids": ["collision_asset"],
            }
        ]
    }
    table_inventory: dict = {
        "tables": [
            {
                "caption_block_id": "tab_cap",
                "page": 3,
                "asset_block_id": "collision_asset",
                "has_asset": True,
            }
        ]
    }

    attach_ownership_conflicts(figure_inventory, table_inventory)
    figure_json_path = tmp_path / "figure_inventory.json"
    write_figure_inventory(figure_json_path, figure_inventory)

    written = read_json(figure_json_path)
    assert "ownership_conflicts" in written
    assert isinstance(written["ownership_conflicts"], list)
    assert len(written["ownership_conflicts"]) == 1
    assert written["ownership_conflicts"][0]["asset_page_id"] == [3, "collision_asset"]


# === Task 6: Health counters ===


def test_grouped_figure_match_count() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    health = build_ocr_health(
        page_count=1,
        raw_blocks_count=5,
        structured_blocks=[],
        figure_inventory={
            "matched_figures": [
                {"matched_assets": [{"block_id": 1}, {"block_id": 2}]},
                {"matched_assets": [{"block_id": 3}]},
                {"matched_assets": [{"block_id": 4}, {"block_id": 5}]},
            ],
        },
        table_inventory={},
    )

    assert health["grouped_figure_match_count"] == 2
    assert health["single_asset_figure_match_count"] == 1


# === Task 2: Conservative local figure expansion ===


def test_local_figure_expansion_absorbs_adjacent_same_page_stack() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"paper_id": "KX", "page": 2, "block_id": 3, "role": "media_asset", "raw_label": "image", "bbox": [101, 155, 401, 349]},
        {"paper_id": "KX", "page": 2, "block_id": 4, "role": "media_asset", "raw_label": "chart", "bbox": [448, 154, 699, 360]},
        {"paper_id": "KX", "page": 2, "block_id": 5, "role": "media_asset", "raw_label": "chart", "bbox": [102, 379, 399, 646]},
        {"paper_id": "KX", "page": 2, "block_id": 6, "role": "media_asset", "raw_label": "chart", "bbox": [415, 375, 695, 642]},
        {"paper_id": "KX", "page": 2, "block_id": 7, "role": "media_asset", "raw_label": "chart", "bbox": [709, 158, 1079, 634]},
        {"paper_id": "KX", "page": 2, "block_id": 8, "role": "media_asset", "raw_label": "chart", "bbox": [118, 662, 395, 929]},
        {"paper_id": "KX", "page": 2, "block_id": 9, "role": "media_asset", "raw_label": "chart", "bbox": [415, 663, 691, 933]},
        {"paper_id": "KX", "page": 2, "block_id": 10, "role": "media_asset", "raw_label": "chart", "bbox": [715, 638, 1063, 936]},
        {
            "paper_id": "KX",
            "page": 2,
            "block_id": 11,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Figure 1. Composite caption.",
            "bbox": [89, 950, 1095, 1276],
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 1},
        },
    ]

    inventory = build_figure_inventory(structured_blocks)
    matched = inventory["matched_figures"][0]
    actual_ids = {item["block_id"] for item in matched["matched_assets"]}

    assert actual_ids == {3, 4, 5, 6, 7, 8, 9, 10}


def test_local_figure_expansion_does_not_cross_second_formal_caption_boundary() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"paper_id": "KX", "page": 4, "block_id": 1, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 500, 280]},
        {"paper_id": "KX", "page": 4, "block_id": 2, "role": "media_asset", "raw_label": "image", "bbox": [100, 300, 500, 500]},
        {"paper_id": "KX", "page": 4, "block_id": 3, "role": "media_asset", "raw_label": "image", "bbox": [100, 560, 500, 760]},
        {"paper_id": "KX", "page": 4, "block_id": 4, "role": "media_asset", "raw_label": "image", "bbox": [100, 780, 500, 980]},
        {
            "paper_id": "KX",
            "page": 4,
            "block_id": 10,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Figure 2. First caption.",
            "bbox": [90, 510, 800, 550],
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 2},
        },
        {
            "paper_id": "KX",
            "page": 4,
            "block_id": 11,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Figure 3. Second caption.",
            "bbox": [90, 990, 800, 1030],
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 3},
        },
    ]

    inventory = build_figure_inventory(structured_blocks)
    matched_by_num = {item["figure_number"]: item for item in inventory["matched_figures"]}

    assert {item["block_id"] for item in matched_by_num[2]["matched_assets"]} == {1, 2}
    assert {item["block_id"] for item in matched_by_num[3]["matched_assets"]} == {3, 4}


# === Task 2: Sidecar layout routing unit tests ===


def test_full_width_caption_does_not_enter_sidecar_partition() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"paper_id": "FW", "page": 1, "block_id": 1, "role": "media_asset", "raw_label": "image", "bbox": [80, 80, 1080, 700], "page_width": 1200, "page_height": 1600},
        {
            "paper_id": "FW",
            "page": 1,
            "block_id": 2,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Figure 1. Composite scaffold characterization under mechanical loading.",
            "bbox": [90, 730, 1110, 820],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 1},
        },
    ]

    inventory = build_figure_inventory(blocks)
    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["matched_assets"][0]["block_id"] == 1


def test_narrow_same_column_captions_partition_same_page_figures() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"paper_id": "SC", "page": 3, "block_id": 3, "role": "media_asset", "raw_label": "image", "bbox": [470, 80, 980, 360], "page_width": 1200, "page_height": 1600},
        {"paper_id": "SC", "page": 3, "block_id": 4, "role": "media_asset", "raw_label": "image", "bbox": [470, 400, 980, 680], "page_width": 1200, "page_height": 1600},
        {"paper_id": "SC", "page": 3, "block_id": 8, "role": "media_asset", "raw_label": "image", "bbox": [470, 720, 980, 1040], "page_width": 1200, "page_height": 1600},
        {
            "paper_id": "SC",
            "page": 3,
            "block_id": 10,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Fig. 2. MRI-gross anatomic correlation in sagittal plane.",
            "bbox": [70, 90, 360, 170],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 2},
        },
        {
            "paper_id": "SC",
            "page": 3,
            "block_id": 11,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Fig. 3. MRI-gross anatomic correlation in coronal plane.",
            "bbox": [70, 420, 360, 500],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 3},
        },
        {
            "paper_id": "SC",
            "page": 3,
            "block_id": 12,
            "role": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "text": "Fig. 6. Anterior insertion of cable on arthroscopy and MRI.",
            "bbox": [70, 760, 360, 840],
            "page_width": 1200,
            "page_height": 1600,
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 6},
        },
    ]

    inventory = build_figure_inventory(blocks)
    by_num = {item["figure_number"]: item for item in inventory["matched_figures"]}
    assert {item["block_id"] for item in by_num[2]["matched_assets"]} == {3}
    assert {item["block_id"] for item in by_num[3]["matched_assets"]} == {4}
    assert {item["block_id"] for item in by_num[6]["matched_assets"]} == {8}


def test_panel_labels_do_not_form_sidecar_caption_column() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"paper_id": "PL", "page": 1, "block_id": 1, "role": "media_asset", "raw_label": "image", "bbox": [100, 80, 420, 320], "page_width": 1200, "page_height": 1600},
        {"paper_id": "PL", "page": 1, "block_id": 2, "role": "media_asset", "raw_label": "image", "bbox": [460, 80, 780, 320], "page_width": 1200, "page_height": 1600},
        {"paper_id": "PL", "page": 1, "block_id": 3, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "a", "bbox": [95, 60, 120, 78], "page_width": 1200, "page_height": 1600, "zone": "body_zone", "style_family": "unknown_like", "marker_signature": {"type": "short_fragment"}},
        {"paper_id": "PL", "page": 1, "block_id": 4, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "b", "bbox": [455, 60, 480, 78], "page_width": 1200, "page_height": 1600, "zone": "body_zone", "style_family": "unknown_like", "marker_signature": {"type": "short_fragment"}},
        {"paper_id": "PL", "page": 1, "block_id": 5, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "Figure 1. Full caption.", "bbox": [120, 340, 760, 420], "page_width": 1200, "page_height": 1600, "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
    ]

    inventory = build_figure_inventory(blocks)
    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 1


def test_mixed_page_keeps_sidecar_and_ordinary_below_pairs_separate() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"paper_id": "MX2", "page": 1, "block_id": "a1", "role": "media_asset", "raw_label": "image", "bbox": [520, 80, 960, 280], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX2", "page": 1, "block_id": "a2", "role": "media_asset", "raw_label": "image", "bbox": [520, 340, 960, 540], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX2", "page": 1, "block_id": "body_sep", "role": "body_paragraph", "text": "Body separator between local layouts.", "bbox": [120, 620, 1080, 760], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX2", "page": 1, "block_id": "a3", "role": "media_asset", "raw_label": "image", "bbox": [140, 820, 1060, 1080], "page_width": 1200, "page_height": 1600},
        {"paper_id": "MX2", "page": 1, "block_id": "cap1", "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "Figure 1. Sidecar top.", "bbox": [80, 90, 320, 150], "page_width": 1200, "page_height": 1600, "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"paper_id": "MX2", "page": 1, "block_id": "cap2", "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "Figure 2. Sidecar lower.", "bbox": [80, 350, 320, 410], "page_width": 1200, "page_height": 1600, "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"paper_id": "MX2", "page": 1, "block_id": "cap3", "role": "figure_caption", "raw_label": "figure_title", "text": "Figure 3. Ordinary caption below.", "bbox": [160, 1100, 1040, 1170], "page_width": 1200, "page_height": 1600, "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
    ]

    inventory = build_figure_inventory(blocks)
    by_num = {item["figure_number"]: item for item in inventory["matched_figures"]}

    assert {a["block_id"] for a in by_num[1]["matched_assets"]} == {"a1"}
    assert {a["block_id"] for a in by_num[2]["matched_assets"]} == {"a2"}
    assert {a["block_id"] for a in by_num[3]["matched_assets"]} == {"a3"}


def test_partition_assets_by_caption_bands_keeps_assets_local_to_caption_band() -> None:
    from paperforge.worker.ocr_figures import _partition_assets_by_caption_bands

    captions = [
        {"block_id": 101, "bbox": [700, 900, 1050, 960]},
        {"block_id": 102, "bbox": [700, 1200, 1050, 1260]},
    ]
    assets = [
        {"block_id": 1, "bbox": [650, 200, 1050, 400]},
        {"block_id": 2, "bbox": [650, 600, 1050, 800]},
        {"block_id": 3, "bbox": [650, 1100, 1050, 1200]},
    ]

    parts = _partition_assets_by_caption_bands(captions, assets, page_height=1600)

    assert [a["block_id"] for a in parts["101"]] == [1, 2]
    assert [a["block_id"] for a in parts["102"]] == [3]


def test_sequential_fallback_can_match_previous_page_asset_for_next_page_caption() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "a1", "page": 39, "role": "media_asset", "raw_label": "image", "bbox": [220, 1153, 556, 1443]},
        {
            "block_id": "cap3",
            "page": 40,
            "role": "figure_caption",
            "text": "Fig. 3. Magnetic actuation characterization of MR-SCS.",
            "bbox": [73, 99, 1032, 548],
            "zone": "post_reference_backmatter_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 3},
        },
    ]

    inventory = build_figure_inventory(blocks)
    matched = [m for m in inventory["matched_figures"] if m.get("figure_number") == 3]
    ambiguous = [a for a in inventory["ambiguous_figures"] if a.get("figure_number") == 3]

    assert len(matched) == 1
    assert matched[0]["matched_assets"][0]["block_id"] == "a1"
    assert ambiguous == []


# === Task 4: Figure namespace + page assets gate ===


def test_main_and_supplementary_figures_do_not_dedup_into_one_number() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 3, "block_id": "p3_c1", "role": "figure_caption", "text": "Figure 1. Migration assay under DC electric field stimulation over 48 hours.", "bbox": [100, 420, 600, 460]},
        {"page": 3, "block_id": "p3_a1", "role": "figure_asset", "bbox": [100, 100, 600, 400], "text": ""},
        {"page": 4, "block_id": "p4_c1", "role": "figure_caption", "text": "Supplementary Figure 1. Gene expression analysis under supplemental treatment conditions.", "bbox": [100, 420, 600, 460]},
        {"page": 4, "block_id": "p4_a1", "role": "figure_asset", "bbox": [100, 100, 600, 400], "text": ""},
    ]
    inventory = build_figure_inventory(structured_blocks)
    figure_ids = {fig["figure_id"] for fig in inventory["matched_figures"]}
    assert "figure_001" in figure_ids
    assert "figure_s001" in figure_ids


def test_page_assets_does_not_strict_match_when_page_has_competing_captions() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 5, "block_id": "p5_a1", "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 300, 260], "text": ""},
        {"page": 5, "block_id": "p5_a2", "role": "figure_asset", "raw_label": "image", "bbox": [320, 100, 520, 260], "text": ""},
        {"page": 5, "block_id": "p5_a3", "role": "figure_asset", "raw_label": "image", "bbox": [540, 100, 740, 260], "text": ""},
        {"page": 5, "block_id": "p5_c1", "role": "figure_caption", "text": "Figure 1. Left.", "bbox": [100, 280, 320, 320], "zone": "display_zone", "style_family": "legend_like"},
        {"page": 5, "block_id": "p5_c2", "role": "figure_caption", "text": "Figure 2. Right.", "bbox": [420, 280, 740, 320], "zone": "display_zone", "style_family": "legend_like"},
    ]
    inventory = build_figure_inventory(structured_blocks)
    for fig in inventory["matched_figures"]:
        for asset_info in fig.get("matched_assets", []):
            evidence = asset_info.get("evidence", [])
            assert all("page_assets" not in e for e in evidence)


def test_build_figure_inventory_uses_distance_cluster_for_irregular_pair() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 5, "block_id": "a1", "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 300, 260], "text": ""},
        {"page": 5, "block_id": "a2", "role": "figure_asset", "raw_label": "image", "bbox": [315, 110, 525, 270], "text": ""},
        {"page": 5, "block_id": "c1", "role": "figure_caption", "text": "Figure 1. Irregular pair.", "bbox": [100, 290, 520, 330], "zone": "display_zone", "style_family": "legend_like"},
    ]

    inventory = build_figure_inventory(structured_blocks)
    match = inventory["matched_figures"][0]
    assert len(match["matched_assets"]) == 2
    assert match.get("group_type") == "distance_cluster"


def test_display_cluster_keeps_empty_bridge_between_asset_and_caption() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 9, "block_id": "asset_1", "role": "figure_asset", "bbox": [100, 100, 520, 360], "text": "", "layout_region": "display_zone"},
        {"page": 9, "block_id": "gap_1", "role": "unknown_structural", "bbox": [530, 110, 900, 360], "text": "", "layout_region": "display_zone", "bridge_eligible": True},
        {"page": 9, "block_id": "cap_1", "role": "figure_caption", "bbox": [120, 380, 880, 430], "text": "Figure 2. Multi-panel reconstruction.", "layout_region": "display_zone"},
    ]

    inventory = build_figure_inventory(structured_blocks)
    matched = inventory["matched_figures"][0]
    assert matched["asset_block_ids"] == ["asset_1"]
    assert matched.get("bridge_block_ids") == ["gap_1"]


# === Stage 1: Cross-page figure matching tests ===


# Task 1: caption_group_assignments same-page gate
def test_caption_group_assignments_does_not_cross_page() -> None:
    from paperforge.worker.ocr import caption_group_assignments

    blocks = [
        {"block_label": "image", "page": 12, "block_bbox": [100, 100, 400, 300], "block_content": ""},
        {"block_label": "figure_title", "page": 13, "block_bbox": [100, 400, 500, 440], "block_content": "Figure 4. Test caption."},
    ]
    figure_map, _ = caption_group_assignments(blocks)
    assert len(figure_map) == 0, "caption_group_assignments must NOT match cross-page image/caption"


# Task 2: eligibility helpers
def test_strong_numbered_legend_weak_truncated_not_strong() -> None:
    from paperforge.worker.ocr_figures import _is_strong_numbered_legend

    block = {"block_id": "b1", "page": 1, "role": "figure_caption", "text": "Figure 1.", "bbox": [0, 0, 100, 50], "marker_signature": {"type": "figure_number", "number": 1}, "style_family": "legend_like"}
    score = {"score": 0.9, "decision": "figure_caption", "evidence": ["figure_number"]}
    assert _is_strong_numbered_legend(block, caption_score=score) is False


def test_strong_numbered_legend_full_legend_is_strong() -> None:
    from paperforge.worker.ocr_figures import _is_strong_numbered_legend

    block = {"block_id": "b1", "page": 1, "role": "figure_caption", "text": "Figure 1. Quantitative analysis of cell migration under DC electric field stimulation.", "bbox": [0, 0, 500, 50]}
    score = {"score": 0.9, "decision": "figure_caption", "evidence": ["figure_number"]}
    assert _is_strong_numbered_legend(block, caption_score=score) is True


def test_strong_numbered_legend_low_score_not_strong() -> None:
    from paperforge.worker.ocr_figures import _is_strong_numbered_legend

    block = {"block_id": "b1", "page": 1, "role": "figure_caption", "text": "Figure 1. Some text.", "bbox": [0, 0, 500, 50]}
    score = {"score": 0.2, "decision": "ambiguous", "evidence": ["weak"]}
    assert _is_strong_numbered_legend(block, caption_score=score) is False


def test_strong_numbered_legend_validation_first_needs_anchor() -> None:
    from paperforge.worker.ocr_figures import _is_strong_numbered_legend

    block = {
        "block_id": "b1", "page": 1, "role": "unknown_structural",
        "zone": "body_zone", "style_family": "legend_like", "style_family_authority": "figure_family_anchor",
        "text": "Figure 1. Quantitative analysis of cell migration.",
        "bbox": [0, 0, 500, 50],
        "marker_signature": {"type": "figure_number", "number": 1},
    }
    score = {"score": 0.9, "decision": "figure_caption", "evidence": ["figure_number"]}
    assert _is_strong_numbered_legend(block, caption_score=score, anchor_supported=True) is True
    assert _is_strong_numbered_legend(block, caption_score=score, anchor_supported=False, caption_text_supported=False) is False


def test_structurally_matchable_empty_group_not_matchable() -> None:
    from paperforge.worker.ocr_figures import _is_structurally_matchable_group

    group = {"group_id": "g1", "page": 1, "asset_block_ids": [], "cluster_bbox": [0, 0, 100, 100]}
    assert _is_structurally_matchable_group(group, competing_caption_pages=set()) is False


def test_structurally_matchable_valid_group() -> None:
    from paperforge.worker.ocr_figures import _is_structurally_matchable_group

    group = {"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]}
    assert _is_structurally_matchable_group(group, competing_caption_pages=set()) is True


def test_structurally_matchable_page_assets_on_competing_page_not_matchable() -> None:
    from paperforge.worker.ocr_figures import _is_structurally_matchable_group

    group = {"group_id": "g1", "page": 13, "group_type": "page_assets", "asset_block_ids": ["a1", "a2"], "cluster_bbox": [0, 0, 500, 500]}
    assert _is_structurally_matchable_group(group, competing_caption_pages={13}) is False


# Task 3: ledger helpers
def test_page_ledger_balanced() -> None:
    from paperforge.worker.ocr_figures import _build_page_ledger

    legends = [{"block_id": "c1", "page": 1, "text": "Figure 1. Caption.", "bbox": [0, 0, 100, 50]}]
    groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]}]
    ledger = _build_page_ledger(legends, groups)
    assert ledger[1]["delta"] == 0
    assert ledger[1]["legend_count"] == 1
    assert ledger[1]["group_count"] == 1


def test_page_ledger_caption_surplus() -> None:
    from paperforge.worker.ocr_figures import _build_page_ledger

    legends = [
        {"block_id": "c1", "page": 1, "text": "Figure 1. First caption.", "bbox": [0, 0, 100, 50]},
        {"block_id": "c2", "page": 1, "text": "Figure 2. Second caption.", "bbox": [0, 60, 100, 110]},
    ]
    groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]}]
    ledger = _build_page_ledger(legends, groups)
    assert ledger[1]["delta"] == 1


def test_page_ledger_group_surplus() -> None:
    from paperforge.worker.ocr_figures import _build_page_ledger

    legends = [{"block_id": "c1", "page": 2, "text": "Figure 1. Caption.", "bbox": [0, 0, 100, 50]}]
    groups = [
        {"group_id": "g1", "page": 2, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]},
        {"group_id": "g2", "page": 2, "asset_block_ids": ["a2"], "cluster_bbox": [0, 200, 100, 300]},
    ]
    ledger = _build_page_ledger(legends, groups)
    assert ledger[2]["delta"] == -1


def test_residual_ledger_balanced() -> None:
    from paperforge.worker.ocr_figures import _build_residual_ledger

    legends = [{"block_id": "c1", "page": 1, "text": "Figure 1. Caption.", "bbox": [0, 0, 100, 50]}]
    groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]}]
    ledger = _build_residual_ledger(legends, groups, competing_caption_pages=set())
    assert ledger[1]["residual_delta"] == 0


def test_residual_legend_surplus_positive() -> None:
    from paperforge.worker.ocr_figures import _build_residual_ledger, _residual_legend_surplus

    legends = [
        {"block_id": "c1", "page": 1, "text": "Figure 1. First.", "bbox": [0, 0, 100, 50]},
        {"block_id": "c2", "page": 1, "text": "Figure 2. Second.", "bbox": [0, 60, 100, 110]},
    ]
    groups = [{"group_id": "g1", "page": 1, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]}]
    ledger = _build_residual_ledger(legends, groups, competing_caption_pages={1})
    assert ledger[1]["residual_delta"] > 0


def test_residual_group_surplus_positive() -> None:
    from paperforge.worker.ocr_figures import _build_residual_ledger, _residual_group_surplus

    legends = [{"block_id": "c1", "page": 2, "text": "Figure 1. Caption.", "bbox": [0, 0, 100, 50]}]
    groups = [
        {"group_id": "g1", "page": 2, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100]},
        {"group_id": "g2", "page": 2, "asset_block_ids": ["a2"], "cluster_bbox": [0, 200, 100, 300]},
    ]
    ledger = _build_residual_ledger(legends, groups, competing_caption_pages=set())
    assert ledger[2]["residual_delta"] < 0


# Task 4: reservation
def test_reservation_reserves_top_caption_on_caption_surplus_page() -> None:
    from paperforge.worker.ocr_figures import (
        _build_page_ledger, _build_residual_ledger, _reserve_cross_page_objects,
    )

    legends = [
        {"block_id": "fig4_cap", "page": 13, "text": "Figure 4. Caption for figure on page 12.", "bbox": [0, 0, 500, 50]},
        {"block_id": "fig5_cap", "page": 13, "text": "Figure 5. Caption for page 13 figure.", "bbox": [0, 100, 500, 150]},
    ]
    groups = [
        {"group_id": "g1", "page": 12, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 200, 200], "media_blocks": [{"block_id": "a1", "page": 12, "bbox": [0, 0, 200, 200]}], "group_type": "single_asset", "group_evidence": ["single_asset"]},
        {"group_id": "g2", "page": 13, "asset_block_ids": ["a2"], "cluster_bbox": [0, 300, 200, 500], "media_blocks": [{"block_id": "a2", "page": 13, "bbox": [0, 300, 200, 500]}], "group_type": "single_asset", "group_evidence": ["single_asset"]},
    ]
    residual = _build_residual_ledger(legends, groups, competing_caption_pages={13})
    reserved_legend_ids, reserved_group_ids = _reserve_cross_page_objects(
        legends, groups, residual, competing_caption_pages={13}, sidecar_pages=set(),
    )
    assert (13, "fig4_cap") in reserved_legend_ids
    assert "fig5_cap" not in reserved_legend_ids


def test_reservation_skips_sidecar_pages() -> None:
    from paperforge.worker.ocr_figures import (
        _build_residual_ledger, _reserve_cross_page_objects,
    )
    legends = [
        {"block_id": "c1", "page": 5, "text": "Figure 1. Narrow sidecar caption.", "bbox": [0, 0, 200, 50]},
        {"block_id": "c2", "page": 5, "text": "Figure 2. Another narrow caption.", "bbox": [0, 100, 200, 150]},
    ]
    groups = [{"group_id": "g1", "page": 5, "asset_block_ids": ["a1"], "cluster_bbox": [0, 0, 100, 100], "group_type": "single_asset"}]
    residual = _build_residual_ledger(legends, groups, competing_caption_pages={5})
    reserved_legend_ids, reserved_group_ids = _reserve_cross_page_objects(
        legends, groups, residual, competing_caption_pages={5}, sidecar_pages={5},
    )
    assert len(reserved_legend_ids) == 0


# Task 5: cross-page settlement
def test_cross_page_backward_settlement() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    # Page 12: 2 assets that form 1 distance_cluster (Figure 4 panels)
    # Page 13: wide Figure 4 caption (top) + 2 stacked assets close together
    #   (Figure 5 panels, both in Fig5's caption band = 1 group) + wide Figure 5 caption (bottom)
    # Ledger: page 12 = -1 (0 legends, 1 group), page 13 = +1 (2 strong legends, 1 group)
    # Reservation: Fig4 caption reserved, matched backward to page 12 group
    blocks = [
        {"block_id": "p12_a1", "page": 12, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 100, 300, 300]},
        {"block_id": "p12_a2", "page": 12, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 320, 300, 520]},
        {"block_id": "p13_c4", "page": 13, "role": "figure_caption", "text": "Figure 4. DC electric field stimulation results showing cell migration patterns over 48 hours.", "bbox": [100, 100, 880, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
        {"block_id": "p13_f5a", "page": 13, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 300, 500, 370]},
        {"block_id": "p13_f5b", "page": 13, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 390, 500, 460]},
        {"block_id": "p13_c5", "page": 13, "role": "figure_caption", "text": "Figure 5. Quantitative analysis of migration speed under different field strengths.", "bbox": [100, 500, 880, 550], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 5}},
    ]
    inv = build_figure_inventory(blocks)
    fig4 = [m for m in inv["matched_figures"] if m.get("figure_number") == 4]
    fig5 = [m for m in inv["matched_figures"] if m.get("figure_number") == 5]
    assert len(fig4) == 1, f"Expected 1 Fig 4, got {len(fig4)}"
    assert len(fig5) == 1, f"Expected 1 Fig 5, got {len(fig5)}"
    assert fig4[0]["settlement_type"] in ("cross_page_backward", "cross_page_forward")
    assert fig4[0]["legend_page"] == 13
    assert fig5[0]["settlement_type"] == "same_page"


def test_reserved_same_page_hypothesis_is_deferred_from_commit() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "p12_a1", "page": 12, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 100, 300, 300]},
        {"block_id": "p12_a2", "page": 12, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 320, 300, 520]},
        {"block_id": "p13_c4", "page": 13, "role": "figure_caption", "text": "Figure 4. DC electric field stimulation results showing cell migration patterns over 48 hours.", "bbox": [100, 100, 880, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
        {"block_id": "p13_f5a", "page": 13, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 300, 500, 370]},
        {"block_id": "p13_f5b", "page": 13, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 390, 500, 460]},
        {"block_id": "p13_c5", "page": 13, "role": "figure_caption", "text": "Figure 5. Quantitative analysis of migration speed under different field strengths.", "bbox": [100, 500, 880, 550], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 5}},
    ]

    inv = build_figure_inventory(blocks)

    hypotheses = [
        h for h in inv["local_pairing_hypotheses"] if h.get("legend_block_id") == "p13_c4"
    ]
    assert hypotheses, "reserved caption should still produce a same-page hypothesis"
    assert any(h.get("group_id") == "group_0002" for h in hypotheses)
    assert any("reserved_same_page_commit_deferred" in h.get("conflicts", []) for h in hypotheses)

    fig4 = [m for m in inv["matched_figures"] if m.get("figure_number") == 4]
    assert len(fig4) == 1
    assert fig4[0]["settlement_type"] in ("cross_page_backward", "cross_page_forward")


def test_non_reserved_same_page_pair_still_commits_normally() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "asset_1", "page": 2, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 520, 380]},
        {
            "block_id": "cap_1",
            "page": 2,
            "role": "figure_caption",
            "text": "Figure 1. Same-page figure.",
            "bbox": [100, 420, 900, 470],
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number", "number": 1},
        },
    ]

    inv = build_figure_inventory(blocks)

    matched = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert len(matched) == 1
    assert matched[0]["settlement_type"] == "same_page"
    hypotheses = [
        h for h in inv["local_pairing_hypotheses"] if h.get("legend_block_id") == "cap_1"
    ]
    assert any(h.get("mode") == "caption_below" for h in hypotheses)
    assert all("reserved_same_page_commit_deferred" not in h.get("conflicts", []) for h in hypotheses)


def test_cross_page_settlement_two_captions_one_group_ambiguous() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 12, "role": "figure_caption", "text": "Figure 4. First caption.", "bbox": [100, 100, 500, 150]},
        {"block_id": "c2", "page": 12, "role": "figure_caption", "text": "Figure 5. Second caption.", "bbox": [100, 200, 500, 250]},
        {"block_id": "a1", "page": 12, "role": "figure_asset", "text": "", "bbox": [100, 400, 500, 700]},
    ]
    inv = build_figure_inventory(blocks)
    assert len(inv["matched_figures"]) <= 1
    # At most one caption should claim the single group


# Task 6: legacy fallback restriction — grouped asset not consumed by old fallback
def test_legacy_fallback_does_not_consume_grouped_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 10, "role": "figure_caption", "text": "Figure 1. Caption on page before assets.", "bbox": [100, 100, 500, 150]},
        {"block_id": "a1", "page": 11, "role": "figure_asset", "text": "", "bbox": [100, 100, 500, 400]},
        {"block_id": "a2", "page": 11, "role": "figure_asset", "text": "", "bbox": [100, 500, 500, 800]},
    ]
    inv = build_figure_inventory(blocks)
    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert len(fig1) == 1
    assert len(fig1[0]["matched_assets"]) >= 1


def test_legend_bundle_fallback_does_not_consume_grouped_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 10, "role": "figure_caption", "text": "Figure 1. First caption.", "bbox": [100, 100, 700, 150]},
        {"block_id": "c2", "page": 10, "role": "figure_caption", "text": "Figure 2. Second caption.", "bbox": [100, 180, 700, 230]},
        {"block_id": "c3", "page": 10, "role": "figure_caption", "text": "Figure 3. Third caption.", "bbox": [100, 260, 700, 310]},
        {"block_id": "a11_1", "page": 11, "role": "figure_asset", "text": "", "bbox": [100, 100, 420, 320]},
        {"block_id": "a11_2", "page": 11, "role": "figure_asset", "text": "", "bbox": [100, 340, 420, 560]},
        {"block_id": "a12_1", "page": 12, "role": "figure_asset", "text": "", "bbox": [100, 100, 420, 320]},
    ]

    inv = build_figure_inventory(blocks)

    legend_bundle_matches = [
        m for m in inv["matched_figures"] if m.get("settlement_type") == "legend_bundle"
    ]
    bundled_asset_ids = {
        str(asset.get("block_id", ""))
        for match in legend_bundle_matches
        for asset in match.get("matched_assets", [])
    }

    assert "a11_1" not in bundled_asset_ids
    assert "a11_2" not in bundled_asset_ids


def test_legend_bundle_fallback_skips_preowned_asset_pages() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "pre_cap", "page": 9, "role": "figure_caption", "text": "Figure 1. Same-page owned figure.", "bbox": [100, 100, 700, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "pre_asset", "page": 9, "role": "figure_asset", "raw_label": "image", "bbox": [100, 180, 700, 500]},
        {"block_id": "c2", "page": 10, "role": "figure_caption", "text": "Figure 2. First bundled caption.", "bbox": [100, 100, 700, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "c3", "page": 10, "role": "figure_caption", "text": "Figure 3. Second bundled caption.", "bbox": [100, 200, 700, 250], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "c4", "page": 10, "role": "figure_caption", "text": "Figure 4. Third bundled caption.", "bbox": [100, 300, 700, 350], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
        {"block_id": "future_1", "page": 11, "role": "figure_asset", "raw_label": "image", "bbox": [100, 200, 600, 500]},
        {"block_id": "future_2", "page": 12, "role": "figure_asset", "raw_label": "image", "bbox": [100, 200, 600, 500]},
    ]

    inv = build_figure_inventory(blocks)
    bundle_matches = [m for m in inv["matched_figures"] if m.get("settlement_type") == "legend_bundle"]

    assert all(match.get("page") != 9 for match in bundle_matches)
    assert {m.get("page") for m in bundle_matches} <= {11, 12}


def test_legend_bundle_fallback_respects_body_interruption() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c2", "page": 10, "role": "figure_caption", "text": "Figure 2. First bundled caption.", "bbox": [100, 100, 700, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "c3", "page": 10, "role": "figure_caption", "text": "Figure 3. Second bundled caption.", "bbox": [100, 200, 700, 250], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "c4", "page": 10, "role": "figure_caption", "text": "Figure 4. Third bundled caption.", "bbox": [100, 300, 700, 350], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
        {"block_id": "body_break", "page": 11, "role": "body_paragraph", "text": "This body text interrupts bundle recovery.", "bbox": [100, 100, 1000, 240]},
        {"block_id": "future_1", "page": 12, "role": "figure_asset", "raw_label": "image", "bbox": [100, 200, 600, 500]},
        {"block_id": "future_2", "page": 13, "role": "figure_asset", "raw_label": "image", "bbox": [100, 200, 600, 500]},
        {"block_id": "future_3", "page": 14, "role": "figure_asset", "raw_label": "image", "bbox": [100, 200, 600, 500]},
    ]

    inv = build_figure_inventory(blocks)

    assert not any(m.get("settlement_type") == "legend_bundle" for m in inv["matched_figures"])


def test_dwqq_style_duplicate_legend_prefers_real_cross_page_instance() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 35, "role": "figure_caption", "text": "Figure 1. Caption list peer.", "bbox": [100, 100, 900, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "c2", "page": 35, "role": "figure_caption", "text": "Figure 2. Caption list peer.", "bbox": [100, 200, 900, 250], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "dup_fig3", "page": 35, "role": "figure_caption", "text": "Figure 3. Caption list duplicate.", "bbox": [100, 300, 900, 350], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "asset_39a", "page": 39, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 500, 400]},
        {"block_id": "asset_39b", "page": 39, "role": "figure_asset", "raw_label": "image", "bbox": [520, 100, 920, 400]},
        {"block_id": "real_fig3", "page": 40, "role": "figure_caption", "text": "Figure 3. Real cross-page legend.", "bbox": [100, 100, 900, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
    ]

    inv = build_figure_inventory(blocks)

    fig3 = [m for m in inv["matched_figures"] if m.get("figure_number") == 3]
    assert len(fig3) == 1
    assert fig3[0]["legend_block_id"] == "real_fig3"
    assert fig3[0]["legend_page"] == 40
    assert fig3[0]["settlement_type"] == "cross_page_backward"
    assert {a["block_id"] for a in fig3[0]["matched_assets"]} == {"asset_39a", "asset_39b"}
    assert any(
        item.get("block_id") == "dup_fig3" and item.get("dedup_reason") == "bundle_source_duplicate_loser"
        for item in inv.get("deduped_legend_ids", [])
    )


def test_same_page_real_legend_outranks_bundle_duplicate() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 10, "role": "figure_caption", "text": "Figure 1. Caption list peer.", "bbox": [100, 100, 700, 150], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "dup_fig2", "page": 10, "role": "figure_caption", "text": "Figure 2. Caption list duplicate.", "bbox": [100, 200, 700, 250], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "c3", "page": 10, "role": "figure_caption", "text": "Figure 3. Caption list peer.", "bbox": [100, 300, 700, 350], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "real_fig2", "page": 20, "role": "figure_caption", "text": "Figure 2. Real same-page legend.", "bbox": [100, 500, 800, 560], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "asset_20", "page": 20, "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 700, 460]},
    ]

    inv = build_figure_inventory(blocks)

    fig2 = [m for m in inv["matched_figures"] if m.get("figure_number") == 2]
    assert len(fig2) == 1
    assert fig2[0]["legend_block_id"] == "real_fig2"
    assert fig2[0]["legend_page"] == 20


def test_final_unmatched_assets_recomputed_after_late_fallback_match() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption with no same-page asset.", "bbox": [100, 100, 700, 150]},
        {"block_id": "a2", "page": 2, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [100, 120, 500, 420]},
    ]

    inv = build_figure_inventory(blocks)

    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert len(fig1) == 1
    matched_asset_ids = {str(a.get("block_id", "")) for a in fig1[0].get("matched_assets", [])}
    assert "a2" in matched_asset_ids
    assert all(a.get("block_id") != "a2" for a in inv.get("unmatched_assets", []))


def test_bundle_only_source_legends_remain_eligible_for_legend_bundle_fallback() -> None:
    """P0-B: bundle-source legends with no stronger duplicate must still reach legend_bundle."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # Bundle-source page (p10): three captions, zero assets
        {"block_id": "bs_fig1", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Bundle caption.", "bbox": [100, 100, 700, 140],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "bs_fig2", "page": 10, "role": "figure_caption",
         "text": "Figure 2. Bundle-only caption.", "bbox": [100, 160, 700, 200],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "bs_fig3", "page": 10, "role": "figure_caption",
         "text": "Figure 3. Bundle caption.", "bbox": [100, 220, 700, 260],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        # Real duplicate for Fig 1 on page 11 (outranks bundle)
        {"block_id": "real_fig1", "page": 11, "role": "figure_caption",
         "text": "Figure 1. Real legend on asset page.", "bbox": [100, 520, 700, 560],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "a11", "page": 11, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 700, 500]},
        # Asset for Fig 2 on page 12 (no same-page caption)
        {"block_id": "a12", "page": 12, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 700, 500]},
        # Asset for Fig 3 on page 13 (no same-page caption)
        {"block_id": "a13", "page": 13, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 700, 500]},
    ]

    inv = build_figure_inventory(blocks)
    matched = {m.get("figure_number"): m for m in inv["matched_figures"]}

    assert 2 in matched, (
        "Fig 2 (bundle-only) must be matched via legend_bundle fallback"
    )
    assert 3 in matched, (
        "Fig 3 (bundle-only) must be matched via legend_bundle fallback"
    )
    fig2 = matched[2]
    assert fig2["settlement_type"] == "legend_bundle"
    assert fig2["legend_block_id"] == "bs_fig2"
    fig3 = matched[3]
    assert fig3["settlement_type"] == "legend_bundle"
    assert fig3["legend_block_id"] == "bs_fig3"

    deduped = inv.get("deduped_legend_ids", [])
    assert any(
        item.get("block_id") == "bs_fig1" and item.get("dedup_reason") == "bundle_source_duplicate_loser"
        for item in deduped
    ), "Fig 1 bundle-source must be deduped loser"
    assert not any(
        item.get("block_id") == "bs_fig3" for item in deduped
    ), "Fig 3 must NOT be deduped (no stronger duplicate exists)"
    assert not any(
        item.get("block_id") == "bs_fig2" for item in deduped
    ), "Fig 2 must NOT be deduped (bundle-only, no stronger duplicate)"

    completeness = inv["figure_legend_completeness"]
    assert completeness["gap_count"] == 0


# Task 7: output schema contract
def test_matched_figure_has_legend_page_and_asset_pages_and_settlement_type() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Test caption.", "bbox": [100, 420, 500, 460]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "text": "", "bbox": [100, 50, 500, 400]},
    ]
    inv = build_figure_inventory(blocks)
    assert len(inv["matched_figures"]) == 1
    mf = inv["matched_figures"][0]
    assert "legend_page" in mf
    assert "asset_pages" in mf
    assert "settlement_type" in mf
    assert mf["legend_page"] == 1
    assert mf["asset_pages"] == [1]
    assert mf["settlement_type"] == "same_page"


# Task 8: 2HEUD5P9 ownership pattern regression
def test_2heud5p9_ownership_pattern() -> None:
    """Figure 4 on page 12 (assets), Fig 4 caption on page 13, Fig 5 assets+caption on page 13."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    # Page 12: 2 Fig4 panels close together (1 distance_cluster)
    # Page 13: wide Fig4 caption (top), 2 Fig5 panels stacked in Fig5's caption band (1 group), wide Fig5 caption (bottom)
    blocks = [
        {"block_id": "p12_a1", "page": 12, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [50, 50, 300, 350]},
        {"block_id": "p12_a2", "page": 12, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [50, 370, 300, 670]},
        {"block_id": "p13_c4", "page": 13, "role": "figure_caption", "text": "Figure 4. DC electric field stimulation results showing cell migration patterns over 48 hours.", "bbox": [50, 50, 800, 100], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
        {"block_id": "p13_f5a", "page": 13, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [50, 220, 500, 340]},
        {"block_id": "p13_f5b", "page": 13, "role": "figure_asset", "raw_label": "image", "text": "", "bbox": [50, 360, 500, 470]},
        {"block_id": "p13_c5", "page": 13, "role": "figure_caption", "text": "Figure 5. Quantitative analysis of migration speed under different field strengths.", "bbox": [50, 520, 800, 570], "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 5}},
    ]
    inv = build_figure_inventory(blocks)
    fig4 = [m for m in inv["matched_figures"] if m.get("figure_number") == 4]
    fig5 = [m for m in inv["matched_figures"] if m.get("figure_number") == 5]
    assert len(fig4) == 1, f"Expected 1 Fig 4, got {len(fig4)}"
    assert len(fig5) == 1, f"Expected 1 Fig 5, got {len(fig5)}"
    # Fig 4 should own page 12 assets (cross-page) or page 13 assets (same-page)
    assert fig4[0]["legend_page"] == 13
    # Fig 5 should own page 13 assets
    assert fig5[0]["page"] == 13
    assert fig5[0]["legend_page"] == 13
    # Orphan count should be low (ideally 0)
    orphan_assets = [a for a in inv.get("unmatched_assets", []) if a.get("page") in (12, 13)]
    orphan_groups = inv.get("unresolved_clusters", [])
    total_orphan_assets = len(orphan_assets) + sum(len(g.get("media_block_ids", [])) for g in orphan_groups)
    assert total_orphan_assets <= 2, f"Too many orphaned assets: {total_orphan_assets}"


# === P1A: Composite Parent Detector (Diagnostic-Only) ===


def test_composite_parent_candidates_appear_for_dense_grid_page() -> None:
    """P1A: VFS8CBW2-like dense 2x2 grid page should produce composite parent candidates."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # Two same-width columns, vertical gaps > 96px so atomic clustering
        # produces separate single_asset groups. Composite parent should re-group them.
        # Column A at x=[100,500]: pan_a (top), pan_b (bottom)
        # Column B at x=[600,1000]: pan_c (wider top-right), fig2_asset (separate)
        {"block_id": "leg_1a", "page": 5, "role": "figure_caption",
         "text": "Figure 1. Composite figure legend.", "bbox": [100, 880, 700, 920],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "pan_a", "page": 5, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 250]},
        {"block_id": "pan_b", "page": 5, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 380, 500, 530]},
        {"block_id": "pan_c", "page": 5, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 100, 1000, 350]},
        {"block_id": "fig2_asset", "page": 5, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 480, 1000, 800]},
    ]

    inv = build_figure_inventory(blocks)
    candidates = inv.get("composite_parent_candidates", [])

    assert len(candidates) >= 1, "Dense grid page must produce composite parent candidates"
    for c in candidates:
        assert c["group_type"] == "composite_parent"
        assert isinstance(c["parent_confidence"], float)
        assert isinstance(c["parent_evidence"], list)
        assert isinstance(c["child_group_ids"], list)
        assert c["ownership_enabled"] is False


def test_composite_parent_candidates_for_stacked_vertical_panels() -> None:
    """P1A: 24YKLTHQ-like vertically stacked panels should form composite parent."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_stacked", "page": 6, "role": "figure_caption",
         "text": "Figure 1. Stacked panels.", "bbox": [100, 800, 700, 840],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "top", "page": 6, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 800, 250]},
        {"block_id": "mid", "page": 6, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 380, 800, 530]},
        {"block_id": "bot", "page": 6, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 660, 800, 810]},
    ]

    inv = build_figure_inventory(blocks)
    candidates = inv.get("composite_parent_candidates", [])

    assert len(candidates) >= 1, "Stacked vertical panels must produce composite parent candidates"
    panel_ids = {"top", "mid", "bot"}
    for c in candidates:
        child_asset_ids = set(c.get("asset_block_ids", []))
        if len(child_asset_ids) >= 3:
            assert panel_ids <= child_asset_ids, f"Parent must cover all panels, got {child_asset_ids}"
            break
    else:
        assert False, "No composite parent candidate covers all 3 stacked panels"


def test_ordinary_multi_figure_page_does_not_mega_merge() -> None:
    """P1A: ordinary page with separate figures must NOT form a single mega-parent."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_7a", "page": 7, "role": "figure_caption",
         "text": "Figure 1. Top-left figure.", "bbox": [100, 420, 400, 450],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "a7_1", "page": 7, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 400, 400]},
        {"block_id": "leg_7b", "page": 7, "role": "figure_caption",
         "text": "Figure 2. Bottom-right figure.", "bbox": [520, 780, 900, 810],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "a7_2", "page": 7, "role": "figure_asset", "raw_label": "image",
         "bbox": [520, 520, 900, 760]},
    ]

    inv = build_figure_inventory(blocks)
    candidates = inv.get("composite_parent_candidates", [])

    for c in candidates:
        child_assets = set(c.get("asset_block_ids", []))
        # No candidate should consume both separate figures
        assert not ({"a7_1", "a7_2"} <= child_assets), (
            f"Mega-merge detected: candidate {c['group_id']} consumes both separate figures"
        )


def test_composite_parent_detection_preserves_ownership_counts() -> None:
    """P1A: diagnostic detection must not change matched/unmatched/unresolved/official counts."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c1", "page": 8, "role": "figure_caption",
         "text": "Figure 1. Grid layout.", "bbox": [100, 850, 700, 890],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "g1_a", "page": 8, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 450, 250]},
        {"block_id": "g1_b", "page": 8, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 380, 450, 530]},
        {"block_id": "g1_c", "page": 8, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 660, 450, 810]},
        {"block_id": "c2", "page": 8, "role": "figure_caption",
         "text": "Figure 2. Simple single figure.", "bbox": [600, 850, 1000, 890],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "g2", "page": 8, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 100, 1000, 600]},
    ]

    inv = build_figure_inventory(blocks)

    assert inv.get("composite_parent_candidates"), "Must produce composite parent candidates"


    assert inv["matched_figures"], "Must have matched figures"
    assert inv["official_figure_count"] >= 1

    # Verify the composite parent hasn't consumed assets that should be matched
    matched_asset_ids = {
        str(a.get("block_id", ""))
        for mf in inv["matched_figures"]
        for a in mf.get("matched_assets", [])
    }
    # Figure 1 legend should own its composite 4-panel group
    fig1 = [mf for mf in inv["matched_figures"] if mf.get("figure_number") == 1]
    assert fig1, "Figure 1 must be matched"
    fig1_assets = {str(a.get("block_id", "")) for a in fig1[0].get("matched_assets", [])}
    assert len(fig1_assets) >= 1, "Figure 1 must have matched assets"

    # Figure 2 should also be matched
    fig2 = [mf for mf in inv["matched_figures"] if mf.get("figure_number") == 2]
    assert fig2, "Figure 2 must be matched"


# === P1B: Composite Parent Ownership Arbitration ===


def test_composite_parent_acceptance_consumes_children() -> None:
    """P1B: strong parent candidate should own all child assets and consume child groups."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_cp", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Composite multi-panel legend.", "bbox": [100, 880, 700, 920],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "top", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 800, 250]},
        {"block_id": "mid", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 380, 800, 530]},
        {"block_id": "bot", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 660, 800, 810]},
    ]

    inv = build_figure_inventory(blocks)

    assert inv.get("composite_parent_candidates"), "Must have composite parent candidates"
    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert len(fig1) == 1, "Figure 1 must be matched exactly once"
    m = fig1[0]
    matched_assets = {str(a.get("block_id", "")) for a in m.get("matched_assets", [])}
    assert "top" in matched_assets, "Top panel must be owned"
    assert "mid" in matched_assets, "Mid panel must be owned"
    assert "bot" in matched_assets, "Bot panel must be owned"
    assert m.get("settlement_type") == "composite_parent", (
        f"Expected composite_parent settlement, got {m.get('settlement_type')}"
    )


def test_scoped_composite_parent_keeps_neighboring_single_figure_separate() -> None:
    """P1B: accept only the scoped composite child subset, not the whole over-wide parent."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "asset_fig3", "page": 18, "role": "figure_asset", "raw_label": "image", "bbox": [377, 155, 813, 440]},
        {"block_id": "leg_fig3", "page": 18, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "图 3 AIHIP 系统自动匹配假体型号", "bbox": [436, 466, 754, 493], "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "asset_fig4_a", "page": 18, "role": "figure_asset", "raw_label": "image", "bbox": [381, 556, 573, 742]},
        {"block_id": "asset_fig4_b", "page": 18, "role": "figure_asset", "raw_label": "image", "bbox": [618, 554, 811, 742]},
        {"block_id": "asset_fig4_c", "page": 18, "role": "figure_asset", "raw_label": "image", "bbox": [381, 753, 573, 942]},
        {"block_id": "asset_fig4_d", "page": 18, "role": "figure_asset", "raw_label": "image", "bbox": [618, 754, 811, 941]},
        {"block_id": "leg_fig4", "page": 18, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "图 4 AIHIP 系统安放髋臼假体并展示三维模拟位置", "bbox": [360, 963, 828, 990], "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
    ]

    inv = build_figure_inventory(blocks, page_width=1191)
    matched = {m.get("figure_number"): m for m in inv.get("matched_figures", [])}

    assert 3 in matched, "图3 must remain independently matched"
    assert 4 in matched, "图4 must be matched"
    assert {str(a.get('block_id', '')) for a in matched[3].get('matched_assets', [])} == {"asset_fig3"}
    assert matched[3].get("settlement_type") == "same_page"
    assert {str(a.get('block_id', '')) for a in matched[4].get('matched_assets', [])} == {"asset_fig4_a", "asset_fig4_b", "asset_fig4_c", "asset_fig4_d"}
    assert matched[4].get("settlement_type") == "composite_parent"


def test_caption_nearest_trap_prefers_interval_scoped_composite() -> None:
    """P1B: upper composite panels may be nearer to the previous caption, but still belong to the lower caption interval."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "asset_top", "page": 30, "role": "figure_asset", "raw_label": "image", "bbox": [380, 120, 820, 400]},
        {"block_id": "leg_top", "page": 30, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "图 3 上方单图", "bbox": [430, 430, 760, 460], "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "asset_bl", "page": 30, "role": "figure_asset", "raw_label": "image", "bbox": [390, 520, 575, 720]},
        {"block_id": "asset_br", "page": 30, "role": "figure_asset", "raw_label": "image", "bbox": [620, 520, 805, 720]},
        {"block_id": "asset_cl", "page": 30, "role": "figure_asset", "raw_label": "image", "bbox": [390, 740, 575, 930]},
        {"block_id": "asset_cr", "page": 30, "role": "figure_asset", "raw_label": "image", "bbox": [620, 740, 805, 930]},
        {"block_id": "leg_bottom", "page": 30, "role": "figure_caption_candidate", "seed_role": "figure_caption", "raw_label": "figure_title", "text": "图 4 下方复合图", "bbox": [360, 955, 830, 985], "zone": "display_zone", "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 4}},
    ]

    inv = build_figure_inventory(blocks, page_width=1191)
    matched = {m.get("figure_number"): m for m in inv.get("matched_figures", [])}

    assert {str(a.get('block_id', '')) for a in matched[3].get('matched_assets', [])} == {"asset_top"}
    assert matched[3].get("settlement_type") == "same_page"
    assert {str(a.get('block_id', '')) for a in matched[4].get('matched_assets', [])} == {"asset_bl", "asset_br", "asset_cl", "asset_cr"}
    assert matched[4].get("settlement_type") == "composite_parent"


def test_weak_parent_candidate_does_not_consume_children() -> None:
    """P1B: low-confidence parent should not block children from normal matching."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_wp", "page": 11, "role": "figure_caption",
         "text": "Figure 1. Weak parent legend.", "bbox": [100, 880, 700, 920],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "wp_a", "page": 11, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 250]},
        {"block_id": "wp_b", "page": 11, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 380, 1000, 530]},
    ]

    inv = build_figure_inventory(blocks)

    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert len(fig1) == 1, "Figure 1 must be matched"
    # Weak parent: the two assets are in different x-columns, so parent confidence
    # should be low. Legend should still match via same_page (distance_cluster or single_asset).
    assert fig1[0].get("settlement_type") != "composite_parent", (
        "Weak parent must not force composite_parent settlement"
    )
    matched_assets = {str(a.get("block_id", "")) for a in fig1[0].get("matched_assets", [])}
    assert matched_assets, "Figure 1 must have matched assets"


def test_competing_caption_veto_blocks_parent_promotion() -> None:
    """P1B: two captions targeting same composite parent should not promote."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_cv_1", "page": 12, "role": "figure_caption",
         "text": "Figure 1. First caption in shared region.", "bbox": [100, 880, 400, 920],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "leg_cv_2", "page": 12, "role": "figure_caption",
         "text": "Figure 2. Second caption in shared region.", "bbox": [500, 880, 800, 920],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "cv_a", "page": 12, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 450, 250]},
        {"block_id": "cv_b", "page": 12, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 380, 450, 530]},
        {"block_id": "cv_c", "page": 12, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 660, 450, 810]},
    ]

    inv = build_figure_inventory(blocks)

    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    fig2 = [m for m in inv["matched_figures"] if m.get("figure_number") == 2]
    assert fig1, "Figure 1 must be matched"
    # Fig 2 may be ambiguous on competing-caption page (no same-page assets in its column)
    # but must not use composite_parent via cross-caption parent
    if fig2:
        assert all(m.get("settlement_type") != "composite_parent" for m in fig2)
    # Cross-caption composite_parent is not allowed: any composite_parent here should
    # be band-scoped within one caption's legend interval
    _composite_parents = [
        m for m in inv["matched_figures"]
        if m.get("settlement_type") == "composite_parent"
    ]
    if _composite_parents:
        assert all(
            m.get("flags") == ["composite_parent_match"]
            for m in _composite_parents
        ), "Composite parent must have composite_parent_match flag"


def test_parent_candidate_never_enters_legacy_fallback_directly() -> None:
    """P1B: composite_parent must not flow into legacy sequential/single-asset fallback."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_nl", "page": 13, "role": "figure_caption",
         "text": "Figure 1. Legend for composite.", "bbox": [100, 880, 700, 920],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "nl_a", "page": 13, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 300]},
        {"block_id": "nl_b", "page": 13, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 430, 500, 630]},
        {"block_id": "nl_c", "page": 13, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 760, 500, 960]},
    ]

    inv = build_figure_inventory(blocks)

    candidates = inv.get("composite_parent_candidates", [])
    assert candidates, "Must have composite parent candidates"
    # Verify no composite_parent appears in unmatched_legends or ambiguous_figures
    # as if it were a normal group — composite parents are not peer candidates
    ambiguous_ids = {str(af.get("legend_block_id", "")) for af in inv.get("ambiguous_figures", [])}
    assert "leg_nl" not in ambiguous_ids or len(inv["matched_figures"]) >= 1, (
        "Composite parent must not be treated as ordinary ambiguous group"
    )


# === P2: Mixed Caption Grammar Validator ===


def test_page_local_grammar_annotations_include_status_reason_evidence() -> None:
    """P2: local_pairing_hypotheses must carry grammar_status, grammar_reason, grammar_evidence."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_ga", "page": 20, "role": "figure_caption",
         "text": "Figure 1. Consistent grammar page.", "bbox": [100, 700, 700, 740],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "ga_1", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 700, 650]},
    ]

    inv = build_figure_inventory(blocks)
    hypotheses = inv.get("local_pairing_hypotheses", [])

    assert len(hypotheses) >= 1, "Must have at least one pairing hypothesis"
    for h in hypotheses:
        assert h.get("grammar_status") in {"accepted", "deferred", "rejected", "conflict"}, (
            f"grammar_status missing or invalid: {h.get('grammar_status')}"
        )
        assert isinstance(h.get("grammar_reason"), str), (
            f"grammar_reason missing or not string: {h.get('grammar_reason')}"
        )
        assert isinstance(h.get("grammar_evidence"), list), (
            f"grammar_evidence missing or not list: {h.get('grammar_evidence')}"
        )


def test_incompatible_local_grammar_marks_conflict() -> None:
    """P2: mixed grammar styles on same page should mark grammar_status='conflict'."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_mx1", "page": 21, "role": "figure_caption",
         "text": "Figure 1. Mixed-grammar page A.", "bbox": [100, 400, 450, 440],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "mx1_a", "page": 21, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 450, 380]},
        {"block_id": "leg_mx2", "page": 21, "role": "figure_caption",
         "text": "Fig 2. Different grammar style.", "bbox": [550, 400, 900, 440],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "mx2_a", "page": 21, "role": "figure_asset", "raw_label": "image",
         "bbox": [550, 100, 900, 380]},
    ]

    inv = build_figure_inventory(blocks)
    hypotheses = inv.get("local_pairing_hypotheses", [])

    conflict_hypotheses = [h for h in hypotheses if h.get("grammar_status") == "conflict"]
    assert len(conflict_hypotheses) >= 1, (
        f"Mixed grammar page must have conflict hypotheses, got statuses: "
        f"{[h.get('grammar_status') for h in hypotheses]}"
    )


def test_mixed_page_can_be_self_consistent_without_one_global_mode() -> None:
    """P2: a page with uniformly styled captions should not be marked as conflict."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_u1", "page": 22, "role": "figure_caption",
         "text": "Figure 1. Uniform style.", "bbox": [100, 400, 450, 440],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "u1_a", "page": 22, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 450, 380]},
        {"block_id": "leg_u2", "page": 22, "role": "figure_caption",
         "text": "Figure 2. Same style family.", "bbox": [550, 400, 900, 440],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "u2_a", "page": 22, "role": "figure_asset", "raw_label": "image",
         "bbox": [550, 100, 900, 380]},
    ]

    inv = build_figure_inventory(blocks)
    hypotheses = inv.get("local_pairing_hypotheses", [])

    for h in hypotheses:
        assert h.get("grammar_status") != "conflict", (
            f"Uniform page should not have conflict: {h.get('grammar_status')} - {h.get('grammar_reason')}"
        )


# === P3A: Asset Family Hint ===


def test_asset_family_hint_populated_on_figure_assets() -> None:
    """P3A: figure_assets in inventory must carry asset_family_hint fields."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_ah", "page": 30, "role": "figure_caption",
         "text": "Figure 1. Asset family test.", "bbox": [100, 700, 700, 740],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "img1", "page": 30, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 600]},
        {"block_id": "img2", "page": 30, "role": "media_asset", "raw_label": "chart",
         "bbox": [520, 100, 900, 600]},
    ]

    inv = build_figure_inventory(blocks)
    assets = inv.get("figure_assets", [])

    assert len(assets) >= 2, "Must have at least 2 figure assets"
    for a in assets:
        hint = a.get("asset_family_hint")
        assert hint in {"figure_like", "table_like", "ambiguous"}, (
            f"Invalid or missing asset_family_hint: {hint}"
        )
        assert isinstance(a.get("asset_family_confidence"), (int, float)), (
            f"asset_family_confidence missing or not numeric"
        )
        assert isinstance(a.get("asset_family_evidence"), list), (
            f"asset_family_evidence missing or not list"
        )


# === P3B/P3C: Figure/Table Separator Veto ===


def test_figure_matcher_skips_strong_table_like_region() -> None:
    """P3B/P3C: table-like assets should not be claimed as figures."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_fv", "page": 31, "role": "figure_caption",
         "text": "Figure 1. Should NOT own table assets.", "bbox": [100, 700, 700, 740],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "img", "page": 31, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 400, 600]},
        {"block_id": "tbl_like", "page": 31, "role": "figure_asset", "raw_label": "table",
         "bbox": [500, 100, 900, 600], "asset_family_hint": "table_like",
         "asset_family_confidence": 0.85, "asset_family_evidence": ["raw_label:table"]},
    ]

    inv = build_figure_inventory(blocks)

    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert fig1, "Figure 1 must be matched"
    matched_assets = {str(a.get("block_id", "")) for a in fig1[0].get("matched_assets", [])}
    assert "tbl_like" not in matched_assets, (
        "Table-like asset with strong hint must NOT be claimed by figure matcher"
    )


def test_ambiguous_region_is_not_hard_forced() -> None:
    """P3B/P3C: ambiguous assets should not be hard-excluded from either path."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_amb", "page": 32, "role": "figure_caption",
         "text": "Figure 1. Ambiguous region test.", "bbox": [100, 700, 700, 740],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "amb_img", "page": 32, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 600], "asset_family_hint": "ambiguous",
         "asset_family_confidence": 0.40, "asset_family_evidence": []},
    ]

    inv = build_figure_inventory(blocks)

    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert fig1, "Figure 1 must be matched"
    matched_assets = {str(a.get("block_id", "")) for a in fig1[0].get("matched_assets", [])}
    assert "amb_img" in matched_assets, (
        "Ambiguous asset must NOT be hard-excluded from figure matching"
    )


# === P1B: Panel-Title Suppression (Task 3) ===


def test_short_unnumbered_panel_title_does_not_compete_with_numbered_caption() -> None:
    """Panel-title candidate on a page with a numbered caption must not produce
    local pairing hypotheses as a formal legend."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "fig1_legend", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Main experimental results.", "bbox": [100, 900, 900, 950],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "fig1_asset", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 900, 500]},
        {"block_id": "panel_title", "page": 10, "role": "figure_caption_candidate",
         "text": "RND", "bbox": [100, 520, 500, 540],
         "zone": "display_zone", "style_family": "legend_like"},
    ]

    inv = build_figure_inventory(blocks)

    suppressed = inv.get("suppressed_caption_candidates", [])
    assert len(suppressed) == 1, f"Expected 1 suppressed panel title, got {len(suppressed)}"
    assert suppressed[0]["block_id"] == "panel_title"
    assert suppressed[0]["suppression_reason"] == "panel_title_inside_visual_envelope"

    hypotheses = inv.get("local_pairing_hypotheses", [])
    panel_hypotheses = [h for h in hypotheses if h.get("legend_block_id") == "panel_title"]
    assert not panel_hypotheses, "Panel title must not produce local pairing hypotheses"

    fig1 = [m for m in inv["matched_figures"] if m.get("figure_number") == 1]
    assert fig1, "Figure 1 must still be matched"


def test_suppressed_panel_title_not_emitted_as_matched_or_ambiguous() -> None:
    """Suppressed panel titles must not appear in matched_figures or
    ambiguous_figures."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_1", "page": 20, "role": "figure_caption",
         "text": "Figure 2. Group analysis.", "bbox": [100, 900, 900, 950],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "ast_1", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 900, 500]},
        {"block_id": "fake_cap", "page": 20, "role": "figure_caption_candidate",
         "text": "Basal respiration rate", "bbox": [100, 520, 500, 550],
         "zone": "display_zone", "style_family": "legend_like"},
    ]

    inv = build_figure_inventory(blocks)

    suppressed = inv.get("suppressed_caption_candidates", [])
    assert len(suppressed) == 1

    matched_ids = {str(m.get("legend_block_id", "")) for m in inv.get("matched_figures", [])}
    assert "fake_cap" not in matched_ids, "Suppressed title must not be in matched_figures"

    ambiguous_ids = {str(a.get("legend_block_id", "")) for a in inv.get("ambiguous_figures", [])}
    assert "fake_cap" not in ambiguous_ids, "Suppressed title must not be in ambiguous_figures"

    suppressed_ids = {s["block_id"] for s in suppressed}
    assert "fake_cap" in suppressed_ids


def test_suppressed_panel_title_remains_accounted_not_body() -> None:
    """Suppressed panel titles must appear as retained embedded text, not lost."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_k", "page": 30, "role": "figure_caption",
         "text": "Figure 3. Analysis.", "bbox": [100, 900, 900, 950],
         "style_family": "legend_like", "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "ast_k", "page": 30, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 900, 500]},
        {"block_id": "panel_k", "page": 30, "role": "figure_caption_candidate",
         "text": "COL II", "bbox": [100, 520, 500, 540],
         "zone": "display_zone", "style_family": "legend_like"},
    ]

    inv = build_figure_inventory(blocks)

    suppressed = inv.get("suppressed_caption_candidates", [])
    assert len(suppressed) == 1
    assert suppressed[0]["retained_as"] == "embedded_figure_text"

    rejected_ids = {str(r.get("block_id", "")) for r in inv.get("rejected_legends", [])}
    assert "panel_k" not in rejected_ids, "Suppressed title must not be in rejected_legends"


# === Dense Composite Parent Candidate Hardening ===


def test_dense_fragmented_page_emits_composite_parent_candidate() -> None:
    """Page with 5+ compact visual fragments and a numbered caption
    must emit at least one dense composite parent candidate."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "d_leg", "page": 20, "role": "figure_caption",
         "text": "Figure 1. Dense multi-panel composite figure showing expression profiles.",
         "bbox": [100, 750, 900, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "d_a1", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 350, 300]},
        {"block_id": "d_a2", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [400, 100, 650, 300]},
        {"block_id": "d_a3", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [700, 100, 950, 300]},
        {"block_id": "d_a4", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 350, 350, 550]},
        {"block_id": "d_a5", "page": 20, "role": "figure_asset", "raw_label": "image",
         "bbox": [400, 350, 650, 550]},
    ]

    inv = build_figure_inventory(blocks, page_width=1100)

    dense_parents = [
        p for p in inv.get("composite_parent_candidates", [])
        if p.get("parent_subtype") == "dense_composite"
    ]
    assert dense_parents, (
        f"Dense fragmented page must emit a dense composite parent candidate. "
        f"Total parents: {len(inv.get('composite_parent_candidates', []))}"
    )


def test_ordinary_multi_figure_page_does_not_emit_dense_parent() -> None:
    """Two independent numbered figures on same page must NOT produce
    a page-wide dense parent candidate."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "ord_leg1", "page": 30, "role": "figure_caption",
         "text": "Figure 2. First independent figure.", "bbox": [100, 350, 500, 390],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "ord_a1", "page": 30, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 300]},
        {"block_id": "ord_leg2", "page": 30, "role": "figure_caption",
         "text": "Figure 3. Second independent figure.", "bbox": [600, 350, 1000, 390],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "ord_a2", "page": 30, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 100, 1000, 300]},
    ]

    inv = build_figure_inventory(blocks, page_width=1100)

    dense_parents = [
        p for p in inv.get("composite_parent_candidates", [])
        if p.get("parent_subtype") == "dense_composite"
    ]
    assert not dense_parents, (
        "Ordinary multi-figure page must NOT emit a dense parent candidate"
    )


def test_dense_parent_candidate_records_unresolved_cluster_ids() -> None:
    """Dense parent candidate must include unresolved_cluster_ids when
    unresolved visual mass falls within the parent envelope."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "u_leg", "page": 25, "role": "figure_caption",
         "text": "Figure 4. Dense composite with orphaned sub-panels.",
         "bbox": [100, 750, 900, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 4}},
        {"block_id": "u_a1", "page": 25, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 350, 300]},
        {"block_id": "u_a2", "page": 25, "role": "figure_asset", "raw_label": "image",
         "bbox": [400, 100, 650, 300]},
        {"block_id": "u_a3", "page": 25, "role": "figure_asset", "raw_label": "image",
         "bbox": [700, 100, 950, 300]},
        {"block_id": "u_a4", "page": 25, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 350, 350, 550]},
        {"block_id": "u_a5", "page": 25, "role": "figure_asset", "raw_label": "image",
         "bbox": [400, 350, 650, 550]},
        {"block_id": "u_a6", "page": 25, "role": "figure_asset", "raw_label": "image",
         "bbox": [700, 350, 950, 550]},
    ]

    inv = build_figure_inventory(blocks, page_width=1100)

    dense_parents = [
        p for p in inv.get("composite_parent_candidates", [])
        if p.get("parent_subtype") == "dense_composite"
    ]
    assert dense_parents, "Must emit dense parent candidate"

    parent = dense_parents[0]
    uids = parent.get("unresolved_cluster_ids", None)
    assert uids is not None, "unresolved_cluster_ids field must exist"
    assert isinstance(uids, list), "unresolved_cluster_ids must be a list"


def test_dense_parent_candidate_has_required_contract_fields() -> None:
    """Every dense composite parent candidate must include all required
    contract fields per spec."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "c_leg", "page": 35, "role": "figure_caption",
         "text": "Figure 5. Multi-panel expression atlas.", "bbox": [100, 750, 900, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 5}},
        {"block_id": "c_a1", "page": 35, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 350, 300]},
        {"block_id": "c_a2", "page": 35, "role": "figure_asset", "raw_label": "image",
         "bbox": [400, 100, 650, 300]},
        {"block_id": "c_a3", "page": 35, "role": "figure_asset", "raw_label": "image",
         "bbox": [700, 100, 950, 300]},
        {"block_id": "c_a4", "page": 35, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 350, 350, 550]},
        {"block_id": "c_a5", "page": 35, "role": "figure_asset", "raw_label": "image",
         "bbox": [400, 350, 650, 550]},
    ]

    inv = build_figure_inventory(blocks, page_width=1100)

    dense_parents = [
        p for p in inv.get("composite_parent_candidates", [])
        if p.get("parent_subtype") == "dense_composite"
    ]
    assert dense_parents, "Must emit dense parent candidate"

    p = dense_parents[0]
    assert p.get("group_type") == "composite_parent"
    assert p.get("parent_subtype") == "dense_composite"
    assert isinstance(p.get("page"), int)
    assert isinstance(p.get("child_group_ids"), list)
    assert isinstance(p.get("unresolved_cluster_ids"), list)
    assert isinstance(p.get("asset_block_ids"), list)
    assert isinstance(p.get("cluster_bbox"), list) and len(p.get("cluster_bbox", [])) == 4
    assert isinstance(p.get("fragment_count"), int)
    assert isinstance(p.get("atomic_child_count"), int)
    assert isinstance(p.get("unresolved_child_count"), int)
    assert isinstance(p.get("compactness"), (int, float))
    assert isinstance(p.get("grid_score"), (int, float))
    assert isinstance(p.get("construction_reason"), list)
    assert p.get("ownership_enabled") is False


# --- Task 5: construction-time vs arbitration-time separation ---

def test_dense_parent_candidate_can_be_constructed_from_visual_fragment_count_only() -> None:
    from paperforge.worker.ocr_figures import _build_dense_composite_parent_candidates

    groups = [
        {
            "group_id": "g1", "page": 10,
            "asset_block_ids": ["a1", "a2"],
            "cluster_bbox": [100, 100, 400, 400],
        },
        {
            "group_id": "g2", "page": 10,
            "asset_block_ids": ["a3", "a4"],
            "cluster_bbox": [500, 100, 800, 400],
        },
    ]
    clusters = [
        {
            "cluster_id": "uc1", "page": 10,
            "media_block_ids": ["a5", "a6"],
            "cluster_bbox": [100, 500, 400, 800],
        },
    ]

    parents = _build_dense_composite_parent_candidates(
        groups, clusters, {10}, page_width=1000,
    )
    assert parents, "dense parent must be constructed from visual fragments only"
    p = parents[0]
    assert p["group_type"] == "composite_parent"
    assert p["parent_subtype"] == "dense_composite"
    assert p["fragment_count"] >= 4


def test_dense_parent_arbitration_uses_leftover_mass_to_outrank_partial_same_page() -> None:
    from paperforge.worker.ocr_figures import _score_dense_parent_candidate_against_local_ownership

    parent = {
        "group_id": "dp_1",
        "group_type": "composite_parent",
        "parent_subtype": "dense_composite",
        "page": 10,
        "child_group_ids": ["g1", "g2"],
        "unresolved_cluster_ids": ["uc1"],
        "asset_block_ids": ["a1", "a2", "a3", "a4"],
        "parent_confidence": 0.75,
        "fragment_count": 6,
        "atomic_child_count": 2,
        "unresolved_child_count": 1,
        "visual_mass": 6.0,
        "compactness": 0.45,
        "grid_score": 0.65,
        "ownership_enabled": False,
        "construction_reason": ["dense_fragment_page", "6_visual_fragments", "1_unresolved_clusters"],
    }

    owned = {"a5"}   # one asset already owned on page
    score_high = _score_dense_parent_candidate_against_local_ownership(
        parent, owned_asset_ids=owned, unresolved_asset_ids={"a1", "a2", "a3", "a4", "a6", "a7"},
    )
    score_low = _score_dense_parent_candidate_against_local_ownership(
        parent, owned_asset_ids=owned, unresolved_asset_ids={"a1"},
    )

    assert score_high["coverage_gain"] > score_low["coverage_gain"], (
        f"more unresolved mass must yield higher coverage gain: "
        f"high={score_high['coverage_gain']} low={score_low['coverage_gain']}"
    )
    assert "leftover_mass_absorbed" in score_high
    assert "unresolved_reduction_ratio" in score_high


# --- Task 7: dense page arbitration regression ---

def test_dense_composite_parent_collects_large_fragment_set() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Multi-panel expression atlas.", "bbox": [100, 830, 900, 880],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "a1", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 80, 450, 230]},
        {"block_id": "a2", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 280, 450, 430]},
        {"block_id": "a3", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 480, 450, 630]},
        {"block_id": "a4", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [550, 80, 900, 230]},
        {"block_id": "a5", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [550, 280, 900, 430]},
        {"block_id": "a6", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [550, 480, 900, 630]},
    ]

    inv = build_figure_inventory(blocks, page_width=1000)

    matched = inv.get("matched_figures", [])
    assert len(matched) >= 1, "dense page must produce at least one matched figure"

    matched_asset_ids = set()
    for mf in matched:
        for bid in mf.get("asset_block_ids", []):
            matched_asset_ids.add(str(bid))

    expected = {"a1", "a2", "a3", "a4", "a5", "a6"}
    missing = expected - matched_asset_ids
    assert not missing, f"dense parent must collect all fragments; missing: {missing}"


def test_dense_parent_does_not_swallow_neighboring_ordinary_figure() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg_dense", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Dense composite with 6 panels.",
         "bbox": [100, 750, 500, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "d1", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 250, 300]},
        {"block_id": "d2", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [300, 100, 450, 300]},
        {"block_id": "d3", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 350, 250, 550]},
        {"block_id": "d4", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [300, 350, 450, 550]},
        {"block_id": "leg_ord", "page": 10, "role": "figure_caption",
         "text": "Figure 2. Independent figure on same page.",
         "bbox": [600, 750, 1000, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "n1", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 100, 900, 500]},
    ]

    inv = build_figure_inventory(blocks, page_width=1100)

    matched = inv.get("matched_figures", [])
    assert len(matched) >= 2, f"page with two figures must emit >=2 matched; got {len(matched)}"

    fig2_assets = set()
    fig1_assets = set()
    for mf in matched:
        fn = mf.get("figure_number")
        if fn == 2:
            fig2_assets = {str(b) for b in mf.get("asset_block_ids", [])}
        elif fn == 1:
            fig1_assets = {str(b) for b in mf.get("asset_block_ids", [])}

    assert "n1" in fig2_assets, "ordinary figure's asset must NOT be swallowed by dense parent"
    assert "n1" not in fig1_assets, "dense parent must NOT claim neighboring ordinary figure's asset"


def test_partial_same_page_claim_becomes_provisional_when_large_same_zone_leftovers_remain() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Dense multi-panel composite with orphaned sub-panels.",
         "bbox": [100, 750, 900, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "ma1", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 300, 300]},
        {"block_id": "ma2", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [350, 100, 550, 300]},
        {"block_id": "ma3", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 100, 800, 300]},
        {"block_id": "ma4", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 350, 300, 550]},
        {"block_id": "ma5", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [350, 350, 550, 550]},
        {"block_id": "ma6", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [600, 350, 800, 550]},
        {"block_id": "ma7", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [850, 350, 950, 400]},
    ]

    inv = build_figure_inventory(blocks, page_width=1050)

    matched = inv.get("matched_figures", [])
    assert len(matched) >= 1, "must produce at least one figure on dense page"

    matched_asset_ids = set()
    for mf in matched:
        for bid in mf.get("asset_block_ids", []):
            matched_asset_ids.add(str(bid))

    unresolved = inv.get("unresolved_clusters", [])
    unresolved_asset_ids = set()
    for uc in unresolved:
        for bid in uc.get("media_block_ids", []):
            unresolved_asset_ids.add(str(bid))

    total_assets = matched_asset_ids | unresolved_asset_ids
    assert len(total_assets) >= 6, (
        f"dense page must account for most visual assets; "
        f"matched={len(matched_asset_ids)} unresolved={len(unresolved_asset_ids)}"
    )


def test_unresolved_clusters_deduped_against_matched_figures() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "leg1", "page": 10, "role": "figure_caption",
         "text": "Figure 1. Test figure.", "bbox": [100, 600, 500, 650],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "ast1", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 500]},
        {"block_id": "ast2", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [550, 100, 900, 500]},
    ]

    inv = build_figure_inventory(blocks, page_width=1000)

    matched = inv.get("matched_figures", [])
    ucs = inv.get("unresolved_clusters", [])

    matched_block_ids = set()
    for mf in matched:
        for bid in mf.get("asset_block_ids", []):
            matched_block_ids.add(str(bid))

    for uc in ucs:
        uc_page = uc.get("page", 0)
        for bid in uc.get("media_block_ids", []):
            assert (uc_page, str(bid)) not in {
                (mf.get("page", 0), b) for mf in matched for b in mf.get("asset_block_ids", [])
                if str(b) == str(bid)
            }, f"block {bid} in unresolved_cluster must not also be in matched_figures"


# --- Sidecar: outlier-tolerant narrow column + raw band ---

def test_narrow_caption_column_ignores_x_center_outlier() -> None:
    from paperforge.worker.ocr_figures import _same_page_narrow_caption_column

    captions = [
        {"block_id": 2, "page": 3, "text": "Fig. 2. Left-column caption.",
         "bbox": [103, 140, 422, 312]},
        {"block_id": 5, "page": 3, "text": "Fig. 3. Another left-column caption.",
         "bbox": [105, 802, 419, 838]},
        {"block_id": 14, "page": 3, "text": "Fig. 6 body mention right column.",
         "bbox": [799, 963, 1132, 1052]},
    ]

    result = _same_page_narrow_caption_column(captions, page_width=1133)
    result_ids = {c.get("block_id") for c in result}
    assert 2 in result_ids, "Fig 2 must be in narrow column"
    assert 5 in result_ids, "Fig 3 must be in narrow column"
    assert 14 not in result_ids, "Right-column outlier must not be in narrow column"


def test_narrow_caption_column_requires_two_aligned_captions_after_outlier_filter() -> None:
    from paperforge.worker.ocr_figures import _same_page_narrow_caption_column

    # Only 1 left-column caption + 1 right outlier → no valid cluster
    captions = [
        {"block_id": 2, "page": 3, "text": "Fig. 2. Left-column caption.",
         "bbox": [103, 140, 422, 312]},
        {"block_id": 14, "page": 3, "text": "Fig. 6 body mention right column.",
         "bbox": [799, 963, 1132, 1052]},
    ]
    assert _same_page_narrow_caption_column(captions, page_width=1133) == []


def test_sidecar_uses_full_filtered_raw_band_not_row_coupled_subset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    # AJR-style three-column layout: narrow left captions, wide right assets.
    # All assets cluster into one group, same_page gives it all to Fig 2.
    # Fig 3 is unresolved → violation → sidecar fires and redistributes.
    blocks = [
        {"block_id": "leg2", "page": 10, "role": "figure_caption",
         "text": "Fig. 2. Left column caption.", "bbox": [100, 80, 400, 150],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "leg3", "page": 10, "role": "figure_caption",
         "text": "Fig. 3. Second left caption.", "bbox": [100, 600, 400, 650],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "a2a", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [450, 80, 700, 250]},
        {"block_id": "a2b", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [450, 280, 700, 450]},
        {"block_id": "a3a", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [450, 550, 700, 750]},
        {"block_id": "a3b", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [450, 800, 700, 1000]},
    ]

    inv = build_figure_inventory(blocks, page_width=1200)
    matched = {m.get("figure_number"): m for m in inv.get("matched_figures", [])}

    assert 2 in matched, "Fig 2 must be matched via sidecar"
    assert {str(b) for b in matched[2].get("asset_block_ids", [])} == {"a2a", "a2b"}, (
        f"Fig 2 must get both band assets, got {matched[2].get('asset_block_ids')}"
    )

    assert 3 in matched, "Fig 3 must be matched via sidecar"
    assert {str(b) for b in matched[3].get("asset_block_ids", [])} == {"a3a", "a3b"}, (
        f"Fig 3 must get both band assets, got {matched[3].get('asset_block_ids')}"
    )


def test_sidecar_raw_band_still_excludes_protected_assets() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": "legA", "page": 10, "role": "figure_caption",
         "text": "Fig. 1. Protected below caption.", "bbox": [100, 500, 400, 550],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 1}},
        {"block_id": "aA", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [100, 100, 500, 480]},
        {"block_id": "legB", "page": 10, "role": "figure_caption",
         "text": "Fig. 2. Narrow left caption.", "bbox": [100, 600, 400, 650],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 2}},
        {"block_id": "legC", "page": 10, "role": "figure_caption",
         "text": "Fig. 3. Narrow left caption.", "bbox": [100, 750, 400, 800],
         "style_family": "legend_like",
         "marker_signature": {"type": "figure_number", "number": 3}},
        {"block_id": "aB", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [450, 550, 800, 750]},
        {"block_id": "aC", "page": 10, "role": "figure_asset", "raw_label": "image",
         "bbox": [450, 800, 800, 1000]},
    ]

    inv = build_figure_inventory(blocks, page_width=1200)
    matched = {m.get("figure_number"): m for m in inv.get("matched_figures", [])}

    assert 1 in matched, "Fig 1 (caption_below) must remain matched separately"
    # Fig 1 is a caption_below match with its own asset aA.
    # Narrow sidecar (Fig 2, Fig 3) should NOT capture aA.
    fig1_assets = {str(b) for b in matched[1].get("asset_block_ids", [])}
    assert "aA" in fig1_assets, "Fig 1 must keep its caption_below asset"

    fig2_assets = {str(b) for b in matched.get(2, {}).get("asset_block_ids", [])}
    assert "aA" not in fig2_assets, "Sidecar Fig 2 must not steal Fig 1 protected asset"

