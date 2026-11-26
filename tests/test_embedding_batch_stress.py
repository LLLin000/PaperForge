"""Heavy mixed-state stress tests for the Embedding parallel/shadow batch pipeline."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.test_embed_eligibility import _drop_manifest, _drop_units
from tests.test_lineage import _make_vault

EMBEDDING_DIM = 1536


def _parse_ndjson(raw: str) -> list[dict]:
    events: list[dict] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def _items_for(keys: list[str]) -> list[dict]:
    return [
        {"zotero_key": k, "ocr_status": "done", "fulltext_path": f"{k}.md"}
        for k in keys
    ]


class _MixedFaultProvider:
    def __init__(
        self,
        *,
        fail_keys: set[str] | None = None,
        nan_keys: set[str] | None = None,
        error_msg: str = "429 Rate limit exceeded",
        delay_sec: float = 0.0,
    ) -> None:
        self.fail_keys = set(fail_keys or ())
        self.nan_keys = set(nan_keys or ())
        self.error_msg = error_msg
        self.delay_sec = delay_sec
        self.encoded_texts: list[str] = []
        self._lock = threading.Lock()

    def encode(self, texts: list[str]) -> list[list[float]]:
        import time

        if self.delay_sec > 0:
            time.sleep(self.delay_sec)
        out: list[list[float]] = []
        for t in texts:
            with self._lock:
                self.encoded_texts.append(t)
            for fk in self.fail_keys:
                if fk in t:
                    raise RuntimeError(f"{self.error_msg} ({fk})")
            if any(nk in t for nk in self.nan_keys):
                out.append([float("nan")] + [0.1] * (EMBEDDING_DIM - 1))
                continue
            h = hashlib.sha256(t.encode()).digest()
            out.append([round((h[i % 32] / 255.0) + 0.01, 6) for i in range(EMBEDDING_DIM)])
        return out

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]


def _seed_unique_body_text(vault: Path, keys: list[str]) -> None:
    """Ensure each key's body_units text contains its key + updated manifest hash."""
    from paperforge.lineage import compute_retrieval_identity
    from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
    from paperforge.retrieval.manifest import compute_body_units_hash

    conn = get_connection(get_memory_db_path(vault))
    try:
        ensure_vec_extension(conn)
        for key in keys:
            conn.execute(
                "UPDATE body_units SET unit_text = ? WHERE paper_id = ?",
                (f"Clinical text payload for paper {key}", key),
            )
            rows = conn.execute(
                "SELECT * FROM body_units WHERE paper_id = ? AND indexable = 1 ORDER BY unit_id",
                (key,),
            ).fetchall()
            units = [dict(r) for r in rows]
            mrow = conn.execute(
                "SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)
            ).fetchone()
            if mrow:
                manifest = json.loads(mrow[0])
                manifest["body_units_hash"] = compute_body_units_hash(units)
                manifest["retrieval_identity"] = compute_retrieval_identity(
                    ocr_result_hash=manifest["ocr_result_hash"],
                    retrieval_policy_version=manifest["retrieval_policy_version"],
                    structure_tree_hash=manifest["structure_tree_hash"],
                    body_units_hash=manifest["body_units_hash"],
                    object_units_hash=manifest["object_units_hash"],
                )
                conn.execute(
                    "UPDATE meta SET value = ? WHERE key = ?",
                    (json.dumps(manifest), f"manifest:{key}"),
                )
        conn.commit()
    finally:
        conn.close()


def _pre_embed_keys(vault: Path, keys: list[str], *, stale: bool = False) -> None:
    from paperforge.embedding._config import get_api_model, get_effective_api_base_url
    from paperforge.embedding.builder import encode_payload, prepare_body_payload, prepare_object_payload, write_encoded_payload_to_conn
    from paperforge.embedding.dim_detect import ensure_vec_tables
    from paperforge.embedding.providers import resolve_embedding_provider
    from paperforge.embedding.substrate import VECTOR_IDENTITY_VERSION
    from paperforge.lineage import write_vector_lineage
    from paperforge.memory.db import ensure_vec_extension, get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.embedding import get_body_units_for_embedding, get_object_units_for_embedding

    model = get_api_model(vault)
    endpoint = get_effective_api_base_url(vault)
    units_by_key = {
        key: (
            get_body_units_for_embedding(vault, key),
            get_object_units_for_embedding(vault, key),
        )
        for key in keys
    }
    prov = resolve_embedding_provider(vault)
    conn = get_connection(get_memory_db_path(vault))
    try:
        ensure_vec_extension(conn)
        ensure_schema(conn)
        ensure_vec_tables(conn, vault, allow_recreate=True)
        for key in keys:
            bu, ou = units_by_key[key]
            if bu:
                p = prepare_body_payload(key, bu)
                enc = encode_payload(vault, p, provider=prov)
                if stale:
                    for m in enc.metadatas:
                        m["body_units_hash"] = "stale_old_hash"
                write_encoded_payload_to_conn(conn, enc)
            if ou:
                p = prepare_object_payload(key, ou)
                enc = encode_payload(vault, p, provider=prov)
                write_encoded_payload_to_conn(conn, enc)
        conn.execute(
            "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', ?)",
            (json.dumps(VECTOR_IDENTITY_VERSION),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_dimension', ?)",
            (json.dumps(EMBEDDING_DIM),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO build_state (key, value) VALUES ('model', ?)",
            (json.dumps(model),),
        )
        conn.execute(
            "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_provider_endpoint', ?)",
            (json.dumps(endpoint),),
        )
        write_vector_lineage(
            conn,
            vault,
            endpoint=endpoint,
            model=model,
            dimension=EMBEDDING_DIM,
            paper_ids=keys,
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _embed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "embed-stress-token")
    monkeypatch.setattr("paperforge.services.embedding.PR9B_MAX_WORKERS", 2)


class TestEmbeddingBatchStress:
    def test_15_paper_mixed_state_embed_storm_fail_fast_then_resume_recovery(
        self, tmp_path: Path, capsys, monkeypatch
    ) -> None:
        from paperforge.embedding.build_state import read_vector_build_state
        from paperforge.memory.db import WriterLock, get_memory_db_path
        from paperforge.services.embedding import run_embedding_build

        keys = [f"EM{i:02d}" for i in range(1, 16)]
        vault = _make_vault(tmp_path, keys=tuple(keys))
        _seed_unique_body_text(vault, keys)

        # Mixed states:
        # EM01-EM02: not_ready (no retrieval manifest)
        # EM03-EM04: no_content (0 units)
        # EM05-EM07: already embedded (hash match -> noop skip)
        # EM08-EM09: stale hash (must re-embed)
        # EM10-EM15: fresh eligible, with EM12 failing in worker!
        _drop_manifest(vault, "EM01")
        _drop_manifest(vault, "EM02")
        _drop_units(vault, ("EM03", "EM04"))

        clean_provider = _MixedFaultProvider()
        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=clean_provider),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=clean_provider),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=clean_provider),
        ):
            _pre_embed_keys(vault, ["EM05", "EM06", "EM07"], stale=False)
            _pre_embed_keys(vault, ["EM08", "EM09"], stale=True)

        failing_provider = _MixedFaultProvider(fail_keys={"EM12"}, delay_sec=0.01)
        sink1: dict = {}
        item_events1: list[tuple[str, str]] = []

        # Use deterministic single-worker order so EM12 deterministically fails mid-batch
        monkeypatch.setattr("paperforge.services.embedding.PR9B_MAX_WORKERS", 1)
        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=failing_provider),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=failing_provider),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=failing_provider),
        ):
            rc1 = run_embedding_build(
                vault,
                _items_for(keys),
                force=True,
                resume=False,
                json=False,
                emit_events=True,
                on_item_result=lambda k, st: item_events1.append((k, st)),
                result_sink=sink1,
            )

        out1 = capsys.readouterr().out
        ndjson1 = _parse_ndjson(out1)
        assert rc1 == 1
        assert ndjson1[-1]["event"] == "error", f"Missing #137 terminal error event: {ndjson1}"
        assert sum(1 for e in ndjson1 if e["event"] in ("result", "error", "cancelled")) == 1
        assert ("EM12", "failed") in item_events1
        assert "429 Rate limit exceeded" in sink1["result"].error.message

        state1 = read_vector_build_state(vault)
        assert state1["status"] == "failed"
        assert "429 Rate limit exceeded" in str(state1.get("message", ""))

        # WriterLock must be completely unlocked after failure:
        with WriterLock(vault):
            pass

        # Shadow candidate survives for resume recovery; every paper that committed
        # in Pass 1 must be skipped via noop on resume, while remaining papers succeed.
        cand_path = get_memory_db_path(vault).with_suffix(".db.build")
        assert cand_path.exists()
        committed_pass1 = {k for k, st in item_events1 if st == "succeeded"}
        assert len(committed_pass1) >= 4
        assert "EM12" not in committed_pass1
        encoded_texts_joined = "\n".join(failing_provider.encoded_texts)
        assert "EM15" not in encoded_texts_joined, "Queued papers after failure should not all run"

        # Pass 2: resume=True with healthy provider recovers candidate & publishes live DB!
        recovery_provider = _MixedFaultProvider()
        sink2: dict = {}
        item_events2: list[tuple[str, str]] = []
        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=recovery_provider),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=recovery_provider),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=recovery_provider),
        ):
            rc2 = run_embedding_build(
                vault,
                _items_for(keys),
                force=False,
                resume=True,
                json=False,
                emit_events=True,
                on_item_result=lambda k, st: item_events2.append((k, st)),
                result_sink=sink2,
            )

        out2 = capsys.readouterr().out
        ndjson2 = _parse_ndjson(out2)
        assert rc2 == 0
        assert ndjson2[-1]["event"] == "result"
        assert not cand_path.exists(), "Published shadow candidate should move into live DB"
        by_key2 = dict(item_events2)
        for prior in committed_pass1:
            assert by_key2.get(prior) == "noop", f"{prior} should be resumed via noop, got {by_key2.get(prior)}"
        eligible_after_EM04 = {f"EM{i:02d}" for i in range(5, 16)}
        for rem in eligible_after_EM04 - committed_pass1:
            assert by_key2.get(rem) == "succeeded", f"{rem} should succeed on resume, got {by_key2.get(rem)}"

    def test_12_paper_embed_nan_vector_validation_failure_preserves_live_db(
        self, tmp_path: Path, capsys
    ) -> None:
        from paperforge.memory.db import WriterLock, get_memory_db_path
        from paperforge.services.embedding import run_embedding_build

        keys = [f"NV{i:02d}" for i in range(1, 13)]
        vault = _make_vault(tmp_path, keys=tuple(keys))
        _seed_unique_body_text(vault, keys)

        clean = _MixedFaultProvider()
        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=clean),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=clean),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=clean),
        ):
            _pre_embed_keys(vault, ["NV01", "NV02"], stale=False)

        conn_before = sqlite3.connect(str(get_memory_db_path(vault)))
        before_rows = conn_before.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0]
        conn_before.close()
        assert before_rows == 2

        nan_provider = _MixedFaultProvider(nan_keys={"NV07"})
        sink: dict = {}
        item_events: list[tuple[str, str]] = []
        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=nan_provider),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=nan_provider),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=nan_provider),
        ):
            rc = run_embedding_build(
                vault,
                _items_for(keys),
                force=True,
                json=False,
                emit_events=True,
                on_item_result=lambda k, st: item_events.append((k, st)),
                result_sink=sink,
            )

        out = capsys.readouterr().out
        ndjson = _parse_ndjson(out)
        assert rc == 1
        assert ndjson[-1]["event"] == "error"
        assert ("NV07", "failed") in item_events
        assert "NaN/Inf" in sink["result"].error.message

        # Live DB stayed completely untouched at 2 vectors:
        conn_after = sqlite3.connect(str(get_memory_db_path(vault)))
        after_rows = conn_after.execute("SELECT COUNT(*) FROM vec_body_meta").fetchone()[0]
        conn_after.close()
        assert after_rows == 2

        with WriterLock(vault):
            pass

    def test_14_paper_embed_cooperative_stop_cancels_queued_window_promptly(
        self, tmp_path: Path, capsys, monkeypatch
    ) -> None:
        from paperforge.memory.db import WriterLock
        from paperforge.services.embedding import run_embedding_build

        keys = [f"ST{i:02d}" for i in range(1, 15)]
        vault = _make_vault(tmp_path, keys=tuple(keys))
        _seed_unique_body_text(vault, keys)

        monkeypatch.setattr("paperforge.services.embedding.PR9B_MAX_WORKERS", 2)
        prov = _MixedFaultProvider(delay_sec=0.02)
        settled: list[str] = []
        stopped = False

        def _on_item(k: str, st: str) -> None:
            nonlocal stopped
            settled.append(k)
            if len(settled) >= 3:
                stopped = True

        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=prov),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=prov),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=prov),
        ):
            rc1 = run_embedding_build(
                vault,
                _items_for(keys),
                force=True,
                json=False,
                emit_events=True,
                stop_check=lambda: stopped,
                on_item_result=_on_item,
            )

        ndjson1 = _parse_ndjson(capsys.readouterr().out)
        assert rc1 == 130
        assert ndjson1[-1]["event"] == "cancelled"
        assert len(settled) < len(keys), "Stop should abort before embedding all 14 papers"
        with WriterLock(vault):
            pass

        # Resume finishes cleanly to rc == 0:
        prov2 = _MixedFaultProvider()
        with (
            patch("paperforge.embedding.builder.OpenAICompatibleProvider", return_value=prov2),
            patch("paperforge.embedding.dim_detect.OpenAICompatibleProvider", return_value=prov2),
            patch("paperforge.embedding.providers.openai_compatible.OpenAICompatibleProvider", return_value=prov2),
        ):
            rc2 = run_embedding_build(vault, _items_for(keys), resume=True, json=False, emit_events=True)
        ndjson2 = _parse_ndjson(capsys.readouterr().out)
        assert rc2 == 0
        assert ndjson2[-1]["event"] == "result"

    def test_select_embedding_candidates_batched_single_reader_under_load(
        self, tmp_path: Path
    ) -> None:
        from paperforge.memory import db as memory_db
        from paperforge.services.embedding import select_embedding_candidates

        keys = [f"LD{i:03d}" for i in range(1, 101)]
        vault = _make_vault(tmp_path, keys=tuple(keys))

        # 60 eligible (LD001..LD060), 20 no_content (LD061..LD080), 20 not_ready (LD081..LD100)
        _drop_units(vault, tuple(keys[60:80]))
        for k in keys[80:100]:
            _drop_manifest(vault, k)

        reader_calls = 0
        orig_reader = memory_db.open_live_reader

        def _counting_reader(*args, **kwargs):
            nonlocal reader_calls
            reader_calls += 1
            return orig_reader(*args, **kwargs)

        fake_lineage = {
            "papers": {
                k: {"retrieval": "missing" if k in set(keys[80:100]) else "current"}
                for k in keys
            }
        }
        with (
            patch("paperforge.lineage.probe_lineage", return_value=fake_lineage),
            patch("paperforge.memory.db.open_live_reader", side_effect=_counting_reader),
        ):
            result = select_embedding_candidates(vault)

        assert len(result["eligible"]) == 60
        assert len(result["no_content"]) == 20
        assert len(result["not_ready"]) == 20
        assert reader_calls == 1, f"Expected 1 batched reader open for 100 papers, got {reader_calls}"
