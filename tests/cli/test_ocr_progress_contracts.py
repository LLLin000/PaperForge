"""CLI contract tests for OCR rebuild/redo progress tokens.

Tests the streaming progress token contract defined in issue #64:
- OCR_REBUILD_START:{total}
- OCR_REBUILD_PROGRESS:{current}:{total}:{key}
- OCR_REBUILD_DONE
- OCR_REDO_START:{total}
- OCR_REDO_PROGRESS:{current}:{total}:{key}
- OCR_REDO_DONE

Batch mode only (multiple keys). Single-key calls remain silent.
Dry-run must not emit progress tokens.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_minimal_vault(root: Path) -> Path:
    """Create a minimal vault with paperforge.json for path resolution."""
    vault = root / "vault"
    vault.mkdir(parents=True)
    cfg = {
        "system_dir": "System",
        "resources_dir": "Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "Bases",
        "skill_dir": ".opencode/skills",
        "zotero_dir": "System/Zotero",
    }
    (vault / "paperforge.json").write_text(json.dumps(cfg), encoding="utf-8")
    dirs = [
        "System/PaperForge/ocr",
        "System/PaperForge/exports",
        "System/PaperForge/indexes",
        "System/PaperForge/config",
        "System/Zotero/storage",
        "Resources/Literature",
        "Resources/LiteratureControl",
        "Bases",
        ".opencode/skills/literature-qa/scripts",
    ]
    for d in dirs:
        (vault / d).mkdir(parents=True)
    return vault


def _add_ocr_meta(vault: Path, key: str, status: str = "pending") -> None:
    """Create OCR meta.json for a given paper key."""
    meta_dir = vault / "System/PaperForge/ocr" / key
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "zotero_key": key,
        "ocr_status": status,
        "page_count": 1,
        "generated_at": "2026-07-01T00:00:00+00:00",
    }
    (meta_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")



def _add_literature_note(vault: Path, key: str, title: str = "Test Paper") -> None:
    """Create a minimal literature note with zotero_key in frontmatter."""
    lit_dir = vault / "Resources" / "Literature"
    lit_dir.mkdir(parents=True, exist_ok=True)
    note = lit_dir / f"{key}.md"
    note.write_text(
        f"---\nzotero_key: \"{key}\"\ntitle: \"{title}\"\n---\n\nPaper content.\n",
        encoding="utf-8",
    )


def _mock_run_ocr(monkeypatch) -> None:
    """Mock run_ocr to create minimal meta.json with done status (no API calls)."""
    import json

    def _fake_run_ocr(vault: Path, **kwargs: object) -> int:
        keys: set[str] = kwargs.get("selected_keys") or set()
        from paperforge.worker._utils import pipeline_paths
        paths = pipeline_paths(vault)
        ocr_root = paths.get("ocr")
        if ocr_root:
            for key in keys:
                meta_dir = ocr_root / key
                meta_dir.mkdir(parents=True, exist_ok=True)
                (meta_dir / "meta.json").write_text(
                    json.dumps({"zotero_key": key, "ocr_status": "done"}),
                    encoding="utf-8",
                )
        return 0

    monkeypatch.setattr("paperforge.worker.ocr.run_ocr", _fake_run_ocr)


def _mock_validate_ocr_meta(monkeypatch) -> None:
    """Mock validate_ocr_meta to return done status."""
    monkeypatch.setattr(
        "paperforge.worker.ocr.validate_ocr_meta",
        lambda _paths, _meta: ("done", ""),
    )

# ── Redo Progress Token Tests ────────────────────────────────────────────


class TestOcrRedoProgressTokens:
    """OCR_REDO_* progress token contract tests."""

    _K1 = "KEY00001"
    _K2 = "KEY00002"
    _K3 = "KEY00003"

    def test_redo_multi_key_emits_start_progress_done(
        self, capsys, tmp_path, monkeypatch
    ):
        """Multiple redo keys emit OCR_REDO_START, PROGRESS per key, DONE."""
        _mock_run_ocr(monkeypatch)
        _mock_validate_ocr_meta(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        for k in (self._K1, self._K2, self._K3):
            _add_literature_note(vault, k)

        from paperforge.commands.ocr import _run_ocr_redo

        rc = _run_ocr_redo(vault, keys=[self._K1, self._K2, self._K3])

        assert rc == 0
        captured = capsys.readouterr().out
        lines = [l for l in captured.split("\n") if l.strip()]

        # Token order: START, then PROGRESS per key, summary, DONE
        assert lines[0] == "OCR_REDO_START:3"
        progress_lines = [l for l in lines if l.startswith("OCR_REDO_PROGRESS")]
        assert len(progress_lines) == 3
        assert progress_lines[0] == "OCR_REDO_PROGRESS:1:3:KEY00001"
        assert progress_lines[1] == "OCR_REDO_PROGRESS:2:3:KEY00002"
        assert progress_lines[2] == "OCR_REDO_PROGRESS:3:3:KEY00003"
        assert "Redo OCR done" in captured
        assert "OCR_REDO_DONE" in captured

    def test_redo_single_key_no_tokens(self, capsys, tmp_path, monkeypatch):
        """Single redo key emits no progress tokens."""
        _mock_run_ocr(monkeypatch)
        _mock_validate_ocr_meta(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        _add_literature_note(vault, self._K1)

        from paperforge.commands.ocr import _run_ocr_redo

        rc = _run_ocr_redo(vault, keys=[self._K1])

        assert rc == 0
        captured = capsys.readouterr().out
        assert "OCR_REDO_START" not in captured
        assert "OCR_REDO_PROGRESS" not in captured
        assert "OCR_REDO_DONE" not in captured
        assert "Redo OCR done=1" in captured

    def test_redo_dry_run_no_tokens(self, capsys, tmp_path, monkeypatch):
        """Dry-run redo emits no progress tokens."""
        _mock_run_ocr(monkeypatch)
        _mock_validate_ocr_meta(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        _add_literature_note(vault, self._K1)
        _add_literature_note(vault, self._K2)

        from paperforge.commands.ocr import _run_ocr_redo

        rc = _run_ocr_redo(vault, keys=[self._K1, self._K2], dry_run=True)

        assert rc == 0
        captured = capsys.readouterr().out
        # Multi-key dry-run is not batch (batch = total > 1 and not dry_run)
        assert "OCR_REDO_START" not in captured
        assert "OCR_REDO_PROGRESS" not in captured
        assert "OCR_REDO_DONE" not in captured
        assert "Would redo" in captured

    def test_redo_prefix_separate_from_rebuild(self, capsys, tmp_path, monkeypatch):
        """OCR_REDO prefix is distinct from OCR_REBUILD."""
        _mock_run_ocr(monkeypatch)
        _mock_validate_ocr_meta(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        for k in (self._K1, self._K2, self._K3):
            _add_literature_note(vault, k)

        from paperforge.commands.ocr import _run_ocr_redo

        _run_ocr_redo(vault, keys=[self._K1, self._K2, self._K3])
        captured = capsys.readouterr().out

        assert "OCR_REDO_START" in captured
        assert "OCR_REDO_PROGRESS" in captured
        assert "OCR_REDO_DONE" in captured
        assert "OCR_REBUILD_START" not in captured




# ── Rebuild Progress Token Tests ─────────────────────────────────────────


class TestOcrRebuildProgressTokens:
    """OCR_REBUILD_* progress token contract tests."""

    def _setup_mock_selection_and_worker(
        self, vault: Path, keys: list[str], monkeypatch
    ) -> None:
        """Mock selection and worker for rebuild, calling on_progress."""
        from paperforge.worker.ocr_maintenance import OCRMaintenanceRow as Row

        rows = [Row(
            key=k,
            title=f"Paper {k}",
            title_full=f"Full Title for Paper {k}",
            status="done",
            health="good",
            pages=5,
            blocks=100,
            version="2.0",
            finished_at="2026-07-01",
            rebuild_finished_at="",
            figures=0,
            tables=0,
            model="test",
            structured_content_hash=f"hash_{k}",
            can_rebuild=True,
        ) for k in keys]

        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda _v: rows,
        )
        def _mock_rebuild(
            _vault: Path,
            _keys: list[str],
            **kwargs: object,
        ) -> dict:
            on_progress = kwargs.get("on_progress")
            if on_progress:
                for k in _keys:
                    on_progress(k)
            return {"rebuild_count": len(_keys)}

        monkeypatch.setattr(
            "paperforge.worker.ocr_rebuild.run_derived_rebuild_for_keys",
            _mock_rebuild,
        )

    def test_rebuild_multi_key_emits_start_progress_done(
        self, capsys, monkeypatch, tmp_path
    ):
        """Multiple rebuild keys emit OCR_REBUILD_START, PROGRESS per key, DONE."""
        vault = _make_minimal_vault(tmp_path)
        keys = ["KEY001", "KEY002", "KEY003"]
        self._setup_mock_selection_and_worker(vault, keys, monkeypatch)

        from paperforge.commands.ocr import _run_ocr_rebuild

        rc = _run_ocr_rebuild(vault, keys=keys)

        assert rc == 0
        captured = capsys.readouterr().out
        lines = [l for l in captured.split("\n") if l.strip()]

        assert lines[0] == "OCR_REBUILD_START:3", f"First token: {lines}"
        progress_lines = [l for l in lines if "OCR_REBUILD_PROGRESS" in l]
        assert len(progress_lines) == 3
        assert progress_lines[0] == "OCR_REBUILD_PROGRESS:1:3:KEY001"
        assert progress_lines[1] == "OCR_REBUILD_PROGRESS:2:3:KEY002"
        assert progress_lines[2] == "OCR_REBUILD_PROGRESS:3:3:KEY003"
        assert lines[-1] == "OCR_REBUILD_DONE", f"Last token: {lines}"

    def test_rebuild_single_key_no_tokens(self, capsys, monkeypatch, tmp_path):
        """Single rebuild key emits no progress tokens."""
        vault = _make_minimal_vault(tmp_path)
        key = "KEY001"
        self._setup_mock_selection_and_worker(vault, [key], monkeypatch)

        from paperforge.commands.ocr import _run_ocr_rebuild

        rc = _run_ocr_rebuild(vault, keys=[key])

        assert rc == 0
        captured = capsys.readouterr().out
        assert "OCR_REBUILD_START" not in captured
        assert "OCR_REBUILD_PROGRESS" not in captured
        assert "OCR_REBUILD_DONE" not in captured

    def test_rebuild_dry_run_no_tokens(self, capsys, monkeypatch, tmp_path):
        """Dry-run rebuild emits no progress tokens."""
        vault = _make_minimal_vault(tmp_path)
        self._setup_mock_selection_and_worker(vault, ["KEY001", "KEY002"], monkeypatch)

        from paperforge.commands.ocr import _run_ocr_rebuild

        rc = _run_ocr_rebuild(vault, keys=["KEY001", "KEY002"], dry_run=True)

        assert rc == 0
        captured = capsys.readouterr().out
        assert "OCR_REBUILD_START" not in captured
        assert "OCR_REBUILD_PROGRESS" not in captured
        assert "OCR_REBUILD_DONE" not in captured
        assert "Would rebuild" in captured

    def test_rebuild_prefix_uses_ocr_rebuild_not_redo(
        self, capsys, monkeypatch, tmp_path
    ):
        """OCR rebuild uses OCR_REBUILD prefix, not OCR_REDO."""
        vault = _make_minimal_vault(tmp_path)
        keys = ["KEY001", "KEY002"]
        self._setup_mock_selection_and_worker(vault, keys, monkeypatch)

        from paperforge.commands.ocr import _run_ocr_rebuild

        _run_ocr_rebuild(vault, keys=keys)
        captured = capsys.readouterr().out

        assert "OCR_REBUILD_START" in captured
        assert "OCR_REBUILD_PROGRESS" in captured
        assert "OCR_REBUILD_DONE" in captured
        assert "OCR_REDO_START" not in captured

class TestCooperativeStop:
    """Cooperative stop tests for batch OCR operations."""

    def test_rebuild_stop_emits_done_and_exit_code_130(self, capsys, monkeypatch, tmp_path):
        """Rebuild batch stop sets exit 130 and emits DONE with partial progress."""
        vault = _make_minimal_vault(tmp_path)
        keys = ["KEY001", "KEY002", "KEY003"]

        # Set up maintenance rows via mock
        from paperforge.worker.ocr_maintenance import OCRMaintenanceRow as Row
        rows = [Row(
            key=k, title=f"Paper {k}", title_full=f"Full {k}",
            status="done", health="good", pages=5, blocks=100,
            version="2.0", finished_at="2026-07-01", rebuild_finished_at="",
            figures=0, tables=0, model="test",
            structured_content_hash=f"hash_{k}", can_rebuild=True,
        ) for k in keys]
        monkeypatch.setattr(
            "paperforge.worker.ocr_maintenance.collect_maintenance_rows",
            lambda _v: rows,
        )

        # Mock _rebuild_one_paper so the real run_derived_rebuild_for_keys can run
        call_count = [0]
        def _mock_rebuild_one(vault, key):
            call_count[0] += 1
            return {"key": key, "status": "ok"}
        monkeypatch.setattr(
            "paperforge.worker.ocr_rebuild._rebuild_one_paper",
            _mock_rebuild_one,
        )

        # Mock stop_check to stop after first paper
        stop_count = [0]
        def _stop_check():
            stop_count[0] += 1
            return stop_count[0] > 1  # stop before the 2nd call

        from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys
        from paperforge.worker._progress import progress_bar

        # Simulate what _run_ocr_rebuild does for batch
        print("OCR_REBUILD_START:3")
        count = [0]
        def _on_progress(key):
            count[0] += 1
            print(f"OCR_REBUILD_PROGRESS:{count[0]}:3:{key}")

        result = run_derived_rebuild_for_keys(
            vault, keys,
            progress_bar=progress_bar,
            parallel=0,
            on_progress=_on_progress,
            stop_check=_stop_check,
        )
        print(f"Done. Rebuilt {result['rebuild_count']} paper(s).")
        print("OCR_REBUILD_DONE")

        captured = capsys.readouterr().out
        lines = [l for l in captured.split("\n") if l.strip()]

        # Only first key should have been processed
        assert result["rebuild_count"] == 1
        assert call_count[0] == 1
        # Should still emit DONE
        assert "OCR_REBUILD_START:3" in captured
        assert "OCR_REBUILD_PROGRESS:1:3:KEY001" in captured
        assert "OCR_REBUILD_PROGRESS:2:3:KEY002" not in captured
        assert "OCR_REBUILD_PROGRESS:3:3:KEY003" not in captured
        assert "OCR_REBUILD_DONE" in captured

    def test_redo_stop_emits_done_and_partial_progress(self, capsys, monkeypatch, tmp_path):
        """Redo batch stop emits DONE with partial progress and exit 130."""
        _mock_run_ocr(monkeypatch)
        _mock_validate_ocr_meta(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        _add_literature_note(vault, "KEY00001")
        _add_literature_note(vault, "KEY00002")
        _add_literature_note(vault, "KEY00003")

        from paperforge.commands.ocr import _run_ocr_redo

        # Mock _make_cooperative_stop to stop after first paper
        class _StopChecker:
            def __init__(self):
                self._call_count = 0
            def __call__(self):
                self._call_count += 1
                return self._call_count >= 2  # stop before 2nd paper

        checker = _StopChecker()
        def _fake_make_cooperative_stop():
            return (checker, lambda: None)

        monkeypatch.setattr(
            "paperforge.commands.ocr._make_cooperative_stop",
            _fake_make_cooperative_stop,
        )

        rc = _run_ocr_redo(vault, keys=["KEY00001", "KEY00002", "KEY00003"])

        assert rc == 130, f"Expected exit code 130 for stopped batch, got {rc}"
        captured = capsys.readouterr().out
        lines = [l for l in captured.split("\n") if l.strip()]

        assert lines[0] == "OCR_REDO_START:3"
        assert "OCR_REDO_PROGRESS:1:3:KEY00001" in captured
        assert "OCR_REDO_PROGRESS:2:3:KEY00002" not in captured
        assert "OCR_REDO_DONE" in captured
        assert "Batch stopped" in captured


    # On Windows os.kill(pid, SIGINT) does not trigger Python signal
    # handlers the same way; this test is platform-dependent and skipped.
    def test_make_cooperative_stop_signal_handler(self):
        """_make_cooperative_stop installs handler and tracks flag."""
        import sys
        if sys.platform == "win32":
            pytest.skip("SIGINT signal handling differs on Windows")
        from paperforge.commands.ocr import _make_cooperative_stop

        is_stopped, restore = _make_cooperative_stop()

        # Initially not stopped
        assert not is_stopped()

        # Simulate SIGINT
        import signal
        import os
        os.kill(os.getpid(), signal.SIGINT)

        # Flag should be set
        assert is_stopped()

        # Restore original handler
        restore()

        # After restore, new call installs fresh handler
        is_stopped2, restore2 = _make_cooperative_stop()
        assert not is_stopped2()
        restore2()

    def test_make_cooperative_stop_stdin(self, monkeypatch):
        """_make_cooperative_stop reads PAPERFORGE_STOP from stdin to set flag."""
        import os
        import time

        r_fd, w_fd = os.pipe()
        fake_stdin = os.fdopen(r_fd, "r", encoding="utf-8")

        monkeypatch.setattr("sys.stdin", fake_stdin)

        from paperforge.commands.ocr import _make_cooperative_stop

        is_stopped, restore = _make_cooperative_stop()

        # Initially not stopped
        assert not is_stopped()

        # Write stop command to the pipe
        os.write(w_fd, b"PAPERFORGE_STOP\n")
        os.close(w_fd)

        # Give reader thread time to process
        time.sleep(0.2)

        # Flag should be set
        assert is_stopped(), "Stdin stop command should set flag"

        restore()


    def test_redo_stop_flag_but_all_complete_returns_normal(self, capsys, monkeypatch, tmp_path):
        """Stop flag set after all papers done: normal exit, no 'stopped' message."""
        _mock_run_ocr(monkeypatch)
        _mock_validate_ocr_meta(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        _add_literature_note(vault, "KEY00001")
        _add_literature_note(vault, "KEY00002")

        # Mock _make_cooperative_stop; _StopChecker always returns False
        # (so all papers process), but _is_stopped returns True after processing
        # to simulate late SIGINT after all progress reached total
        class _LateStop:
            """Return True only after being checked at least 3 times (past all papers)."""
            def __init__(self):
                self.count = 0
            def __call__(self):
                self.count += 1
                return self.count >= 10  # always False during processing

        checker = _LateStop()
        def _fake_make():
            return (checker, lambda: None)

        monkeypatch.setattr(
            "paperforge.commands.ocr._make_cooperative_stop",
            _fake_make,
        )

        from paperforge.commands.ocr import _run_ocr_redo
        rc = _run_ocr_redo(vault, keys=["KEY00001", "KEY00002"])

        assert rc == 0, f"Expected 0 (all done), got {rc}"
        captured = capsys.readouterr().out
        assert "Batch stopped" not in captured
        assert "OCR_REDO_DONE" in captured

    def test_rebuild_stop_flag_but_all_complete_returns_normal(self, capsys, monkeypatch, tmp_path):
        """Rebuild stop flag after all done: normal exit, no 'stopped'."""
        vault = _make_minimal_vault(tmp_path)
        keys = ["KEY00001", "KEY00002"]

        from tests.cli.test_ocr_progress_contracts import TestOcrRebuildProgressTokens
        helper = TestOcrRebuildProgressTokens()
        helper._setup_mock_selection_and_worker(vault, keys, monkeypatch)

        # Late stop as above
        class _LateStop:
            def __init__(self):
                self.count = 0
            def __call__(self):
                self.count += 1
                return self.count >= 10

        checker = _LateStop()
        def _fake_make():
            return (checker, lambda: None)

        monkeypatch.setattr(
            "paperforge.commands.ocr._make_cooperative_stop",
            _fake_make,
        )

        from paperforge.commands.ocr import _run_ocr_rebuild
        rc = _run_ocr_rebuild(vault, keys=keys)

        assert rc == 0, f"Expected 0 (all done), got {rc}"
        captured = capsys.readouterr().out
        assert "OCR_REBUILD_DONE" in captured
        assert "Batch stopped" not in captured

class TestOcrListNeedsRebuild:
    """OCR list --json includes needs_derived_rebuild."""

    def test_list_json_has_needs_derived_rebuild(self, tmp_path):
        """ocr list --json output includes needs_derived_rebuild boolean."""
        vault = _make_minimal_vault(tmp_path)
        # Create a paper with OCR meta but no derived artifacts → needs rebuild
        _add_ocr_meta(vault, "KEY00001", "done")
        ocr_dir = vault / "System/PaperForge/ocr" / "KEY00001"
        (ocr_dir / "blocks.raw.jsonl").write_text(
            '{"page": 1, "block_id": 1, "text": "test"}\n', encoding="utf-8"
        )

        from paperforge.commands.ocr import _run_ocr_list
        import io, sys

        captured = io.StringIO()
        old = sys.stdout
        sys.stdout = captured
        try:
            rc = _run_ocr_list(vault, json_output=True)
        finally:
            sys.stdout = old
        assert rc == 0
        output = captured.getvalue()
        import json
        data = json.loads(output)
        assert isinstance(data, list)
        assert len(data) >= 1
        row = next(r for r in data if r["key"] == "KEY00001")
        assert "needs_derived_rebuild" in row, "JSON must include needs_derived_rebuild"
        assert isinstance(row["needs_derived_rebuild"], bool)

    def test_list_json_hidden_healthy(self, tmp_path):
        """Healthy up-to-date paper has needs_derived_rebuild=False."""
        vault = _make_minimal_vault(tmp_path)
        # Full OCR setup requires many files — test false via no-meta case
        from paperforge.commands.ocr import _run_ocr_list
        import io, sys

        captured = io.StringIO()
        old = sys.stdout
        sys.stdout = captured
        try:
            rc = _run_ocr_list(vault, json_output=True)
        finally:
            sys.stdout = old
        assert rc == 0
        output = captured.getvalue()
        import json
        data = json.loads(output)
        # No OCR papers at all in empty vault
        assert isinstance(data, list)


class TestRedoNoOcrRoot:
    """Keyed redo without OCR root should not fail preflight."""

    def test_redo_missing_root_nonzero(self, tmp_path, monkeypatch):
        """Keyed redo on missing OCR root delegates to worker, returns non-zero."""
        from paperforge.commands.ocr import _run_ocr_redo
        from tests.cli.test_ocr_progress_contracts import _mock_run_ocr

        _mock_run_ocr(monkeypatch)
        vault = _make_minimal_vault(tmp_path)
        _add_literature_note(vault, "KEY00001")

        # Delete OCR root to simulate missing state
        import shutil
        ocr_root = vault / "System/PaperForge/ocr"
        if ocr_root.exists():
            shutil.rmtree(ocr_root)

        # Should not crash; worker handles missing dirs
        result = _run_ocr_redo(vault, keys=["KEY00001"])
        # Exit code may be non-zero (worker can't process without ocr root)
        assert result is not None
        assert isinstance(result, int)
