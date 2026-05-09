from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from paperforge.adapters.zotero_paths import (
    absolutize_vault_path,
    obsidian_wikilink_for_path,
    obsidian_wikilink_for_pdf,
)


class TestObsidianWikilinkForPdf:
    """Tests for obsidian_wikilink_for_pdf path resolution."""

    def test_empty_path_returns_empty(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        assert obsidian_wikilink_for_pdf("", vault) == ""
        assert obsidian_wikilink_for_pdf(None, vault) == ""
        assert obsidian_wikilink_for_pdf("  ", vault) == ""

    def test_storage_prefix_resolves_through_zotero_dir(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        zotero = tmp_path / "zotero_data"
        zotero.mkdir()
        result = obsidian_wikilink_for_pdf("storage:ABCD1234/paper.pdf", vault, zotero)
        assert result == f"[[{(zotero / 'storage' / 'ABCD1234' / 'paper.pdf').as_posix()}]]"

    def test_absolute_windows_path_outside_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        abs_path = tmp_path / "outside" / "file.pdf"
        abs_path.parent.mkdir(parents=True)
        abs_path.write_text("content")
        result = obsidian_wikilink_for_pdf(str(abs_path), vault)
        assert "outside" in result
        assert "file.pdf" in result
        assert result.startswith("[[")
        assert result.endswith("]]")

    def test_cjk_filename_with_spaces(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        zotero = tmp_path / "zotero_data"
        zotero.mkdir()
        result = obsidian_wikilink_for_pdf("storage:KEY/中文 文件.pdf", vault, zotero)
        assert "中文" in result
        assert "文件" in result

    def test_bare_key_no_prefix_resolves_relative_to_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        result = obsidian_wikilink_for_pdf("ABCD1234/paper.pdf", vault)
        assert result == "[[ABCD1234/paper.pdf]]"

    def test_storage_prefix_without_zotero_dir_falls_back(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        result = obsidian_wikilink_for_pdf("storage:ABCD/paper.pdf", vault)
        assert "ABCD" in result


class TestAbsolutizeVaultPath:
    """Tests for absolutize_vault_path."""

    def test_empty_path_returns_empty(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        assert absolutize_vault_path(vault, "") == ""
        assert absolutize_vault_path(vault, "  ") == ""

    def test_relative_path_resolution(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        result = absolutize_vault_path(vault, "subdir/file.pdf")
        expected = str((vault / "subdir" / "file.pdf").resolve())
        assert result == expected

    def test_relative_with_backslashes(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        result = absolutize_vault_path(vault, "subdir\\file.pdf")
        expected = str((vault / "subdir" / "file.pdf").resolve())
        assert result == expected

    def test_absolute_path_passthrough(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        abs_path = str(tmp_path / "outside" / "file.pdf")
        result = absolutize_vault_path(vault, abs_path)
        assert result == abs_path

    def test_junction_resolution_applied_when_flag_set(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        with patch("paperforge.pdf_resolver.resolve_junction") as mock_resolve:
            mock_resolve.return_value = tmp_path / "resolved" / "file.pdf"
            result = absolutize_vault_path(vault, "sub/file.pdf", resolve_junction=True)
            assert "resolved" in result

    def test_junction_not_applied_when_flag_false(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        with patch("paperforge.pdf_resolver.resolve_junction") as mock_resolve:
            result = absolutize_vault_path(vault, "sub/file.pdf", resolve_junction=False)
            mock_resolve.assert_not_called()


class TestObsidianWikilinkForPath:
    """Tests for obsidian_wikilink_for_path."""

    def test_empty_path_returns_empty(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        assert obsidian_wikilink_for_path(vault, "") == ""
        assert obsidian_wikilink_for_path(vault, "  ") == ""

    def test_relative_path_to_wikilink(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        result = obsidian_wikilink_for_path(vault, "subdir/paper.pdf")
        assert result == "[[subdir/paper.pdf]]"

    def test_absolute_path_outside_vault(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        abs_path = tmp_path / "outside" / "file.pdf"
        abs_path.parent.mkdir(parents=True)
        abs_path.write_text("content")
        result = obsidian_wikilink_for_path(vault, str(abs_path))
        assert result == f"[[{abs_path.as_posix()}]]"
