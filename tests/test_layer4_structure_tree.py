"""Tests for Layer 4 structure tree builder using heading_events + emitted_block_events."""

from __future__ import annotations

from paperforge.retrieval.structure_tree import (
    build_structure_tree,
    summarize_role_index,
    write_structure_tree,
)


def _h(emitted_order, markdown_level, title, page=1, block_id=None):
    return {
        "line_number": emitted_order * 10,
        "markdown_level": markdown_level,
        "title": title,
        "page": page,
        "block_id": block_id or f"h_{emitted_order}",
        "emitted_order": emitted_order,
    }


def _e(emitted_order, block_id, role="body_paragraph", page=1, emitted_as="body"):
    return {
        "emitted_order": emitted_order,
        "line_start": emitted_order * 10,
        "line_end": emitted_order * 10 + 5,
        "page": page,
        "block_id": block_id,
        "role": role,
        "emitted_as": emitted_as,
    }


def test_single_heading_with_body():
    heading_events = [_h(0, 2, "Methods", block_id="b1")]
    emitted = [_e(0, "b1"), _e(1, "b2")]
    structured = [{"paper_id": "ABCD1234"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    assert tree["paper_id"] == "ABCD1234"
    assert len(tree["nodes"]) == 1
    n = tree["nodes"][0]
    assert n["title"] == "Methods"
    assert n["level"] == 2
    assert n["block_id"] == "b1"
    assert set(n["subtree_block_ids"]) == {"b1", "b2"}
    assert n["own_block_ids"] == ["b2"]


def test_h2_h3_nesting():
    heading_events = [
        _h(0, 2, "Methods", block_id="b1"),
        _h(2, 3, "Statistics", block_id="b3"),
    ]
    emitted = [_e(0, "b1"), _e(1, "b2"), _e(2, "b3"), _e(3, "b4")]
    structured = [{"paper_id": "P001"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    assert len(tree["nodes"]) == 1
    parent = tree["nodes"][0]
    child = parent["children"][0]
    assert parent["title"] == "Methods"
    assert child["title"] == "Statistics"
    assert parent["own_block_ids"] == ["b2"]
    assert child["own_block_ids"] == ["b4"]


def test_h2_h3_h2_sibling():
    heading_events = [
        _h(0, 2, "Methods", block_id="b1"),
        _h(2, 3, "Statistics", block_id="b3"),
        _h(4, 2, "Results", block_id="b5"),
    ]
    emitted = [
        _e(0, "b1"), _e(1, "b2"),
        _e(2, "b3"), _e(3, "b4"),
        _e(4, "b5"), _e(5, "b6"),
    ]
    structured = [{"paper_id": "P002"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    assert len(tree["nodes"]) == 2
    assert tree["nodes"][0]["title"] == "Methods"
    assert tree["nodes"][1]["title"] == "Results"
    assert len(tree["nodes"][0]["children"]) == 1


def test_page_span_extended_from_emitted_blocks():
    heading_events = [_h(0, 2, "Intro", page=1, block_id="b1")]
    emitted = [_e(0, "b1", page=1), _e(1, "b2", page=2), _e(2, "b3", page=3)]
    structured = [{"paper_id": "P003"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    assert tree["nodes"][0]["page_span"] == [1, 3]


def test_empty_heading_events():
    tree = build_structure_tree([], [], [])
    assert tree["paper_id"] == ""
    assert tree["nodes"] == []


def test_write_structure_tree_creates_file(tmp_path):
    tree = {"paper_id": "X", "nodes": []}
    write_structure_tree(tmp_path, tree)
    target = tmp_path / "structure-tree.json"
    assert target.exists()
    import json
    assert json.loads(target.read_text(encoding="utf-8")) == tree


def test_summarize_role_index_counts_roles():
    role_index = {
        "headings": [{"paper_id": "X"}, {"paper_id": "X"}],
        "body_paragraphs": [{"paper_id": "X"} for _ in range(5)],
        "figure_captions": [{"paper_id": "X"}],
    }
    summary = summarize_role_index(role_index)
    assert summary["role_counts"]["headings"] == 2
    assert summary["role_counts"]["body_paragraphs"] == 5
    assert summary["role_counts"]["figure_captions"] == 1


def test_own_block_ids_excludes_children():
    heading_events = [
        _h(0, 2, "Discussion", block_id="d1"),
        _h(2, 3, "Limitation", block_id="d3"),
    ]
    emitted = [_e(0, "d1"), _e(1, "d2"), _e(2, "d3"), _e(3, "d4")]
    structured = [{"paper_id": "P004"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    parent = tree["nodes"][0]
    child = parent["children"][0]
    assert parent["own_block_ids"] == ["d2"]
    assert child["own_block_ids"] == ["d4"]
    assert parent["subtree_block_ids"] == ["d1", "d2", "d3", "d4"]
    assert child["subtree_block_ids"] == ["d3", "d4"]


def test_summary_in_last_child_scope():
    """Summary after last child falls within child's scope (no boundary)."""
    heading_events = [
        _h(0, 2, "Discussion", block_id="d1"),
        _h(2, 3, "Mechanism", block_id="d3"),
    ]
    emitted = [
        _e(0, "d1"), _e(1, "d2"),
        _e(2, "d3"), _e(3, "d4"), _e(4, "d5"),
    ]
    structured = [{"paper_id": "P005"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    parent = tree["nodes"][0]
    child = parent["children"][0]
    assert parent["own_block_ids"] == ["d2"]
    assert child["own_block_ids"] == ["d4", "d5"]


def test_rendered_order_differs_from_structured_order():
    heading_events = [_h(1, 2, "Results", block_id="b1")]
    emitted = [_e(0, "b3", page=1), _e(1, "b1", page=1), _e(2, "b2", page=1)]
    structured = [{"paper_id": "P006"}]
    tree = build_structure_tree(heading_events, emitted, structured)
    assert "b3" not in tree["nodes"][0]["subtree_block_ids"]
    assert "b1" in tree["nodes"][0]["subtree_block_ids"]
    assert "b2" in tree["nodes"][0]["subtree_block_ids"]
