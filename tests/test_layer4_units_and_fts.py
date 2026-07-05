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


def test_build_unit_id_format():
    uid = build_unit_id("ABCD1234", "body", "sec:b1", 1, "b1", 1, "b2")
    assert uid == "ABCD1234:body:sec:b1:1-b1:1-b2"


def test_build_body_units_assigns_stable_ids_and_audit_fields():
    tree = {
        "paper_id": "ABCD1234",
        "nodes": [
            {
                "node_id": "sec:b1",
                "title": "Methods",
                "section_path": ["Methods"],
                "page_span": [1, 1],
                "block_span": [[1, "b1"], [1, "b2"]],
            }
        ],
    }
    blocks = [
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b1", "role": "section_heading", "text": "Methods"},
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b2", "role": "body_paragraph", "text": "We recruited 30 patients."},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert units[0]["unit_id"].startswith("ABCD1234:body:")
    assert units[0]["indexable"] is True
    assert units[0]["veto_reason"] == ""


def test_build_body_units_concatenates_multiple_paragraphs():
    tree = {
        "paper_id": "P001",
        "nodes": [
            {
                "node_id": "sec:x",
                "title": "Results",
                "section_path": ["Results"],
                "page_span": [2, 2],
                "block_span": [[2, "b1"], [2, "b2"], [2, "b3"]],
            }
        ],
    }
    blocks = [
        {"paper_id": "P001", "page": 2, "block_id": "b1", "role": "section_heading", "text": "Results"},
        {"paper_id": "P001", "page": 2, "block_id": "b2", "role": "body_paragraph", "text": "First result."},
        {"paper_id": "P001", "page": 2, "block_id": "b3", "role": "body_paragraph", "text": "Second result."},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert "First result." in units[0]["unit_text"]
    assert "Second result." in units[0]["unit_text"]


def test_build_body_units_marks_empty_as_non_indexable():
    tree = {
        "paper_id": "P002",
        "nodes": [
            {
                "node_id": "sec:empty",
                "title": "Empty",
                "section_path": ["Empty"],
                "page_span": [3, 3],
                "block_span": [[3, "e1"]],
            }
        ],
    }
    blocks = [
        {"paper_id": "P002", "page": 3, "block_id": "e1", "role": "section_heading", "text": "Empty"},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert units[0]["indexable"] is False
    assert units[0]["veto_reason"] == "empty"


def test_build_body_units_token_estimate():
    tree = {
        "paper_id": "P003",
        "nodes": [
            {
                "node_id": "sec:t1",
                "title": "Introduction",
                "section_path": ["Introduction"],
                "page_span": [1, 1],
                "block_span": [[1, "b1"]],
            }
        ],
    }
    blocks = [
        {"paper_id": "P003", "page": 1, "block_id": "b1", "role": "body_paragraph", "text": "A" * 100},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert units[0]["token_estimate"] == 25  # 100 // 4


def test_build_body_units_empty_tree():
    units = build_body_units(tree={"paper_id": "P004", "nodes": []}, structured_blocks=[])
    assert units == []


def test_build_object_units_from_role_index():
    tree = {
        "paper_id": "P010",
        "nodes": [
            {
                "node_id": "sec:figs",
                "title": "Figures",
                "section_path": ["Figures"],
                "page_span": [4, 4],
                "block_span": [[4, "f1"], [4, "f2"]],
            }
        ],
    }
    blocks = [
        {"paper_id": "P010", "page": 4, "block_id": "f1", "role": "section_heading", "text": "Figures"},
        {"paper_id": "P010", "page": 4, "block_id": "f2", "role": "body_paragraph", "text": "As shown in Figure 1."},
    ]
    role_index = {
        "figure_captions": [
            {"page": 4, "block_id": "f2", "text": "Figure 1: Results", "role": "figure_caption"},
        ]
    }
    units = build_object_units(tree=tree, structured_blocks=blocks, role_index=role_index)
    assert len(units) >= 1
    assert units[0]["unit_id"].startswith("P010:object:")
    assert units[0]["object_kind"] == "figure"
    assert units[0]["object_label"] == "Figure 1"
    assert units[0]["caption_text"] == "Figure 1: Results"
    assert "As shown in Figure 1." in units[0]["nearby_body_text"]


def test_build_object_units_empty_role_index():
    tree = {
        "paper_id": "P011",
        "nodes": [
            {
                "node_id": "sec:empty",
                "title": "Empty",
                "section_path": ["Empty"],
                "page_span": [5, 5],
                "block_span": [[5, "e1"]],
            }
        ],
    }
    units = build_object_units(tree=tree, structured_blocks=[], role_index={})
    assert units == []


def test_build_paper_manifest():
    body_units = [
        {"unit_id": "P001:body:sec:1:1-b1:1-b2", "paper_id": "P001"},
    ]
    object_units = [
        {"unit_id": "P001:object:sec:1:1-f1:1-f1", "paper_id": "P001"},
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

    # Insert a row and let FTS index it
    conn.execute(
        """INSERT INTO body_units (unit_id, paper_id, section_path, unit_text,
           page_span_json, block_span_json, token_estimate, indexable, veto_reason, quality_hints_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "P001:body:sec:1:1-b1:1-b2",
            "P001",
            "Methods",
            "We recruited 30 patients.",
            json.dumps([1, 1]),
            json.dumps([[1, "b1"], [1, "b2"]]),
            10,
            1,
            "",
            "[]",
        ),
    )
    conn.commit()

    # Manually populate FTS (no trigger yet)
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
    assert results[0][0] == "P001:body:sec:1:1-b1:1-b2"
    # Verify unit_kind was set via DEFAULT
    row = conn.execute("SELECT unit_kind FROM body_units WHERE unit_id = ?", ("P001:body:sec:1:1-b1:1-b2",)).fetchone()
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
            "P001:object:sec:1:1-f1:1-f1",
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
    row = conn.execute("SELECT unit_id, object_kind, object_label, caption_text FROM object_units WHERE unit_id = ?", ("P001:object:sec:1:1-f1:1-f1",)).fetchone()
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


def test_body_units_schema_includes_unit_kind(tmp_path):
    db = tmp_path / "test_schema_body_units.db"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    ensure_schema(conn)

    cols = {
        r[1] for r in conn.execute("PRAGMA table_info(body_units)").fetchall()
    }
    assert "unit_kind" in cols, "body_units missing unit_kind column"
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
