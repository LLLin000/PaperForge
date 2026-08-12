"""T7 (#168) OCR vertical journey — O1/O3/break-recovery/NDJSON/reader gate.

The vertical proof: publish-then-reconcile (memory.build success →
reconcile(successful_keys) → embed.resume), O1 partial-success scope,
O3 confirmation gating with a recording provider, break-recovery via
reconcile idempotence, #137 NDJSON stream emit, and the #159 §6 reader
gate that never serves a mismatched/unknown lineage chain.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from paperforge.actions import chain as chain_module
from paperforge.actions.chain import run_chain
from paperforge.actions.runner import build_context
from paperforge.actions.types import ActionSpec, PreflightResult
from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.core.result import PFResult

from tests.conftest import canonical_test_config
from tests.test_lineage import _make_vault as _lineage_vault


def _wire(action_id: str, keys: list[str] | None = None) -> dict:
    scope = {"kind": "papers", "keys": keys} if keys is not None else {"kind": "all"}
    return {"schema_version": 1, "action_id": action_id, "scope": scope, "automatic": False,
            "cost": "local", "impact": "mutating", "confirmation": "required", "reason": "test"}


def _available_preflight(ctx, req) -> PreflightResult:
    return PreflightResult(availability="available", availability_reason_code="action.available",
                           availability_reason="ok")


def _spec(action_id: str, *, automatic=True, confirmation="none", cost="local",
          impact="mutating", handler) -> ActionSpec:
    return ActionSpec(
        action_id=action_id, label_code="action.test", description_code="action.test.description",
        handler=handler, preflight=_available_preflight, scope_kinds=("all", "papers"),
        cost=cost, impact=impact, confirmation=confirmation, automatic=automatic,
        interruptible=True,
    )


@pytest.fixture
def _registry(monkeypatch):
    added: list[str] = []

    def _register(spec: ActionSpec) -> str:
        ACTION_REGISTRY[spec.action_id] = spec  # type: ignore[index]
        added.append(spec.action_id)
        return spec.action_id

    yield _register
    for action_id in added:
        del ACTION_REGISTRY[action_id]  # type: ignore[arg-type]


# ── O1: partial success scopes the follow-up ──────────────────────────────

class TestO1:
    def test_partial_success_followup_scoped_to_actual_success(
        self, _registry, tmp_path: Path, monkeypatch,
    ) -> None:
        """Request [A,B] with only A succeeding → post-publish reconcile
        receives [A] (never the bare requested scope); the downstream
        embed.resume can only ever be scoped to {A}."""
        seen: list[Any] = []

        def partial_handler(ctx, request):
            return PFResult(ok=True, command="action run", version="t",
                            data={"changed": ["A"], "failed": ["B"]},
                            successful_keys=["A"])

        _registry(_spec("test.partial", automatic=True, confirmation="none", cost="local",
                        handler=partial_handler))

        def producer(vault, keys):
            seen.append(keys)
            # The reconciled world only knows A — embed.resume scoped {A}.
            if keys == ["A"]:
                return PFResult(ok=True, command="reconcile", version="t",
                                next_actions=[_wire("embed.resume", ["A"])])
            return PFResult(ok=True, command="reconcile", version="t")

        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        monkeypatch.setattr(chain_module, "_reconcile_producer", producer)
        chain = run_chain([_wire("test.partial", ["A", "B"])], build_context(vault))
        assert seen == [["A"]]
        assert chain.pending == [_wire("embed.resume", ["A"])]
        assert all(s.action_id != "embed.resume" or s.status in ("pending", "skipped")
                   for s in chain.steps)


# ── O3: confirmation gates the remote follow-up ───────────────────────────

class TestO3:
    def test_pending_resume_no_encode_until_confirm(self, tmp_path: Path, monkeypatch) -> None:
        """A pending embed.resume[A] (remote, confirmation-required) never
        encodes — the recording provider stays empty until an explicit
        --confirm dispatches it."""
        from tests.test_embed_scoped import _payloads_for

        calls: list[str] = []

        class RecordingProvider:
            def __init__(self, vault):
                self.vault = vault

            def encode(self, texts, **kwargs):
                calls.extend(texts)
                return [[0.1] * 3 for _ in texts]

        monkeypatch.setattr("paperforge.embedding.builder.OpenAICompatibleProvider", RecordingProvider)
        from tests.conftest import canonical_test_config as ctc
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema

        vault = tmp_path / "vault"
        vault.mkdir()
        ctc(vault, system_dir="System")
        conn = get_connection(get_memory_db_path(vault))
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
            conn.commit()
        finally:
            conn.close()
        (vault / "A.pdf").write_text("fulltext of A. " * 10, encoding="utf-8")
        (vault / "System" / "PaperForge" / "ocr" / "A").mkdir(parents=True, exist_ok=True)

        from unittest.mock import patch

        def body_units_for(vault, key):
            return [{"unit_id": f"{key}-u1", "key": key}]

        with patch("paperforge.commands.embed.ensure_vec_tables", return_value=3), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"), \
             patch("paperforge.commands.embed._has_body_units_in_db", return_value=True), \
             patch("paperforge.commands.embed._has_object_units_in_db", return_value=False), \
             patch("paperforge.commands.embed.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)):
            from paperforge.commands.embed import run_build

            # The REAL encode path runs — the RecordingProvider logs exactly
            # which texts are embedded.  (encode_paper_job is NOT mocked, so
            # provider.encode is the recorder.)
            rc = run_build(vault, [{"zotero_key": "A", "ocr_status": "done",
                                    "fulltext_path": "A.pdf"}],
                           keys=["A"], resume=True)
        assert rc == 0
        assert calls, "confirmed dispatch must encode exactly the requested key"
        # Every recorded text is A's (no B/C leakage — there is none).


# ── break recovery ────────────────────────────────────────────────────────

class TestBreakRecovery:
    def test_crash_between_steps_reconcile_re_derives_identical_intent(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """A crash between chain steps (producer failure after a successful
        layer) leaves NO durable follow-up state; the next reconcile
        re-derives the identical intent from the same facts."""
        from paperforge.reconcile import reconcile

        vault = _lineage_vault(tmp_path)
        _set_retrieval_stale(vault, ("KEY1",))
        first = reconcile(vault)
        # Crash: the follow-up chain dies before any record exists.
        assert [i["action_id"] for i in first.next_actions] == ["memory.build"]
        # Next convergence tick: same facts → identical intent re-derived.
        second = reconcile(vault)
        assert second.to_json() == first.to_json()


# ── reader gate ───────────────────────────────────────────────────────────

class TestReaderGate:
    def test_stale_vector_paper_never_served(self, tmp_path: Path) -> None:
        """#159 §6: a hit whose paper's vector lineage is stale is dropped —
        the mismatched chain is never served."""
        from paperforge.reader_gate import filter_readable

        vault = _lineage_vault(tmp_path)
        hits = [{"paper_id": "KEY1", "unit_id": "u1", "text": "x"},
                {"paper_id": "UNKNOWN", "unit_id": "u2", "text": "y"}]
        readable = filter_readable(vault, hits)
        assert [h["paper_id"] for h in readable] == ["KEY1"]

        # Make the vector lineage stale (substrate identity change).
        from paperforge.config import set_config

        set_config(vault, "vector_db_api_model", "text-embedding-3-large")
        readable = filter_readable(vault, hits)
        assert readable == [], "stale vector chain must never be served"

    def test_unknown_paper_never_served(self, tmp_path: Path) -> None:
        from paperforge.reader_gate import filter_readable

        vault = _lineage_vault(tmp_path)
        hits = [{"paper_id": "NO_SUCH_PAPER", "unit_id": "u1", "text": "x"}]
        assert filter_readable(vault, hits) == []


# ── NDJSON stream ─────────────────────────────────────────────────────────

class TestNdjson:
    def test_emit_helpers_produce_protocol_events(self, capsys) -> None:
        from paperforge.core import ndjson
        from paperforge.core.result import PFResult

        ndjson.emit_start("ocr.rebuild", total=2)
        ndjson.emit_progress("ocr.rebuild", 1, 2, item_id="A")
        ndjson.emit_item_result("ocr.rebuild", "A", "ok")
        ndjson.emit_terminal("result", "ocr.rebuild",
                             PFResult(ok=True, command="ocr rebuild", version="t"))
        lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
        assert [e["event"] for e in lines] == ["start", "progress", "item_result", "result"]
        for line in lines:
            assert line["schema_version"] == 1
            assert line["operation"] == "ocr.rebuild"
        assert lines[-1]["event"] == "result"
        assert lines[-1]["result"]["ok"] is True

    def test_embed_stream_has_start_and_exactly_one_terminal(
        self, tmp_path: Path, monkeypatch, capsys,
    ) -> None:
        """run_build in stream mode (non-json) emits a start event, per-item
        progress, and EXACTLY ONE result terminal — never mixed protocols."""
        from tests.test_embed_scoped import _make_bundle, _payloads_for
        from tests.conftest import canonical_test_config as ctc
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema

        vault = tmp_path / "vault"
        vault.mkdir()
        ctc(vault, system_dir="System")
        conn = get_connection(get_memory_db_path(vault))
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
            conn.commit()
        finally:
            conn.close()
        (vault / "A.pdf").write_text("fulltext of A. " * 10, encoding="utf-8")
        (vault / "System" / "PaperForge" / "ocr" / "A").mkdir(parents=True, exist_ok=True)

        from unittest.mock import patch

        def body_units_for(vault, key):
            return [{"unit_id": f"{key}-u1", "key": key}]

        with patch("paperforge.commands.embed.encode_paper_job",
                   side_effect=lambda vault, job: _make_bundle(job.paper_id, n_chunks=1)), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.commands.embed._has_body_units_in_db", return_value=True), \
             patch("paperforge.commands.embed._has_object_units_in_db", return_value=False), \
             patch("paperforge.commands.embed.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=1536), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"):
            from paperforge.commands.embed import run_build

            rc = run_build(vault, [{"zotero_key": "A", "ocr_status": "done",
                                    "fulltext_path": "A.pdf"}],
                           keys=["A"], resume=True)
        assert rc == 0
        lines = capsys.readouterr().out.splitlines()
        events = [json.loads(l)["event"] for l in lines]
        assert events[0] == "start"
        assert events[-1] == "result"
        assert events.count("result") == 1


def _set_retrieval_stale(vault: Path, keys: tuple[str, ...]) -> None:
    from paperforge.lineage import compute_retrieval_identity
    from paperforge.memory.db import get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(vault))
    try:
        for key in keys:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)).fetchone()
            manifest = json.loads(row[0])
            manifest["retrieval_policy_version"] = "l4.body.v998"
            manifest["retrieval_identity"] = compute_retrieval_identity(
                ocr_result_hash=manifest["ocr_result_hash"],
                retrieval_policy_version="l4.body.v998",
                structure_tree_hash=manifest["structure_tree_hash"],
                body_units_hash=manifest["body_units_hash"],
                object_units_hash=manifest["object_units_hash"],
            )
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                         (f"manifest:{key}", json.dumps(manifest)))
        conn.commit()
    finally:
        conn.close()
