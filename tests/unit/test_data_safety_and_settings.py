"""Unit tests for Commit 1C: UI config routing, OCR selection guard, and user data safety."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from paperforge.adapters.bbt import load_export_rows
from paperforge.commands.prune import run as prune_run
from paperforge.commands.reading_log import _render_reading_log_md
from paperforge.ocr_diagnostics import ocr_doctor
from paperforge.services.sync_service import SyncService
from paperforge.worker.asset_index import build_index
from paperforge.worker.ocr import run_ocr
from paperforge.worker.sync import frontmatter_note
from tests.conftest import canonical_test_config


def test_ocr_doctor_uses_vault_config_endpoint_and_actionable_fixes(
    tmp_path: Path, monkeypatch
) -> None:
    captured: list[tuple[str, dict]] = []

    def fake_post(url: str, headers=None, json=None, data=None, files=None, timeout=30):
        captured.append((url, json or {}))
        return SimpleNamespace(status_code=401, json=lambda: {})

    monkeypatch.setattr("paperforge.credentials.resolve", lambda _key: "tok-123")
    monkeypatch.setattr("paperforge.ocr_diagnostics.requests.post", fake_post)

    res = ocr_doctor(
        config={
            "paddleocr_job_url": "https://custom.ocr.example/v2/jobs",
            "paddleocr_model": "PaddleOCR-Custom-X",
        },
        live=False,
    )
    assert res["passed"] is False
    assert captured[0][0] == "https://custom.ocr.example/v2/jobs"
    assert captured[0][1]["model"] == "PaddleOCR-Custom-X"
    assert "PaperForge Settings" in res["fix"]
    assert ".env" not in res["fix"]


def test_run_ocr_blocks_silent_all_library_when_none_checked(
    tmp_path: Path, monkeypatch
) -> None:
    canonical_test_config(tmp_path)
    lit = tmp_path / "Resources" / "Literature" / "Ortho"
    ws = lit / "K001 - Sample"
    ws.mkdir(parents=True)
    note = lit / "K001.md"
    note.write_text("---\ntitle: Sample\ndo_ocr: false\n---\n", encoding="utf-8")

    idx_path = tmp_path / "System" / "PaperForge" / "indexes" / "library_assets.json"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [
                    {
                        "zotero_key": "K001",
                        "domain": "Ortho",
                        "note_path": "Resources/Literature/Ortho/K001.md",
                        "workspace_dir": "Resources/Literature/Ortho/K001 - Sample",
                        "has_pdf": True,
                        "pdf_path": "dummy.pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("OCR worker should not upload when allow_unselected_all=False and 0 checked")

    monkeypatch.setattr("paperforge.worker.ocr.cleanup_blocked_ocr_dirs", fail_if_called)
    rc = run_ocr(tmp_path, selected_keys=None, allow_unselected_all=False)
    assert rc == 0
    assert called is False


def test_sync_preserves_custom_frontmatter_and_abstract_hr_and_migrates_renamed_domain(
    tmp_path: Path,
) -> None:
    canonical_test_config(tmp_path)
    zotero_dir = tmp_path / "System" / "Zotero"
    storage = zotero_dir / "storage" / "AT01"
    storage.mkdir(parents=True)
    (storage / "paper.pdf").write_bytes(b"%PDF-1.4 dummy")

    exports = tmp_path / "System" / "PaperForge" / "exports"
    exports.mkdir(parents=True)
    bbt_payload = {
        "items": [
            {
                "key": "ZKEY1",
                "citationKey": "smith2024",
                "title": "Knee Biomechanics Overview",
                "date": "2024",
                "publicationTitle": "J Biomech",
                "creators": [{"creatorType": "author", "lastName": "Smith"}],
                "abstractNote": "Background sentence.\n\n---\n\nSecond paragraph.",
                "attachments": [{"path": "storage:AT01/paper.pdf", "title": "Full Text"}],
            }
        ]
    }
    (exports / "Ortho.json").write_text(json.dumps(bbt_payload), encoding="utf-8")

    # Initial sync in Ortho
    entry_rows = load_export_rows(exports / "Ortho.json")
    assert len(entry_rows) == 1
    assert build_index(tmp_path) == 1

    old_ws = next((tmp_path / "Resources" / "Literature" / "Ortho").glob("ZKEY1 - *"))
    (old_ws / "ai").mkdir(parents=True, exist_ok=True)
    (old_ws / "ai" / "discussion.md").write_text("My discussion notes", encoding="utf-8")
    old_note = tmp_path / "Resources" / "Literature" / "Ortho" / "ZKEY1.md"
    initial_note = frontmatter_note(
        {
            "key": "ZKEY1",
            "title": "Knee Biomechanics Overview",
            "year": "2024",
            "journal": "J Biomech",
            "first_author": "Smith",
            "domain": "Ortho",
            "has_pdf": True,
        }
    )
    # Simulate user adding custom frontmatter keys + deep reading section
    custom_note = initial_note.replace(
        "do_ocr: false\n",
        "do_ocr: false\nrating: 5\nmy_project: KneeOA\n",
    ) + "\n## 🔍 精读\n\n- **Clarity**（清晰度）：Clear\n"
    old_note.write_text(custom_note, encoding="utf-8")

    # Second pass inside same domain: custom props and body stay intact even with --- inside abstract
    assert build_index(tmp_path) == 1
    note_text = old_note.read_text(encoding="utf-8")
    assert "rating: 5" in note_text
    assert "my_project: KneeOA" in note_text
    assert "## 🔍 精读" in note_text

    # Rename Ortho.json -> Orthopedics.json and add duplicate key in another file
    (exports / "Ortho.json").unlink()
    (exports / "Orthopedics.json").write_text(json.dumps(bbt_payload), encoding="utf-8")
    (exports / "Z_Duplicate.json").write_text(json.dumps(bbt_payload), encoding="utf-8")

    # Need migrated note in new domain OR workspace folder moved cleanly without duplicate entries
    total = build_index(tmp_path)
    assert total == 1  # deduplicated across exports

    migrated_ws_list = list((tmp_path / "Resources" / "Literature" / "Orthopedics").glob("ZKEY1 - *"))
    assert len(migrated_ws_list) == 1
    assert (migrated_ws_list[0] / "ai" / "discussion.md").read_text(encoding="utf-8") == "My discussion notes"
    assert not old_ws.exists()


def test_reading_log_render_project_uses_index_md_preserving_narrative(tmp_path: Path) -> None:
    canonical_test_config(tmp_path)
    proj_dir = tmp_path / "Resources" / "Projects" / "ProjA"
    proj_dir.mkdir(parents=True)
    narrative = proj_dir / "reading-log.md"
    narrative.write_text("# Narrative Review\n\nHand-written synthesis.", encoding="utf-8")

    log_jsonl = tmp_path / "System" / "PaperForge" / "logs" / "reading-log.jsonl"
    log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    log_jsonl.write_text(
        json.dumps(
            {
                "id": "rl_1",
                "paper_id": "K001",
                "section": "Methods",
                "excerpt": "Sample excerpt",
                "usage": "method",
                "project": "ProjA",
                "created_at": "2026-11-18T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    _render_reading_log_md(tmp_path, project="ProjA")
    assert narrative.read_text(encoding="utf-8") == "# Narrative Review\n\nHand-written synthesis."
    assert (proj_dir / "reading-log.index.md").exists()


def test_prune_and_orphan_records_do_not_collide_or_fail_on_empty_path(
    tmp_path: Path, monkeypatch
) -> None:
    canonical_test_config(tmp_path)
    lit_ws = tmp_path / "Resources" / "Literature" / "Ortho" / "ORPH1 - Orphan Study"
    lit_ws.mkdir(parents=True)
    (lit_ws / "ORPH1.md").write_text("---\ntitle: Orphan Study\n---\n", encoding="utf-8")
    ocr_dir = tmp_path / "System" / "PaperForge" / "ocr" / "ORPH1"
    ocr_dir.mkdir(parents=True)
    (ocr_dir / "meta.json").write_text('{"zotero_key": "ORPH1"}', encoding="utf-8")

    monkeypatch.setattr(
        "paperforge.lineage._detect_residuals",
        lambda vault, scope="all": {"keys": ["ORPH1"], "count": 1},
    )
    answers = iter(["d", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    rc = prune_run(argparse.Namespace(vault_path=tmp_path, dry_run=False, force=True, json=False, keys=None))
    assert rc == 0
    assert not lit_ws.exists()
    assert not ocr_dir.exists()

    # SyncService.clean_orphaned_records must not collide on 20-char prefixes and must use trash
    from paperforge.config import paperforge_paths
    from paperforge.worker.trash import trash_root

    paths = paperforge_paths(tmp_path)
    ortho_dir = paths["literature"] / "Ortho"
    ortho_dir.mkdir(parents=True, exist_ok=True)
    f1 = ortho_dir / "K1.md"
    f2 = ortho_dir / "K2.md"
    f3 = ortho_dir / "K3.md"
    f1.write_text('---\nzotero_key: K1\ntitle: "Study on Knee Joint Alpha"\nhas_pdf: false\n---\n', encoding="utf-8")
    f2.write_text('---\nzotero_key: K2\ntitle: "Study on Knee Joint Beta"\nhas_pdf: true\n---\n', encoding="utf-8")
    f3.write_text('---\nzotero_key: K3\ntitle: "Study on Knee Joint Beta"\nhas_pdf: false\n---\n', encoding="utf-8")
    svc = SyncService(tmp_path)
    deleted = svc.clean_orphaned_records({"Ortho": {"K2": {}}}, paths, json_output=True)
    assert deleted == 1
    assert f1.exists() and f2.exists()
    assert not f3.exists()
    assert list(trash_root(tmp_path).rglob("K3.md"))
