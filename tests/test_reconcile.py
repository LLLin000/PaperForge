"""Reconcile module tests (#166 / T5 + corrective, #159 §3).

Pure derivation + intent emission; global-first; minimal repair frontier;
scope merging; unknown fails closed; operation vs policy separation;
substrate ≠ credential availability (P0-1); W2 no-blind-retry gate (P0-2);
single next_actions channel (P1-1); unregistered fail-closed (P1-2);
facet_summary independent of global-first (P1-3).
"""

from __future__ import annotations

import json
from pathlib import Path

from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.actions.types import ActionIntent, PapersScope
from paperforge.reconcile import (
    _intent_input_digest,
    observe,
    reconcile,
    record_last_attempt,
)

from tests.conftest import canonical_test_config
from tests.test_lineage import _make_vault as _lineage_vault


def _run_cli(*argv: str) -> tuple[int, dict]:
    import io as _io

    from paperforge.cli import main

    old_out = __import__("sys").stdout
    buf = _io.StringIO()
    __import__("sys").stdout = buf
    try:
        rc = main(list(argv))
    finally:
        __import__("sys").stdout = old_out
    return rc, json.loads(buf.getvalue())


def _db(vault: Path):
    from paperforge.memory.db import get_connection, get_memory_db_path

    return get_connection(get_memory_db_path(vault))


def _set_retrieval_stale(vault: Path, keys: tuple[str, ...]) -> None:
    _set_retrieval_stale_variant(vault, keys, policy="l4.body.v999")


def _set_retrieval_stale_variant(vault: Path, keys: tuple[str, ...], policy: str) -> None:
    """Simulate a retrieval change under a SPECIFIC policy version, so the
    written retrieval identity differs between calls (W2 digest material)."""
    from paperforge.lineage import compute_retrieval_identity

    conn = _db(vault)
    try:
        for key in keys:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)).fetchone()
            manifest = json.loads(row[0])
            manifest["retrieval_policy_version"] = policy
            manifest["retrieval_identity"] = compute_retrieval_identity(
                ocr_result_hash=manifest["ocr_result_hash"],
                retrieval_policy_version=policy,
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


def _set_vector_missing(vault: Path, key: str) -> None:
    """Delete a paper's vector rows so probe reports vector missing while
    the substrate stays compatible (per-paper deficit → embed.resume)."""
    conn = _db(vault)
    try:
        conn.execute("DELETE FROM vec_fulltext_meta WHERE paper_id = ?", (key,))
        conn.execute("DELETE FROM vec_body_meta WHERE paper_id = ?", (key,))
        conn.execute("DELETE FROM vec_objects_meta WHERE paper_id = ?", (key,))
        conn.execute("DELETE FROM lineage WHERE paper_id = ? AND layer = 'vector'", (key,))
        conn.commit()
    finally:
        conn.close()


def _set_model_changed(vault: Path) -> None:
    """Change the configured embedding model — desired identity diverges
    from the published substrate → GLOBAL embed.build (P0-1)."""
    from paperforge.config import set_config

    set_config(vault, "vector_db_api_model", "text-embedding-3-large")


def _intent_ids(result) -> list[str]:
    return [i["action_id"] for i in result.next_actions]


# ── pure derivation / idempotence ─────────────────────────────────────────

class TestPureDerivation:
    def test_healthy_library_emits_nothing(self, tmp_path: Path) -> None:
        vault = _lineage_vault(tmp_path)
        result = reconcile(vault)
        assert result.next_actions == []
        assert result.data["facet_summary"]["current"] == 3

    def test_idempotent_same_facts_same_result(self, tmp_path: Path) -> None:
        vault = _lineage_vault(tmp_path)
        assert reconcile(vault).to_json() == reconcile(vault).to_json()


# ── global-first ──────────────────────────────────────────────────────────

class TestGlobalFirst:
    def test_no_db_emits_single_global_memory_build(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        result = reconcile(vault)
        assert _intent_ids(result) == ["memory.build"]
        assert result.data["global"]["memory_substrate_ok"] is False

    def test_model_change_emits_global_embed_build_and_summary_counts(
        self, tmp_path: Path,
    ) -> None:
        """Desired embedding identity diverged from the published substrate
        → exactly one global embed.build; per-paper facets blocked_global;
        facet_summary STILL counts the observed facets (P1-3)."""
        vault = _lineage_vault(tmp_path)
        _set_model_changed(vault)
        result = reconcile(vault)
        assert _intent_ids(result) == ["embed.build"]
        assert result.data["global"]["vector_substrate_ok"] is False
        # Model change flips the vector facet stale (correct observation) —
        # the summary must count the REAL facets, never zero (P1-3).
        assert result.data["facet_summary"] == {"current": 2, "stale": 1, "missing": 0, "unknown": 0}
        for reasons in result.data["per_paper"].values():
            assert reasons["reasons"] == ["blocked_global:vector_substrate"]

    def test_missing_credential_does_not_block_unrelated_repair(
        self, tmp_path: Path,
    ) -> None:
        """P0-1: no embedding credential configured must NOT flip the
        substrate state — OCR/retrieval repair still flows, and the vector
        intent is emitted (availability is the registry preflight's job)."""
        vault = _lineage_vault(tmp_path)
        _set_ocr_stale(vault, "KEY1")
        result = reconcile(vault)
        assert _intent_ids(result) == ["ocr.run"]
        assert result.data["global"]["vector_substrate_ok"] is True


# ── minimal repair frontier + unknown fails closed ────────────────────────

class TestMinimalFrontier:
    def test_ocr_stale_emits_ocr_run(self, tmp_path: Path) -> None:
        vault = _lineage_vault(tmp_path)
        _set_ocr_stale(vault, "KEY1")
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["ocr.run"]
        assert result.next_actions[0]["scope"] == {"kind": "papers", "keys": ["KEY1"]}

    def test_retrieval_stale_emits_memory_build_only_when_ocr_current(self, tmp_path: Path) -> None:
        vault = _lineage_vault(tmp_path)
        _set_retrieval_stale(vault, ("KEY1",))
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["memory.build"]

    def test_ocr_stale_blocks_downstream_retrieval(self, tmp_path: Path) -> None:
        """Minimal frontier: with OCR stale, retrieval's prerequisite is not
        satisfied — no memory.build for the same paper."""
        vault = _lineage_vault(tmp_path)
        _set_ocr_stale(vault, "KEY1")
        _set_retrieval_stale(vault, ("KEY1",))
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["ocr.run"]

    def test_unknown_retrieval_emits_no_intent(self, tmp_path: Path) -> None:
        """Unknown per-paper lineage alone -> NO per-paper repair intent
        (never stale, never mass rebuild); reasons surface."""
        vault = _lineage_vault(tmp_path)
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
        result = reconcile(vault)
        assert result.next_actions == []
        assert "unknown:retrieval" in result.data["per_paper"]["KEY1"]["reasons"]

    def test_vector_missing_emits_embed_resume(self, tmp_path: Path) -> None:
        """Per-paper vector deficit on a COMPATIBLE substrate → embed.resume
        (keys), NOT a global build (P0-1 classification)."""
        vault = _lineage_vault(tmp_path)
        _set_vector_missing(vault, "KEY1")
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["embed.resume"]
        assert result.next_actions[0]["scope"]["keys"] == ["KEY1"]

    def test_pristine_vector_substrate_emits_per_paper_resume(self, tmp_path: Path) -> None:
        """#167 P0-4: no vector rows AND no published identity version
        (pristine) is a per-paper missing deficit — embed.resume(keys),
        NEVER a legacy global embed.build."""
        vault = _lineage_vault(tmp_path)
        conn = _db(vault)
        try:
            for table in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta"):
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM build_state")
            conn.commit()
        finally:
            conn.close()
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["embed.resume"]
        assert result.data["global"]["vector_substrate_ok"] is True
        assert result.data["global"]["reasons"] == []  # no substrate defect


# ── scope merging ─────────────────────────────────────────────────────────

class TestScopeMerging:
    def test_100_stale_papers_merge_into_one_intent(self, tmp_path: Path) -> None:
        """Scope merging: many stale papers -> ONE memory.build with the full
        key list (canonical action merge)."""
        keys = tuple(f"K{i:03d}" for i in range(100))
        vault = _lineage_vault(tmp_path, keys=keys)
        _set_retrieval_stale(vault, keys)
        result = reconcile(vault)
        memory_intents = [i for i in result.next_actions if i["action_id"] == "memory.build"]
        assert len(memory_intents) == 1
        assert len(memory_intents[0]["scope"]["keys"]) == 100


# ── W2 not-a-retry ────────────────────────────────────────────────────────

class TestW2Gate:
    def _stale_retrieval_with_digest(self, tmp_path: Path) -> tuple[Path, ActionIntent, str]:
        vault = _lineage_vault(tmp_path)
        _set_retrieval_stale(vault, ("KEY1",))
        obs = observe(vault)
        intent = ActionIntent(
            "memory.build", PapersScope(("KEY1",)),
            "lineage.retrieval_defect", "stale",
        )
        return vault, intent, _intent_input_digest(obs, intent, vault)

    def test_failed_last_attempt_same_digest_suppresses(self, tmp_path: Path) -> None:
        """W2: same input digest + failed last attempt → NO re-emission."""
        vault, intent, digest = self._stale_retrieval_with_digest(tmp_path)
        record_last_attempt(vault, action_id="memory.build", scope=intent.scope,
                            input_digest=digest, outcome="failed", error_code="memory.build_failed")
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == []
        assert any("w2.suppressed:memory.build" in d for d in result.data["diagnostics"])

    def test_changed_digest_reemits(self, tmp_path: Path) -> None:
        """W2: the input digest changed (R1 → R2) since the failed attempt →
        emission allowed again."""
        vault, intent, digest = self._stale_retrieval_with_digest(tmp_path)
        record_last_attempt(vault, action_id="memory.build", scope=intent.scope,
                            input_digest=digest, outcome="failed")
        # Cause a NEW stale with a DIFFERENT retrieval identity (R1 → R2):
        # the semantic digest changes, so re-emission is allowed.
        _set_retrieval_stale_variant(vault, ("KEY1",), policy="l4.body.v997")
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["memory.build"]

    def test_succeeded_last_attempt_allows_emission(self, tmp_path: Path) -> None:
        """W2: a succeeded last attempt never suppresses (only failed does)."""
        vault, intent, digest = self._stale_retrieval_with_digest(tmp_path)
        record_last_attempt(vault, action_id="memory.build", scope=intent.scope,
                            input_digest=digest, outcome="succeeded")
        result = reconcile(vault)
        assert [i["action_id"] for i in result.next_actions] == ["memory.build"]

    def test_record_is_overwrite_only(self, tmp_path: Path) -> None:
        """The last-attempt record stays bounded: same canonical key is
        overwritten, never appended (no history)."""
        vault, intent, digest = self._stale_retrieval_with_digest(tmp_path)
        record_last_attempt(vault, action_id="memory.build", scope=intent.scope,
                            input_digest=digest, outcome="failed", error_code="e1")
        record_last_attempt(vault, action_id="memory.build", scope=intent.scope,
                            input_digest=digest, outcome="failed", error_code="e2")
        from paperforge.reconcile import read_last_attempts

        attempts = read_last_attempts(vault)
        assert len(attempts) == 1
        assert attempts["memory.build:papers:KEY1"]["error_code"] == "e2"


# ── operation vs policy separation ────────────────────────────────────────

class TestOperationPolicySeparation:
    def test_policy_comes_from_registry(self) -> None:
        """Reconcile emits the operation; cost/confirmation come from the
        registry (T2) — embed.resume intents carry the registered policy."""
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

    def test_unregistered_action_fails_closed(self, tmp_path: Path, monkeypatch) -> None:
        """P1-2: an unregistered action is NEVER emitted; a structured
        diagnostic records the invariant break instead."""
        from paperforge import reconcile as reconcile_mod

        vault = _lineage_vault(tmp_path)
        _set_ocr_stale(vault, "KEY1")

        real_emit = reconcile_mod.emit_next_action

        def broken_emit(intent):
            if intent.action_id == "ocr.run":
                raise KeyError(intent.action_id)
            return real_emit(intent)

        monkeypatch.setattr(reconcile_mod, "emit_next_action", broken_emit)
        result = reconcile(vault)
        assert result.next_actions == []
        assert "reconcile.action_unregistered:ocr.run" in result.data["diagnostics"]

    def test_cli_emits_next_actions_channel(self, tmp_path: Path) -> None:
        """P1-1: the CLI surfaces intents ONLY on next_actions; data carries
        no separate 'intents' wire."""
        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        rc, payload = _run_cli("--vault", str(vault), "reconcile", "--json")
        assert rc == 0
        assert payload["ok"] is True
        assert payload["command"] == "reconcile"
        assert payload["data"]["global"]["memory_substrate_ok"] is False
        assert "intents" not in payload["data"]
        assert [i["action_id"] for i in payload["next_actions"]] == ["memory.build"]
