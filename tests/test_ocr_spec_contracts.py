from __future__ import annotations

import pytest


class TestOcrRoleContracts:
    """Architecture contract tests for OCR-v2 role assignment invariants."""

    def test_contract_zone_is_not_role(self) -> None:
        """Being in the body_zone does not make a block body_paragraph by itself."""
        from paperforge.worker.ocr_roles import assign_block_role

        block = {
            "block_label": "text",
            "block_content": "Check for updates",
            "block_bbox": [900, 50, 1100, 72],
        }
        role = assign_block_role(
            block, page_blocks=[block], page_width=1200, page_height=1600,
        )
        assert role.role not in ("section_heading", "subsection_heading"), (
            f"zone-only text must not become heading: {role.role}"
        )

    def test_contract_reference_tail_first(self) -> None:
        """Reference-like text without reference_zone/numbering support must not become reference_item."""
        from paperforge.worker.ocr_roles import assign_block_role

        for ordinal_word in (
            "First,",
            "Fourth,",
            "Sixth,",
            "Additionally,",
            "Historically,",
            "Metabolically,",
        ):
            block = {
                "block_label": "text",
                "block_content": f"{ordinal_word} some body prose that looks like a reference but is not one.",
                "block_bbox": [100, 200, 800, 260],
            }
            role = assign_block_role(
                block, page_blocks=[block], page_width=1200, page_height=1600,
            )
            assert role.role != "reference_item", (
                f"Ordinal body opening '{ordinal_word}' must not become reference_item, got {role.role}"
            )


class TestOcrRenderContracts:
    """Architecture contract tests for OCR-v2 renderer invariants."""

    def test_contract_renderer_is_not_semantic_rescue(self) -> None:
        """render_fulltext_markdown must not promote blocks based on raw text alone."""
        from paperforge.worker.ocr_render import render_fulltext_markdown

        blocks = [
            {
                "block_id": "p1_b1",
                "page": 1,
                "role": "body_paragraph",
                "raw_label": "text",
                "text": "Fig. 1 This looks like a figure caption but has no accepted figure role.",
                "bbox": [100, 100, 800, 160],
                "page_width": 1200,
                "page_height": 1600,
            },
        ]
        markdown = render_fulltext_markdown(
            structured_blocks=blocks,
            resolved_metadata={},
            figure_inventory={"matched_figures": []},
            table_inventory={"tables": []},
            page_count=1,
            document_structure=None,
            reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
        )
        assert "Fig. 1" in markdown, "readable text must not be silently dropped"
        assert "![[assets/figures/" not in markdown, (
            "renderer must not invent figure embedding from raw text"
        )

    def test_contract_object_ownership_is_exclusive(self) -> None:
        """A block consumed by a figure object must not also appear as loose body text."""
        from paperforge.worker.ocr_render import render_fulltext_markdown

        blocks = [
            {
                "block_id": "p1_b1",
                "page": 1,
                "role": "figure_caption",
                "raw_label": "figure_title",
                "text": "Figure 1. A sample figure.",
                "bbox": [100, 100, 800, 160],
                "page_width": 1200,
                "page_height": 1600,
            },
        ]
        reader_payload = {
            "reader_figures": [
                {
                    "reader_figure_id": "figure_001_reader",
                    "reader_status": "EXACT_MATCH",
                    "caption_block_id": "p1_b1",
                    "consumed_caption_block_ids": ["p1_b1"],
                },
            ],
            "consumed_caption_block_ids": ["p1_b1"],
        }
        markdown = render_fulltext_markdown(
            structured_blocks=blocks,
            resolved_metadata={},
            figure_inventory={
                "matched_figures": [
                    {
                        "figure_id": "figure_001",
                        "text": "Figure 1. A sample figure.",
                        "page": 1,
                    },
                ],
            },
            table_inventory={"tables": []},
            page_count=1,
            document_structure=None,
            reader_payload=reader_payload,
        )
        occurrences = markdown.count("Figure 1.")
        assert occurrences == 1, (
            f"Consumed caption must appear exactly once, found {occurrences} occurrences"
        )

    def test_contract_reading_segments_are_authoritative(self) -> None:
        """Conclusion must appear before References in final markdown, regardless of page geometry."""
        from paperforge.worker.ocr_render import render_fulltext_markdown

        blocks = [
            {
                "block_id": "p1_b2",
                "page": 1,
                "role": "reference_heading",
                "raw_label": "paragraph_title",
                "text": "References",
                "bbox": [100, 600, 400, 640],
                "page_width": 1200,
                "page_height": 1600,
            },
            {
                "block_id": "p1_b3",
                "page": 1,
                "role": "reference_item",
                "raw_label": "text",
                "text": "[1] Example reference.",
                "bbox": [100, 660, 800, 700],
                "page_width": 1200,
                "page_height": 1600,
            },
            {
                "block_id": "p1_b1",
                "page": 1,
                "role": "subsection_heading",
                "raw_label": "paragraph_title",
                "text": "Conclusion",
                "bbox": [100, 800, 400, 840],
                "page_width": 1200,
                "page_height": 1600,
            },
        ]
        markdown = render_fulltext_markdown(
            structured_blocks=blocks,
            resolved_metadata={},
            figure_inventory={"matched_figures": []},
            table_inventory={"tables": []},
            page_count=1,
            document_structure=None,
            reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
        )
        conclusion_pos = markdown.find("Conclusion")
        references_pos = markdown.find("References")
        assert conclusion_pos < references_pos, (
            f"Conclusion must appear before References "
            f"(conclusion at {conclusion_pos}, refs at {references_pos})"
        )
