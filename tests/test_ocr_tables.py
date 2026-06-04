"""Phase 2 contract tests for table inventory.

paperforge.worker.ocr_tables does not exist yet -- tests will fail until
Task 7 implements the module.
"""
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
