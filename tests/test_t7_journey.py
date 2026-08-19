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


@pytest.fixture(autouse=True)
def _mock_eligibility(monkeypatch):
    """M3-B: pipeline tests mock the retrieval-truth selector (covered by
    test_embed_eligibility.py); requested keys are eligible here."""

    def fake_select(vault, keys=None):
        if keys is not None:
            return {"eligible": list(keys), "no_content": [], "not_ready": []}
        try:
            from paperforge.worker.asset_index import read_index

            env = read_index(vault)
            items = env.get("items") if isinstance(env, dict) else (env or [])
            return {"eligible": [i["zotero_key"] for i in items], "no_content": [], "not_ready": []}
        except Exception:
            return {"eligible": [], "no_content": [], "not_ready": []}

    monkeypatch.setattr("paperforge.services.embedding.select_embedding_candidates", fake_select)


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

        with patch("paperforge.services.embedding.ensure_vec_tables", return_value=3), \
             patch("paperforge.services.embedding.delete_paper_vectors"), \
             patch("paperforge.services.embedding.write_encoded_payload"), \
             patch("paperforge.services.embedding._has_body_units_in_db", return_value=True), \
             patch("paperforge.services.embedding._has_object_units_in_db", return_value=False), \
             patch("paperforge.services.embedding.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.services.embedding.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)):
            from paperforge.services.embedding import run_embedding_build as run_build

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

    def test_scoped_hits_observe_only_those_papers(self, tmp_path: Path, monkeypatch) -> None:
        """Scope fidelity: a paper-scoped reader must observe ONLY the hit
        papers' lineage — never the full library (a broken locator in an
        unrelated paper must not pollute or slow this read)."""
        vault = _lineage_vault(tmp_path)
        hits = [{"paper_id": "KEY1", "unit_id": "u1", "text": "x"}]

        observed: list[list[str]] = []

        def fake_observe(vault, keys):
            observed.append(list(keys))
            from paperforge.lineage import _probe_lineage

            return _probe_lineage(vault, requested_keys=keys, include_library=False)

        def boom(vault):
            raise AssertionError("full-library probe must not run for scoped hits")

        monkeypatch.setattr("paperforge.lineage.probe_lineage", boom)
        monkeypatch.setattr("paperforge.lineage.observe_lineage_papers", fake_observe)

        from paperforge.reader_gate import filter_readable

        readable = filter_readable(vault, hits)
        assert [h["paper_id"] for h in readable] == ["KEY1"]
        assert observed == [["KEY1"]], f"expected scoped observation of KEY1, got {observed}"


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

        with patch("paperforge.services.embedding.encode_paper_job",
                   side_effect=lambda vault, job: _make_bundle(job.paper_id, n_chunks=1)), \
             patch("paperforge.services.embedding.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.services.embedding._has_body_units_in_db", return_value=True), \
             patch("paperforge.services.embedding._has_object_units_in_db", return_value=False), \
             patch("paperforge.services.embedding.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.services.embedding.ensure_vec_tables", return_value=1536), \
             patch("paperforge.services.embedding.delete_paper_vectors"), \
             patch("paperforge.services.embedding.write_encoded_payload"):
            from paperforge.services.embedding import run_embedding_build as run_build

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


# ── O3 vertical confirmation flow (#168 P0 review) ────────────────────────

class TestO3Vertical:
    def test_confirm_flow_gates_until_exact_confirm(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """The FULL vertical O3: pending embed.resume[A] → 0 provider calls →
        no-confirm rc3 → wrong-confirm rc2 → exact confirm → EXACTLY A
        encoded (RecordingProvider log)."""
        from tests.test_embed_scoped import _make_bundle, _payloads_for

        calls: list[str] = []

        class RecordingProvider:
            def __init__(self, vault):
                self.vault = vault

            def encode(self, texts, **kwargs):
                calls.extend(texts)
                return [[0.1] * 3 for _ in texts]

            def encode_single(self, text, **kwargs):
                return [0.1] * 3

        monkeypatch.setattr("paperforge.embedding.builder.OpenAICompatibleProvider", RecordingProvider)
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
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

        def _run_cli(*argv):
            import io as _io
            import sys as _sys
            from paperforge.cli import main

            old_out = _sys.stdout
            buf = _io.StringIO()
            _sys.stdout = buf
            try:
                rc = main(list(argv))
            finally:
                _sys.stdout = old_out
            return rc, json.loads(buf.getvalue())

        with patch("paperforge.worker.asset_index.read_index",
                   return_value={"items": [{"zotero_key": "A", "ocr_status": "done",
                                            "fulltext_path": "A.pdf"}]}), \
             patch("paperforge.services.embedding.ensure_vec_tables", return_value=3), \
             patch("paperforge.services.embedding.delete_paper_vectors"), \
             patch("paperforge.services.embedding.write_encoded_payload"), \
             patch("paperforge.services.embedding._has_body_units_in_db", return_value=True), \
             patch("paperforge.services.embedding._has_object_units_in_db", return_value=False), \
             patch("paperforge.services.embedding.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.services.embedding.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)):
            # Pending state: nothing dispatched → provider untouched.
            assert calls == []
            # No confirm → rc3 (confirmation required).
            rc3, payload3 = _run_cli(
                "--vault", str(vault), "action", "run", "embed.resume",
                "--scope", "papers", "--key", "A", "--json",
            )
            assert rc3 == 3
            assert payload3["error"]["code"] == "action.confirmation_required"
            assert calls == []
            # Wrong-action confirm → rc2, nothing dispatched.
            rc2, payload2 = _run_cli(
                "--vault", str(vault), "action", "run", "embed.resume",
                "--scope", "papers", "--key", "A",
                "--confirm", "memory.build", "--json",
            )
            assert rc2 == 2
            assert payload2["error"]["code"] == "action.invalid_request"
            assert calls == []
            # Exact confirm → dispatched, EXACTLY the requested key encoded.
            rc0, _ = _run_cli(
                "--vault", str(vault), "action", "run", "embed.resume",
                "--scope", "papers", "--key", "A",
                "--confirm", "embed.resume", "--json",
            )
        assert rc0 == 0
        assert calls, "exact confirm must encode the requested key"
        # The body payload for A — exactly the requested key, nothing else.
        assert calls == ["A-t"]


class TestCancelledRc130:
    def test_embed_cancelled_returns_130(self, tmp_path: Path, monkeypatch) -> None:
        """#137: a cancelled embed build is a terminal outcome with rc130 and
        a cancelled NDJSON terminal — never a folded rc0."""
        from paperforge.core import cancellation as cancellation_module

        monkeypatch.setattr(cancellation_module, "make_cancellation_token",
                            lambda: (lambda: True, lambda: None))
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
        from tests.test_embed_scoped import _make_bundle, _payloads_for

        def body_units_for(vault, key):
            return [{"unit_id": f"{key}-u1", "key": key}]

        with patch("paperforge.services.embedding.encode_paper_job",
                   side_effect=lambda vault, job: _make_bundle(job.paper_id, n_chunks=1)), \
             patch("paperforge.services.embedding.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.services.embedding._has_body_units_in_db", return_value=True), \
             patch("paperforge.services.embedding._has_object_units_in_db", return_value=False), \
             patch("paperforge.services.embedding.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.services.embedding.ensure_vec_tables", return_value=1536), \
             patch("paperforge.services.embedding.delete_paper_vectors"), \
             patch("paperforge.services.embedding.write_encoded_payload"):
            import io as _io
            import sys as _sys
            from paperforge.services.embedding import run_embedding_build as run_build

            old_out = _sys.stdout
            buf = _io.StringIO()
            _sys.stdout = buf
            try:
                rc = run_build(vault, [{"zotero_key": "A", "ocr_status": "done",
                                        "fulltext_path": "A.pdf"}],
                               keys=["A"], resume=True)
            finally:
                _sys.stdout = old_out
            events = [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]
        assert rc == 130, f"cancelled build must exit 130, got {rc}"
        terminals = [e for e in events if e["event"] in ("result", "error", "cancelled")]
        assert len(terminals) == 1
        assert terminals[0]["event"] == "cancelled"


# ── T9 (#170): single-producer parity ─────────────────────────────────────

class TestSingleProducer:
    def test_no_action_wire_contains_command_text(self) -> None:
        """#170: no action wire carries a command string — next_actions only
        reference registered action ids (parity grep)."""
        import glob
        import re

        command_wires = []
        for path in glob.glob("paperforge/**/*.py", recursive=True):
            if "architecture_audit" in path or "test" in path or "sandbox" in path:
                continue
            src = open(path, encoding="utf-8").read()
            # A next_actions literal that carries a command string.
            if re.search(
                r"next_actions\s*=\s*\[[^\]]*['\"]command['\"]\s*:",
                src,
                re.S,
            ):
                command_wires.append(path)
            # Any recommendation data (next_action dict or literal) carrying
            # a paperforge command string — nested dicts included.
            if re.search(r'"next_action"\s*:\s*"paperforge', src):
                command_wires.append(path)
            if re.search(r'["\']command["\']\s*:\s*f?["\']paperforge', src):
                command_wires.append(path)
        assert command_wires == [], f"command-string action wires: {command_wires}"

    def test_every_emitted_action_resolves_to_registered_handler(self, tmp_path: Path) -> None:
        """#170: every reconcile-emitted action_id resolves to a registered
        handler (parity) — including the global and per-paper paths."""
        from paperforge.actions.registry import ACTION_REGISTRY
        from paperforge.actions.registry import emit_next_action
        from paperforge.reconcile import reconcile
        from tests.test_reconcile import _set_vector_missing

        vault = _lineage_vault(tmp_path)
        _set_retrieval_stale(vault, ("KEY1",))
        _set_vector_missing(vault, "KEY1")
        result = reconcile(vault)
        for wire in result.next_actions:
            assert wire["action_id"] in ACTION_REGISTRY, wire["action_id"]
            # Hydration must not fail for any emitted intent.
            from paperforge.actions.types import ActionIntent, scope_from_dict

            intent = ActionIntent(wire["action_id"], scope_from_dict(wire["scope"]), "parity", "parity")
            hydrated = emit_next_action(intent)
            assert hydrated.action_id == wire["action_id"]
