"""OCR integration tests for build_from_index() — real main-path coverage.

These tests exercise the full scheduling contract with minimal OCR
artifacts: fresh build, OCR-only incremental, artifacts disappearance,
partial derived state, and transaction failure. Helper unit tests alone
missed multiple regressions (imports dropped, fast-path guards, hash
materialization) — these tests cover those paths.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Fixture helpers ───────────────────────────────────────────────────────


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "03_Resources" / "Literature" / "骨科").mkdir(parents=True)
    (vault / "System" / "PaperForge").mkdir(parents=True)
    return vault


def _write_index(vault: Path, items: list[dict]) -> None:
    from paperforge.worker.asset_index import atomic_write_index, get_index_path

    idx_path = get_index_path(vault)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_index(idx_path, {"items": items, "generated_at": ""})


def _make_ocr_artifacts(vault: Path, key: str, *, hash_content: str = "v1") -> None:
    """Create structure-tree.json, blocks.structured.jsonl, role-index.json,
    and result-hash.txt for a paper."""
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / key
    index_dir = ocr_dir / "index"
    structure_dir = ocr_dir / "structure"
    index_dir.mkdir(parents=True, exist_ok=True)
    structure_dir.mkdir(parents=True, exist_ok=True)

    tree = {
        "paper_id": key,
        "nodes": [
            {
                "node_id": "sec:intro",
                "kind": "section",
                "title": "Introduction",
                "level": 1,
                "section_path": ["Introduction"],
                "page_span": [1, 2],
                "own_block_ids": ["p1:b1"],
                "subtree_block_ids": ["p1:b1"],
                "children": [],
            }
        ],
    }
    (index_dir / "structure-tree.json").write_text(
        json.dumps(tree, ensure_ascii=False), encoding="utf-8"
    )

    blocks = [
        {"block_id": "b1", "page": 1, "role": "body_paragraph",
         "text": f"This is the introduction paragraph for {key}."}
    ]
    (structure_dir / "blocks.structured.jsonl").write_text(
        "\n".join(json.dumps(b, ensure_ascii=False) for b in blocks) + "\n",
        encoding="utf-8",
    )

    role_index = {"figure_captions": [], "table_captions": [], "headings": []}
    (index_dir / "role-index.json").write_text(
        json.dumps(role_index, ensure_ascii=False), encoding="utf-8"
    )

    (index_dir / "result-hash.txt").write_text(hash_content, encoding="utf-8")

def _db(vault: Path):
    from paperforge.memory.db import get_connection, get_memory_db_path

    return get_connection(get_memory_db_path(vault))



# ── A. Fresh OCR build ────────────────────────────────────────────────────


def test_fresh_ocr_build_creates_units(tmp_path: Path) -> None:
    """Fresh DB + minimal OCR artifacts → papers, units, manifest created;
    second run stabilizes to no-change."""
    from paperforge.memory.builder import build_from_index
    from paperforge.memory.schema import ensure_schema

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A")
    _write_index(vault, [{"zotero_key": "A", "title": "Paper A", "domain": "骨科"}])

    r1 = build_from_index(vault)
    assert r1.get("papers_indexed", 0) >= 1

    conn = _db(vault)
    ensure_schema(conn)
    body_units = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0]
    manifest = conn.execute("SELECT 1 FROM meta WHERE key='manifest:A'").fetchone()
    assert body_units >= 1, f"A should have body units, got {body_units}"
    assert manifest is not None, "A should have a manifest"
    conn.close()

    # Second run: same content → fast path (hash_match True)
    r2 = build_from_index(vault)
    assert r2.get("hash_match") is True, "second identical run should be fast path"


# ── B. OCR-only incremental ───────────────────────────────────────────────


def test_ocr_only_change_rebuilds_only_that_paper(tmp_path: Path) -> None:
    """Change only A's ocr_result_hash → only A's units rebuilt, B untouched,
    A's old vectors invalidated, A's paper_state_hash preserved."""
    from paperforge.memory.builder import build_from_index

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A", hash_content="v1")
    _make_ocr_artifacts(vault, "B", hash_content="v1")
    _write_index(vault, [
        {"zotero_key": "A", "title": "Paper A", "domain": "骨科"},
        {"zotero_key": "B", "title": "Paper B", "domain": "骨科"},
    ])
    build_from_index(vault)

    conn = _db(vault)
    a_units_v1 = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0]
    b_units_v1 = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='B'").fetchone()[0]
    a_state_hash = conn.execute("SELECT value FROM meta WHERE key='paper_state_hash:A'").fetchone()[0]
    conn.close()

    # Change A's OCR result hash only (content in tree stays same)
    _make_ocr_artifacts(vault, "A", hash_content="v2")
    r = build_from_index(vault)

    conn = _db(vault)
    a_units_v2 = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0]
    b_units_v2 = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='B'").fetchone()[0]
    a_state_hash_v2 = conn.execute("SELECT value FROM meta WHERE key='paper_state_hash:A'").fetchone()[0]
    a_manifest = conn.execute("SELECT value FROM meta WHERE key='manifest:A'").fetchone()
    a_vectors = conn.execute("SELECT COUNT(*) FROM vec_body_meta WHERE paper_id='A'").fetchone()[0]
    conn.close()

    assert a_units_v1 == a_units_v2, "A units rebuilt (same count expected)"
    assert b_units_v1 == b_units_v2, "B units untouched"
    assert a_state_hash == a_state_hash_v2, "paper_state_hash preserved (metadata unchanged)"
    assert a_manifest is not None and "v2" in a_manifest[0], "manifest updated to v2"
    assert a_vectors == 0, "A's vectors invalidated after OCR change"
    assert set(r.get("changed", [])) == set(), "metadata unchanged → no paper in changed set"


# ── C. Artifacts disappeared ──────────────────────────────────────────────


def test_artifacts_disappear_invalidate_state_fast_path(tmp_path: Path) -> None:
    """Delete A's OCR artifacts with canonical hash unchanged (fast path) →
    units/manifest/vectors cleared, papers row + paper_state_hash preserved."""
    from paperforge.memory.builder import build_from_index

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A")
    _write_index(vault, [{"zotero_key": "A", "title": "Paper A", "domain": "骨科"}])
    build_from_index(vault)

    # Delete A's OCR artifacts entirely
    import shutil
    shutil.rmtree(vault / "System" / "PaperForge" / "ocr" / "A")

    # Canonical index unchanged → fast path runs
    r = build_from_index(vault)

    conn = _db(vault)
    assert conn.execute("SELECT 1 FROM papers WHERE zotero_key='A'").fetchone() is not None, \
        "papers row preserved"
    assert conn.execute("SELECT 1 FROM meta WHERE key='paper_state_hash:A'").fetchone() is not None, \
        "paper_state_hash preserved (metadata layer)"
    assert conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0] == 0, \
        "body units cleared"
    assert conn.execute("SELECT 1 FROM meta WHERE key='manifest:A'").fetchone() is None, \
        "manifest cleared"
    assert conn.execute("SELECT COUNT(*) FROM vec_body_meta WHERE paper_id='A'").fetchone()[0] == 0, \
        "vectors cleared"
    conn.close()
    assert r.get("hash_match") is True, "should have been fast path"


def test_artifacts_disappear_invalidate_state_metadata_change(tmp_path: Path) -> None:
    """Delete A's OCR artifacts AND change B's title → both handled correctly."""
    from paperforge.memory.builder import build_from_index

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A")
    _make_ocr_artifacts(vault, "B")
    _write_index(vault, [
        {"zotero_key": "A", "title": "Paper A", "domain": "骨科"},
        {"zotero_key": "B", "title": "Paper B", "domain": "骨科"},
    ])
    build_from_index(vault)

    # A's artifacts gone; B's title changes
    import shutil
    shutil.rmtree(vault / "System" / "PaperForge" / "ocr" / "A")
    _write_index(vault, [
        {"zotero_key": "A", "title": "Paper A", "domain": "骨科"},
        {"zotero_key": "B", "title": "Paper B v2", "domain": "骨科"},
    ])
    r = build_from_index(vault)

    conn = _db(vault)
    assert conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='B'").fetchone()[0] >= 1
    conn.close()
    assert set(r.get("changed", [])) == {"B"}, f"only B should be metadata-changed, got {r.get('changed')}"


# ── D. Partial/legacy derived state ───────────────────────────────────────


def test_object_only_derived_state_cleared(tmp_path: Path) -> None:
    """Paper with only object_units (no body_units) still gets cleared when
    OCR artifacts disappear."""
    from paperforge.memory.builder import build_from_index
    from paperforge.memory.schema import ensure_schema

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A")
    _write_index(vault, [{"zotero_key": "A", "title": "Paper A", "domain": "骨科"}])
    build_from_index(vault)

    # Delete artifacts AND remove body_units manually to simulate partial state
    import shutil
    shutil.rmtree(vault / "System" / "PaperForge" / "ocr" / "A")
    conn = _db(vault)
    ensure_schema(conn)
    conn.execute("DELETE FROM body_units WHERE paper_id='A'")
    conn.commit()
    conn.close()

    build_from_index(vault)

    conn = _db(vault)
    # manifest should be cleared (we created it during first build)
    assert conn.execute("SELECT 1 FROM meta WHERE key='manifest:A'").fetchone() is None, \
        "manifest cleared for object-only partial state"
    assert conn.execute("SELECT 1 FROM papers WHERE zotero_key='A'").fetchone() is not None, \
        "papers row preserved"
    conn.close()


def test_manifest_only_derived_state_cleared(tmp_path: Path) -> None:
    """Paper with only a manifest (no units) still gets invalidated."""
    from paperforge.memory.builder import build_from_index
    from paperforge.memory.schema import ensure_schema

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A")
    _write_index(vault, [{"zotero_key": "A", "title": "Paper A", "domain": "骨科"}])
    build_from_index(vault)

    import shutil
    shutil.rmtree(vault / "System" / "PaperForge" / "ocr" / "A")
    conn = _db(vault)
    ensure_schema(conn)
    conn.execute("DELETE FROM body_units WHERE paper_id='A'")
    conn.execute("DELETE FROM object_units WHERE paper_id='A'")
    conn.commit()
    conn.close()

    build_from_index(vault)

    conn = _db(vault)
    assert conn.execute("SELECT 1 FROM meta WHERE key='manifest:A'").fetchone() is None, \
        "manifest cleared (manifest-only state)"
    conn.close()


# ── E. Transaction failure ────────────────────────────────────────────────


def test_unit_rebuild_failure_rolls_back_canonical_hash(tmp_path: Path, monkeypatch) -> None:
    """If unit rebuild throws mid-way, the transaction rolls back — old units
    intact, canonical hash not advanced, next run retries."""
    import importlib
    from paperforge.memory import builder as builder_mod
    from paperforge.memory.schema import ensure_schema

    vault = _make_vault(tmp_path)
    _make_ocr_artifacts(vault, "A", hash_content="v1")
    _write_index(vault, [{"zotero_key": "A", "title": "Paper A", "domain": "骨科"}])
    builder_mod.build_from_index(vault)

    conn = _db(vault)
    ensure_schema(conn)
    units_before = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0]
    hash_before = conn.execute("SELECT value FROM meta WHERE key='canonical_index_hash'").fetchone()[0]
    conn.close()

    # Change OCR hash → rebuild will trigger; make it throw
    _make_ocr_artifacts(vault, "A", hash_content="v2")
    real_upsert = builder_mod._upsert_body_units

    def _boom(*args, **kwargs):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(builder_mod, "_upsert_body_units", _boom)
    with pytest.raises(RuntimeError, match="injected failure"):
        builder_mod.build_from_index(vault)

    # Transaction rolled back
    conn = _db(vault)
    units_after = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id='A'").fetchone()[0]
    hash_after = conn.execute("SELECT value FROM meta WHERE key='canonical_index_hash'").fetchone()[0]
    conn.close()
    assert units_after == units_before, "units not half-updated"
    assert hash_after == hash_before, "canonical hash not advanced on failure"

    # Next run retries successfully
    monkeypatch.setattr(builder_mod, "_upsert_body_units", real_upsert)
    r3 = builder_mod.build_from_index(vault)
    assert r3 is not None, "retry succeeds"
