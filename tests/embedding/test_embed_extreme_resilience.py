"""Extreme-state resilience tests for SQLite-vec / shadow-build embedding pipeline."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from paperforge.embedding.build_state import read_vector_build_state
from paperforge.embedding.build_target import BuildTarget, ShadowBuild
from paperforge.embedding.status import get_embed_status
from paperforge.embedding.substrate import (
    assess_vector_publication,
    assess_vector_substrate,
    effective_vector_db,
)
from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from paperforge.services.embedding import _restore_db_from_backup, run_embedding_build
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


def _seed_vault_with_two_papers(tmp_path: Path) -> tuple[Path, list[dict]]:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    pf = tmp_path / ".paperforge"
    db_path = get_memory_db_path(tmp_path)
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    for tbl in ("vec_fulltext", "vec_body", "vec_objects"):
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
        conn.execute(f"CREATE VIRTUAL TABLE {tbl} USING vec0(embedding float[4])")

    items = []
    for k in ("EMB00001", "EMB00002"):
        conn.execute(
            "INSERT INTO papers (zotero_key, title) VALUES (?, ?)",
            (k, f"Study {k}"),
        )
        conn.execute(
            """INSERT INTO body_units (unit_id, paper_id, section_path, section_path_json, section_level,
               section_title, node_id, unit_text, unit_kind, part_ordinal, page_span_json, block_span_json,
               token_estimate, indexable, veto_reason, quality_hints_json)
               VALUES (?, ?, 'Methods', '["Methods"]', 1, 'Methods', 'n1', ?, 'body', 0, '[1,1]', '["b1"]', 10, 1, '', '[]')""",
            (f"{k}:b1", k, f"Methods text for {k}"),
        )
        conn.execute(
            """INSERT INTO object_units (unit_id, paper_id, section_path, node_id, section_path_json,
               object_kind, object_label, caption_text, nearby_body_text, page_span_json, block_span_json,
               token_estimate, indexable, veto_reason, quality_hints_json)
               VALUES (?, ?, 'Results', 'n2', '["Results"]', 'figure', 'Fig 1', ?, '', '[2,2]', '["b2"]', 8, 1, '', '[]')""",
            (f"{k}:fig1", k, f"Caption for {k}"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"manifest:{k}", json.dumps({"paper_id": k, "ocr_result_hash": f"h_{k}", "retrieval_policy_version": "v1"})),
        )
        items.append({"zotero_key": k, "title": f"Study {k}", "ocr_status": "done"})

    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES ('model', '\"text-embedding-3-small\"')"
    )
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_provider_endpoint', '\"https://api.openai.com/v1\"')"
    )
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_dimension', '4')")
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')")
    conn.commit()
    conn.close()
    (pf / "indexes" / "formal-library.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    return db_path, items


class _StubProvider:
    model = "text-embedding-3-small"

    def __init__(self, vec: list[float] | None = None) -> None:
        self._vec = vec or [0.1, 0.2, 0.3, 0.4]

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [list(self._vec) for _ in texts]

    def encode_single(self, text: str) -> list[float]:
        return list(self._vec)


def test_corrupt_candidate_does_not_shadow_live_and_resume_cleans_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path, items = _seed_vault_with_two_papers(tmp_path)
    # Seed a valid vector row in LIVE so live is healthy
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    cur = conn.execute("INSERT INTO vec_body(embedding) VALUES (?)", ['[0.1, 0.2, 0.3, 0.4]'])
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, chunk_index, unit_id, text) VALUES (?, 'EMB00001', 0, 'EMB00001:b1', 'txt')",
        (cur.lastrowid,),
    )
    conn.commit()
    conn.close()

    # Create a corrupt/truncated `.db.build` candidate
    cand = db_path.with_suffix(".db.build")
    cand.write_bytes(b"NOT A VALID SQLITE FILE OR TRUNCATED")

    # Must NEVER shadow the healthy live DB
    assert effective_vector_db(tmp_path) == db_path

    # Running resume build cleans up the corrupt candidate instead of crashing
    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "sk-test-token")
    monkeypatch.setattr(
        "paperforge.embedding.builder.resolve_embedding_provider",
        lambda *_a, **_kw: _StubProvider(),
    )
    monkeypatch.setattr(
        "paperforge.embedding.dim_detect.resolve_embedding_provider",
        lambda *_a, **_kw: _StubProvider(),
    )
    rc = run_embedding_build(tmp_path, items, resume=True, json=True, emit_events=False)
    assert rc == 0
    assert not cand.exists()


def test_model_switch_with_surviving_candidate_clears_recover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from paperforge.config import set_config

    db_path, items = _seed_vault_with_two_papers(tmp_path)
    cand = db_path.with_suffix(".db.build")
    # Build a valid 4-dim candidate stamped with OLD model "text-embedding-3-small"
    conn = get_connection(cand)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    for tbl in ("vec_fulltext", "vec_body", "vec_objects"):
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
        conn.execute(f"CREATE VIRTUAL TABLE {tbl} USING vec0(embedding float[4])")
    cur = conn.execute("INSERT INTO vec_body(embedding) VALUES (?)", ['[0.1, 0.2, 0.3, 0.4]'])
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, chunk_index, unit_id, text) VALUES (?, 'EMB00001', 0, 'EMB00001:b1', 'old')",
        (cur.lastrowid,),
    )
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('model', '\"text-embedding-3-small\"')")
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_provider_endpoint', '\"https://api.openai.com/v1\"')"
    )
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')")
    conn.commit()
    conn.close()

    # Switch model to a NEW 6-dim model while candidate sits on disk
    set_config(tmp_path, "vector_db_api_model", "text-embedding-3-large")
    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "sk-test-token")
    new_provider = _StubProvider(vec=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    new_provider.model = "text-embedding-3-large"
    monkeypatch.setattr(
        "paperforge.embedding.builder.resolve_embedding_provider",
        lambda *_a, **_kw: new_provider,
    )
    monkeypatch.setattr(
        "paperforge.embedding.dim_detect.resolve_embedding_provider",
        lambda *_a, **_kw: new_provider,
    )
    monkeypatch.setattr(
        "paperforge.services.embedding.select_embedding_candidates",
        lambda _v, keys=None: {"eligible": ["EMB00001", "EMB00002"], "no_content": [], "not_ready": []},
    )
    from paperforge.embedding.dim_detect import reset_dim_cache

    reset_dim_cache()
    rc = run_embedding_build(tmp_path, items, resume=True, json=True, emit_events=False)
    assert rc == 0
    # Verify new live DB rebuilt cleanly at 6 dims instead of trying to recover 4-dim candidate
    status = get_embed_status(tmp_path)
    assert status["dimension"] == 6
    assert status["valid_total_chunks"] == 4


def test_transient_publish_failure_after_verified_preserves_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from paperforge.config import set_config

    db_path, items = _seed_vault_with_two_papers(tmp_path)
    # Trigger a shadow rebuild by switching model (still 4-dim so provider matches)
    set_config(tmp_path, "vector_db_api_model", "new-4d-model")
    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "sk-test-token")
    monkeypatch.setattr(
        "paperforge.embedding.builder.resolve_embedding_provider",
        lambda *_a, **_kw: _StubProvider(),
    )
    monkeypatch.setattr(
        "paperforge.embedding.dim_detect.resolve_embedding_provider",
        lambda *_a, **_kw: _StubProvider(),
    )
    monkeypatch.setattr(
        "paperforge.services.embedding.select_embedding_candidates",
        lambda _v, keys=None: {"eligible": ["EMB00001", "EMB00002"], "no_content": [], "not_ready": []},
    )
    monkeypatch.setattr(
        ShadowBuild,
        "publish",
        lambda self: (_ for _ in ()).throw(PermissionError("simulated Windows lock on live DB")),
    )
    rc = run_embedding_build(tmp_path, items, resume=False, json=True, emit_events=False)
    assert rc == 1

    # Verified candidate MUST NOT be aborted/deleted!
    cand = db_path.with_suffix(".db.build")
    assert cand.exists()
    pub = assess_vector_publication(tmp_path)
    assert pub["publish_pending"] is True
    assert pub["candidate_has_rows"] is True


def test_inplace_write_failure_between_payloads_rolls_back_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path, items = _seed_vault_with_two_papers(tmp_path)
    # Pre-seed old vectors for EMB00001
    conn = get_connection(db_path)
    ensure_vec_extension(conn)
    c1 = conn.execute("INSERT INTO vec_body(embedding) VALUES (?)", ['[0.9, 0.9, 0.9, 0.9]'])
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, chunk_index, unit_id, text) VALUES (?, 'EMB00001', 0, 'EMB00001:b1', 'old-body')",
        (c1.lastrowid,),
    )
    conn.commit()
    conn.close()

    from paperforge.services import embedding as emb_svc

    orig_write = emb_svc.write_encoded_payload_to_conn
    calls = 0

    def _fail_on_object_payload(conn_arg, payload_arg):
        nonlocal calls
        calls += 1
        if payload_arg.collection_name == "paperforge_objects":
            raise sqlite3.OperationalError("injected mid-paper write failure")
        orig_write(conn_arg, payload_arg)

    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "sk-test-token")
    monkeypatch.setattr(
        "paperforge.embedding.builder.resolve_embedding_provider",
        lambda *_a, **_kw: _StubProvider(),
    )
    monkeypatch.setattr(
        "paperforge.embedding.dim_detect.resolve_embedding_provider",
        lambda *_a, **_kw: _StubProvider(),
    )
    monkeypatch.setattr(
        "paperforge.services.embedding.select_embedding_candidates",
        lambda _v, keys=None: {"eligible": ["EMB00001", "EMB00002"], "no_content": [], "not_ready": []},
    )
    monkeypatch.setattr(emb_svc, "write_encoded_payload_to_conn", _fail_on_object_payload)

    rc = run_embedding_build(tmp_path, items[:1], keys=["EMB00001"], resume=True, json=True, emit_events=False)
    assert rc == 1

    # Old vector must still be intact (rollback restored pre-paper delete + partial insert)
    ro = get_connection(db_path, read_only=True)
    try:
        rows = ro.execute("SELECT text FROM vec_body_meta WHERE paper_id = 'EMB00001'").fetchall()
        assert [r[0] for r in rows] == ["old-body"]
    finally:
        ro.close()


def test_restore_db_from_backup_clears_stale_wal_sidecars(tmp_path: Path) -> None:
    live = tmp_path / "paperforge.db"
    bak = tmp_path / "paperforge.pre-rebuild.db"

    c_bak = sqlite3.connect(str(bak))
    c_bak.execute("CREATE TABLE t (x INT)")
    c_bak.execute("INSERT INTO t VALUES (42)")
    c_bak.commit()
    c_bak.close()

    live.write_bytes(b"corrupted-main-db")
    Path(str(live) + "-wal").write_bytes(b"stale-wal-garbage-that-would-corrupt-restore")
    Path(str(live) + "-shm").write_bytes(b"stale-shm")

    _restore_db_from_backup(bak, live)
    assert not Path(str(live) + "-wal").exists()
    assert not Path(str(live) + "-shm").exists()

    c_live = sqlite3.connect(str(live))
    try:
        assert c_live.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert c_live.execute("SELECT x FROM t").fetchone()[0] == 42
    finally:
        c_live.close()


def test_malformed_live_db_handled_gracefully(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    db_path = get_memory_db_path(tmp_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"this is completely corrupt sqlite bytes !@#$" * 20)

    bs = read_vector_build_state(tmp_path)
    assert bs["status"] == "idle"

    sub = assess_vector_substrate(tmp_path)
    assert sub.compatible is False
    assert sub.layout_incompatible is True
    assert "vector.db_corrupt" in sub.reason_codes

    status = get_embed_status(tmp_path)
    assert status["healthy"] is False
    assert status["corrupted"] is True
    assert status["vector_state"] != "ready"


def test_delete_paper_vectors_in_conn_loads_vec0(tmp_path: Path) -> None:
    """PF-OCR-002: delete_paper_vectors_in_conn loads vec0 without caller pre-loading it."""
    from paperforge.embedding._chroma import delete_paper_vectors_in_conn
    from paperforge.embedding.vectors import delete_paper_vectors_in_conn as delete_v2
    from paperforge.memory.db import ensure_vec_extension
    from paperforge.memory.schema import ensure_schema

    db_path = tmp_path / "vec_del.db"
    conn = sqlite3.connect(str(db_path))
    ensure_vec_extension(conn)
    ensure_schema(conn)
    conn.execute("INSERT INTO papers(zotero_key, title) VALUES ('DEL1', 'Paper 1')")
    conn.execute("INSERT INTO papers(zotero_key, title) VALUES ('DEL2', 'Paper 2')")
    dim_zero = json.dumps([0.0] * 1536)
    conn.execute("INSERT INTO vec_body(rowid, embedding) VALUES (1, ?)", (dim_zero,))
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, unit_id, chunk_index, text) VALUES (1, 'DEL1', 'u1', 0, 'txt')"
    )
    conn.execute("INSERT INTO vec_body(rowid, embedding) VALUES (2, ?)", (dim_zero,))
    conn.execute(
        "INSERT INTO vec_body_meta(rowid, paper_id, unit_id, chunk_index, text) VALUES (2, 'DEL2', 'u2', 0, 'txt2')"
    )
    conn.commit()
    conn.close()

    # Open raw sqlite3 connection without vec0 loaded
    raw_conn = sqlite3.connect(str(db_path))
    try:
        assert delete_paper_vectors_in_conn(raw_conn, "DEL1") >= 1
        assert delete_v2(raw_conn, "DEL2") >= 1
        raw_conn.commit()
        assert raw_conn.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0] == 0
    finally:
        raw_conn.close()


def test_openai_lazy_import_and_optional_runtime_check(tmp_path: Path, monkeypatch) -> None:
    """PF-UX-001: missing openai must not crash non-embedding imports or setup checks."""
    import sys as _sys
    import types
    from paperforge.commands import retrieve as retrieve_cmd
    from paperforge.setup.runtime import check_runtime_dependencies

    monkeypatch.setitem(_sys.modules, "openai", None)
    # Re-importing openai_compatible must not import openai at module import time
    mod_name = "paperforge.embedding.providers.openai_compatible"
    monkeypatch.delitem(_sys.modules, mod_name, raising=False)
    mod = __import__(mod_name, fromlist=["OpenAICompatibleProvider"])
    assert hasattr(mod, "OpenAICompatibleProvider")

    # Missing optional extras keeps check_runtime_dependencies ok=True
    monkeypatch.setattr("paperforge.setup.runtime.vector_extras_missing", lambda: ["openai", "sqlite_vec"])
    res = check_runtime_dependencies()
    assert res.ok is True
    assert "openai" in res.details["optional_missing"]

    # Standard vector retrieve rejects unhealthy/corrupted index even if valid_total > 0 (PF-OCR-007)
    monkeypatch.setattr(
        "paperforge.embedding.get_embed_status",
        lambda _v: {"healthy": False, "corrupted": True, "valid_total_chunks": 5, "vector_state": "stale"},
    )
    ns = types.SimpleNamespace(vault_path=tmp_path, query="q", limit=5, deep=False, expand=True, paper=None, domain=None, json=True)
    assert retrieve_cmd.run(ns) == 1


def test_corrupt_db_auto_quarantine_on_rebuild(tmp_path: Path) -> None:
    """PF-UX-002: memory build & engine rebuild-db quarantine corrupt DB and recover."""
    from paperforge.memory.builder import build_for_keys
    from paperforge.services.vault_engine import rebuild_db_from_truth
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    idx = get_index_path(vault)
    idx.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_index(idx, build_envelope([{"zotero_key": "K1", "title": "Recovered Paper", "domain": "Ortho"}]))

    db_path = get_memory_db_path(vault)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"corrupt garbage bytes" * 10)

    res = build_for_keys(vault)
    assert res["papers_indexed"] == 1
    assert res.get("quarantined_corrupt_db")

    # Corrupt again and verify rebuild_db_from_truth recovers cleanly
    db_path.write_bytes(b"corrupt garbage bytes again" * 10)
    eng = rebuild_db_from_truth(vault, backup_existing=True)
    assert eng["memory_build"]["papers_indexed"] == 1
    assert eng.get("quarantined_corrupt_db")


def test_meta_only_candidate_resumable_but_never_promotable_or_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Meta-only interrupted candidate offers embed.resume, yet fails verify_candidate/publish and is never ready."""
    from paperforge import probes as probe_mod
    from paperforge.embedding.build_target import BuildTargetError, verify_candidate
    from paperforge.embedding.status import get_embed_status_for_path
    from paperforge.embedding.substrate import candidate_is_healthy_with_rows

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    live = get_memory_db_path(vault)
    live.parent.mkdir(parents=True, exist_ok=True)
    live_conn = get_connection(live)
    ensure_vec_extension(live_conn)
    ensure_schema(live_conn)
    live_conn.commit()
    live_conn.close()

    cand = live.with_suffix(".db.build")
    conn = get_connection(cand)
    ensure_vec_extension(conn)
    ensure_schema(conn)
    conn.execute("INSERT INTO vec_body_meta(rowid, paper_id, chunk_index, unit_id, text) VALUES (1, 'KEY1', 0, 'KEY1:b1', 'txt')")
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('model', '\"text-embedding-3-small\"')")
    conn.execute(
        "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_provider_endpoint', '\"https://api.openai.com/v1\"')"
    )
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_dimension', '1536')")
    conn.execute("INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')")
    conn.commit()
    conn.close()

    assert candidate_is_healthy_with_rows(cand) is True
    assert effective_vector_db(vault) == cand

    monkeypatch.setattr(
        "paperforge.memory.query.get_memory_status",
        lambda _v: {
            "db_exists": True, "schema_ok": True, "fresh": True,
            "hash_match": True, "count_match": True,
            "paper_count_db": 1, "paper_count_index": 1,
            "needs_rebuild": False, "schema_version": 7,
        },
    )
    monkeypatch.setattr(
        "paperforge.embedding.build_state.read_vector_build_state",
        lambda _v: {"status": "interrupted", "current": 1, "total": 2, "pid": 0, "message": "Interrupted"},
    )
    probe_data = probe_mod.probe_memory(vault)
    assert probe_data["action"]["primary"]["action_id"] == "embed.resume"

    # Must NEVER verify or promote to live, nor report healthy/ready
    verdict = verify_candidate(cand, dimension=1536, expected_count=1)
    assert verdict["ok"] is False

    st = get_embed_status_for_path(vault, cand)
    assert st["healthy"] is False
    assert st["vector_state"] != "ready"

    sb = ShadowBuild(BuildTarget(source_path=live, vector_path=cand))
    with pytest.raises(BuildTargetError):
        sb.publish()
