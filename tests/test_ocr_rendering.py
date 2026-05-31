from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image


def test_caption_group_assignments_respects_columns() -> None:
    from paperforge.worker.ocr import caption_group_assignments

    blocks = [
        {
            "block_id": 1,
            "block_label": "chart",
            "block_bbox": [80, 116, 546, 434],
            "block_content": "",
        },
        {
            "block_id": 2,
            "block_label": "figure_title",
            "block_bbox": [66, 446, 559, 628],
            "block_content": "Figure 1. Left column figure.",
        },
        {
            "block_id": 3,
            "block_label": "chart",
            "block_bbox": [598, 114, 1063, 493],
            "block_content": "",
        },
        {
            "block_id": 4,
            "block_label": "figure_title",
            "block_bbox": [584, 503, 1079, 744],
            "block_content": "Figure 2. Right column figure.",
        },
    ]

    figure_map, _table_map = caption_group_assignments(blocks)

    left_ids = [item["block_id"] for item in figure_map[2]]
    right_ids = [item["block_id"] for item in figure_map[4]]

    assert left_ids == [1]
    assert right_ids == [3]


def test_validate_block_order_falls_back_to_column_major_on_excessive_switches() -> None:
    from paperforge.worker.ocr import validate_block_order

    blocks = [
        {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [80, 100, 500, 140], "block_content": "L1"},
        {"block_id": 2, "block_label": "text", "block_order": 1, "block_bbox": [700, 110, 1120, 150], "block_content": "R1"},
        {"block_id": 3, "block_label": "text", "block_order": 2, "block_bbox": [80, 200, 500, 240], "block_content": "L2"},
        {"block_id": 4, "block_label": "text", "block_order": 3, "block_bbox": [700, 210, 1120, 250], "block_content": "R2"},
        {"block_id": 5, "block_label": "text", "block_order": 4, "block_bbox": [80, 300, 500, 340], "block_content": "L3"},
        {"block_id": 6, "block_label": "text", "block_order": 5, "block_bbox": [700, 310, 1120, 350], "block_content": "R3"},
        {"block_id": 7, "block_label": "text", "block_order": 6, "block_bbox": [80, 400, 500, 440], "block_content": "L4"},
        {"block_id": 8, "block_label": "text", "block_order": 7, "block_bbox": [700, 410, 1120, 450], "block_content": "R4"},
    ]

    ordered = validate_block_order(blocks, page_width=1200)

    assert [block["block_content"] for block in ordered] == ["L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"]


def test_validate_block_order_repairs_non_monotonic_order_within_column() -> None:
    from paperforge.worker.ocr import validate_block_order

    blocks = [
        {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [80, 100, 500, 140], "block_content": "L1"},
        {"block_id": 2, "block_label": "text", "block_order": 1, "block_bbox": [80, 300, 500, 340], "block_content": "L3"},
        {"block_id": 3, "block_label": "text", "block_order": 2, "block_bbox": [80, 200, 500, 240], "block_content": "L2"},
        {"block_id": 4, "block_label": "text", "block_order": 3, "block_bbox": [700, 150, 1120, 190], "block_content": "R1"},
    ]

    ordered = validate_block_order(blocks, page_width=1200)

    assert [block["block_content"] for block in ordered] == ["L1", "L2", "L3", "R1"]


def test_validate_block_order_keeps_bbox_sort_when_block_order_missing() -> None:
    from paperforge.worker.ocr import block_sort_key, validate_block_order

    blocks = [
        {"block_id": 1, "block_label": "text", "block_bbox": [700, 300, 1120, 340], "block_content": "R2"},
        {"block_id": 2, "block_label": "text", "block_bbox": [80, 100, 500, 140], "block_content": "L1"},
        {"block_id": 3, "block_label": "text", "block_bbox": [700, 100, 1120, 140], "block_content": "R1"},
        {"block_id": 4, "block_label": "text", "block_bbox": [80, 300, 500, 340], "block_content": "L2"},
    ]

    ordered = validate_block_order(sorted(blocks, key=block_sort_key), page_width=0)

    assert [block["block_content"] for block in ordered] == ["L1", "R1", "L2", "R2"]


def test_validate_block_order_preserves_center_spanning_blocks() -> None:
    from paperforge.worker.ocr import validate_block_order

    blocks = [
        {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [120, 80, 1080, 140], "block_content": "Full-width section heading"},
        {"block_id": 2, "block_label": "text", "block_order": 1, "block_bbox": [80, 180, 500, 240], "block_content": "Left paragraph one"},
        {"block_id": 3, "block_label": "text", "block_order": 2, "block_bbox": [700, 190, 1120, 250], "block_content": "Right paragraph one"},
        {"block_id": 4, "block_label": "text", "block_order": 3, "block_bbox": [80, 280, 500, 340], "block_content": "Left paragraph two"},
        {"block_id": 5, "block_label": "text", "block_order": 4, "block_bbox": [700, 290, 1120, 350], "block_content": "Right paragraph two"},
    ]

    ordered = validate_block_order(blocks, page_width=1200)

    assert [block["block_content"] for block in ordered] == [
        "Full-width section heading",
        "Left paragraph one",
        "Right paragraph one",
        "Left paragraph two",
        "Right paragraph two",
    ]


def test_validate_block_order_retains_blocks_with_invalid_bbox() -> None:
    from paperforge.worker.ocr import validate_block_order

    blocks = [
        {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [80, 100, 500, 140], "block_content": "Left valid"},
        {"block_id": 2, "block_label": "text", "block_order": 1, "block_bbox": [500, 160, 500, 200], "block_content": "Broken bbox"},
        {"block_id": 3, "block_label": "text", "block_order": 2, "block_bbox": [700, 180, 1120, 220], "block_content": "Right valid"},
        {"block_id": 4, "block_label": "text", "block_order": 3, "block_bbox": [80, 260, 500, 300], "block_content": "Left lower"},
    ]

    ordered = validate_block_order(blocks, page_width=1200)

    assert [block["block_content"] for block in ordered] == ["Left valid", "Broken bbox", "Right valid", "Left lower"]


def test_render_page_blocks_reorders_interleaved_two_column_text_by_geometry(tmp_path: Path) -> None:
    from paperforge.worker.ocr import render_page_blocks

    vault = tmp_path / "vault"
    images_dir = vault / "System" / "PaperForge" / "ocr" / "KEY" / "images"
    page_cache_dir = vault / "System" / "PaperForge" / "ocr" / "KEY" / "pages"
    images_dir.mkdir(parents=True)
    page_cache_dir.mkdir(parents=True)

    result = {
        "prunedResult": {
            "width": 1200,
            "height": 1600,
            "parsing_res_list": [
                {"block_id": 1, "block_label": "text", "block_order": 0, "block_bbox": [80, 100, 500, 160], "block_content": "Left intro paragraph with enough body text."},
                {"block_id": 2, "block_label": "text", "block_order": 1, "block_bbox": [700, 110, 1120, 170], "block_content": "Right intro paragraph with enough body text."},
                {"block_id": 3, "block_label": "text", "block_order": 2, "block_bbox": [80, 200, 500, 260], "block_content": "Left methods paragraph with enough body text."},
                {"block_id": 4, "block_label": "text", "block_order": 3, "block_bbox": [700, 210, 1120, 270], "block_content": "Right methods paragraph with enough body text."},
                {"block_id": 5, "block_label": "text", "block_order": 4, "block_bbox": [80, 300, 500, 360], "block_content": "Left results paragraph with enough body text."},
                {"block_id": 6, "block_label": "text", "block_order": 5, "block_bbox": [700, 310, 1120, 370], "block_content": "Right results paragraph with enough body text."},
                {"block_id": 7, "block_label": "text", "block_order": 6, "block_bbox": [80, 400, 500, 460], "block_content": "Left discussion paragraph with enough body text."},
                {"block_id": 8, "block_label": "text", "block_order": 7, "block_bbox": [700, 410, 1120, 470], "block_content": "Right discussion paragraph with enough body text."},
            ],
        },
        "inputImage": "",
    }

    rendered = render_page_blocks(vault, 2, result, images_dir, page_cache_dir, pdf_doc=None)
    body_lines = [line for line in rendered if line and not line.startswith("<!-- page")]

    assert body_lines == [
        "Left intro paragraph with enough body text.",
        "Left methods paragraph with enough body text.",
        "Left results paragraph with enough body text.",
        "Left discussion paragraph with enough body text.",
        "Right intro paragraph with enough body text.",
        "Right methods paragraph with enough body text.",
        "Right results paragraph with enough body text.",
        "Right discussion paragraph with enough body text.",
    ]


def test_render_page_blocks_links_media_for_text_caption(tmp_path: Path) -> None:
    from paperforge.worker.ocr import render_page_blocks

    vault = tmp_path / "vault"
    images_dir = vault / "System" / "PaperForge" / "ocr" / "KEY" / "images"
    page_cache_dir = vault / "System" / "PaperForge" / "ocr" / "KEY" / "pages"
    images_dir.mkdir(parents=True)
    page_cache_dir.mkdir(parents=True)

    page_image = page_cache_dir / "page_009.png"
    Image.new("RGB", (1200, 1600), color="white").save(page_image)

    result = {
        "prunedResult": {
            "width": 1200,
            "height": 1600,
            "parsing_res_list": [
                {
                    "block_id": 1,
                    "block_label": "vision_footnote",
                    "block_bbox": [449, 168, 738, 219],
                    "block_content": "No Electrical Stimulation\nElectrical Stimulation 100 mV/mm",
                },
                {
                    "block_id": 2,
                    "block_label": "chart",
                    "block_bbox": [429, 237, 733, 485],
                    "block_content": "",
                },
                {
                    "block_id": 3,
                    "block_label": "chart",
                    "block_bbox": [772, 238, 1071, 484],
                    "block_content": "",
                },
                {
                    "block_id": 4,
                    "block_label": "chart",
                    "block_bbox": [363, 504, 742, 757],
                    "block_content": "",
                },
                {
                    "block_id": 5,
                    "block_label": "chart",
                    "block_bbox": [766, 503, 1075, 750],
                    "block_content": "",
                },
                {
                    "block_id": 6,
                    "block_label": "chart",
                    "block_bbox": [428, 774, 729, 1016],
                    "block_content": "",
                },
                {
                    "block_id": 7,
                    "block_label": "chart",
                    "block_bbox": [765, 768, 1075, 1013],
                    "block_content": "",
                },
                {
                    "block_id": 8,
                    "block_label": "figure_title",
                    "block_bbox": [374, 1046, 1143, 1077],
                    "block_content": "Days post culture in osteogenic differentiation supplemented medium",
                },
                {
                    "block_id": 9,
                    "block_label": "text",
                    "block_bbox": [373, 1101, 1143, 1258],
                    "block_content": "Figure 4 RT-qPCR results. Temporal changes in messenger RNA (mRNA) of (A) Runx2, (B) Osteopontin and (C) Col1A2.",
                },
            ],
        },
        "inputImage": "",
    }

    with patch("paperforge.worker.ocr.render_pdf_page_cached", return_value=page_image):
        rendered = render_page_blocks(vault, 9, result, images_dir, page_cache_dir, pdf_doc=None)

    assert any(line.startswith("![[") for line in rendered)
    assert any(line.startswith("Figure 4 RT-qPCR results.") for line in rendered)


def test_embedded_figure_text_excludes_body_paragraph_like_text() -> None:
    from paperforge.worker.ocr import is_embedded_figure_text_block

    blocks = [
        {
            "block_id": 1,
            "block_label": "paragraph_title",
            "block_bbox": [80, 530, 269, 554],
            "block_content": "Immunohistochemistry",
        },
        {
            "block_id": 2,
            "block_label": "text",
            "block_bbox": [78, 577, 498, 915],
            "block_content": (
                "To determine which cells express these proteins, we performed immunohistochemical analyses "
                "for Tyk2, S100A9, and ZNF 217 from the same tissues used in 2-DE. Positively stained cells "
                "of Tyk2 and ZNF 217 were located at cytoplasm of epithelial cells. Although the majority of "
                "cases of SCC and adjacent normal tissues showed cytoplasmic S100A9 positivity of epithelial "
                "cells, some cases also showed nuclear S100A9 positivity, as shown in Fig. 3."
            ),
        },
        {
            "block_id": 3,
            "block_label": "image",
            "block_bbox": [272, 964, 610, 1421],
            "block_content": "",
        },
        {
            "block_id": 4,
            "block_label": "image",
            "block_bbox": [620, 964, 933, 1421],
            "block_content": "",
        },
        {
            "block_id": 5,
            "block_label": "figure_title",
            "block_bbox": [78, 1448, 1129, 1511],
            "block_content": (
                "Fig. 3. Immunohistochemical staining in SCC and adjacent normal tissues. Sections from SCC and "
                "nontumorous tissue were immunostained with antibodies against Tyk2 (left), S100A9 (middle), "
                "and ZNF 217 (right)."
            ),
        },
    ]

    assert is_embedded_figure_text_block(blocks[1], blocks, page_width=1200, page_height=1600) is False


def test_embedded_figure_text_keeps_narrow_in_figure_note() -> None:
    from paperforge.worker.ocr import is_embedded_figure_text_block

    blocks = [
        {
            "block_id": 1,
            "block_label": "chart",
            "block_bbox": [320, 260, 620, 1080],
            "block_content": "",
        },
        {
            "block_id": 2,
            "block_label": "chart",
            "block_bbox": [640, 260, 920, 1080],
            "block_content": "",
        },
        {
            "block_id": 3,
            "block_label": "text",
            "block_bbox": [470, 1090, 760, 1160],
            "block_content": "Patient A\nAge 42\nHPV16 positive",
        },
        {
            "block_id": 4,
            "block_label": "figure_title",
            "block_bbox": [300, 1180, 980, 1250],
            "block_content": "Figure 2. Representative pathology records and imaging findings.",
        },
    ]

    assert is_embedded_figure_text_block(blocks[2], blocks, page_width=1200, page_height=1600) is True
