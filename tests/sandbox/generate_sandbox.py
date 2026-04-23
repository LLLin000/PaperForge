#!/usr/bin/env python3
"""Generate a completely sealed test sandbox vault for PaperForge Lite.

Run from repo root:
    python tests/sandbox/generate_sandbox.py

This creates tests/sandbox/vault/ with:
- Full vault directory structure
- Mock Zotero storage with 3 PDFs
- Better BibTeX JSON exports (2 domains)
- Library records for all papers
- paperforge.json with defaults
- .env with dummy credentials

Everything isolated — never touches real vault or Zotero.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent
SANDBOX_VAULT = ROOT / "vault"

PAPERFORGE_CFG = {
    "system_dir": "99_System",
    "resources_dir": "03_Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "05_Bases",
}

ZOTERO_JSON_ITEMS = {
    "骨科": [
        {
            "key": "SANDBOX001",
            "itemType": "journalArticle",
            "title": "Suture Anchor Fixation for Rotator Cuff Tears: A Biomechanical Analysis",
            "creators": [
                {"creatorType": "author", "firstName": "James", "lastName": "Burkhardt"},
                {"creatorType": "author", "firstName": "Maria", "lastName": "Chen"},
            ],
            "date": "2024",
            "publicationTitle": "Journal of Shoulder and Elbow Surgery",
            "DOI": "10.1016/j.jses.2024.01.001",
            "PMID": "38234156",
            "abstractNote": "BACKGROUND: Suture anchor fixation is critical for rotator cuff repair. We compared pull-out strength across 3 anchor types.",
            "collections": ["骨科"],
            "attachments": [{"path": "storage:SANDBOX001/SANDBOX001.pdf", "contentType": "application/pdf"}],
        },
        {
            "key": "SANDBOX002",
            "itemType": "journalArticle",
            "title": "Machine Learning Prediction of Anterior Cruciate Ligament Injury Risk in Athletes",
            "creators": [
                {"creatorType": "author", "firstName": "Wei", "lastName": "Zhang"},
            ],
            "date": "2023",
            "publicationTitle": "American Journal of Sports Medicine",
            "DOI": "10.1177/03635465231123456",
            "PMID": "37123456",
            "abstractNote": "PURPOSE: To develop and validate an ML model for predicting ACL injury risk using biomechanical and demographic features.",
            "collections": ["骨科"],
            "attachments": [{"path": "storage:SANDBOX002/SANDBOX002.pdf", "contentType": "application/pdf"}],
        },
        {
            "key": "SANDBOX003",
            "itemType": "journalArticle",
            "title": "Platelet-Rich Plasma Injection for Knee Osteoarthritis: Randomized Controlled Trial",
            "creators": [
                {"creatorType": "author", "firstName": "Sarah", "lastName": "Johnson"},
                {"creatorType": "author", "firstName": "Ahmed", "lastName": "Hassan"},
            ],
            "date": "2022",
            "publicationTitle": "Osteoarthritis and Cartilage",
            "DOI": "10.1016/j.joca.2022.03.012",
            "PMID": "35412345",
            "abstractNote": "OBJECTIVE: To evaluate the efficacy of PRP injections vs hyaluronic acid for symptomatic knee OA.",
            "collections": ["骨科"],
            "attachments": [],
        },
    ],
    "运动医学": [
        {
            "key": "SANDBOX004",
            "itemType": "journalArticle",
            "title": "Return to Sport Protocols After ACL Reconstruction: A Systematic Review",
            "creators": [
                {"creatorType": "author", "firstName": "Lisa", "lastName": "Park"},
                {"creatorType": "author", "firstName": "Tom", "lastName": "Nguyen"},
            ],
            "date": "2024",
            "publicationTitle": "Sports Health",
            "DOI": "10.1177/19417381241234567",
            "PMID": "38876543",
            "abstractNote": "DATA SOURCES: PubMed, Embase, Cochrane. 23 studies included. Return-to-sport criteria varied widely.",
            "collections": ["运动医学"],
            "attachments": [{"path": "storage:SANDBOX004/SANDBOX004.pdf", "contentType": "application/pdf"}],
        },
        {
            "key": "SANDBOX005",
            "itemType": "journalArticle",
            "title": "Ultrasound-Guided Percutaneous Achilles Tendon Repair in Acute Ruptures",
            "creators": [
                {"creatorType": "author", "firstName": "Carlos", "lastName": "Rodriguez"},
            ],
            "date": "2023",
            "publicationTitle": "Foot and Ankle International",
            "DOI": "10.1177/107110072311234",
            "PMID": "37234567",
            "abstractNote": "CASE SERIES: 28 patients. Primary outcomes: AOFAS score, time to weight-bearing, complications.",
            "collections": ["运动医学"],
            "attachments": [{"path": "storage:SANDBOX005/SANDBOX005.pdf", "contentType": "application/pdf"}],
        },
    ],
}

OCR_STATUSES = {
    "SANDBOX001": "pending",
    "SANDBOX002": "pending",
    "SANDBOX003": "nopdf",
    "SANDBOX004": "pending",
    "SANDBOX005": "pending",
}


def write_minimal_pdf(path: Path) -> None:
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n199\n"
        b"%%EOF\n"
    )
    path.write_bytes(pdf_content)


def build_vault() -> None:
    print(f"Generating sandbox vault at: {SANDBOX_VAULT}")

    vault = SANDBOX_VAULT
    if vault.exists():
        import shutil
        shutil.rmtree(vault)
    vault.mkdir(parents=True)

    system = vault / "99_System"
    pf = system / "PaperForge"
    exports = pf / "exports"
    ocr = pf / "ocr"
    zotero_link = system / "Zotero"

    resources = vault / "03_Resources"
    literature = resources / "Literature"
    control = resources / "LiteratureControl"
    records_root = control / "library-records"

    bases = vault / "05_Bases"
    opencode = vault / ".opencode"
    skills = opencode / "skills"
    cmd_dir = opencode / "command"

    dirs = [
        exports, ocr, zotero_link,
        literature, control, records_root,
        bases, skills, cmd_dir,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    (vault / "paperforge.json").write_text(
        json.dumps(PAPERFORGE_CFG, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (vault / ".env").write_text(
        "PADDLEOCR_API_TOKEN=sandbox_dummy_token_do_not_use\n"
        "PADDLEOCR_API_TOKEN_USER=\n"
        "PADDLEOCR_JOB_URL=https://api.paddleocr.com/v1/job\n"
        "PADDLEOCR_MODEL=docThinking\n"
        "PADDLEOCR_MAX_ITEMS=10\n",
        encoding="utf-8",
    )

    zotero_storage = zotero_link / "storage"
    zotero_storage.mkdir(exist_ok=True)

    for domain, items in ZOTERO_JSON_ITEMS.items():
        domain_records = records_root / domain
        domain_records.mkdir(exist_ok=True)

        export_items = []
        for item in items:
            key = item["key"]
            export_items.append(item)

            attachments = item.get("attachments", [])
            for att in attachments:
                att_path = att["path"]
                if att_path.startswith("storage:"):
                    storage_rel = att_path[len("storage:") :]
                    storage_path = zotero_storage / storage_rel
                    storage_path.parent.mkdir(parents=True, exist_ok=True)
                    write_minimal_pdf(storage_path)

            doi = item.get("DOI", "")
            year = item.get("date", "")
            title = item.get("title", "")
            ocr_status = OCR_STATUSES.get(key, "pending")
            has_pdf = "true" if attachments else "false"
            pdf_path_val = f"storage:{key}/{key}.pdf" if attachments else ""

            record_text = f"""---
zotero_key: "{key}"
domain: "{domain}"
title: "{title}"
year: "{year}"
doi: "{doi}"
has_pdf: {has_pdf}
pdf_path: "{pdf_path_val}"
fulltext_md_path: ""
recommend_analyze: true
analyze: false
do_ocr: false
ocr_status: "{ocr_status}"
deep_reading_status: "pending"
analysis_note: ""
---

# {title}

DOI: {doi}
Year: {year}

Abstract:
{item.get('abstractNote', '')}

---
*Generated sandbox record — not a real citation*
"""
            record_file = domain_records / f"{key}.md"
            record_file.write_text(record_text, encoding="utf-8")

            literature_note = f"""---
title: "{title}"
year: {year}
type: journal
category: "{domain}"
tags:
  - sandbox
  - test
pdf_link: "99_System/Zotero/storage/{key}/{key}.pdf"
---

# {title}

{item.get('abstractNote', '')}

---
*Generated sandbox literature note*
"""
            lit_dir = literature / domain
            lit_dir.mkdir(exist_ok=True)
            lit_file = lit_dir / f"{key} - {title[:30]}.md"
            lit_file.write_text(literature_note, encoding="utf-8")

        bbt_export = exports / f"{domain}.json"
        bbt_export.write_text(
            json.dumps({"items": export_items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    for domain in ZOTERO_JSON_ITEMS:
        base_file = bases / f"{domain}.base"
        base_file.write_text(
            f"""# GENERATED by PaperForge sandbox — test fixture
name: {domain}
type: ObsidianBase

views:
  - name: 全记录
    type: table
    filters: ""
    order: title, year

---
# {domain} Literature Base
""",
            encoding="utf-8",
        )

    lit_hub = bases / "Literature Hub.base"
    lit_hub.write_text(
        """# GENERATED by PaperForge sandbox — test fixture
name: Literature Hub
type: ObsidianBase

views:
  - name: 全记录
    type: table
    filters: ""
    order: title, year

---
# Literature Hub
Cross-domain overview.
""",
        encoding="utf-8",
    )

    readme = vault / "README.md"
    readme.write_text(
        """# Sandbox Vault

This is a completely sealed test vault for PaperForge Lite testing.
Do not use with a real Obsidian vault.

- 5 mock papers across 2 domains (骨科, 运动医学)
- 4 with PDFs, 1 without (no-pdf case)
- paperforge.json configured with default paths
- .env with dummy PaddleOCR credentials

Zotero storage: 99_System/Zotero/storage/
BBT exports: 99_System/PaperForge/exports/
Library records: 03_Resources/LiteratureControl/library-records/
Literature notes: 03_Resources/Literature/
Bases: 05_Bases/

DO NOT ADD REAL DATA HERE.
""",
        encoding="utf-8",
    )

    print(f"  vault/                    — root")
    print(f"  99_System/               — system dir (Zotero junction, PaperForge)")
    print(f"    Zotero/storage/         — 4 mock PDFs")
    print(f"    PaperForge/exports/      — 2 BBT JSON files (骨科.json, 运动医学.json)")
    print(f"    PaperForge/ocr/         — OCR output dir")
    print(f"  03_Resources/             — resources dir")
    print(f"    Literature/              — formal literature notes (5)")
    print(f"    LiteratureControl/       — control dir")
    print(f"      library-records/       — 5 library records")
    print(f"  05_Bases/                 — 3 Base files")
    print(f"  .opencode/                — skills + command stubs")
    print(f"  .env                      — dummy credentials")
    print(f"  paperforge.json          — default config")
    print(f"\nTotal: 5 papers, 4 PDFs, 2 domains")
    print(f"Sandbox vault ready at: {SANDBOX_VAULT}")


if __name__ == "__main__":
    build_vault()
