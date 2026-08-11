"""Reconcile module tests (#166 / T5, #159 §3).

Pure derivation + intent emission; global-first; minimal repair frontier;
scope merging; unknown fails closed; operation vs policy separation.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.reconcile import reconcile

from tests.conftest import canonical_test_config
from tests.test_lineage import _make_vault as _lineage_vault


def _run_cli(*argv: str) -> tuple[int, dict]:
    import io as _io

    from paperforge.cli import main

    old_out = sys.stdout
    buf = _io.StringIO()
    sys.stdout = buf
    try:
        rc = main(list(argv))
    finally:
        sys.stdout = old_out
    return rc, json.loads(buf.getvalue())


def _db(vault: Path):
    from paperforge.memory.db import get_connection, get_memory_db_path

    return get_connection(get_memory_db_path(vault))


def _set_retrieval_stale(vault: Path, keys: tuple[str, ...]) -> None:
    """Simulate a retrieval change: rewrite manifests with a NEW retrieval
    identity (policy/units changed) so probe reports retrieval stale."""
    from paperforge.lineage import compute_retrieval_identity

    conn = _db(vault)
    try:
        for key in keys:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)).fetchone()
            manifest = json.loads(row[0])
            manifest["retrieval_policy_version"] = "l4.body.v999"
            manifest["retrieval_identity"] = compute_retrieval_identity(
                ocr_result_hash=manifest["ocr_result_hash"],
                retrieval_policy_version="l4.body.v999",
                structure_tree_hash=manifest["structure_tree_hash"],
                body_units_hash=manifest["body_units_hash"],
                object_units_hash=manifest["object_units_hash"],
            )
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                         (f"manifest:{key}", json.dumps(manifest)))
        conn.commit()
    finally:
        conn.close()


def _set_ocr_stale(vault: Path, key: str) -> None:
    """Touch the OCR artifact after publish so probe reports ocr stale."""
    ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / key
    (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps({"blocks": [key, "changed"]}), encoding="utf-8"
    )


def _set_vector_stale(vault: Path, key: str) -> None:
    """Change the configured embedding model so vector identity differs."""
    from paperforge.config import set_config

    set_config(vault, "vector_db_api_model", "text-embedding-3-large")


def _intent_ids(payload: dict) -> list[str]:
    return [i["action_id"] for i in payload["intents"]]


# ── pure derivation / idempotence ─────────────────────────────────────────

class TestPureDerivation:
    def test_healthy_library_emits_nothing(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        vault = _lineage_vault(tmp_path)
        payload = reconcile(vault)
        assert payload["intents"] == []
        assert payload["facet_summary"]["current"] == 3

    def test_idempotent_same_facts_same_result(self, tmp_path: Path) -> None:
        vault = _lineage_vault(tmp_path)
        first = reconcile(vault)
        second = reconcile(vault)
        assert first == second


# ── global-first ──────────────────────────────────────────────────────────

class TestGlobalFirst:
    def test_no_db_emits_single_global_memory_build(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        payload = reconcile(vault)
        assert _intent_ids(payload) == ["memory.build"]
        assert payload["global"]["memory_substrate_ok"] is False

    def test_vector_substrate_incompatible_emits_global_embed_build(self, tmp_path: Path) -> None:
        """Credential missing -> vector substrate incompatible -> exactly one
        global embed.build; per-paper facets blocked_global."""
        vault = _lineage_vault(tmp_path)
        payload = reconcile(vault)
        assert _intent_ids(payload) == ["embed.build"]
        assert payload["global"]["vector_substrate_ok"] is False
        for reasons in payload["per_paper"].values():
            assert reasons["reasons"] == ["blocked_global:vector_substrate"]


# ── minimal repair frontier + unknown fails closed ────────────────────────

class TestMinimalFrontier:
    def test_ocr_stale_emits_ocr_run(self, tmp_path: Path, monkeypatch) -> None:
        vault = _lineage_vault(tmp_path)
        _set_ocr_stale(vault, "KEY1")
        # ensure credential available so substrate observation passes
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_OCR__DEFAULT", "t")
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        payload = reconcile(vault)
        intents = payload["intents"]
        assert [i["action_id"] for i in intents] == ["ocr.run"]
        assert intents[0]["scope"] == {"kind": "papers", "keys": ["KEY1"]}

    def test_retrieval_stale_emits_memory_build_only_when_ocr_current(self, tmp_path: Path, monkeypatch) -> None:
        vault = _lineage_vault(tmp_path)
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        _set_retrieval_stale(vault, ("KEY1",))
        payload = reconcile(vault)
        assert [i["action_id"] for i in payload["intents"]] == ["memory.build"]

    def test_ocr_stale_blocks_downstream_retrieval(self, tmp_path: Path, monkeypatch) -> None:
        """Minimal frontier: with OCR stale, retrieval's prerequisite is not
        satisfied — no memory.build for the same paper."""
        vault = _lineage_vault(tmp_path)
        _set_ocr_stale(vault, "KEY1")
        _set_retrieval_stale(vault, ("KEY1",))
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_OCR__DEFAULT", "t")
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        payload = reconcile(vault)
        assert [i["action_id"] for i in payload["intents"]] == ["ocr.run"]

    def test_unknown_retrieval_emits_no_intent(self, tmp_path: Path, monkeypatch) -> None:
        """Unknown per-paper lineage alone -> NO per-paper repair intent
        (never stale, never mass rebuild); reasons surface."""
        vault = _lineage_vault(tmp_path)
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        conn = _db(vault)
        try:
            manifest = json.loads(conn.execute(
                "SELECT value FROM meta WHERE key='manifest:KEY1'"
            ).fetchone()[0])
            del manifest["retrieval_identity"]
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                         ("manifest:KEY1", json.dumps(manifest)))
            conn.commit()
        finally:
            conn.close()
        payload = reconcile(vault)
        assert [i["action_id"] for i in payload["intents"]] == []
        assert "unknown:retrieval" in payload["per_paper"]["KEY1"]["reasons"]

    def test_vector_stale_emits_embed_resume(self, tmp_path: Path, monkeypatch) -> None:
        vault = _lineage_vault(tmp_path)
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        _set_vector_stale(vault, "KEY1")
        payload = reconcile(vault)
        assert [i["action_id"] for i in payload["intents"]] == ["embed.resume"]
        assert payload["intents"][0]["scope"]["keys"] == ["KEY1"]


# ── scope merging ─────────────────────────────────────────────────────────

class TestScopeMerging:
    def test_100_stale_papers_merge_into_one_intent(self, tmp_path: Path, monkeypatch) -> None:
        """Scope merging: many stale papers -> ONE memory.build with the full
        key list (canonical action merge)."""
        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        from tests.test_lineage import _write_ocr_paper, _manifest_for
        from paperforge.lineage import compute_vector_identity, compute_embedding_identity
        from paperforge.embedding._config import get_api_model, get_effective_api_base_url

        keys = [f"K{i:03d}" for i in range(100)]
        for key in keys:
            _write_ocr_paper(vault, key)
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            from paperforge.memory.schema import ensure_schema

            ensure_schema(conn)
            for key in keys:
                ocr_hash = (
                    vault / "99_System" / "PaperForge" / "ocr" / key / "index" / "result-hash.txt"
                ).read_text(encoding="utf-8").strip()
                manifest = _manifest_for(key, ocr_hash)
                conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                             (f"manifest:{key}", json.dumps(manifest)))
                conn.execute(
                    "INSERT OR REPLACE INTO vec_fulltext_meta (paper_id, chunk_index, text) VALUES (?, ?, ?)",
                    (key, 0, f"{key}-ft"),
                )
                identity = compute_vector_identity(
                    retrieval_identity=manifest["retrieval_identity"],
                    embedding_identity=compute_embedding_identity(
                        endpoint=get_effective_api_base_url(vault),
                        model=get_api_model(vault),
                        dimension=1536,
                    ),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO lineage (paper_id, layer, identity, derived_from, embedding_identity, updated_at) "
                    "VALUES (?, 'vector', ?, ?, ?, '2026-01-01T00:00:00+00:00')",
                    (key, identity, manifest["retrieval_identity"],
                     compute_embedding_identity(
                         endpoint=get_effective_api_base_url(vault),
                         model=get_api_model(vault),
                         dimension=1536,
                     )),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_dimension', '1536')"
                )
            conn.commit()
        finally:
            conn.close()

        # 100 stale retrievals (policy bumped).
        _set_retrieval_stale(vault, tuple(keys))
        monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "t")
        payload = reconcile(vault)
        memory_intents = [i for i in payload["intents"] if i["action_id"] == "memory.build"]
        assert len(memory_intents) == 1
        assert len(memory_intents[0]["scope"]["keys"]) == 100


# ── operation vs policy separation ────────────────────────────────────────

class TestOperationPolicySeparation:
    def test_policy_comes_from_registry(self) -> None:
        """Reconcile emits the operation; cost/confirmation come from the
        registry (T2) — embed.resume intents carry the registered policy."""
        from paperforge.actions.types import ActionIntent, PapersScope
        from paperforge.actions.registry import emit_next_action

        intent = ActionIntent(
            "embed.resume", PapersScope(("A",)),
            "lineage.vector_defect", "stale",
        )
        wire = emit_next_action(intent).to_dict()
        spec = ACTION_REGISTRY["embed.resume"]
        assert wire["cost"] == spec.cost == "remote_possible"
        assert wire["confirmation"] == spec.confirmation == "required"
        assert wire["automatic"] == spec.automatic is False

    def test_cli_emits_next_actions_channel(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        rc, payload = _run_cli("--vault", str(vault), "reconcile", "--json")
        assert rc == 0
        assert payload["ok"] is True
        assert payload["command"] == "reconcile"
        assert payload["data"]["global"]["memory_substrate_ok"] is False
        assert [i["action_id"] for i in payload["next_actions"]] == ["memory.build"]
