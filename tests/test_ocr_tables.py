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
    assert "held_tables" in inventory
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


def test_validation_first_table_candidate_remains_stable_under_anchor_first_roles() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY010B",
            "page": 6,
            "block_id": "p6_a1",
            "role": "table_asset",
            "raw_label": "table",
            "text": "parsed table image",
            "bbox": [120, 140, 760, 520],
        },
        {
            "paper_id": "KEY010B",
            "page": 6,
            "block_id": "p6_c1",
            "role": "body_paragraph",
            "raw_label": "text",
            "text": "Table 4. Quantitative outcomes for anchor-first validation.",
            "bbox": [120, 540, 760, 600],
            "zone": "display_zone",
            "style_family": "table_caption_like",
            "marker_signature": {"type": "table_number", "number": 4},
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    assert inventory["tables"][0]["caption_block_id"] == "p6_c1"
    assert inventory["tables"][0]["has_asset"] is True


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
    assert t["asset_block_id"] == "p3_a1"


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


def test_table_inventory_match_score_evidence() -> None:
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
    ]

    inventory = build_table_inventory(structured_blocks)
    assert len(inventory["tables"]) == 1
    table = inventory["tables"][0]
    assert "match_score" in table
    assert table["match_score"]["decision"] in {"matched", "continuation"}
    assert table["match_score"]["evidence"]


def test_table_matching_can_hold_when_caption_and_asset_conflict() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 12,
            "block_id": "p12_b1",
            "zone": "display_zone",
            "style_family": "table_caption_like",
            "text": "Table 2.",
            "marker_signature": {"type": "table_number", "number": 2},
            "bbox": [50, 50, 300, 90],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 12,
            "block_id": "p12_b2",
            "zone": "display_zone",
            "style_family": "unknown_like",
            "text": "",
            "marker_signature": {"type": "none"},
            "raw_label": "table",
            "bbox": [50, 120, 900, 500],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_table_inventory(structured_blocks)

    assert inv["held_tables"]
    assert inv["tables"] == []
    held = inv["held_tables"][0]
    assert held["hold_reason"] == "insufficient_caption_evidence"
    assert held["caption_block_id"] == "p12_b1"


def test_validation_first_table_candidate_with_asset_can_still_match() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 7,
            "block_id": "p7_b1",
            "zone": "display_zone",
            "style_family": "table_caption_like",
            "text": "Table 3. Cell counts across conditions",
            "marker_signature": {"type": "table_number", "number": 3},
            "bbox": [100, 100, 700, 140],
            "page_width": 1200,
            "page_height": 1600,
        },
        {
            "paper_id": "K001",
            "page": 7,
            "block_id": "p7_b2",
            "role": "table_asset",
            "raw_label": "table",
            "text": "",
            "bbox": [100, 160, 700, 520],
            "page_width": 1200,
            "page_height": 1600,
        },
    ]

    inv = build_table_inventory(structured_blocks)

    assert inv["held_tables"] == []
    assert len(inv["tables"]) == 1
    assert inv["tables"][0]["has_asset"] is True
    assert inv["tables"][0]["match_status"] == "matched"


def test_table_continuation_match_score_evidence() -> None:
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
    assert "match_score" in t
    assert t["match_score"]["decision"] == "continuation"
    assert "continuation_same_page" in t["match_score"]["evidence"]


def test_table_inventory_considers_previous_page_assets() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    blocks = [
        {"block_id": "asset1", "role": "table_asset", "page": 1, "bbox": [100, 900, 700, 1200]},
        {"block_id": "cap1", "role": "table_caption", "page": 2, "text": "Table 1. Baseline characteristics", "bbox": [100, 80, 700, 120]},
    ]

    inventory = build_table_inventory(blocks)

    table = inventory["tables"][0]
    assert table["asset_block_id"] == "asset1"
    assert table["match_status"] in {"matched", "matched_low_confidence"}


def test_table_inventory_marks_close_scores_ambiguous() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    blocks = [
        {"block_id": "cap1", "role": "table_caption", "page": 1, "text": "Table 1. Baseline characteristics", "bbox": [100, 100, 700, 140]},
        {"block_id": "asset1", "role": "table_asset", "page": 1, "bbox": [100, 160, 700, 400]},
        {"block_id": "asset2", "role": "table_asset", "page": 1, "bbox": [105, 165, 705, 405]},
    ]

    inventory = build_table_inventory(blocks)
    table = inventory["tables"][0]
    assert table["match_status"] == "ambiguous"
    assert table["has_asset"] is False
    assert len(table["candidate_assets"]) == 2
