from __future__ import annotations


def test_aside_text_edge_band_is_noise_not_body() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    page_blocks = [
        {
            "block_label": "aside_text",
            "block_content": "Downloaded from http://journals.lww.com/example by user. For personal use only.",
            "block_bbox": [0, 200, 18, 1550],
            "page": 4,
        }
    ]
    role = assign_block_role(page_blocks[0], page_blocks, page_width=1200, page_height=1600)
    assert role.role == "noise"


def test_lowercase_panel_label_is_figure_inner_text() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    role = assign_block_role(
        {
            "block_label": "text",
            "block_content": "(a)",
            "block_bbox": [90, 90, 120, 120],
            "page": 1,
        },
        page_blocks=[],
    )
    assert role.role == "figure_inner_text"


def test_single_panel_label_is_figure_inner_text() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    page_blocks = [
        {
            "block_label": "text",
            "block_content": "A",
            "block_bbox": [90, 90, 120, 120],
            "page": 1,
        },
        {
            "block_label": "image",
            "block_content": "",
            "block_bbox": [80, 130, 500, 420],
            "page": 1,
        },
    ]

    role = assign_block_role(page_blocks[0], page_blocks, page_width=1200, page_height=1600)

    assert role.role == "figure_inner_text"


def test_left_margin_vertical_notice_is_not_body_paragraph() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    page_blocks = [
        {
            "block_label": "text",
            "block_content": "Downloaded from example.org by user on date. Copyright holder.",
            "block_bbox": [0, 220, 30, 1320],
            "page": 1,
        }
    ]

    role = assign_block_role(page_blocks[0], page_blocks, page_width=1200, page_height=1600)

    assert role.role in {"noise", "frontmatter_noise", "unknown_structural"}
    assert role.role != "body_paragraph"


def test_media_asset_can_match_table_caption_even_without_raw_table_label() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

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
            "raw_label": "image",
        },
    ]

    inventory = build_table_inventory(structured_blocks)

    assert inventory["official_table_count"] == 1
    assert inventory["tables"][0]["asset_block_id"] == "p3_b2"


def test_keep_formal_caption_seed_for_numbered_display_legend() -> None:
    from paperforge.worker.ocr_document import _should_keep_formal_caption_seed

    block = {
        "text": "Fig. 2 Migration of osteoblasts under stimulation.",
        "marker_signature": {"type": "figure_number"},
        "zone": "display_zone",
        "style_family": "legend_like",
    }

    assert _should_keep_formal_caption_seed(block) is True
