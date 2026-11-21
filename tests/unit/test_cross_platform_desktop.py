"""Cross-platform desktop tests (macOS APFS NFD/NFC, Linux case/zombie/tilde, POSIX permissions)."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from paperforge.core import io as pf_io
from paperforge.probes.library import probe_library
from paperforge.services.control_daemon import _is_linux_zombie_proc_stat
from paperforge.services.identity_resolver import scan_vault_identities
from paperforge.services.vault_upgrade import _is_paperforge_owned_base_file
from tests.conftest import canonical_test_config

pytestmark = pytest.mark.unit


def test_macos_apfs_nfd_vs_nfc_domain_and_note_matching(tmp_path: Path) -> None:
    """macOS APFS returns NFD decomposed strings (`e\\u0301`), while YAML/BBT use NFC (`\\u00e9`)."""
    nfd_domain = unicodedata.normalize("NFD", "Neuroé")
    nfc_domain = unicodedata.normalize("NFC", "Neuroé")
    assert nfd_domain != nfc_domain

    lit_root = tmp_path / "Resources" / "Literature"
    ws_dir = lit_root / nfd_domain / unicodedata.normalize("NFD", "MAC00001 - Café Study")
    ws_dir.mkdir(parents=True)
    # Linux case-sensitive uppercase `.MD` extension + NFD stem
    note_file = ws_dir / (unicodedata.normalize("NFD", "MAC00001 - Café Study") + ".MD")
    note_file.write_text(
        '---\nzotero_key: "MAC00001"\ntitle: "Café Study"\nocr_status: "done"\n---\n\nBody\n',
        encoding="utf-8",
    )
    (ws_dir / "paper-meta.json").write_text('{"zotero_key": "MAC00001"}', encoding="utf-8")

    scan = scan_vault_identities(lit_root)
    assert "MAC00001" in scan.workspaces
    ws = scan.workspaces["MAC00001"]
    assert ws.domain == nfc_domain
    assert ws.main_note_path == note_file

    # Base file stem in NFD matches NFC known_domains
    base_file = tmp_path / (nfd_domain + ".base")
    base_txt = 'filters:\n  and:\n    - "!zotero_key.isEmpty()"\nviews:\n  - type: table\n    name: 文献库\n'
    base_file.write_text(base_txt, encoding="utf-8")
    assert _is_paperforge_owned_base_file(base_txt, base_file, {nfc_domain}) is True


def test_linux_proc_stat_zombie_detection_even_with_parens_in_comm() -> None:
    # Comm name can contain spaces and parentheses on Linux (`1234 (obsidian (helper)) Z ...`)
    assert _is_linux_zombie_proc_stat("4321 (obsidian (gpu)) Z 1 4321 4321 0 -1") is True
    assert _is_linux_zombie_proc_stat("4321 (obsidian) S 1 4321 4321 0 -1") is False
    assert _is_linux_zombie_proc_stat("4321 (python3) R 100 4321 4321 0 -1") is False


def test_tilde_expansion_for_macos_and_linux_zotero_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = tmp_path / "home" / "researcher"
    zot_dir = fake_home / "Zotero"
    zot_dir.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir=".paperforge")
    # Write `~/Zotero` shorthand commonly used by macOS & Linux users
    cfg_path = vault / "paperforge.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["vault_config"]["zotero_data_dir"] = "~/Zotero"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    env = probe_library(vault)
    assert env["reason"]["code"] != "library.zotero_not_found"


def test_posix_atomic_write_preserves_existing_file_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chmod_calls: list[int] = []
    target = tmp_path / "shared_note.md"
    target.write_text("initial\n", encoding="utf-8")

    monkeypatch.setattr(pf_io, "_IS_WINDOWS", False)
    orig_chmod = pf_io.os.chmod
    monkeypatch.setattr(
        pf_io.os,
        "chmod",
        lambda p, mode: (chmod_calls.append(mode), orig_chmod(p, mode))[1],
    )
    pf_io.write_text_atomic(target, "updated\n")
    assert target.read_text(encoding="utf-8") == "updated\n"
    assert len(chmod_calls) == 1
