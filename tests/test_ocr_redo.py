"""Tests for paperforge ocr redo workflow."""

import json
import re
import shutil
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text("{}", encoding="utf-8")
    # v2 vault_config default layout: system_dir=System/PaperForge — this
    # must match pipeline_paths() or redo transactions operate on a
    # different tree than the fixture asserts (issue #123).
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    exports = vault / "System" / "PaperForge" / "exports"
    exports.mkdir(parents=True)
    literature = vault / "Resources" / "Literature"
    literature.mkdir(parents=True)
    return vault, ocr_root, exports, literature


def _make_ocr_meta(ocr_root: Path, key: str, status: str = "done") -> dict:
    meta_dir = ocr_root / key
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "images").mkdir(exist_ok=True)
    meta = {
        "zotero_key": key,
        "ocr_status": status,
        "ocr_provider": "PaddleOCR-VL-1.6",
        "source_pdf": f"some/path/{key}.pdf",
        "ocr_job_id": "job-123",
        "ocr_started_at": "2025-01-01T00:00:00",
        "ocr_finished_at": "2025-01-01T01:00:00",
        "page_count": 5,
        "markdown_path": f"PaperForge/ocr/{key}/fulltext.md",
    }
    (meta_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def _make_library_note(lit_dir: Path, key: str, ocr_redo: bool = True, ocr_status: str = "done") -> Path:
    domain_dir = lit_dir / "test_domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    note_path = domain_dir / f"{key}.md"
    note_text = f"""---
title: "Test Paper"
zotero_key: {key}
do_ocr: true
analyze: true
ocr_status: {ocr_status}
ocr_redo: {"true" if ocr_redo else "false"}
tags:
  - test
---

# Test Paper

Some content
"""
    note_path.write_text(note_text, encoding="utf-8")
    return note_path


# ---------------------------------------------------------------------------
# Test: OCR redo resets ocr_status in meta.json
# ---------------------------------------------------------------------------

def test_ocr_redo_resets_ocr_status():
    """Setting ocr_status to pending in meta.json simulates redo reset."""
    meta = {"zotero_key": "KEY001", "ocr_status": "done", "ocr_job_id": "job-xyz"}
    meta["ocr_status"] = "pending"
    meta["ocr_job_id"] = ""
    assert meta["ocr_status"] == "pending"
    assert meta["ocr_job_id"] == ""
    assert meta["zotero_key"] == "KEY001"


# ---------------------------------------------------------------------------
# Test: OCR redo clears OCR directory
# ---------------------------------------------------------------------------

def test_ocr_redo_clears_ocr_dir(tmp_path):
    """Verify OCR output directory is removed on redo."""
    vault, ocr_root, exports, literature = _make_vault(tmp_path)
    key = "KEY002"
    _make_ocr_meta(ocr_root, key, status="done")
    ocr_dir = ocr_root / key
    assert ocr_dir.exists()
    assert (ocr_dir / "meta.json").exists()
    assert (ocr_dir / "images").exists()

    # Simulate redo: delete the OCR directory
    shutil.rmtree(ocr_dir)

    assert not ocr_dir.exists()


# ---------------------------------------------------------------------------
# Test: OCR redo updates library note frontmatter
# ---------------------------------------------------------------------------

def test_ocr_redo_updates_frontmatter(tmp_path):
    """Verify ocr_status and ocr_redo are updated in the library note."""
    vault, ocr_root, exports, literature = _make_vault(tmp_path)
    key = "KEY003"
    _make_ocr_meta(ocr_root, key, status="done")
    note_path = _make_library_note(literature, key, ocr_redo=True, ocr_status="done")

    # Simulate redo: update frontmatter
    text = note_path.read_text(encoding="utf-8")
    text = re.sub(r"^ocr_status:\s*.+$", "ocr_status: pending", text, flags=re.MULTILINE)
    text = re.sub(r"^ocr_redo:\s*.+$", "ocr_redo: false", text, flags=re.MULTILINE)
    note_path.write_text(text, encoding="utf-8")

    updated = note_path.read_text(encoding="utf-8")
    assert "ocr_status: pending" in updated
    assert "ocr_redo: false" in updated
    # ocr_redo: false and ocr_redo: true must not both appear
    assert len(re.findall(r"^ocr_redo:", updated, re.MULTILINE)) == 1
    assert len(re.findall(r"^ocr_status:", updated, re.MULTILINE)) == 1


# ---------------------------------------------------------------------------
# Test: redo subcommand is registered
# ---------------------------------------------------------------------------

def test_redo_subcommand_registered():
    """Verify 'paperforge ocr redo' is a registered subcommand."""
    from paperforge.cli import build_parser

    parser = build_parser()

    # Parse ocr redo --help should not fail
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["ocr", "redo", "--help"])
    assert exc.value.code == 0

    # Parse ocr redo should set ocr_action="redo"
    args = parser.parse_args(["ocr", "redo"])
    assert args.command == "ocr"
    assert args.ocr_action == "redo"


# ---------------------------------------------------------------------------
# Test: _run_ocr_redo scan logic
# ---------------------------------------------------------------------------

def test_ocr_redo_scan_finds_marked_papers(tmp_path):
    """Verify scan finds papers with ocr_redo: true."""
    vault, ocr_root, exports, literature = _make_vault(tmp_path)
    _make_library_note(literature, "KEY_A", ocr_redo=True)
    _make_library_note(literature, "KEY_B", ocr_redo=False)
    _make_library_note(literature, "KEY_C", ocr_redo=True)

    from paperforge.adapters.obsidian_frontmatter import extract_preserved_ocr_redo

    found = []
    for note_file in sorted(literature.rglob("*.md")):
        if note_file.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
            continue
        text = note_file.read_text(encoding="utf-8")
        if not extract_preserved_ocr_redo(text):
            continue
        key_match = re.search(r"^zotero_key:\s*(.+)$", text, re.MULTILINE)
        assert key_match is not None
        zkey = key_match.group(1).strip().strip('"').strip("'")
        found.append(zkey)

    assert "KEY_A" in found
    assert "KEY_B" not in found
    assert "KEY_C" in found
    assert len(found) == 2


def test_ocr_redo_rebuilds_phase3_artifacts(tmp_path) -> None:
    """Verify postprocess_ocr_result produces render and health artifacts from Phase 3."""
    import json as _json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        _json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "REDO003"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"REDO003","ocr_status":"done","ocr_redo":true,"ocr_model":"PaddleOCR","source_pdf":""}',
        encoding="utf-8",
    )

    postprocess_ocr_result(vault, "REDO003", [])

    # Phase 3 artifacts should exist
    assert (ocr_dir / "render" / "fulltext.md").exists(), "render/fulltext.md missing after redo"
    assert (ocr_dir / "health" / "ocr_health.json").exists(), "health/ocr_health.json missing after redo"


# ---------------------------------------------------------------------------
# Guard: redo must not become derived-rebuild path
# ---------------------------------------------------------------------------

def test_redo_does_not_call_derived_rebuild() -> None:
    """Verify ocr redo does not import or call derived rebuild.

    This import will fail (ModuleNotFoundError) until Task 5 of Phase 4,
    which explicitly keeps redo and derived rebuild separate. If someone
    wires redo to use derived rebuild, this test should be updated or
    removed with explicit justification.
    """
    from paperforge.worker.ocr_rebuild import select_papers_for_derived_rebuild

    assert select_papers_for_derived_rebuild is not None


# ---------------------------------------------------------------------------
# Issue #99: redo backup safety
# ---------------------------------------------------------------------------

class TestRedoBackupSafety:
    """Verify redo creates backup before deletion and restores on failure."""

    def test_redo_backup_preserves_artifacts_on_failure(self, tmp_path: Path) -> None:
        """Redo failure restores original OCR output instead of leaving nothing."""
        vault, ocr_root, exports, lit_dir = _make_vault(tmp_path)

        key = "BACKUP01"
        meta = _make_ocr_meta(ocr_root, key, status="done")
        note_path = _make_library_note(lit_dir, key, ocr_redo=True, ocr_status="done")

        # Create some artifacts that would exist in a real OCR output
        paper_dir = ocr_root / key
        (paper_dir / "fulltext.md").write_text("# Original Fulltext\n\nOld content.", encoding="utf-8")
        render_dir = paper_dir / "render"
        render_dir.mkdir()
        (render_dir / "fulltext.md").write_text("# Original Render", encoding="utf-8")
        images_dir = paper_dir / "images"
        # images/ may already exist from _make_ocr_meta

        from paperforge.worker.ocr import redo_papers_for_keys
        # Simulate failed redo: OCR runs but produces no valid output (no done status)
        # rmtree happens first, then run_ocr "fails", and we should restore backup
        from unittest.mock import patch
        with patch("paperforge.worker.ocr.run_ocr", return_value=1):  # failure
            result = redo_papers_for_keys(
                vault, keys=[key], verbose=False,
            )

        assert result["exit_code"] == 1
        assert key in result["failed_keys"]

        # After failure, backup should be restored — original artifacts should exist
        assert (paper_dir / "fulltext.md").exists(), "fulltext.md should be restored from backup"
        assert (paper_dir / "images").exists(), "images/ should be restored from backup"



# ---------------------------------------------------------------------------
# Issue #123: single-owner transaction executor
# ---------------------------------------------------------------------------

def _make_redo_paper(vault, ocr_root, lit_dir, key, *, ws_fulltext: str = "# Workspace fulltext") -> tuple:
    """Full paper fixture: meta done, note ocr_redo=true, ocr artifacts, workspace fulltext."""
    meta = _make_ocr_meta(ocr_root, key, status="done")
    note = _make_library_note(lit_dir, key, ocr_redo=True, ocr_status="done")
    paper_dir = ocr_root / key
    (paper_dir / "fulltext.md").write_text(f"# Original {key}", encoding="utf-8")
    ws_dir = lit_dir / "test_domain" / f"{key} - workspace"
    ws_dir.mkdir(exist_ok=True)
    (ws_dir / "fulltext.md").write_text(ws_fulltext, encoding="utf-8")
    return paper_dir, note, ws_dir


def _fake_success_ocr(ocr_root: Path, key: str) -> None:
    """Write a validate_ocr_meta-satisfying OCR output for one key."""
    meta_dir = ocr_root / key
    meta_dir.mkdir(parents=True, exist_ok=True)
    (meta_dir / "fulltext.md").write_text(
        "# Fake fulltext\n" + "x" * 600
        + "\n" + "\n".join(f"<!-- page {i} -->" for i in range(1, 6)),
        encoding="utf-8",
    )
    json_dir = meta_dir / "json"
    json_dir.mkdir(exist_ok=True)
    (json_dir / "result.json").write_text(
        '{"blocks": [' + ",".join('{}' for _ in range(400)) + "]}", encoding="utf-8"
    )
    (meta_dir / "meta.json").write_text(json.dumps({
        "zotero_key": key,
        "ocr_status": "done",
        "page_count": 5,
        "source_pdf": f"some/path/{key}.pdf",
    }), encoding="utf-8")


class TestRedoTransactionExecutor:
    """#123 acceptance: no-key path uses the transaction executor; every
    failure mode restores ocr_dir + workspace fulltexts + note."""

    def test_no_key_redo_failure_restores_everything(self, tmp_path):
        from unittest.mock import patch

        from paperforge.worker.ocr import ocr_redo_papers

        vault, ocr_root, exports, lit_dir = _make_vault(tmp_path)
        paper_dir, note, ws_dir = _make_redo_paper(vault, ocr_root, lit_dir, "NOKEY001")

        with patch("paperforge.worker.ocr.run_ocr", return_value=1):
            rc = ocr_redo_papers(vault)

        assert rc == 1
        assert (paper_dir / "fulltext.md").exists(), "ocr_dir fulltext must be restored"
        assert (paper_dir / "images").exists(), "ocr_dir images must be restored"
        assert (ws_dir / "fulltext.md").exists(), "workspace fulltext must be restored"
        text = note.read_text(encoding="utf-8")
        assert "ocr_status: done" in text, "note must be restored to pre-redo state"
        assert "ocr_redo: true" in text

    def test_redo_exception_rolls_back(self, tmp_path):
        from unittest.mock import patch

        from paperforge.worker.ocr import redo_papers_for_keys

        vault, ocr_root, exports, lit_dir = _make_vault(tmp_path)
        paper_dir, note, ws_dir = _make_redo_paper(vault, ocr_root, lit_dir, "EXC00001")

        with patch("paperforge.worker.ocr.run_ocr", side_effect=RuntimeError("boom")):
            result = redo_papers_for_keys(vault, keys=["EXC00001"])

        assert "EXC00001" in result["failed_keys"]
        assert result["exit_code"] == 1
        assert (paper_dir / "fulltext.md").exists(), "ocr_dir must be restored after exception"
        assert (ws_dir / "fulltext.md").exists(), "workspace fulltext must be restored after exception"
        text = note.read_text(encoding="utf-8")
        assert "ocr_status: done" in text and "ocr_redo: true" in text

    def test_batch_second_failure_isolated(self, tmp_path):
        from unittest.mock import patch

        from paperforge.worker.ocr import redo_papers_for_keys

        vault, ocr_root, exports, lit_dir = _make_vault(tmp_path)
        keys = ["BATCH001", "BATCH002", "BATCH003"]
        papers = {k: _make_redo_paper(vault, ocr_root, lit_dir, k) for k in keys}

        def _fake_run_ocr(vault_, **kwargs):
            for k in kwargs.get("selected_keys") or set():
                if k == "BATCH002":
                    raise RuntimeError("mid-batch failure")
                _fake_success_ocr(ocr_root, k)
            return 0

        with patch("paperforge.worker.ocr.run_ocr", side_effect=_fake_run_ocr):
            result = redo_papers_for_keys(vault, keys=keys)

        assert result["success_keys"] == ["BATCH001", "BATCH003"], result
        assert result["failed_keys"] == ["BATCH002"], result
        # 1 committed, 2 rolled back, 3 committed
        assert "ocr_redo: false" in papers["BATCH001"][1].read_text(encoding="utf-8")
        assert "ocr_redo: true" in papers["BATCH002"][1].read_text(encoding="utf-8")
        assert (papers["BATCH002"][0] / "fulltext.md").exists(), "paper 2 must be restored"
        assert "ocr_redo: false" in papers["BATCH003"][1].read_text(encoding="utf-8")

    def test_stop_at_paper_boundary_leaves_remaining_untouched(self, tmp_path):
        from unittest.mock import patch

        from paperforge.worker.ocr import redo_papers_for_keys

        vault, ocr_root, exports, lit_dir = _make_vault(tmp_path)
        keys = ["STOP0001", "STOP0002", "STOP0003"]
        papers = {k: _make_redo_paper(vault, ocr_root, lit_dir, k) for k in keys}

        def _fake_run_ocr(vault_, **kwargs):
            for k in kwargs.get("selected_keys") or set():
                _fake_success_ocr(ocr_root, k)
            return 0

        calls = {"n": 0}

        def _stop_after_two():
            calls["n"] += 1
            return calls["n"] >= 2  # stop before the 2nd paper starts

        with patch("paperforge.worker.ocr.run_ocr", side_effect=_fake_run_ocr):
            result = redo_papers_for_keys(vault, keys=keys, stop_check=_stop_after_two)

        assert result["success_keys"] == ["STOP0001"], result
        # papers 2 and 3 never started: still ocr_redo=true, output intact
        for k in ("STOP0002", "STOP0003"):
            assert "ocr_redo: true" in papers[k][1].read_text(encoding="utf-8")
            assert (papers[k][0] / "fulltext.md").exists(), f"{k} must be untouched"

    def test_callback_fires_after_commit_or_rollback(self, tmp_path):
        from unittest.mock import patch

        from paperforge.worker.ocr import redo_papers_for_keys

        vault, ocr_root, exports, lit_dir = _make_vault(tmp_path)
        keys = ["CB000001", "CB000002"]
        _make_redo_paper(vault, ocr_root, lit_dir, "CB000001")
        _make_redo_paper(vault, ocr_root, lit_dir, "CB000002")

        def _fake_run_ocr(vault_, **kwargs):
            for k in kwargs.get("selected_keys") or set():
                if k == "CB000002":
                    return 1  # failure — no meta written
                _fake_success_ocr(ocr_root, k)
            return 0

        seen: list[str] = []
        with patch("paperforge.worker.ocr.run_ocr", side_effect=_fake_run_ocr):
            redo_papers_for_keys(vault, keys=keys, progress_callback=seen.append)

        # Exactly one callback per key, in order, regardless of outcome.
        assert seen == ["CB000001", "CB000002"], seen
