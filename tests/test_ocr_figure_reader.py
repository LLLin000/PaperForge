from __future__ import annotations


def test_normalize_strict_inventory_maps_bucket_variants_to_common_fields() -> None:
    from paperforge.worker.ocr_figure_reader import _normalize_strict_figure_inventory

    strict_inventory = {
        "matched_figures": [
            {
                "figure_number": 6,
                "block_id": 15,
                "text": "Fig. 6 The figure represents...",
                "matched_assets": [{"block_id": 40, "bbox": [1, 2, 3, 4]}],
                "match_score": 0.91,
            }
        ],
        "ambiguous_figures": [
            {
                "figure_number": 3,
                "legend_block_id": 9,
                "text": "FIGURE 3 | Histological evaluation...",
                "candidates": [
                    {"asset_block_id": 10, "match_score": 0.51},
                    {"asset_block_id": 11, "match_score": 0.49},
                ],
            }
        ],
        "unmatched_legends": [
            {
                "block_id": 21,
                "text": "FIGURE 2 | Treadmill exercise protocols...",
                "figure_number": 2,
            }
        ],
        "unresolved_clusters": [
            {
                "page": 7,
                "media_block_ids": [30, 31],
            }
        ],
    }

    structured_blocks = [
        {
            "block_id": 21,
            "marker_signature": {"type": "figure_number"},
            "zone": "display_zone",
            "style_family": "legend_like",
        }
    ]

    normalized = _normalize_strict_figure_inventory(strict_inventory, structured_blocks)

    assert normalized["matched_figures"][0]["legend_block_id"] == 15
    assert normalized["matched_figures"][0]["caption_text"] == "Fig. 6 The figure represents..."
    assert normalized["matched_figures"][0]["asset_block_ids"] == [40]
    assert normalized["ambiguous_figures"][0]["candidate_asset_ids"] == [10, 11]
    assert normalized["unmatched_legends"][0]["legend_block_id"] == 21
    assert normalized["unresolved_clusters"][0]["asset_block_ids"] == [30, 31]


def test_reader_figure_preserves_separate_reader_and_strict_status() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    normalized_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [
            {
                "figure_number": 3,
                "legend_block_id": 9,
                "caption_text": "FIGURE 3 | Histological evaluation...",
                "candidate_asset_ids": [10, 11],
                "strict_status": "ambiguous",
                "marker_type": "figure_number",
            }
        ],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(normalized_inventory, structured_blocks=[])

    rf = result["reader_figures"][0]
    assert rf["reader_status"] == "GROUPED_APPROXIMATE"
    assert rf["strict_status"] == "ambiguous"
    assert rf["strict_source"] == "ambiguous_figures"


def test_reader_figure_id_uses_first_asset_id_for_visual_group_when_figure_number_missing() -> None:
    from paperforge.worker.ocr_figure_reader import _stable_reader_figure_id

    assert _stable_reader_figure_id(None, page=7, first_asset_block_id=31, ordinal=2) == "visual_group_7_31_reader"


def test_coverage_total_counts_deduplicated_eligible_inputs() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "ambiguous_figures": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "candidate_asset_ids": [30, 31],
                "marker_type": "figure_number",
            }
        ],
        "unmatched_legends": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "marker_type": "figure_number",
            }
        ],
        "matched_figures": [],
        "held_figures": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_coverage"]["total"] == 1


def test_ambiguous_without_formal_legend_does_not_enter_reader_layer() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [
            {
                "legend_block_id": 50,
                "caption_text": "Figure 2 shows the progression...",
                "candidate_asset_ids": [70],
                "marker_type": "figure_number",
                "inline_mention": True,
            }
        ],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_figures"] == []
    assert result["reader_coverage"]["total"] == 0


def test_grouped_approximate_requires_visual_candidates() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [
            {
                "figure_number": 4,
                "legend_block_id": 44,
                "caption_text": "FIGURE 4 | Immunohistochemical staining...",
                "candidate_asset_ids": [],
                "marker_type": "figure_number",
            }
        ],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert len(result["reader_figures"]) == 1
    rf = result["reader_figures"][0]
    assert rf["reader_status"] == "LEGEND_ONLY"
    assert rf["visual_groups"] == [
        {
            "page": None,
            "asset_block_ids": [],
            "group_status": "legend_only_group",
            "rendered_as_representative": False,
        }
    ]


def test_reader_hold_does_not_default_to_caption_consumption() -> None:
    from paperforge.worker.ocr_figure_reader import _materialize_hold_outcome

    hold = _materialize_hold_outcome(
        legend_block_id=80,
        caption_text="weak fragment",
        page=10,
        candidate_asset_ids=[],
        hold_visibility="audit_hold",
    )

    assert hold["consumed_caption_block_ids"] == []
    assert hold["debug_refs"]["hold_visibility"] == "audit_hold"


def test_legend_only_consumes_caption_when_rendered() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "marker_type": "figure_number",
            }
        ],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert len(result["reader_figures"]) == 1
    rf = result["reader_figures"][0]
    assert rf["reader_status"] == "LEGEND_ONLY"
    assert rf["consumed_caption_block_ids"] == [{"page": None, "block_id": 21}]


def test_reader_sequence_match_promoted_figure_gets_proper_status() -> None:
    """A figure promoted via sequence_match must get SEQUENCE_MATCH reader_status."""
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [
            {
                "figure_number": 2,
                "legend_block_id": 12,
                "text": "Figure 2. Histological analysis.",
                "matched_assets": [],
                "match_score": {"score": 0.0, "decision": "sequence_match", "evidence": ["sequence_promotion"]},
                "flags": ["sequence_match"],
                "strict_status": "sequence_match",
                "marker_type": "figure_number",
            }
        ],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert len(result["reader_figures"]) == 1
    rf = result["reader_figures"][0]
    assert rf["reader_status"] == "SEQUENCE_MATCH", f"Expected SEQUENCE_MATCH, got {rf['reader_status']}"
    assert rf["strict_status"] == "sequence_match"
    assert rf["strict_source"] == "matched_figures"


def test_reader_payload_coverage_accounted_matches_reader_figures() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "matched_figures": [
            {
                "figure_number": 1,
                "legend_block_id": 5,
                "text": "Fig. 1 Overview of the system...",
                "matched_assets": [{"block_id": 10, "bbox": [1, 2, 3, 4]}],
                "match_score": 0.91,
                "marker_type": "figure_number",
            }
        ],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [
            {
                "figure_number": 2,
                "legend_block_id": 21,
                "text": "FIGURE 2 | Treadmill exercise protocols...",
                "marker_type": "figure_number",
            }
        ],
        "unresolved_clusters": [],
    }

    result = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    assert result["reader_coverage"]["total"] == 2
    assert result["reader_coverage"]["accounted"] == 2
    assert result["reader_coverage"]["gap_count"] == 0
    assert result["reader_coverage"]["ratio"] == 1.0
    assert result["consumed_caption_block_ids"] == [
        {"page": None, "block_id": 5},
        {"page": None, "block_id": 21},
    ]


def test_reader_figures_emit_from_matched_or_unresolved_object_inputs() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    payload = synthesize_reader_figures(
        {
            "matched_figures": [
                {
                    "figure_id": "figure_001",
                    "page": 2,
                    "legend_block_id": 21,
                    "asset_block_ids": [90],
                    "strict_status": "matched",
                }
            ],
            "held_figures": [],
            "ambiguous_figures": [],
            "unmatched_legends": [],
            "unresolved_clusters": [],
        },
        structured_blocks=[{"block_id": 21, "page": 2, "role": "figure_caption_candidate", "text": "Fig. 1 Caption"}],
    )

    assert len(payload["reader_figures"]) >= 1


def test_reader_normalization_keeps_same_block_id_legends_separate_by_page() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    structured_blocks = [
        {
            "page": 5,
            "block_id": 5,
            "role": "figure_caption",
            "text": "Fig. 1 Critical shoulder angle.",
            "marker_signature": {"type": "figure_number", "number": 1},
            "style_family": "legend_like",
            "zone": "display_zone",
        },
        {
            "page": 6,
            "block_id": 5,
            "role": "figure_caption",
            "text": "Fig. 5 Acromial index.",
            "marker_signature": {"type": "figure_number", "number": 5},
            "style_family": "legend_like",
            "zone": "display_zone",
        },
    ]
    strict_inventory = {
        "figure_legends": structured_blocks,
        "unmatched_legends": [structured_blocks[0], structured_blocks[1]],
    }

    payload = synthesize_reader_figures(strict_inventory, structured_blocks)

    numbers = [item["figure_number"] for item in payload["normalized_inputs"]["unmatched_legends"]]
    rendered_numbers = [item["figure_number"] for item in payload["reader_figures"]]

    assert numbers == [1, 5]
    assert rendered_numbers == [1, 5]


def test_reader_materializes_grouped_strict_match_as_single_visual_group() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "figure_legends": [],
        "matched_figures": [
            {
                "figure_number": 2,
                "legend_block_id": 10,
                "page": 3,
                "text": "Fig. 2 A and B, paired figure.",
                "matched_assets": [
                    {"block_id": 20, "bbox": [100, 100, 300, 300]},
                    {"block_id": 21, "bbox": [320, 100, 520, 300]},
                ],
                "match_score": {"score": 0.82, "decision": "matched", "evidence": ["same_row_pair"]},
                "caption_score": {"score": 0.9},
            }
        ],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    payload = synthesize_reader_figures(strict_inventory, structured_blocks=[])
    rf = payload["reader_figures"][0]
    assert rf["figure_number"] == 2
    assert len(rf["visual_groups"]) == 1
    assert rf["visual_groups"][0]["asset_block_ids"] == [20, 21]
    assert rf["visual_groups"][0]["group_status"] == "matched_group"


def test_reader_matched_cross_page_figure_consumes_caption_on_legend_page() -> None:
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

    strict_inventory = {
        "figure_legends": [],
        "matched_figures": [
            {
                "figure_id": "figure_004",
                "figure_number": 4,
                "legend_block_id": 6,
                "page": 12,
                "legend_page": 13,
                "asset_pages": [12],
                "text": "Figure 4. Cross-page caption.",
                "matched_assets": [
                    {"block_id": 101, "bbox": [100, 100, 300, 300]},
                ],
                "asset_block_ids": [101],
                "strict_status": "matched",
                "match_score": {"score": 0.8, "decision": "matched"},
            }
        ],
        "held_figures": [],
        "ambiguous_figures": [],
        "unmatched_legends": [],
        "unresolved_clusters": [],
    }

    payload = synthesize_reader_figures(strict_inventory, structured_blocks=[])

    rf = payload["reader_figures"][0]
    assert rf["visual_groups"][0]["page"] == 12
    assert rf["consumed_caption_block_ids"] == [{"page": 13, "block_id": 6}]
    assert payload["consumed_caption_block_ids"] == [{"page": 13, "block_id": 6}]
