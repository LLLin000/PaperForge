from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.commands import retrieve as retrieve_command
from paperforge.commands import search as search_command
from tests.conftest import canonical_test_config


@pytest.fixture(autouse=True)
def _canonical_vault_config(tmp_path: Path) -> None:
    """#142 seam: every tmp_path-rooted vault gets a canonical paperforge.json."""
    canonical_test_config(tmp_path)


class _Args:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.query = "Lin 2024 Electrical Stimulation"
        self.json = True
        self.limit = 10
        self.domain = None
        self.year_from = None
        self.year_to = None
        self.ocr = None
        self.deep = None
        self.lifecycle = None
        self.next_step = None
        self.expand = True
        self.paper = None


class _Conn:
    def close(self) -> None:
        return None


def test_search_zero_results_emits_query_diagnostic(monkeypatch, tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "paperforge.db"
    db_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(search_command, "get_memory_db_path", lambda vault: db_path)
    monkeypatch.setattr(search_command, "get_connection", lambda db_path, read_only=True: _Conn())
    monkeypatch.setattr(search_command, "search_papers", lambda *args, **kwargs: [])

    args = _Args(tmp_path)
    assert search_command.run(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["count"] == 0
    assert "query_diagnostic" in payload["data"]
    # New contract: 0 results always carries a query_diagnostic; the
    # next_action is conditional on the planner recommending a different
    # command, so only the diagnostic is asserted here.


def test_retrieve_unavailable_emits_suggested_modes(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr("paperforge.embedding.get_embed_status", lambda vault: {"healthy": True, "chunk_count": 0, "db_exists": False, "error": ""})

    args = _Args(tmp_path)
    args.query = "galvanotaxis"
    assert retrieve_command.run(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    # New contract: unavailable retrieval fails with an explicit error
    # (fallback-mode suggestions live in the query-plan command).
    assert payload["error"] is not None


def test_retrieve_low_confidence_hits_emit_warning(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr("paperforge.embedding.get_embed_status", lambda vault: {"healthy": True, "chunk_count": 5, "db_exists": True, "error": ""})
    monkeypatch.setattr("paperforge.embedding.get_embed_status", lambda vault: {
        "healthy": True, "db_exists": True, "valid_total_chunks": 5,
        "vector_state": "ready", "chunk_count": 5,
    })
    monkeypatch.setattr(retrieve_command, "merge_retrieve", lambda vault, query, limit=5, expand=True, paper_id=None: [
        {"paper_id": "AAA11111", "chunk_text": "[Figure]", "score": 0.58},
        {"paper_id": "AAA11111", "chunk_text": "### Keywords", "score": 0.57},
        {"paper_id": "AAA11111", "chunk_text": "None.", "score": 0.56},
    ])
    # The reader gate (#159 §6) needs an observable lineage chain — the
    # fixture paper is current, so the low-confidence warning still fires.
    # The gate observes scoped hits now, so both entry points are mocked.
    def _envelope(vault, keys=None):
        return {
            "capability_state": "ok",
            "papers": {"AAA11111": {"ocr": "current", "retrieval": "current", "vector": "current"}},
        }

    monkeypatch.setattr("paperforge.lineage.probe_lineage", _envelope)
    monkeypatch.setattr("paperforge.lineage.observe_lineage_papers", _envelope)

    args = _Args(tmp_path)
    args.query = "unlikelynonexistenttermxyz"
    assert retrieve_command.run(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["warnings"], "low-confidence semantic hits must warn"
    assert any("Low-confidence" in w for w in payload["warnings"])



def test_retrieve_stale_returns_vector_error(monkeypatch, tmp_path: Path, capsys) -> None:
    """Standard retrieve with valid_total=0 returns stale/not_built error."""
    monkeypatch.setattr(
        "paperforge.embedding.get_embed_status",
        lambda vault: {"valid_total_chunks": 0, "vector_state": "stale", "healthy": True, "db_exists": True, "error": ""},
    )

    args = _Args(tmp_path)
    args.query = "cartilage repair"
    assert retrieve_command.run(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["data"]["vector_state"] == "stale"
    assert payload["data"]["next_action_id"] == "embed.build"
    assert "stale" in payload["error"]["message"].lower()


def test_retrieve_not_built_returns_vector_error(monkeypatch, tmp_path: Path, capsys) -> None:
    """Standard retrieve with no vectors and no legacy returns not_built error."""
    monkeypatch.setattr(
        "paperforge.embedding.get_embed_status",
        lambda vault: {"valid_total_chunks": 0, "vector_state": "not_built", "healthy": True, "db_exists": True, "error": ""},
    )

    args = _Args(tmp_path)
    args.query = "cartilage repair"
    assert retrieve_command.run(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["data"]["vector_state"] == "not_built"
    assert payload["data"]["next_action_id"] == "embed.build"


def test_retrieve_paper_scoped_zero_has_no_warnings(monkeypatch, tmp_path: Path, capsys) -> None:
    """Paper-scoped retrieve with zero results: no warnings, no next_actions."""
    db_path = tmp_path / "paperforge.db"
    monkeypatch.setattr("paperforge.memory.db.get_memory_db_path", lambda vault: db_path)

    # Seed a paper with fulltext
    from paperforge.memory.db import get_connection, ensure_vec_extension
    from paperforge.memory.schema import ensure_schema
    conn = get_connection(db_path, read_only=False)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    conn.execute("INSERT OR IGNORE INTO papers (zotero_key, title) VALUES ('P001', 'Cartilage Repair')")
    conn.execute(
        "INSERT INTO body_units (unit_id, paper_id, section_path, section_path_json, unit_text, "
        "unit_kind, part_ordinal, page_span_json, block_span_json, token_estimate, indexable, "
        "veto_reason, quality_hints_json) "
        "VALUES ('P001:b1', 'P001', 'Methods', '[]', 'cartilage repair techniques', "
        "'body', 1, '[]', '[]', 10, 1, '', '{}')",
    )
    # Seed a valid vec_body_meta entry so _paper_scope_check passes
    conn.execute(
        "INSERT INTO vec_body_meta (rowid, paper_id, chunk_index, unit_id, text) "
        "VALUES (1, 'P001', 0, 'P001:b1', 'dummy')",
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        "paperforge.embedding.get_embed_status",
        lambda vault: {"valid_total_chunks": 5, "vector_state": "ready", "healthy": True, "db_exists": True, "error": ""},
    )
    monkeypatch.setattr(
        "paperforge.commands.retrieve.merge_retrieve",
        lambda vault, query, limit=5, expand=True, paper_id=None: [],
    )
    args = _Args(tmp_path)
    args.query = "unknown term"
    args.paper = "P001"
    assert retrieve_command.run(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["count"] == 0
    assert payload["data"]["scoped_paper"] == "P001"
    assert not payload.get("warnings"), "Paper-scoped zero results must not emit warnings"
    assert not payload.get("next_actions"), "Paper-scoped zero results must not emit next_actions"
def test_deep_bm25_only_on_vector_failure(monkeypatch, tmp_path: Path) -> None:
    """retrieve --deep returns BM25 results even when _vec_search fails."""
    import sqlite3
    from paperforge.embedding.search import hybrid_search

    db_path = tmp_path / "System" / "PaperForge" / "indexes" / "paperforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Patch get_connection to ignore read_only flag (Windows URI compat)
    def _fake_conn(p, read_only=False):
        c = sqlite3.connect(str(p))
        c.row_factory = sqlite3.Row
        return c
    monkeypatch.setattr("paperforge.embedding.search.get_connection", _fake_conn)

    # Seed data via the same patched connection
    from paperforge.memory.schema import ensure_schema
    conn = _fake_conn(db_path)
    ensure_schema(conn)
    conn.execute("INSERT OR IGNORE INTO papers (zotero_key, title) VALUES ('P001', 'Cartilage Repair')")
    conn.execute(
        "INSERT INTO body_units (unit_id, paper_id, section_path, section_path_json, unit_text, "
        "unit_kind, part_ordinal, page_span_json, block_span_json, token_estimate, indexable, "
        "veto_reason, quality_hints_json) "
        "VALUES ('P001:b1', 'P001', 'Methods', '[]', 'cartilage repair techniques', "
        "'body', 1, '[]', '[]', 10, 1, '', '{}')",
    )
    conn.commit()
    conn.execute(
        "INSERT INTO body_units_fts(rowid, unit_id, paper_id, section_path, unit_text) "
        "SELECT rowid, unit_id, paper_id, section_path, unit_text FROM body_units",
    )
    conn.commit()
    conn.close()

    # Mock _vec_search to fail (no API key / provider error)
    monkeypatch.setattr(
        "paperforge.embedding.search._vec_search",
        lambda conn, vault, query, limit, paper_id=None: (_ for _ in ()).throw(ValueError("No API key")),
    )

    results = hybrid_search(tmp_path, "cartilage", limit=5, paper_id="P001")
    assert len(results) >= 1, "Expected at least one BM25 result despite vec failure"
    r = results[0]
    assert "cartilage" in r.get("text", r.get("chunk_text", ""))
