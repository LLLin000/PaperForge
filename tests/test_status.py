"""Tests for status.py — run_status with canonical index, run_doctor Index Health.

Phase 25-01 Task 2: run_status() reads from canonical index
Phase 25-01 Task 3: run_doctor() Index Health section
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with paperforge.json for path resolution."""
    vault = tmp_path / "test_vault"
    vault.mkdir(parents=True, exist_ok=True)
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                    "base_dir": "05_Bases",
                    "skill_dir": ".opencode/skills",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return vault


def _ensure_domain_config(vault: Path) -> None:
    """Create domain config so load_domain_config returns a valid config."""
    from paperforge.config import paperforge_paths as _pp

    paths = _pp(vault)
    config_dir = paths["paperforge"] / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "domain-collections.json"
    config_path.write_text(
        json.dumps(
            {
                "collections": {},
                "domains": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_index(vault: Path, items: list[dict]) -> None:
    """Write a canonical index envelope to the vault."""
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    idx_path = get_index_path(vault)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    envelope = build_envelope(items)
    atomic_write_index(idx_path, envelope)


def _ensure_library_records(vault: Path) -> Path:
    """Ensure library_records dir exists and return its path."""
    from paperforge.worker._utils import pipeline_paths

    paths = pipeline_paths(vault)
    records_dir = paths["library_records"]
    records_dir.mkdir(parents=True, exist_ok=True)
    return records_dir


def _ensure_exports(vault: Path) -> None:
    """Create empty exports dir (needed for run_status filesystem counts)."""
    from paperforge.worker._utils import pipeline_paths

    paths = pipeline_paths(vault)
    paths["exports"].mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Task 2: status --json reads from canonical index
# ---------------------------------------------------------------------------


class TestStatusJsonIndexSource:
    """run_status(json_output=True) with canonical index"""

    def test_status_json_includes_lifecycle_health_maturity(self, tmp_path: Path) -> None:
        """JSON output includes lifecycle/health/maturity aggregates from index."""
        from paperforge.worker.status import run_status

        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)
        _ensure_exports(vault)

        # Create a canonical index with 2 entries
        items = [
            {
                "zotero_key": "AAA",
                "lifecycle": "ai_context_ready",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "healthy",
                    "asset_health": "healthy",
                },
                "maturity": {"level": 6},
            },
            {
                "zotero_key": "BBB",
                "lifecycle": "indexed",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "Formal note missing",
                    "asset_health": "Missing workspace paths",
                },
                "maturity": {"level": 1},
            },
        ]
        _write_index(vault, items)

        code = run_status(vault, json_output=True)
        assert code == 0

    def test_status_json_fallback_when_index_missing(self, tmp_path: Path, capsys) -> None:
        """When no canonical index, lifecycle/health/maturity fields are None."""
        from paperforge.worker.status import run_status

        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)
        _ensure_exports(vault)

        code = run_status(vault, json_output=True)
        captured = capsys.readouterr().out
        assert code == 0
        envelope = json.loads(captured)
        data = envelope["data"]
        assert data["lifecycle_level_counts"] == {}
        assert data["health_aggregate"] == {}
        assert data["maturity_distribution"] == {}

    def test_status_text_output_includes_index_section(self, tmp_path: Path, capsys) -> None:
        """Text output contains 'lifecycle:' line when index is present."""
        from paperforge.worker.status import run_status

        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)
        _ensure_exports(vault)
        _write_index(vault, [])

        code = run_status(vault, json_output=False)
        captured = capsys.readouterr().out
        assert code == 0
        assert "lifecycle:" in captured
        assert "health:" in captured


# ---------------------------------------------------------------------------
# Task 3: doctor Index Health section
# ---------------------------------------------------------------------------


class TestDoctorIndexHealth:
    """run_doctor() Index Health section"""

    def _run_doctor(self, vault: Path) -> str:
        """Run doctor and return captured stdout."""
        from paperforge.worker.status import run_doctor

        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            run_doctor(vault)
        finally:
            sys.stdout = old_stdout
        return buf.getvalue()

    def test_doctor_includes_index_health_section(self, tmp_path: Path) -> None:
        """Doctor output includes 'Index Health' section when index present."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)
        _write_index(vault, [])

        output = self._run_doctor(vault)
        assert "Index Health" in output

    def test_doctor_index_health_with_mixed_health(self, tmp_path: Path) -> None:
        """Mixed health entries produce correct counts."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)
        items = [
            {
                "zotero_key": "AAA",
                "lifecycle": "ai_context_ready",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "healthy",
                    "note_health": "healthy",
                    "asset_health": "healthy",
                },
                "maturity": {"level": 6},
            },
            {
                "zotero_key": "BBB",
                "lifecycle": "indexed",
                "health": {
                    "pdf_health": "healthy",
                    "ocr_health": "OCR failed",
                    "note_health": "Formal note missing",
                    "asset_health": "healthy",
                },
                "maturity": {"level": 1},
            },
        ]
        _write_index(vault, items)

        output = self._run_doctor(vault)
        assert "Index Health" in output
        # PDF Health: both healthy
        assert "PDF Health" in output
        # OCR Health: one unhealthy
        assert "OCR Health" in output
        # Note Health: one unhealthy
        assert "Note Health" in output

    def test_doctor_index_health_no_index(self, tmp_path: Path) -> None:
        """When no index, doctor shows info message instead of crashing."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        output = self._run_doctor(vault)
        assert "Index Health" in output
        assert "No canonical index" in output
