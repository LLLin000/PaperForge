"""Tests for ocr_profiles.py profile infrastructure."""

from __future__ import annotations


def test_extract_block_span_profile_list_format() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {
        "span_metadata": [
            {"size": 14.0, "font": "Times-Bold", "flags": 16, "color": 0},
            {"size": 14.0, "font": "Times-Bold", "flags": 16, "color": 0},
        ]
    }
    profile = extract_block_span_profile(block)
    assert profile is not None
    assert profile["mean_size"] == 14.0
    assert profile["max_size"] == 14.0
    assert profile["is_bold"] is True
    assert profile["is_italic"] is False
    assert profile["is_colored"] is False


def test_extract_block_span_profile_dict_format() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {
        "span_metadata": {"size": 12.0, "flags": "bold"}
    }
    profile = extract_block_span_profile(block)
    assert profile is not None
    assert profile["mean_size"] == 12.0
    assert profile["is_bold"] is True


def test_extract_block_span_profile_no_data() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {}
    profile = extract_block_span_profile(block)
    assert profile is None


def test_extract_block_span_profile_empty_list() -> None:
    from paperforge.worker.ocr_profiles import extract_block_span_profile

    block = {"span_metadata": []}
    profile = extract_block_span_profile(block)
    assert profile is None


def test_build_role_span_profiles_aggregates_by_role() -> None:
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    blocks = [
        {"role": "section_heading", "span_metadata": {"size": 16.0, "flags": "bold"}},
        {"role": "section_heading", "span_metadata": {"size": 15.5, "flags": "bold"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.0, "flags": "normal"}},
        {"role": "body_paragraph", "span_metadata": {"size": 10.5, "flags": "normal"}},
    ]
    profiles = build_role_span_profiles(blocks)
    assert "section_heading" in profiles
    assert "body_paragraph" in profiles
    assert profiles["section_heading"]["block_count"] == 2
    assert profiles["body_paragraph"]["mean_size"] == 10.25


def test_build_role_span_profiles_profile_quality() -> None:
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    blocks = [
        {"role": "body_paragraph", "span_metadata": {"size": 10.0, "flags": 0}}
    ]
    profiles = build_role_span_profiles(blocks)
    assert profiles["body_paragraph"]["quality"] == "no_data"


def test_build_role_span_profiles_empty_input() -> None:
    from paperforge.worker.ocr_profiles import build_role_span_profiles

    assert build_role_span_profiles([]) == {}


def test_cross_validate_with_span_no_profile() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 10.0, "flags": 0}}
    result = cross_validate_with_span(block, "body_paragraph", {})
    assert result["role"] == "body_paragraph"
    assert result["adjustment"] == 0.0


def test_cross_validate_with_span_mismatch() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 16.0, "flags": "bold"}}
    profiles = {
        "body_paragraph": {
            "block_count": 5, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
            "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
        },
    }
    result = cross_validate_with_span(block, "body_paragraph", profiles)
    assert result["role"] == "body_paragraph"
    assert result["adjustment"] < 0


def test_cross_validate_with_span_match() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 10.0, "flags": 0}}
    profiles = {
        "body_paragraph": {
            "block_count": 5, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
            "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
        },
    }
    result = cross_validate_with_span(block, "body_paragraph", profiles)
    assert result["role"] == "body_paragraph"
    assert result["adjustment"] > 0


def test_cross_validate_with_span_suggests_alternative() -> None:
    from paperforge.worker.ocr_profiles import cross_validate_with_span

    block = {"span_metadata": {"size": 16.0, "flags": "bold"}}
    profiles = {
        "body_paragraph": {
            "block_count": 5, "mean_size": 10.0, "max_size": 10.5, "min_size": 9.5,
            "dispersion": 0.05, "quality": "strong", "bold_ratio": 0.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPSMT"],
        },
        "section_heading": {
            "block_count": 3, "mean_size": 16.0, "max_size": 16.5, "min_size": 15.5,
            "dispersion": 0.03, "quality": "strong", "bold_ratio": 1.0,
            "italic_ratio": 0.0, "font_families": ["TimesNewRomanPS-BoldMT"],
        },
    }
    result = cross_validate_with_span(block, "body_paragraph", profiles)
    assert "section_heading" in result["suggested_roles"]
    assert result["adjustment"] < 0
