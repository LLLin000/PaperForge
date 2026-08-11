"""T3 — memory build papers-scope seam (#164).

Scope fidelity: affected_keys ⊆ requested_keys; subset semantics under
partial success; scoped builds never delete and never touch non-requested
papers' rows (whitelisted operation-global metadata may change).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.memory.builder import build_for_keys

from tests.conftest import canonical_test_config


# ── Fixture helpers (mirror test_build_incremental_ocr.py) ─────────────────


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System", resources_dir="03_Resources")
    (vault / "03_Resources" / "Literature" / "骨科").mkdir(parents=True)
    (vault / "System" / "PaperForge").mkdir(parents=True)
    return vault


def _write_index(vault: Path, items: list[dict]) -> None:
    from paperforge.worker.asset_index import atomic_write_index, get_index_path

    idx_path = get_index_path(vault)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_index(idx_path, {"items": items, "generated_at": ""})


def _make_ocr_artifacts(vault: Path, key: str, *, hash_content: str = "v1") -> None:
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
    (index_dir / "structure-tree.json").write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    blocks = [
        {"block_id": "b1", "page": 1, "role": "body_paragraph",
         "text": f"This is the introduction paragraph for {key}."}
    ]
    (structure_dir / "blocks.structured.jsonl").write_text(
        "\n".join(json.dumps(b, ensure_ascii=False) for b in blocks) + "\n",
        encoding="utf-8",
    )
    (index_dir / "role-index.json").write_text(
        json.dumps({"figure_captions": [], "table_captions": [], "headings": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    (index_dir / "result-hash.txt").write_text(hash_content, encoding="utf-8")


def _entry(key: str, title: str) -> dict:
    return {"zotero_key": key, "title": title, "domain": "骨科"}


def _papers(vault: Path, key: str) -> dict:
    """Full row snapshot of one paper (all columns, rowid, updated_at)."""
    from paperforge.memory.db import get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(vault))
    try:
        row = conn.execute("SELECT * FROM papers WHERE zotero_key = ?", (key,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _rows(vault: Path, sql: str, key: str) -> list[dict]:
    from paperforge.memory.db import get_connection, get_memory_db_path

    conn = get_connection(get_memory_db_path(vault))
    try:
        return [dict(r) for r in conn.execute(sql, (key,)).fetchall()]
    finally:
        conn.close()


def _snapshot(vault: Path, keys: tuple[str, ...]) -> dict[str, object]:
    """Byte-identity snapshot of everything owned by the given papers."""
    out: dict[str, object] = {}
    for key in keys:
        out[f"papers:{key}"] = _papers(vault, key)
        out[f"body:{key}"] = _rows(vault, "SELECT * FROM body_units WHERE paper_id = ? ORDER BY unit_id", key)
        out[f"obj:{key}"] = _rows(vault, "SELECT * FROM object_units WHERE paper_id = ? ORDER BY unit_id", key)
        out[f"alias:{key}"] = _rows(vault, "SELECT * FROM paper_aliases WHERE paper_id = ? ORDER BY alias", key)
        out[f"asset:{key}"] = _rows(vault, "SELECT * FROM paper_assets WHERE paper_id = ? ORDER BY asset_type", key)
        out[f"manifest:{key}"] = _rows(vault, "SELECT value FROM meta WHERE key = ?", f"manifest:{key}")
        out[f"state:{key}"] = _rows(vault, "SELECT value FROM meta WHERE key = ?", f"paper_state_hash:{key}")
    return out


def _three_paper_vault(tmp_path: Path) -> Path:
    vault = _make_vault(tmp_path)
    for key in ("A", "B", "C"):
        _make_ocr_artifacts(vault, key)
    _write_index(vault, [_entry("A", "Paper A"), _entry("B", "Paper B"), _entry("C", "Paper C")])
    build_for_keys(vault, None)  # full build baseline
    return vault


# ── subset semantics (the acceptance test) ─────────────────────────────────

class TestSubsetSemantics:
    def test_scoped_build_touches_only_requested_keys(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        before = _snapshot(vault, ("B", "C"))

        # Change ONLY A: title + OCR artifacts.
        _write_index(vault, [
            _entry("A", "Paper A v2"), _entry("B", "Paper B"), _entry("C", "Paper C"),
        ])
        _make_ocr_artifacts(vault, "A", hash_content="v2")

        result = build_for_keys(vault, ["A", "B"])

        assert set(result["changed"]) == {"A"}
        assert result["deleted"] == []
        after = _snapshot(vault, ("B", "C"))
        # B and C are byte-identical (rowid/updated_at included).
        assert after == before, "non-requested papers changed"
        # A actually rebuilt.
        assert _papers(vault, "A")["title"] == "Paper A v2"

    def test_scoped_build_with_unchanged_keys_is_noop(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        before = _snapshot(vault, ("A", "B", "C"))
        result = build_for_keys(vault, ["A"])
        assert set(result.get("changed", [])) <= {"A"}
        assert result.get("deleted", []) == []
        assert _snapshot(vault, ("A", "B", "C")) == before

    def test_scoped_build_never_deletes_non_requested(self, tmp_path: Path) -> None:
        """Request [A] while B/C exist in the DB — the deletion gate holds."""
        vault = _three_paper_vault(tmp_path)
        before_b = _snapshot(vault, ("B",))
        # Drop B from the index entirely; request only A.
        _write_index(vault, [_entry("A", "Paper A"), _entry("C", "Paper C")])
        result = build_for_keys(vault, ["A"])
        assert result["deleted"] == []
        assert _snapshot(vault, ("B",)) == before_b, "scoped build deleted a non-requested paper"

    def test_scoped_artifacts_gone_clears_requested_only(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        before = _snapshot(vault, ("B", "C"))
        # Delete A's OCR artifacts; scoped build must clear A's units but
        # leave B/C untouched.
        import shutil

        shutil.rmtree(vault / "System" / "PaperForge" / "ocr" / "A")
        result = build_for_keys(vault, ["A"])
        assert _rows(vault, "SELECT COUNT(*) AS n FROM body_units WHERE paper_id = ?", "A") == [{"n": 0}]
        assert _snapshot(vault, ("B", "C")) == before


# ── canonical-keys validation ──────────────────────────────────────────────

class TestKeyValidation:
    def test_unknown_key_raises(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        before = _snapshot(vault, ("A", "B", "C"))
        with pytest.raises(ValueError, match="ZZZ"):
            build_for_keys(vault, ["A", "ZZZ"])
        # DB untouched on validation failure.
        assert _snapshot(vault, ("A", "B", "C")) == before

    def test_full_build_unchanged_behavior(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        result = build_for_keys(vault, None)
        assert result["hash_match"] is True  # second full build fast-paths


# ── action registry / CLI wiring ───────────────────────────────────────────

def _run_cli(*argv: str) -> tuple[int, dict]:
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


class TestGlobalFreshness:
    """#164 corrective: the global canonical_index_hash is a correctness
    marker — only all-scope builds advance it; a scoped publish must not
    mask non-requested papers' stale metadata."""

    def _cached_hash(self, vault: Path):
        from paperforge.memory.db import get_connection, get_memory_db_path

        conn = get_connection(get_memory_db_path(vault))
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key='canonical_index_hash'"
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def test_scoped_build_does_not_advance_global_hash(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        before = self._cached_hash(vault)
        assert before

        # A + B change in the canonical index; scope only A.
        _write_index(vault, [
            _entry("A", "Paper A v2"), _entry("B", "Paper B v2"), _entry("C", "Paper C"),
        ])
        _make_ocr_artifacts(vault, "A", hash_content="v2")
        result = build_for_keys(vault, ["A"])
        assert set(result["changed"]) == {"A"}
        # The global freshness marker is NOT advanced by the scoped build.
        assert self._cached_hash(vault) == before

    def test_full_build_after_scoped_still_rebuilds_stale_paper(self, tmp_path: Path) -> None:
        """The regression: A+B changed, scope A, then full build — B must be
        rebuilt (the scoped publish must not have fast-pathed it away)."""
        vault = _three_paper_vault(tmp_path)
        _write_index(vault, [
            _entry("A", "Paper A v2"), _entry("B", "Paper B v2"), _entry("C", "Paper C"),
        ])
        _make_ocr_artifacts(vault, "A", hash_content="v2")
        build_for_keys(vault, ["A"])

        full = build_for_keys(vault, None)
        assert full["hash_match"] is False
        assert "B" in set(full["changed"]), "full build must still see B's change"
        assert _papers(vault, "B")["title"] == "Paper B v2"

    def test_full_build_still_fast_paths_after_clean_full_build(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        full = build_for_keys(vault, None)
        assert full["hash_match"] is True


class TestScopedOnFreshDatabase:
    """#164 corrective: a scoped request on a fresh/destructive DB must not
    materialize the whole library — it reports global_rebuild_required."""

    def test_scoped_fresh_db_returns_global_rebuild_required(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        for key in ("A", "B", "C"):
            _make_ocr_artifacts(vault, key)
        _write_index(vault, [_entry("A", "A"), _entry("B", "B"), _entry("C", "C")])
        result = build_for_keys(vault, ["A"])
        assert result["global_rebuild_required"] is True
        # No paper rows were materialized by the scoped request.
        assert _papers(vault, "B") is None
        assert _papers(vault, "A") is None

    def test_unknown_key_on_fresh_db_has_zero_side_effects(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        _write_index(vault, [_entry("A", "A")])
        from paperforge.memory.db import get_memory_db_path

        db = get_memory_db_path(vault)
        before = db.exists()
        with pytest.raises(ValueError, match="ZZZ"):
            build_for_keys(vault, ["ZZZ"])
        # Validation happened before any writable DB access.
        assert db.exists() == before

    def test_scoped_action_fresh_db_is_structured_unavailable(self, tmp_path: Path) -> None:
        vault = _make_vault(tmp_path)
        for key in ("A", "B"):
            _make_ocr_artifacts(vault, key)
        _write_index(vault, [_entry("A", "A"), _entry("B", "B")])
        rc, payload = _run_cli(
            "--vault", str(vault), "action", "run", "memory.build",
            "--scope", "papers", "--key", "A", "--json",
        )
        assert rc == 1
        assert payload["error"]["code"] == "action.unavailable"


class TestRegistryAndCli:
    def test_action_unknown_key_is_exit_2(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        rc, payload = _run_cli(
            "--vault", str(vault), "action", "run", "memory.build",
            "--scope", "papers", "--key", "ZZZ", "--json",
        )
        assert rc == 2
        assert payload["error"]["code"] == "action.scope_invalid"

    def test_action_papers_scope_runs(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        _make_ocr_artifacts(vault, "A", hash_content="v3")
        _write_index(vault, [
            _entry("A", "Paper A v3"), _entry("B", "Paper B"), _entry("C", "Paper C"),
        ])
        rc, payload = _run_cli(
            "--vault", str(vault), "action", "run", "memory.build",
            "--scope", "papers", "--key", "A", "--json",
        )
        assert rc == 0, payload
        assert payload["data"]["changed"] == ["A"]
        # scoped follow-up intent carries the same keys
        assert payload["next_actions"][0]["scope"] == {"kind": "papers", "keys": ["A"]}

    def test_action_papers_scope_zero_keys_is_exit_2(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        rc, payload = _run_cli(
            "--vault", str(vault), "action", "run", "memory.build",
            "--scope", "papers", "--json",
        )
        assert rc == 2
        assert payload["error"]["code"] == "action.scope_invalid"

    def test_memory_cli_unknown_key_is_exit_2(self, tmp_path: Path) -> None:
        vault = _three_paper_vault(tmp_path)
        rc, payload = _run_cli("--vault", str(vault), "memory", "build", "--key", "ZZZ", "--json")
        assert rc == 2
        assert payload["error"]["code"] == "action.scope_invalid"
