"""Tests for Phase 2a: rebuild backup mechanism."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.worker.ocr_versions import backup_render_before_rebuild


def test_backup_creates_version_manifest(tmp_path: Path):
    """Backup creates versions/v1/ with manifest.json and copied files."""
    paper_root = tmp_path / "ocr" / "ME6BJZVS"
    render = paper_root / "render"
    render.mkdir(parents=True)
    (render / "fulltext.md").write_text("# Original fulltext\n\nSome content.", encoding="utf-8")
    (render / "render-map.json").write_text('{"meta": "v1"}', encoding="utf-8")

    label = backup_render_before_rebuild(paper_root)

    assert label == "v1"
    manifest_path = paper_root / "versions" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["versions"]) == 1
    assert manifest["versions"][0]["label"] == "v1"
    assert manifest["versions"][0]["fulltext_size"] > 0
    assert (paper_root / "versions" / "v1" / "fulltext.md").exists()
    assert (paper_root / "versions" / "v1" / "render-map.json").read_text(encoding="utf-8") == '{"meta": "v1"}'


def test_backup_increments_version_label(tmp_path: Path):
    """Second backup creates v2, third creates v3."""
    paper_root = tmp_path / "ocr" / "ME6BJZVS"
    render = paper_root / "render"
    render.mkdir(parents=True)

    # First backup
    (render / "fulltext.md").write_text("# Version 1", encoding="utf-8")
    v1 = backup_render_before_rebuild(paper_root)
    assert v1 == "v1"

    # Second backup (simulate rebuild's new content)
    (render / "fulltext.md").write_text("# Version 2", encoding="utf-8")
    v2 = backup_render_before_rebuild(paper_root)
    assert v2 == "v2"

    # Third backup
    (render / "fulltext.md").write_text("# Version 3", encoding="utf-8")
    v3 = backup_render_before_rebuild(paper_root)
    assert v3 == "v3"

    manifest = json.loads(
        (paper_root / "versions" / "manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest["versions"]) == 3
    assert manifest["versions"][0]["label"] == "v1"
    assert manifest["versions"][1]["label"] == "v2"
    assert manifest["versions"][2]["label"] == "v3"


def test_backup_no_render_returns_none(tmp_path: Path):
    """If no render/fulltext.md exists, returns None and creates no files."""
    paper_root = tmp_path / "ocr" / "ME6BJZVS"
    paper_root.mkdir(parents=True)
    # No render/ at all

    label = backup_render_before_rebuild(paper_root)
    assert label is None
    assert not (paper_root / "versions").exists()


def test_backup_carries_structured_content_hash(tmp_path: Path):
    """Backup carries forward structured_content_hash and renderer_version from meta.json."""
    paper_root = tmp_path / "ocr" / "ME6BJZVS"
    render = paper_root / "render"
    render.mkdir(parents=True)
    (render / "fulltext.md").write_text("# Test", encoding="utf-8")

    # Write meta.json with hash and version info
    meta = {
        "structured_content_hash": "abc123",
        "derived_version": {"renderer_version": "2.1.0"},
    }
    (paper_root / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    label = backup_render_before_rebuild(paper_root)
    assert label == "v1"

    manifest = json.loads(
        (paper_root / "versions" / "manifest.json").read_text(encoding="utf-8")
    )
    entry = manifest["versions"][0]
    assert entry["structured_content_hash"] == "abc123"
    assert entry["renderer_version"] == "2.1.0"


def test_backup_idempotent_corrupted_manifest(tmp_path: Path):
    """Backup handles corrupted manifest gracefully (starts fresh)."""
    paper_root = tmp_path / "ocr" / "ME6BJZVS"
    render = paper_root / "render"
    render.mkdir(parents=True)
    (render / "fulltext.md").write_text("# Text", encoding="utf-8")

    # Write corrupted manifest
    versions_dir = paper_root / "versions"
    versions_dir.mkdir(parents=True)
    (versions_dir / "manifest.json").write_text("{corrupted", encoding="utf-8")

    label = backup_render_before_rebuild(paper_root)
    assert label == "v1"
    manifest = json.loads(
        (versions_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest["versions"]) == 1


def test_backup_non_default_files_not_required(tmp_path: Path):
    """Backup only requires fulltext.md; render-map and heading-events are optional."""
    paper_root = tmp_path / "ocr" / "ME6BJZVS"
    render = paper_root / "render"
    render.mkdir(parents=True)
    (render / "fulltext.md").write_text("# Only fulltext", encoding="utf-8")
    # No render-map.json, no heading-events.json

    label = backup_render_before_rebuild(paper_root)
    assert label == "v1"
    assert (paper_root / "versions" / "v1" / "fulltext.md").exists()
    assert not (paper_root / "versions" / "v1" / "render-map.json").exists()
    assert not (paper_root / "versions" / "v1" / "heading-events.json").exists()
