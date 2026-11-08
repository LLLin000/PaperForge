from __future__ import annotations

from pathlib import Path


def test_audit_table_html_metrics() -> None:
    from scripts.dev.table_structure_audit import audit_table_html

    html = """<table><tr><th rowspan="2">Group</th><th colspan="2">Value</th></tr>
    <tr><td>p=0.036</td><td>n/10^4 μm^2</td></tr>
    <tr><td>12</td><td>0.5</td><td>Control</td></tr></table>"""
    result = audit_table_html(html)
    assert result == {
        "html_present": True,
        "html_parse_errors": 0,
        "rows": 3,
        "max_columns": 3,
        "header_rows_heur": 1,
        "cells_with_rowspan": 1,
        "cells_with_colspan": 1,
        "numeric_cell_ratio": 2 / 7,
        "cells_with_pvalue": 1,
        "cells_with_unit": 1,
    }


def test_audit_table_html_handles_malformed_input() -> None:
    from scripts.dev.table_structure_audit import audit_table_html

    result = audit_table_html("<table><tr><th>A<td>1</tr><tr><td>2</table>")
    assert result["html_present"] is True
    assert result["html_parse_errors"] > 0
    assert result["rows"] == 2
    assert result["max_columns"] == 2
    assert result["numeric_cell_ratio"] == 2 / 3



def test_header_row_heuristic_recognizes_paddleocr_td_headers() -> None:
    from scripts.dev.table_structure_audit import audit_table_html

    result = audit_table_html(
        "<table><tr><td>Group</td><td>Outcome</td></tr>"
        "<tr><td>Treatment</td><td>12</td></tr>"
        "<tr><td>Control</td><td>8</td></tr></table>"
    )
    assert result["header_rows_heur"] == 1


def test_caption_comparison_ignores_math_spacing() -> None:
    from scripts.dev.table_structure_audit import _caption_matches

    assert _caption_matches(
        "Table 1 Data at $ \\sim $37 $ ^{\\circ} $C",
        "## Caption\nTable 1 Data at $\\sim$ 37 $^{\\circ}$C\n",
    )

def test_rendered_table_markdown_does_not_emit_html_or_structured_table() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown
    from scripts.dev.table_structure_audit import _MD_TABLE_ROW, _TAG

    markdown = render_table_object_markdown({
        "table_id": "table_001",
        "caption": "Table 1. Results.",
        "image_relpath": "assets/tables/table_001.jpg",
    })
    assert "Table 1. Results." in markdown
    assert "![](../../assets/tables/table_001.jpg)" in markdown
    assert _TAG.search(markdown) is None
    assert _MD_TABLE_ROW.search(markdown) is None


def test_audit_paper_compares_rendered_markdown(tmp_path: Path) -> None:
    import json

    from scripts.dev.table_structure_audit import audit_paper

    (tmp_path / "structure").mkdir()
    (tmp_path / "render" / "tables").mkdir(parents=True)
    (tmp_path / "structure" / "table_inventory.json").write_text(json.dumps({
        "tables": [{
            "table_id": "table_001",
            "caption_text": "Table 1. Results.",
            "assistive_text": "<table><tr><td>12</td></tr></table>",
            "truth_source": "image",
            "note_block_ids": ["n1"],
        }]
    }), encoding="utf-8")
    (tmp_path / "render" / "tables" / "table_001.md").write_text(
        "![[assets/tables/table_001.jpg]]\n\nTable 1. Results.\n", encoding="utf-8"
    )
    result = audit_paper(tmp_path)
    assert result["tables_total"] == 1
    assert result["html_present"] == 1
    assert result["truth_source_distribution"] == {"image": 1}
    assert result["markdown_contains_image"] == 1
    assert result["markdown_contains_caption"] == 1
    assert result["markdown_emits_html_or_structured_content"] == 0
