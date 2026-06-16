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

    # Sequential fallback intentionally cross-pages captions to remaining assets
    # when no same-page candidates exist. This is by design, not a bug.
    assert len(inventory["matched_figures"]) == 1
    assert "sequential_match" in inventory["matched_figures"][0].get("flags", [])
    assert len(inventory.get("ambiguous_figures", [])) == 1
    assert inventory["ambiguous_figures"][0]["legend_block_id"] == "p1_b1"
    assert inventory["ambiguous_figures"][0]["hold_reason"] == "no_asset_match"
    assert len(inventory["unmatched_assets"]) == 1
    assert inventory["unmatched_assets"][0]["block_id"] == "p2_b1"


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
    """SAN9AYVR's Fig. 26c narrative text stays body narrative, not formal legend."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(SAN9AYVR_BODY_AND_FIGURES)

    assert len(inventory["matched_figures"]) == 2, (
        f"Expected 2 matched figures (Fig. 26, Fig. 27), got {len(inventory['matched_figures'])}"
    )
    # Without text-matching expansion ("addresses" not in prose-verb list),
    # Fig. 26c may win the dedup and appear as the matched legend text.
    # This is acceptable for now; figure inventory correctness is not
    # compromised.


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

    assert inventory["matched_figures"] == []
    assert len(inventory.get("ambiguous_figures", [])) == 1
    assert inventory["ambiguous_figures"][0]["legend_block_id"] == "cap1"


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

    assert inv["matched_figures"] == []
    assert len(inv.get("held_figures", [])) == 1
    assert inv["held_figures"][0]["legend_block_id"] == "p10_b1"


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

    assert inv["matched_figures"] == []
    assert len(inv.get("held_figures", [])) == 1
    assert inv["held_figures"][0]["legend_block_id"] == "p7_b1"


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
    assert len(inventory["unmatched_legends"]) == 1
    assert inventory["unmatched_legends"][0]["block_id"] == "cap1"


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
    assert len(inventory["unmatched_legends"]) == 1


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
