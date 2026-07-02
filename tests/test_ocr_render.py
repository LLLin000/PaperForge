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


def test_residual_footnote_skipped_while_converted_callout_renders() -> None:
    """Footnotes surviving _convert_footnotes_to_callouts must not leak into body;
    converted footnote-derived structured_insert blocks must still render."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Main body text provides font reference.",
            "block_id": "p5_b1",
            "span_metadata": {"size": 11},
            "bbox": [100, 100, 500, 130],
        },
        {
            "page": 5,
            "role": "footnote",
            "text": "Plain footnote without symbols or markers.",
            "block_id": "p5_b2",
            "span_metadata": {"size": 9},
            "bbox": [100, 150, 500, 175],
        },
        {
            "page": 5,
            "role": "footnote",
            "text": "* Correspondence: author@example.com",
            "block_id": "p5_b3",
            "span_metadata": {"size": 9},
            "bbox": [100, 180, 500, 205],
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert "Plain footnote without symbols or markers." not in md
    assert "* Correspondence: author@example.com" in md


def test_table_caption_fallback_uses_blockquote_not_heading() -> None:
    """table_caption with no table embed falls back to blockquote, never a heading."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results summary.",
            "block_id": "p5_b1",
        },
    ]

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory={"tables": [], "unmatched_assets": []},
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert "### Table 1. Results summary." not in md
    assert "> **Table Caption:** Table 1. Results summary." in md


def test_weak_match_caption_fallback_not_lost() -> None:
    """Weak-matched table caption uses blockquote, not heading — not silently lost."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results summary.",
            "block_id": "p5_b1",
        },
    ]

    table_inventory = {
        "tables": [
            {
                "page": 5,
                "caption_block_id": "p5_b1",
                "caption_text": "Table 1. Results summary.",
                "has_asset": False,
                "consumed_block_ids": [],
                "match_status": "unmatched_caption",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert "### Table 1. Results summary." not in md
    assert "> **Table Caption:** Table 1. Results summary." in md


def test_consumed_table_note_skipped_before_role_skip() -> None:
    """Non-footnote-role table note removed by ownership skip, not role skip."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Main body text.",
            "block_id": "p5_body",
            "bbox": [100, 100, 500, 130],
        },
        {
            "page": 5,
            "role": "table_asset",
            "raw_label": "table",
            "text": "",
            "block_id": "p5_asset",
            "bbox": [100, 200, 600, 500],
        },
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "block_id": "p5_caption",
            "bbox": [100, 510, 600, 550],
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Note: all values are mean +/- SD.",
            "block_id": "p5_note",
            "bbox": [100, 555, 600, 580],
        },
    ]

    table_inventory = {
        "tables": [
            {
                "caption_block_id": "p5_caption",
                "page": 5,
                "caption_text": "Table 1. Results.",
                "asset_block_id": "p5_asset",
                "has_asset": True,
                "consumed_block_ids": ["p5_caption", "p5_asset", "p5_note"],
                "segments": [{"page": 5, "asset_block_id": "p5_asset", "asset_bbox": [100, 200, 600, 500]}],
                "note_block_ids": ["p5_note"],
                "note_texts": ["Note: all values are mean +/- SD."],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert "Note: all values are mean +/- SD." not in md
    assert "Table 1. Results." not in md
    assert "![[render/tables/table_001.md]]" in md
    assert "> **Table Caption:**" not in md


def test_table_object_renderer_includes_footnote_note() -> None:
    """Table object renderer includes ## Notes; fulltext skips footnote-role note via ownership."""
    from paperforge.worker.ocr_render import render_fulltext_markdown
    from paperforge.worker.ocr_objects import render_table_object_markdown

    note_text = "* p < 0.05 vs baseline."

    obj_md = render_table_object_markdown({
        "table_id": "table_001",
        "page": 5,
        "caption": "Table 1. Results.",
        "image_relpath": "assets/tables/table_001.jpg",
        "confidence": 0.85,
        "formal_table_number": 1,
        "note_texts": [note_text],
        "note_match_reason": "note_band_geometry_match",
    })

    assert "## Notes" in obj_md
    assert note_text in obj_md

    structured = [
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Main body text.",
            "block_id": "p5_body",
            "bbox": [100, 100, 500, 130],
        },
        {
            "page": 5,
            "role": "footnote",
            "text": note_text,
            "block_id": "p5_note",
            "bbox": [100, 905, 600, 930],
        },
        {
            "page": 5,
            "role": "table_asset",
            "raw_label": "table", "text": "",
            "block_id": "p5_asset",
            "bbox": [100, 200, 600, 500],
        },
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "block_id": "p5_caption",
            "bbox": [100, 510, 600, 550],
        },
    ]

    table_inventory = {
        "tables": [
            {
                "caption_block_id": "p5_caption",
                "page": 5,
                "caption_text": "Table 1. Results.",
                "asset_block_id": "p5_asset",
                "has_asset": True,
                "consumed_block_ids": ["p5_caption", "p5_asset", "p5_note"],
                "segments": [{"page": 5, "asset_block_id": "p5_asset", "asset_bbox": [100, 200, 600, 500]}],
                "note_block_ids": ["p5_note"],
                "note_texts": [note_text],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert note_text not in md
    assert "![[render/tables/table_001.md]]" in md
    assert "> **Table Caption:**" not in md


def test_consumed_table_note_uses_actual_block_page_not_table_page() -> None:
    """Consumed key uses each block's real page, not table['page']."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 6,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "block_id": "p6_caption",
        },
        {
            "page": 7,
            "role": "body_paragraph",
            "text": "Note: cross-page table note.",
            "block_id": "p7_note",
        },
    ]

    table_inventory = {
        "tables": [
            {
                "page": 6,
                "caption_text": "Table 1. Results.",
                "has_asset": True,
                "consumed_block_ids": ["p6_caption", "p7_note"],
                "note_block_ids": ["p7_note"],
                "note_texts": ["Note: cross-page table note."],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=7,
        document_structure=None,
        reader_payload={},
    )

    assert "Note: cross-page table note." not in md


def test_consumed_stringified_int_note_id_matches_block_int_id() -> None:
    """consumed_block_ids may contain stringified int IDs; ownership skip must match
    against the structured block's int block_id via str() alias."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Main text.",
            "block_id": "p5_body",
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Table note with int block_id.",
            "block_id": 123,
        },
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Caption.",
            "block_id": "p5_caption",
        },
    ]

    table_inventory = {
        "tables": [
            {
                "page": 5,
                "caption_text": "Table 1. Caption.",
                "has_asset": True,
                "consumed_block_ids": ["p5_caption", "123"],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert "Table note with int block_id." not in md


def test_materialized_table_caption_continuation_is_skipped_by_render_when_consumed():
    from paperforge.worker.ocr_render import render_fulltext_markdown

    blocks = [
        {"page": 1, "block_id": "cap1", "role": "table_caption", "text": "Table 2", "bbox": [100, 100, 220, 120]},
        {"page": 1, "block_id": "cap2", "role": "figure_caption", "text": "Structural parameters of nanocomposites obtained from the d", "bbox": [100, 121, 500, 145]},
    ]
    table_inventory = {
        "tables": [
            {
                "page": 1,
                "caption_block_id": "cap1",
                "caption_text": "Table 2 Structural parameters of nanocomposites obtained from the d",
                "consumed_block_ids": ["cap1", "cap2"],
                "has_asset": False,
                "match_status": "unmatched_caption",
            }
        ]
    }

    md = render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory=table_inventory,
        page_count=1,
        document_structure=None,
        reader_payload={"reader_figures": [], "consumed_caption_block_ids": []},
    )

    assert "Structural parameters of nanocomposites" not in md

def test_cross_page_table_asset_id_does_not_consume_same_id_on_caption_page():
    """
    Caption page has block_id=7 reference_item.
    Table asset on previous page also has block_id=7.
    Explicit segment consumes only previous-page asset, not caption-page ref.
    """
    from paperforge.worker.ocr_render import render_fulltext_markdown

    table_inventory = {
        "tables": [
            {
                "page": 5,
                "caption_block_id": 10,
                "segments": [
                    {"page": 4, "asset_block_id": 7},
                ],
                "note_block_ids": [11],
                "bridge_block_ids": [12],
                "consumed_block_ids": [7, 10, 11, 12],
            }
        ]
    }

    structured_blocks = [
        # Table asset on page 4, block_id=7
        {"block_id": 7, "page": 4, "role": "table_asset", "text": "[Table 1]"},
        # Reference item on page 5, block_id=7 — must NOT be consumed
        {"block_id": 7, "page": 5, "role": "reference_item", "text": "7. Smith J...", "bbox": [0, 0, 500, 20]},
    ]

    result = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        table_inventory=table_inventory,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        page_count=10,
    )

    assert "7. Smith J..." in result, "Reference on caption page should not be consumed"


def test_table_consumed_block_ids_do_not_drop_same_id_reference_on_later_page():
    """Reference on later page with same block_id as earlier table must not be dropped."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    table_inventory = {
        "tables": [
            {
                "page": 1,
                "caption_block_id": 5,
                "segments": [{"page": 1, "asset_block_id": 6}],
                "note_block_ids": [],
                "bridge_block_ids": [],
                "consumed_block_ids": [5, 6],
            }
        ]
    }

    structured_blocks = [
        {"block_id": 5, "page": 1, "role": "table_caption", "text": "Table 1. Results"},
        {"block_id": 6, "page": 1, "role": "table_asset", "text": "[data]"},
        # Same block_id=5 on page 2 — must NOT be consumed
        {"block_id": 5, "page": 2, "role": "reference_item", "text": "5. Author...", "bbox": [0, 0, 500, 20]},
    ]

    result = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        table_inventory=table_inventory,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        page_count=10,
    )

    assert "5. Author..." in result, "Reference on later page with same block_id should not be consumed"


def test_table_caption_still_consumed():
    """Table caption blocks on same page as table must still be consumed."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    table_inventory = {
        "tables": [
            {
                "page": 1,
                "caption_block_id": 5,
                "segments": [{"page": 1, "asset_block_id": 6}],
                "note_block_ids": [],
                "bridge_block_ids": [],
                "consumed_block_ids": [5, 6],
            }
        ]
    }

    structured_blocks = [
        {"block_id": 5, "page": 1, "role": "table_caption", "text": "Table 1. Results"},
        {"block_id": 6, "page": 1, "role": "table_asset", "text": "[data]"},
    ]

    result = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        table_inventory=table_inventory,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        page_count=10,
    )

    assert "Table 1. Results" not in result, "Table caption should be consumed (excluded from output)"
    assert "[data]" not in result, "Table asset should be consumed"

def test_skip_section_grouping_places_tail_nonref_after_refs():
    """When skip_section_grouping=True, tail backmatter (Address correspondence) must appear AFTER refs."""
    from paperforge.worker.ocr_render import _reorder_tail_run

    ref_block = {"role": "reference_item", "text": "1. Author A. Title. Journal. 2024.", "bbox": [100, 0, 500, 20], "block_number": "1"}
    tail_block = {"role": "body_paragraph", "text": "Address correspondence to: Dr. Smith", "bbox": [100, 50, 500, 70], "zone": "tail_nonref_hold_zone"}
    heading = {"role": "backmatter_heading", "text": "Correspondence", "bbox": [100, -10, 500, 10]}

    result, ref, bm = _reorder_tail_run(
        [ref_block, tail_block, heading],
        carried_ref=None,
        carried_backmatter=None,
        page_width=800,
        skip_section_grouping=True,
    )
    texts = [b.get("text", "") for b in result]
    ref_idx = texts.index("1. Author A. Title. Journal. 2024.")
    tail_idx = texts.index("Address correspondence to: Dr. Smith")
    assert tail_idx > ref_idx, f"Tail block at {tail_idx} should be after ref at {ref_idx}"


def test_skip_section_grouping_keeps_ordinary_nonref_before_refs():
    """Ordinary non-ref blocks (not tail backmatter) must remain BEFORE refs."""
    from paperforge.worker.ocr_render import _reorder_tail_run

    ordinary = {"role": "body_paragraph", "text": "This is some ordinary body text.", "bbox": [100, 0, 500, 20]}
    ref_block = {"role": "reference_item", "text": "1. Author A. Title. 2024.", "bbox": [100, 50, 500, 70], "block_number": "1"}

    result, ref, bm = _reorder_tail_run(
        [ordinary, ref_block],
        carried_ref=None,
        carried_backmatter=None,
        page_width=800,
        skip_section_grouping=True,
    )
    texts = [b.get("text", "") for b in result]
    ordinary_idx = texts.index("This is some ordinary body text.")
    ref_idx = texts.index("1. Author A. Title. 2024.")
    assert ordinary_idx < ref_idx, f"Ordinary block at {ordinary_idx} should be before ref at {ref_idx}"


def test_real_backmatter_heading_still_attaches_its_own_body():
    """A real backmatter heading like 'FUNDING' must still have its body attached (not orphaned)."""
    from paperforge.worker.ocr_render import _reorder_tail_run

    heading = {"role": "backmatter_heading", "text": "FUNDING", "bbox": [100, 0, 500, 20]}
    body = {"role": "backmatter_body", "text": "This work was supported by NIH grant R01...", "bbox": [100, 25, 500, 45]}
    ref_block = {"role": "reference_item", "text": "1. Author A. 2024.", "bbox": [100, 100, 500, 120], "block_number": "1"}

    result, ref, bm = _reorder_tail_run(
        [heading, body, ref_block],
        carried_ref=None,
        carried_backmatter=None,
        page_width=800,
        skip_section_grouping=False,
    )
    texts = [b.get("text", "") for b in result]
    assert "FUNDING" in texts
    assert "This work was supported by NIH grant R01..." in texts
    funding_idx = texts.index("FUNDING")
    body_idx = texts.index("This work was supported by NIH grant R01...")
    assert body_idx > funding_idx, "Funding body should be after Funding heading"


def test_phase_4b_does_not_swallow_tail_nonref_into_ref_section():
    """Phase 4b must not place tail backmatter continuations into ref_section["bodies"]."""
    from paperforge.worker.ocr_render import _reorder_tail_run

    ref_heading = {"role": "reference_heading", "text": "References", "bbox": [100, 0, 500, 20]}
    ref_item = {"role": "reference_item", "text": "1. Author. Title. 2024.", "bbox": [100, 25, 500, 45], "block_number": "1"}
    tail_body = {"role": "body_paragraph", "text": "Address correspondence to: Dr. Smith", "bbox": [100, 100, 500, 120], "zone": "tail_nonref_hold_zone"}

    result, ref, bm = _reorder_tail_run(
        [ref_heading, ref_item, tail_body],
        carried_ref=None,
        carried_backmatter=None,
        page_width=800,
    )
    texts = [b.get("text", "") for b in result]
    ref_idx = texts.index("1. Author. Title. 2024.")
    tail_idx = texts.index("Address correspondence to: Dr. Smith")
    assert tail_idx > ref_idx, f"Tail backmatter at {tail_idx} should be after ref at {ref_idx}"


def test_funding_body_still_attaches_to_funding_heading():
    """A real funding body must still attach to its heading even with tail_backmatter_blocks logic."""
    from paperforge.worker.ocr_render import _reorder_tail_run

    funding_heading = {"role": "backmatter_heading", "text": "FUNDING", "bbox": [100, 0, 500, 20]}
    funding_body = {"role": "backmatter_body", "text": "This work was funded by...", "bbox": [100, 25, 500, 45]}
    ref_item = {"role": "reference_item", "text": "1. Author. 2024.", "bbox": [100, 100, 500, 120], "block_number": "1"}

    result, ref, bm = _reorder_tail_run(
        [funding_heading, funding_body, ref_item],
        carried_ref=None,
        carried_backmatter=None,
        page_width=800,
    )
    texts = [b.get("text", "") for b in result]
    funding_idx = texts.index("FUNDING")
    body_idx = texts.index("This work was funded by...")
    assert body_idx > funding_idx, "Funding body after funding heading"


def test_refs_on_heading_page_are_rendered_after_heading():
    """When reference_item blocks appear before reference_heading on the same
    page (e.g. due to column sort or PDF reading order), the helper must
    reorder them so the heading comes first."""
    from paperforge.worker.ocr_render import _force_reference_heading_before_same_page_refs

    ref_heading = {"role": "reference_heading", "text": "References", "bbox": [400, 100, 500, 120]}
    ref_item = {"role": "reference_item", "text": "1. Author A. Title. 2024.", "bbox": [100, 0, 300, 20], "block_number": "1"}
    body_block = {"role": "body_paragraph", "text": "Some body text.", "bbox": [100, 50, 300, 70]}

    # Input has ref_item BEFORE ref_heading (bad ordering)
    result = _force_reference_heading_before_same_page_refs([ref_item, ref_heading, body_block])

    texts = [b.get("text", "") for b in result]
    heading_idx = texts.index("References")
    ref_idx = texts.index("1. Author A. Title. 2024.")
    body_idx = texts.index("Some body text.")

    assert heading_idx < ref_idx, f"Heading at {heading_idx} should be before ref at {ref_idx}"
    assert body_idx < heading_idx or body_idx > ref_idx, f"Body at {body_idx} should stay in its original position relative to heading/ref"


def test_non_ref_blocks_not_moved_by_guard():
    """Blocks without reference role should not be moved or duplicated by
    the force-reorder guard."""
    from paperforge.worker.ocr_render import _force_reference_heading_before_same_page_refs

    body1 = {"role": "body_paragraph", "text": "First body.", "bbox": [100, 0, 300, 20]}
    body2 = {"role": "body_paragraph", "text": "Second body.", "bbox": [100, 30, 300, 50]}
    ref_heading = {"role": "reference_heading", "text": "References", "bbox": [400, 100, 500, 120]}
    ref_item = {"role": "reference_item", "text": "1. Author. 2024.", "bbox": [100, 60, 300, 80], "block_number": "1"}

    result = _force_reference_heading_before_same_page_refs([body1, ref_item, ref_heading, body2])

    texts = [b.get("text", "") for b in result]
    assert "First body." in texts
    assert "Second body." in texts
    assert "References" in texts
    assert "1. Author. 2024." in texts
    # Body blocks must not be duplicated
    assert texts.count("First body.") == 1
    assert texts.count("Second body.") == 1
    assert texts.count("References") == 1
    assert texts.count("1. Author. 2024.") == 1
