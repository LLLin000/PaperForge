"""VaultBuilder — factory for creating disposable test vaults from golden datasets.

Three completeness levels:
- minimal: tmp_path + paperforge.json + dirs + .env
- standard: minimal + BBT exports copied + mock PDFs + Zotero storage
- full: standard + OCR fixtures + formal notes + canonical index

Usage:
    builder = VaultBuilder()
    vault = builder.build("minimal")   # Returns Path to vault
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent


class VaultBuilder:
    """Creates disposable test vaults from golden dataset fixtures."""

    def __init__(self, fixtures_root: Path | None = None):
        self.fixtures_root = fixtures_root or FIXTURES_DIR

    def build(self, level: str = "minimal") -> Path:
        """Build a test vault at the given completeness level.

        Args:
            level: One of "minimal", "standard", "full"

        Returns:
            Path to the vault root directory.
        """
        vault = Path(tempfile.mkdtemp(prefix="pf_vault_"))
        self._create_config(vault)
        self._create_dirs(vault)
        self._create_env(vault)

        if level in ("standard", "full"):
            self._copy_exports(vault)
            self._copy_pdfs(vault)

        if level == "full":
            self._copy_ocr_fixtures(vault)
            self._create_formal_notes(vault)

        return vault

    def _create_config(self, vault: Path) -> None:
        """Create paperforge.json with default clean directory names."""
        config = {
            "version": "1.0.0",
            "system_dir": "System",
            "resources_dir": "Resources",
            "literature_dir": "Literature",
            "control_dir": "LiteratureControl",
            "base_dir": "Bases",
            "skill_dir": ".opencode/skills",
        }
        (vault / "paperforge.json").write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _create_dirs(self, vault: Path) -> None:
        """Create all required vault directories."""
        dirs = [
            "System/PaperForge/exports",
            "System/PaperForge/ocr",
            "System/PaperForge/indexes",
            "System/PaperForge/config",
            "System/Zotero/storage",
            "Resources/Literature",
            "Resources/LiteratureControl",
            "Bases",
            ".opencode/skills/literature-qa/scripts",
        ]
        for d in dirs:
            (vault / d).mkdir(parents=True, exist_ok=True)

    def _create_env(self, vault: Path) -> None:
        """Create .env with mock credentials."""
        env_content = (
            "PADDLEOCR_API_TOKEN=mock_test_token\n"
            "PADDLEOCR_JOB_URL=https://paddleocr.mock/api/v2/ocr/jobs\n"
        )
        (vault / "System/PaperForge/.env").write_text(env_content, encoding="utf-8")

    def _copy_exports(self, vault: Path) -> None:
        """Copy Zotero JSON fixtures into vault exports/."""
        exports_dir = vault / "System/PaperForge/exports"
        zotero_dir = self.fixtures_root / "zotero"
        if zotero_dir.exists():
            for f in zotero_dir.glob("*.json"):
                if f.name in ("empty.json", "malformed.json"):
                    continue  # skip edge cases for standard builds
                shutil.copy2(f, exports_dir / f.name)

    def _copy_pdfs(self, vault: Path) -> None:
        """Copy minimal PDFs into per-paper Zotero storage directories.

        Maps fixture keys to Zotero storage dirs:
        FIXT0001 -> System/Zotero/storage/FIXT0001/FIXT0001.pdf
        """
        pdfs = {
            "FIXT0001": "blank.pdf",
            "FIXT0002": "blank.pdf",
        }
        pdf_dir = self.fixtures_root / "pdf"
        for key, pdf_name in pdfs.items():
            src = pdf_dir / pdf_name
            if not src.exists():
                continue
            dst_dir = vault / "System/Zotero/storage" / key
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_dir / f"{key}.pdf")

    def _copy_ocr_fixtures(self, vault: Path) -> None:
        """Copy OCR fixture data into vault OCR directory."""
        target = vault / "System/PaperForge/ocr/FIXT0001"
        target.mkdir(parents=True, exist_ok=True)
        # Copy expected outputs
        ocr_dir = self.fixtures_root / "ocr"
        for fname in ("extracted_fulltext.md", "figure_map.json"):
            src = ocr_dir / fname
            if src.exists():
                shutil.copy2(src, target / fname)
        # Create meta.json
        (target / "meta.json").write_text(
            json.dumps(
                {
                    "zotero_key": "FIXT0001",
                    "ocr_status": "done",
                    "page_count": 2,
                    "generated_at": "2026-05-08T00:00:00+00:00",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _create_formal_notes(self, vault: Path) -> None:
        """Create formal note files for synced papers."""
        note_content = (
            "---\n"
            'zotero_key: "FIXT0001"\n'
            'domain: "orthopedic"\n'
            'title: "Test Article"\n'
            'year: "2024"\n'
            'doi: "10.1016/j.test.2024.01.001"\n'
            "has_pdf: true\n"
            'pdf_path: "[[System/Zotero/storage/FIXT0001/FIXT0001.pdf]]"\n'
            "recommend_analyze: true\n"
            "analyze: false\n"
            "do_ocr: false\n"
            'ocr_status: "pending"\n'
            'deep_reading_status: "pending"\n'
            'path_error: ""\n'
            'analysis_note: ""\n'
            "---\n\n"
            "# Test Article\n\n"
            "Mock formal note for testing.\n"
        )
        domain_dir = vault / "Resources/Literature/orthopedic"
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / "FIXT0001 - Test Article.md").write_text(
            note_content,
            encoding="utf-8",
        )
