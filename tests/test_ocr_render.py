from __future__ import annotations


def test_render_fulltext_markdown_preserves_role_heading_prefixes() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 1,
            "role": "subsection_heading",
            "text": "Methods",
            "span_metadata": {"size": 12},
            "span_signature": {"bold": True},
            "block_id": "p1_b1",
        },
        {
            "page": 1,
            "role": "body_paragraph",
            "text": "Body text.",
            "block_id": "p1_b2",
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=1,
        document_structure=None,
        reader_payload={},
    )

    # With font-size-based level, a single 12pt bold subsection_heading gets ##
    assert "## Methods" in md


def test_render_fulltext_markdown_suppresses_cross_page_caption_on_legend_page() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 12,
            "role": "body_paragraph",
            "text": "Page 12 body.",
            "block_id": "p12_b1",
        },
        {
            "page": 13,
            "role": "figure_caption",
            "text": "Figure 4. Cross-page caption.",
            "block_id": 6,
        },
        {
            "page": 13,
            "role": "body_paragraph",
            "text": "Page 13 body.",
            "block_id": "p13_b1",
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=13,
        document_structure=None,
        reader_payload={
            "reader_figures": [
                {
                    "reader_figure_id": "figure_004_reader",
                    "consumed_caption_block_ids": [{"page": 13, "block_id": 6}],
                    "consumed_asset_block_ids": [{"page": 12, "block_id": 101}],
                    "caption_text": "Figure 4. Cross-page caption.",
                }
            ],
            "consumed_caption_block_ids": [{"page": 13, "block_id": 6}],
        },
    )

    assert md.count("Figure 4. Cross-page caption.") == 1
    assert "Page 13 body." in md


def test_render_fulltext_markdown_does_not_double_emit_cross_page_figure_embed() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 50,
            "role": "body_paragraph",
            "text": "Page 50 body.",
            "block_id": "p50_b1",
        },
        {
            "page": 51,
            "role": "figure_caption",
            "text": "Figure 24. Cross-page caption.",
            "block_id": 3,
        },
        {
            "page": 51,
            "role": "body_paragraph",
            "text": "Page 51 body.",
            "block_id": "p51_b1",
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={
            "matched_figures": [
                {"figure_id": "figure_024", "page": 50, "text": "Figure 24. Cross-page caption."}
            ],
            "unmatched_assets": [],
            "unresolved_clusters": [],
        },
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=51,
        document_structure=None,
        reader_payload={
            "reader_figures": [
                {
                    "reader_figure_id": "figure_024_reader",
                    "figure_number": 24,
                    "reader_status": "EXACT_MATCH",
                    "consumed_caption_block_ids": [{"page": 51, "block_id": 3}],
                    "consumed_asset_block_ids": [{"page": 50, "block_id": 101}],
                    "caption_text": "Figure 24. Cross-page caption.",
                }
            ],
            "consumed_caption_block_ids": [{"page": 51, "block_id": 3}],
        },
    )

    assert md.count("![[render/figures/figure_024.md]]") == 1
