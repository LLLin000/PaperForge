"""Materialization is transactional: failures never destroy old artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import paperforge.worker.ocr_objects as objects


def _figure(fig_id="figure_001"):
    return {
        "matched_figures": [
            {
                "figure_id": fig_id,
                "page": 1,
                "text": "Figure 1. Caption.",
                "cluster_bbox": [10, 10, 100, 100],
                "matched_assets": [],
            }
        ],
        "unmatched_assets": [],
        "unresolved_clusters": [],
    }


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_successful_materialization_replaces_and_removes_stale_files(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    render = tmp_path / "render"
    _write(assets / "figures" / "stale.jpg", b"old")
    _write(render / "figures" / "stale.md", b"old")
    _write(render / "figures" / "figure_001.md", b"old")

    objects.extract_and_write_objects(
        None, _figure(), {"tables": [], "unmatched_assets": []}, assets, render
    )

    assert (render / "figures" / "figure_001.md").read_text(encoding="utf-8").startswith("# Figure 1")
    assert not (assets / "figures" / "stale.jpg").exists()
    assert not (render / "figures" / "stale.md").exists()
    assert (render / "materialization.provenance.json").is_file()
    assert not list(tmp_path.glob(".materialization-*"))


def test_collision_leaves_old_artifacts_byte_identical(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    render = tmp_path / "render"
    old_asset = assets / "figures" / "same.jpg"
    old_md = render / "figures" / "same.md"
    _write(old_asset, b"old-asset")
    _write(old_md, b"old-markdown")
    figures = {
        "matched_figures": [
            {"figure_id": "same", "page": 1, "text": "Figure 1", "matched_assets": []},
            {"figure_id": "same", "page": 2, "text": "Figure 2", "matched_assets": []},
        ],
        "unmatched_assets": [],
    }

    with pytest.raises(objects.MaterializationCollisionError):
        objects.extract_and_write_objects(None, figures, {"tables": [], "unmatched_assets": []}, assets, render)

    assert old_asset.read_bytes() == b"old-asset"
    assert old_md.read_bytes() == b"old-markdown"
    assert not list(tmp_path.glob(".materialization-*"))


def test_staging_failure_leaves_old_artifacts_untouched(tmp_path: Path, monkeypatch) -> None:
    assets = tmp_path / "assets"
    render = tmp_path / "render"
    old_md = render / "figures" / "figure_001.md"
    _write(old_md, b"old-markdown")

    def _fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(objects, "_write_object_markdown", _fail)
    with pytest.raises(objects.MaterializationError):
        objects.extract_and_write_objects(
            None, _figure(), {"tables": [], "unmatched_assets": []}, assets, render
        )

    assert old_md.read_bytes() == b"old-markdown"
    assert not list(tmp_path.glob(".materialization-*"))


def test_commit_failure_rolls_back_every_swap(tmp_path: Path) -> None:
    paper = tmp_path
    target_a = paper / "assets" / "figures"
    target_b = paper / "render" / "figures"
    old_a = target_a / "figure_001.jpg"
    old_b = target_b / "figure_001.md"
    _write(old_a, b"old-a")
    _write(old_b, b"old-b")
    stage = paper / ".stage"
    staged_a = stage / "assets" / "figures"
    staged_b = stage / "render" / "figures"
    _write(staged_a / "figure_001.jpg", b"new-a")
    # staged_b is intentionally absent, so the second swap fails after the first moved

    with pytest.raises(objects.MaterializationCommitError):
        objects._commit_staged_objects(
            paper_root=paper,
            stage_root=stage,
            staged_targets=[(target_a, staged_a), (target_b, staged_b)],
            provenance=None,
        )

    assert old_a.read_bytes() == b"old-a"
    assert old_b.read_bytes() == b"old-b"
    assert not (target_a / "figure_001.jpg").exists() or (target_a / "figure_001.jpg").read_bytes() == b"old-a"
    assert not list(paper.glob(".materialization-*"))


def test_recovery_restores_old_directories_after_interrupted_commit(tmp_path: Path) -> None:
    paper = tmp_path
    target = paper / "assets" / "figures"
    backup = paper / ".materialization-backup-deadbeef" / "0"
    stage = paper / ".materialization-stage-deadbeef"
    _write(target / "figure_001.jpg", b"new")
    _write(backup / "figure_001.jpg", b"old")
    stage.mkdir()
    journal = paper / ".materialization-journal.json"
    journal.write_text(
        json.dumps(
            {
                "status": "committing",
                "stage_root": str(stage),
                "backup_root": str(backup.parent),
                "targets": [{"target": str(target), "backup": str(backup)}],
            }
        ),
        encoding="utf-8",
    )

    objects._recover_materialization_journal(paper)

    assert (target / "figure_001.jpg").read_bytes() == b"old"
    assert not stage.exists()
    assert not journal.exists()
    assert not backup.parent.exists()


def test_dry_run_builds_manifest_without_touching_stale_journal(tmp_path: Path) -> None:
    journal = tmp_path / ".materialization-journal.json"
    journal.write_text("{ malformed stale journal }", encoding="utf-8")
    original = journal.read_bytes()

    manifest = objects.extract_and_write_objects(
        None,
        _figure(),
        {"tables": [], "unmatched_assets": []},
        tmp_path / "assets",
        tmp_path / "render",
        dry_run=True,
    )
    assert manifest is not None
    assert manifest["figures"] == ["figure_001"]
    assert any(path.endswith("figure_001.md") for path in manifest["render"])
    assert not (tmp_path / "assets").exists()
    assert not (tmp_path / "render").exists()
    assert journal.read_bytes() == original
