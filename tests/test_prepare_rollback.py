"""Test rollback behavior in prepare_deep_reading.

Covers D-13..D-15: partial failure cleanup.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.conftest import create_test_vault


def _import_ld_deep(path: Path | None = None):
    """Import ld_deep.py using importlib, with Python 3.14 workaround."""
    if path is None:
        path = REPO_ROOT / "paperforge" / "skills" / "literature-qa" / "scripts" / "ld_deep.py"

    import importlib.util

    module_name = "_test_rollback_ld_deep"
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


class TestPrepareRollback:
    """Task 5: rollback behavior in prepare_deep_reading."""

    def test_prepare_rollback_on_figure_map_failure(self) -> None:
        """Mock build_figure_map to raise; assert no partial files remain."""
        vault = create_test_vault()
        module = _import_ld_deep()
        prepare_deep_reading = module.prepare_deep_reading

        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "TSTONE001"
        figure_map_path = ocr_dir / "figure-map.json"
        chart_type_map_path = ocr_dir / "chart-type-map.json"
        formal_note = vault / "03_Resources" / "Literature" / "骨科" / "TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair.md"

        # Remove pre-existing fixture files to test clean rollback
        if figure_map_path.exists():
            figure_map_path.unlink()
        if chart_type_map_path.exists():
            chart_type_map_path.unlink()

        original_note_text = formal_note.read_text(encoding="utf-8")

        with patch.object(module, "build_figure_map", side_effect=RuntimeError("mock figure map failure")):
            result = prepare_deep_reading(vault, "TSTONE001")

        assert result["status"] == "error", "should return error status"
        assert "mock figure map failure" in result["message"], "message should contain error"
        assert not figure_map_path.exists(), "figure-map.json should not exist (rollback or never created)"
        assert not chart_type_map_path.exists(), "chart-type-map.json should not exist"
        assert formal_note.read_text(encoding="utf-8") == original_note_text, "formal note should be restored"

    def test_prepare_rollback_on_scaffold_failure(self) -> None:
        """Mock ensure_study_section to raise; assert files cleaned up, note restored."""
        vault = create_test_vault()
        module = _import_ld_deep()
        prepare_deep_reading = module.prepare_deep_reading

        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "TSTONE001"
        figure_map_path = ocr_dir / "figure-map.json"
        chart_type_map_path = ocr_dir / "chart-type-map.json"
        formal_note = vault / "03_Resources" / "Literature" / "骨科" / "TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair.md"

        # Remove pre-existing fixture files to test clean rollback
        if figure_map_path.exists():
            figure_map_path.unlink()
        if chart_type_map_path.exists():
            chart_type_map_path.unlink()

        original_note_text = formal_note.read_text(encoding="utf-8")

        with patch.object(module, "ensure_study_section", side_effect=RuntimeError("mock scaffold failure")):
            result = prepare_deep_reading(vault, "TSTONE001")

        assert result["status"] == "error", "should return error status"
        assert "mock scaffold failure" in result["message"], "message should contain error"
        assert not figure_map_path.exists(), "figure-map.json should be deleted on rollback"
        assert not chart_type_map_path.exists(), "chart-type-map.json should be deleted on rollback"
        assert formal_note.read_text(encoding="utf-8") == original_note_text, "formal note should be restored"

    def test_prepare_success_no_rollback(self) -> None:
        """Normal flow: all files exist, note updated."""
        vault = create_test_vault()
        module = _import_ld_deep()
        prepare_deep_reading = module.prepare_deep_reading

        ocr_dir = vault / "99_System" / "PaperForge" / "ocr" / "TSTONE001"
        figure_map_path = ocr_dir / "figure-map.json"
        chart_type_map_path = ocr_dir / "chart-type-map.json"
        formal_note = vault / "03_Resources" / "Literature" / "骨科" / "TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair.md"

        original_note_text = formal_note.read_text(encoding="utf-8")

        result = prepare_deep_reading(vault, "TSTONE001")

        assert result["status"] == "ok", f"should succeed: {result.get('message')}"
        assert figure_map_path.exists(), "figure-map.json should exist"
        assert chart_type_map_path.exists(), "chart-type-map.json should exist"
        updated_text = formal_note.read_text(encoding="utf-8")
        assert "## 🔍 精读" in updated_text, "formal note should have 精读 section"
        assert updated_text != original_note_text, "formal note should be modified"
