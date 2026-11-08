"""Both OCR entries resolve source_pdf through one shared helper."""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf

from paperforge.pdf_resolver import resolve_source_pdf


def _pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


def test_unreadable_pdf_is_not_evidence(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    (vault / "System" / "Zotero" / "storage" / "ABCD1234").mkdir(parents=True)
    broken = vault / "System" / "Zotero" / "storage" / "ABCD1234" / "paper.pdf"
    broken.write_bytes(b"%PDF-1.4 not really a pdf")
    assert resolve_source_pdf(vault, "[[System/Zotero/storage/ABCD1234/paper.pdf]]") is None


def test_absolute_path_resolves(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "outside" / "paper.pdf")
    assert resolve_source_pdf(tmp_path / "vault", str(pdf)) == pdf


def test_wikilink_resolves_inside_the_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    pdf = _pdf(vault / "System" / "Zotero" / "storage" / "ABCD1234" / "paper.pdf")
    assert resolve_source_pdf(vault, "[[System/Zotero/storage/ABCD1234/paper.pdf]]") == pdf


def test_storage_locator_resolves_through_the_configured_zotero_dir(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    zotero = tmp_path / "zotero"
    pdf = _pdf(zotero / "storage" / "ABCD1234" / "paper.pdf")
    (vault / "paperforge.json").write_text(
        json.dumps({"zotero_data_dir": str(zotero)}), encoding="utf-8"
    )
    assert resolve_source_pdf(vault, "storage:ABCD1234/paper.pdf") == pdf


def test_unknown_locator_returns_none(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    assert resolve_source_pdf(vault, "storage:ZZZZ9999/missing.pdf") is None
    assert resolve_source_pdf(vault, "") is None
