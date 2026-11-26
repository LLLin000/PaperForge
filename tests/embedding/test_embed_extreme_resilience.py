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
