"""SetupChecker — validates preconditions before setup begins."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from paperforge.setup import SetupStepResult


class SetupChecker:
    """Validate all preconditions before any installation step."""

    MIN_PYTHON = (3, 10)

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

        # Check pip availability
        pip_path = shutil.which("pip") or shutil.which("pip3")
        details["pip_found"] = pip_path is not None
        if not pip_path:
            issues.append("pip not found in PATH")

        # Check vault directory
        details["vault_exists"] = self.vault.exists()
        if not self.vault.exists():
            issues.append(f"Vault directory not found: {self.vault}")

        # Check Zotero
        zotero_path = shutil.which("zotero") or shutil.which("zotero.exe")
        details["zotero_found"] = zotero_path is not None

        # Check Better BibTeX exports
        system_dir = self.vault / "99_System"
        exports_dir = system_dir / "PaperForge" / "exports"
        bbt_exists = exports_dir.exists() and len(list(exports_dir.glob("*.json"))) > 0
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
