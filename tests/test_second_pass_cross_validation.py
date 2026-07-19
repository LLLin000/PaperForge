"""Tests for second-pass cross-validation of low-confidence role assignments."""

from __future__ import annotations

SAMPLE_PROFILES = {
    "body_paragraph": {
        "block_count": 10,
        "mean_size": 10.0,
        "max_size": 10.5,
        "min_size": 9.5,
        "dispersion": 0.05,
        "quality": "strong",
        "bold_ratio": 0.0,
        "italic_ratio": 0.0,
        "font_families": ["TimesNewRomanPSMT"],
    },
    "section_heading": {
        "block_count": 3,
        "mean_size": 16.0,
        "max_size": 16.5,
        "min_size": 15.5,
        "dispersion": 0.03,
        "quality": "strong",
        "bold_ratio": 1.0,
        "italic_ratio": 0.0,
        "font_families": ["TimesNewRomanPS-BoldMT"],
    },
    "figure_caption": {
        "block_count": 4,
        "mean_size": 9.0,
        "max_size": 9.5,
        "min_size": 8.5,
        "dispersion": 0.05,
        "quality": "strong",
        "bold_ratio": 0.0,
        "italic_ratio": 0.75,
        "font_families": ["TimesNewRomanPS-ItalicMT"],
    },
    "reference_item": {
        "block_count": 15,
        "mean_size": 8.5,
        "max_size": 9.0,
        "min_size": 8.0,
        "dispersion": 0.04,
        "quality": "strong",
        "bold_ratio": 0.0,
        "italic_ratio": 0.0,
        "font_families": ["TimesNewRomanPSMT"],
    },
}


def test_second_pass_body_paragraph_misclassified_heading() -> None:
    """A body_paragraph with heading-like span should be flagged."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "body_paragraph",
        "role_confidence": 0.4,
        "span_metadata": {"size": 16.0, "flags": "bold"},
        "text": "Clinical Outcomes",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    assert "section_heading" in result["suggested_roles"]
    assert result["confidence_adjustment"] < 0


def test_second_pass_body_paragraph_confirmed_body() -> None:
    """A body_paragraph with body-like span should be left alone."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "body_paragraph",
        "role_confidence": 0.6,
        "span_metadata": {"size": 10.0, "flags": 0},
        "text": "The results show a significant difference between groups.",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    assert result["confidence_adjustment"] > 0


def test_second_pass_caption_long_text() -> None:
    """A long figure_caption with body-sized span should not override formal prefix."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "figure_caption",
        "role_confidence": 0.5,
        "span_metadata": {"size": 10.5, "flags": 0},
        "text": "Figure 4. This is a very long caption that looks like body text in font size...",
        "raw_label": "figure_title",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False  # Don't override formal prefix
    assert result["role"] == "figure_caption"


def test_second_pass_reference_body_style() -> None:
    """A regex-matched reference item with body-sized font should flag body_paragraph as alternative."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "reference_item",
        "role_confidence": 0.55,
        "span_metadata": {"size": 10.5, "flags": 0},
        "text": "Smith et al. (2020) found that...",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False  # confidence 0.55 > 0.3 threshold
    assert "body_paragraph" in result["suggested_roles"]


def test_second_pass_no_span_metadata() -> None:
    """Without span_metadata, second pass should produce no change."""
    from paperforge.worker.ocr_roles import second_pass_cross_validate

    block = {
        "role": "body_paragraph",
        "role_confidence": 0.5,
        "text": "Some paragraph without span data.",
        "raw_label": "text",
    }
    result = second_pass_cross_validate(block, SAMPLE_PROFILES)
    assert result["role_changed"] is False
    assert result["confidence_adjustment"] == 0.0
    assert len(result["suggested_roles"]) == 0
