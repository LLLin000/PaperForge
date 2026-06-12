from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PIL import Image


def test_extract_preserved_ocr_redo_preserves_flag_across_frontmatter_rewrite() -> None:
    """Simulate sync preserving ocr_redo through frontmatter_note()."""
    from paperforge.adapters.obsidian_frontmatter import extract_preserved_ocr_redo
    from paperforge.worker.sync import frontmatter_note

    entry = {"zotero_key": "TEST", "title": "Test", "year": "2025"}

    original = """---
zotero_key: TEST
title: Test
year: 2025
ocr_redo: true
---
"""
    preserved = extract_preserved_ocr_redo(original)
    assert preserved is True

    rewritten = frontmatter_note(entry, existing_text=original)
    assert "ocr_redo: true" in rewritten


def test_extract_preserved_ocr_redo_false_by_default() -> None:
    from paperforge.adapters.obsidian_frontmatter import extract_preserved_ocr_redo

    text = """---
zotero_key: TEST
title: Test
---
"""
    assert extract_preserved_ocr_redo(text) is False


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
        {
            "block_id": 1,
            "block_label": "text",
            "block_order": 0,
            "block_bbox": [80, 100, 500, 140],
            "block_content": "L1",
        },
        {
            "block_id": 2,
            "block_label": "text",
            "block_order": 1,
            "block_bbox": [700, 110, 1120, 150],
            "block_content": "R1",
        },
        {
            "block_id": 3,
            "block_label": "text",
            "block_order": 2,
            "block_bbox": [80, 200, 500, 240],
            "block_content": "L2",
        },
        {
            "block_id": 4,
            "block_label": "text",
            "block_order": 3,
            "block_bbox": [700, 210, 1120, 250],
            "block_content": "R2",
        },
        {
            "block_id": 5,
            "block_label": "text",
            "block_order": 4,
            "block_bbox": [80, 300, 500, 340],
            "block_content": "L3",
        },
        {
            "block_id": 6,
            "block_label": "text",
            "block_order": 5,
            "block_bbox": [700, 310, 1120, 350],
            "block_content": "R3",
        },
        {
            "block_id": 7,
            "block_label": "text",
            "block_order": 6,
            "block_bbox": [80, 400, 500, 440],
            "block_content": "L4",
        },
        {
            "block_id": 8,
            "block_label": "text",
            "block_order": 7,
            "block_bbox": [700, 410, 1120, 450],
            "block_content": "R4",
        },
    ]

    ordered = validate_block_order(blocks, page_width=1200)

    assert [block["block_content"] for block in ordered] == ["L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"]


def test_validate_block_order_repairs_non_monotonic_order_within_column() -> None:
    from paperforge.worker.ocr import validate_block_order

    blocks = [
        {
            "block_id": 1,
            "block_label": "text",
            "block_order": 0,
            "block_bbox": [80, 100, 500, 140],
            "block_content": "L1",
        },
        {
            "block_id": 2,
            "block_label": "text",
            "block_order": 1,
            "block_bbox": [80, 300, 500, 340],
            "block_content": "L3",
        },
        {
            "block_id": 3,
            "block_label": "text",
            "block_order": 2,
            "block_bbox": [80, 200, 500, 240],
            "block_content": "L2",
        },
        {
            "block_id": 4,
            "block_label": "text",
            "block_order": 3,
            "block_bbox": [700, 150, 1120, 190],
            "block_content": "R1",
        },
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
        {
            "block_id": 1,
            "block_label": "text",
            "block_order": 0,
            "block_bbox": [120, 80, 1080, 140],
            "block_content": "Full-width section heading",
        },
        {
            "block_id": 2,
            "block_label": "text",
            "block_order": 1,
            "block_bbox": [80, 180, 500, 240],
            "block_content": "Left paragraph one",
        },
        {
            "block_id": 3,
            "block_label": "text",
            "block_order": 2,
            "block_bbox": [700, 190, 1120, 250],
            "block_content": "Right paragraph one",
        },
        {
            "block_id": 4,
            "block_label": "text",
            "block_order": 3,
            "block_bbox": [80, 280, 500, 340],
            "block_content": "Left paragraph two",
        },
        {
            "block_id": 5,
            "block_label": "text",
            "block_order": 4,
            "block_bbox": [700, 290, 1120, 350],
            "block_content": "Right paragraph two",
        },
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
        {
            "block_id": 1,
            "block_label": "text",
            "block_order": 0,
            "block_bbox": [80, 100, 500, 140],
            "block_content": "Left valid",
        },
        {
            "block_id": 2,
            "block_label": "text",
            "block_order": 1,
            "block_bbox": [500, 160, 500, 200],
            "block_content": "Broken bbox",
        },
        {
            "block_id": 3,
            "block_label": "text",
            "block_order": 2,
            "block_bbox": [700, 180, 1120, 220],
            "block_content": "Right valid",
        },
        {
            "block_id": 4,
            "block_label": "text",
            "block_order": 3,
            "block_bbox": [80, 260, 500, 300],
            "block_content": "Left lower",
        },
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
                {
                    "block_id": 1,
                    "block_label": "text",
                    "block_order": 0,
                    "block_bbox": [80, 100, 500, 160],
                    "block_content": "Left intro paragraph with enough body text.",
                },
                {
                    "block_id": 2,
                    "block_label": "text",
                    "block_order": 1,
                    "block_bbox": [700, 110, 1120, 170],
                    "block_content": "Right intro paragraph with enough body text.",
                },
                {
                    "block_id": 3,
                    "block_label": "text",
                    "block_order": 2,
                    "block_bbox": [80, 200, 500, 260],
                    "block_content": "Left methods paragraph with enough body text.",
                },
                {
                    "block_id": 4,
                    "block_label": "text",
                    "block_order": 3,
                    "block_bbox": [700, 210, 1120, 270],
                    "block_content": "Right methods paragraph with enough body text.",
                },
                {
                    "block_id": 5,
                    "block_label": "text",
                    "block_order": 4,
                    "block_bbox": [80, 300, 500, 360],
                    "block_content": "Left results paragraph with enough body text.",
                },
                {
                    "block_id": 6,
                    "block_label": "text",
                    "block_order": 5,
                    "block_bbox": [700, 310, 1120, 370],
                    "block_content": "Right results paragraph with enough body text.",
                },
                {
                    "block_id": 7,
                    "block_label": "text",
                    "block_order": 6,
                    "block_bbox": [80, 400, 500, 460],
                    "block_content": "Left discussion paragraph with enough body text.",
                },
                {
                    "block_id": 8,
                    "block_label": "text",
                    "block_order": 7,
                    "block_bbox": [700, 410, 1120, 470],
                    "block_content": "Right discussion paragraph with enough body text.",
                },
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


def test_render_page_blocks_keeps_author_year_references_as_reference_items(tmp_path: Path) -> None:
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
                {
                    "block_id": 1,
                    "block_label": "paragraph_title",
                    "block_bbox": [90, 120, 330, 160],
                    "block_content": "References",
                },
                {
                    "block_id": 2,
                    "block_label": "reference_content",
                    "block_bbox": [90, 220, 520, 300],
                    "block_content": "Amin, B., Elahi, M. A., and Porter, E. (2019). A review of dielectric properties.",
                },
                {
                    "block_id": 3,
                    "block_label": "reference_content",
                    "block_bbox": [620, 220, 1100, 300],
                    "block_content": "Barker, A. T., and Lunt, M. J. (1983). The effects of pulsed magnetic fields.",
                },
            ],
        },
        "inputImage": "",
    }

    rendered = render_page_blocks(vault, 22, result, images_dir, page_cache_dir, pdf_doc=None)

    assert "### References" in rendered
    assert any(line.startswith("Amin, B., Elahi") for line in rendered)
    assert any(line.startswith("Barker, A. T.") for line in rendered)


def test_render_page_blocks_does_not_mix_tail_sections_into_references(tmp_path: Path) -> None:
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
                {
                    "block_id": 1,
                    "block_label": "paragraph_title",
                    "block_bbox": [90, 120, 330, 160],
                    "block_content": "References",
                },
                {
                    "block_id": 2,
                    "block_label": "reference_content",
                    "block_bbox": [90, 220, 520, 300],
                    "block_content": "Amin, B., Elahi, M. A., and Porter, E. (2019). A review of dielectric properties.",
                },
                {
                    "block_id": 3,
                    "block_label": "paragraph_title",
                    "block_bbox": [620, 120, 1080, 160],
                    "block_content": "Generative AI statement",
                },
                {
                    "block_id": 4,
                    "block_label": "text",
                    "block_bbox": [620, 220, 1100, 280],
                    "block_content": "The author(s) declare that no Generative AI was used in the creation of this manuscript.",
                },
            ],
        },
        "inputImage": "",
    }

    rendered = render_page_blocks(vault, 22, result, images_dir, page_cache_dir, pdf_doc=None)
    refs_index = rendered.index("### References")
    ai_index = rendered.index("### Generative AI statement")

    assert rendered[refs_index + 1].startswith("Amin, B., Elahi")
    assert rendered[ai_index + 1].startswith("The author(s) declare")


def test_render_page_blocks_orders_references_within_column(tmp_path: Path) -> None:
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
                {
                    "block_id": 1,
                    "block_label": "paragraph_title",
                    "block_bbox": [90, 120, 330, 160],
                    "block_content": "References",
                },
                {
                    "block_id": 2,
                    "block_label": "reference_content",
                    "block_bbox": [620, 200, 1100, 250],
                    "block_content": "Bagnato, G. L. (2016).",
                },
                {
                    "block_id": 3,
                    "block_label": "reference_content",
                    "block_bbox": [90, 200, 520, 250],
                    "block_content": "Amin, B. (2019).",
                },
                {
                    "block_id": 4,
                    "block_label": "reference_content",
                    "block_bbox": [90, 300, 520, 350],
                    "block_content": "Cai, J. (2018).",
                },
                {
                    "block_id": 5,
                    "block_label": "reference_content",
                    "block_bbox": [620, 300, 1100, 350],
                    "block_content": "Bentley, G. (2012).",
                },
            ],
        },
        "inputImage": "",
    }

    rendered = render_page_blocks(vault, 22, result, images_dir, page_cache_dir, pdf_doc=None)
    ref_items = [line for line in rendered if line.startswith(("Amin", "Cai", "Bagnato", "Bentley"))]

    assert ref_items == ["Amin, B. (2019).", "Cai, J. (2018).", "Bagnato, G. L. (2016).", "Bentley, G. (2012)."]


def test_render_page_blocks_keeps_top_figure_before_body_and_keeps_author_et_al_sentence_in_body(
    tmp_path: Path,
) -> None:
    from paperforge.worker.ocr import render_page_blocks

    vault = tmp_path / "vault"
    images_dir = vault / "System" / "PaperForge" / "ocr" / "KEY" / "images"
    page_cache_dir = vault / "System" / "PaperForge" / "ocr" / "KEY" / "pages"
    images_dir.mkdir(parents=True)
    page_cache_dir.mkdir(parents=True)

    page_image = page_cache_dir / "page_008.png"
    Image.new("RGB", (1200, 1600), color="white").save(page_image)

    result = {
        "prunedResult": {
            "width": 1200,
            "height": 1600,
            "parsing_res_list": [
                {
                    "block_id": 1,
                    "block_label": "figure_title",
                    "block_order": 0,
                    "block_bbox": [97, 114, 306, 197],
                    "block_content": "Fig. 3 Schematic representation of mechanical stimulation for tissue engineering constructs",
                },
                {
                    "block_id": 2,
                    "block_label": "image",
                    "block_order": 1,
                    "block_bbox": [374, 117, 1089, 436],
                    "block_content": "",
                },
                {
                    "block_id": 3,
                    "block_label": "paragraph_title",
                    "block_order": 2,
                    "block_bbox": [96, 470, 513, 520],
                    "block_content": "2.5 Electrical stimulation for tissue-engineered articular cartilage",
                },
                {
                    "block_id": 4,
                    "block_label": "text",
                    "block_order": 3,
                    "block_bbox": [95, 543, 583, 918],
                    "block_content": "As hyaline cartilage is an avascular tissue, the synovial fluid is responsible for chondrocyte nutrition and maintenance.",
                },
                {
                    "block_id": 5,
                    "block_label": "text",
                    "block_order": 4,
                    "block_bbox": [95, 920, 583, 1043],
                    "block_content": "Regenerative pathways for cartilage regeneration on iPSCs engineered constructs can be stimulated by endogenous electrical stimulation.",
                },
                {
                    "block_id": 6,
                    "block_label": "text",
                    "block_order": 5,
                    "block_bbox": [95, 1045, 583, 1265],
                    "block_content": "After incorporating ES on stem cells, this stimulus generates ATP oscillations driven by calcium oscillations.",
                },
                {
                    "block_id": 7,
                    "block_label": "paragraph_title",
                    "block_order": 6,
                    "block_bbox": [607, 893, 736, 917],
                    "block_content": "3 Discussion",
                },
                {
                    "block_id": 8,
                    "block_label": "text",
                    "block_order": 7,
                    "block_bbox": [604, 943, 1094, 1341],
                    "block_content": "Bioreactors can be one of the most efficient and reliable methods for testing in vitro articular cartilage-engineered constructs.",
                },
                {
                    "block_id": 9,
                    "block_label": "text",
                    "block_order": 8,
                    "block_bbox": [95, 1268, 583, 1418],
                    "block_content": "Kwon et al. demonstrated that ES also drives ATP oscillations by cAMP modulation, leading to chondrogenic differentiation in the absence of exogenous growth factors.",
                },
            ],
        },
        "inputImage": "",
    }

    with patch("paperforge.worker.ocr.render_pdf_page_cached", return_value=page_image):
        rendered = render_page_blocks(vault, 8, result, images_dir, page_cache_dir, pdf_doc=None)

    body_lines = [line for line in rendered if line and not line.startswith("<!-- page")]

    assert body_lines[0].startswith("Fig. 3 Schematic representation")
    assert body_lines[1].startswith("![[")
    assert body_lines[2] == "### 2.5 Electrical stimulation for tissue-engineered articular cartilage"
    assert body_lines[6].startswith("Kwon et al. demonstrated")
    assert body_lines[7] == "## 3 Discussion"


def test_validate_block_order_preserves_full_width_blocks_between_columns() -> None:
    from paperforge.worker.ocr import validate_block_order

    blocks = [
        {
            "block_id": 1,
            "block_label": "abstract",
            "block_order": 6,
            "block_bbox": [96, 603, 1094, 800],
            "block_content": "BACKGROUND",
        },
        {
            "block_id": 2,
            "block_label": "abstract",
            "block_order": 7,
            "block_bbox": [97, 802, 1094, 851],
            "block_content": "METHODS",
        },
        {
            "block_id": 3,
            "block_label": "abstract",
            "block_order": 8,
            "block_bbox": [96, 899, 1093, 977],
            "block_content": "CONCLUSION",
        },
        {
            "block_id": 4,
            "block_label": "text",
            "block_order": 9,
            "block_bbox": [97, 1000, 872, 1025],
            "block_content": "Keywords",
        },
        {
            "block_id": 5,
            "block_label": "paragraph_title",
            "block_order": 10,
            "block_bbox": [98, 1062, 246, 1086],
            "block_content": "1 Introduction",
        },
        {
            "block_id": 6,
            "block_label": "text",
            "block_order": 11,
            "block_bbox": [96, 1113, 582, 1190],
            "block_content": "Introduction body",
        },
        {
            "block_id": 7,
            "block_label": "text",
            "block_order": 12,
            "block_bbox": [604, 1063, 1094, 1414],
            "block_content": "Right column body",
        },
    ]

    ordered = validate_block_order(blocks, page_width=1191)

    assert [block["block_content"] for block in ordered[:5]] == [
        "BACKGROUND",
        "METHODS",
        "CONCLUSION",
        "Keywords",
        "1 Introduction",
    ]


def test_render_page_blocks_keeps_abstract_heading_before_abstract_body_on_first_page(tmp_path: Path) -> None:
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
                {
                    "block_id": 1,
                    "block_label": "doc_title",
                    "block_order": 0,
                    "block_bbox": [96, 210, 949, 284],
                    "block_content": "Paper Title",
                },
                {
                    "block_id": 2,
                    "block_label": "text",
                    "block_order": 1,
                    "block_bbox": [95, 312, 761, 365],
                    "block_content": "Author One · Author Two",
                },
                {
                    "block_id": 3,
                    "block_label": "text",
                    "block_order": 2,
                    "block_bbox": [96, 485, 880, 528],
                    "block_content": "Received: 10 February 2023",
                },
                {
                    "block_id": 4,
                    "block_label": "paragraph_title",
                    "block_order": 3,
                    "block_bbox": [97, 577, 181, 599],
                    "block_content": "Abstract",
                },
                {
                    "block_id": 5,
                    "block_label": "abstract",
                    "block_order": 4,
                    "block_bbox": [96, 603, 1094, 800],
                    "block_content": "BACKGROUND: Background text.",
                },
                {
                    "block_id": 6,
                    "block_label": "abstract",
                    "block_order": 5,
                    "block_bbox": [97, 802, 1094, 851],
                    "block_content": "METHODS: Methods text.",
                },
                {
                    "block_id": 7,
                    "block_label": "abstract",
                    "block_order": 6,
                    "block_bbox": [96, 899, 1093, 977],
                    "block_content": "CONCLUSION: Conclusion text.",
                },
                {
                    "block_id": 8,
                    "block_label": "text",
                    "block_order": 7,
                    "block_bbox": [97, 1000, 872, 1025],
                    "block_content": "Keywords one two three",
                },
                {
                    "block_id": 9,
                    "block_label": "paragraph_title",
                    "block_order": 8,
                    "block_bbox": [98, 1062, 246, 1086],
                    "block_content": "1 Introduction",
                },
                {
                    "block_id": 10,
                    "block_label": "text",
                    "block_order": 9,
                    "block_bbox": [96, 1113, 582, 1190],
                    "block_content": "Introduction body.",
                },
            ],
        },
        "inputImage": "",
    }

    rendered = render_page_blocks(vault, 1, result, images_dir, page_cache_dir, pdf_doc=None)
    body_lines = [line for line in rendered if line and not line.startswith("<!-- page")]

    abstract_idx = body_lines.index("## Abstract")
    background_idx = body_lines.index("BACKGROUND: Background text.")
    methods_idx = body_lines.index("METHODS: Methods text.")
    conclusion_idx = body_lines.index("CONCLUSION: Conclusion text.")
    keywords_idx = body_lines.index("Keywords one two three")
    intro_idx = body_lines.index("## 1 Introduction")

    assert abstract_idx < background_idx < methods_idx < conclusion_idx < keywords_idx < intro_idx


def test_media_clusters_merge_side_by_side_panels_with_small_gap() -> None:
    from paperforge.worker.ocr import media_clusters

    blocks = [
        {"block_id": 1, "block_label": "image", "block_bbox": [366, 165, 631, 766], "block_content": ""},
        {"block_id": 2, "block_label": "image", "block_bbox": [675, 118, 1091, 738], "block_content": ""},
    ]

    block_to_cluster, clusters = media_clusters(blocks)

    assert len(clusters) == 1
    assert block_to_cluster[1] == block_to_cluster[2]


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


# --- Structured renderer regression tests ---


def test_structured_renderer_abstract_before_introduction() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "role": "section_heading",
            "text": "1 Introduction",
            "render_default": True,
            "page": 1,
        },
        {
            "role": "abstract_heading",
            "text": "",
            "render_default": True,
            "page": 1,
        },
        {
            "role": "abstract_body",
            "text": "This is the abstract body text.",
            "render_default": True,
            "page": 1,
        },
        {
            "role": "body_paragraph",
            "text": "Some body paragraph after the introduction heading.",
            "render_default": True,
            "page": 1,
        },
    ]

    output = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    abstract_idx = output.index("## Abstract")
    abstract_text_idx = output.index("This is the abstract body text.")
    intro_idx = output.index("1 Introduction")

    assert abstract_idx < abstract_text_idx < intro_idx


def test_structured_renderer_figure_and_table_links_rendered() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "role": "figure_caption",
            "text": "Figure 1. A test figure caption.",
            "render_default": True,
            "page": 1,
        },
        {
            "role": "table_caption",
            "text": "Table 1. A test table caption.",
            "render_default": True,
            "page": 1,
        },
        {
            "role": "body_paragraph",
            "text": "Body text between figures and tables.",
            "render_default": True,
            "page": 1,
        },
    ]

    figure_inventory = {
        "matched_figures": [
            {"figure_id": "fig_001"},
        ]
    }
    table_inventory = {
        "tables": [
            {"table_id": "tbl_001", "has_asset": True},
        ]
    }

    output = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory=figure_inventory,
        table_inventory=table_inventory,
    )

    assert "![[render/figures/fig_001.md]]" in output
    assert "![[render/tables/tbl_001.md]]" in output


def test_structured_renderer_respects_render_default_false() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "role": "body_paragraph",
            "text": "VISIBLE_BODY",
            "render_default": True,
            "page": 1,
        },
        {
            "role": "body_paragraph",
            "text": "HIDDEN_BODY",
            "render_default": False,
            "page": 1,
        },
        {
            "role": "section_heading",
            "text": "Hidden Heading",
            "render_default": False,
            "page": 2,
        },
        {
            "role": "body_paragraph",
            "text": "ALSO_VISIBLE",
            "render_default": True,
            "page": 2,
        },
    ]

    output = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "VISIBLE_BODY" in output
    assert "ALSO_VISIBLE" in output
    assert "HIDDEN_BODY" not in output
    assert "Hidden Heading" not in output


def test_stabilize_renderer_output_starts_with_title() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    md = render_fulltext_markdown(
        structured_blocks=[
            {
                "paper_id": "KEY001",
                "page": 1,
                "block_id": "b1",
                "role": "body_paragraph",
                "text": "Body.",
                "render_default": True,
            },
        ],
        resolved_metadata={"title": {"value": "The Paper Title"}},
        figure_inventory={},
        table_inventory={},
    )

    assert md.startswith("# The Paper Title")


def test_structured_renderer_no_duplicate_authors() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "authors",
            "text": "Alice Smith, Bob Jones",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "abstract_heading",
            "text": "Abstract",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b3",
            "role": "abstract_body",
            "text": "Abstract body text.",
            "render_default": True,
        },
    ]
    resolved_metadata = {
        "title": {"value": "Test Paper"},
        "authors": {"value": ["Alice Smith", "Bob Jones"]},
        "journal": {"value": "Test Journal"},
        "year": {"value": 2025},
        "doi": {"value": "10.1000/xyz"},
    }

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata=resolved_metadata,
        figure_inventory={},
        table_inventory={},
    )

    assert md.count("Alice Smith") == 1
    assert md.count("Bob Jones") == 1


def test_structured_renderer_no_inline_table_html() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "The results are shown below:\n<table><tr><td>Tabular data</td></tr></table>",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Body text after table.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "<table>" not in md


def test_structured_renderer_backmatter_sections() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "b1",
            "role": "backmatter_heading",
            "text": "Author contributions",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "b2",
            "role": "backmatter_body",
            "text": "AS and BJ designed the study. CJ collected the data.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Funding",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "This work was supported by NIH grant R01-XX.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "Author contributions" in md
    assert "AS and BJ designed the study" in md
    assert "Funding" in md


def test_structured_renderer_references_as_heading() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b2",
            "role": "reference_item",
            "text": "Smith J, Jones B. (2024) A study on something. Journal of Examples.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "## References" in md


def test_structured_renderer_heading_body_attachment() -> None:
    """Headings with interleaved bodies attach correctly, not cross-wired."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b1",
            "role": "backmatter_heading",
            "text": "Generative AI statement",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b2",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Publisher's note",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "The authors declare no AI-generated content.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b5",
            "role": "backmatter_body",
            "text": "Springer Nature remains neutral.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b6",
            "role": "reference_item",
            "text": "Smith J. (2024) A study.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b7",
            "role": "reference_item",
            "text": "Jones B. (2023) Another study.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "Generative AI statement" in md
    assert "## References" in md
    assert "Publisher's note" in md

    gen_ai_idx = md.index("Generative AI statement")
    refs_idx = md.index("## References")
    pub_idx = md.index("Publisher's note")
    decl_idx = md.index("The authors declare no AI-generated content.")
    springer_idx = md.index("Springer Nature remains neutral.")
    smith_idx = md.index("Smith J. (2024) A study.")
    jones_idx = md.index("Jones B. (2023) Another study.")

    assert gen_ai_idx < decl_idx, "Generative AI body should appear after its heading"
    assert decl_idx < pub_idx, "Generative AI body should appear before Publisher's note"
    assert pub_idx < springer_idx, "Publisher's note body should appear after its heading"
    assert refs_idx > springer_idx, "References should appear after all backmatter sections"
    assert smith_idx > refs_idx and jones_idx > refs_idx, "Reference items should appear under References"


def test_structured_renderer_mixed_column_ordering() -> None:
    """Two-column tail page blocks resolve to correct heading-body attachment."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b2",
            "role": "backmatter_heading",
            "text": "Generative AI statement",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Publisher's note",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "reference_item",
            "text": "Smith J. (2024) A study.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b5",
            "role": "reference_item",
            "text": "Jones B. (2023) Another study.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b6",
            "role": "backmatter_body",
            "text": "The authors declare no AI-generated content.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b7",
            "role": "backmatter_body",
            "text": "Springer Nature remains neutral.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b8",
            "role": "backmatter_heading",
            "text": "Supplementary material",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b9",
            "role": "backmatter_body",
            "text": "Supplementary data are available online.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    gen_ai_idx = md.index("Generative AI statement")
    refs_idx = md.index("## References")
    pub_idx = md.index("Publisher's note")
    supp_idx = md.index("Supplementary material")
    decl_idx = md.index("The authors declare no AI-generated content.")
    springer_idx = md.index("Springer Nature remains neutral.")
    smith_idx = md.index("Smith J. (2024) A study.")

    assert gen_ai_idx < decl_idx, "Generative AI body after its heading"
    assert decl_idx < pub_idx, "Generative AI body before Publisher's note"
    assert pub_idx < springer_idx, "Publisher's note body after its heading"
    assert springer_idx < supp_idx, "Supplementary material after Publisher's note"
    assert refs_idx > supp_idx, "References should appear after all backmatter sections"
    assert smith_idx > refs_idx, "Reference items should appear under References"
    assert md.index("Supplementary data are available online.") > supp_idx, (
        "Supplementary body under Supplementary heading"
    )


def test_render_skips_segment_tail_reorder_when_tail_confidence_is_low() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "First tail block",
            "page": 3,
            "bbox": [700, 100, 1100, 150],
        },
        {
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Second tail block",
            "page": 3,
            "bbox": [100, 100, 500, 150],
        },
    ]
    doc = DocumentStructure(spread_start=3, spread_end=3)
    doc.tail_boundary_score = {"score": 0.2}
    doc.tail_reading_order = [
        {"page": 3, "column_index": 0, "y_top": 100, "y_bottom": 150, "block_indices": [1]},
        {"page": 3, "column_index": 1, "y_top": 100, "y_bottom": 150, "block_indices": [0]},
    ]

    markdown = render_fulltext_markdown(
        structured_blocks=blocks, resolved_metadata={}, figure_inventory={}, table_inventory={}, document_structure=doc
    )

    assert markdown.index("First tail block") < markdown.index("Second tail block")


def test_tail_zone_noise_band_guard() -> None:
    """Mixed tail page: backmatter body in left column below ref items gets stolen.

    Block order simulates a real OCR scan where a backmatter_body block
    lands in the left column (from a left-column backmatter heading like
    "Author contributions"), interleaved AFTER reference_items in column-sorted
    order.  The FIFO heading_queue has no heading to match it, so ref_section
    absorbs it incorrectly.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
            "block_bbox": [80, 100, 520, 140],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b2",
            "role": "reference_item",
            "text": "Smith J. (2024) A study on electric fields.",
            "render_default": True,
            "block_bbox": [80, 180, 520, 220],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b3",
            "role": "reference_item",
            "text": "Jones B. (2023) Another study on galvanotaxis.",
            "render_default": True,
            "block_bbox": [80, 260, 520, 300],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "AS and BJ designed the study. CJ collected the data.",
            "render_default": True,
            "block_bbox": [80, 340, 520, 380],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b5",
            "role": "backmatter_heading",
            "text": "Author contributions",
            "render_default": True,
            "block_bbox": [620, 50, 1100, 90],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b6",
            "role": "backmatter_heading",
            "text": "Generative AI statement",
            "render_default": True,
            "block_bbox": [620, 400, 1100, 440],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b7",
            "role": "backmatter_body",
            "text": "The authors declare no AI-generated content.",
            "render_default": True,
            "block_bbox": [620, 480, 1100, 520],
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "Author contributions" in md
    assert "## References" in md
    assert "Generative AI statement" in md

    gen_ai_idx = md.index("Generative AI statement")
    refs_idx = md.index("## References")
    decl_idx = md.index("The authors declare no AI-generated content.")
    contributions_idx = md.index("AS and BJ designed the study")

    assert contributions_idx < refs_idx, (
        "Author contributions body should appear BEFORE References, not absorbed into ref_section"
    )
    assert gen_ai_idx < decl_idx < refs_idx, "Gen AI section (heading + body) before References, body after its heading"


def test_tail_zone_supplementary_material_not_noise() -> None:
    """Supplementary material body in usable middle band is not treated as noise."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b1",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
            "block_bbox": [80, 450, 520, 490],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b2",
            "role": "reference_item",
            "text": "Smith J. (2024) A study.",
            "render_default": True,
            "block_bbox": [80, 520, 520, 560],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Supplementary material",
            "render_default": True,
            "block_bbox": [620, 120, 1100, 160],
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "Supplementary material body in the middle band of the page.",
            "render_default": True,
            "block_bbox": [620, 300, 1100, 350],
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "Supplementary material" in md
    assert "Supplementary material body in the middle band" in md


def test_tail_candidate_overreach_does_not_absorb_late_body() -> None:
    """Late body paragraphs are NOT absorbed into backmatter sections.

    The FIFO fallback in _reorder_tail_run_fifo treats body_paragraph as
    attachable to the heading_queue, causing late body text to be pulled
    into the backmatter section instead of appearing before it.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "In conclusion, this study demonstrates that the proposed approach achieves significant improvement across all evaluated metrics, outperforming existing methods in both accuracy and efficiency.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b2",
            "role": "body_paragraph",
            "text": "Future work should investigate the applicability of this framework to larger patient cohorts and broader clinical contexts.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b3",
            "role": "backmatter_heading",
            "text": "Funding",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b4",
            "role": "backmatter_body",
            "text": "This work was supported by NIH grant R01-XX and NSF grant DMR-1234.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    body_idx = md.index("In conclusion, this study demonstrates")
    funding_idx = md.index("Funding")

    assert body_idx < funding_idx, (
        "Late body paragraphs should appear before backmatter sections, not absorbed into them"
    )


def test_cross_page_funding_continuation_preserves_order() -> None:
    """Funding body continuation on next page stays before References.

    Cross-page continuation of a backmatter body (tail_candidate_body on
    a subsequent page) should be placed after its heading and before any
    References section.  Current FIFO fallback absorbs it into the
    reference zone when reference_heading precedes it.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b1",
            "role": "backmatter_heading",
            "text": "Funding",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 5,
            "block_id": "b2",
            "role": "backmatter_body",
            "text": "This work was supported by NIH grant R01-XX. Additional funding was provided by NSF grant DMR-1234.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "b3",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "b4",
            "role": "tail_candidate_body",
            "text": "The funders had no role in study design, data collection, analysis, decision to publish, or preparation of the manuscript.",
            "render_default": True,
        },
        {
            "paper_id": "KEY001",
            "page": 6,
            "block_id": "b5",
            "role": "reference_item",
            "text": "Smith J, Jones B. (2024) A study on electric fields. Journal of Bioelectricity.",
            "render_default": True,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    funding_idx = md.index("Funding")
    continuation_idx = md.index("The funders had no role")
    refs_idx = md.index("## References")

    assert funding_idx < continuation_idx, "Funding continuation should appear after its heading"
    assert continuation_idx < refs_idx, (
        "Funding continuation should appear before References, not absorbed into the reference section"
    )


def test_mixed_tail_page_keeps_late_body_out_of_funding_and_attaches_real_funding() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 21,
            "block_id": "b1",
            "role": "body_paragraph",
            "text": "Late conclusion paragraph that should stay in the main body before any tail sections.",
            "render_default": True,
            "block_bbox": [80, 240, 520, 360],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 21,
            "block_id": "b2",
            "role": "backmatter_heading",
            "text": "Funding",
            "render_default": True,
            "block_bbox": [650, 1200, 900, 1240],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 21,
            "block_id": "b3",
            "role": "body_paragraph",
            "text": "This work was supported by Grant A and Grant B.",
            "render_default": True,
            "block_bbox": [650, 1280, 1120, 1500],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b4",
            "role": "body_paragraph",
            "text": "Additional funding continuation text from the next page.",
            "render_default": True,
            "block_bbox": [80, 160, 520, 320],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b5",
            "role": "backmatter_heading",
            "text": "Acknowledgments",
            "render_default": True,
            "block_bbox": [80, 420, 420, 460],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b6",
            "role": "backmatter_body",
            "text": "We thank our collaborators.",
            "render_default": True,
            "block_bbox": [80, 500, 520, 620],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b7",
            "role": "reference_heading",
            "text": "References",
            "render_default": True,
            "block_bbox": [80, 700, 320, 740],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 22,
            "block_id": "b8",
            "role": "reference_item",
            "text": "Smith J. (2024) Tail ordering paper.",
            "render_default": True,
            "block_bbox": [80, 780, 520, 840],
            "page_width": 1200,
            "page_height": 1700,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=22,
    )

    late_body_idx = md.index("Late conclusion paragraph that should stay")
    funding_idx = md.index("Funding")
    funding_body_idx = md.index("This work was supported by Grant A")
    funding_cont_idx = md.index("Additional funding continuation text")
    ack_idx = md.index("Acknowledgments")
    refs_idx = md.index("## References")

    assert late_body_idx < funding_idx, "Late body text must remain before Funding"
    assert funding_idx < funding_body_idx < funding_cont_idx, "Funding body and continuation must stay under Funding"
    assert funding_cont_idx < ack_idx < refs_idx, "Funding continuation must complete before later tail sections"


def test_backmatter_boundary_normalizes_child_sections_before_references() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "paper_id": "KEY001",
            "page": 10,
            "block_id": "b1",
            "role": "backmatter_boundary_heading",
            "text": "ADDITIONAL INFORMATION AND DECLARATIONS",
            "render_default": True,
            "block_bbox": [360, 1200, 1080, 1240],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 10,
            "block_id": "b2",
            "role": "backmatter_heading",
            "text": "Funding",
            "render_default": True,
            "block_bbox": [360, 1280, 520, 1320],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 10,
            "block_id": "b3",
            "role": "backmatter_body",
            "text": "The work was supported by Grant A.",
            "render_default": True,
            "block_bbox": [360, 1330, 1120, 1450],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b4",
            "role": "subsection_heading",
            "text": "Grant Disclosures",
            "render_default": True,
            "block_bbox": [360, 160, 620, 200],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b5",
            "role": "body_paragraph",
            "text": "Grant A was disclosed by the authors.",
            "render_default": True,
            "block_bbox": [360, 210, 920, 290],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b6",
            "role": "backmatter_heading",
            "text": "Author Contributions",
            "render_default": True,
            "block_bbox": [360, 320, 720, 360],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b7",
            "role": "frontmatter_noise",
            "text": "Author A conceived the study and wrote the manuscript.",
            "render_default": True,
            "block_bbox": [360, 370, 1120, 430],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b8",
            "role": "backmatter_heading",
            "text": "Data Availability",
            "render_default": True,
            "block_bbox": [360, 460, 680, 500],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b9",
            "role": "body_paragraph",
            "text": "The raw data has been supplied as Supplementary Files.",
            "render_default": True,
            "block_bbox": [360, 510, 980, 560],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b10",
            "role": "backmatter_boundary_heading",
            "text": "Supplemental Information",
            "render_default": True,
            "block_bbox": [360, 590, 760, 630],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b11",
            "role": "body_paragraph",
            "text": "Supplemental information for this article can be found online.",
            "render_default": True,
            "block_bbox": [360, 640, 1120, 700],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b12",
            "role": "reference_heading",
            "text": "REFERENCES",
            "render_default": True,
            "block_bbox": [360, 760, 620, 800],
            "page_width": 1200,
            "page_height": 1700,
        },
        {
            "paper_id": "KEY001",
            "page": 11,
            "block_id": "b13",
            "role": "reference_item",
            "text": "Smith J. Example reference.",
            "render_default": True,
            "block_bbox": [360, 820, 1000, 880],
            "page_width": 1200,
            "page_height": 1700,
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=11,
    )

    funding_idx = md.index("Funding")
    grant_idx = md.index("Grant Disclosures")
    author_idx = md.index("Author Contributions")
    data_idx = md.index("Data Availability")
    supp_idx = md.index("Supplemental Information")
    refs_idx = md.index("## REFERENCES")
    grant_body_idx = md.index("Grant A was disclosed by the authors.")
    author_body_idx = md.index("Author A conceived the study")
    data_body_idx = md.index("The raw data has been supplied")
    supp_body_idx = md.index("Supplemental information for this article")

    assert funding_idx < grant_idx < author_idx < data_idx < supp_idx < refs_idx
    assert grant_idx < grant_body_idx < author_idx
    assert author_idx < author_body_idx < data_idx
    assert data_idx < data_body_idx < supp_idx
    assert supp_idx < supp_body_idx < refs_idx


def test_unresolved_cluster_appears_in_fulltext() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    md = render_fulltext_markdown(
        structured_blocks=[
            {
                "role": "body_paragraph",
                "text": "Body text on page 1.",
                "render_default": True,
                "page": 1,
            },
        ],
        resolved_metadata={},
        figure_inventory={
            "unresolved_clusters": [
                {
                    "cluster_id": "cluster_001",
                    "page": 1,
                    "bbox": [0, 0, 100, 100],
                    "media_block_ids": [1, 2],
                    "status": "unresolved_multi_panel",
                    "confidence": 0.45,
                }
            ]
        },
        table_inventory={},
    )

    assert "![[render/figures/cluster_001.md]]" in md


def test_unresolved_cluster_link_with_unresolved_cluster_id() -> None:
    """Unresolved cluster with valid cluster_id produces correct wikilink."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    md = render_fulltext_markdown(
        structured_blocks=[
            {
                "role": "body_paragraph",
                "text": "Body text on page 1.",
                "render_default": True,
                "page": 1,
            },
        ],
        resolved_metadata={},
        figure_inventory={
            "unresolved_clusters": [
                {
                    "cluster_id": "unresolved_cluster_001",
                    "page": 1,
                    "cluster_bbox": [363, 237, 1075, 1016],
                    "media_block_ids": [1, 2],
                }
            ]
        },
        table_inventory={},
    )

    assert "![[render/figures/unresolved_cluster_001.md]]" in md
    assert "![[render/figures/.md]]" not in md


def test_unresolved_cluster_link_with_missing_id_is_defensive() -> None:
    """When cluster_id is omitted, no empty wikilink is emitted."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    md = render_fulltext_markdown(
        structured_blocks=[
            {
                "role": "body_paragraph",
                "text": "Body text on page 1.",
                "render_default": True,
                "page": 1,
            },
        ],
        resolved_metadata={},
        figure_inventory={
            "unresolved_clusters": [
                {
                    "page": 1,
                    "cluster_bbox": [363, 237, 1075, 1016],
                    "media_block_ids": [1, 2],
                }
            ]
        },
        table_inventory={},
    )

    assert "![[render/figures/.md]]" not in md
    assert "![[render/figures/unresolved_cluster_001.md]]" in md


def test_table_caption_in_display_zone_not_rendered_as_heading() -> None:
    """Table captions in display_zone or with table_caption_like family should not
    be rendered as ### headings."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "role": "table_caption",
            "text": "Table 1. Patient demographics.",
            "render_default": True,
            "page": 2,
            "zone": "display_zone",
            "style_family": "table_caption_like",
        },
        {
            "role": "body_paragraph",
            "text": "Body text after table.",
            "render_default": True,
            "page": 2,
        },
    ]

    output = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={"tables": [{"table_id": "tbl_001", "has_asset": True}]},
    )

    assert "### Table 1" not in output
    assert "> **Table 1. Patient demographics.**" in output


def test_frontmatter_side_zone_not_rendered_as_heading() -> None:
    """Blocks in frontmatter_side_zone should not appear in rendered output."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "role": "frontmatter_noise",
            "text": "Published online: January 1, 2025",
            "render_default": True,
            "page": 1,
            "zone": "frontmatter_side_zone",
        },
        {
            "role": "body_paragraph",
            "text": "Body text.",
            "render_default": True,
            "page": 1,
        },
    ]

    output = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert "Published online" not in output
    assert "Body text." in output


def test_render_fulltext_skips_consumed_caption_block() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "block_id": 21,
            "role": "figure_caption",
            "text": "FIGURE 2 | Treadmill exercise protocols...",
            "page": 1,
            "bbox": [0, 0, 100, 20],
        },
        {
            "block_id": 22,
            "role": "body_paragraph",
            "text": "The treadmill protocol was well tolerated by all subjects.",
            "page": 1,
            "bbox": [0, 30, 500, 50],
        },
    ]

    reader_payload = {
        "reader_figures": [
            {
                "reader_figure_id": "figure_002_reader",
                "reader_status": "LEGEND_ONLY",
                "strict_status": "unmatched",
                "figure_number": 2,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "caption_block_id": 21,
                "visual_groups": [],
                "consumed_caption_block_ids": [21],
                "consumed_asset_block_ids": [],
                "debug_refs": {},
            }
        ],
        "consumed_caption_block_ids": [21],
        "consumed_asset_block_ids": [],
    }

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        reader_payload=reader_payload,
    )

    assert "FIGURE 2 | Treadmill exercise protocols..." in markdown
    assert "<!-- page 1 -->" in markdown


def test_render_fulltext_hides_debug_artifacts() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"block_id": 1, "role": "body_paragraph", "text": "Body text.", "page": 1, "bbox": [0, 0, 100, 20]},
    ]

    reader_payload = {
        "reader_figures": [
            {
                "reader_figure_id": "figure_003_reader",
                "reader_status": "LEGEND_ONLY",
                "strict_status": "unmatched",
                "figure_number": 3,
                "caption_text": "FIGURE 3 | Histological evaluation...",
                "caption_block_id": 30,
                "visual_groups": [],
                "consumed_caption_block_ids": [30],
                "consumed_asset_block_ids": [],
                "debug_refs": {"strict_name": "unmatched_legend_003"},
            }
        ],
        "consumed_caption_block_ids": [30],
        "consumed_asset_block_ids": [],
    }

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        reader_payload=reader_payload,
    )

    assert "unmatched_legend_" not in markdown
    assert "unresolved_cluster_" not in markdown
    assert "orphan_" not in markdown


def test_render_fulltext_skips_consumed_caption_block_even_when_role_is_body_paragraph() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "block_id": 21,
            "role": "body_paragraph",
            "text": "FIGURE 2 | Treadmill exercise protocols...",
            "page": 1,
            "bbox": [0, 0, 100, 20],
        },
        {
            "block_id": 22,
            "role": "body_paragraph",
            "text": "The treadmill protocol was well tolerated.",
            "page": 1,
            "bbox": [0, 30, 500, 50],
        },
    ]
    reader_payload = {
        "reader_figures": [
            {
                "reader_figure_id": "figure_002_reader",
                "reader_status": "LEGEND_ONLY",
                "strict_status": "unmatched",
                "figure_number": 2,
                "caption_text": "FIGURE 2 | Treadmill exercise protocols...",
                "caption_block_id": 21,
                "visual_groups": [],
                "consumed_caption_block_ids": [21],
                "consumed_asset_block_ids": [],
                "debug_refs": {},
            }
        ],
        "consumed_caption_block_ids": [21],
        "consumed_asset_block_ids": [],
    }

    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory={"tables": []},
        page_count=1,
        reader_payload=reader_payload,
    )

    assert markdown.count("FIGURE 2 | Treadmill exercise protocols...") == 1


def test_render_fulltext_prefers_reader_figures_over_legacy_matched_figures() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [{"block_id": 22, "role": "body_paragraph", "text": "Results body.", "page": 1, "bbox": [0, 30, 500, 50]}]
    markdown = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={
            "matched_figures": [{"figure_id": "figure_002", "page": 1, "text": "Figure 2 legacy caption"}]
        },
        table_inventory={"tables": []},
        page_count=1,
        reader_payload={
            "reader_figures": [
                {
                    "reader_figure_id": "figure_002_reader",
                    "reader_status": "LEGEND_ONLY",
                    "strict_status": "unmatched",
                    "strict_source": "unmatched_legends",
                    "figure_number": 2,
                    "caption_text": "FIGURE 2 | Reader caption",
                    "caption_block_id": 21,
                    "visual_groups": [],
                    "consumed_caption_block_ids": [21],
                    "consumed_asset_block_ids": [],
                    "debug_refs": {},
                }
            ],
            "consumed_caption_block_ids": [21],
            "consumed_asset_block_ids": [],
        },
    )

    assert "![[render/figures/figure_002.md]]" not in markdown
    assert "> **Figure 2**" in markdown


def test_render_fulltext_uses_accepted_abstract_span_only() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    doc = DocumentStructure()
    doc.abstract_span = {"heading_block_id": "h", "body_block_ids": ["a"], "status": "ACCEPT"}

    structured_blocks = [
        {
            "block_id": "h",
            "page": 1,
            "role": "abstract_heading",
            "role_verification_status": "ACCEPT",
            "text": "Abstract",
            "render_default": True,
        },
        {
            "block_id": "a",
            "page": 1,
            "role": "abstract_body",
            "role_verification_status": "ACCEPT",
            "text": "Real abstract.",
            "render_default": True,
        },
        {
            "block_id": "bad",
            "page": 1,
            "role": "abstract_body",
            "role_verification_status": "HOLD",
            "text": "Mislabeled body.",
            "render_default": True,
        },
        {
            "block_id": "intro",
            "page": 1,
            "role": "section_heading",
            "role_verification_status": "ACCEPT",
            "text": "Introduction",
            "render_default": True,
        },
    ]

    markdown = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        document_structure=doc,
        reader_payload={"reader_figures": []},
    )

    assert "Real abstract." in markdown
    assert "Mislabeled body." not in markdown


def test_render_fulltext_renders_all_reader_visible_statuses() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    statuses = ["EXACT_MATCH", "SEQUENCE_MATCH", "GROUPED_APPROXIMATE", "LEGEND_ONLY", "ASSET_GROUP_ONLY", "HOLD"]
    reader_figures = [
        {
            "reader_figure_id": f"fig_reader_{i}",
            "figure_number": i,
            "block_id": f"fig_{i}",
            "page": 1,
            "page_coords": {"x": 100, "y": 100 + i * 100, "width": 400, "height": 300},
            "reader_status": status,
            "consumed_caption_block_ids": [],
        }
        for i, status in enumerate(statuses)
    ]

    structured_blocks = [
        {"block_id": "a", "page": 1, "role": "body_paragraph", "text": "Some body text.", "render_default": True},
    ]

    markdown = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        reader_payload={"reader_figures": reader_figures},
    )

    for status in statuses:
        assert status in markdown
