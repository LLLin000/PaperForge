"""Test fixtures and helpers for PaperForge smoke tests."""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SANDBOX_DIR = REPO_ROOT / "tests" / "sandbox"
FIXTURE_VAULT = SANDBOX_DIR / "00_TestVault"
OCR_FIXTURE = SANDBOX_DIR / "ocr-complete" / "TSTONE001"
EXPORT_FIXTURE = SANDBOX_DIR / "exports" / "骨科.json"


def canonical_test_config(vault: Path, **overrides: str) -> None:
    """Create canonical paperforge.json through the #142 seam for a test vault.

    The fail-closed config authority rejects legacy/missing configs, so every
    test vault that reaches ``paperforge_paths`` / the seam must be bootstrapped
    here.
    """
    from paperforge.config import bootstrap_config, set_config

    bootstrap_config(vault)
    for key, value in overrides.items():
        set_config(vault, key, value)


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

    for d in [exports_dir, ocr_dir, literature_dir, records_dir, base_dir, skill_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Create canonical paperforge.json through the #142 seam (single writer)
    from paperforge.config import bootstrap_config, set_config

    bootstrap_config(vault)
    for _key, _value in {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
        "skill_dir": ".opencode/skills",
    }.items():
        set_config(vault, _key, _value)

    # Create .env with PADDLEOCR_API_TOKEN
    env_path = pf_dir / ".env"
    env_path.write_text(
        "PADDLEOCR_API_TOKEN=test_token\nPADDLEOCR_JOB_URL=https://example.com/api\n",
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
        "has_pdf: true\n"
        'pdf_path: "[[99_System/Zotero/storage/TSTONE001/TSTONE001.pdf]]"\n'
        'fulltext_md_path: "[[99_System/PaperForge/ocr/TSTONE001/fulltext.md]]"\n'
        "recommend_analyze: true\n"
        "analyze: true\n"
        "do_ocr: true\n"
        'ocr_status: "done"\n'
        'deep_reading_status: "pending"\n'
        'analysis_note: ""\n'
        "collection_group:\n"
        '  - "骨科"\n'
        "collections:\n"
        '  - "骨科"\n'
        "collection_tags:\n"
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
    note_path = (
        literature_dir
        / "骨科"
        / "TSTONE001.md"
    )
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "---\n"
        'title: "Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair"\n'
        'year: "2024"\n'
        'type: "journal"\n'
        'journal: "Journal of Shoulder and Elbow Surgery"\n'
        'impact_factor: "5.2"\n'
        'category: "骨科"\n'
        'zotero_key: "TSTONE001"\n'
        'domain: "骨科"\n'
        "analyze: true\n"
        "do_ocr: true\n"
        'ocr_status: "done"\n'
        "tags:\n"
        "  - 文献阅读\n"
        "  - 骨科\n"
        'keywords: ["biomechanics", "rotator cuff"]\n'
        'pdf_link: "[[99_System/Zotero/storage/TSTONE001/TSTONE001.pdf]]"\n'
        "---\n\n"
        "# Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair\n\n"
        "## Abstract\n\n"
        "This study compares the biomechanical properties...\n",
        encoding="utf-8",
    )

    # Create Zotero storage with mock PDF
    # PDF goes at Zotero/KEY/filename.pdf so resolve_pdf_path can find it
    zotero_dir = system_dir / "Zotero" / "TSTONE001"
    zotero_dir.mkdir(parents=True, exist_ok=True)
    (zotero_dir / "TSTONE001.pdf").write_text("mock pdf content", encoding="utf-8")

    # Also create in storage/ subdirectory for legacy path resolution
    storage_dir = system_dir / "Zotero" / "storage" / "TSTONE001"
    storage_dir.mkdir(parents=True, exist_ok=True)
    (storage_dir / "TSTONE001.pdf").write_text("mock pdf content", encoding="utf-8")

    # Copy ld_deep.py to skill_dir (simulating deployment)
    ld_deep_src = REPO_ROOT / "paperforge" / "skills" / "literature-qa" / "scripts" / "ld_deep.py"
    if ld_deep_src.exists():
        shutil.copy2(ld_deep_src, skill_dir / "ld_deep.py")

    return vault


@pytest.fixture(autouse=True)
def _hermetic_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    """#173/C1: every test runs against an in-memory fake keyring.

    The real OS keyring is never consulted — dev machines may hold real
    entries that would make credential tests non-hermetic.  Canonical
    credential env vars from the dev machine are cleared too; tests that
    need a credential set them explicitly or store into the fake.
    """
    from paperforge import credentials as _cred

    class _FakeKeyring:
        class errors:
            class PasswordDeleteError(Exception):
                pass

        def __init__(self) -> None:
            self._d: dict[tuple[str, str], str] = {}

        def get_password(self, service: str, username: str) -> str | None:
            return self._d.get((service, username))

        def set_password(self, service: str, username: str, password: str) -> None:
            self._d[(service, username)] = password

        def delete_password(self, service: str, username: str) -> None:
            if (service, username) not in self._d:
                raise self.errors.PasswordDeleteError()
            del self._d[(service, username)]

        def get_keyring(self) -> object:
            return "FakeKeyring"

    monkeypatch.setattr(_cred, "_keyring_module", None)
    monkeypatch.delenv("PAPERFORGE_CREDENTIAL_OCR__DEFAULT", raising=False)
    monkeypatch.delenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", raising=False)
    _cred.set_keyring_override(_FakeKeyring())
    yield
    _cred.set_keyring_override(None)


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

@pytest.fixture(scope="session")
def e2e_fixture_dir() -> Path:
    """Return the path to E2E test fixture directories."""
    return REPO_ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def synthetic_paper_paths(e2e_fixture_dir: Path) -> list[tuple[str, Path]]:
    """Return list of (paper_id, pdf_path) for synthetic E2E test papers."""
    papers_dir = e2e_fixture_dir / "papers"
    return [
        ("paper_a", papers_dir / "paper_a.pdf"),
        ("paper_b", papers_dir / "paper_b.pdf"),
        ("paper_c", papers_dir / "paper_c.pdf"),
    ]


def api_key_available() -> bool:
    """True when a real embedding API key is reachable (env or repo .env).

    Used to skip true E2E embed tests that require live API calls — CI can
    opt in by exporting VECTOR_DB_API_KEY / OPENAI_API_KEY.
    """
    import os

    if os.environ.get("VECTOR_DB_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        return True
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(("VECTOR_DB_API_KEY=", "OPENAI_API_KEY=")) and line.split("=", 1)[1].strip():
                return True
    return False
