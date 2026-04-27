"""Unit tests for _utils.py slugify and year extraction functions.

Covers: slugify_filename, _extract_year
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paperforge.worker._utils import _extract_year, slugify_filename


class TestSlugifyFilename:
    """slugify_filename(text: str) -> str"""

    def test_normal_text(self) -> None:
        assert slugify_filename("Hello World") == "Hello World"

    def test_strips_angle_brackets(self) -> None:
        assert slugify_filename("Hello <World>") == "Hello World"

    def test_strips_colon(self) -> None:
        assert slugify_filename("Title: Subtitle") == "Title Subtitle"

    def test_strips_double_quote(self) -> None:
        assert slugify_filename('Title "Sub"') == "Title Sub"

    def test_strips_forward_slash(self) -> None:
        assert slugify_filename("a/b") == "ab"

    def test_strips_backslash(self) -> None:
        assert slugify_filename("a\\b") == "ab"

    def test_strips_pipe_and_question_mark(self) -> None:
        assert slugify_filename("What? | Yes") == "What  Yes"

    def test_strips_asterisk(self) -> None:
        assert slugify_filename("Test * File") == "Test  File"

    def test_truncates_at_120_chars(self) -> None:
        long_str = "a" * 200
        result = slugify_filename(long_str)
        assert len(result) == 120

    def test_empty_string_falls_back(self) -> None:
        assert slugify_filename("") == "untitled"

    def test_only_special_chars_falls_back(self) -> None:
        assert slugify_filename("<>:\"/\\|?*") == "untitled"

    def test_leading_trailing_spaces(self) -> None:
        assert slugify_filename("  hello  ") == "hello"


class TestExtractYear:
    """_extract_year(value: str) -> str"""

    def test_four_digit_year(self) -> None:
        assert _extract_year("Published in 2024") == "2024"

    def test_19xx_year(self) -> None:
        assert _extract_year("1999") == "1999"

    def test_20xx_year(self) -> None:
        assert _extract_year("2001: A Space Odyssey") == "2001"

    def test_no_year_returns_empty(self) -> None:
        assert _extract_year("No digits here") == ""

    def test_empty_string_returns_empty(self) -> None:
        assert _extract_year("") == ""

    def test_none_input_returns_empty(self) -> None:
        assert _extract_year(None) == ""  # type: ignore[arg-type]

    def test_year_in_middle_of_string(self) -> None:
        assert _extract_year("Published 2024 in Journal") == "2024"

    def test_18xx_not_extracted(self) -> None:
        assert _extract_year("old 1899 ref") == ""
        # 18xx is NOT extracted because regex anchor is (19|20)\\d{2}
