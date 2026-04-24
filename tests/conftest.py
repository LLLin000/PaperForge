"""Test fixtures and helpers for PaperForge Lite smoke tests."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = REPO_ROOT / "tests" / "sandbox"
FIXTURE_VAULT = SANDBOX_DIR / "00_TestVault"
OCR_FIXTURE = SANDBOX_DIR / "ocr-complete" / "TSTONE001"
EXPORT_FIXTURE = SANDBOX_DIR / "exports" / "骨科.json"


def create_test_vault() -> Path:
    """Create a fresh test vault with necessary structure."""
    vault = FIXTURE_VAULT
    if vault.exists():
        shutil.rmtree(vault)
    vault.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    system_dir = vault / "99_System"
    pf_dir = system_dir / "PaperForge"
    exports_dir = pf_dir / "exports"
    ocr_dir = pf_dir / "ocr"
    resources_dir = vault / "03_Resources"
    literature_dir = resources_dir / "Literature"
    control_dir = resources_dir / "LiteratureControl"
    records_dir = control_dir / "library-records"
    base_dir = vault / "05_Bases"
    skill_dir = vault / ".opencode" / "skills" / "literature-qa" / "scripts"

    for d in [
        exports_dir, ocr_dir, literature_dir, records_dir, base_dir, skill_dir
    ]:
        d.mkdir(parents=True, exist_ok=True)

    # Create paperforge.json
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "system_dir": "99_System",
                "resources_dir": "03_Resources",
                "literature_dir": "Literature",
                "control_dir": "LiteratureControl",
                "base_dir": "05_Bases",
                "skill_dir": ".opencode/skills",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Create .env with PADDLEOCR_API_TOKEN
    env_path = pf_dir / ".env"
    env_path.write_text(
        "PADDLEOCR_API_TOKEN=test_token\n"
        "PADDLEOCR_JOB_URL=https://example.com/api\n",
        encoding="utf-8",
    )

    # Copy OCR fixture
    target_ocr = ocr_dir / "TSTONE001"
    if OCR_FIXTURE.exists():
        shutil.copytree(OCR_FIXTURE, target_ocr, dirs_exist_ok=True)

    # Copy export fixture
    if EXPORT_FIXTURE.exists():
        shutil.copy2(EXPORT_FIXTURE, exports_dir / "骨科.json")

    # Create library record for TSTONE001
    domain_dir = records_dir / "骨科"
    domain_dir.mkdir(parents=True, exist_ok=True)
    record_path = domain_dir / "TSTONE001.md"
    record_path.write_text(
        "---\n"
        'zotero_key: "TSTONE001"\n'
        'domain: "骨科"\n'
        'title: "Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair"\n'
        'year: "2024"\n'
        'doi: "10.1016/j.jse.2024.01.001"\n'
        'date: "2024-03-15"\n'
        'collection_path: ""\n'
        'has_pdf: true\n'
        'pdf_path: "[[99_System/Zotero/storage/TSTONE001/TSTONE001.pdf]]"\n'
        'fulltext_md_path: "[[99_System/PaperForge/ocr/TSTONE001/fulltext.md]]"\n'
        'recommend_analyze: true\n'
        'analyze: true\n'
        'do_ocr: true\n'
        'ocr_status: "done"\n'
        'deep_reading_status: "pending"\n'
        'analysis_note: ""\n'
        'collection_group:\n'
        '  - "骨科"\n'
        'collections:\n'
        '  - "骨科"\n'
        'collection_tags:\n'
        '  - "骨科"\n'
        'first_author: "John Smith"\n'
        'journal: "Journal of Shoulder and Elbow Surgery"\n'
        'impact_factor: ""\n'
        "---\n\n"
        "# Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair\n\n"
        "正式库控制记录。\n",
        encoding="utf-8",
    )

    # Create formal note for TSTONE001
    note_path = literature_dir / "骨科" / "TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "---\n"
        'title: "Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair"\n'
        'year: "2024"\n'
        'type: "journal"\n'
        'journal: "Journal of Shoulder and Elbow Surgery"\n'
        'impact_factor: "5.2"\n'
        'category: "骨科"\n'
        'tags:\n'
        '  - 文献阅读\n'
        '  - 骨科\n'
        'keywords: ["biomechanics", "rotator cuff"]\n'
        'pdf_link: "[[99_System/Zotero/storage/TSTONE001/TSTONE001.pdf]]"\n'
        "---\n\n"
        "# Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair\n\n"
        "## Abstract\n\n"
        "This study compares the biomechanical properties...\n",
        encoding="utf-8",
    )

    # Create Zotero storage with mock PDF
    zotero_dir = system_dir / "Zotero" / "storage" / "TSTONE001"
    zotero_dir.mkdir(parents=True, exist_ok=True)
    (zotero_dir / "TSTONE001.pdf").write_text("mock pdf content", encoding="utf-8")

    # Copy ld_deep.py to skill_dir (simulating deployment)
    ld_deep_src = REPO_ROOT / "paperforge" / "skills" / "literature-qa" / "scripts" / "ld_deep.py"
    if ld_deep_src.exists():
        shutil.copy2(ld_deep_src, skill_dir / "ld_deep.py")

    return vault


@pytest.fixture
def test_vault() -> Generator[Path, None, None]:
    """Pytest fixture providing a fresh test vault."""
    vault = create_test_vault()
    yield vault
    # Cleanup
    if FIXTURE_VAULT.exists():
        shutil.rmtree(FIXTURE_VAULT)


@pytest.fixture
def test_vault_preserved() -> Generator[Path, None, None]:
    """Pytest fixture providing a test vault without automatic cleanup."""
    vault = create_test_vault()
    yield vault
