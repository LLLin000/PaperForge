"""Digest lineage publish + probe lineage (#162 / T1).

Covers the frozen #159 §2.3/§6 contract: content-addressed identities,
identical rebuild → identical digest, unknown fails closed (never stale),
no auto-rebuild path.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

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
    """Create a canonical OCR paper dir with three artifacts + published hash."""
    ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / key
    (ocr_dir / "structure").mkdir(parents=True, exist_ok=True)
    (ocr_dir / "index").mkdir(parents=True, exist_ok=True)
    (ocr_dir / "structure" / "blocks.structured.jsonl").write_text(
        json.dumps({"blocks": [key]}), encoding="utf-8"
    )
    (ocr_dir / "index" / "structure-tree.json").write_text(
        json.dumps({"root": key}), encoding="utf-8"
    )
    (ocr_dir / "index" / "role-index.json").write_text(
        json.dumps({"roles": [key]}), encoding="utf-8"
    )
    if pending:
        (ocr_dir / "index" / "result-hash.pending").write_text("pending", encoding="utf-8")
    else:
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
        from paperforge.memory.schema import ensure_schema

        ensure_schema(conn)
        for key in keys:
            ocr_hash = _published_ocr_hash(vault, key)
            manifest = _manifest_for(key, ocr_hash)
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (f"manifest:{key}", json.dumps(manifest)),
            )
            conn.execute(
                "INSERT OR REPLACE INTO vec_fulltext_meta (paper_id, chunk_index, text) VALUES (?, ?, ?)",
                (key, 0, f"{key}-ft1"),
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
        assert payload["papers"]["KEY1"] == {
            "ocr": "current", "retrieval": "current", "vector": "current",
        }

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
            json.dumps({"blocks": ["KEY1", "changed"]}), encoding="utf-8"
        )
        payload = probe_lineage(vault)
        assert payload["papers"]["KEY1"] == {
            "ocr": "stale", "retrieval": "stale", "vector": "stale",
        }

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
