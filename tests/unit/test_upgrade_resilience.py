"""Unit tests for backend upgrade resilience & hotfix-safety fixes."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from paperforge import runtime_installer
from paperforge.config import paperforge_paths, set_config
from paperforge.memory.builder import build_for_keys
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import drop_all_tables
from paperforge.services.memory_card_service import get_memory_history, refine_memory_facet
from paperforge.services.storage_migration import migrate_vault_storage
from paperforge.worker.asset_index import atomic_write_index
from paperforge.worker.repair import repair_pdf_paths
from tests.conftest import canonical_test_config


def test_runtime_installer_normalizes_semver_and_pep440(tmp_path: Path, monkeypatch) -> None:
    pip_specs: list[str] = []

    def fake_run(command: list[str], *, cwd: Path | None = None, timeout: int = 300):
        del cwd, timeout
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "Python 3.12.4\n", "")
        if command[1:3] == ["-m", "venv"]:
            venv_dir = Path(command[-1])
            py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            py.parent.mkdir(parents=True, exist_ok=True)
            py.write_bytes(b"python")
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected command: {command!r}")

    monkeypatch.setattr(runtime_installer, "_run", fake_run)
    monkeypatch.setattr(
        runtime_installer,
        "_pip_install",
        lambda python, spec, *, cwd: pip_specs.append(spec)
        or subprocess.CompletedProcess([str(python)], 0, "", ""),
    )
    monkeypatch.setattr(
        runtime_installer,
        "_fresh_verify",
        lambda python, *, cwd=None: (True, "2.0.0rc6", None),
    )
    monkeypatch.setattr(runtime_installer, "_vector_imports_ok", lambda python, *, cwd=None: True)

    res = runtime_installer.install_runtime(
        expected_version="2.0.0-rc.6",
        home=tmp_path,
        base_python="python-test",
    )
    assert res.ok is True
    assert pip_specs == ["paperforge[vector]==2.0.0rc6"]

    status = runtime_installer.inspect_runtime(
        home=tmp_path,
        expected_version="2.0.0-rc.6",
        base_python="python-test",
    )
    assert status["version_matches_expected"] is True
    assert status["runtime_ready"] is True


def test_repair_pdf_paths_uses_configured_external_zotero_dir(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")

    ext_zotero = (tmp_path / "external_zotero").resolve()
    pdf_file = ext_zotero / "storage" / "EXT01" / "trial.pdf"
    pdf_file.parent.mkdir(parents=True)
    pdf_file.write_bytes(b"%PDF-1.4\n")
    set_config(vault, "zotero_data_dir", str(ext_zotero))

    paths = paperforge_paths(vault)
    assert paths["zotero_dir"] == ext_zotero
    (paths["exports"]).mkdir(parents=True, exist_ok=True)
    (paths["exports"] / "Ortho.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "itemType": "journalArticle",
                        "key": "ZOTEXT01",
                        "title": "External Zotero Trial",
                        "attachments": [
                            {"contentType": "application/pdf", "path": "storage:EXT01/trial.pdf"}
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    note_dir = vault / "Resources" / "Literature" / "Ortho"
    note_dir.mkdir(parents=True)
    note = note_dir / "ZOTEXT01.md"
    initial_text = (
        '---\nzotero_key: "ZOTEXT01"\npdf_path: ""\npath_error: "not_found"\n'
        'bbt_path_raw: ""\nzotero_storage_key: ""\n---\n\n# External Zotero Trial\n'
    )
    note.write_text(initial_text, encoding="utf-8")

    fixed = repair_pdf_paths(
        vault,
        paths,
        [
            {
                "path": note,
                "zotero_key": "ZOTEXT01",
                "domain": "Ortho",
                "path_error": "not_found",
                "text": initial_text,
            }
        ],
    )
    assert fixed == 1
    repaired = note.read_text(encoding="utf-8")
    assert 'path_error: ""' in repaired
    assert "storage:EXT01/trial.pdf" in repaired


def test_migrate_vault_storage_rewrites_title_named_formal_note(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")
    old_ocr = vault / "System" / "PaperForge" / "ocr" / "KEY999"
    (old_ocr / "assets" / "figures").mkdir(parents=True)
    (old_ocr / "assets" / "figures" / "figure_001.jpg").write_bytes(b"fig1")

    ws_name = "KEY999 - Sample Title"
    ws = vault / "Resources" / "Literature" / "Ortho" / ws_name
    ws.mkdir(parents=True)
    titled_note = ws / f"{ws_name}.md"
    titled_note.write_text(
        "---\nzotero_key: KEY999\n---\n\n![[render/figures/figure_001.md|Figure 1]]\n",
        encoding="utf-8",
    )

    report = migrate_vault_storage(vault, dry_run=False)
    assert report["notes_rewritten"] == 1
    assert "![[KEY999_figure_001.jpg|Figure 1]]" in titled_note.read_text(encoding="utf-8")


def test_memory_card_history_survives_db_drop_and_rebuild(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    pf = vault / ".paperforge"
    ws = vault / "Resources" / "Literature" / "Ortho" / "HIST01 - Study"
    ws.mkdir(parents=True)
    (ws / "HIST01.md").write_text('---\nzotero_key: "HIST01"\n---\n', encoding="utf-8")
    atomic_write_index(
        pf / "indexes" / "formal-library.json",
        {
            "version": 1,
            "items": [
                {
                    "zotero_key": "HIST01",
                    "title": "History Preservation Trial",
                    "domain": "Ortho",
                    "paper_root": "Resources/Literature/Ortho/HIST01 - Study/",
                    "main_note_path": "Resources/Literature/Ortho/HIST01 - Study/HIST01.md",
                    "note_path": "Resources/Literature/Ortho/HIST01 - Study/HIST01.md",
                }
            ],
        },
    )
    build_for_keys(vault)

    refine_memory_facet(vault, "HIST01", facet="idea_logic", content="First hypothesis draft")
    refine_memory_facet(vault, "HIST01", facet="idea_logic", content="Refined mechanistic insight")

    sidecar = json.loads((ws / "ai" / "memory-card.json").read_text(encoding="utf-8"))
    assert len(sidecar["history"]) == 2

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path)
    try:
        drop_all_tables(conn)
    finally:
        conn.close()
    db_path.unlink()

    # Sidecar fallback works even before DB rebuild completes
    fallback_hist = get_memory_history(vault, "HIST01", facet="idea_logic")["history"]
    assert [h["revision"] for h in fallback_hist] == [2, 1]

    # Full rebuild restores SQLite paper_memory_history losslessly
    build_for_keys(vault)
    rebuilt_hist = get_memory_history(vault, "HIST01", facet="idea_logic")["history"]
    assert [h["revision"] for h in rebuilt_hist] == [2, 1]
    assert rebuilt_hist[0]["content"] == "Refined mechanistic insight"
    assert rebuilt_hist[1]["content"] == "First hypothesis draft"
