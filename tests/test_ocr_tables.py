"""Task 5 tests for hardened table matching."""

from __future__ import annotations


def test_extract_table_number_chinese_biao_prefix() -> None:
    from paperforge.worker.ocr_tables import _extract_table_number

    assert _extract_table_number("表 3 术前规划时间比较") == 3


def test_extract_table_number_garbled_biao_prefix() -> None:
    from paperforge.worker.ocr_tables import _extract_table_number

    assert _extract_table_number("�� 4 AIHIP术前规划结果") == 4


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


def test_table_inventory_preserves_asset_family_hints() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_b10",
            "role": "table_asset",
            "raw_label": "table",
            "asset_family_hint": "table_like",
            "asset_family_confidence": 0.70,
            "asset_family_evidence": ["raw_label:table"],
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
    table = inventory["tables"][0]

    assert table["asset_family_hint"] == "table_like"
    assert table["asset_family_confidence"] == 0.70
    assert table["asset_family_evidence"] == ["raw_label:table"]


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


def test_weak_explicit_table_caption_matches_with_strong_geometry() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 9,
            "block_id": "p9_c1",
            "role": "table_caption",
            "text": "Table 2.",
            "bbox": [100, 100, 700, 140],
        },
        {
            "paper_id": "K001",
            "page": 9,
            "block_id": "p9_a1",
            "role": "table_asset",
            "raw_label": "table",
            "text": "",
            "bbox": [100, 160, 700, 520],
        },
    ]

    inv = build_table_inventory(structured_blocks)

    assert inv["held_tables"] == []
    assert len(inv["tables"]) == 1
    table = inv["tables"][0]
    assert table["has_asset"] is True
    assert table["asset_block_id"] == "p9_a1"


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
        {
            "block_id": "cap1",
            "role": "table_caption",
            "page": 2,
            "text": "Table 1. Baseline characteristics",
            "bbox": [100, 80, 700, 120],
        },
    ]

    inventory = build_table_inventory(blocks)

    table = inventory["tables"][0]
    assert table["asset_block_id"] == "asset1"
    assert table["match_status"] in {"matched", "matched_low_confidence"}


def test_table_inventory_marks_close_scores_ambiguous() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    blocks = [
        {
            "block_id": "cap1",
            "role": "table_caption",
            "page": 1,
            "text": "Table 1. Baseline characteristics",
            "bbox": [100, 100, 700, 140],
        },
        {"block_id": "asset1", "role": "table_asset", "page": 1, "bbox": [100, 160, 700, 400]},
        {"block_id": "asset2", "role": "table_asset", "page": 1, "bbox": [105, 165, 705, 405]},
    ]

    inventory = build_table_inventory(blocks)
    table = inventory["tables"][0]
    assert table["match_status"] == "ambiguous"
    assert table["has_asset"] is False
    assert len(table["candidate_assets"]) == 2


def test_table_note_binds_footnote_role_block_adjacent_below_asset() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_fn1",
            "role": "footnote",
            "raw_label": "table_footnote",
            "text": "* p < 0.05",
            "bbox": [100, 410, 600, 435],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    t = inventory["tables"][0]
    assert t["note_block_ids"] == ["p5_fn1"]


def test_table_note_binds_short_text_block_adjacent_below_asset() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_bn1",
            "role": "body_paragraph",
            "text": "Data are mean ± SD.",
            "bbox": [100, 410, 600, 430],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    t = inventory["tables"][0]
    assert t["note_block_ids"] == ["p5_bn1"]


def test_table_note_excludes_block_too_far_below_asset() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_far",
            "role": "footnote",
            "text": "too far below",
            "bbox": [100, 520, 600, 540],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    t = inventory["tables"][0]
    assert t["note_block_ids"] == []


def test_table_note_excludes_block_on_different_page() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "p6_fn1",
            "role": "footnote",
            "text": "* p < 0.05",
            "bbox": [100, 110, 600, 130],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    t = inventory["tables"][0]
    assert t["note_block_ids"] == []


def test_table_note_excludes_section_headings_from_short_text_match() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_sh",
            "role": "section_heading",
            "text": "Results",
            "bbox": [100, 410, 300, 430],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    t = inventory["tables"][0]
    assert t["note_block_ids"] == []


def test_table_note_binds_vision_footnote_raw_label() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_vf1",
            "role": "body_paragraph",
            "raw_label": "vision_footnote",
            "text": "Abbreviations: CI, confidence interval",
            "bbox": [100, 405, 600, 425],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    t = inventory["tables"][0]
    assert t["note_block_ids"] == ["p5_vf1"]


def test_table_note_binds_multiple_adjacent_notes() -> None:
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
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_fn1",
            "role": "footnote",
            "text": "* p < 0.05",
            "bbox": [100, 405, 600, 420],
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "p5_fn2",
            "role": "footnote",
            "text": "** p < 0.01",
            "bbox": [100, 422, 600, 438],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    t = inventory["tables"][0]
    assert set(t["note_block_ids"]) == {"p5_fn1", "p5_fn2"}


def test_table_without_matched_asset_has_empty_note_block_ids() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 7,
            "block_id": "p7_c1",
            "role": "table_caption",
            "text": "Table 2. No asset here",
            "bbox": [50, 50, 500, 80],
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["tables"][0]["note_block_ids"] == []


def test_table_inventory_emits_note_payload_and_consumed_block_ids() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 5, "block_id": "p5_a1", "role": "table_asset", "text": "table data", "bbox": [100, 100, 600, 400]},
        {
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "page": 5,
            "block_id": "p5_n1",
            "role": "footnote",
            "raw_label": "table_footnote",
            "text": "* p < 0.05",
            "bbox": [100, 405, 600, 425],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["note_block_ids"] == ["p5_n1"]
    assert table["note_texts"] == ["* p < 0.05"]
    assert set(table["consumed_block_ids"]) == {"p5_a1", "p5_c1", "p5_n1"}


def test_matched_table_asset_role_is_written_back() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory, write_back_table_roles

    structured_blocks = [
        {
            "paper_id": "K001",
            "page": 3,
            "block_id": "p3_b1",
            "role": "table_caption_candidate",
            "text": "Table 1. Baseline characteristics.",
            "bbox": [100, 460, 620, 520],
            "page_width": 1200,
            "page_height": 1600,
            "raw_label": "text",
        },
        {
            "paper_id": "K001",
            "page": 3,
            "block_id": "p3_b2",
            "role": "media_asset",
            "text": "",
            "bbox": [100, 100, 640, 430],
            "page_width": 1200,
            "page_height": 1600,
            "raw_label": "table",
        },
    ]
    inv = build_table_inventory(structured_blocks)
    write_back_table_roles(inv, structured_blocks)
    asset = next(b for b in structured_blocks if b["block_id"] == "p3_b2")
    assert asset["role"] == "table_html"


def test_bare_table_number_matches_when_geometry_and_table_evidence_are_strong() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 5, "block_id": "p5_c1", "role": "table_caption", "text": "Table 1", "bbox": [100, 100, 600, 140]},
        {
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 160, 600, 400],
            "text": "",
        },
    ]
    inventory = build_table_inventory(structured_blocks)
    assert len(inventory["tables"]) == 1
    table = inventory["tables"][0]
    assert table["has_asset"] is True
    assert table["asset_block_id"] == "p5_a1"


def test_page_footnote_prior_prevents_table_at_page_bottom_from_absorbing_footer_note() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 4,
            "block_id": "p4_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [80, 980, 760, 1280],
            "text": "",
        },
        {
            "page": 4,
            "block_id": "p4_c1",
            "role": "table_caption",
            "text": "Table 2. Results",
            "bbox": [80, 1295, 760, 1330],
        },
        {
            "page": 4,
            "block_id": "p4_fn1",
            "role": "footnote",
            "raw_label": "vision_footnote",
            "text": "* Correspondence footnote",
            "bbox": [80, 1365, 760, 1390],
        },
        {
            "page": 2,
            "block_id": "p2_fn1",
            "role": "footnote",
            "raw_label": "vision_footnote",
            "text": "* prior footer",
            "bbox": [70, 1360, 750, 1388],
        },
        {
            "page": 3,
            "block_id": "p3_fn1",
            "role": "footnote",
            "raw_label": "vision_footnote",
            "text": "* prior footer",
            "bbox": [72, 1362, 748, 1389],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["note_block_ids"] == []
    assert table["note_bboxes"] == []
    assert table["note_band_bbox"] == []
    assert table["note_confidence"] == 0.0
    assert table["note_match_reason"] == "page_footnote_prior_rejected"


def test_table_note_blocks_group_into_single_note_band() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 100, 640, 430],
            "text": "",
        },
        {
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1. Main results",
            "bbox": [100, 445, 640, 475],
        },
        {
            "page": 5,
            "block_id": "p5_n1",
            "role": "footnote",
            "raw_label": "table_footnote",
            "text": "* p < 0.05",
            "bbox": [110, 440, 520, 458],
        },
        {
            "page": 5,
            "block_id": "p5_n2",
            "role": "footnote",
            "raw_label": "table_footnote",
            "text": "Data are mean ± SD.",
            "bbox": [110, 460, 560, 480],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["note_block_ids"] == ["p5_n1", "p5_n2"]
    assert table["note_texts"] == ["* p < 0.05", "Data are mean ± SD."]
    assert table["note_bboxes"] == [[110, 440, 520, 458], [110, 460, 560, 480]]
    assert table["note_band_bbox"] == [110, 440, 560, 480]
    assert table["note_confidence"] == 0.85
    assert table["note_match_reason"] == "note_band_geometry_match"


def test_bare_table_number_stays_ambiguous_when_competing_assets_are_close() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 100, 430, 400],
            "text": "",
        },
        {
            "page": 5,
            "block_id": "p5_a2",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [450, 100, 780, 400],
            "text": "",
        },
        {"page": 5, "block_id": "p5_c1", "role": "table_caption", "text": "Table 1", "bbox": [100, 420, 780, 450]},
    ]
    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]
    assert table["has_asset"] is False
    assert table["match_status"] == "ambiguous"


def test_bare_table_number_prefers_candidate_with_better_x_overlap_and_shorter_vertical_gap() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 6,
            "block_id": "p6_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 200, 600, 500],
            "text": "",
        },
        {
            "page": 6,
            "block_id": "p6_a2",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [620, 120, 980, 520],
            "text": "",
        },
        {"page": 6, "block_id": "p6_c1", "role": "table_caption", "text": "Table 3", "bbox": [100, 520, 600, 545]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["asset_block_id"] == "p6_a1"
    assert table["match_status"] in {"matched", "matched_low_confidence"}


def test_bare_table_number_can_match_previous_page_continuation_under_strong_geometry() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 7,
            "block_id": "p7_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 120, 640, 1000],
            "text": "",
        },
        {"page": 8, "block_id": "p8_c1", "role": "table_caption", "text": "Table 4", "bbox": [100, 90, 640, 120]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["match_status"] in {"matched_low_confidence", "matched"}
    assert table["asset_block_id"] == "p7_a1"


def test_table_inventory_keeps_bridge_gap_inside_sparse_display_cluster() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 10, "block_id": "table_asset", "role": "table_asset", "raw_label": "table", "bbox": [100, 120, 620, 420], "text": "", "layout_region": "display_zone"},
        {"page": 10, "block_id": "gap_block", "role": "unknown_structural", "bbox": [640, 130, 930, 420], "text": "", "layout_region": "display_zone", "bridge_eligible": True},
        {"page": 10, "block_id": "table_caption", "role": "table_caption", "bbox": [120, 450, 900, 490], "text": "Table 1. Sparse reconstruction.", "layout_region": "display_zone"},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]
    assert table["asset_block_id"] == "table_asset"
    assert table.get("bridge_block_ids") == ["gap_block"]


def test_bare_table_number_caption_matches_with_strong_geometry() -> None:
    """Bare 'Table N.' captions with same-page, x_overlap, asset-below evidence
    should match a table asset, not be left as unmatched/ambiguous."""
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_asset",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 540, 600, 900],
            "text": "",
        },
        {
            "page": 5,
            "block_id": "p5_caption",
            "role": "table_caption",
            "text": "Table 1.",
            "bbox": [100, 500, 600, 540],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    assert inventory["official_table_count"] == 1
    table = inventory["tables"][0]
    assert table["has_asset"] is True
    assert table["match_status"] in {"matched", "matched_low_confidence"}
    assert table["asset_block_id"] == "p5_asset"
