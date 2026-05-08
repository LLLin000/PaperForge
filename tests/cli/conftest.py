"""CLI contract test fixtures — subprocess invoker, vault builder, mock OCR backend."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def vault_builder():
    """Fixture providing VaultBuilder instance connected to fixtures/ directory."""
    from fixtures.vault_builder import VaultBuilder
    return VaultBuilder()


@pytest.fixture
def cli_invoker(vault_builder):
    """Returns a function that runs paperforge CLI subprocess in a disposable vault.

    The returned function accepts:
        args: list[str] — CLI arguments (e.g., ["paths", "--json"])
        vault_level: str — vault completeness level (default "minimal")
        input_text: str | None — stdin text (for interactive commands)
        env: dict | None — additional env vars

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    vaults = []

    def _invoke(
        args: list[str],
        vault_level: str = "minimal",
        input_text: str | None = None,
        env: dict | None = None,
    ) -> subprocess.CompletedProcess:
        vault = vault_builder.build(vault_level)
        vaults.append(vault)

        cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args

        # Merge env with vault path so paperforge finds it
        base_env = {**os.environ.copy(), "PAPERFORGE_VAULT": str(vault)}
        if env:
            base_env.update(env)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            input=input_text,
            env=base_env,
        )
        return result

    yield _invoke

    # Cleanup vaults
    import shutil
    for v in vaults:
        if v.exists():
            shutil.rmtree(v, ignore_errors=True)


@pytest.fixture
def mock_ocr_backend():
    """Intercept HTTP calls to PaddleOCR API using responses library.

    Usage:
        def test_ocr_with_mock(mock_ocr_backend, cli_invoker):
            with mock_ocr_backend() as rsps:
                result = cli_invoker(["ocr", "--diagnose"])

    This fixture is context-managed — use it with 'with' statement.
    """
    import json
    from pathlib import Path
    import responses as _responses

    ocr_fixtures_dir = Path(__file__).resolve().parent.parent.parent / "fixtures" / "ocr"

    def _create_mock():
        rsps = _responses.RequestsMock(assert_all_requests_are_fired=False)

        # Submit endpoint — POST
        submit_data = json.loads(
            (ocr_fixtures_dir / "paddleocr_submit.json").read_text(encoding="utf-8")
        )
        rsps.add(
            _responses.POST,
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            json=submit_data,
            status=202,
        )

        # Poll endpoint — GET (returns done)
        poll_data = json.loads(
            (ocr_fixtures_dir / "paddleocr_poll_done.json").read_text(encoding="utf-8")
        )
        rsps.add(
            _responses.GET,
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/mock-job-001",
            json=poll_data,
            status=200,
        )

        # Result URL — GET
        result_data = json.loads(
            (ocr_fixtures_dir / "paddleocr_result.json").read_text(encoding="utf-8")
        )
        rsps.add(
            _responses.GET,
            "https://api.mock/results/mock-job-001",
            json=result_data,
            status=200,
        )

        return rsps

    yield _create_mock


@pytest.fixture
def snapshot_dir():
    """Return path to the snapshots directory."""
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent / "fixtures" / "snapshots"
