from __future__ import annotations


def test_heading_role_is_not_figure_text() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "5.1 Bone",
        "block_bbox": [606, 732, 709, 759],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1191, page_height=1684)

    assert role.role in {"section_heading", "subsection_heading"}


def test_figure_caption_role_beats_body_paragraph() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "Figure 4 RT-qPCR results. Temporal changes in messenger RNA...",
        "block_bbox": [373, 1101, 1143, 1258],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role == "figure_caption"


def test_paragraph_title_is_heading_prior() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "paragraph_title",
        "block_content": "5 In vitro PEMF studies",
        "block_bbox": [94, 1328, 387, 1356],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1191, page_height=1684)

    assert role.role in {"section_heading", "subsection_heading"}
    assert role.confidence >= 0.7


def test_figure_title_is_caption_prior() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "figure_title",
        "block_content": "Figure 2. Representative pathology records.",
        "block_bbox": [300, 1180, 980, 1250],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role == "figure_caption"
    assert role.confidence >= 0.8


def test_unknown_structural_for_unrecognized() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {
        "block_label": "text",
        "block_content": "xyz",
        "block_bbox": [100, 100, 200, 120],
    }

    role = assign_block_role(block, page_blocks=[], page_width=1200, page_height=1600)

    assert role.role in {"body_paragraph", "unknown_structural"}
    assert role.confidence < 0.8
