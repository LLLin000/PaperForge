from __future__ import annotations

from pathlib import Path


def test_body_abstract_seed_does_not_render_as_abstract() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {
            "block_id": "h",
            "seed_role": "abstract_heading",
            "page": 1,
            "role": "unassigned",
            "text": "Abstract",
            "render_default": True,
        },
        {
            "block_id": "a",
            "seed_role": "abstract_body",
            "page": 1,
            "role": "unassigned",
            "text": "Real abstract.",
            "render_default": True,
        },
        {
            "block_id": "intro",
            "seed_role": "section_heading",
            "page": 1,
            "role": "unassigned",
            "text": "Introduction",
            "render_default": True,
        },
        {
            "block_id": "bad",
            "seed_role": "abstract_body",
            "page": 1,
            "role": "unassigned",
            "text": "Body mislabeled as abstract.",
            "render_default": True,
        },
    ]
    doc, normalized = normalize_document_structure(blocks)

    # Real abstract renders inside Abstract section
    assert doc.abstract_span["body_block_ids"] == ["a"]

    # Bad block (mislabeled abstract body after Introduction) is held
    bad = next(b for b in normalized if b["block_id"] == "bad")
    assert bad["role"] == "unknown_structural"
    assert bad["role_verification_status"] == "HOLD"
    assert bad["render_default"] is False

    markdown = render_fulltext_markdown(
        structured_blocks=normalized,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        document_structure=doc,
        reader_payload={"reader_figures": []},
    )

    # Abstract content renders
    assert "Real abstract." in markdown
    # Introduction: held because no heading artifact evidence, not rendered
    assert "Introduction" not in markdown
    # Held abstract body (after Introduction) is suppressed from render
    assert "Body mislabeled as abstract." not in markdown


def test_z75_like_headingless_abstract_restores_late_body_order() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"block_id": 1, "page": 2, "seed_role": "paper_title", "role": "unassigned", "text": "Preparation of Ultra-Small Copper Nanoparticles", "render_default": True},
        {"block_id": 8, "page": 2, "seed_role": "abstract_body", "role": "unassigned", "text": "Background: Bacterial invasion, protracted inflammation.", "render_default": True},
        {"block_id": 9, "page": 2, "seed_role": "abstract_body", "role": "unassigned", "text": "Results: The findings showed that a kind of ultra-small.", "render_default": True},
        {"block_id": 10, "page": 2, "seed_role": "keywords", "role": "unassigned", "text": "Keywords: diabetic wounds, hydrogel", "render_default": True},
        {"block_id": 12, "page": 2, "seed_role": "section_heading", "role": "unassigned", "text": "Introduction", "render_default": True},
        {"block_id": 3, "page": 13, "seed_role": "abstract_body", "role": "unassigned", "text": "Endothelial autophagy has been demonstrated to be activated.", "render_default": True},
        {"block_id": 4, "page": 13, "seed_role": "subsection_heading", "role": "unassigned", "text": "Cunps@CMCS-PCA Hydrogel Mainly Depended on PCA Mediated Inhibition", "render_default": True},
        {"block_id": 5, "page": 13, "seed_role": "abstract_body", "role": "unassigned", "text": "As diabetic wounds are typically characterized by chronic inflammation.", "render_default": True},
        {"block_id": 6, "page": 14, "seed_role": "subsection_heading", "role": "unassigned", "text": "Cunps@CMCS-PCA Hydrogel Accelerated Diabetic Wound Healing", "render_default": True},
    ]
    doc, normalized = normalize_document_structure(blocks)

    by_id = {b["block_id"]: b for b in normalized}
    assert by_id[3]["role"] == "body_paragraph"
    assert by_id[5]["role"] == "body_paragraph"
    assert by_id[3]["render_default"] is True
    assert by_id[8]["role"] == "abstract_body"
    assert by_id[9]["role"] == "abstract_body"

    markdown = render_fulltext_markdown(
        structured_blocks=normalized,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=14,
        document_structure=doc,
        reader_payload={"reader_figures": []},
    )

    # Abstract section holds only the true abstract
    abstract_section = markdown.split("## Abstract", 1)[1].split("\n## ", 1)[0]
    assert "Background: Bacterial invasion" in abstract_section
    assert "Endothelial autophagy" not in abstract_section
    assert "As diabetic wounds" not in abstract_section
    # Body order restored: late paragraphs stay under their Results subsections
    pos_end = markdown.find("Endothelial autophagy")
    pos_pca = markdown.find("Cunps@CMCS-PCA Hydrogel Mainly Depended")
    pos_asi = markdown.find("As diabetic wounds")
    pos_acc = markdown.find("Cunps@CMCS-PCA Hydrogel Accelerated")
    assert 0 < pos_end < pos_pca < pos_asi < pos_acc
    # No content lost: each late paragraph renders exactly once
    assert markdown.count("Endothelial autophagy") == 1
    assert markdown.count("As diabetic wounds") == 1


def test_yoo_like_tail_order_through_render_fulltext_markdown() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "block_id": "refs",
            "page": 35,
            "role": "reference_heading",
            "role_verification_status": "ACCEPT",
            "text": "References",
            "render_default": True,
        },
        {
            "block_id": "r1",
            "page": 35,
            "role": "reference_item",
            "role_verification_status": "ACCEPT",
            "text": "[1] Yoo H. Real reference.",
            "render_default": True,
        },
        {"block_id": "bio", "page": 34, "role": "body_paragraph", "text": "Biography", "render_default": True},
        {
            "block_id": "caps",
            "page": 35,
            "role": "section_heading",
            "role_verification_status": "ACCEPT",
            "text": "Table and Figure Captions",
            "render_default": True,
        },
    ]
    ds = DocumentStructure()
    ds.abstract_span = {"heading_block_id": None, "body_block_ids": [], "status": "MISSING"}
    ds.reference_zone = {"heading_block_id": "refs", "item_block_ids": ["r1"], "status": "ACCEPT"}

    markdown = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=35,
        document_structure=ds,
        reader_payload={"reader_figures": []},
    )

    assert "References" in markdown
    assert "[1] Yoo H. Real reference." in markdown


def test_caffard_like_abstract_flow_through_normalize_document_structure() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "q", "seed_role": "section_heading", "text": "Questions/purposes"},
        {"block_id": "a1", "seed_role": "abstract_body", "text": "First abstract sentence."},
        {"block_id": "authors", "seed_role": "authors", "text": "Author One Author Two"},
        {"block_id": "m", "seed_role": "section_heading", "text": "Methods"},
        {"block_id": "a2", "seed_role": "abstract_body", "text": "Second abstract sentence."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "Introduction"},
    ]
    context = {
        "body_start_block_id": "intro",
        "frontmatter_main_zone_ids": {"h", "q", "a1", "m", "a2"},
        "frontmatter_support_zone_ids": {"authors"},
        "publisher_sidebar_zone_ids": set(),
        "correspondence_zone_ids": set(),
        "affiliation_zone_ids": set(),
    }

    span = build_document_abstract_span(blocks, context)

    assert span["body_block_ids"] == ["q", "a1", "m", "a2"]
    assert "authors" in span["excluded_support_block_ids"]


def test_regression_file_does_not_use_legacy_page_renderers() -> None:
    render_source = Path("paperforge", "worker", "ocr_render.py").read_text(encoding="utf-8")

    assert "render_page_blocks" not in render_source
    assert "emit_page_markdown" not in render_source
    assert "ocr_emit" not in render_source
