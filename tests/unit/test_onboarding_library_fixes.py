"""Unit tests for Stage 2 library setup, BBT validation, and external Zotero support."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from paperforge.adapters.bbt import detect_bbt_export_problem, load_export_rows
from paperforge.memory.record_source import capture_source, source_provenance
from paperforge.probes.library import probe_library
from paperforge.setup.vault import VaultInitializer
from tests.conftest import canonical_test_config


def test_csl_json_is_rejected_with_actionable_bbt_guidance(tmp_path: Path) -> None:
    export = tmp_path / "library.json"
    export.write_text(
        json.dumps([
            {
                "id": "http://zotero.org/users/1/items/ABCD1234",
                "type": "article-journal",
                "title": "Sample Study",
            }
        ]),
        encoding="utf-8",
    )

    msg = detect_bbt_export_problem(export)
    assert msg is not None
    assert "CSL JSON" in msg
    assert "Better BibTeX JSON" in msg

    with pytest.raises(ValueError, match="Better BibTeX JSON"):
        load_export_rows(export)


def test_probe_library_surfaces_csl_json_and_bib_errors(tmp_path: Path) -> None:
    ext_zotero = tmp_path / "ExtZotero"
    ext_zotero.mkdir()
    canonical_test_config(tmp_path, zotero_data_dir=str(ext_zotero))
    exports = tmp_path / "System" / "PaperForge" / "exports"
    exports.mkdir(parents=True, exist_ok=True)

    csl = exports / "refs.json"
    csl.write_text(json.dumps([{"id": "x", "type": "article-journal"}]), encoding="utf-8")
    env = probe_library(tmp_path)
    assert env["reason"]["code"] == "library.bbt_invalid_format"
    assert "Better BibTeX JSON" in env["reason"]["text"]

    csl.unlink()
    (exports / "refs.bib").write_text("@article{a, title={x}}\n", encoding="utf-8")
    env_bib = probe_library(tmp_path)
    assert env_bib["reason"]["code"] == "library.bbt_invalid_format"
    assert ".bib" in env_bib["reason"]["text"]


def test_record_source_allows_configured_external_zotero_pdf(tmp_path: Path) -> None:
    import pymupdf

    vault = tmp_path / "vault"
    vault.mkdir()
    ext_zotero = tmp_path / "ZoteroData"
    pdf_dir = ext_zotero / "storage" / "EXT00001"
    pdf_dir.mkdir(parents=True)
    pdf = pdf_dir / "paper.pdf"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "Unique external Zotero excerpt")
        doc.save(pdf)

    canonical_test_config(vault, zotero_data_dir=ext_zotero.as_posix())
    idx = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "zotero_key": "EXTPAPER",
                        "pdf_path": f"[[{pdf.as_posix()}]]",
                        "has_pdf": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    excerpt = "Unique external Zotero excerpt"
    source = capture_source(
        vault,
        "EXTPAPER",
        excerpt,
        {"path": pdf.as_posix(), "physical_page": 1, "basis": "exact_text", "anchor": excerpt},
    )
    assert source["verification"]["status"] == "matched"
    assert source_provenance(vault, "EXTPAPER", excerpt, source)["status"] == "matched"

    # Arbitrary path outside vault AND outside configured zotero_data_dir stays rejected.
    outside_pdf = tmp_path / "OutsideOther" / "evil.pdf"
    outside_pdf.parent.mkdir()
    outside_pdf.write_bytes(pdf.read_bytes())
    rejected = capture_source_or_none(vault, "EXTPAPER", excerpt, outside_pdf.as_posix())
    assert rejected is False


def capture_source_or_none(vault: Path, key: str, excerpt: str, pdf_path: str) -> bool:
    try:
        capture_source(vault, key, excerpt, {"path": pdf_path, "physical_page": 1})
        return True
    except ValueError:
        return False


def test_vault_initializer_skips_junction_for_hidden_dot_paperforge(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    ext_zotero = tmp_path / "Zotero"
    vault.mkdir()
    ext_zotero.mkdir()
    vi = VaultInitializer(
        vault,
        {"system": vault / ".paperforge", "paperforge": vault / ".paperforge"},
    )
    res = vi.create_zotero_junction(str(ext_zotero))
    assert res.ok is True
    assert res.details.get("reason") == "direct_zotero_data_dir"
    assert not (vault / ".paperforge" / "Zotero").exists()


def test_vault_initializer_tolerates_junction_failure_when_zotero_exists(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    ext_zotero = tmp_path / "Zotero"
    vault.mkdir()
    ext_zotero.mkdir()
    (vault / "System").mkdir()
    vi = VaultInitializer(
        vault,
        {"system": vault / "System", "paperforge": vault / "System" / "PaperForge"},
    )
    if os.name == "nt":
        import subprocess

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "junction denied"),
        )
    else:
        monkeypatch.setattr(Path, "symlink_to", lambda *a, **kw: (_ for _ in ()).throw(OSError("denied")))

    res = vi.create_zotero_junction(str(ext_zotero))
    assert res.ok is True
    assert res.details.get("fallback") == "direct_zotero_data_dir"
