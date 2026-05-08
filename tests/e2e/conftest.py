"""E2E test fixtures — temp vault builder, CLI invoker, mock OCR backend, Windows-safe cleanup."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Windows-safe recursive directory removal
# ---------------------------------------------------------------------------
def _force_rmtree(root: Path) -> None:
    """Remove a directory tree, handling Windows file-locking issues."""
    for dirpath, dirnames, filenames in os.walk(str(root)):
        for f in filenames:
            try:
                os.chmod(os.path.join(dirpath, f), stat.S_IWRITE)
            except OSError:
                pass
        for d in dirnames:
            try:
                os.chmod(os.path.join(dirpath, d), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(str(root), ignore_errors=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def vault_builder() -> object:
    """Session-scoped VaultBuilder instance connected to fixtures/ directory."""
    from fixtures.vault_builder import VaultBuilder

    return VaultBuilder()


@pytest.fixture
def temp_vault(vault_builder: object, tmp_path: Path) -> Path:
    """Function-scoped temp vault at 'standard' level."""
    vault = Path(vault_builder.build("standard"))
    yield vault
    if vault.exists():
        _force_rmtree(vault)


@pytest.fixture
def full_vault(vault_builder: object, tmp_path: Path) -> Path:
    """Function-scoped temp vault at 'full' level (includes OCR fixtures, formal notes)."""
    vault = Path(vault_builder.build("full"))
    yield vault
    if vault.exists():
        _force_rmtree(vault)


@pytest.fixture
def e2e_cli_invoker(temp_vault: Path) -> callable:
    """Returns (invoke_fn, vault_path) tuple for running CLI in temp vault.

    Usage:
        invoker, vault = e2e_cli_invoker
        result = invoker(["sync"])
    """
    vault = temp_vault

    def _invoke(
        args: list[str],
        input_text: str | None = None,
        env: dict | None = None,
    ) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + list(args)

        base_env = os.environ.copy()
        base_env["PAPERFORGE_VAULT"] = str(vault)
        if env:
            base_env.update(env)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            input=input_text,
            env=base_env,
        )
        return result

    return (_invoke, vault)
