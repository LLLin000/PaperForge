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
    probe_lineage,
    retrieval_identity_from_manifest,
    write_vector_lineage,
)
from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION, build_paper_manifest
from tests.conftest import canonical_test_config

# Same defaults the embed build uses so identities line up in fixtures.
DIMENSION = 1536


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
        (ocr_dir / "meta.json").write_text(json.dumps({
            "ocr_status": "done",
            "zotero_key": key,
            "raw_version": {"pdf_fingerprint": "sha256:test-fingerprint"},
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
                "node_id": "n1",
                "section_path": ["s"],
                "unit_text": "body text",
            }
        ],
        object_units=[
            {
                "unit_id": f"{key}-o1",
                "paper_id": key,
                "node_id": "n2",
                "section_path": ["s"],
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
        # KEY2 has a manifest but no OCR; KEY3 has neither.
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
            # Simulate a memory publish: unit digests changed → new identity,
            # stored consistently in the manifest (retrieval stays current).
            manifest["body_units_hash"] = "f" * 64
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
    (d / "meta.json").write_text(json.dumps({
        "ocr_status": status,
        "zotero_key": key,
        "raw_version": {"pdf_fingerprint": "sha256:test-fingerprint"},
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

    from paperforge.lineage import _ocr_detail, _probe_ocr_state
    from paperforge.reconcile import PaperObservation, _per_paper_intents

    state, _ = _probe_ocr_state(d)
    detail = _ocr_detail(d)
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

class TestMaterializationCorrective:
    """P0-A corrective (2026-08-15 review): partial really detected,
    version_old is a flag not a failure detail, permission states emit."""

    def test_version_old_is_flag_not_detail(self, tmp_path: Path) -> None:
        from paperforge.lineage import _ocr_detail, _ocr_version_old

        vault = tmp_path / "vault"
        vault.mkdir(parents=True)
        canonical_test_config(vault, system_dir="99_System")
        d = _state_paper(vault, "KEY1")
        # simulate an old pipeline version in meta
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        meta["ocr_pipeline_version"] = "0.0.0"
        (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        assert _ocr_version_old(d) is True
        assert _ocr_detail(d) is None  # NOT version_old — no failure reason

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
