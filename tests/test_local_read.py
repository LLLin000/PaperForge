"""Canonical local-read primitive tests (#189).

Covers the observable contract of ``paperforge read KEY --find TERM``:
three structured statuses (matched / no_match / no_readable_source), literal
case-insensitive matching (never regex), auto = fulltext + canonical PDF
with dedupe, wikilink locator handling, read-only behavior, and --source
filtering.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema
from tests.conftest import canonical_test_config

FULLTEXT_LINES = [
    "INTRODUCTION",
    "The RFE model reduced redundant variables.",
    "Results are shown in Figure 2.",
]
PDF_TEXT = "Supplementary: RFE recursive feature elimination details here."


def _vault(tmp_path: Path) -> Path:
    """Canonical test vault (config bootstrapped, directory present)."""
    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault)
    return vault


def _seed_paper(vault: Path, key: str, *, with_pdf: bool = True) -> None:
    """Canonical vault: papers row + fulltext file + (optional) PDF."""
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / key
    ocr_dir.mkdir(parents=True, exist_ok=True)
    ft = ocr_dir / "fulltext.md"
    ft.write_text("\n".join(FULLTEXT_LINES), encoding="utf-8")

    db = get_memory_db_path(vault)
    conn = get_connection(db, read_only=False)
    try:
        ensure_schema(conn)
        pdf_path = ""
        if with_pdf:
            import fitz

            pdf_path = f"[[System/Zotero/storage/{key}/paper.pdf]]"
            pdf = vault / "System" / "Zotero" / "storage" / key / "paper.pdf"
            pdf.parent.mkdir(parents=True, exist_ok=True)
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), PDF_TEXT)
            doc.save(str(pdf))
            doc.close()
        conn.execute(
            "INSERT INTO papers (zotero_key, title, fulltext_path, pdf_path, has_pdf) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, f"Paper {key}", f"System/PaperForge/ocr/{key}/fulltext.md", pdf_path,
             1 if with_pdf else 0),
        )
        conn.commit()
    finally:
        conn.close()


def _read(vault: Path, key: str, find: str, source: str = "auto") -> dict:
    from paperforge.services.local_read import read_paper_local

    return read_paper_local(vault, key, find, source=source)


def test_fulltext_literal_hit_returns_line(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    result = _read(vault, "AAAA1111", "redundant variables")
    assert result["status"] == "matched"
    hits = [m for m in result["matches"] if m["source"] == "fulltext"]
    assert hits and hits[0]["line"] == 2
    assert "RFE model" in hits[0]["text"]


def test_pdf_only_hit_returns_page(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    result = _read(vault, "AAAA1111", "recursive feature elimination", source="auto")
    pdf_hits = [m for m in result["matches"] if m["source"] == "pdf"]
    assert pdf_hits and pdf_hits[0]["page"] == 1
    assert "recursive feature" in pdf_hits[0]["text"].lower()


def test_auto_dedupes_identical_source_text(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    result = _read(vault, "AAAA1111", "RFE")
    texts = [(m["source"], m["text"]) for m in result["matches"]]
    assert len(texts) == len(set(texts)), "duplicate matches must be deduped"
    assert any(s == "fulltext" for s, _ in texts)
    assert any(s == "pdf" for s, _ in texts)


def test_literal_is_case_insensitive_not_regex(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    # "RFE" appears lowercase in fulltext line 2; a regex special char must
    # be treated literally (no match -> no_match, not an error or wildcard).
    assert _read(vault, "AAAA1111", "rfe")["status"] == "matched"
    assert _read(vault, "AAAA1111", "redu.*able")["status"] == "no_match"


def test_zero_match_is_no_match_not_error(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    result = _read(vault, "AAAA1111", "galvanotaxis")
    assert result["status"] == "no_match"
    assert result["matches"] == []


def test_no_readable_source_distinct_from_no_match(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111", with_pdf=False)
    # fulltext exists but pdf missing; literal absent in fulltext -> no_match.
    assert _read(vault, "AAAA1111", "galvanotaxis")["status"] == "no_match"
    # A key with NO row at all -> no_readable_source.
    assert _read(vault, "NOPE1234", "x")["status"] == "no_readable_source"


def test_unknown_key_is_no_readable_source(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    assert _read(vault, "NOPE1234", "x")["status"] == "no_readable_source"


def test_source_fulltext_only(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    result = _read(vault, "AAAA1111", "RFE", source="fulltext")
    assert all(m["source"] == "fulltext" for m in result["matches"])
    assert _read(vault, "AAAA1111", "recursive feature elimination", source="fulltext")["status"] == "no_match"


def test_source_pdf_only(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    result = _read(vault, "AAAA1111", "recursive feature", source="pdf")
    assert all(m["source"] == "pdf" for m in result["matches"])
    assert _read(vault, "AAAA1111", "galvanotaxis", source="pdf")["status"] == "no_match"


def test_read_is_read_only(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    ft = vault / "System" / "PaperForge" / "ocr" / "AAAA1111" / "fulltext.md"
    meta = vault / "System" / "PaperForge" / "ocr" / "AAAA1111" / "meta.json"
    before_ft = ft.read_bytes()
    before_meta = meta.read_bytes() if meta.exists() else b"<absent>"
    _read(vault, "AAAA1111", "RFE")
    assert ft.read_bytes() == before_ft, "fulltext mutated by read"
    assert (meta.read_bytes() if meta.exists() else b"<absent>") == before_meta, "meta mutated by read"


def test_cli_wire_shape(tmp_path: Path, capsys) -> None:
    """CLI: ok/status/matches envelope, PATH_NOT_FOUND for no source."""
    import subprocess
    import sys

    vault = _vault(tmp_path)
    _seed_paper(vault, "AAAA1111")
    r = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), "read", "AAAA1111",
         "--find", "RFE", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    assert payload["data"]["status"] == "matched"
    assert payload["data"]["matches"][0]["source"] == "fulltext"

    r2 = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault), "read", "NOPE1234",
         "--find", "x", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r2.returncode == 1
    p2 = json.loads(r2.stdout)
    assert p2["data"]["status"] == "no_readable_source"
