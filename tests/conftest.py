"""Shared pytest fixtures for PaperForge Lite smoke tests.

Fixture vault factory + test data fixtures for end-to-end smoke testing
without touching any real vault.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixture vault factory
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_vault(tmp_path: Path) -> Path:
    """Create a complete fixture vault with realistic directory structure.

    Creates:
        <vault>/99_System/PaperForge/{exports,ocr}
        <vault>/03_Resources/{Literature,LiteratureControl/library-records/骨科}
        <vault>/05_Bases
        <vault>/.opencode/{skills,command}
        <vault>/paperforge.json
    """
    vault = tmp_path / "fixture_vault"
    vault.mkdir()

    # System / PaperForge structure
    system = vault / "99_System"
    pf = system / "PaperForge"
    (pf / "exports").mkdir(parents=True)
    (pf / "ocr").mkdir(parents=True)

    # Resources structure
    resources = vault / "03_Resources"
    literature = resources / "Literature"
    literature.mkdir(parents=True)
    control = resources / "LiteratureControl"
    control.mkdir(parents=True)
    records = control / "library-records" / "骨科"
    records.mkdir(parents=True)

    # Bases
    (vault / "05_Bases").mkdir(parents=True)

    # OpenCode skills / command
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)

    # paperforge.json with defaults
    pf_cfg = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
    }
    (vault / "paperforge.json").write_text(
        json.dumps(pf_cfg, ensure_ascii=False), encoding="utf-8"
    )

    return vault


# ---------------------------------------------------------------------------
# Library record fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_library_records(fixture_vault: Path) -> list[Path]:
    """Create 3 minimal library-record markdown files in fixture vault.

    Returns:
        List of Path objects for the created record files.
    """
    records_dir = (
        fixture_vault
        / "03_Resources"
        / "LiteratureControl"
        / "library-records"
        / "骨科"
    )
    records_dir.mkdir(parents=True, exist_ok=True)

    records = [
        {
            "zotero_key": "TESTKEY001",
            "domain": "骨科",
            "title": "Test Paper Alpha: A Study on Bone Healing",
            "year": "2023",
            "doi": "10.1234/test.alpha",
            "has_pdf": "true",
            "pdf_path": "",
            "fulltext_md_path": "",
            "recommend_analyze": "true",
            "analyze": "false",
            "do_ocr": "false",
            "ocr_status": "pending",
            "deep_reading_status": "pending",
            "analysis_note": "",
        },
        {
            "zotero_key": "TESTKEY002",
            "domain": "骨科",
            "title": "Test Paper Beta: Knee Arthroscopy Techniques",
            "year": "2024",
            "doi": "10.1234/test.beta",
            "has_pdf": "true",
            "pdf_path": "",
            "fulltext_md_path": "",
            "recommend_analyze": "true",
            "analyze": "false",
            "do_ocr": "false",
            "ocr_status": "pending",
            "deep_reading_status": "pending",
            "analysis_note": "",
        },
        {
            "zotero_key": "TESTKEY003",
            "domain": "骨科",
            "title": "Test Paper Gamma: Sports Injury Prevention",
            "year": "2022",
            "doi": "10.1234/test.gamma",
            "has_pdf": "false",
            "pdf_path": "",
            "fulltext_md_path": "",
            "recommend_analyze": "false",
            "analyze": "false",
            "do_ocr": "false",
            "ocr_status": "nopdf",
            "deep_reading_status": "pending",
            "analysis_note": "",
        },
    ]

    created: list[Path] = []
    for row in records:
        key = row["zotero_key"]
        title_slug = row["title"].split(":")[0].strip()
        path = records_dir / f"{key}.md"

        def yaml_val(v: str) -> str:
            return f'"{v}"' if v else '""'

        lines = ["---"]
        for k, v in row.items():
            if k == "title":
                lines.append(f'title: {yaml_val(v)}')
            elif k in ("doi", "pdf_path", "fulltext_md_path", "analysis_note", "ocr_status", "deep_reading_status"):
                lines.append(f"{k}: {yaml_val(v)}")
            elif k in ("recommend_analyze", "analyze", "do_ocr"):
                lines.append(f"{k}: {v}")
            else:
                lines.append(f"{k}: {yaml_val(v)}")
        lines.extend(["---", "", f'# {row["title"]}', ""])
        lines.append("正式库控制记录。")
        lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        created.append(path)

    return created


# ---------------------------------------------------------------------------
# Better BibTeX JSON fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_bbt_json(fixture_vault: Path) -> Path:
    """Create a minimal Better BibTeX JSON export in fixture vault exports/.

    Returns:
        Path to the created JSON export file.
    """
    exports_dir = fixture_vault / "99_System" / "PaperForge" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    export_data = {
        "items": [
            {
                "key": "TESTKEY001",
                "itemType": "journalArticle",
                "title": "Test Paper Alpha: A Study on Bone Healing",
                "creators": [
                    {"creatorType": "author", "firstName": "Alice", "lastName": "Smith"},
                    {"creatorType": "author", "firstName": "Bob", "lastName": "Jones"},
                ],
                "date": "2023",
                "publicationTitle": "Journal of Orthopedic Research",
                "DOI": "10.1234/test.alpha",
                "PMID": "",
                "abstractNote": "Abstract of Test Paper Alpha.",
                "collections": [],
                "attachments": [
                    {"path": "TESTKEY001.pdf", "contentType": "application/pdf"}
                ],
            },
            {
                "key": "TESTKEY002",
                "itemType": "journalArticle",
                "title": "Test Paper Beta: Knee Arthroscopy Techniques",
                "creators": [
                    {"creatorType": "author", "firstName": "Carol", "lastName": "Wang"},
                ],
                "date": "2024",
                "publicationTitle": "Sports Medicine",
                "DOI": "10.1234/test.beta",
                "PMID": "12345678",
                "abstractNote": "Abstract of Test Paper Beta.",
                "collections": [],
                "attachments": [
                    {"path": "TESTKEY002.pdf", "contentType": "application/pdf"}
                ],
            },
            {
                "key": "TESTKEY003",
                "itemType": "journalArticle",
                "title": "Test Paper Gamma: Sports Injury Prevention",
                "creators": [
                    {"creatorType": "author", "firstName": "Dan", "lastName": "Lee"},
                ],
                "date": "2022",
                "publicationTitle": "Injury Prevention",
                "DOI": "10.1234/test.gamma",
                "PMID": "",
                "abstractNote": "Abstract of Test Paper Gamma.",
                "collections": [],
                "attachments": [],
            },
        ]
    }

    export_path = exports_dir / "骨科.json"
    export_path.write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return export_path


# ---------------------------------------------------------------------------
# Fixture with real PDF file
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture_with_pdf(tmp_path: Path) -> tuple[Path, Path]:
    """Create a fixture vault with a real temporary PDF file.

    Creates paperforge.json, library-record with has_pdf=true, and a real
    temp PDF file on disk.

    Returns:
        Tuple of (vault_path, pdf_path).
    """
    vault = tmp_path / "fixture_with_pdf"
    vault.mkdir()

    system = vault / "99_System"
    pf = system / "PaperForge"
    (pf / "exports").mkdir(parents=True)
    (pf / "ocr").mkdir(parents=True)

    resources = vault / "03_Resources"
    literature = resources / "Literature"
    literature.mkdir(parents=True)
    control = resources / "LiteratureControl"
    control.mkdir(parents=True)
    records = control / "library-records" / "骨科"
    records.mkdir(parents=True)

    (vault / "05_Bases").mkdir(parents=True)
    (vault / ".opencode" / "skills").mkdir(parents=True)
    (vault / ".opencode" / "command").mkdir(parents=True)

    pf_cfg = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
    }
    (vault / "paperforge.json").write_text(
        json.dumps(pf_cfg, ensure_ascii=False), encoding="utf-8"
    )

    # Create a minimal valid PDF
    pdf_path = records / "TESTPDF001.pdf"
    _write_minimal_pdf(pdf_path)

    # Library record with has_pdf: true
    record_path = records / "TESTPDF001.md"
    record_text = f"""---
zotero_key: TESTPDF001
domain: 骨科
title: "Test Paper With Real PDF"
year: 2024
doi: "10.1234/test.real"
has_pdf: true
pdf_path: "{pdf_path.name}"
fulltext_md_path: ""
recommend_analyze: true
analyze: false
do_ocr: true
ocr_status: pending
deep_reading_status: pending
analysis_note: ""
---

# Test Paper With Real PDF

正式库控制记录。
"""
    record_path.write_text(record_text, encoding="utf-8")

    return vault, pdf_path


def _write_minimal_pdf(path: Path) -> None:
    """Write a minimal valid PDF 1.4 file to disk."""
    # Minimal PDF 1.4 with one empty page
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n"
        b"<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n"
        b"199\n"
        b"%%EOF\n"
    )
    path.write_bytes(pdf_content)
