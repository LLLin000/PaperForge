"""Journey test fixtures — temp vaults at specific onboarding stages with mock data.

All vault fixtures MUST include an isolation assertion to prevent accidental real-vault use.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Windows-safe recursive removal (reused from e2e/conftest.py)
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
# Helpers
# ---------------------------------------------------------------------------
def _edit_frontmatter_field(note_path: Path, field: str, value: str) -> None:
    """Edit a single frontmatter field in a formal note, preserving YAML structure."""
    content = note_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"Invalid frontmatter in {note_path}"
    lines = parts[1].splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{field}:"):
            lines[i] = f"{field}: {value}\n"
            found = True
            break
    if not found:
        # Append field
        lines.append(f"{field}: {value}\n")
    parts[1] = "".join(lines)
    note_path.write_text("---".join(parts), encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def journey_fresh_vault(tmp_path: Path) -> tuple[Path, object]:
    """A fresh vault at 'standard' level: config + dirs + env + exports + PDFs, NO formal notes yet.

    Returns:
        (vault_path, vault_builder) tuple so tests can add more data.
    """
    from fixtures.vault_builder import VaultBuilder

    builder = VaultBuilder()
    vault = Path(builder.build("standard"))

    # Isolation guard — must never point at a real vault
    vault_lower = str(vault).lower()
    assert any(x in vault_lower for x in ("tmp", "temp")), (
        f"Isolation VIOLATION: vault path {vault} does not contain 'tmp' or 'Temp'"
    )

    yield (vault, builder)

    if vault.exists():
        _force_rmtree(vault)


@pytest.fixture
def journey_established_vault(tmp_path: Path) -> tuple[Path, object]:
    """A fully-established vault at 'full' level: formal notes, canonical index, OCR fixtures,
    plus a second domain with an additional formal note.

    Returns:
        (vault_path, vault_builder) tuple so tests can inspect or extend.
    """
    from fixtures.vault_builder import VaultBuilder
    import json

    builder = VaultBuilder()
    vault = Path(builder.build("full"))

    # Isolation guard — must never point at a real vault
    vault_lower = str(vault).lower()
    assert any(x in vault_lower for x in ("tmp", "temp")), (
        f"Isolation VIOLATION: vault path {vault} does not contain 'tmp' or 'Temp'"
    )

    # Add a second domain with an additional formal note
    sports_dir = vault / "Resources" / "Literature" / "sports_medicine"
    sports_dir.mkdir(parents=True, exist_ok=True)

    second_note_content = (
        "---\n"
        'zotero_key: "FIXT0002"\n'
        'domain: "sports_medicine"\n'
        'title: "ACL Reconstruction: A Meta-Analysis of Outcomes"\n'
        'year: "2024"\n'
        'doi: "10.1177/ajsm.2024.06.001"\n'
        "has_pdf: true\n"
        'pdf_path: "[[System/Zotero/storage/FIXT0002/FIXT0002.pdf]]"\n'
        "recommend_analyze: true\n"
        "analyze: false\n"
        "do_ocr: false\n"
        'ocr_status: "pending"\n'
        'deep_reading_status: "pending"\n'
        'path_error: ""\n'
        'analysis_note: ""\n'
        "---\n\n"
        "# ACL Reconstruction: A Meta-Analysis of Outcomes\n\n"
        "Mock formal note for daily workflow testing.\n"
    )
    (sports_dir / "FIXT0002 - ACL Reconstruction A Meta-Analysis of Outcomes.md").write_text(
        second_note_content, encoding="utf-8"
    )

    # Also copy sports_medicine.json export to exports/ if not already there
    from fixtures.vault_builder import FIXTURES_DIR as fixtures_root

    sports_export = fixtures_root / "zotero" / "sports_medicine.json"
    if sports_export.exists():
        shutil.copy2(sports_export, vault / "System" / "PaperForge" / "exports" / "sports_medicine.json")

    # Update canonical index to reflect both domains
    index_path = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    index = {"items": [], "collections": {}, "generated_at": "2026-05-09T00:00:00+00:00"}
    index["items"] = [
        {
            "zotero_key": "FIXT0001",
            "domain": "orthopedic",
            "title": "Test Article",
            "note_path": "Resources/Literature/orthopedic/FIXT0001 - Test Article.md",
            "has_pdf": True,
            "ocr_status": "done",
            "analyze": False,
        },
        {
            "zotero_key": "FIXT0002",
            "domain": "sports_medicine",
            "title": "ACL Reconstruction: A Meta-Analysis of Outcomes",
            "note_path": "Resources/Literature/sports_medicine/FIXT0002 - ACL Reconstruction A Meta-Analysis of Outcomes.md",
            "has_pdf": True,
            "ocr_status": "pending",
            "analyze": False,
        },
    ]
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    yield (vault, builder)

    if vault.exists():
        _force_rmtree(vault)


@pytest.fixture
def journey_cli_invoker() -> callable:
    """Returns a function: invoker(vault_path, args, env_override) -> subprocess.CompletedProcess.

    Runs ``python -m paperforge --vault {vault} {args}`` via subprocess.
    Sets PAPERFORGE_VAULT in the subprocess environment.
    """
    from fixtures.vault_builder import FIXTURES_DIR

    def _invoke(
        vault: Path,
        args: list[str],
        input_text: str | None = None,
        env: dict | None = None,
    ) -> subprocess.CompletedProcess:
        cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + list(args)

        base_env = os.environ.copy()
        base_env["PAPERFORGE_VAULT"] = str(vault)
        # Ensure PYTHONPATH includes the repo root for fixture imports
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
            timeout=120,
            input=input_text,
            env=base_env,
        )
        return result

    return _invoke
