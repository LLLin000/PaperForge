"""Tests for OCR object writeback (Workstream A)."""
from __future__ import annotations


def test_apply_object_writebacks_preserves_existing_role_writebacks() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {"block_id": "fa1", "page": 3, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 400, 400], "text": ""},
        {"block_id": "ta1", "page": 3, "role": "media_asset", "raw_label": "table", "bbox": [450, 100, 850, 400], "text": ""},
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "page": 3,
                "figure_id": "figure_001",
                "matched_assets": [{"block_id": "fa1", "bbox": [100, 100, 400, 400]}],
                "asset_block_ids": ["fa1"],
            }
        ]
    }
    table_inventory = {
        "tables": [
            {
                "page": 3,
                "table_id": "table_001",
                "asset_block_id": "ta1",
            }
        ]
    }

    report = apply_object_writebacks(
        structured_blocks=blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    by_id = {b["block_id"]: b for b in blocks}
    assert by_id["fa1"]["role"] == "figure_asset"
    assert by_id["ta1"]["role"] == "table_html"
    assert report["applied_count"] >= 2


def test_apply_object_writebacks_records_consumed_block_contract() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {"block_id": "fa1", "page": 3, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 400, 400], "text": ""},
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "page": 3,
                "figure_id": "figure_001",
                "matched_assets": [{"block_id": "fa1", "bbox": [100, 100, 400, 400]}],
                "asset_block_ids": ["fa1"],
            }
        ]
    }
    table_inventory = {"tables": []}

    report = apply_object_writebacks(
        structured_blocks=blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert blocks[0]["_object_owner_family"] == "figure"
    assert blocks[0]["_object_owner_id"] == "figure_001"
    assert blocks[0]["_object_owner_role"] == "asset"
    assert blocks[0]["_object_writeback_phase"] == "post_inventory"
    assert blocks[0]["_object_consumed"] is True
    assert figure_inventory["matched_figures"][0]["consumed_block_ids"] == ["fa1"]
    assert report["claims"][0]["owner_id"] == "figure_001"


def test_apply_object_writebacks_is_idempotent() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {"block_id": "fa1", "page": 3, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 400, 400], "text": ""},
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "page": 3,
                "figure_id": "figure_001",
                "matched_assets": [{"block_id": "fa1", "bbox": [100, 100, 400, 400]}],
                "asset_block_ids": ["fa1"],
            }
        ]
    }
    table_inventory = {"tables": []}

    first = apply_object_writebacks(structured_blocks=blocks, figure_inventory=figure_inventory, table_inventory=table_inventory)
    second = apply_object_writebacks(structured_blocks=blocks, figure_inventory=figure_inventory, table_inventory=table_inventory)

    assert second["applied_count"] == 0
    assert first["consumed_block_ids"] == second["consumed_block_ids"]


def test_side_adjacent_text_claims_are_written_for_matched_figure() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {
            "block_id": "txt1",
            "page": 8,
            "role": "body_paragraph",
            "raw_label": "text",
            "bbox": [191, 1022, 514, 1083],
            "text": "Age in years - 67:52.8",
            "span_metadata": {"font": "Arial", "size": 10},
        },
        {
            "block_id": "cap1",
            "page": 8,
            "role": "figure_caption",
            "raw_label": "text",
            "bbox": [534, 1340, 978, 1370],
            "text": "Figure 1. Caption.",
            "span_metadata": {"font": "Arial", "size": 10},
        },
        {
            "block_id": "asset1",
            "page": 8,
            "role": "figure_asset",
            "raw_label": "image",
            "bbox": [534, 976, 978, 1334],
            "text": "",
        },
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "page": 8,
                "figure_id": "figure_a001",
                "legend_block_id": "cap1",
                "matched_assets": [{"block_id": "asset1", "bbox": [534, 976, 978, 1334]}],
                "asset_block_ids": ["asset1"],
                "cluster_bbox": [534, 976, 978, 1334],
            }
        ]
    }
    table_inventory = {"tables": []}

    report = apply_object_writebacks(
        structured_blocks=blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    by_id = {b["block_id"]: b for b in blocks}
    assert by_id["txt1"]["role"] == "figure_inner_text"
    assert by_id["txt1"]["_object_owner_id"] == "figure_a001"
    assert by_id["txt1"]["_object_association_reason"] == "side_adjacent"
    assert "txt1" in figure_inventory["matched_figures"][0]["associated_text_block_ids"]
    assert any(c["owner_id"] == "figure_a001" and c["owner_role"] == "inner_text" for c in report["claims"])


def test_side_adjacent_score_requires_container_caption_and_uncontested_layout() -> None:
    from paperforge.worker.ocr_object_writeback import _score_side_adjacent_text_claim

    block = {
        "block_id": "note",
        "page": 1,
        "raw_label": "text",
        "role": "body_paragraph",
        "text": "Panel note",
        "bbox": [80, 150, 90, 180],
        "span_metadata": {"font": "Arial", "size": 10},
    }
    figure = {
        "figure_id": "fig1",
        "page": 1,
        "cluster_bbox": [100, 100, 300, 300],
        "legend_block_id": "cap",
    }
    caption = {
        "block_id": "cap",
        "page": 1,
        "role": "figure_caption",
        "span_metadata": {"font": "Arial", "size": 10},
    }

    weak_block = {**block, "bbox": [80, 70, 90, 110]}
    weak_score = _score_side_adjacent_text_claim(weak_block, figure)
    assert 0 <= weak_score < 0.9
    assert _score_side_adjacent_text_claim(block, figure, page_blocks=[block, caption]) >= 0.9

    body_paragraph = {
        "block_id": "gap_text",
        "page": 1,
        "role": "body_paragraph",
        "raw_label": "text",
        "bbox": [92, 150, 98, 180],
    }
    assert _score_side_adjacent_text_claim(
        block, figure, page_blocks=[block, caption, body_paragraph]
    ) >= 0.9

    competitor = {"figure_id": "fig2", "cluster_bbox": [30, 100, 70, 300], "page": 1}
    competitor_score = _score_side_adjacent_text_claim(
        block,
        figure,
        page_blocks=[block, caption],
        page_figures=[figure, competitor],
    )
    assert competitor_score < 0.9

    visual_separator = {
        "block_id": "separator",
        "page": 1,
        "raw_label": "image",
        "bbox": [92, 150, 98, 180],
    }
    separator_score = _score_side_adjacent_text_claim(
        block,
        figure,
        page_blocks=[block, caption, visual_separator],
    )
    assert separator_score < 0.9



def test_side_adjacent_claim_with_missing_caption_uses_available_evidence() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    note = {
        "block_id": "note",
        "page": 1,
        "role": "body_paragraph",
        "raw_label": "text",
        "text": "Panel note",
        "bbox": [80, 150, 90, 180],
        "_in_visual_container": True,
    }
    figure = {
        "figure_id": "fig1",
        "page": 1,
        "cluster_bbox": [100, 100, 300, 300],
    }
    report = apply_object_writebacks(
        structured_blocks=[note],
        figure_inventory={"matched_figures": [figure]},
        table_inventory={"tables": []},
    )

    assert note["role"] == "figure_inner_text"
    assert note["_object_owner_id"] == "fig1"
    assert report["claims"][0]["confidence"] >= 0.9

def test_protected_roles_are_never_stolen_by_side_adjacent_claims() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {
            "block_id": "ref1",
            "page": 8,
            "role": "reference_item",
            "raw_label": "reference_content",
            "bbox": [191, 1022, 514, 1083],
            "text": "63. Some reference",
        },
        {
            "block_id": "asset1",
            "page": 8,
            "role": "figure_asset",
            "raw_label": "image",
            "bbox": [534, 976, 978, 1334],
            "text": "",
        },
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "page": 8,
                "figure_id": "figure_a001",
                "matched_assets": [{"block_id": "asset1", "bbox": [534, 976, 978, 1334]}],
                "asset_block_ids": ["asset1"],
                "cluster_bbox": [534, 976, 978, 1334],
            }
        ]
    }
    table_inventory = {"tables": []}

    report = apply_object_writebacks(
        structured_blocks=blocks,
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert blocks[0]["role"] == "reference_item"
    assert report["applied"] == [] or all(item.get("block_id") != "ref1" for item in report["applied"])


def test_apply_object_writebacks_respects_page_for_duplicate_block_ids() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {"block_id": "99", "page": 1, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 400, 400], "text": ""},
        {"block_id": "99", "page": 2, "role": "media_asset", "raw_label": "image", "bbox": [100, 100, 400, 400], "text": ""},
    ]
    figure_inventory = {
        "matched_figures": [
            {"page": 1, "figure_id": "fig1", "matched_assets": [{"block_id": "99", "bbox": [100, 100, 400, 400]}], "asset_block_ids": ["99"]},
        ]
    }
    table_inventory = {"tables": []}

    apply_object_writebacks(structured_blocks=blocks, figure_inventory=figure_inventory, table_inventory=table_inventory)

    # Page 1, block 99 should be claimed (matched figure is on page 1)
    assert blocks[0]["_object_consumed"] is True
    assert blocks[0]["_object_owner_role"] == "asset"
    # Page 2, block 99 should NOT be claimed (matched figure is on page 1)
    assert blocks[1].get("_object_consumed") is not True


def test_contained_figure_text_stamps_ownership_evidence() -> None:
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks

    blocks = [
        {
            "block_id": "asset1",
            "page": 5,
            "role": "figure_asset",
            "raw_label": "image",
            "bbox": [100, 100, 400, 400],
            "text": "",
        },
        {
            "block_id": "inner1",
            "page": 5,
            "role": "body_paragraph",
            "raw_label": "text",
            "bbox": [120, 120, 380, 200],
            "text": "Age 42",
        },
    ]
    figure_inventory = {
        "matched_figures": [
            {
                "page": 5,
                "figure_id": "fig1",
                "matched_assets": [{"block_id": "asset1", "bbox": [100, 100, 400, 400]}],
                "asset_block_ids": ["asset1"],
                "cluster_bbox": [100, 100, 400, 400],
            }
        ]
    }
    table_inventory = {"tables": []}

    report = apply_object_writebacks(structured_blocks=blocks, figure_inventory=figure_inventory, table_inventory=table_inventory)

    inner = blocks[1]
    assert inner["_object_owner_family"] == "figure"
    assert inner["_object_owner_role"] == "inner_text"
    assert inner["_object_association_reason"] == "contained"
    assert inner["_object_consumed"] is True
    assert "inner1" in figure_inventory["matched_figures"][0].get("consumed_block_ids", [])
    assert any(c["owner_id"] == "fig1" and c["association_reason"] == "contained" for c in report["claims"])

def test_side_adjacent_claim_records_evidence_coverage() -> None:
    """A normalised score must not be reported as a calibrated probability."""
    from paperforge.worker.ocr_object_writeback import _side_adjacent_evidence, apply_object_writebacks

    note = {
        "block_id": "note",
        "page": 1,
        "role": "body_paragraph",
        "raw_label": "text",
        "text": "Panel note",
        "bbox": [80, 150, 90, 180],
        "_in_visual_container": True,
    }
    figure = {"figure_id": "fig1", "page": 1, "cluster_bbox": [100, 100, 300, 300]}

    score, coverage = _side_adjacent_evidence(note, figure)
    assert score >= 0.9
    assert coverage < 1.0, "caption style was not evaluable; coverage must say so"

    report = apply_object_writebacks(
        structured_blocks=[note],
        figure_inventory={"matched_figures": [figure]},
        table_inventory={"tables": []},
    )
    claim = report["claims"][0]
    assert claim["confidence"] >= 0.9
    assert claim["evidence_coverage"] == coverage


def test_side_adjacent_caption_style_is_page_scoped() -> None:
    """A same-id caption on another page must not supply style evidence."""
    from paperforge.worker.ocr_object_writeback import _side_adjacent_evidence

    note = {
        "block_id": "note",
        "page": 1,
        "role": "body_paragraph",
        "raw_label": "text",
        "text": "Panel note",
        "bbox": [80, 150, 90, 180],
        "_in_visual_container": True,
        "span_metadata": {"font": "Arial", "size": 10},
    }
    figure = {"figure_id": "fig1", "page": 1, "cluster_bbox": [100, 100, 300, 300], "legend_block_id": "cap"}
    caption_other_page = {
        "block_id": "cap",
        "page": 2,
        "role": "figure_caption",
        "span_metadata": {"font": "Arial", "size": 10},
    }

    _score, coverage = _side_adjacent_evidence(note, figure, page_blocks=[note, caption_other_page])
    assert coverage < 1.0, "the caption was on another page; style is not evaluable"
