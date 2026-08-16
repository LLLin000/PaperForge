"""P0-4: canonical paper-key normalization (core/keys.py)."""

from __future__ import annotations

from paperforge.core.keys import normalize_paper_keys


def test_crlf_and_whitespace_stripped():
    raw = "ABC12345\r\nDEF23456\r\n  GHI34567  \r\n"
    assert normalize_paper_keys(raw) == ["ABC12345", "DEF23456", "GHI34567"]


def test_comma_and_space_separated():
    raw = "ABC12345, DEF23456 GHI34567"
    assert normalize_paper_keys(raw) == ["ABC12345", "DEF23456", "GHI34567"]


def test_bom_tolerated():
    raw = "\ufeffABC12345\nDEF23456"
    assert normalize_paper_keys(raw) == ["ABC12345", "DEF23456"]


def test_duplicates_deduped_stably():
    raw = "ABC12345\nDEF23456\nABC12345"
    assert normalize_paper_keys(raw) == ["ABC12345", "DEF23456"]


def test_blank_lines_dropped():
    raw = "\n\nABC12345\n\n\n"
    assert normalize_paper_keys(raw) == ["ABC12345"]


def test_membership_filter_drops_strays():
    raw = "ABC12345\nGHOSTKEY\nDEF23456"
    known = {"ABC12345", "DEF23456"}
    assert normalize_paper_keys(raw, known_keys=known) == ["ABC12345", "DEF23456"]


def test_iterable_input():
    assert normalize_paper_keys(["ABC12345", " DEF23456 ", "ABC12345"]) == [
        "ABC12345",
        "DEF23456",
    ]
