"""Audit test fixtures — vault builder, CLI invoker, golden vault, snapshot comparators.

These fixtures build real vaults from golden dataset fixtures and run the paperforge
CLI via subprocess — same L4 boundary as E2E tests. The purpose is to validate
that L1 mock expectations still match real pipeline output.
"""

from __future__ import annotations

import json
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
# Path helpers
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"
SNAPSHOTS_DIR = FIXTURES_DIR / "snapshots"
OCR_FIXTURES_DIR = FIXTURES_DIR / "ocr"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def vault_builder() -> object:
    """Session-scoped VaultBuilder instance connected to fixtures/ directory."""
    from fixtures.vault_builder import VaultBuilder
    return VaultBuilder()


@pytest.fixture
def cli_invoker(vault_builder: object) -> callable:
    """Returns a callable that runs paperforge CLI subprocess in a disposable vault.

    Unlike other conftest files, the default vault_level is "full" — audit tests
    need the richest golden dataset to validate cross-layer consistency.

    The returned callable accepts:
        args: list[str] — CLI arguments
        vault_level: str — vault completeness level (default "full")
        input_text: str | None — stdin text
        env: dict | None — additional env vars

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    vaults: list[Path] = []

    def _invoke(
        args: list[str],
        vault_level: str = "full",
        input_text: str | None = None,
        env: dict | None = None,
    ) -> subprocess.CompletedProcess:
        vault = Path(vault_builder.build(vault_level))
        vaults.append(vault)

        cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args

        base_env = {**os.environ.copy(), "PAPERFORGE_VAULT": str(vault)}
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

    yield _invoke

    for v in vaults:
        if v.exists():
            _force_rmtree(v)


@pytest.fixture
def golden_vault(vault_builder: object) -> tuple[callable, Path]:
    """Build a "full" vault, run the real sync pipeline, return (invoker, vault_path).

    This is the L4 golden dataset — any mock drift against L1 snapshots will be
    detected by comparing the output of this fixture against snapshot contracts.

    Returns:
        (invoke_fn, vault_path) tuple. The invoker function automatically targets
        this specific vault (omit vault_level — it is pre-set).
    """
    vault_paths: list[Path] = []

    def _setup() -> tuple[callable, Path]:
        # Build a fresh full vault for golden dataset comparison
        vault = Path(vault_builder.build("full"))
        vault_paths.append(vault)

        def _invoke_in_golden(
            args: list[str],
            input_text: str | None = None,
            env: dict | None = None,
        ) -> subprocess.CompletedProcess:
            cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args
            base_env = {**os.environ.copy(), "PAPERFORGE_VAULT": str(vault)}
            if env:
                base_env.update(env)
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                input=input_text,
                env=base_env,
            )

        # Run the real sync pipeline to create formal notes + index
        _invoke_in_golden(["sync"])

        return (_invoke_in_golden, vault)

    result = _setup()
    yield result

    for v in vault_paths:
        if v.exists():
            _force_rmtree(v)


@pytest.fixture
def snapshot_contracts() -> dict[str, object]:
    """Load all snapshot contracts from fixtures/snapshots/.

    Returns:
        dict mapping contract name -> parsed content (JSON for .json, YAML for .yaml)
    """
    contracts: dict[str, object] = {}

    if SNAPSHOTS_DIR.exists():
        for snap_file in SNAPSHOTS_DIR.rglob("*"):
            if not snap_file.is_file():
                continue
            rel = snap_file.relative_to(SNAPSHOTS_DIR)
            key = str(rel.as_posix())

            if snap_file.suffix == ".json":
                contracts[key] = json.loads(snap_file.read_text(encoding="utf-8"))
            elif snap_file.suffix in (".yaml", ".yml"):
                import yaml
                contracts[key] = yaml.safe_load(snap_file.read_text(encoding="utf-8"))

    return contracts


@pytest.fixture
def golden_dataset_manifest() -> dict:
    """Load and return fixtures/MANIFEST.json as a dict."""
    manifest_path = FIXTURES_DIR / "MANIFEST.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"fixtures": []}
