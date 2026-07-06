"""Tests for Layer 4 body/object units, manifest, and body-unit FTS."""

from __future__ import annotations

import json
import sqlite3

from paperforge.retrieval.units import build_body_units, build_object_units, build_unit_id
from paperforge.retrieval.manifest import build_paper_manifest
from paperforge.memory.schema import (
    CREATE_BODY_UNITS,
    CREATE_BODY_UNITS_FTS,
    CREATE_OBJECT_UNITS,
    ensure_schema,
)


def _node(node_id, title, level=2, block_id=None, own_block_ids=None,
           subtree_block_ids=None, children=None, page_span=None):
    return {
        "node_id": node_id,
        "kind": "section",
        "title": title,
        "level": level,
        "block_id": block_id or node_id.split(":")[1],
        "own_block_ids": own_block_ids or [],
        "subtree_block_ids": subtree_block_ids or [],
        "children": children or [],
        "objects": [],
        "page_span": page_span or [1, 1],
    }


def test_build_unit_id_format():
    uid = build_unit_id("ABCD1234", "body", "sec:b1", 1, "b1", 1, "b2")
    assert uid == "ABCD1234:body:sec:b1:1-b1:1-b2"


def test_build_body_units_assigns_stable_ids_and_audit_fields():
    tree = {
        "paper_id": "ABCD1234",
        "nodes": [
            _node("sec:b1", "Methods", own_block_ids=["p1:b2"]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "section_heading", "text": "Methods", "page": 1},
        {"block_id": "b2", "role": "body_paragraph", "text": "We recruited 30 patients.", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert len(units) == 1
    assert units[0]["unit_id"].startswith("ABCD1234:body:")
    assert units[0]["indexable"] is True
    assert units[0]["veto_reason"] == ""
    assert units[0]["section_path"] == "Methods"
    assert units[0]["section_level"] == 2
    assert units[0]["section_title"] == "Methods"
    assert units[0]["part_ordinal"] == 0
    assert "section_path_json" in units[0]


def test_build_body_units_concatenates_multiple_paragraphs():
    tree = {
        "paper_id": "P001",
        "nodes": [
            _node("sec:x", "Results", own_block_ids=["p1:b2", "p1:b3"]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "section_heading", "text": "Results", "page": 1},
        {"block_id": "b2", "role": "body_paragraph", "text": "First result.", "page": 1},
        {"block_id": "b3", "role": "body_paragraph", "text": "Second result.", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert "First result." in units[0]["unit_text"]
    assert "Second result." in units[0]["unit_text"]


def test_build_body_units_marks_empty_as_non_indexable():
    tree = {
        "paper_id": "P002",
        "nodes": [
            _node("sec:empty", "Empty", own_block_ids=[]),
        ],
    }
    blocks = [
        {"block_id": "e1", "role": "section_heading", "text": "Empty", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert units == []  # no own_block_ids with body role → no units


def test_build_body_units_token_estimate():
    tree = {
        "paper_id": "P003",
        "nodes": [
            _node("sec:t1", "Introduction", own_block_ids=["p1:b1"]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "A" * 100, "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert len(units) == 1
    assert units[0]["token_estimate"] == 25  # 100 // 4


def test_build_body_units_empty_tree():
    units = build_body_units(tree={"paper_id": "P004", "nodes": []}, structured_blocks=[])
    assert units == []


def test_body_unit_excludes_reference_item():
    tree = {
        "paper_id": "P005",
        "nodes": [
            _node("sec:body", "Discussion", own_block_ids=["p1:b1", "p1:r1"]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "Main text.", "page": 1},
        {"block_id": "r1", "role": "reference_item", "text": "[1] Smith et al.", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert len(units) == 1
    assert "Main text." in units[0]["unit_text"]
    assert "Smith" not in units[0]["unit_text"]


def test_backmatter_body_creates_separate_unit():
    tree = {
        "paper_id": "P006",
        "nodes": [
            _node("sec:funding", "Funding", own_block_ids=["p1:s1"]),
        ],
    }
    blocks = [
        {"block_id": "s1", "role": "structured_insert", "text": "This work was funded by NIH.", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert len(units) == 1
    assert units[0]["unit_kind"] == "backmatter_body"


def test_mixed_body_and_backmatter_split():
    tree = {
        "paper_id": "P007",
        "nodes": [
            _node("sec:end", "End", own_block_ids=["p1:b1", "p1:s1"]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "Main text.", "page": 1},
        {"block_id": "s1", "role": "structured_insert", "text": "Data available on request.", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    kinds = {u["unit_kind"] for u in units}
    assert "body" in kinds
    assert "backmatter_body" in kinds
    assert len(units) == 2
    assert len({u["unit_id"] for u in units}) == len(units)


def test_token_cap_splits_into_parts():
    tree = {
        "paper_id": "P008",
        "nodes": [
            _node("sec:big", "Long Section", own_block_ids=["p1:b1"]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "word " * 1000, "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert len(units) >= 2  # should be split
    assert units[0]["part_ordinal"] == 1
    assert units[1]["part_ordinal"] == 2
    assert units[0]["section_path"] == units[1]["section_path"]


def test_recursive_walk_produces_correct_section_path():
    tree = {
        "paper_id": "P009",
        "nodes": [
            _node("sec:root", "Root", own_block_ids=["p1:b1"], children=[
                _node("sec:child", "Child", level=3, own_block_ids=["p1:b2"]),
            ]),
        ],
    }
    blocks = [
        {"block_id": "b1", "role": "body_paragraph", "text": "Root text.", "page": 1},
        {"block_id": "b2", "role": "body_paragraph", "text": "Child text.", "page": 1},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    paths = {u["unit_id"]: u["section_path"] for u in units}
    root_unit = [u for u in units if u["section_title"] == "Root"][0]
    child_unit = [u for u in units if u["section_title"] == "Child"][0]
    assert root_unit["section_path"] == "Root"
    assert child_unit["section_path"] == "Root/Child"


def test_build_object_units_from_role_index():
    tree = {
        "paper_id": "P010",
        "nodes": [
            _node("sec:figs", "Figures", own_block_ids=["f2"],
                  subtree_block_ids=["f1", "f2"],
                  page_span=[4, 4]),
        ],
    }
    blocks = [
        {"block_id": "f1", "role": "section_heading", "text": "Figures"},
        {"block_id": "f2", "role": "body_paragraph", "text": "As shown in Figure 1."},
    ]
    role_index = {
        "captions": [
            {"figure_id": "Figure 1", "caption_block_id": "f2", "text": "Figure 1: Results"},
        ]
    }
    units = build_object_units(tree=tree, structured_blocks=blocks, role_index=role_index)
    assert len(units) >= 1
    assert units[0]["object_kind"] == "figure"
    assert units[0]["object_label"] == "Figure 1"
    assert units[0]["caption_text"] == "Figure 1: Results"


def test_build_object_units_empty_role_index():
    tree = {
        "paper_id": "P011",
        "nodes": [
            _node("sec:empty", "Empty", own_block_ids=[]),
        ],
    }
    units = build_object_units(tree=tree, structured_blocks=[], role_index={})
    assert units == []


def test_build_paper_manifest():
    body_units = [
        {"unit_id": "P001:body:sec:1", "paper_id": "P001"},
    ]
    object_units = [
        {"unit_id": "P001:object:sec:1", "paper_id": "P001"},
    ]
    manifest = build_paper_manifest(
        paper_id="P001",
        ocr_result_hash="abc123",
        structure_tree_bytes=b'{"paper_id": "P001", "nodes": []}',
        retrieval_policy_version="l4.body.v1",
        body_units=body_units,
        object_units=object_units,
        source_paths={"structured_blocks": "/some/path.json"},
    )
    assert manifest["paper_id"] == "P001"
    assert manifest["body_unit_count"] == 1
    assert manifest["object_unit_count"] == 1
    assert manifest["ocr_result_hash"] == "abc123"
    assert manifest["retrieval_policy_version"] == "l4.body.v1"
    assert "built_at" in manifest
    assert "structure_tree_hash" in manifest


def test_fts_body_units_table_creation(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_BODY_UNITS)
    conn.execute(CREATE_BODY_UNITS_FTS)
    conn.commit()

    conn.execute(
        """INSERT INTO body_units (unit_id, paper_id, section_path,
           section_path_json, section_level, section_title,
           unit_text, unit_kind, part_ordinal,
           page_span_json, block_span_json, token_estimate,
           indexable, veto_reason, quality_hints_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "P001:body:sec:1",
            "P001",
            "Methods",
            '["Methods"]',
            2,
            "Methods",
            "We recruited 30 patients.",
            "body",
            0,
            json.dumps([1, 1]),
            json.dumps([[1, "b1"], [1, "b2"]]),
            10,
            1,
            "",
            "[]",
        ),
    )
    conn.commit()

    conn.execute(
        """INSERT INTO body_units_fts(rowid, unit_id, paper_id, section_path, unit_text)
           SELECT rowid, unit_id, paper_id, section_path, unit_text FROM body_units"""
    )
    conn.commit()

    results = conn.execute(
        "SELECT unit_id FROM body_units_fts WHERE body_units_fts MATCH ?",
        ("patients",),
    ).fetchall()
    assert len(results) == 1
    assert results[0][0] == "P001:body:sec:1"
    row = conn.execute("SELECT unit_kind FROM body_units WHERE unit_id = ?", ("P001:body:sec:1",)).fetchone()
    assert row["unit_kind"] == "body"
    conn.close()


def test_object_units_table_creation(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute(CREATE_OBJECT_UNITS)
    conn.commit()
    conn.execute(
        """INSERT INTO object_units (unit_id, paper_id, section_path,
           object_kind, object_label, caption_text, nearby_body_text,
           page_span_json, block_span_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "P001:object:sec:1",
            "P001",
            "Figures",
            "figure",
            "Figure 1",
            "Figure 1: Results",
            "As shown in Figure 1.",
            json.dumps([4, 4]),
            json.dumps([[4, "f1"]]),
        ),
    )
    row = conn.execute("SELECT unit_id, object_kind, object_label, caption_text FROM object_units WHERE unit_id = ?",
                       ("P001:object:sec:1",)).fetchone()
    assert row is not None
    assert row["object_kind"] == "figure"
    assert row["object_label"] == "Figure 1"
    assert row["caption_text"] == "Figure 1: Results"
    conn.close()


def test_ensure_schema_includes_new_tables(tmp_path):
    db = tmp_path / "test_schema.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    ensure_schema(conn)

    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "body_units" in tables
    assert "body_units_fts" in tables
    assert "object_units" in tables

    fts_tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts%'").fetchall()]
    assert "body_units_fts" in fts_tables
    conn.close()


def test_body_units_schema_includes_v4_columns(tmp_path):
    db = tmp_path / "test_schema_body_units.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    ensure_schema(conn)

    cols = {
        r[1] for r in conn.execute("PRAGMA table_info(body_units)").fetchall()
    }
    assert "unit_kind" in cols
    assert "section_path_json" in cols
    assert "section_level" in cols
    assert "section_title" in cols
    assert "part_ordinal" in cols
    conn.close()


def test_object_units_schema_includes_new_columns(tmp_path):
    db = tmp_path / "test_schema_obj_units.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    ensure_schema(conn)

    cols = {
        r[1] for r in conn.execute("PRAGMA table_info(object_units)").fetchall()
    }
    for col in ("object_kind", "object_label", "caption_text", "nearby_body_text"):
        assert col in cols, f"object_units missing {col} column"
    assert "object_role" not in cols, "object_units should not have legacy object_role column"
    conn.close()
