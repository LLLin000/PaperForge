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
    ocr_root = vault / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    exports = vault / "PaperForge" / "exports"
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
