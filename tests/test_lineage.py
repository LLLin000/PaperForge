"""Digest lineage publish + probe lineage (#162 / T1).

Covers the frozen #159 §2.3/§6 contract: content-addressed identities,
identical rebuild → identical digest, unknown fails closed (never stale),
no auto-rebuild path.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from paperforge.embedding._config import (
    get_api_model,
    get_effective_api_base_url,
)
from paperforge.lineage import (
    LINEAGE_LAYER_VECTOR,
    compute_embedding_identity,
    compute_retrieval_identity,
    compute_vector_identity,
    observe_lineage_papers,
    probe_lineage,
    retrieval_identity_from_manifest,
    write_vector_lineage,
)
from paperforge.retrieval.manifest import (
    RETRIEVAL_POLICY_VERSION,
    build_paper_manifest,
    compute_body_units_hash,
)
from tests.conftest import canonical_test_config

# Same defaults the embed build uses so identities line up in fixtures.
DIMENSION = 1536


def _seed_canonical_pdf(vault: Path, key: str) -> bytes:
    """Canonical library main PDF + formal-library entry with pdf_path
    (P0-B: provenance's canonical PDF must come from the library, never
    from meta.source_pdf).  Returns the PDF bytes so callers can record
    the real fingerprint."""
    pdf = vault / "99_System" / "Zotero" / "storage" / key / "paper.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    payload = f"paper-{key}".encode()
    pdf.write_bytes(payload)
    idx = vault / "99_System" / "PaperForge" / "indexes" / "formal-library.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    if idx.exists():
        _data = json.loads(idx.read_text(encoding="utf-8"))
        _items = [i for i in _data.get("items", []) if i.get("zotero_key") != key]
    else:
        _data = {"schema_version": "3"}
        _items = []
    _items.append({"zotero_key": key, "pdf_path": f"[[99_System/Zotero/storage/{key}/paper.pdf]]"})
    _data["items"] = _items
    idx.write_text(json.dumps(_data), encoding="utf-8")
    return payload

def test_canonical_pdf_map_reads_index_once(tmp_path: Path, monkeypatch) -> None:
    """A lineage scan resolves the canonical index once per observation."""
    from paperforge.lineage import _canonical_pdf_map
    from paperforge.worker import asset_index

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="99_System")
    calls = 0
    resolved_pdf = vault / "paper.pdf"

    def fake_read_index(_vault: Path) -> dict:
        nonlocal calls
        calls += 1
        return {
            "items": [
                {"zotero_key": "KEY1", "pdf_path": "paper.pdf"},
                {"zotero_key": "KEY2", "pdf_path": "paper-2.pdf"},
            ]
        }

    monkeypatch.setattr(asset_index, "read_index", fake_read_index)
    monkeypatch.setattr(
        "paperforge.pdf_resolver.resolve_pdf_path",
        lambda *_args, **_kwargs: str(resolved_pdf),
    )

    assert _canonical_pdf_map(vault, ["KEY1"]) == {"KEY1": resolved_pdf}
    assert calls == 1


def _write_ocr_paper(vault: Path, key: str, *, pending: bool = False) -> None:
    """Create a canonical OCR paper dir: raw + derived artifacts + hash."""
    ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / key
    (ocr_dir / "structure").mkdir(parents=True, exist_ok=True)
    (ocr_dir / "index").mkdir(parents=True, exist_ok=True)
    (ocr_dir / "canonical").mkdir(parents=True, exist_ok=True)
    # [3] RAW OCR truth — the production source (ADR-0002 raw-first check).
    (ocr_dir / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps({"block_id": key, "page": 1, "role": "body_paragraph"}), encoding="utf-8"
    )
    (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps({"block_id": key, "page": 1, "role": "body_paragraph"}), encoding="utf-8"
    )
    (ocr_dir / "index" / "structure-tree.json").write_text(
        # A complete tree carries a non-empty nodes list; an empty/missing
        # nodes list is the INCOMPLETE product state (probe reports it).
        json.dumps({"root": key, "nodes": [{"id": "root", "depth": 0}]}),
        encoding="utf-8",
    )
    (ocr_dir / "index" / "role-index.json").write_text(
        json.dumps({"roles": [key]}), encoding="utf-8"
    )
    if pending:
        # no meta.json at all — lifecycle falls through to the publish
        # marker (recent → unknown/wait).
        (ocr_dir / "index" / "result-hash.pending").write_text("pending", encoding="utf-8")
    else:
        import hashlib as _hl

        _pdf_bytes = _seed_canonical_pdf(vault, key)
        _raw = json.dumps({"block_id": key, "page": 1, "role": "body_paragraph"})
        (ocr_dir / "meta.json").write_text(json.dumps({
            "ocr_status": "done",
            "zotero_key": key,
            "raw_version": {
                "pdf_fingerprint": "sha256:" + _hl.sha256(_pdf_bytes).hexdigest(),
                "raw_blocks_hash": "sha256:" + _hl.sha256(_raw.encode("utf-8")).hexdigest(),
            },
        }), encoding="utf-8")
        from paperforge.worker.ocr_hash import publish_ocr_result_hash

        publish_ocr_result_hash(ocr_dir)


def _manifest_for(key: str, ocr_result_hash: str, **overrides: Any) -> dict[str, Any]:
    """A manifest built through the production path (identity included)."""
    return build_paper_manifest(
        paper_id=key,
        ocr_result_hash=ocr_result_hash,
        structure_tree_bytes=json.dumps({"root": key}).encode("utf-8"),
        retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
        body_units=[
            {
                "unit_id": f"{key}-b1",
                "section_path": "s",
                "section_path_json": json.dumps(["s"]),
                "node_id": "n1",
                "unit_text": "body text",
            }
        ],
        object_units=[
            {
                "unit_id": f"{key}-o1",
                "paper_id": key,
                "section_path": "s",
                "node_id": "n2",
                "section_path_json": json.dumps(["s"]),
                "object_kind": "figure",
                "object_label": "Fig 1",
                "caption_text": "caption",
                "nearby_body_text": "nearby",
            }
        ],
        source_paths={"structured_blocks": f"ocr/{key}/structure/blocks.structured.jsonl"},
        **overrides,
    )


def _make_vault(tmp_path: Path, keys=("KEY1",)) -> Path:
    """Canonical vault with OCR papers + memory DB (schema, manifests, vec
    meta rows, build_state dimension) — the current lineage chain."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault, system_dir="99_System")
    for key in keys:
        _write_ocr_paper(vault, key)
    indexes = vault / "99_System" / "PaperForge" / "indexes"
    indexes.mkdir(parents=True, exist_ok=True)
    db = indexes / "paperforge.db"
    conn = sqlite3.connect(str(db))
    try:
        from paperforge.memory.db import ensure_vec_extension
        from paperforge.memory.schema import ensure_schema

        ensure_vec_extension(conn)
        ensure_schema(conn)
        for key in keys:
            ocr_hash = _published_ocr_hash(vault, key)
            manifest = _manifest_for(key, ocr_hash)
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (f"manifest:{key}", json.dumps(manifest)),
            )
            conn.execute(
                """INSERT INTO body_units (
                    unit_id, paper_id, section_path, section_path_json,
                    section_level, section_title, node_id, unit_text,
                    unit_kind, part_ordinal, page_span_json, block_span_json,
                    token_estimate, indexable, veto_reason, quality_hints_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"{key}-b1", key, "s", json.dumps(["s"]), 0, "", "n1",
                    "body text", "body", 0, "[]", "[]", 2, 1, "", "[]",
                ),
            )
            conn.execute(
                """INSERT INTO object_units (
                    unit_id, paper_id, section_path, node_id, section_path_json,
                    object_kind, object_label, caption_text, nearby_body_text,
                    page_span_json, block_span_json, token_estimate, indexable,
                    veto_reason, quality_hints_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"{key}-o1", key, "s", "n2", json.dumps(["s"]), "figure",
                    "Fig 1", "caption", "nearby", "[]", "[]", 2, 1, "", "[]",
                ),
            )
            # vec0 row first, meta aligned via lastrowid — the layout check
            # rejects orphan meta rows (meta without a matching vec row).
            cur = conn.execute(
                "INSERT INTO vec_fulltext(embedding) VALUES (?)",
                (json.dumps([0.0] * DIMENSION),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vec_fulltext_meta (rowid, paper_id, chunk_index, text) VALUES (?, ?, ?, ?)",
                (cur.lastrowid, key, 0, f"{key}-ft1"),
            )
            identity = compute_vector_identity(
                retrieval_identity=manifest["retrieval_identity"],
                embedding_identity=compute_embedding_identity(
                    endpoint=get_effective_api_base_url(vault),
                    model=get_api_model(vault),
                    dimension=DIMENSION,
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO lineage "
                "(paper_id, layer, identity, derived_from, embedding_identity, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    key,
                    LINEAGE_LAYER_VECTOR,
                    identity,
                    manifest["retrieval_identity"],
                    compute_embedding_identity(
                        endpoint=get_effective_api_base_url(vault),
                        model=get_api_model(vault),
                        dimension=DIMENSION,
                    ),
                    "2026-08-10T00:00:00+00:00",
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_dimension', ?)",
                (str(DIMENSION),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('model', ?)",
                (get_api_model(vault),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_provider_endpoint', ?)",
                (get_effective_api_base_url(vault),),
            )
            conn.execute(
                "INSERT OR REPLACE INTO build_state (key, value) VALUES ('vector_identity_version', '1')"
            )
        conn.commit()
    finally:
        conn.close()
    return vault


def _published_ocr_hash(vault: Path, key: str) -> str:
    return (
        vault / "99_System" / "PaperForge" / "ocr" / key / "index" / "result-hash.txt"
    ).read_text(encoding="utf-8").strip()


# ── identity formulas ─────────────────────────────────────────────────────

class TestIdentityFormulas:
    def test_retrieval_identity_deterministic_and_sensitive(self) -> None:
        kwargs = dict(
            ocr_result_hash="a" * 64,
            retrieval_policy_version="p1",
            structure_tree_hash="b" * 64,
            body_units_hash="c" * 64,
            object_units_hash="d" * 64,
        )
        first = compute_retrieval_identity(**kwargs)
        assert compute_retrieval_identity(**kwargs) == first  # identical rebuild
        for field in kwargs:
            changed = dict(kwargs)
            changed[field] = "x" * 64
            assert compute_retrieval_identity(**changed) != first, field

    def test_embedding_identity_dimension_change_flips_identity(self) -> None:
        base = compute_embedding_identity(endpoint="https://api.openai.com/v1", model="m", dimension=1536)
        assert compute_embedding_identity(endpoint="https://api.openai.com/v1", model="m", dimension=1536) == base
        assert compute_embedding_identity(endpoint="https://api.openai.com/v1", model="m", dimension=3072) != base
        assert compute_embedding_identity(endpoint="https://other/v1", model="m", dimension=1536) != base
        assert compute_embedding_identity(endpoint="https://api.openai.com/v1", model="m2", dimension=1536) != base

    def test_vector_identity_derives_from_both(self) -> None:
        r1, r2 = "1" * 64, "2" * 64
        e1, e2 = "3" * 64, "4" * 64
        v = compute_vector_identity(retrieval_identity=r1, embedding_identity=e1)
        assert v == compute_vector_identity(retrieval_identity=r1, embedding_identity=e1)
        assert v != compute_vector_identity(retrieval_identity=r2, embedding_identity=e1)
        assert v != compute_vector_identity(retrieval_identity=r1, embedding_identity=e2)

    def test_manifest_carries_retrieval_identity_identical_rebuild(self) -> None:
        m1 = _manifest_for("KEY1", "a" * 64)
        m2 = _manifest_for("KEY1", "a" * 64)
        assert m1["retrieval_identity"] == m2["retrieval_identity"]
        assert "retrieval_identity" in m1
        # any input change flips the identity
        assert _manifest_for("KEY1", "b" * 64)["retrieval_identity"] != m1["retrieval_identity"]
        assert retrieval_identity_from_manifest(m1) == m1["retrieval_identity"]

    def test_legacy_manifest_without_identity_is_unknown_source(self) -> None:
        manifest = _manifest_for("KEY1", "a" * 64)
        del manifest["retrieval_identity"]
        assert retrieval_identity_from_manifest(manifest) is not None  # recomputable
        # probe treats missing stored identity as unknown (tested below)


# ── vector lineage write ──────────────────────────────────────────────────

class TestWriteVectorLineage:
    def test_writes_rows_only_for_identity_carrying_papers(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        canonical_test_config(vault, system_dir="99_System")
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True)
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            from paperforge.memory.schema import ensure_schema

            ensure_schema(conn)
            good = _manifest_for("GOOD", "a" * 64)
            legacy = _manifest_for("LEGACY", "b" * 64)
            del legacy["retrieval_identity"]
            for key, manifest in (("GOOD", good), ("LEGACY", legacy), ("NOMANIFEST", None)):
                if manifest is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                        (f"manifest:{key}", json.dumps(manifest)),
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO vec_fulltext_meta (paper_id, chunk_index, text) VALUES (?, ?, ?)",
                    (key, 0, f"{key}-ft1"),
                )
            conn.commit()

            written = write_vector_lineage(
                conn, vault, endpoint="https://api.openai.com/v1", model="m", dimension=1536
            )
            conn.commit()
        finally:
            conn.close()

        assert written == 1  # only GOOD
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            ids = [r[0] for r in conn.execute("SELECT paper_id FROM lineage")]
            assert ids == ["GOOD"]
            row = conn.execute(
                "SELECT derived_from, embedding_identity FROM lineage WHERE paper_id='GOOD'"
            ).fetchone()
            assert row[0] == good["retrieval_identity"]
            assert row[1] == compute_embedding_identity(
                endpoint="https://api.openai.com/v1", model="m", dimension=1536
            )
        finally:
            conn.close()


# ── probe lineage read model ──────────────────────────────────────────────

class TestProbeLineage:
    def test_no_db_returns_unknown_envelope(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        canonical_test_config(vault, system_dir="99_System")
        result = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(vault), "probe", "lineage", "--json"],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["module"] == "lineage"
        assert payload["capability_state"] == "unknown"
        assert payload["reason"]["code"] == "lineage.db_missing"
        assert payload["papers"] == {}

    def test_current_chain(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        payload = probe_lineage(vault)
        assert payload["capability_state"] == "ok"
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert payload["papers"]["KEY1"]["retrieval"] == "current"
        assert payload["papers"]["KEY1"]["vector"] == "current"
        assert payload["papers"]["KEY1"]["details"]["render_consistency"]["state"] == "NOT_RUN"

    def test_render_consistency_projects_existing_report(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        report_path = (
            vault / "99_System" / "PaperForge" / "ocr" / "KEY1" / "render" / "render.consistency.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "render_consistency_schema_version": 1,
                    "audit_algorithm_version": 1,
                    "state": "DEGRADED",
                    "input_snapshot": {"render_hash": "sha256:test"},
                    "summary": {
                        "issues_found": 3,
                        "issues_repaired": 0,
                        "issues_remaining": 3,
                    },
                    "materialization_provenance": {
                        "path": "render/materialization.provenance.json",
                        "state": "available",
                    },
                }
            ),
            encoding="utf-8",
        )

        detail = probe_lineage(vault)["papers"]["KEY1"]["details"]["render_consistency"]
        assert detail["materialization_provenance"]["state"] == "available"

        assert detail["state"] == "DEGRADED"
        assert detail["summary"]["issues_found"] == 3
        assert detail["input_snapshot"]["render_hash"] == "sha256:test"
        assert detail["report_path"] == "render/render.consistency.json"

    def test_meta_read_once_per_paper_per_observation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Probe reads meta.json exactly ONCE per paper — lifecycle, detail,
        version, and execution all consume the injected copy.  Re-reading is
        the O(n×I/O) cost the canonical-PDF fix did not remove."""
        import paperforge.materialization.ocr as ocr_mat

        vault = _make_vault(tmp_path, keys=("KEY1", "KEY2"))
        calls = 0
        real_read_meta = ocr_mat.read_meta

        def counting_read_meta(paper_dir):
            nonlocal calls
            calls += 1
            return real_read_meta(paper_dir)

        monkeypatch.setattr(ocr_mat, "read_meta", counting_read_meta)
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert calls == 2, f"meta.json read {calls} times for 2 papers — must be 1 each"

    def test_current_paper_skips_detail_recompute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `current` paper's WHY is provably None (current requires a
        verified provenance) — probe must NOT re-run the artifact chain and
        PDF/raw hash just to produce that None.  provenance_state runs once
        inside the state probe, never a second time from detail."""
        import paperforge.materialization.ocr as ocr_mat

        vault = _make_vault(tmp_path)
        prov_calls = 0
        real_prov = ocr_mat.provenance_state

        def counting_prov(paper_dir, canonical_pdf, meta=None):
            nonlocal prov_calls
            prov_calls += 1
            return real_prov(paper_dir, canonical_pdf, meta=meta)

        monkeypatch.setattr(ocr_mat, "provenance_state", counting_prov)
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert payload["papers"]["KEY1"]["details"]["ocr"] is None
        assert prov_calls == 1, (
            f"provenance_state called {prov_calls} times for one current paper "
            "— detail must be skipped, not recomputed"
        )
    def test_scoped_observation_matches_paper_facts_without_library_scan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        vault = _make_vault(tmp_path, keys=("KEY1", "KEY2"))
        full = probe_lineage(vault)

        def fail_library_scan(_vault: Path) -> dict:
            raise AssertionError("scoped observation must not scan library carriers")

        monkeypatch.setattr("paperforge.lineage._detect_residuals", fail_library_scan)
        scoped = observe_lineage_papers(vault, ("KEY2", "UNKNOWN"))

        assert scoped["papers"]["KEY2"] == full["papers"]["KEY2"]
        assert scoped["identities"]["KEY2"] == full["identities"]["KEY2"]
        assert "UNKNOWN" not in scoped["papers"]
        assert "residuals" not in scoped
        assert "orphan" not in scoped


    def test_ocr_snapshot_missing_is_publish_metadata_missing(self, tmp_path: Path) -> None:
        """ADR-0002 (contract §5.3): result-hash.txt is the PUBLISHED
        canonical identity, not a disposable cache.  Missing → 
        publish_metadata_missing → incomplete, never a silent current —
        artifacts being intact does not prove publication happened."""
        vault = _make_vault(tmp_path)
        snapshot = (
            vault / "99_System" / "PaperForge" / "ocr" / "KEY1" / "index" / "result-hash.txt"
        )
        assert snapshot.exists()
        snapshot.unlink()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "incomplete"
        assert (
            payload["papers"]["KEY1"].get("details", {}).get("ocr")
            == "publish_metadata_missing"
        )

    def test_embedding_identity_reads_dim_from_vec_ddl(self, tmp_path: Path) -> None:
        """DAG principle: the dimension comes from the vec0 DDL (the
        artifact's own declaration), never from an external build_state key.
        Clearing build_state.vector_dimension must not break the chain."""
        vault = _make_vault(tmp_path)
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            conn.execute("DELETE FROM build_state WHERE key = 'vector_dimension'")
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["vector"] == "current"

    def test_ocr_pending_marker_is_unknown(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        canonical_test_config(vault, system_dir="99_System")
        _write_ocr_paper(vault, "KEY1", pending=True)
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True)
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            from paperforge.memory.schema import ensure_schema

            ensure_schema(conn)
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "unknown"
        assert payload["papers"]["KEY1"]["retrieval"] == "unknown"

    def test_legacy_manifest_retrieval_unknown_never_stale(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            manifest = json.loads(
                conn.execute("SELECT value FROM meta WHERE key='manifest:KEY1'").fetchone()[0]
            )
            del manifest["retrieval_identity"]
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("manifest:KEY1", json.dumps(manifest)),
            )
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["retrieval"] == "unknown"
        assert payload["papers"]["KEY1"]["vector"] == "unknown"

    def test_vectors_without_lineage_row_unknown(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            conn.execute("DELETE FROM lineage")
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["vector"] == "unknown"
        assert payload["papers"]["KEY1"]["retrieval"] == "current"

    def test_ocr_hash_change_marks_chain_stale(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        # Touch the OCR artifact AFTER publish — published hash now differs.
        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "KEY1"
        (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
            json.dumps({"block_id": "KEY1", "page": 1, "role": "body_paragraph", "changed": True}), encoding="utf-8"
        )
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "stale"
        assert payload["papers"]["KEY1"]["retrieval"] == "stale"
        assert payload["papers"]["KEY1"]["vector"] == "stale"

    def test_model_change_marks_vector_stale(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        from paperforge.config import set_config

        set_config(vault, "vector_db_api_model", "text-embedding-3-large")
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert payload["papers"]["KEY1"]["retrieval"] == "current"
        assert payload["papers"]["KEY1"]["vector"] == "stale"

    def test_missing_paper_dirs_and_no_manifest(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path, keys=("KEY1",))
        # KEY2 has a manifest but no OCR; KEY3 has neither.  KEY2 joins the
        # canonical universe (formal-library) so the probe reports it.
        _seed_canonical_pdf(vault, "KEY2")
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("manifest:KEY2", json.dumps(_manifest_for("KEY2", "c" * 64))),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vec_fulltext_meta (paper_id, chunk_index, text) VALUES (?, ?, ?)",
                ("KEY2", 0, "KEY2-ft1"),
            )
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY2"]["ocr"] == "missing"
        assert payload["papers"]["KEY2"]["retrieval"] == "missing"
        # KEY2 has vectors but no lineage row → unknown, never stale.
        assert payload["papers"]["KEY2"]["vector"] == "unknown"

    def test_new_published_ocr_identity_marks_retrieval_and_vector_stale(self, tmp_path: Path) -> None:
        """#162 P0-1: a NORMAL OCR publish (artifacts + result-hash both
        updated) must make the old retrieval and vector stale — the manifest
        embeds the old OCR identity."""
        vault = _make_vault(tmp_path)
        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "KEY1"
        from paperforge.worker.ocr_hash import publish_ocr_result_hash

        # Normal publish: rewrite the artifact AND publish the new hash.
        (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
            json.dumps({"block_id": "KEY1", "page": 1, "role": "body_paragraph", "changed": True}), encoding="utf-8"
        )
        publish_ocr_result_hash(ocr_dir)
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert payload["papers"]["KEY1"]["retrieval"] == "stale"
        assert payload["papers"]["KEY1"]["vector"] == "stale"

    def test_new_retrieval_publish_marks_old_vector_stale(self, tmp_path: Path) -> None:
        """#162 P0-2: after memory publishes a new retrieval identity, old
        vectors (derived_from the previous identity) are stale even though
        the retrieval layer itself is current."""
        vault = _make_vault(tmp_path)
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            manifest = json.loads(
                conn.execute("SELECT value FROM meta WHERE key='manifest:KEY1'").fetchone()[0]
            )
            # Simulate a real memory publish: the carrier and manifest change
            # together, so retrieval remains current while old vectors stale.
            conn.execute(
                "UPDATE body_units SET unit_text = ? WHERE paper_id = ?",
                ("new body after publish", "KEY1"),
            )
            manifest["body_units_hash"] = compute_body_units_hash([{
                "unit_id": "KEY1-b1",
                "node_id": "n1",
                "section_path": "s",
                "section_path_json": json.dumps(["s"]),
                "section_level": 0,
                "section_title": "",
                "unit_kind": "body",
                "part_ordinal": 0,
                "unit_text": "new body after publish",
            }])
            manifest["retrieval_identity"] = compute_retrieval_identity(
                ocr_result_hash=manifest["ocr_result_hash"],
                retrieval_policy_version=manifest["retrieval_policy_version"],
                structure_tree_hash=manifest["structure_tree_hash"],
                body_units_hash=manifest["body_units_hash"],
                object_units_hash=manifest["object_units_hash"],
            )
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("manifest:KEY1", json.dumps(manifest)),
            )
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert payload["papers"]["KEY1"]["retrieval"] == "current"
        # Vector lineage still derives from the OLD retrieval identity.
        assert payload["papers"]["KEY1"]["vector"] == "stale"

    def test_policy_bump_marks_retrieval_and_vector_stale(self, tmp_path: Path, monkeypatch) -> None:
        """#162 P0-1: a retrieval-policy bump (global desired state) makes
        manifests built under the old policy stale."""
        vault = _make_vault(tmp_path)
        import paperforge.retrieval.manifest as manifest_mod

        monkeypatch.setattr(manifest_mod, "RETRIEVAL_POLICY_VERSION", "l4.body.v999")
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "current"
        assert payload["papers"]["KEY1"]["retrieval"] == "stale"
        assert payload["papers"]["KEY1"]["vector"] == "stale"

    def test_mutated_retrieval_carrier_is_not_current(self, tmp_path: Path) -> None:
        """A post-publish unit mutation must fail the retrieval state closed."""
        vault = _make_vault(tmp_path)
        db_path = vault / "99_System" / "PaperForge" / "indexes" / "paperforge.db"
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE body_units SET unit_text = ? WHERE paper_id = ?",
                ("BROKEN AFTER PUBLISH", "KEY1"),
            )
            conn.commit()
        finally:
            conn.close()

        state = probe_lineage(vault)["papers"]["KEY1"]
        assert state["retrieval"] == "stale"
        assert state["vector"] == "stale"
        assert state["integrity"]["snapshot_integrity"] == "corrupt"


    def test_cli_output_shape_and_no_autorebuild(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(vault), "probe", "lineage", "--json"],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["module"] == "lineage"
        assert payload["capability_state"] == "ok"
        assert payload["papers"]["KEY1"]["vector"] == "current"
        # probe must never write: no new files under the vault
        assert not (vault / "99_System" / "PaperForge" / "ocr" / "KEY1" / "index" / "result-hash.pending").exists()


class TestIncompleteOcrState:
    """2026-08-14: OCR products with a missing/EMPTY structure tree are an
    INCOMPLETE product — distinct from quality problems, never `current`."""

    def _write_empty_tree_paper(self, vault: Path, key: str) -> None:
        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / key
        (ocr_dir / "structure").mkdir(parents=True, exist_ok=True)
        (ocr_dir / "index").mkdir(parents=True, exist_ok=True)
        (ocr_dir / "canonical").mkdir(parents=True, exist_ok=True)
        (ocr_dir / "canonical" / "blocks.raw.jsonl").write_text(
            json.dumps({"block_id": key, "page": 1, "role": "body_paragraph"}), encoding="utf-8"
        )
        (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
            json.dumps({"block_id": key, "page": 1, "role": "body_paragraph"}), encoding="utf-8"
        )
        (ocr_dir / "index" / "structure-tree.json").write_text(
            json.dumps({"root": key, "nodes": []}), encoding="utf-8"
        )
        (ocr_dir / "index" / "role-index.json").write_text(
            json.dumps({"roles": [key]}), encoding="utf-8"
        )
        from paperforge.worker.ocr_hash import publish_ocr_result_hash

        publish_ocr_result_hash(ocr_dir)

    def test_empty_structure_tree_is_incomplete(self, tmp_path: Path) -> None:

        vault = tmp_path / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        canonical_test_config(vault, system_dir="99_System")
        self._write_empty_tree_paper(vault, "KEY1")
        indexes = vault / "99_System" / "PaperForge" / "indexes"
        indexes.mkdir(parents=True)
        conn = sqlite3.connect(str(indexes / "paperforge.db"))
        try:
            from paperforge.memory.schema import ensure_schema

            ensure_schema(conn)
            # A real (if structurally incomplete) vector row exists — the
            # probe must report the vector as incomplete (not missing).
            conn.execute(
                "INSERT INTO vec_fulltext_meta(rowid, paper_id) VALUES (1, 'KEY1')"
            )
            conn.commit()
        finally:
            conn.close()
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"]["ocr"] == "incomplete"
        assert payload["papers"]["KEY1"]["retrieval"] == "incomplete"
        assert payload["papers"]["KEY1"]["vector"] == "incomplete"
        # The reader gate must NOT drop already-materialized incomplete
        # vectors (they are real data), while missing-structure stays out.
        from paperforge.reader_gate import filter_readable

        allowed = filter_readable(
            vault,
            [{"paper_id": "KEY1", "text": "hit"}],
            require_vector=True,
        )
        assert len(allowed) == 1

    def test_missing_tree_file_is_incomplete(self, tmp_path: Path) -> None:
        from paperforge.lineage import _ocr_detail

        vault = tmp_path / "vault"
        vault.mkdir(parents=True, exist_ok=True)
        canonical_test_config(vault, system_dir="99_System")
        self._write_empty_tree_paper(vault, "KEY1")
        # remove the tree file entirely
        (vault / "99_System" / "PaperForge" / "ocr" / "KEY1" / "index" / "structure-tree.json").unlink()
        paper_dir = vault / "99_System" / "PaperForge" / "ocr" / "KEY1"
        assert _ocr_detail(paper_dir) == "tree_missing"


# ── 2026-08-14 audit: the OCR state machine, probe→action end to end ─────

_GOOD_BLOCKS = b'{"block_id": "K1", "page": 1, "role": "body_paragraph"}\n{"block_id": "K2", "page": 1, "role": "section_heading"}\n'
_GOOD_TREE = '{"nodes": [{"id": "n1", "depth": 0}]}'
_GOOD_ROLE = '{"body": [], "captions": []}'


def _state_paper(root: Path, key: str, status: str = "done") -> Path:
    """A paper with raw + all derived artifacts valid, then mutated by the
    caller.  meta lifecycle set by *status*.  ADR-0002: raw is checked
    FIRST, so derived defects only surface with healthy raw."""
    d = root / "99_System" / "PaperForge" / "ocr" / key
    (d / "structure").mkdir(parents=True, exist_ok=True)
    (d / "index").mkdir(parents=True, exist_ok=True)
    (d / "canonical").mkdir(parents=True, exist_ok=True)
    (d / "canonical" / "blocks.raw.jsonl").write_bytes(_GOOD_BLOCKS)
    (d / "structure" / "blocks.structured.jsonl").write_bytes(_GOOD_BLOCKS)
    (d / "index" / "structure-tree.json").write_text(_GOOD_TREE, encoding="utf-8")
    (d / "index" / "role-index.json").write_text(_GOOD_ROLE, encoding="utf-8")
    import hashlib as _hl

    _pdf_bytes = _seed_canonical_pdf(root, key)
    _raw_hash = "sha256:" + _hl.sha256(_GOOD_BLOCKS).hexdigest()
    (d / "meta.json").write_text(json.dumps({
        "ocr_status": status,
        "zotero_key": key,
        "raw_version": {
            "pdf_fingerprint": "sha256:" + _hl.sha256(_pdf_bytes).hexdigest(),
            "raw_blocks_hash": _raw_hash,
        },
    }), encoding="utf-8")
    if status == "done":
        from paperforge.worker.ocr_hash import publish_ocr_result_hash

        publish_ocr_result_hash(d)
    return d


_STATE_CASES = [
    # (meta_status, mutation, expected_state, expected_detail, expected_action)
    ("pending", None, "missing", "not_started", "ocr.run"),
    ("queued", None, "missing", "queued", None),
    ("running", None, "missing", "queued", None),
    ("retryable_error", None, "failed", "retryable_error", "ocr.run"),
    ("fatal_error", None, "failed", "fatal_error", "ocr.run"),
    ("failed", None, "failed", "failed_legacy", "ocr.run"),  # P0-1 regression
    ("blocked", None, "missing", "blocked", None),  # P1-1 no ocr.run
    ("nopdf", None, "missing", "no_pdf", None),  # P1-1 no ocr.run
    # ADR-0002: raw is the deepest frontier.  raw broken → ocr.run.
    ("done", "raw_missing", "missing", "raw_missing", "ocr.run"),
    ("done", "raw_unreadable", "missing", "raw_unreadable", "ocr.run"),
    ("done", "raw_empty", "missing", "raw_empty", "ocr.run"),
    ("done", "raw_partial", "missing", "raw_partial", "ocr.run"),
    # Derived defects with HEALTHY raw → local rebuild, never remote OCR.
    ("done", "blocks_empty", "incomplete", "blocks_empty", "ocr.rebuild_derived"),
    ("done", "blocks_missing", "incomplete", "blocks_missing", "ocr.rebuild_derived"),
    ("done", "blocks_invalid", "incomplete", "blocks_invalid", "ocr.rebuild_derived"),
    ("done", "blocks_partial", "incomplete", "blocks_partial", "ocr.rebuild_derived"),
    ("done", "tree_missing", "incomplete", "tree_missing", "ocr.rebuild_derived"),
    ("done", "tree_empty", "incomplete", "tree_empty", "ocr.rebuild_derived"),
    ("done", "tree_invalid", "incomplete", "tree_invalid", "ocr.rebuild_derived"),
    ("done", "role_missing", "incomplete", "role_index_missing", "ocr.rebuild_derived"),
    ("done", "role_invalid", "incomplete", "role_index_invalid", "ocr.rebuild_derived"),
    ("done", "publish_recent", "unknown", "publish_pending_recent", None),
    ("done", "publish_stale", "incomplete", "publish_pending_stale", "ocr.rebuild_derived"),
    ("done", None, "current", None, None),
]


def _apply_mutation(d: Path, mutation: str | None, key: str) -> None:
    if mutation is None:
        return
    if mutation == "raw_missing":
        (d / "canonical" / "blocks.raw.jsonl").unlink()
    elif mutation == "raw_unreadable":
        (d / "canonical" / "blocks.raw.jsonl").write_bytes(b"\x83\x04g\xa9\xcb")
    elif mutation == "raw_empty":
        (d / "canonical" / "blocks.raw.jsonl").write_bytes(b"")
    elif mutation == "raw_partial":
        (d / "canonical" / "blocks.raw.jsonl").write_bytes(
            b'{"block_id": "ok", "page": 1}\n{"block_id": "truncated"'
        )
    elif mutation == "blocks_partial":
        (d / "structure" / "blocks.structured.jsonl").write_bytes(
            b'{"block_id": "ok", "page": 1}\n{"block_id": "truncated"'
        )
    elif mutation == "blocks_empty":
        (d / "structure" / "blocks.structured.jsonl").write_bytes(b"")
    elif mutation == "blocks_missing":
        (d / "structure" / "blocks.structured.jsonl").unlink()
    elif mutation == "blocks_invalid":
        (d / "structure" / "blocks.structured.jsonl").write_bytes(b'["not a block"]\n')
    elif mutation == "tree_missing":
        (d / "index" / "structure-tree.json").unlink()
    elif mutation == "tree_empty":
        (d / "index" / "structure-tree.json").write_text('{"nodes": []}', encoding="utf-8")
    elif mutation == "tree_invalid":
        (d / "index" / "structure-tree.json").write_text('{"nodes": "hello"}', encoding="utf-8")
    elif mutation == "role_missing":
        (d / "index" / "role-index.json").unlink()
    elif mutation == "role_invalid":
        (d / "index" / "role-index.json").write_text("123", encoding="utf-8")
    elif mutation == "publish_recent":
        p = d / "index" / "result-hash.pending"
        p.write_text("pending", encoding="utf-8")
        os.utime(p, (time.time() - 60, time.time() - 60))
    elif mutation == "publish_stale":
        p = d / "index" / "result-hash.pending"
        p.write_text("pending", encoding="utf-8")
        os.utime(p, (time.time() - 7200, time.time() - 7200))


@pytest.mark.parametrize(
    "meta_status, mutation, exp_state, exp_detail, exp_action",
    _STATE_CASES,
    ids=[f"{m or 'ok'}-{s}" for s, m, *_ in _STATE_CASES],
)
def test_ocr_state_machine_probe_to_action(
    tmp_path: Path, meta_status: str, mutation: str | None,
    exp_state: str, exp_detail: str, exp_action: str | None,
) -> None:
    """The full seam: probe state + detail AND reconcile's next action stay
    consistent for every OCR state machine branch (2026-08-14 audit)."""

    root = tmp_path / "vault"
    root.mkdir(parents=True, exist_ok=True)
    canonical_test_config(root, system_dir="99_System")
    key = "STATE1"
    d = _state_paper(root, key, status=meta_status)
    _apply_mutation(d, mutation, key)

    from paperforge.lineage import (
        _ocr_detail,
        _probe_ocr_state,
        _resolve_canonical_pdf,
    )
    from paperforge.reconcile import PaperObservation, _per_paper_intents

    _pdf = _resolve_canonical_pdf(root, d)
    state, _ = _probe_ocr_state(d, canonical_pdf=_pdf)
    detail = _ocr_detail(d, _pdf)
    assert state == exp_state, f"state {state} != {exp_state} ({detail})"
    assert detail == exp_detail, f"detail {detail} != {exp_detail}"

    obs = PaperObservation(
        key=key,
        ocr=state,
        retrieval="current" if state == "current" else "missing",
        vector="current" if state == "current" else "missing",
        identities={},
        details={"ocr": detail},
    )
    intents = _per_paper_intents(obs)
    actions = [i.action_id for i in intents]
    if exp_action is None:
        assert not actions, f"expected NO action, got {actions}"
    else:
        assert exp_action in actions, f"expected {exp_action} in {actions}"

def test_preflight_matches_reconcile_first_frontier() -> None:
    """Preflight and reconcile must agree on the action that is needed."""
    from paperforge.actions.preflight_projection import _rule
    from paperforge.reconcile import PaperObservation, _per_paper_intents

    cases = [
        (
            {"ocr": "stale", "retrieval": "current", "vector": "current",
             "details": {"ocr": "provenance_pdf_changed"}},
            {"ocr.run"},
        ),
        (
            {"ocr": "incomplete", "retrieval": "missing", "vector": "missing",
             "details": {"ocr": "tree_missing"}},
            {"ocr.rebuild_derived"},
        ),
        (
            {"ocr": "current", "retrieval": "stale", "vector": "current",
             "details": {}},
            {"memory.build"},
        ),
        (
            {"ocr": "current", "retrieval": "current", "vector": "missing",
             "details": {"vector": "vector_not_embedded"}},
            {"embed.resume"},
        ),
        (
            {"ocr": "current", "retrieval": "current", "vector": "missing",
             "details": {"vector": "vector_no_content"}},
            set(),
        ),
    ]
    for index, (state, expected) in enumerate(cases):
        paper = PaperObservation(
            key=f"PARITY{index}",
            ocr=str(state["ocr"]),
            retrieval=str(state["retrieval"]),
            vector=str(state["vector"]),
            identities={},
            details=dict(state["details"]),
        )
        actual = {intent.action_id for intent in _per_paper_intents(paper)}
        assert actual == expected
        for action_id in ("ocr.run", "ocr.rebuild_derived", "memory.build", "embed.resume"):
            applicability, *_ = _rule(action_id, state, key=paper.key)
            assert (applicability == "needed") is (action_id in expected)

class TestMaterializationCorrective:
    """P0-A corrective (2026-08-15 review): partial really detected,
    version_old is a flag not a failure detail, permission states emit."""

    def test_version_old_is_flag_not_detail(self, tmp_path: Path) -> None:
        from paperforge.lineage import _ocr_detail, _ocr_version_old, _resolve_canonical_pdf

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        # simulate an old pipeline version in meta
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        meta["ocr_pipeline_version"] = "0.0.0"
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        pdf = _resolve_canonical_pdf(vault, d)
        assert _ocr_version_old(d) is True
        assert _ocr_detail(d, pdf) is None  # NOT version_old — no failure reason

    def test_tree_permission_emits_permission_state(self, tmp_path: Path, monkeypatch) -> None:
        from paperforge.materialization.ocr import TREE_PERMISSION, _tree_state

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        tree = d / "index" / "structure-tree.json"

        def _deny(*args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr("paperforge.materialization.ocr.Path.read_text", _deny)
        assert _tree_state(d) == TREE_PERMISSION

class TestProvenance:
    """P0-B: OCR ownership — key binding, PDF fingerprint, raw content hash.
    PDF path is a locator; bytes are the identity (ADR-0002 §5 #1)."""

    def test_key_mismatch_is_stale(self, tmp_path: Path) -> None:
        from paperforge.materialization.ocr import (
            PROVENANCE_KEY_MISMATCH,
            provenance_state,
        )

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        meta["zotero_key"] = "OTHERKEY"
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        assert provenance_state(d, None) == PROVENANCE_KEY_MISMATCH

    def test_pdf_changed_is_stale(self, tmp_path: Path) -> None:
        from paperforge.materialization.ocr import (
            PROVENANCE_PDF_CHANGED,
            provenance_state,
        )

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        pdf = tmp_path / "canonical.pdf"
        pdf.write_bytes(b"new pdf bytes")
        assert provenance_state(d, pdf) == PROVENANCE_PDF_CHANGED

    def test_pdf_match_passes(self, tmp_path: Path) -> None:
        from paperforge.materialization.ocr import provenance_state

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        pdf = tmp_path / "canonical.pdf"
        pdf.write_bytes(b"same bytes")
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        import hashlib

        meta["raw_version"]["pdf_fingerprint"] = (
            "sha256:" + hashlib.sha256(b"same bytes").hexdigest()
        )
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        assert provenance_state(d, pdf) is None

    def test_legacy_unknown_no_autorepair(self, tmp_path: Path) -> None:
        from paperforge.materialization.ocr import (
            PROVENANCE_UNKNOWN,
            provenance_state,
        )

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        meta.pop("raw_version", None)  # legacy OCR — no fingerprint/hash
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        assert provenance_state(d, None) == PROVENANCE_UNKNOWN

    def test_legacy_fp_without_raw_hash_is_unknown(self, tmp_path: Path) -> None:
        """P0-B corrective: a legacy pdf_fingerprint WITHOUT raw_blocks_hash
        cannot prove the current raw is the original raw — fail-closed to
        unknown, never pass."""
        from paperforge.materialization.ocr import (
            PROVENANCE_UNKNOWN,
            provenance_state,
        )

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        meta["raw_version"].pop("raw_blocks_hash", None)  # pre-P0-B OCR
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        assert provenance_state(d, None) == PROVENANCE_UNKNOWN

    def test_meta_unreadable_is_provenance_unknown(self, tmp_path: Path) -> None:
        """P0-B corrective: an UNREADABLE meta.json (restore corruption)
        cannot prove provenance — fail-closed to unknown, never a pass
        (raw-healthy + meta-corrupt is the case that matters)."""
        from paperforge.materialization.ocr import (
            PROVENANCE_UNKNOWN,
            provenance_state,
        )

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        (d / "meta.json").write_bytes(b"\x83\x04g\xa9\xcb\x7c")  # random bytes
        assert provenance_state(d, None) == PROVENANCE_UNKNOWN

    def test_tree_dangling_block_ref_is_inconsistent(self, tmp_path: Path) -> None:
        """P1-C: a tree referencing blocks that do not exist in
        blocks.structured.jsonl is TREE_INCONSISTENT, never accepted."""
        from paperforge.materialization.ocr import (
            TREE_INCONSISTENT,
            ocr_artifact_detail,
        )

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        # blocks only have p1:block_id for the fixture rows; tree references
        # a page:block pair that cannot exist → dangling.
        tree = d / "index" / "structure-tree.json"
        tree.write_text(json.dumps({
            "nodes": [{
                "node_id": "n1", "page": 999, "block_id": 12345,
                "own_block_ids": ["p999:12345"],
            }],
        }), encoding="utf-8")
        assert ocr_artifact_detail(d) == TREE_INCONSISTENT

    def test_tree_consistent_refs_pass(self, tmp_path: Path) -> None:
        """P1-C: tree refs that resolve to real blocks are consistent."""
        from paperforge.materialization.ocr import ocr_artifact_detail

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        # fixture blocks: {"block_id": key, "page": 1} — tree referencing
        # p1:KEY1 is consistent.
        tree = d / "index" / "structure-tree.json"
        tree.write_text(json.dumps({
            "nodes": [{
                "node_id": "n1", "page": 1, "block_id": "KEY1",
                "own_block_ids": ["p1:KEY1"],
            }],
        }), encoding="utf-8")
        assert ocr_artifact_detail(d) is not None  # may hit role/publish next
