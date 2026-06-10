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
                "candidates": [{"asset_block_id": 10, "match_score": 0.51}, {"asset_block_id": 11, "match_score": 0.49}],
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
        {"block_id": 21, "marker_signature": {"type": "figure_number"}, "zone": "display_zone", "style_family": "legend_like"}
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
