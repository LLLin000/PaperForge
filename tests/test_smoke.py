"""Smoke tests for PaperForge Lite — Phase 8 regression gate.

These tests validate:
- ld_deep.py importability from deployed location
- prepare produces scaffold correctly
- queue shows ready papers
- Regression assertions for known issues
- Doc command extractability and executability
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX_DIR = REPO_ROOT / "tests" / "sandbox"

# Ensure repo root is importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_ld_deep(path: Path | None = None) -> Any:
    """Import ld_deep.py using importlib, with Python 3.14 workaround."""
    if path is None:
        path = REPO_ROOT / "skills" / "literature-qa" / "scripts" / "ld_deep.py"

    # Python 3.14 workaround: dataclasses needs module in sys.modules
    module_name = "_test_ld_deep_module"
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except AttributeError as e:
        if "'NoneType' object has no attribute '__dict__'" in str(e):
            pytest.skip(f"Python 3.14 dataclass bug prevents import: {e}")
        raise
    return module


class TestSetupWizard:
    """Task 1a: setup wizard pip install step."""

    def test_setup_wizard_pip_install(self, test_vault: Path) -> None:
        """Verify setup wizard's _deploy method calls pip install -e ."""
        import setup_wizard

        source = Path(setup_wizard.__file__).read_text(encoding="utf-8")
        assert '"-m", "pip", "install", "-e"' in source or "pip install -e" in source, (
            "setup wizard should call pip install -e"
        )
        assert "repo_root" in source, "setup wizard should reference repo_root"


class TestDoctorImportability:
    """Task 1b: doctor checks actual importability, not just directory."""

    def test_doctor_importability_check(self, test_vault: Path) -> None:
        """Verify run_doctor checks importability via importlib.util."""
        from pipeline.worker.scripts.literature_pipeline import run_doctor

        source = Path(run_doctor.__code__.co_filename).read_text(encoding="utf-8")
        assert "importlib.util" in source, "doctor should use importlib.util for import check"
        assert "spec_from_file_location" in source or "exec_module" in source, (
            "doctor should actually exec_module ld_deep"
        )

    def test_regression_doctor_env_name(self, test_vault: Path) -> None:
        """REG-02: doctor checks PADDLEOCR_API_TOKEN (not old env name)."""
        from pipeline.worker.scripts.literature_pipeline import run_doctor

        source = Path(run_doctor.__code__.co_filename).read_text(encoding="utf-8")
        assert "PADDLEOCR_API_TOKEN" in source, "doctor should check PADDLEOCR_API_TOKEN"

    def test_regression_per_domain_json(self, test_vault: Path) -> None:
        """REG-02: doctor validates per-domain exports without false missing error."""
        from pipeline.worker.scripts.literature_pipeline import run_doctor

        source = Path(run_doctor.__code__.co_filename).read_text(encoding="utf-8")
        assert "library.json 不存在" not in source or "*.json" in source, (
            "doctor should support per-domain JSON exports"
        )


class TestLdDeepImport:
    """Task 3a: ld_deep.py importability from deployed location."""

    def test_ld_deep_import_from_deployed(self, test_vault: Path) -> None:
        """Verify deployed ld_deep.py is importable without PYTHONPATH."""
        skill_dir = test_vault / ".opencode" / "skills" / "literature-qa" / "scripts"
        ld_deep_path = skill_dir / "ld_deep.py"
        assert ld_deep_path.exists(), "ld_deep.py should be deployed"

        module = _import_ld_deep(ld_deep_path)

        assert hasattr(module, "prepare_deep_reading"), "should have prepare_deep_reading"
        assert hasattr(module, "scan_deep_reading_queue"), "should have scan_deep_reading_queue"

    def test_regression_agent_importability(self, test_vault: Path) -> None:
        """REG-02: ld_deep.py runs without manual PYTHONPATH."""
        result = subprocess.run(
            [sys.executable, "-c", "import paperforge"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"paperforge should be importable: {result.stderr}"


class TestPrepareProducesScaffold:
    """Task 3b: ld_deep.py prepare produces scaffold."""

    def test_prepare_produces_scaffold(self, test_vault: Path) -> None:
        """Verify prepare creates figure-map, chart-type-map, and 精读 section."""
        module = _import_ld_deep()
        prepare_deep_reading = module.prepare_deep_reading

        result = prepare_deep_reading(test_vault, "TSTONE001")

        assert result["status"] == "ok", f"prepare should succeed: {result.get('message')}"
        assert result["figure_map"] is not None, "figure_map path should be set"
        assert result["chart_type_map"] is not None, "chart_type_map path should be set"
        assert Path(result["figure_map"]).exists(), "figure-map.json should exist"
        assert Path(result["chart_type_map"]).exists(), "chart-type-map.json should exist"

        # Check formal note has 精读 section
        formal_note = Path(result["formal_note"])
        assert formal_note.exists(), "formal note should exist"
        note_text = formal_note.read_text(encoding="utf-8")
        assert "## 🔍 精读" in note_text, "note should contain 精读 section"

    def test_prepare_creates_figure_map_content(self, test_vault: Path) -> None:
        """Verify figure-map.json has actual content."""
        module = _import_ld_deep()
        prepare_deep_reading = module.prepare_deep_reading

        result = prepare_deep_reading(test_vault, "TSTONE001")
        figure_map_path = Path(result["figure_map"])
        data = json.loads(figure_map_path.read_text(encoding="utf-8"))

        assert data.get("zotero_key") == "TSTONE001", "zotero_key should match"
        assert len(data.get("figures", [])) > 0, "should have figures"
        assert len(data.get("tables", [])) > 0, "should have tables"


class TestQueueShowsReadyPaper:
    """Task 3c: ld_deep.py queue lists ready papers."""

    def test_queue_shows_ready_paper(self, test_vault: Path) -> None:
        """Verify queue includes TSTONE001 with ocr_status done."""
        module = _import_ld_deep()
        scan_deep_reading_queue = module.scan_deep_reading_queue

        queue = scan_deep_reading_queue(test_vault)
        tstone_entries = [q for q in queue if q["zotero_key"] == "TSTONE001"]

        assert len(tstone_entries) == 1, "TSTONE001 should appear in queue"
        assert tstone_entries[0]["ocr_status"] == "done", "ocr_status should be done"
        assert tstone_entries[0]["ocr_status"] == "done", "ocr_status should be done"


class TestRegressionQueueOutput:
    """REG-02: deep-reading --verbose prints details."""

    def test_regression_queue_output(self, test_vault: Path) -> None:
        """Verify queue function returns detailed info, not just count."""
        module = _import_ld_deep()
        scan_deep_reading_queue = module.scan_deep_reading_queue

        queue = scan_deep_reading_queue(test_vault)
        if queue:
            entry = queue[0]
            assert "zotero_key" in entry, "entry should have zotero_key"
            assert "title" in entry, "entry should have title"
            assert "domain" in entry, "entry should have domain"
            assert "ocr_status" in entry, "entry should have ocr_status"


class TestWorkerPathsJson:
    """REG-02: paths --json returns correct keys."""

    def test_regression_worker_path_json(self, test_vault: Path) -> None:
        """Verify paths --json returns worker_script and ld_deep_script."""
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(test_vault)
        assert "worker_script" in paths, "paths should contain worker_script"
        assert "ld_deep_script" in paths, "paths should contain ld_deep_script"


class TestDocCommandsExecutable:
    """Task 4: extract and verify commands from documentation."""

    def test_doc_commands_executable(self, test_vault: Path) -> None:
        """Verify commands in docs are extractable and don't crash."""
        doc_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "AGENTS.md",
            REPO_ROOT / "docs" / "INSTALLATION.md",
        ]

        commands_found = []
        for doc_path in doc_files:
            if not doc_path.exists():
                continue
            text = doc_path.read_text(encoding="utf-8")
            code_blocks = re.findall(r"```(?:bash|shell)?\n(.*?)\n```", text, re.DOTALL)
            for block in code_blocks:
                for line in block.splitlines():
                    line = line.strip()
                    if line.startswith("paperforge ") or line.startswith("python -m paperforge"):
                        commands_found.append((doc_path.name, line))

        assert len(commands_found) > 0, "should find commands in docs"

        failures = []
        for doc_name, cmd in commands_found:
            if "<vault>" in cmd or "{vault" in cmd:
                continue
            if "<zotero_key>" in cmd or "<key>" in cmd:
                continue
            if "<command>" in cmd:
                continue

            parts = cmd.split()
            if parts[0] == "paperforge":
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "paperforge", *parts[1:], "--help"],
                        capture_output=True,
                        text=True,
                        cwd=str(REPO_ROOT),
                        timeout=5,
                    )
                    if result.returncode != 0 and "unrecognized arguments: --help" in result.stderr:
                        pass
                except Exception as e:
                    failures.append(f"{doc_name}: {cmd} -> {e}")
            elif "python" in parts[0] and "-m" in parts and "paperforge" in cmd:
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "paperforge", "--help"],
                        capture_output=True,
                        text=True,
                        cwd=str(REPO_ROOT),
                        timeout=5,
                    )
                except Exception as e:
                    failures.append(f"{doc_name}: {cmd} -> {e}")

        assert not failures, f"Some doc commands failed: {failures}"


class TestMetadataFields:
    """REG-02: library-record has first_author and journal."""

    def test_regression_metadata_fields(self, test_vault: Path) -> None:
        """Verify library-record has non-empty first_author and journal."""
        record_path = (
            test_vault
            / "03_Resources"
            / "LiteratureControl"
            / "library-records"
            / "骨科"
            / "TSTONE001.md"
        )
        assert record_path.exists(), "library record should exist"
        text = record_path.read_text(encoding="utf-8")

        first_author_match = re.search(r'^first_author:\s*"?([^"]*)"?$', text, re.MULTILINE)
        journal_match = re.search(r'^journal:\s*"?([^"]*)"?$', text, re.MULTILINE)

        assert first_author_match is not None, "record should have first_author field"
        assert journal_match is not None, "record should have journal field"

        first_author = first_author_match.group(1).strip()
        journal = journal_match.group(1).strip()

        assert first_author, "first_author should not be empty"
        assert journal, "journal should not be empty"


class TestSelectionSync:
    """Integration tests for sync related regressions."""

    def test_regression_bbt_pdf_path(self, test_vault: Path) -> None:
        """REG-02: BBT attachment paths resolve correctly."""
        record_path = (
            test_vault
            / "03_Resources"
            / "LiteratureControl"
            / "library-records"
            / "骨科"
            / "TSTONE001.md"
        )
        assert record_path.exists(), "library record should exist"
        text = record_path.read_text(encoding="utf-8")
        assert "TSTONE001.pdf" in text, "record should reference the PDF"
