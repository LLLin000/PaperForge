from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_MAIN = REPO_ROOT / "paperforge" / "plugin" / "main.js"


def test_plugin_install_bootstraps_pip_before_setup() -> None:
    """First-time plugin install must install the Python package before setup."""
    source = PLUGIN_MAIN.read_text(encoding="utf-8")
    assert "python -m paperforge" in source or "'-m', 'paperforge'" in source
    assert (
        '"-m", "pip", "install"' in source
        or "-m', 'pip', 'install'" in source
    ), "plugin install flow should bootstrap pip install before running paperforge setup"


def test_plugin_validates_setup_complete_against_paperforge_json() -> None:
    """setup_complete must be cross-checked against real vault config."""
    source = PLUGIN_MAIN.read_text(encoding="utf-8")
    assert "setup_complete" in source
    assert "paperforge.json" in source, "plugin should verify setup_complete against paperforge.json"


def test_setup_args_global_vault_before_subcommand() -> None:
    """Global --vault argument must appear before subcommand 'setup'."""
    source = PLUGIN_MAIN.read_text(encoding="utf-8")
    # Check that '--vault' appears before 'setup' in the setupArgs array
    vault_pos = source.find("'--vault'")
    setup_pos = source.find("'setup'")
    assert vault_pos > 0 and setup_pos > 0
    assert vault_pos < setup_pos, (
        f"'--vault' (pos {vault_pos}) must appear before 'setup' (pos {setup_pos}) "
        "in setupArgs, because --vault is a global paperforge argument"
    )
