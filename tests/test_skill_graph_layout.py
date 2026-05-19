from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / "paperforge" / "skills" / "paperforge"


def test_skill_uses_atoms_and_molecules_directories() -> None:
    assert (SKILL_ROOT / "atoms").is_dir()
    assert (SKILL_ROOT / "molecules").is_dir()


def test_chart_reading_target_directory_exists() -> None:
    assert (SKILL_ROOT / "atoms" / "chart-reading").is_dir()
