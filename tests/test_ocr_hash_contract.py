"""#126 PR A — canonical OCR result hash contract, pending marker, structured
rebuild results, and reader safety."""
from __future__ import annotations

import json
from pathlib import Path

from paperforge.memory.builder import _incremental_units_only, _resolve_ocr_result_hash
from paperforge.worker.ocr_hash import (
    OCR_RESULT_HASH_ARTIFACTS,
    clear_result_hash_pending,
    compute_ocr_result_hash,
    create_result_hash_pending,
    has_result_hash_pending,
    publish_ocr_result_hash,
)
from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys


def _paper_root(tmp_path: Path, key: str = "PAPER01") -> Path:
    root = tmp_path / "ocr" / key
    for rel in OCR_RESULT_HASH_ARTIFACTS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": rel}), encoding="utf-8")
    return root


class TestCanonicalHash:
    def test_hash_covers_all_three_artifacts(self, tmp_path):
        root = _paper_root(tmp_path)
        digest = compute_ocr_result_hash(root)
        assert digest is not None and len(digest) == 64

    def test_missing_artifact_returns_none(self, tmp_path):
        root = _paper_root(tmp_path)
        (root / "index" / "role-index.json").unlink()
        assert compute_ocr_result_hash(root) is None

    def test_any_artifact_change_changes_hash(self, tmp_path):
        root = _paper_root(tmp_path)
        before = compute_ocr_result_hash(root)
        (root / "index" / "role-index.json").write_text("{}", encoding="utf-8")
        assert compute_ocr_result_hash(root) != before

    def test_fixed_order_deterministic(self, tmp_path):
        root = _paper_root(tmp_path)
        assert compute_ocr_result_hash(root) == compute_ocr_result_hash(root)


class TestPendingMarker:
    def test_publish_creates_atomic_hash_and_clears_marker(self, tmp_path):
        root = _paper_root(tmp_path)
        create_result_hash_pending(root)
        assert has_result_hash_pending(root)
        digest = publish_ocr_result_hash(root)
        clear_result_hash_pending(root)
        assert digest == compute_ocr_result_hash(root)
        assert (root / "index" / "result-hash.txt").read_text(encoding="utf-8") == digest
        assert not has_result_hash_pending(root)

    def test_failure_leaves_marker(self, tmp_path):
        root = _paper_root(tmp_path)
        create_result_hash_pending(root)
        (root / "index" / "role-index.json").unlink()
        assert publish_ocr_result_hash(root) is None
        assert has_result_hash_pending(root)

    def test_previous_hash_kept_until_verified_publish(self, tmp_path):
        root = _paper_root(tmp_path)
        digest = publish_ocr_result_hash(root)
        assert digest is not None
        create_result_hash_pending(root)
        (root / "index" / "role-index.json").unlink()
        # stale level-1 file still on disk but marker present
        assert (root / "index" / "result-hash.txt").exists()
        assert has_result_hash_pending(root)


class TestReaderSafety:
    def test_pending_marker_makes_reader_return_empty(self, tmp_path):
        root = _paper_root(tmp_path)
        publish_ocr_result_hash(root)
        create_result_hash_pending(root)
        assert _resolve_ocr_result_hash(root) == ""

    def test_level1_used_when_no_marker(self, tmp_path):
        root = _paper_root(tmp_path)
        digest = publish_ocr_result_hash(root)
        assert _resolve_ocr_result_hash(root) == digest

    def test_level2_fallback_matches_shared_helper(self, tmp_path):
        root = _paper_root(tmp_path)
        assert _resolve_ocr_result_hash(root) == compute_ocr_result_hash(root)

    def test_pending_paper_skipped_by_incremental_build(self, tmp_path, monkeypatch):
        """A paper with a pending marker is neither rebuilt nor cleared."""
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
        conn.execute("CREATE TABLE body_units (paper_id TEXT)")
        conn.execute("CREATE TABLE body_units_fts (paper_id TEXT)")
        conn.execute("CREATE TABLE object_units (paper_id TEXT)")

        root = _paper_root(tmp_path)
        create_result_hash_pending(root)
        items = [{"zotero_key": "PAPER01"}]

        rebuilt: list[str] = []
        monkeypatch.setattr(
            "paperforge.memory.builder._rebuild_paper_units",
            lambda conn, key, paper_dir, tree, blocks, vault=None: rebuilt.append(key),
        )
        _incremental_units_only(conn, items, tmp_path / "ocr")
        assert rebuilt == []
        assert conn.execute("SELECT COUNT(*) FROM body_units").fetchone()[0] == 0

    def test_clear_marker_allows_incremental_build(self, tmp_path, monkeypatch):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
        conn.execute("CREATE TABLE body_units (paper_id TEXT)")
        conn.execute("CREATE TABLE body_units_fts (paper_id TEXT)")
        conn.execute("CREATE TABLE object_units (paper_id TEXT)")

        root = _paper_root(tmp_path)
        publish_ocr_result_hash(root)
        clear_result_hash_pending(root)
        items = [{"zotero_key": "PAPER01"}]

        rebuilt: list[str] = []
        monkeypatch.setattr(
            "paperforge.memory.builder._rebuild_paper_units",
            lambda conn, key, paper_dir, tree, blocks, vault=None: rebuilt.append(key),
        )
        _incremental_units_only(conn, items, tmp_path / "ocr")
        assert rebuilt == ["PAPER01"]


class TestStructuredResults:
    def test_mixed_outcomes_aggregated(self, tmp_path, monkeypatch):
        outcomes = {
            "A": {"key": "A", "status": "ok"},
            "B": {"key": "B", "status": "failed", "error": "boom"},
            "C": {"key": "C", "status": "skipped", "reason": "no_raw_blocks"},
        }
        monkeypatch.setattr(
            "paperforge.worker.ocr_rebuild._rebuild_one_paper",
            lambda vault, key: outcomes[key],
        )
        result = run_derived_rebuild_for_keys(tmp_path, ["A", "B", "C"], parallel=0)
        assert result["success_keys"] == ["A"]
        assert result["failed_keys"] == ["B"]
        assert result["skipped"] == [{"key": "C", "reason": "no_raw_blocks"}]
        assert result["rebuild_count"] == 1

    def test_exception_is_per_key_failure_not_crash(self, tmp_path, monkeypatch):
        def _explode(vault, key):
            if key == "A":
                raise RuntimeError("crash")
            return {"key": key, "status": "ok"}

        monkeypatch.setattr("paperforge.worker.ocr_rebuild._rebuild_one_paper", _explode)
        result = run_derived_rebuild_for_keys(tmp_path, ["A", "B"], parallel=0)
        assert result["failed_keys"] == ["A"]
        assert result["success_keys"] == ["B"]

    def test_stop_marks_unprocessed_as_skipped(self, tmp_path, monkeypatch):
        calls = [0]

        def _stop_after_one():
            calls[0] += 1
            return calls[0] > 1

        monkeypatch.setattr(
            "paperforge.worker.ocr_rebuild._rebuild_one_paper",
            lambda vault, key: {"key": key, "status": "ok"},
        )
        result = run_derived_rebuild_for_keys(
            tmp_path, ["A", "B", "C"], parallel=0, stop_check=_stop_after_one
        )
        assert result["success_keys"] == ["A"]
        assert {s["key"] for s in result["skipped"]} == {"B", "C"}
        assert all(s["reason"] == "stopped" for s in result["skipped"])

    def test_empty_keys(self, tmp_path):
        result = run_derived_rebuild_for_keys(tmp_path, [], parallel=0)
        assert result == {
            "success_keys": [],
            "failed_keys": [],
            "skipped": [],
            "results": [],
            "rebuild_count": 0,
        }
