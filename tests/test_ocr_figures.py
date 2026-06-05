"""Phase 2 contract tests for figure inventory.

paperforge.worker.ocr_figures does not exist yet -- tests will fail until
Task 5 implements the module.
"""

from __future__ import annotations


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
