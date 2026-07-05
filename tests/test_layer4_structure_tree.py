"""Tests for Layer 4 structure tree builder and paper navigation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from paperforge.retrieval.structure_tree import (
    build_structure_tree,
    summarize_role_index,
    write_structure_tree,
)


def test_build_structure_tree_creates_section_nodes_from_headings():
    structured_blocks = [
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b1", "role": "section_heading", "text": "Methods"},
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b2", "role": "body_paragraph", "text": "We recruited 30 patients."},
    ]
    tree = build_structure_tree(structured_blocks)
    assert tree["paper_id"] == "ABCD1234"
    assert len(tree["nodes"]) == 1
    assert tree["nodes"][0]["title"] == "Methods"
    assert tree["nodes"][0]["section_path"] == ["Methods"]
    assert tree["nodes"][0]["level"] == 1
    assert tree["nodes"][0]["page_span"] == [1, 1]


def test_build_structure_tree_handles_subsection():
    structured_blocks = [
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b1", "role": "section_heading", "text": "Methods"},
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b2", "role": "body_paragraph", "text": "We recruited 30 patients."},
        {"paper_id": "ABCD1234", "page": 2, "block_id": "b3", "role": "subsection_heading", "text": "Statistical Analysis"},
        {"paper_id": "ABCD1234", "page": 2, "block_id": "b4", "role": "body_paragraph", "text": "We used t-tests."},
    ]
    tree = build_structure_tree(structured_blocks)
    assert tree["paper_id"] == "ABCD1234"
    assert len(tree["nodes"]) == 2
    assert tree["nodes"][1]["title"] == "Statistical Analysis"
    assert tree["nodes"][1]["level"] == 2
    assert tree["nodes"][1]["section_path"] == ["Methods", "Statistical Analysis"]


def test_build_structure_tree_extends_page_span():
    structured_blocks = [
        {"paper_id": "X", "page": 1, "block_id": "s1", "role": "section_heading", "text": "Introduction"},
        {"paper_id": "X", "page": 1, "block_id": "p1", "role": "body_paragraph", "text": "Para 1"},
        {"paper_id": "X", "page": 2, "block_id": "p2", "role": "body_paragraph", "text": "Para 2"},
        {"paper_id": "X", "page": 3, "block_id": "p3", "role": "body_paragraph", "text": "Para 3"},
    ]
    tree = build_structure_tree(structured_blocks)
    assert tree["nodes"][0]["page_span"] == [1, 3]


def test_build_structure_tree_handles_introduction_and_abstract_headings():
    blocks = [
        {"paper_id": "Y", "page": 1, "block_id": "a1", "role": "abstract_heading", "text": "Abstract"},
        {"paper_id": "Y", "page": 1, "block_id": "b1", "role": "abstract_body", "text": "Summary here."},
        {"paper_id": "Y", "page": 1, "block_id": "i1", "role": "introduction_heading", "text": "Introduction"},
        {"paper_id": "Y", "page": 2, "block_id": "b2", "role": "body_paragraph", "text": "Background."},
    ]
    tree = build_structure_tree(blocks)
    assert len(tree["nodes"]) == 2
    assert tree["nodes"][0]["title"] == "Abstract"
    assert tree["nodes"][1]["title"] == "Introduction"
    assert tree["nodes"][0]["kind"] == "section"


def test_build_structure_tree_ignores_heading_roles_with_empty_text():
    blocks = [
        {"paper_id": "Z", "page": 1, "block_id": "h1", "role": "section_heading", "text": ""},
        {"paper_id": "Z", "page": 1, "block_id": "b1", "role": "body_paragraph", "text": "Some text."},
    ]
    tree = build_structure_tree(blocks)
    assert len(tree["nodes"]) == 0


def test_build_structure_tree_empty_input():
    tree = build_structure_tree([])
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


def test_build_structure_tree_block_span_accumulates():
    blocks = [
        {"paper_id": "P", "page": 1, "block_id": "sec1", "role": "section_heading", "text": "Results"},
        {"paper_id": "P", "page": 1, "block_id": "r1", "role": "body_paragraph", "text": "Result A"},
        {"paper_id": "P", "page": 2, "block_id": "r2", "role": "body_paragraph", "text": "Result B"},
    ]
    tree = build_structure_tree(blocks)
    assert len(tree["nodes"][0]["block_span"]) == 3
    assert [1, "sec1"] in tree["nodes"][0]["block_span"]
    assert [2, "r2"] in tree["nodes"][0]["block_span"]
