"""Chaos test fixtures — disposable vaults with isolation guards.

ALL chaos test vaults MUST use tmp_path and include the isolation assertion:
    assert "tmp" in str(vault)
"""

from __future__ import annotations

import json
import os
import random
import shutil
import stat
import string
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Windows-safe recursive removal
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
# File corruption helpers
# ---------------------------------------------------------------------------
def corrupt_json(path: Path) -> None:
    """Corrupt a JSON file by truncating the last 5 characters."""
    content = path.read_bytes()
    if len(content) > 10:
        path.write_bytes(content[:-5])


def corrupt_pdf(path: Path) -> None:
    """Corrupt a PDF by writing binary garbage to it."""
    garbage = bytes([random.randint(0, 255) for _ in range(64)])
    path.write_bytes(garbage)


def strip_frontmatter_fields(path: Path, fields: list[str]) -> None:
    """Remove specific frontmatter fields from a markdown file."""
    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return
    lines = parts[1].splitlines(keepends=True)
    filtered = [l for l in lines if not any(l.strip().startswith(f + ":") for f in fields)]
    parts[1] = "".join(filtered)
    path.write_text("---".join(parts), encoding="utf-8")


def create_broken_meta_json(path: Path) -> None:
    """Write invalid JSON to a meta.json file."""
    path.write_text('{"zotero_key": "FIXT0001", "ocr_status": "done",,}', encoding="utf-8")


def setup_vault_from_export(vault: Path, fixture_name: str) -> None:
    """Copy a specific fixture JSON into vault exports/.

    Args:
        vault: Vault root path.
        fixture_name: Basename of a JSON file in fixtures/zotero/.
    """
    from fixtures.vault_builder import FIXTURES_DIR

    src = FIXTURES_DIR / "zotero" / fixture_name
    if not src.exists():
        raise FileNotFoundError(f"Fixture not found: {src}")
    dst = vault / "System" / "PaperForge" / "exports" / fixture_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def chaos_vault(tmp_path: Path) -> Path:
    """Minimal disposable vault for chaos tests.

    Isolation guard: asserts "tmp" is in the vault path.
    """
    from fixtures.vault_builder import VaultBuilder

    builder = VaultBuilder()
    vault = Path(builder.build("minimal"))

    vault_lower = str(vault).lower()
    assert any(x in vault_lower for x in ("tmp", "temp")), (
        f"Isolation VIOLATION: vault path {vault} does not contain 'tmp' or 'Temp'"
    )

    yield vault

    if vault.exists():
        _force_rmtree(vault)


@pytest.fixture
def chaos_vault_standard(tmp_path: Path) -> Path:
    """Standard disposable vault (has BBT exports, PDFs, Zotero storage) for chaos tests.

    Isolation guard: asserts "tmp" is in the vault path.
    """
    from fixtures.vault_builder import VaultBuilder

    builder = VaultBuilder()
    vault = Path(builder.build("standard"))

    vault_lower = str(vault).lower()
    assert any(x in vault_lower for x in ("tmp", "temp")), (
        f"Isolation VIOLATION: vault path {vault} does not contain 'tmp' or 'Temp'"
    )

    yield vault

    if vault.exists():
        _force_rmtree(vault)


@pytest.fixture
def chaos_cli_invoker() -> callable:
    """Returns invoker function: chaos_cli_invoker(vault_path, args, env) -> CompletedProcess.

    Runs ``python -m paperforge --vault {vault} {args}`` via subprocess.
    """
    from fixtures.vault_builder import FIXTURES_DIR

    def _invoke(
        vault: Path,
        args: list[str],
        input_text: str | None = None,
        env: dict | None = None,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + list(args)

        base_env = os.environ.copy()
        base_env["PAPERFORGE_VAULT"] = str(vault)
        # Ensure PYTHONPATH includes repo root
        if "PYTHONPATH" in base_env:
            base_env["PYTHONPATH"] = str(FIXTURES_DIR.parent) + os.pathsep + base_env["PYTHONPATH"]
        else:
            base_env["PYTHONPATH"] = str(FIXTURES_DIR.parent)
        if env:
            base_env.update(env)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
            env=base_env,
        )
        return result

    return _invoke
