"""Tests for skeleton rendering in ld_deep.py."""

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

from ld_deep import (
    render_figure_block,
    render_table_block,
    FigureEntry,
    TableEntry,
    FIGURE_SUBHEADINGS,
    TABLE_SUBHEADINGS,
)


class TestRenderFigureBlock:
    def test_all_subheadings_present(self):
        fig = FigureEntry(
            number=1, title="Test", image_id="fig1",
            image_link="path/img.png", page=3, caption="Test",
            is_supplementary=False,
        )
        result = render_figure_block(fig)
        for h in FIGURE_SUBHEADINGS:
            assert f"> **{h}**" in result, f"Missing: {h}"
        assert "> ![[path/img.png]]" in result
        assert "> [!note]- Figure 1：" in result

    def test_image_inside_callout_block(self):
        """The image embed must be between the heading and the first sub-heading."""
        fig = FigureEntry(
            number=2, title="Test2", image_id="fig2",
            image_link="img/test.png", page=5, caption="Test2",
            is_supplementary=False,
        )
        result = render_figure_block(fig)
        heading_end = result.index("> ![[img/test.png]]")
        first_sub = result.index(f"> **{FIGURE_SUBHEADINGS[0]}**")
        assert heading_end < first_sub, "Image must appear before first sub-heading"

    def test_no_placeholder_text(self):
        """No '待补充' or '[?]' text in the rendered block."""
        fig = FigureEntry(
            number=3, title="Test3", image_id="fig3",
            image_link="img/fig3.png", page=0, caption="Test3",
            is_supplementary=False,
        )
        result = render_figure_block(fig)
        assert "[?]" not in result
        assert "待补充" not in result


class TestRenderTableBlock:
    def test_all_subheadings_present(self):
        table = TableEntry(
            number=1, image_id="tab1",
            image_link="path/table.png", page=4,
        )
        result = render_table_block(table)
        for h in TABLE_SUBHEADINGS:
            assert f"> **{h}**" in result, f"Missing: {h}"
        assert "> ![[path/table.png]]" in result
        assert "> [!note]- Table 1" in result
