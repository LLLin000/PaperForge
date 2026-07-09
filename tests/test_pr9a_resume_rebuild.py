"""Tests for PR9A: Resume & Rebuild Correctness."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Import shim: paperforge.commands.ocr lazily imports pipeline_paths from
# paperforge.worker._utils; provide the re-export before the ocr module loads.
# ---------------------------------------------------------------------------
import paperforge.config
from paperforge.worker._utils import pipeline_paths as _pipeline_paths_impl

paperforge.config.pipeline_paths = _pipeline_paths_impl

from paperforge.commands.ocr import _needs_derived_rebuild, _select_rebuild_keys
from paperforge.commands.embed import _pid_alive, _assert_collections_healthy
from paperforge.worker.ocr_rebuild import _apply_post_rebuild_version_flags

# ---------------------------------------------------------------------------
# _needs_derived_rebuild
# ---------------------------------------------------------------------------
# These tests patch paperforge.worker._utils.pipeline_paths because
# _needs_derived_rebuild imports it lazily at runtime.
# They also patch artifact_paths_for_root to avoid the real filesystem.


def _make_artifact_paths_mock(tmp_path, key, meta_content="{}",
                               blocks_raw_exists=True, source_meta_exists=True):
    """Build a mock for artifact_paths_for_root returning structured paths."""
    paper_dir = tmp_path / key
    paper_dir.mkdir(parents=True, exist_ok=True)
    meta_file = paper_dir / "meta.json"
    meta_file.write_text(meta_content)
    blocks_raw = paper_dir / "blocks_raw"
    if blocks_raw_exists:
        blocks_raw.mkdir(parents=True, exist_ok=True)
    source_meta = paper_dir / "source_metadata.json"
    if source_meta_exists:
        source_meta.write_text("{}")

    mock_artifacts = MagicMock()
    mock_artifacts.meta_json = meta_file
    mock_artifacts.paper_root = paper_dir
    mock_artifacts.blocks_raw = blocks_raw
    mock_artifacts.source_metadata = source_meta
    return mock_artifacts, paper_dir


class TestNeedsDerivedRebuild:
    """Tests for _needs_derived_rebuild."""

    PATCH_PP = "paperforge.worker._utils.pipeline_paths"
    PATCH_ART = "paperforge.commands.ocr.artifact_paths_for_root"

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=True)
    @patch("paperforge.commands.ocr.classify_version_state")
    def test_version_mismatch(self, mock_cvs, mock_cr, mock_art, mock_pp):
        """Stale derived_version triggers (True, 'version_mismatch')."""
        tmp_path = Path("/tmp/test_vm")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, _ = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts
        mock_cvs.return_value = {"derived_stale": True}

        assert _needs_derived_rebuild(Path("/vault"), "key") == (True, "version_mismatch")

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=True)
    @patch("paperforge.commands.ocr.classify_version_state")
    def test_missing_artifact(self, mock_cvs, mock_cr, mock_art, mock_pp):
        """Missing required artifact returns (True, 'missing:<name>')."""
        tmp_path = Path("/tmp/test_ma")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, paper_dir = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts
        mock_cvs.return_value = {"derived_stale": False}

        # Create all required files except index/role-index.json
        present = [
            "structure/blocks.structured.jsonl",
            "render/render-map.json",
            "index/structure-tree.json",
            "fulltext.md",
            "health/ocr_health.json",
        ]
        for rel in present:
            (paper_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (paper_dir / rel).write_text("")

        ok, reason = _needs_derived_rebuild(Path("/vault"), "key")
        assert ok is True
        assert reason == "missing:role-index.json"

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=True)
    @patch("paperforge.commands.ocr.classify_version_state")
    def test_current(self, mock_cvs, mock_cr, mock_art, mock_pp):
        """All checks pass -> (False, 'current')."""
        tmp_path = Path("/tmp/test_cu")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, paper_dir = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts
        mock_cvs.return_value = {"derived_stale": False}

        required = [
            "structure/blocks.structured.jsonl",
            "render/render-map.json",
            "index/structure-tree.json",
            "index/role-index.json",
            "fulltext.md",
            "health/ocr_health.json",
        ]
        for rel in required:
            (paper_dir / rel).parent.mkdir(parents=True, exist_ok=True)
            (paper_dir / rel).write_text("")

        assert _needs_derived_rebuild(Path("/vault"), "key") == (False, "current")

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=False)
    def test_cannot_rebuild(self, mock_cr, mock_art, mock_pp):
        """_can_rebuild=False -> (False, 'cannot_rebuild')."""
        tmp_path = Path("/tmp/test_cnr")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, _ = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts

        assert _needs_derived_rebuild(Path("/vault"), "key") == (False, "cannot_rebuild")

    def _write_blocks_structured(self, paper_dir, content="test content"):
        """Create a blocks.structured.jsonl with given content."""
        path = paper_dir / "structure" / "blocks.structured.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=True)
    def test_hash_stat_skip(self, mock_cr, mock_art, mock_pp):
        """Tier 1: mtime+size match stored values -> current, no hash call."""
        tmp_path = Path("/tmp/test_hss")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, paper_dir = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts

        blocks_path = self._write_blocks_structured(paper_dir)
        st = blocks_path.stat()
        mock_artifacts.blocks_structured = blocks_path

        # Write meta with matching hash + stat values
        meta = {"structured_content_hash": "abc123", "structured_mtime": st.st_mtime,
                "structured_size": st.st_size}
        meta_file = mock_artifacts.meta_json

        meta_file.write_text(json.dumps(meta))

        ok, reason = _needs_derived_rebuild(Path("/vault"), "key")
        assert ok is False
        assert reason == "current"

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=True)
    @patch("paperforge.commands.ocr.compute_structured_hash", return_value="abc")
    def test_hash_match_false_alarm(self, mock_csh, mock_cr, mock_art, mock_pp):
        """Tier 2: stat changed but hash matches -> false alarm recovery -> current."""
        tmp_path = Path("/tmp/test_hfa")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, paper_dir = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts

        blocks_path = self._write_blocks_structured(paper_dir)
        st = blocks_path.stat()
        mock_artifacts.blocks_structured = blocks_path

        # Deliberately wrong mtime/size to trigger Tier 2
        meta = {"structured_content_hash": "abc", "structured_mtime": 0, "structured_size": 0}

        meta_file = mock_artifacts.meta_json
        meta_file.write_text(json.dumps(meta))

        ok, reason = _needs_derived_rebuild(Path("/vault"), "key")
        assert ok is False
        assert reason == "current"

        # Verify meta was updated with correct stat values
        updated_meta = json.loads(meta_file.read_text())
        assert updated_meta["structured_mtime"] == st.st_mtime
        assert updated_meta["structured_size"] == st.st_size

    @patch(PATCH_PP)
    @patch(PATCH_ART)
    @patch("paperforge.commands.ocr._can_rebuild", return_value=True)
    @patch("paperforge.commands.ocr.compute_structured_hash", return_value="xyz")
    def test_hash_mismatch_triggers_rebuild(self, mock_csh, mock_cr, mock_art, mock_pp):
        """Tier 2: hash differs -> content_hash_changed."""
        tmp_path = Path("/tmp/test_hm")
        mock_pp.return_value = {"ocr": tmp_path}
        mock_artifacts, paper_dir = _make_artifact_paths_mock(tmp_path, "key")
        mock_art.return_value = mock_artifacts

        blocks_path = self._write_blocks_structured(paper_dir)
        mock_artifacts.blocks_structured = blocks_path

        meta = {"structured_content_hash": "abc", "structured_mtime": 0, "structured_size": 0}

        meta_file = mock_artifacts.meta_json
        meta_file.write_text(json.dumps(meta))

        ok, reason = _needs_derived_rebuild(Path("/vault"), "key")
        assert ok is True
        assert reason == "content_hash_changed"


# ---------------------------------------------------------------------------
# _select_rebuild_keys
# ---------------------------------------------------------------------------

class FakeRow:
    """Minimal replacement for OCRMaintenanceRow."""
    def __init__(self, key, status="done", can_rebuild=True):
        self.key = key
        self.status = status
        self.can_rebuild = can_rebuild


class TestSelectRebuildKeys:
    """Tests for _select_rebuild_keys."""

    @patch("paperforge.commands.ocr._needs_derived_rebuild")
    def test_all_papers_selects_stale_only(self, mock_need):
        """all_papers=True selects only keys where _needs_derived_rebuild is True."""
        rows = [
            FakeRow("stale1"),
            FakeRow("stale2"),
            FakeRow("current1"),
        ]

        def side_effect(vault, key):
            return (True, "version_mismatch") if key.startswith("stale") else (False, "current")

        mock_need.side_effect = side_effect

        selected, reasons = _select_rebuild_keys(
            Path("/vault"), rows, all_papers=True, status_filter=None, keys=None
        )
        assert selected == ["stale1", "stale2"]
        assert reasons == {"stale1": "version_mismatch", "stale2": "version_mismatch"}

    def test_explicit_keys_skip_version_check(self):
        """Explicit keys are selected regardless of version state."""
        rows = [
            FakeRow("current_key"),
            FakeRow("other_key"),
        ]

        selected, reasons = _select_rebuild_keys(
            Path("/vault"), rows, all_papers=False, status_filter=None, keys=["current_key"]
        )
        assert selected == ["current_key"]
        assert reasons == {}

    def test_status_filter_skips_version_check(self):
        """status_filter selects matching rows regardless of version state."""
        rows = [
            FakeRow("k1", status="done_degraded"),
            FakeRow("k2", status="done"),
        ]

        selected, reasons = _select_rebuild_keys(
            Path("/vault"), rows, all_papers=False, status_filter="done_degraded", keys=None
        )
        assert selected == ["k1"]
        assert reasons == {}

    def test_cannot_rebuild_excluded(self):
        """Keys with can_rebuild=False are excluded from explicit keys."""
        rows = [
            FakeRow("good", can_rebuild=True),
            FakeRow("bad", can_rebuild=False),
        ]
        selected, reasons = _select_rebuild_keys(
            Path("/vault"), rows, all_papers=False, status_filter=None, keys=["good", "bad"]
        )
        assert selected == ["good"]

    def test_empty_all_returns_empty(self):
        """all_papers=True with all current returns empty list."""
        rows = [FakeRow("p1"), FakeRow("p2")]

        with patch("paperforge.commands.ocr._needs_derived_rebuild", return_value=(False, "current")):
            selected, reasons = _select_rebuild_keys(
                Path("/vault"), rows, all_papers=True, status_filter=None, keys=None
            )
            assert selected == []
            assert reasons == {}


# ---------------------------------------------------------------------------
# _apply_post_rebuild_version_flags
# ---------------------------------------------------------------------------

class TestPostRebuildVersionFlags:
    """Tests for _apply_post_rebuild_version_flags."""

    def test_writes_derived_version(self):
        """Rebuild completion writes derived_version dict with structure_version."""
        meta = {"derived_stale": True, "ocr_status": "done", "version_state_updated_at": ""}
        result = _apply_post_rebuild_version_flags(meta)

        assert "derived_version" in result
        assert isinstance(result["derived_version"], dict)
        assert "structure_version" in result["derived_version"]
        assert not result["derived_stale"]
        assert result["version_state_updated_at"] != ""

    def test_preserves_existing_keys(self):
        """Function preserves other meta keys."""
        meta = {"zotero_key": "ABC123", "ocr_status": "done", "derived_stale": True}
        result = _apply_post_rebuild_version_flags(meta)
        assert result["zotero_key"] == "ABC123"


# ---------------------------------------------------------------------------
# _pid_alive
# ---------------------------------------------------------------------------

class TestPidAlive:
    """Tests for _pid_alive."""

    def test_dead_pid(self):
        """PID 0 or negative is always dead."""
        assert not _pid_alive(0)
        assert not _pid_alive(-1)


# ---------------------------------------------------------------------------
# _assert_collections_healthy
# ---------------------------------------------------------------------------

class TestAssertCollectionsHealthy:
    """Tests for _assert_collections_healthy (sqlite-vec path)."""

    def test_healthy_collections(self, tmp_path):
        """All three meta tables accessible -> (True, '')."""
        from paperforge.memory.db import get_connection, get_memory_db_path, ensure_vec_extension
        from paperforge.memory.schema import ensure_schema
        db_path = get_memory_db_path(tmp_path)
        conn = get_connection(db_path)
        try:
            ensure_vec_extension(conn)
            ensure_schema(conn)
        finally:
            conn.close()

        ok, msg = _assert_collections_healthy(tmp_path)
        assert ok is True
        assert msg == ""

    def test_corrupted_collection(self, tmp_path):
        """Missing paperforge.db -> (False, 'paperforge.db not found')."""
        ok, msg = _assert_collections_healthy(tmp_path)
        assert ok is False
        assert "paperforge.db not found" in msg
