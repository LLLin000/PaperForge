from __future__ import annotations

import pytest

from paperforge.worker.ocr_figures import (
    _extract_figure_marker,
    _extract_figure_number,
    _format_figure_id,
    build_figure_inventory_vnext,
)


class TestExtractFigureNumber:
    """Test _extract_figure_number after regex change to named groups."""

    def test_main_after_regex_change(self):
        assert _extract_figure_number("Figure 1. Caption") == 1

    def test_supplementary_after_regex_change(self):
        assert _extract_figure_number("Figure S1. Caption") == 1

    def test_appendix_after_regex_change(self):
        assert _extract_figure_number("Figure A1. Caption") == 1


class TestExtractFigureMarker:
    """Test _extract_figure_marker returns correct structured dict."""

    def test_supplementary_keyword_has_no_prefix(self):
        marker = _extract_figure_marker("Supplementary Figure 1. Caption")
        # "Supplementary" keyword determines namespace, not the S prefix.
        # Since there's no explicit prefix letter before the number,
        # prefix is None.
        assert marker["prefix"] is None
        assert marker["namespace"] == "supplementary"
        assert _format_figure_id("supplementary", 1) == "figure_s001"

    def test_supplementary_keyword_overrides_appendix_prefix(self):
        """Supplementary keyword in text takes precedence over prefix letter A."""
        marker = _extract_figure_marker("Supplementary Figure A1. Caption")
        # prefix is "A", but "supplementary" keyword forces namespace to
        # "supplementary", overriding the appendix inference from prefix.
        assert marker["namespace"] == "supplementary"

    def test_extended_data_keyword_overrides_appendix_prefix(self):
        """Extended Data keyword in text takes precedence over prefix letter A."""
        marker = _extract_figure_marker("Extended Data Figure A1. Caption")
        assert marker["namespace"] == "extended_data"

    def test_lowercase_appendix_prefix_normalized(self):
        """Lowercase prefix letter is normalized to uppercase."""
        marker = _extract_figure_marker("Figure a1")
        assert marker["prefix"] == "A"

    @pytest.mark.parametrize(
        "text, expected_prefix",
        [
            ("Figure S1", "S"),
            ("Figure A1", "A"),
            ("Figure A.1", "A"),
            ("Figure B2", "B"),
            ("Figure 1", None),
        ],
    )
    def test_prefix_extraction(self, text, expected_prefix):
        marker = _extract_figure_marker(text)
        assert marker["prefix"] == expected_prefix

    @pytest.mark.parametrize(
        "text, expected_namespace",
        [
            ("Figure S1", "supplementary"),
            ("Figure A1", "appendix"),
            ("Figure 1", "main"),
        ],
    )
    def test_namespace_resolution(self, text, expected_namespace):
        marker = _extract_figure_marker(text)
        assert marker["namespace"] == expected_namespace


class TestFormatFigureId:
    """Test _format_figure_id with alpha_prefix support."""

    def test_appendix_letter_is_preserved(self):
        """Appendix prefix letter is embedded in the figure id."""
        assert _format_figure_id("appendix", 2, alpha_prefix="B") == "figure_b002"

    def test_figure_a1_and_figure_b1_do_not_collide(self):
        """Different appendix letters produce distinct ids for same number."""
        id_a = _format_figure_id("appendix", 1, alpha_prefix="A")
        id_b = _format_figure_id("appendix", 1, alpha_prefix="B")
        assert id_a == "figure_a001"
        assert id_b == "figure_b001"
        assert id_a != id_b

    def test_main_number_unchanged(self):
        """Main namespace unchanged by alpha_prefix addition."""
        assert _format_figure_id("main", 1) == "figure_001"

    def test_supplementary_unchanged(self):
        """Supplementary namespace unchanged by alpha_prefix addition."""
        assert _format_figure_id("supplementary", 1) == "figure_s001"


class TestTableA1Leak:
    """Ensure Table A1 captions do not leak into the figure inventory."""

    def test_table_a1_caption_not_consumed_by_figure_inventory(self):
        blocks = [
            {
                "block_id": "t1",
                "page": 1,
                "role": "table_caption",
                "text": "Table A1. Patient Demographics",
                "bbox": [100, 100, 500, 120],
                "zone": "display_zone",
                "style_family": "legend_like",
            },
            {
                "block_id": "a1",
                "page": 1,
                "role": "media_asset",
                "text": "",
                "bbox": [100, 130, 500, 600],
                "zone": "display_zone",
            },
        ]
        result = build_figure_inventory_vnext(blocks, 1200)
        matched = result.get("matched_figures", [])
        # No figure should have been created with an appendix a-prefixed id
        assert not any(m.get("figure_id", "") == "figure_a001" for m in matched)
        # No matched figure text should contain "Table A1"
        assert not any("Table A1" in (m.get("text") or "") for m in matched)


class TestTableLeakRegression:
    """Guard against table captions being parsed by figure regex helpers."""

    def test_table_numeric_caption_is_not_a_figure_number(self):
        assert _extract_figure_number("TABLE 2. Baseline characteristics") is None

    def test_table_appendix_caption_marker_has_no_figure_number(self):
        marker = _extract_figure_marker("TABLE A1. Patient Demographics")
        assert marker["number"] is None
        assert marker["namespace"] == "main"


class TestCrossPageIntBlockIds:
    """Real structured blocks use per-page int block IDs; settlement must preserve legend text."""

    def test_cross_page_reserved_lookup_handles_int_block_ids(self):
        blocks = [
            {
                "block_id": 1,
                "page": 1,
                "role": "figure_caption",
                "text": "Figure 1. Cross-page caption.",
                "bbox": [100, 100, 500, 150],
            },
            {
                "block_id": 2,
                "page": 2,
                "role": "figure_asset",
                "text": "",
                "bbox": [100, 100, 500, 400],
            },
        ]

        result = build_figure_inventory_vnext(blocks, 1200)
        matched = result.get("matched_figures", [])
        assert len(matched) == 1
        assert matched[0]["legend_block_id"] == "1"
        assert matched[0]["text"] == "Figure 1. Cross-page caption."


class TestPageLocalBlockIds:
    """Structured block ids repeat per page; figure materialization must use page + block_id."""

    def test_same_page_match_uses_legend_from_same_page(self):
        blocks = [
            {
                "block_id": 4,
                "page": 4,
                "role": "figure_caption",
                "text": "TABLE 2\nWrong text from another page",
                "bbox": [100, 100, 500, 150],
            },
            {
                "block_id": 4,
                "page": 5,
                "role": "figure_caption",
                "text": "Figure 1. Real same-page caption.",
                "bbox": [100, 100, 500, 150],
            },
            {
                "block_id": "asset1",
                "page": 5,
                "role": "figure_asset",
                "text": "",
                "bbox": [100, 180, 500, 500],
            },
        ]

        result = build_figure_inventory_vnext(blocks, 1200)
        matched = result.get("matched_figures", [])
        assert len(matched) == 1
        assert matched[0]["page"] == 5
        assert matched[0]["text"] == "Figure 1. Real same-page caption."


class TestAppendixSamePageMatching:
    """Appendix captions should score as formal figure legends when near media."""

    def test_appendix_same_page_candidate_matches_media(self):
        blocks = [
            {
                "block_id": "c1",
                "page": 1,
                "role": "figure_caption_candidate",
                "text": "Figure A1. Appendix caption.",
                "bbox": [100, 100, 500, 130],
            },
            {
                "block_id": "a1",
                "page": 1,
                "role": "media_asset",
                "text": "",
                "bbox": [100, 160, 500, 500],
            },
        ]

        result = build_figure_inventory_vnext(blocks, 1200)
        matched = result.get("matched_figures", [])
        assert len(matched) == 1
        assert matched[0]["figure_id"] == "figure_a001"
