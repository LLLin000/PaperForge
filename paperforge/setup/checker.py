"""SetupChecker — validates preconditions before setup begins."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from paperforge.setup import SetupStepResult


class SetupChecker:
    """Validate all preconditions before any installation step."""

    MIN_PYTHON = (3, 11)

    def __init__(self, vault: Path):
        self.vault = vault

    def run(self) -> SetupStepResult:
        """Run all precondition checks. Returns result with details."""
        issues: list[str] = []
        details: dict[str, Any] = {}

        # Check Python version
        py_version = sys.version_info[:2]
        details["python_version"] = f"{py_version[0]}.{py_version[1]}"
        if py_version < self.MIN_PYTHON:
            issues.append(f"Python {py_version[0]}.{py_version[1]} < {self.MIN_PYTHON[0]}.{self.MIN_PYTHON[1]}")

        # Check pip availability via python -m pip
        pip_ok = False
        try:
            import subprocess
            r = subprocess.run([sys.executable, "-m", "pip", "--version"],
                               capture_output=True, timeout=10)
            pip_ok = r.returncode == 0
        except Exception:
            pip_ok = False
        details["pip_found"] = pip_ok
        if not pip_ok:
            issues.append("pip not found via python -m pip")

        # Check vault directory
        details["vault_exists"] = self.vault.exists()
        if not self.vault.exists():
            issues.append(f"Vault directory not found: {self.vault}")

        # Check Zotero
        zotero_path = shutil.which("zotero") or shutil.which("zotero.exe")
        details["zotero_found"] = zotero_path is not None

        # Check Better BibTeX exports — via the canonical resolver, and
        # only when a config exists (a fresh vault has no exports yet and
        # must not fail the foundation checks on that account).
        from paperforge.config import ConfigError, load_config, resolve_paths

        try:
            load_config(self.vault)
            exports_dir = resolve_paths(self.vault)["exports"]
            bbt_exists = exports_dir.exists() and len(list(exports_dir.glob("*.json"))) > 0
        except (ConfigError, KeyError):
            # No canonical config yet = fresh vault: BBT exports are a
            # later (library) stage, not a foundation precondition.
            bbt_exists = True
        details["bbt_exports_found"] = bbt_exists

        if issues:
            return SetupStepResult(
                step="checker",
                ok=False,
                message=f"Precondition checks failed ({len(issues)} issue(s))",
                error="; ".join(issues),
                details=details,
            )

        return SetupStepResult(
            step="checker",
            ok=True,
            message="All preconditions met",
            details=details,
        )
