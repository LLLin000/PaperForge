"""Task 5 tests for hardened table matching."""
from __future__ import annotations


def test_table_image_is_truth_source_and_text_is_assistive() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_b10",
            "role": "table_asset",
            "text": "raw parsed cells",
            "bbox": [100, 100, 600, 500],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_b11",
            "role": "table_caption",
            "text": "Table 1. Results",
            "bbox": [100, 520, 600, 560],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    assert inventory["tables"][0]["truth_source"] == "image"


def test_table_inventory_includes_all_sections() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    inventory = build_table_inventory([])

    assert "tables" in inventory
    assert "unmatched_captions" in inventory
    assert "unmatched_assets" in inventory
    assert "official_table_count" in inventory


def test_table_without_asset_is_tracked_as_unmatched_caption() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 7,
            "block_id": "p7_b5",
            "role": "table_caption",
            "text": "Table 2. Data",
            "bbox": [50, 50, 500, 80],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 0
    assert len(inventory["unmatched_captions"]) == 1


def test_continuation_table_matches_same_page_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 10,
            "block_id": "p10_a1",
            "role": "table_asset",
            "text": "continued data",
            "bbox": [100, 100, 600, 400],
        },
        {
            "paper_id": "KEY001",
            "page": 10,
            "block_id": "p10_c1",
            "role": "table_caption",
            "text": "Table 1 (Continued)",
            "bbox": [100, 420, 600, 460],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert len(inventory["tables"]) == 1
    t = inventory["tables"][0]
    assert t["is_continuation"] is True
    assert t["has_asset"] is True
    assert t["asset_block_id"] == "p10_a1"


def test_continuation_does_not_increment_official_count() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "text": "table data",
            "bbox": [100, 100, 600, 400],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1. Main data",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "p6_a1",
            "role": "table_asset",
            "text": "continued data",
            "bbox": [100, 100, 600, 300],
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "p6_c1",
            "role": "table_caption",
            "text": "Table 1 (Continued)",
            "bbox": [100, 320, 600, 360],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    normal = [t for t in inventory["tables"] if not t["is_continuation"]]
    continued = [t for t in inventory["tables"] if t["is_continuation"]]
    assert len(normal) == 1
    assert len(continued) == 1
    assert normal[0]["has_asset"] is True
    assert continued[0]["has_asset"] is True


def test_continuation_without_asset_has_has_asset_false() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 10,
            "block_id": "p10_c1",
            "role": "table_caption",
            "text": "Table 1 (Continued)",
            "bbox": [100, 100, 600, 140],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert len(inventory["tables"]) == 1
    assert inventory["tables"][0]["is_continuation"] is True
    assert inventory["tables"][0]["has_asset"] is False
    assert len(inventory["unmatched_captions"]) == 1


def test_multi_signal_scoring_prefers_better_asset() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_a1",
            "role": "table_asset",
            "text": "far table",
            "bbox": [50, 600, 300, 800],
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_a2",
            "role": "table_asset",
            "text": "near table",
            "bbox": [50, 50, 550, 300],
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_c1",
            "role": "table_caption",
            "text": "Table 3. Nearby data",
            "bbox": [50, 310, 550, 350],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    t = inventory["tables"][0]
    assert t["asset_block_id"] == "p3_a2"


def test_continuation_matches_only_same_page_not_adjacent() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 4,
            "block_id": "p4_a1",
            "role": "table_asset",
            "text": "wrong page",
            "bbox": [100, 100, 600, 400],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "text": "same page",
            "bbox": [100, 100, 600, 400],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 2 (cont.)",
            "bbox": [100, 420, 600, 460],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert len(inventory["tables"]) == 1
    t = inventory["tables"][0]
    assert t["is_continuation"] is True
    assert t["asset_block_id"] == "p5_a1"


def test_multiple_captions_match_correct_assets_in_order() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "a5b",
            "role": "table_asset",
            "text": "table 1 body",
            "bbox": [100, 100, 600, 400],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "c5a",
            "role": "table_caption",
            "text": "Table 1. First",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "a6b",
            "role": "table_asset",
            "text": "table 2 body",
            "bbox": [100, 100, 600, 400],
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "c6a",
            "role": "table_caption",
            "text": "Table 2. Second",
            "bbox": [100, 420, 600, 460],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 2
    assert inventory["tables"][0]["asset_block_id"] == "a5b"
    assert inventory["tables"][1]["asset_block_id"] == "a6b"
