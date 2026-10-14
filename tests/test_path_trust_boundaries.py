"""Trust-boundary tests for X02 (containment + injection surface)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from paperforge.commands import versions
from paperforge.promote_r import _raw_path_has_symlink, _safe_stage_path
from paperforge.services import local_read


def _can_create_junction() -> bool:
    try:
        d = Path(os.environ.get("TEMP", ".")) / "_junction_probe"
        target = d / "target"
        link = d / "link"
        target.mkdir(parents=True, exist_ok=True)
        if link.exists():
            link.rmdir()
        subprocess.run(
            ["powershell", "-Command", f"New-Item -ItemType Junction -Path '{link}' -Target '{target}'"],
            check=True,
            capture_output=True,
        )
        ok = link.is_dir()
        try:
            link.rmdir()
        except OSError:
            pass
        try:
            target.rmdir()
        except OSError:
            pass
        try:
            d.rmdir()
        except OSError:
            pass
        return ok
    except Exception:  # noqa: BLE001
        return False


JUNCTION_AVAILABLE = _can_create_junction()


def make_junction(link: Path, target: Path) -> bool:
    target.mkdir(parents=True, exist_ok=True)
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        try:
            link.rmdir()
        except OSError:
            pass
    try:
        subprocess.run(
            ["powershell", "-Command", f"New-Item -ItemType Junction -Path '{link}' -Target '{target}'"],
            check=True,
            capture_output=True,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def test_raw_path_rejects_symlink_segment(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("x", encoding="utf-8")
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink privilege unavailable on this host")
    assert _raw_path_has_symlink(root, "link/secret.txt") is True


@pytest.mark.skipif(not JUNCTION_AVAILABLE, reason="junction creation unavailable")
def test_raw_path_rejects_junction_segment(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("x", encoding="utf-8")
    link = root / "junc"
    assert make_junction(link, outside)
    assert _raw_path_has_symlink(root, "junc/secret.txt") is True


def test_raw_path_clean(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a").mkdir()
    (root / "a" / "f.txt").write_text("x", encoding="utf-8")
    assert _raw_path_has_symlink(root, "a/f.txt") is False


def test_safe_stage_path_rejects_traversal(tmp_path):
    root = tmp_path / "stage"
    root.mkdir()
    assert _safe_stage_path(root, "../escape.txt") is None
    assert _safe_stage_path(root, "a/../../escape.txt") is None


@pytest.mark.skipif(not JUNCTION_AVAILABLE, reason="junction creation unavailable")
def test_safe_stage_path_rejects_junction_escape(tmp_path):
    root = tmp_path / "stage"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "junc"
    assert make_junction(link, outside)
    assert _safe_stage_path(root, "junc/escape.txt") is None


def test_resolve_fulltext_rejects_traversal(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    paper = {"fulltext_path": "../outside.txt"}
    assert local_read._resolve_fulltext(vault, paper) is None


def test_resolve_fulltext_allows_in_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    ft = vault / "fulltext.md"
    ft.write_text("hello", encoding="utf-8")
    paper = {"fulltext_path": "fulltext.md"}
    assert local_read._resolve_fulltext(vault, paper) == ft.resolve()


@pytest.mark.skipif(not JUNCTION_AVAILABLE, reason="junction creation unavailable")
def test_resolve_fulltext_rejects_junction_escape(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside_dir"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = vault / "junc"
    assert make_junction(link, outside)
    paper = {"fulltext_path": "junc/secret.txt"}
    assert local_read._resolve_fulltext(vault, paper) is None


def test_versions_contained_rejects_outside(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    assert versions._contained(root, outside) is False
    assert versions._safe_artifact_path(root, outside) is None


def test_versions_contained_accepts_inside(tmp_path):
    root = tmp_path / "paper"
    root.mkdir()
    inside = root / "render" / "fulltext.md"
    inside.parent.mkdir(parents=True, exist_ok=True)
    inside.write_text("x", encoding="utf-8")
    assert versions._contained(root, inside) is True
    assert versions._safe_artifact_path(root, inside) == str(inside)


def test_image_regex_does_not_execute(tmp_path):
    from paperforge.promote_r import _IMAGE_RE

    text = "![x](http://evil.example/a.png) ![[../../../etc/passwd]]"
    matches = _IMAGE_RE.findall(text)
    assert isinstance(matches, list)


def test_safe_segment_rejects_dotdot():
    assert versions._safe_segment("..") is False
    assert versions._safe_segment("") is False
    assert versions._safe_segment("a/b") is False
    assert versions._safe_segment("legit") is True
