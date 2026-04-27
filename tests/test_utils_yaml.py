"""Unit tests for _utils.py YAML helper functions.

Covers: yaml_quote, yaml_block, yaml_list
"""

from __future__ import annotations

from pathlib import Path

import pytest

from paperforge.worker._utils import yaml_block, yaml_list, yaml_quote


class TestYamlQuote:
    """yaml_quote(value: str) -> str"""

    def test_plain_string(self) -> None:
        assert yaml_quote("hello") == '"hello"'

    def test_string_with_quotes(self) -> None:
        assert yaml_quote('say "hello"') == '"say \\"hello\\""'

    def test_string_with_backslash(self) -> None:
        assert yaml_quote("a\\b") == '"a\\\\b"'

    def test_boolean_true(self) -> None:
        assert yaml_quote(True) == "true"

    def test_boolean_false(self) -> None:
        assert yaml_quote(False) == "false"

    def test_none_becomes_empty_quoted(self) -> None:
        assert yaml_quote(None) == '""'

    def test_empty_string(self) -> None:
        assert yaml_quote("") == '""'

    def test_int_converts_to_string(self) -> None:
        assert yaml_quote(42) == '"42"'

    def test_string_with_only_special_yaml_chars(self) -> None:
        assert yaml_quote(": ") == '": "'


class TestYamlBlock:
    """yaml_block(value: str) -> list[str]"""

    def test_single_line(self) -> None:
        result = yaml_block("Hello world")
        assert result[0] == "abstract: |-"
        assert "Hello world" in result[1]

    def test_multi_line(self) -> None:
        text = "Line 1\nLine 2\nLine 3"
        result = yaml_block(text)
        assert result[0] == "abstract: |-"
        assert len(result) == 4  # header + 3 lines
        assert "  Line 1" in result[1]
        assert "  Line 2" in result[2]
        assert "  Line 3" in result[3]

    def test_empty_string(self) -> None:
        result = yaml_block("")
        assert len(result) == 2
        assert "abstract: |-" in result[0]

    def test_none_input(self) -> None:
        result = yaml_block(None)  # type: ignore[arg-type]
        assert len(result) == 2
        assert "abstract: |-" in result[0]

    def test_whitespace_only(self) -> None:
        result = yaml_block("   ")
        assert len(result) == 2
        assert "abstract: |-" in result[0]

    def test_trailing_newline_stripped(self) -> None:
        result = yaml_block("Hello\n")
        assert len(result) == 2
        assert "  Hello" in result[1]

    def test_lines_are_indented_with_two_spaces(self) -> None:
        result = yaml_block("Test")
        assert result[1].startswith("  ")


class TestYamlList:
    """yaml_list(key: str, values) -> list[str]"""

    def test_list_of_strings(self) -> None:
        result = yaml_list("tags", ["a", "b", "c"])
        assert result[0] == "tags:"
        assert "  - " in result[1] and "a" in result[1]
        assert "  - " in result[2] and "b" in result[2]
        assert "  - " in result[3] and "c" in result[3]

    def test_empty_list(self) -> None:
        result = yaml_list("tags", [])
        assert result == ["tags: []"]

    def test_none_values_filtered(self) -> None:
        result = yaml_list("tags", ["a", None, "c"])
        assert len(result) == 3
        assert "a" in result[1]
        assert "c" in result[2]

    def test_all_none_returns_empty_list(self) -> None:
        result = yaml_list("tags", [None, None])
        assert result == ["tags: []"]

    def test_none_input(self) -> None:
        result = yaml_list("tags", None)  # type: ignore[arg-type]
        assert result == ["tags: []"]

    def test_string_with_quotes_in_list(self) -> None:
        result = yaml_list("items", ['hello "world"'])
        assert len(result) == 2
        assert '\\"' in result[1]
