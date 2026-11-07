from __future__ import annotations

import copy
import random

def test_tail_segments_keep_original_indices_after_spatial_page_sort() -> None:
    from paperforge.worker.ocr_document import PageLayoutProfile, _build_tail_reading_order

    blocks = [
        {"page": 3, "block_id": "right", "role": "reference_item", "bbox": [650, 30, 1100, 60]},
        {"page": 3, "block_id": "left", "role": "reference_item", "bbox": [70, 30, 550, 60]},
    ]
    segments = _build_tail_reading_order(blocks, {3: PageLayoutProfile(column_count=2, column_boundaries=[600])})
    assert [blocks[index]["block_id"] for segment in segments for index in segment.block_indices] == ["left", "right"]





def test_layout_facts_and_box_merges_are_order_invariant() -> None:
    from paperforge.worker.ocr_document import _merge_box_content, compute_layout_facts

    blocks = [
        {"page": 1, "block_id": "title", "role": "section_heading", "text": "Full-width heading", "bbox": [60, 30, 1140, 70], "page_width": 1200},
        {"page": 1, "block_id": "left-1", "role": "body_paragraph", "text": "Left paragraph one.", "bbox": [70, 120, 560, 180], "page_width": 1200},
        {"page": 1, "block_id": "right-1", "role": "body_paragraph", "text": "Right paragraph one.", "bbox": [640, 120, 1130, 180], "page_width": 1200},
        {"page": 1, "block_id": "left-2", "role": "body_paragraph", "text": "Left paragraph two.", "bbox": [70, 190, 560, 250], "page_width": 1200},
        {"page": 1, "block_id": "right-2", "role": "body_paragraph", "text": "Right paragraph two.", "bbox": [640, 190, 1130, 250], "page_width": 1200},
        {"page": 1, "block_id": "caption", "role": "figure_caption", "text": "Figure 1. Example caption.", "bbox": [640, 300, 1130, 330], "page_width": 1200},
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1: Summary", "bbox": [70, 400, 220, 430], "page_width": 1200},
        {"page": 1, "block_id": "box-body-1", "role": "body_paragraph", "text": "Box body one.", "bbox": [70, 435, 560, 475], "page_width": 1200},
        {"page": 1, "block_id": "box-body-2", "role": "body_paragraph", "text": "Box body two.", "bbox": [70, 480, 560, 520], "page_width": 1200},
    ]

    def structure(rows: list[dict]) -> dict[str, tuple]:
        _merge_box_content(rows)
        facts = {(fact["page"], fact["block_id"]): fact for fact in compute_layout_facts(rows)}
        return {
            row["block_id"]: (
                row["role"], row.get("_container_text"), row.get("_container_of"),
                row.get("render_default"), facts[(row["page"], row["block_id"])]["layout_region"],
                facts[(row["page"], row["block_id"])]["display_cluster_candidate_id"],
            )
            for row in rows
        }

    expected = structure(copy.deepcopy(blocks))
    shuffled = copy.deepcopy(blocks)
    random.Random(211).shuffle(shuffled)
    assert structure(shuffled) == expected
    assert expected["box-body-1"][0] == "body_paragraph"
    assert expected["box-body-1"][2] == "box"
    assert expected["box-body-2"][2] == "box"


def test_layout_facts_disambiguate_reused_block_ids_by_page() -> None:
    from paperforge.worker.ocr_document import _attach_layout_facts

    blocks = [
        {"page": 1, "block_id": "same", "role": "body_paragraph", "bbox": [60, 10, 500, 30], "page_width": 600},
        {"page": 2, "block_id": "same", "role": "reference_item", "bbox": [700, 10, 1100, 30], "page_width": 1200},
    ]
    _attach_layout_facts(blocks)
    assert blocks[0]["reading_band_id"] != blocks[1]["reading_band_id"]


def test_box_merge_rejects_right_column_paragraph() -> None:
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 500, 130], "page_width": 1200},
        {"page": 1, "block_id": "right", "role": "body_paragraph", "text": "Right column.", "bbox": [650, 140, 1100, 180], "page_width": 1200},
    ]
    _merge_box_content(blocks)
    assert "_container_text" not in blocks[0]
    assert blocks[1]["role"] == "body_paragraph"


def test_box_merge_stops_after_bounded_vertical_gap() -> None:
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 500, 130], "page_width": 1200},
        {"page": 1, "block_id": "distant", "role": "body_paragraph", "text": "Distant paragraph.", "bbox": [70, 180, 500, 220], "page_width": 1200},
    ]
    _merge_box_content(blocks)
    assert "_container_text" not in blocks[0]
    assert blocks[1]["role"] == "body_paragraph"


def test_box_merge_stops_at_figure_asset() -> None:
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 500, 130], "page_width": 1200},
        {"page": 1, "block_id": "figure", "role": "figure_asset", "text": "", "bbox": [70, 140, 500, 200], "page_width": 1200},
        {"page": 1, "block_id": "after", "role": "body_paragraph", "text": "Not box content.", "bbox": [70, 210, 500, 240], "page_width": 1200},
    ]
    _merge_box_content(blocks)
    assert "_container_text" not in blocks[0]
    assert blocks[2]["text"] == "Not box content."
    assert blocks[2]["role"] == "body_paragraph"


def test_box_merge_rejects_body_beyond_column_right_bound() -> None:
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 220, 130], "page_width": 1200},
        {"page": 1, "block_id": "wide", "role": "body_paragraph", "text": "Too wide.", "bbox": [70, 140, 700, 180], "page_width": 1200},
    ]
    _merge_box_content(blocks)
    assert "_container_text" not in blocks[0]
    assert blocks[1]["role"] == "body_paragraph"

def test_box_merge_ignores_non_body_blocks_in_the_other_column() -> None:
    """A right-column caption below a left-column Box must not end the merge."""
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 220, 130], "page_width": 1200},
        {"page": 1, "block_id": "right-caption", "role": "figure_caption", "text": "Figure 2.", "bbox": [650, 140, 1100, 170], "page_width": 1200},
        {"page": 1, "block_id": "left-body", "role": "body_paragraph", "text": "Still box content.", "bbox": [70, 140, 560, 180], "page_width": 1200},
    ]
    _merge_box_content(blocks)

    assert blocks[0].get("_container_text") == "Box 1\nStill box content."
    assert blocks[2].get("_container_of") == "box"
    assert blocks[2]["role"] == "body_paragraph"

def test_box_merge_requires_an_explicit_page_width() -> None:
    """A bbox-derived width is not evidence of the page's column geometry."""
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 220, 130]},
        {"page": 1, "block_id": "body", "role": "body_paragraph", "text": "Box body.", "bbox": [70, 140, 500, 180]},
    ]
    _merge_box_content(blocks)

    assert "_container_text" not in blocks[0]
    assert blocks[1].get("_container_of") is None


def test_box_merge_merges_when_the_page_width_is_explicit() -> None:
    from paperforge.worker.ocr_document import _merge_box_content

    blocks = [
        {"page": 1, "block_id": "box", "role": "structured_insert", "text": "Box 1", "bbox": [70, 100, 220, 130], "page_width": 1200},
        {"page": 1, "block_id": "body", "role": "body_paragraph", "text": "Box body.", "bbox": [70, 140, 500, 180], "page_width": 1200},
    ]
    _merge_box_content(blocks)

    assert blocks[0].get("_container_text") == "Box 1\nBox body."
    assert blocks[1].get("_container_of") == "box"
