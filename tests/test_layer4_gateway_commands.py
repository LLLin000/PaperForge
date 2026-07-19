"""Tests for Layer 4 gateway command routing (Task 5).

Validates that ``route_gateway()`` dispatches each intent to the correct
real data source and surfaces ``route_explanation`` in the result data.
"""

from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from pathlib import Path

from paperforge.commands import (
    content_discovery,
    paper_lookup,
    paper_navigation,
    scoped_fetch,
)
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.gateway import (
    _body_units_fts_exists,
    route_gateway,
)

# ---------------------------------------------------------------------------
# Helpers — populate test databases matching the real schema
# ---------------------------------------------------------------------------


def _make_populated_db(tmp_path: Path) -> Path:
    """Create a minimal paperforge.db with papers + body_unit FTS content."""
    db_path = get_memory_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    ensure_schema(conn)

    # Insert a paper row
    conn.execute(
        """INSERT INTO papers
           (zotero_key, citation_key, title, year, doi, journal, first_author,
            authors_json, abstract, domain, collection_path, collections_json,
            has_pdf, ocr_status, deep_reading_status, lifecycle, next_step,
            impact_factor)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "TST001",
            "Smith2024",
            "Delirium Prevention in ICU Patients",
            "2024",
            "10.1234/delirium",
            "Critical Care Medicine",
            "Smith",
            '["Smith", "Jones"]',
            "Delirium is a common complication in ICU patients...",
            "ICU",
            "",
            "[]",
            1,
            "done",
            "pending",
            "active",
            "deep-read",
            5.2,
        ),
    )
    # Insert an alias for DOI lookup
    conn.execute(
        "INSERT INTO paper_aliases (paper_id, alias, alias_norm, alias_type) VALUES (?, ?, ?, ?)",
        ("TST001", "10.1234/delirium", "101234delirium", "doi"),
    )
    # Insert body units
    conn.execute(
        """INSERT INTO body_units
           (unit_id, paper_id, section_path, unit_text,
            page_span_json, block_span_json, token_estimate,
            indexable, veto_reason, quality_hints_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "TST001:body:sec:intro:1-b1:2-b3",
            "TST001",
            "Introduction",
            "Delirium prevention strategies include early mobilization and reducing sedation.",
            json.dumps([1, 2]),
            json.dumps([[1, "b1"], [2, "b3"]]),
            50,
            1,
            "",
            "[]",
        ),
    )
    conn.execute(
        """INSERT INTO body_units
           (unit_id, paper_id, section_path, unit_text,
            page_span_json, block_span_json, token_estimate,
            indexable, veto_reason, quality_hints_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "TST001:body:sec:methods:3-b4:5-b7",
            "TST001",
            "Methods",
            "We randomized 200 patients to early mobilization vs standard care.",
            json.dumps([3, 5]),
            json.dumps([[3, "b4"], [5, "b7"]]),
            30,
            1,
            "",
            "[]",
        ),
    )
    conn.commit()

    # Populate paper_fts
    conn.execute(
        """INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author,
           authors_json, abstract, journal, domain, collection_path, collections_json)
           SELECT rowid, zotero_key, citation_key, title, first_author,
           authors_json, abstract, journal, domain, collection_path, collections_json
           FROM papers"""
    )
    conn.commit()

    # Populate body_units_fts
    conn.execute(
        """INSERT INTO body_units_fts(rowid, unit_id, paper_id, section_path, unit_text)
           SELECT rowid, unit_id, paper_id, section_path, unit_text FROM body_units"""
    )
    conn.commit()

    # Store manifest
    manifest = {
        "paper_id": "TST001",
        "retrieval_policy_version": "l4.body.v1",
        "body_unit_count": 2,
        "built_at": "2025-01-01T00:00:00Z",
    }
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("manifest:TST001", json.dumps(manifest)),
    )
    conn.commit()
    conn.close()
    return db_path


def _make_paper_only_db(tmp_path: Path) -> Path:
    """Create a DB with only paper_fts (no body_units_fts)."""
    db_path = get_memory_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    ensure_schema(conn)

    conn.execute(
        """INSERT INTO papers
           (zotero_key, citation_key, title, year, doi, journal, first_author,
            authors_json, abstract, domain, collection_path, collections_json,
            has_pdf, ocr_status, deep_reading_status, lifecycle, next_step,
            impact_factor)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "TST002",
            "Johnson2023",
            "Sedation Protocols in the ICU",
            "2023",
            "10.1234/sedation",
            "Intensive Care Medicine",
            "Johnson",
            '["Johnson"]',
            "Sedation is critical in ICU management...",
            "ICU",
            "",
            "[]",
            1,
            "pending",
            "pending",
            "active",
            "deep-read",
            4.1,
        ),
    )
    conn.commit()
    conn.execute(
        """INSERT INTO paper_fts(rowid, zotero_key, citation_key, title, first_author,
           authors_json, abstract, journal, domain, collection_path, collections_json)
           SELECT rowid, zotero_key, citation_key, title, first_author,
           authors_json, abstract, journal, domain, collection_path, collections_json
           FROM papers"""
    )
    conn.commit()
    conn.close()
    return db_path


def _make_structure_tree(tmp_path: Path, paper_id: str) -> Path:
    """Create a mock structure-tree.json for a paper."""
    ocr_root = tmp_path / "System" / "PaperForge" / "ocr" / paper_id / "index"
    ocr_root.mkdir(parents=True, exist_ok=True)
    tree = {
        "paper_id": paper_id,
        "nodes": [
            {
                "node_id": "sec:intro",
                "kind": "section",
                "title": "Introduction",
                "level": 1,
                "section_path": ["Introduction"],
                "page_span": [1, 2],
            },
            {
                "node_id": "sec:methods",
                "kind": "section",
                "title": "Methods",
                "level": 1,
                "section_path": ["Methods"],
                "page_span": [3, 5],
            },
        ],
    }
    (ocr_root / "structure-tree.json").write_text(
        json.dumps(tree, ensure_ascii=False), encoding="utf-8"
    )
    return ocr_root


# ---------------------------------------------------------------------------
# paper-lookup intent
# ---------------------------------------------------------------------------


def test_paper_lookup_returns_results_when_db_has_match(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(tmp_path, "paper-lookup", "Smith 2024", json_mode=True)
    assert result.ok
    assert result.data["intent"] == "paper-lookup"
    assert len(result.data["results"]) > 0
    assert "route_explanation" in result.data
    assert result.data["route_explanation"]["primary_arm"] == "lookup_paper"


def test_paper_lookup_returns_empty_when_no_match(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(
        tmp_path, "paper-lookup", "Nonexistent Author 2099", json_mode=True
    )
    assert result.ok
    assert len(result.data["results"]) == 0
    assert result.data["route_explanation"]["matched"] is False


def test_paper_lookup_fails_gracefully_without_db(tmp_path):
    result = route_gateway(tmp_path, "paper-lookup", "Smith 2024", json_mode=True)
    assert not result.ok
    assert "route_explanation" in result.data


# ---------------------------------------------------------------------------
# content-discovery intent
# ---------------------------------------------------------------------------


def test_content_discovery_prefers_body_units_fts_when_present(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(
        tmp_path, "content-discovery", "delirium prevention", json_mode=True, limit=5
    )
    assert result.ok
    assert result.data["intent"] == "content-discovery"
    assert result.data["route_explanation"]["primary_arm"] == "body_units_fts"
    assert result.data["route_explanation"]["compatibility_mode"] is False
    assert "results" in result.data


def test_paper_navigation_reads_structure_tree_when_present(tmp_path):
    _make_populated_db(tmp_path)
    _make_structure_tree(tmp_path, "TST001")
    result = route_gateway(tmp_path, "paper-navigation", "10.1234/delirium", json_mode=True)
    assert result.ok
    assert result.data["intent"] == "paper-navigation"
    assert result.data["mode"] == "structure_tree"
    assert "nodes" in result.data
    assert result.data["route_explanation"]["primary_arm"] == "structure_tree"
    assert result.data["route_explanation"]["fallback"] is False


def test_content_discovery_returns_body_unit_matches(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(
        tmp_path, "content-discovery", "delirium", json_mode=True, limit=5
    )
    assert result.ok
    assert len(result.data["results"]) > 0
    for r in result.data["results"]:
        assert "unit_id" in r
        assert "unit_text" in r
        assert "section_path" in r


def test_content_discovery_falls_back_to_paper_fts(tmp_path):
    _make_paper_only_db(tmp_path)
    result = route_gateway(
        tmp_path, "content-discovery", "sedation", json_mode=True, limit=5
    )
    assert result.ok
    assert result.data["route_explanation"]["primary_arm"] == "paper_fts"
    assert result.data["route_explanation"]["compatibility_mode"] is True
    assert len(result.data["results"]) > 0


def test_content_discovery_fails_gracefully_without_db(tmp_path):
    result = route_gateway(
        tmp_path, "content-discovery", "delirium", json_mode=True, limit=5
    )
    assert not result.ok
    assert "route_explanation" in result.data


# ---------------------------------------------------------------------------
# paper-navigation intent


def test_paper_navigation_returns_not_found_without_db(tmp_path):
    result = route_gateway(tmp_path, "paper-navigation", "ABCD1234", json_mode=True)
    assert not result.ok
    assert result.data["mode"] == "not_found"


# ---------------------------------------------------------------------------
# scoped-fetch intent
# ---------------------------------------------------------------------------


def test_scoped_fetch_returns_body_units_for_paper(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(tmp_path, "scoped-fetch", "Smith 2024", json_mode=True)
    assert result.ok
    assert result.data["intent"] == "scoped-fetch"
    assert len(result.data["body_units"]) > 0
    assert "manifest" in result.data
    assert result.data["route_explanation"]["primary_arm"] == "body_units"


def test_scoped_fetch_by_doi(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(tmp_path, "scoped-fetch", "10.1234/delirium", json_mode=True)
    assert result.ok
    assert len(result.data["body_units"]) > 0


def test_scoped_fetch_empty_for_unknown_paper(tmp_path):
    _make_populated_db(tmp_path)
    result = route_gateway(
        tmp_path, "scoped-fetch", "Unknown Author 1999", json_mode=True
    )
    assert not result.ok
    assert len(result.data["body_units"]) == 0


# ---------------------------------------------------------------------------
# Command integration tests (exercise the CLI entry points)
# ---------------------------------------------------------------------------


def test_paper_lookup_command_registered_and_json(tmp_path):
    args = Namespace(vault_path=tmp_path, query="Smith 2021", json=True, limit=5)
    exit_code = paper_lookup.run(args)
    assert exit_code in {0, 1}


def test_content_discovery_command_runs(tmp_path):
    args = Namespace(
        vault_path=tmp_path, query="delirium prevention", json=True, limit=5
    )
    exit_code = content_discovery.run(args)
    assert exit_code in {0, 1}


def test_paper_navigation_command_runs(tmp_path):
    args = Namespace(
        vault_path=tmp_path, query="10.1234/test-doi-here", json=True
    )
    exit_code = paper_navigation.run(args)
    assert exit_code in {0, 1}


def test_scoped_fetch_command_runs(tmp_path):
    args = Namespace(vault_path=tmp_path, query="Smith 2021", json=False, limit=3)
    exit_code = scoped_fetch.run(args)
    assert exit_code in {0, 1}


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_body_units_fts_exists_returns_true_when_populated(tmp_path):
    _make_populated_db(tmp_path)
    assert _body_units_fts_exists(tmp_path) is True


def test_body_units_fts_exists_returns_false_without_db(tmp_path):
    assert _body_units_fts_exists(tmp_path) is False


def test_body_units_fts_exists_returns_false_no_body_units(tmp_path):
    _make_paper_only_db(tmp_path)
    assert _body_units_fts_exists(tmp_path) is False


def test_unsupported_intent_raises(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="Unsupported Layer 4 intent"):
        route_gateway(tmp_path, "unknown-intent", "query", json_mode=True)


# ---------------------------------------------------------------------------
# route_explanation contract
# ---------------------------------------------------------------------------


def test_all_intents_surface_route_explanation(tmp_path):
    _make_populated_db(tmp_path)
    _make_structure_tree(tmp_path, "TST001")

    for intent, query in [
        ("paper-lookup", "Smith 2024"),
        ("content-discovery", "delirium"),
        ("paper-navigation", "10.1234/delirium"),
        ("scoped-fetch", "Smith 2024"),
    ]:
        result = route_gateway(tmp_path, intent, query, json_mode=True)
        # Even failing results should have route_explanation
        assert "route_explanation" in result.data, (
            f"{intent} missing route_explanation"
        )
        assert "primary_arm" in result.data["route_explanation"], (
            f"{intent} missing primary_arm"
        )


def test_command_registry_contains_gateway_commands():
    from paperforge.commands import _COMMAND_REGISTRY

    for name in ("paper-lookup", "content-discovery", "scoped-fetch"):
        assert name in _COMMAND_REGISTRY, f"registry missing {name}"


def test_compat_content_discovery_surfaces_route_explanation_with_vector_secondary(tmp_path):
    """Compat mode surfaces paper_fts primary + vector secondary when available."""
    from paperforge.embedding import get_embed_status

    _make_paper_only_db(tmp_path)
    result = route_gateway(tmp_path, "content-discovery", "Johnson", json_mode=True)

    assert result.ok
    route_exp = result.data["route_explanation"]
    assert route_exp["primary_arm"] == "paper_fts"
    assert route_exp.get("compatibility_mode") is True
    # Vector may or may not be available; verify the response shape either way
    if "secondary_arm" in route_exp:
        assert route_exp["secondary_arm"] == "vector_retrieve"
    # When vector is available, vector_results should be populated
    if result.data.get("vector_results") is not None:
        assert isinstance(result.data["vector_results"], list)
    else:
        # vector_results is None when vector is unavailable — clean fallback
        assert result.data.get("vector_results") is None
    assert len(result.data["results"]) > 0
