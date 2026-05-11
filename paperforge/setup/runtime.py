"""RuntimeInstaller -- pip install with version pinning."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable

from paperforge.core.errors import ErrorCode
from paperforge.setup import SetupStepResult


ProgressCallback = Callable[[str], None]


class RuntimeInstaller:
    """Install PaperForge Python package with version pinning."""

    def __init__(
        self,
        vault: Path,
        version: str | None = None,
        progress_callback: ProgressCallback | None = None,
    ):
        self.vault = vault
        self.version = version
        self.progress_callback = progress_callback

    def _log(self, message: str) -> None:
        if self.progress_callback:
            self.progress_callback(message)

    def _pip_install(self, package_spec: str) -> tuple[bool, str, str]:
        """Run pip install and return (ok, stdout, stderr)."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_spec],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return (result.returncode == 0, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            return (False, "", "pip install timed out after 120s")
        except Exception as e:
            return (False, "", str(e))

    def install(self) -> SetupStepResult:
        """Install paperforge via pip with optional version pin."""
        self._log("Installing PaperForge...")

        if self.version:
            tag = self.version if self.version.startswith("v") else f"v{self.version}"
            package_spec = f"git+https://github.com/LLLin000/PaperForge.git@{tag}"
        else:
            package_spec = "git+https://github.com/LLLin000/PaperForge.git"

        ok, stdout, stderr = self._pip_install(package_spec)

        if ok:
            return SetupStepResult(
                step="runtime_installer",
                ok=True,
                message=(f"PaperForge installed successfully{(' (' + self.version + ')') if self.version else ''}"),
                details={"version": self.version or "latest", "stdout": stdout[:500]},
            )
        else:
            error_code = ErrorCode.INTERNAL_ERROR
            if "pip" in stderr.lower():
                error_code = ErrorCode.INTERNAL_ERROR
            elif "connection" in stderr.lower() or "timeout" in stderr.lower():
                error_code = ErrorCode.INTERNAL_ERROR

            return SetupStepResult(
                step="runtime_installer",
                ok=False,
                message="Failed to install PaperForge",
                error=f"[{error_code.value}] {stderr[:500]}",
                details={"version": self.version or "latest", "stderr": stderr[:500]},
            )

    def check_installed(self) -> bool:
        """Check if paperforge is already installed."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from paperforge import __version__; print(__version__)",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return False
