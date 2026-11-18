"""Unit tests for Commit 2A: .paperforge layout, per-paper visual assets, O(1) sync, and storage migration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from paperforge.commands.migrate_storage import run as migrate_storage_run
from paperforge.config import load_config, resolve_paths
from paperforge.services.storage_migration import migrate_vault_storage
from paperforge.services.sync_service import SyncService
from paperforge.worker.asset_index import build_index, sync_workspace_visual_assets
from paperforge.worker.ocr_versions import backup_render_before_rebuild
from tests.conftest import canonical_test_config


def test_resolve_paths_collapses_dot_paperforge_leaf(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    paths = resolve_paths(tmp_path)
    assert paths["system"] == (tmp_path / ".paperforge").resolve()
    assert paths["paperforge"] == (tmp_path / ".paperforge").resolve()
    assert paths["ocr"] == (tmp_path / ".paperforge" / "ocr").resolve()


def test_fresh_cli_setup_defaults_to_dot_paperforge(tmp_path: Path) -> None:
    from paperforge.cli import main

    rc = main(["--vault", str(tmp_path), "setup", "--headless", "--skip-checks"])
    assert isinstance(rc, int)
    snap = load_config(tmp_path)
    assert snap.values["system_dir"].value == ".paperforge"


def test_dot_paperforge_materializes_prefixed_assets_and_hides_workspace_fulltext(
    tmp_path: Path,
) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "exports").mkdir(parents=True)
    (pf_dir / "Zotero" / "storage" / "AT01").mkdir(parents=True)
    (pf_dir / "Zotero" / "storage" / "AT01" / "paper.pdf").write_bytes(b"%PDF-1.4")

    ocr_paper = pf_dir / "ocr" / "K100"
    (ocr_paper / "assets" / "figures").mkdir(parents=True)
    (ocr_paper / "assets" / "tables").mkdir(parents=True)
    (ocr_paper / "json").mkdir(parents=True)
    (ocr_paper / "json" / "result.json").write_text('{"pages": []}', encoding="utf-8")
    (ocr_paper / "assets" / "figures" / "figure_001.jpg").write_bytes(b"fig1")
    (ocr_paper / "assets" / "tables" / "table_001.jpg").write_bytes(b"tbl1")
    (ocr_paper / "fulltext.md").write_text("# Internal OCR fulltext\n", encoding="utf-8")
    (ocr_paper / "meta.json").write_text(
        json.dumps(
            {
                "zotero_key": "K100",
                "ocr_status": "done",
                "page_count": 3,
                "markdown_path": ".paperforge/ocr/K100/fulltext.md",
                "json_path": ".paperforge/ocr/K100/json/result.json",
            }
        ),
        encoding="utf-8",
    )

    (pf_dir / "exports" / "Ortho.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "key": "K100",
                        "citationKey": "lin2026",
                        "title": "Cartilage Regeneration Study",
                        "date": "2026",
                        "publicationTitle": "Nat Med",
                        "creators": [{"creatorType": "author", "lastName": "Lin"}],
                        "attachments": [{"path": "storage:AT01/paper.pdf"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert build_index(tmp_path) == 1
    ws = next((tmp_path / "Resources" / "Literature" / "Ortho").glob("K100 - *"))
    assert (ws / "assets" / "K100_figure_001.jpg").read_bytes() == b"fig1"
    assert (ws / "assets" / "K100_table_001.jpg").read_bytes() == b"tbl1"
    assert not (ws / "fulltext.md").exists()

    note_text = (ws / "K100.md").read_text(encoding="utf-8")
    assert 'fulltext_md_path: ""' in note_text

    # Re-create stale workspace fulltext; fastpath _sync_workspace_fulltexts cleans it up
    (ws / "fulltext.md").write_text("stale", encoding="utf-8")
    assert build_index(tmp_path) == 1
    assert not (ws / "fulltext.md").exists()


def test_sync_service_fastpath_short_circuits_and_invalidates_on_meta_change(
    tmp_path: Path, monkeypatch
) -> None:
    canonical_test_config(tmp_path, system_dir=".paperforge")
    pf_dir = tmp_path / ".paperforge"
    (pf_dir / "exports").mkdir(parents=True)
    (pf_dir / "ocr" / "K200").mkdir(parents=True)
    (pf_dir / "exports" / "Ortho.json").write_text(json.dumps({"items": []}), encoding="utf-8")
    meta_file = pf_dir / "ocr" / "K200" / "meta.json"
    meta_file.write_text('{"zotero_key": "K200", "ocr_status": "pending"}', encoding="utf-8")

    svc = SyncService(tmp_path)
    first = svc.run(json_output=True)
    assert first.ok is True
    assert (pf_dir / "indexes" / ".sync-fastpath.json").exists()

    # Second call must short-circuit without calling run_selection_sync or build_index
    with patch("paperforge.worker.sync.run_selection_sync", side_effect=AssertionError("should not run")):
        with patch("paperforge.worker.asset_index.build_index", side_effect=AssertionError("should not run")):
            second = svc.run(json_output=True)
            assert second.ok is True

    # Mutate meta.json -> invalidates fastpath
    meta_file.write_text('{"zotero_key": "K200", "ocr_status": "done", "page_count": 2}', encoding="utf-8")
    calls = {"sel": 0}

    def count_sel(v, verbose=False, json_output=False):
        calls["sel"] += 1
        return {"new": 0, "updated": 0, "skipped": 0, "failed": 0, "errors": []}

    with patch("paperforge.worker.sync.run_selection_sync", side_effect=count_sel):
        third = svc.run(json_output=True)
        assert third.ok is True
        assert calls["sel"] == 1


def test_backup_version_cap_evicts_oldest_snapshots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PAPERFORGE_MAX_OCR_VERSIONS", "3")
    paper_root = tmp_path / "ocr" / "CAP1"
    render_dir = paper_root / "render"
    render_dir.mkdir(parents=True)
    for i in range(1, 5):
        (render_dir / "fulltext.md").write_text(f"# Version {i}", encoding="utf-8")
        backup_render_before_rebuild(paper_root)

    manifest = json.loads((paper_root / "versions" / "manifest.json").read_text(encoding="utf-8"))
    labels = [v["label"] for v in manifest["versions"]]
    assert labels == ["v2", "v3", "v4"]
    assert not (paper_root / "versions" / "v1").exists()
    assert (paper_root / "versions" / "v4" / "fulltext.md").exists()


def test_migrate_vault_storage_relocates_engine_and_rewrites_embeds(tmp_path: Path) -> None:
    canonical_test_config(tmp_path, system_dir="System")
    old_pf = tmp_path / "System" / "PaperForge"
    ocr_p = old_pf / "ocr" / "M001"
    (ocr_p / "assets" / "figures").mkdir(parents=True)
    (ocr_p / "assets" / "figures" / "figure_001.jpg").write_bytes(b"img-bytes")
    (ocr_p / "meta.json").write_text('{"zotero_key": "M001", "ocr_status": "done"}', encoding="utf-8")

    ws = tmp_path / "Resources" / "Literature" / "Ortho" / "M001 - Demo Study"
    ws.mkdir(parents=True)
    (ws / ("full" + "text.md")).write_text("legacy mirror", encoding="utf-8")
    note = ws / "M001.md"
    note.write_text(
        "---\ntitle: Demo\n---\n\n## 🔍 精读\n\n![[render/figures/figure_001.md|Fig 1]]\n",
        encoding="utf-8",
    )

    rc = migrate_storage_run(argparse.Namespace(vault_path=tmp_path, dry_run=False, json=True))
    assert rc == 0

    assert (tmp_path / ".paperforge" / "ocr" / "M001" / "meta.json").exists()
    assert not (tmp_path / "System" / "PaperForge").exists()
    assert (ws / "assets" / "M001_figure_001.jpg").read_bytes() == b"img-bytes"
    assert not (ws / ("full" + "text.md")).exists()
    assert "![[M001_figure_001.jpg|Fig 1]]" in note.read_text(encoding="utf-8")
    assert load_config(tmp_path).values["system_dir"].value == ".paperforge"
