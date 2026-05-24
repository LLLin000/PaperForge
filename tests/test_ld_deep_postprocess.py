"""Tests for postprocess_pass2 validation."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_ld_spec = spec_from_file_location(
    "ld_deep",
    _REPO_ROOT / "paperforge" / "skills" / "literature-qa" / "scripts" / "ld_deep.py",
)
_ld_mod = module_from_spec(_ld_spec)
sys.modules["ld_deep"] = _ld_mod
_ld_spec.loader.exec_module(_ld_mod)

from ld_deep import postprocess_pass2, FIGURE_SUBHEADINGS


def _make_note_with_figures(count_or_order):
    """Build a note with figure blocks in given order."""
    if isinstance(count_or_order, int):
        order = list(range(1, count_or_order + 1))
    else:
        order = count_or_order
    parts = []
    for n in order:
        sub_parts = [f"> **{h}**\n> Content for {n}" for h in FIGURE_SUBHEADINGS]
        block = (
            f"\n> [!note]- Figure {n}: Test caption\n"
            f"> ![[fig_{n}.png]]\n"
            f">\n" +
            "\n>\n".join(sub_parts) +
            "\n"
        )
        parts.append(block)
    return "\n".join(parts)


class TestPostprocessPass2:
    def test_clean_note(self):
        note = _make_note_with_figures(3)
        errors = postprocess_pass2(note, figure_count=3)
        assert errors == []

    def test_out_of_order(self):
        note = _make_note_with_figures([1, 3, 2])
        errors = postprocess_pass2(note, figure_count=3)
        assert any(e["type"] == "order" for e in errors)

    def test_stray_image(self):
        note = _make_note_with_figures(2) + "\n![[stray_image.png]]\n"
        errors = postprocess_pass2(note, figure_count=2)
        assert any(e["type"] == "image_bounds" for e in errors)

    def test_empty_figure_block(self):
        """Figure with only sub-headings and no content between them."""
        parts = []
        for n in [1, 2]:
            block = (
                f"\n> [!note]- Figure {n}: Test caption\n"
                f"> ![[fig_{n}.png]]\n"
                f">\n"
                + "\n>\n".join([f"> **{h}**\n>" for h in FIGURE_SUBHEADINGS]) +
                "\n"
            )
            parts.append(block)
        note = "\n".join(parts)
        errors = postprocess_pass2(note, figure_count=2)
        assert any(e["type"] == "empty_block" for e in errors)

    def test_missing_subheading(self):
        """Figure block missing '我的理解' sub-heading."""
        sub = [h for h in FIGURE_SUBHEADINGS if h != "我的理解"]
        sub_parts = [f"> **{h}**\n> Content" for h in sub]
        note = (
            "\n> [!note]- Figure 1: Test caption\n"
            "> ![[fig_1.png]]\n"
            ">\n" +
            "\n>\n".join(sub_parts) +
            "\n"
        )
        errors = postprocess_pass2(note, figure_count=1)
        assert any(e["type"] == "missing_subheading" for e in errors)

    def test_duplicate_figure(self):
        note = _make_note_with_figures([1, 2, 2])
        errors = postprocess_pass2(note, figure_count=2)
        assert any(e["type"] == "duplicate" for e in errors)

    def test_missing_figure(self):
        note = _make_note_with_figures([1, 2])
        errors = postprocess_pass2(note, figure_count=3)
        assert any(e["type"] == "missing" for e in errors)

    def test_extra_figure(self):
        note = _make_note_with_figures(3)
        errors = postprocess_pass2(note, figure_count=2)
        assert any(e["type"] == "extra" for e in errors)

    def test_zero_figures(self):
        note = "# Test\nNo figures here.\n"
        errors = postprocess_pass2(note, figure_count=0)
        assert errors == []
