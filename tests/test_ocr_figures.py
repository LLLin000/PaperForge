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


def test_figure_inventory_includes_all_sections() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory([])

    assert "figure_legends" in inventory
    assert "figure_assets" in inventory
    assert "matched_figures" in inventory
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
    assert inventory["matched_figures"][0]["confidence"] == 0.85


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

    assert len(inventory["matched_figures"]) == 2
    match_texts = [m["text"] for m in inventory["matched_figures"]]
    assert any("No figure prefix" in t for t in match_texts)


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

    assert len(inventory["matched_figures"]) == 1
    assert inventory["matched_figures"][0]["figure_number"] == 2
    assert len(inventory["matched_figures"][0]["matched_assets"]) == 0
    assert "legend_only" in inventory["matched_figures"][0]["flags"]
    assert inventory["matched_figures"][0]["confidence"] == 0.4


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

    assert len(inventory["matched_figures"]) == 1
    assert len(inventory["matched_figures"][0]["matched_assets"]) == 0
    assert "legend_only" in inventory["matched_figures"][0]["flags"]
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
    """Multi-sentence narrative prose starting with Fig. N must not become a legend."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "raw_role": "figure_caption",
            "block_label": "text",
            "text": "Fig. 26c addresses a limiting case. The trend reverses at higher "
            "concentrations. This is consistent with prior work.",
            "bbox": [50, 100, 550, 140],
        },
    ]

    inventory = build_figure_inventory(structured_blocks)

    assert len(inventory["matched_figures"]) == 0
    assert len(inventory["rejected_legends"]) == 1
    assert len(inventory["figure_legends"]) == 0


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


def test_prose_shaped_figure_caption_rejected() -> None:
    """Prose-shaped figure_caption (multi-sentence, no verb match) lands in rejected_legends."""
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 1,
            "block_id": "p1_b1",
            "role": "figure_caption",
            "raw_role": "figure_caption",
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

    assert len(inventory["figure_legends"]) == 0
    assert len(inventory["rejected_legends"]) == 1
    assert len(inventory["matched_figures"]) == 0
