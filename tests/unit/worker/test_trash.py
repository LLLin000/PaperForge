"""Trash safety-layer tests — pinned against the 2026-08-14 incident.

Regression: an empty/current-directory path (Path() == cwd == vault root)
must NEVER reach a recursive delete; prune's file removal is a MOVE into
.paperforge/trash with a manifest, restorable, and purge is restricted to
the trash root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.worker.trash import (
    DangerousPathError,
    list_trash,
    purge_trash,
    restore_trash,
    trash_remove,
    validate_target,
)
from tests.conftest import canonical_test_config


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault, system_dir="99_System")
    return vault


class TestValidateTarget:
    """fail-closed capability check."""

    @pytest.mark.parametrize(
        "dangerous",
        [
            Path(),
            Path("."),
            Path(""),
            Path(".."),
            None,
        ],
    )
    def test_refuses_empty_and_cwd_paths(self, tmp_path: Path, dangerous) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        root.mkdir(parents=True, exist_ok=True)
        with pytest.raises(DangerousPathError):
            validate_target(dangerous, allowed_root=root)

    def test_refuses_allowed_root_itself(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        root.mkdir(parents=True, exist_ok=True)
        with pytest.raises(DangerousPathError):
            validate_target(root, allowed_root=root)

    def test_refuses_path_escaping_root(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        root.mkdir(parents=True, exist_ok=True)
        outside = vault / "Resources"
        outside.mkdir()
        with pytest.raises(DangerousPathError):
            validate_target(outside, allowed_root=root)

    def test_accepts_path_inside_root(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        target = root / "KEY12345"
        target.mkdir(parents=True)
        resolved = validate_target(target, allowed_root=root)
        assert resolved == target.resolve()


class TestTrashRemove:
    def test_moves_to_trash_with_manifest(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        target = root / "KEY12345"
        target.mkdir(parents=True)
        (target / "fulltext.md").write_text("data", encoding="utf-8")

        rec = trash_remove(
            target, vault=vault, allowed_root=root,
            operation="library.prune", paper_key="KEY12345",
        )
        assert rec is not None
        assert rec["paper_key"] == "KEY12345"
        assert rec["original_path"] == str(target.resolve())
        assert not target.exists()  # moved away
        assert Path(rec["trash_path"]).exists()

        records = list_trash(vault)
        assert len(records) == 1
        assert records[0]["trash_id"] == rec["trash_id"]
        # manifest on disk matches
        manifest = Path(rec["trash_path"]).parent / "manifest.json"
        assert json.loads(manifest.read_text(encoding="utf-8"))["paper_key"] == "KEY12345"

    def test_missing_target_returns_none(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        root.mkdir(parents=True)
        assert trash_remove(root / "NOPE", vault=vault, allowed_root=root,
                            operation="library.prune") is None

    def test_refuses_vault_root_target(self, tmp_path: Path) -> None:
        """The 2026-08-14 incident: Path() resolved to the vault root and
        was rmtree'd.  Now it raises and nothing is touched."""
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        root.mkdir(parents=True, exist_ok=True)
        marker = vault / "important.md"
        marker.write_text("keep me", encoding="utf-8")
        with pytest.raises(DangerousPathError):
            trash_remove(Path(), vault=vault, allowed_root=root,
                         operation="library.prune")
        assert marker.exists()


class TestRestoreAndPurge:
    def test_restore_moves_back(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        target = root / "KEY9"
        target.mkdir(parents=True)
        (target / "f.md").write_text("x", encoding="utf-8")
        rec = trash_remove(target, vault=vault, allowed_root=root,
                           operation="library.prune", paper_key="KEY9")
        assert rec is not None

        original = restore_trash(vault, rec["trash_id"])
        assert original == Path(rec["original_path"])
        assert original.exists()
        assert not Path(rec["trash_path"]).exists()

    def test_purge_only_removes_trash_root(self, tmp_path: Path) -> None:
        vault = _vault(tmp_path)
        root = vault / "99_System" / "PaperForge" / "ocr"
        target = root / "KEY9"
        target.mkdir(parents=True)
        rec = trash_remove(target, vault=vault, allowed_root=root,
                           operation="library.prune", paper_key="KEY9")
        assert rec is not None

        purged = purge_trash(vault)
        assert purged >= 1
        assert not Path(rec["trash_path"]).exists()
        # non-trash content untouched
        assert root.exists()
