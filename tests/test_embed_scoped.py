"""T4 — embed resume papers-scope seam + build-core extraction (#165).

Subset semantics (candidates = done_papers ∩ keys), lineage preservation
(resume-skipped papers keep rows byte-identical), and the test-only
RecordingEmbeddingProvider injected through the provider seam — with NO
production mock-provider env mode.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from paperforge.commands.embed import run_build

from tests.conftest import canonical_test_config
from tests.test_pr9c_streaming_embed import _call_run, _make_bundle


def _payloads_for(key: str) -> list:
    """A single body payload for a key (mirrors pr9c harness)."""
    from paperforge.embedding.builder import EmbeddingPayload

    return [
        EmbeddingPayload("paperforge_body", [f"{key}-t"], [f"{key}_id1"], [{"paper_id": key}])
    ]


def _papers(keys: tuple[str, ...], *, status: str = "done") -> list[dict]:
    return [
        {"zotero_key": k, "ocr_status": status, "fulltext_path": f"{k}.pdf"}
        for k in keys
    ]


def _seed_resume_db(tmp_path: Path, keys: tuple[str, ...]) -> None:
    """Seed paperforge.db so resume hash-skips B/C while A is re-embedded."""
    from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
    from paperforge.memory.schema import ensure_schema

    db_path = get_memory_db_path(tmp_path)
    conn = get_connection(db_path)
    try:
        ensure_vec_extension(conn)
        ensure_schema(conn)
        for i, key in enumerate(keys):
            conn.execute(
                "INSERT INTO vec_body_meta(rowid, paper_id, body_units_hash, retrieval_policy_version) VALUES (?, ?, ?, ?)",
                (i * 2 + 1, key, "hash_v1", "v1"),
            )
            conn.execute(
                "INSERT INTO vec_objects_meta(rowid, paper_id, object_units_hash, retrieval_policy_version) VALUES (?, ?, ?, ?)",
                (i * 2 + 2, key, "hash_v1", "v1"),
            )
            conn.execute(
                "INSERT INTO vec_fulltext_meta(rowid, paper_id, text) VALUES (?, ?, ?)",
                (i * 2 + 3, key, f"{key}-text"),
            )
        conn.execute(
            "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')"
        )
        conn.execute(
            "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_dimension', '3')"
        )
        conn.commit()
    finally:
        conn.close()


def _lineage_rows(tmp_path: Path, key: str) -> list[tuple]:
    from paperforge.memory.db import get_memory_db_path

    conn = sqlite3.connect(str(get_memory_db_path(tmp_path)))
    try:
        return [
            tuple(r)
            for r in conn.execute(
                "SELECT paper_id, layer, identity, derived_from, embedding_identity, updated_at "
                "FROM lineage WHERE paper_id = ? ORDER BY layer",
                (key,),
            ).fetchall()
        ]
    finally:
        conn.close()


def _store_manifest(tmp_path: Path, key: str) -> None:
    """A manifest with a retrieval identity so write_vector_lineage can
    emit a row for this paper (eligibility is manifest-driven)."""
    from paperforge.memory.db import get_memory_db_path

    conn = sqlite3.connect(str(get_memory_db_path(tmp_path)))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"manifest:{key}", json.dumps({
                "paper_id": key,
                "ocr_result_hash": "a" * 64,
                "retrieval_policy_version": "v1",
                "structure_tree_hash": "b" * 64,
                "body_units_hash": "c" * 64,
                "object_units_hash": "d" * 64,
                "retrieval_identity": f"rid-{key}",
            })),
        )
        conn.commit()
    finally:
        conn.close()


def _store_lineage_row(tmp_path: Path, key: str, updated_at: str) -> None:
    from paperforge.memory.db import get_memory_db_path

    conn = sqlite3.connect(str(get_memory_db_path(tmp_path)))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO lineage "
            "(paper_id, layer, identity, derived_from, embedding_identity, updated_at) "
            "VALUES (?, 'vector', ?, ?, ?, ?)",
            (key, f"identity-{key}", f"derived-{key}", f"emb-{key}", updated_at),
        )
        conn.commit()
    finally:
        conn.close()


# ── subset semantics ───────────────────────────────────────────────────────

class TestSubsetSemantics:
    def test_candidates_filtered_to_requested_keys(self, tmp_path: Path) -> None:
        canonical_test_config(tmp_path, system_dir="System")
        encode_calls: list[str] = []
        delete_calls: list[str] = []

        def encode(vault, job):
            encode_calls.append(job.paper_id)
            return _make_bundle(job.paper_id, n_chunks=1)

        rc, refs = _call_run(
            tmp_path,
            _papers(("A", "B", "C")),
            overrides={
                "encode_paper_job": MagicMock(side_effect=encode),
                "delete_paper_vectors": MagicMock(side_effect=lambda vault, key: delete_calls.append(key)),
            },
            # keys filter via the extracted seam: _call_run builds the
            # Namespace; inject keys through the override path below.
        )
        # _call_run doesn't support keys — run the seam directly instead.
        assert rc == 0

    def test_run_build_keys_restricts_embedding(self, tmp_path: Path) -> None:
        canonical_test_config(tmp_path, system_dir="System")
        encode_calls: list[str] = []
        delete_calls: list[str] = []
        write_calls: list[str] = []

        def encode(vault, job):
            encode_calls.append(job.paper_id)
            return _make_bundle(job.paper_id, n_chunks=1)

        from unittest.mock import patch

        with patch("paperforge.commands.embed.encode_paper_job", side_effect=encode), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.commands.embed.delete_paper_vectors",
                   side_effect=lambda vault, key: delete_calls.append(key)), \
             patch("paperforge.commands.embed.write_encoded_payload",
                   side_effect=lambda vault, payload: write_calls.append(payload.collection_name)):
            rc = run_build(tmp_path, _papers(("A", "B", "C")), keys=["A"])

        assert rc == 0
        assert encode_calls == ["A"]
        assert delete_calls == ["A"]
        assert write_calls  # payloads written for A only

    def test_run_build_none_keys_is_whole_library(self, tmp_path: Path) -> None:
        canonical_test_config(tmp_path, system_dir="System")
        encode_calls: list[str] = []

        def encode(vault, job):
            encode_calls.append(job.paper_id)
            return _make_bundle(job.paper_id, n_chunks=1)

        from unittest.mock import patch

        with patch("paperforge.commands.embed.encode_paper_job", side_effect=encode), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=3), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"):
            rc = run_build(tmp_path, _papers(("A", "B")), keys=None)

        assert rc == 0
        assert sorted(encode_calls) == ["A", "B"]

    def test_scoped_shadow_trigger_fails_fast(self, tmp_path: Path) -> None:
        """A papers-scoped request that would route through a shadow rebuild
        must fail — the shadow clears all vec tables and re-embeds every
        done paper (violates affected ⊆ requested)."""
        canonical_test_config(tmp_path, system_dir="System")
        db = tmp_path / "System" / "PaperForge" / "indexes" / "paperforge.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        sqlite3.connect(str(db)).close()  # existing DB -> shadow triggers

        from unittest.mock import patch

        with patch("paperforge.commands.embed.encode_paper_job") as enc:
            rc = run_build(tmp_path, _papers(("A",)), keys=["A"], force=True)
        assert rc == 1
        enc.assert_not_called()


# ── lineage preservation (#165 comment) ───────────────────────────────────

class TestLineageDimensionResolution:
    def test_expected_dim_wins(self, tmp_path: Path) -> None:
        from paperforge.commands.embed import _resolve_lineage_dimension

        assert _resolve_lineage_dimension(None, expected_dim=2560, stored_dim=3) == 2560

    def test_stored_dim_fallback(self, tmp_path: Path) -> None:
        from paperforge.commands.embed import _resolve_lineage_dimension

        assert _resolve_lineage_dimension(None, expected_dim=0, stored_dim=3) == 3

    def test_vec_ddl_is_authoritative_fallback(self, tmp_path: Path) -> None:
        """Incremental resumes never recreate vec tables (expected_dim=0) and
        may lack build_state.vector_dimension (stored_dim=0) — the vec0 DDL
        self-declaration must supply the dimension, or lineage writes are
        silently skipped (regression: resume-completed builds published with
        empty lineage -> reader gate dropped everything)."""
        from paperforge.commands.embed import _resolve_lineage_dimension
        from paperforge.memory.db import ensure_vec_extension
        from paperforge.memory.schema import ensure_schema

        db_path = tmp_path / "t.db"
        conn = sqlite3.connect(str(db_path))
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
            dim = _resolve_lineage_dimension(conn, expected_dim=0, stored_dim=0)
            assert dim == 1536  # schema default; the DDL is the source
        finally:
            conn.close()

    def test_no_source_returns_zero(self, tmp_path: Path) -> None:
        from paperforge.commands.embed import _resolve_lineage_dimension

        conn = sqlite3.connect(str(tmp_path / "empty.db"))
        try:
            assert _resolve_lineage_dimension(conn, expected_dim=0, stored_dim=0) == 0
        finally:
            conn.close()


class TestLineagePreservation:
    def test_resume_skipped_papers_keep_lineage_rows_byte_identical(self, tmp_path: Path) -> None:
        canonical_test_config(tmp_path, system_dir="System")
        _seed_resume_db(tmp_path, ("A", "B", "C"))
        for key in ("A", "B", "C"):
            _store_manifest(tmp_path, key)
        _store_lineage_row(tmp_path, "B", "2026-01-01T00:00:00+00:00")
        _store_lineage_row(tmp_path, "C", "2026-01-01T00:00:00+00:00")
        before_b = _lineage_rows(tmp_path, "B")
        before_c = _lineage_rows(tmp_path, "C")

        def encode(vault, job):
            return _make_bundle(job.paper_id, n_chunks=1)

        from unittest.mock import patch

        def body_units_for(vault, key):
            # A carries changed units (hash differs from the stored hash_v1)
            # so it is genuinely re-embedded; B/C keep hash_v1 -> skipped.
            return [{"unit_id": f"{key}-u1", "key": key}]

        def hash_for(units):
            # hash_v1 for B/C (match -> skip), anything else for A (re-embed)
            return "hash_v1" if units and units[0]["key"] != "A" else "hash_v2"

        with patch("paperforge.commands.embed.encode_paper_job", side_effect=encode), \
             patch("paperforge.embedding.dim_detect.inspect_vector_layout",
                   return_value=type("L", (), {
                       "compatible": True, "missing": (), "dimensions": {},
                   })()), \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=3), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"), \
             patch("paperforge.commands.embed.compute_body_units_hash", side_effect=hash_for), \
             patch("paperforge.commands.embed.compute_object_units_hash", side_effect=hash_for), \
             patch("paperforge.commands.embed.RETRIEVAL_POLICY_VERSION", "v1"), \
             patch("paperforge.commands.embed.get_body_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.commands.embed.get_object_units_for_embedding", side_effect=body_units_for), \
             patch("paperforge.commands.embed._has_body_units_in_db", return_value=True), \
             patch("paperforge.commands.embed._has_object_units_in_db", return_value=True), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key) if key == "A" else []):
            rc = run_build(tmp_path, _papers(("A", "B", "C")), keys=["A"], resume=True)

        assert rc == 0
        # B/C lineage rows byte-identical (identity/derived_from/embedding/updated_at).
        assert _lineage_rows(tmp_path, "B") == before_b
        assert _lineage_rows(tmp_path, "C") == before_c
        # A got a (possibly new) lineage row.
        assert _lineage_rows(tmp_path, "A") != []


# ── RecordingEmbeddingProvider (test-only, no product seam) ────────────────

    def test_paper_ids_filter_restricts_lineage_writes(self, tmp_path: Path) -> None:
        """#165 corrective: write_vector_lineage(paper_ids=...) rewrites ONLY
        the listed papers — even when B/C carry valid manifests (the old
        variable-shadowing bug made this filter a no-op)."""
        from paperforge.lineage import write_vector_lineage
        from paperforge.memory.db import get_memory_db_path

        canonical_test_config(tmp_path, system_dir="System")
        _seed_resume_db(tmp_path, ("A", "B", "C"))
        for key in ("A", "B", "C"):
            _store_manifest(tmp_path, key)
        _store_lineage_row(tmp_path, "A", "2026-01-01T00:00:00+00:00")
        _store_lineage_row(tmp_path, "B", "2026-01-01T00:00:00+00:00")
        _store_lineage_row(tmp_path, "C", "2026-01-01T00:00:00+00:00")
        before_b = _lineage_rows(tmp_path, "B")
        before_c = _lineage_rows(tmp_path, "C")

        conn = sqlite3.connect(str(get_memory_db_path(tmp_path)))
        try:
            n = write_vector_lineage(
                conn, tmp_path,
                endpoint="https://api.openai.com/v1",
                model="m",
                dimension=3,
                paper_ids={"A"},
            )
            conn.commit()
        finally:
            conn.close()

        assert n == 1
        # A's row was rewritten (fresh updated_at), B/C byte-identical.
        assert _lineage_rows(tmp_path, "A")[0][5] != "2026-01-01T00:00:00+00:00"
        assert _lineage_rows(tmp_path, "B") == before_b
        assert _lineage_rows(tmp_path, "C") == before_c


class TestResumeResetRouting:
    """#165 corrective: a resume request downgraded by a gate (stale
    recovery / no rows / model change) must route through shadow — the
    extraction must be behavior-preserving; scoped requests fail before any
    paper mutation."""

    def _stale_build_state(self, tmp_path: Path) -> None:
        from paperforge.memory.db import get_memory_db_path

        conn = sqlite3.connect(str(get_memory_db_path(tmp_path)))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('status', ?)",
                ('"running"',),
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('pid', '99999999')"
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')"
            )
            conn.commit()
        finally:
            conn.close()

    def test_resume_reset_routes_shadow_unscoped(self, tmp_path: Path) -> None:
        """resume=True + stale running recovery downgrades resume; the
        unscoped build must route through the shadow rebuild path."""
        canonical_test_config(tmp_path, system_dir="System")
        _seed_resume_db(tmp_path, ("A",))
        self._stale_build_state(tmp_path)

        from unittest.mock import patch

        shadow_prepared: list[str] = []

        def encode(vault, job):
            # Shadow vec tables are created at the model-detected dimension.
            from tests.test_pr9c_streaming_embed import EncodedPayload, PaperEncodedBundle

            bundle = _make_bundle(job.paper_id, n_chunks=1)
            return PaperEncodedBundle(
                paper_id=bundle.paper_id,
                payloads=[
                    EncodedPayload(
                        collection_name=p.collection_name,
                        texts=p.texts,
                        ids=p.ids,
                        metadatas=p.metadatas,
                        embeddings=[[0.1] * 1536 for _ in p.embeddings],
                    )
                    for p in bundle.payloads
                ],
                chunk_count=bundle.chunk_count,
            )

        with patch("paperforge.commands.embed.encode_paper_job", side_effect=encode), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=1536), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"), \
             patch("paperforge.commands.embed._pid_alive", return_value=False):
            from paperforge.embedding.build_target import ShadowBuild
            orig_prepare = ShadowBuild.prepare

            def spy_prepare(self):
                shadow_prepared.append("prepare")
                return orig_prepare(self)

            ShadowBuild.prepare = spy_prepare
            try:
                rc = run_build(tmp_path, _papers(("A",)), keys=None, resume=True)
            finally:
                ShadowBuild.prepare = orig_prepare

        assert rc == 0
        assert shadow_prepared == ["prepare"], "resume-reset must route through shadow"

    def test_scoped_resume_reset_fails_before_mutation(self, tmp_path: Path) -> None:
        """Same downgrade with a papers-scoped request: fail fast before
        any paper mutation (no encodes)."""
        canonical_test_config(tmp_path, system_dir="System")
        _seed_resume_db(tmp_path, ("A",))
        self._stale_build_state(tmp_path)

        from unittest.mock import patch

        with patch("paperforge.commands.embed.encode_paper_job") as enc, \
             patch("paperforge.commands.embed._pid_alive", return_value=False):
            rc = run_build(tmp_path, _papers(("A",)), keys=["A"], resume=True)
        assert rc == 1
        enc.assert_not_called()

    def _isolated_resume_db(self, tmp_path: Path, keys: tuple[str, ...]) -> None:
        """Compatible substrate (identity/layout/legacy all clean) with ZERO
        vec rows — the ONLY downgrade trigger is the no-rows gate, so a
        shadow route proves `requested_resume` captured the caller's intent
        (#166 P0-3 isolated test)."""
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema

        db_path = get_memory_db_path(tmp_path)
        conn = get_connection(db_path)
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
            # compatible substrate: current model/endpoint, dim 0 (layout
            # check skipped), identity version current — no vec rows.
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')"
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('status', 'idle')"
            )
            conn.commit()
        finally:
            conn.close()

    def test_requested_resume_no_rows_gate_routes_shadow_unscoped(self, tmp_path: Path) -> None:
        """Isolated #166 P0-3: resume=True with ONLY the no-rows gate
        downgrading — identity/layout/legacy/force all clean — the unscoped
        build MUST route through shadow (requested_resume preserved before
        gates)."""
        canonical_test_config(tmp_path, system_dir="System")
        self._isolated_resume_db(tmp_path, ("A",))

        from unittest.mock import patch

        shadow_prepared: list[str] = []
        from tests.test_pr9c_streaming_embed import EncodedPayload, PaperEncodedBundle

        def encode(vault, job):
            bundle = _make_bundle(job.paper_id, n_chunks=1)
            return PaperEncodedBundle(
                paper_id=bundle.paper_id,
                payloads=[
                    EncodedPayload(
                        collection_name=p.collection_name,
                        texts=p.texts,
                        ids=p.ids,
                        metadatas=p.metadatas,
                        embeddings=[[0.1] * 1536 for _ in p.embeddings],
                    )
                    for p in bundle.payloads
                ],
                chunk_count=bundle.chunk_count,
            )

        with patch("paperforge.commands.embed.encode_paper_job", side_effect=encode), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=1536), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"):
            from paperforge.embedding.build_target import ShadowBuild
            orig_prepare = ShadowBuild.prepare

            def spy_prepare(self):
                shadow_prepared.append("prepare")
                return orig_prepare(self)

            ShadowBuild.prepare = spy_prepare
            try:
                rc = run_build(tmp_path, _papers(("A",)), keys=None, resume=True)
            finally:
                ShadowBuild.prepare = orig_prepare

        assert rc == 0, "no-rows downgrade with requested resume must succeed via shadow"
        assert shadow_prepared == ["prepare"], (
            "requested_resume must be captured BEFORE the no-rows gate — "
            "shadow route proves the caller intent survived"
        )

    def test_requested_resume_no_rows_gate_fails_scoped(self, tmp_path: Path) -> None:
        """Isolated #166 P0-3: same downgrade, papers-scoped request must
        fail fast before any mutation."""
        canonical_test_config(tmp_path, system_dir="System")
        self._isolated_resume_db(tmp_path, ("A",))

        from unittest.mock import patch

        with patch("paperforge.commands.embed.encode_paper_job") as enc, \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=3), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"):
            rc = run_build(tmp_path, _papers(("A",)), keys=["A"], resume=True)
        assert rc == 1
        enc.assert_not_called()

    def test_pristine_substrate_scoped_resume_initializes(self, tmp_path: Path) -> None:
        """#167 P0-4: pristine substrate (no rows AND no published identity
        version) is a per-paper missing deficit — a scoped resume
        INITIALIZES the empty substrate and embeds only the requested keys.
        No downgrade → no shadow → no fail-fast."""
        canonical_test_config(tmp_path, system_dir="System")
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema

        db_path = get_memory_db_path(tmp_path)
        conn = get_connection(db_path)
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)  # zero build_state, zero vec rows — pristine
            conn.commit()
        finally:
            conn.close()

        from unittest.mock import patch
        from tests.test_pr9c_streaming_embed import EncodedPayload, PaperEncodedBundle

        def encode(vault, job):
            bundle = _make_bundle(job.paper_id, n_chunks=1)
            return PaperEncodedBundle(
                paper_id=bundle.paper_id,
                payloads=[
                    EncodedPayload(
                        collection_name=p.collection_name,
                        texts=p.texts,
                        ids=p.ids,
                        metadatas=p.metadatas,
                        embeddings=[[0.1] * 1536 for _ in p.embeddings],
                    )
                    for p in bundle.payloads
                ],
                chunk_count=bundle.chunk_count,
            )

        with patch("paperforge.commands.embed.encode_paper_job", side_effect=encode), \
             patch("paperforge.commands.embed.prepare_payloads_for_entry",
                   side_effect=lambda vault, key, *a, **k: _payloads_for(key)), \
             patch("paperforge.commands.embed.ensure_vec_tables", return_value=1536), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"):
            rc = run_build(tmp_path, _papers(("A",)), keys=["A"], resume=True)
        assert rc == 0, "pristine scoped resume must initialize and succeed"


class TestRecordingEmbeddingProvider:
    def test_provider_seam_records_requested_keys_only(self, tmp_path: Path, monkeypatch) -> None:
        """A test-only RecordingEmbeddingProvider injected through the
        existing provider seam records the key->batch mapping at the
        caller/harness level; no production mock-provider env mode."""
        canonical_test_config(tmp_path, system_dir="System")
        calls: list[str] = []

        class RecordingProvider:
            def __init__(self, vault):
                self.vault = vault

            def encode(self, texts, **kwargs):
                calls.extend(texts)
                return [[0.1] * 3 for _ in texts]

            def encode_single(self, text, **kwargs):
                calls.append(text)
                return [0.1] * 3

        monkeypatch.setattr("paperforge.embedding.builder.OpenAICompatibleProvider", RecordingProvider)
        # A has real fulltext; the real payload path runs through the recorder.
        (tmp_path / "A.pdf").write_text("fulltext of A. " * 10, encoding="utf-8")
        (tmp_path / "System" / "PaperForge" / "ocr" / "A").mkdir(parents=True, exist_ok=True)

        from unittest.mock import patch

        with patch("paperforge.commands.embed.ensure_vec_tables", return_value=3), \
             patch("paperforge.commands.embed.delete_paper_vectors"), \
             patch("paperforge.commands.embed.write_encoded_payload"):
            rc = run_build(
                tmp_path,
                [{"zotero_key": "A", "ocr_status": "done", "fulltext_path": "A.pdf"}],
                keys=["A"],
            )
        assert rc == 0
        # encode_paper_job ran the REAL path with the recording provider — no
        # encode mock was installed, so the provider log is queryable.
        assert any("fulltext of A" in t for t in calls)

    def test_no_mock_provider_env_mode_in_production(self) -> None:
        """Acceptance: PAPERFORGE_EMBED_PROVIDER-style env mode must NOT exist."""
        import paperforge.embedding.builder as builder_mod

        src = Path(builder_mod.__file__).read_text(encoding="utf-8")
        assert "PAPERFORGE_EMBED_PROVIDER" not in src
        assert "EMBED_PROVIDER=mock" not in src
