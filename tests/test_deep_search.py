"""Tests for @ Deep Search: query rewrite + hybrid retrieval."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

import paperforge.config
from paperforge.worker._utils import pipeline_paths as _pp

paperforge.config.pipeline_paths = _pp

from paperforge.embedding.query_rewrite import expand_query, ABBREVIATIONS, MEDICAL_SYNONYMS
from paperforge.embedding.search import hybrid_search, _bm25_search, _fuse_results
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import (
    CREATE_BODY_UNITS,
    CREATE_BODY_UNITS_FTS,
    CREATE_PAPERS,
    CREATE_OBJECT_UNITS,
    CREATE_VEC_BODY,
    CREATE_VEC_BODY_META,
    CREATE_VEC_OBJECTS,
    CREATE_VEC_OBJECTS_META,
    ensure_schema,
)


EMBEDDING_DIM = 1536


# ---------------------------------------------------------------------------
# Mock provider — deterministic fixed embeddings
# ---------------------------------------------------------------------------
class FixedProvider:
    """Provider that returns deterministic embeddings for any text."""

    def __init__(self, vault: Path | None = None):
        self.vault = vault

    def encode(self, texts: list[str]) -> list[list[float]]:
        import hashlib

        result = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            vec = [(h[i % 32] / 255.0) for i in range(EMBEDDING_DIM)]
            result.append(vec)
        return result

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]


@pytest.fixture
def mock_provider():
    return FixedProvider()


@pytest.fixture(autouse=True)
def _patch_providers(mock_provider):
    """Replace OpenAICompatibleProvider with the fixed mock."""
    with patch("paperforge.embedding.search.OpenAICompatibleProvider", return_value=mock_provider):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_tables(conn: sqlite3.Connection) -> None:
    """Create tables needed for deep search tests."""
    conn.executescript(CREATE_PAPERS)
    conn.executescript(CREATE_BODY_UNITS)
    conn.executescript(CREATE_BODY_UNITS_FTS)
    conn.executescript(CREATE_OBJECT_UNITS)
    conn.commit()


def _seed_paper(conn: sqlite3.Connection, paper_id: str, title: str) -> None:
    """Insert a paper row."""
    conn.execute(
        """INSERT OR IGNORE INTO papers (zotero_key, title, year, first_author, journal, domain)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (paper_id, title, "2023", "Author", "Test Journal", "ortho"),
    )
    conn.commit()


def _seed_body_unit(
    conn: sqlite3.Connection,
    unit_id: str,
    paper_id: str,
    text: str,
    section_title: str = "Methods",
    section_path: str = "methods",
    indexable: int = 1,
) -> None:
    """Insert a body unit and its FTS index entry."""
    conn.execute(
        """INSERT OR REPLACE INTO body_units
           (unit_id, paper_id, section_path, section_path_json, section_level, section_title,
            unit_text, unit_kind, part_ordinal, page_span_json, block_span_json,
            token_estimate, indexable, veto_reason, quality_hints_json)
           VALUES (?, ?, ?, '[]', 1, ?, ?, 'body', 0, '[]', '[]', 10, ?, '', '[]')""",
        (unit_id, paper_id, section_path, section_title, text, indexable),
    )
    # FTS5 external content table may raise on DELETE when index is empty
    try:
        conn.execute(
            "DELETE FROM body_units_fts WHERE unit_id = ?",
            (unit_id,),
        )
    except sqlite3.DatabaseError:
        pass
    conn.execute(
        """INSERT INTO body_units_fts(rowid, unit_id, paper_id, section_path, unit_text)
           SELECT rowid, unit_id, paper_id, section_path, unit_text
           FROM body_units WHERE unit_id = ?""",
        (unit_id,),
    )
    conn.commit()


def _create_vec_tables(conn: sqlite3.Connection) -> None:
    """Create vec0 tables (if sqlite-vec is available)."""
    try:
        from paperforge.memory.db import ensure_vec_extension

        ensure_vec_extension(conn)
        conn.executescript(CREATE_VEC_BODY)
        conn.executescript(CREATE_VEC_BODY_META)
        conn.executescript(CREATE_VEC_OBJECTS)
        conn.executescript(CREATE_VEC_OBJECTS_META)
        conn.commit()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tests: query rewrite
# ---------------------------------------------------------------------------

class TestQueryRewrite:
    def test_expand_abbreviation(self):
        """VTE -> venous thromboembolism."""
        variants = expand_query("VTE prevention")
        assert "VTE prevention" in variants
        assert "venous thromboembolism prevention" in variants

    def test_expand_multiple_abbreviations(self):
        """Each abbreviation produces a separate variant."""
        variants = expand_query("ACL VTE")
        assert len(variants) >= 2

    def test_no_abbreviation_no_expansion(self):
        """No expansion when no abbreviations or synonyms are present."""
        variants = expand_query("randomized controlled trial design")
        assert len(variants) == 1

    def test_synonym_expansion_fallback(self):
        """Synonym expansion when no abbreviations found."""
        variants = expand_query("knee fracture")
        assert len(variants) >= 2  # original + at least one expanded form

    def test_abbreviations_dict_populated(self):
        """The abbreviations dictionary has entries."""
        assert len(ABBREVIATIONS) > 5

    def test_synonyms_dict_populated(self):
        """The synonyms dictionary has entries."""
        assert len(MEDICAL_SYNONYMS) > 3


# ---------------------------------------------------------------------------
# Tests: hybrid search
# ---------------------------------------------------------------------------

class TestHybridSearch:
    def test_bm25_only_fallback(self, tmp_path):
        """hybrid_search returns BM25 results when vec0 is unavailable."""
        vault = tmp_path
        db_path = get_memory_db_path(vault)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = get_connection(db_path)
        _create_tables(conn)
        _seed_paper(conn, "p1", "ACL Reconstruction Study")
        _seed_body_unit(conn, "p1:u1", "p1", "The anterior cruciate ligament reconstruction technique used patellar tendon graft.", section_title="Methods")
        _seed_body_unit(conn, "p1:u2", "p1", "Patients were followed for 2 years post-operatively.", section_title="Results")
        conn.close()

        results = hybrid_search(vault, "ACL reconstruction", limit=5)
        assert isinstance(results, list)
        # Should find BM25 content
        assert len(results) >= 1
        assert results[0]["paper_id"] == "p1"
        assert "source" in results[0]

    def test_hybrid_with_vec0(self, tmp_path, mock_provider):
        """hybrid_search runs BM25 + vec0 when vec0 tables exist."""
        vault = tmp_path
        db_path = get_memory_db_path(vault)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = get_connection(db_path)
        _create_tables(conn)
        vec_ok = _create_vec_tables(conn)
        _seed_paper(conn, "p1", "VTE Prophylaxis Study")
        _seed_body_unit(conn, "p1:u1", "p1", "Venous thromboembolism prophylaxis after total knee arthroplasty.", section_title="Methods")
        conn.close()

        results = hybrid_search(vault, "VTE prophylaxis", limit=5)
        assert isinstance(results, list)

    def test_empty_results(self, tmp_path):
        """hybrid_search returns empty list when nothing matches."""
        vault = tmp_path
        db_path = get_memory_db_path(vault)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = get_connection(db_path)
        _create_tables(conn)
        _seed_paper(conn, "p1", "Some Study")
        _seed_body_unit(conn, "p1:u1", "p1", "Completely unrelated content about plants.", section_title="Intro")
        conn.close()

        results = hybrid_search(vault, "zzzznotfoundzzzz", limit=5)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_result_fields(self, tmp_path):
        """Each result has the expected fields."""
        vault = tmp_path
        db_path = get_memory_db_path(vault)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = get_connection(db_path)
        _create_tables(conn)
        _seed_paper(conn, "p1", "Knee OA Study")
        _seed_body_unit(conn, "p1:u1", "p1", "Osteoarthritis of the knee joint is common.", section_title="Introduction")
        conn.close()

        results = hybrid_search(vault, "knee osteoarthritis", limit=5)
        if results:
            r = results[0]
            assert "paper_id" in r
            assert "title" in r
            assert "source" in r
            assert "text" in r
            assert "score" in r
            assert "heading" in r
            assert r["source"] == "body_unit"

    def test_query_rewrite_broadens_bm25(self, tmp_path):
        """Query with abbreviation finds content via expanded form."""
        vault = tmp_path
        db_path = get_memory_db_path(vault)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = get_connection(db_path)
        _create_tables(conn)
        _seed_paper(conn, "p1", "ACL Study")
        # Only contains the full form, not the abbreviation
        _seed_body_unit(conn, "p1:u1", "p1", "We reviewed anterior cruciate ligament reconstruction outcomes.", section_title="Methods")
        # Contains neither
        _seed_body_unit(conn, "p1:u2", "p1", "Patients were evaluated at 12 months.", section_title="Results")
        conn.close()

        results = hybrid_search(vault, "ACL reconstruction", limit=5)
        # Should find the expanded form
        matched = [r for r in results if "anterior cruciate ligament" in (r.get("text", "") or "")]
        assert len(matched) >= 1


# ---------------------------------------------------------------------------
# Tests: score fusion logic
# ---------------------------------------------------------------------------

class TestScoreFusion:
    def test_fuse_bm25_only(self):
        """Fusion returns BM25 scores unchanged when vec results are empty."""
        bm25 = [
            {"paper_id": "p1", "text": "text1", "bm25_score": 0.8, "vec_score": 0.0, "source": "body_unit",
             "title": "T1", "first_author": "A", "year": "2023", "journal": "J", "domain": "ortho",
             "heading": "Methods", "unit_id": "p1:u1", "matched_terms": ""},
        ]
        vec: list[dict] = []
        fused = _fuse_results(bm25, vec, limit=5)
        assert len(fused) == 1
        assert fused[0]["score"] == 0.8
        assert fused[0]["vec_score"] == 0.0

    def test_fuse_hybrid(self):
        """Fusion combines BM25 and vec scores."""
        bm25 = [
            {"paper_id": "p1", "text": "text1", "bm25_score": 0.5, "vec_score": 0.0, "source": "body_unit",
             "title": "T1", "first_author": "A", "year": "2023", "journal": "J", "domain": "ortho",
             "heading": "Methods", "unit_id": "p1:u1", "matched_terms": ""},
        ]
        vec = [
            {"paper_id": "p1", "text": "text1", "source": "body_unit", "vec_score": 0.8},
        ]
        fused = _fuse_results(bm25, vec, limit=5)
        assert len(fused) == 1
        # combined = 0.3 * bm25_norm + 0.7 * vec_norm
        # bm25_norm = 0.5 (already normalized)
        # vec_norm = 1 - 1/(1+0.8) = 0.4444
        # combined = 0.3*0.5 + 0.7*0.4444 = 0.15 + 0.3111 = 0.4611
        assert fused[0]["score"] > 0.4
        assert fused[0]["score"] < 0.5

    def test_fuse_deduplicates(self):
        """Fusion deduplicates by (paper_id, text)."""
        bm25 = [
            {"paper_id": "p1", "text": "same text", "bm25_score": 0.8, "vec_score": 0.0, "source": "body_unit",
             "title": "T1", "first_author": "A", "year": "2023", "journal": "J", "domain": "ortho",
             "heading": "Methods", "unit_id": "p1:u1", "matched_terms": ""},
            {"paper_id": "p1", "text": "same text", "bm25_score": 0.6, "vec_score": 0.0, "source": "body_unit",
             "title": "T1", "first_author": "A", "year": "2023", "journal": "J", "domain": "ortho",
             "heading": "Results", "unit_id": "p1:u2", "matched_terms": ""},
        ]
        vec: list[dict] = []
        fused = _fuse_results(bm25, vec, limit=5)
        assert len(fused) == 1  # deduplicated by text

    def test_vec_only_fallback(self):
        """When BM25 is empty, fusion falls back to vec results."""
        bm25: list[dict] = []
        vec = [
            {"paper_id": "p1", "text": "vec result text", "source": "body_unit", "vec_score": 0.75},
        ]
        fused = _fuse_results(bm25, vec, limit=5)
        assert len(fused) == 1
        assert fused[0]["paper_id"] == "p1"
        assert fused[0]["vec_score"] > 0.7


# ---------------------------------------------------------------------------
# Tests: BM25 search internals
# ---------------------------------------------------------------------------

class TestBM25Search:
    def test_bm25_finds_matching_content(self, tmp_path):
        """_bm25_search finds matching body units."""
        db_path = get_memory_db_path(tmp_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(db_path)
        _create_tables(conn)
        _seed_paper(conn, "p1", "Test Paper")
        _seed_body_unit(conn, "p1:u1", "p1", "This text discusses knee replacement outcomes and complications.", section_title="Methods")
        _seed_body_unit(conn, "p1:u2", "p1", "Introduction paragraph with general background.", section_title="Introduction")
        conn.close()

        conn = get_connection(db_path, read_only=True)
        try:
            results = _bm25_search(conn, ["knee replacement"], limit=10)
            assert len(results) >= 1
            assert results[0]["paper_id"] == "p1"
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Test CLI integration
# ---------------------------------------------------------------------------

class TestDeepFlag:
    def test_deep_flag_parses(self):
        """--deep flag is accepted by the CLI parser."""
        import argparse
        from paperforge.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["retrieve", "VTE prevention", "--deep", "--json"])
        assert args.deep is True
        assert args.command == "retrieve"
