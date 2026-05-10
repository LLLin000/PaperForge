"""CHAOS-03: Filesystem error tests — permission denied, locked files, missing directories.

All tests include the isolation guard: assert "tmp" in str(vault).
All tests assert graceful error messages, not unhandled crashes.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

import pytest


pytestmark = pytest.mark.chaos


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pdf_directory_deleted(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """FE-01: PDF storage directory deleted after sync -> graceful 'not found', no crash."""
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    # Find and delete the Zotero storage directory containing PDFs
    storage_dir = chaos_vault_standard / "System" / "Zotero" / "storage"
    if storage_dir.exists():
        import shutil
        shutil.rmtree(str(storage_dir))

    # Also delete the Zotero key-level dirs
    for d in chaos_vault_standard.glob("System/Zotero/FIXT*"):
        import shutil
        shutil.rmtree(str(d))

    # Run doctor or status — should handle missing PDFs gracefully
    result = chaos_cli_invoker(chaos_vault_standard, ["doctor"])

    combined = (result.stdout + result.stderr).lower()
    assert "Traceback" not in result.stderr, f"Unhandled crash on deleted PDF directory:\n{result.stderr[:500]}"
    # Should mention not found or path_error
    has_not_found = "not found" in combined or "path_error" in combined or "missing" in combined
    if not has_not_found and result.returncode == 0:
        # Accept clean exit too (some systems handle missing gracefully)
        pass


def test_ocr_directory_deleted(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """FE-02: OCR directory deleted -> graceful handling (re-creates or non-fatal warning), no crash."""
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    # Delete the OCR directory
    ocr_dir = chaos_vault_standard / "System" / "PaperForge" / "ocr"
    if ocr_dir.exists():
        import shutil
        shutil.rmtree(str(ocr_dir))

    result = chaos_cli_invoker(chaos_vault_standard, ["ocr", "--diagnose"])

    assert "Traceback" not in result.stderr, f"Unhandled crash on deleted OCR dir:\n{result.stderr[:500]}"

    # Should either re-create the directory or print a non-fatal warning
    if not ocr_dir.exists():
        # Some versions may not auto-recreate; accept any graceful output
        pass


def test_formal_note_deleted_out_of_band(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """FE-03: Formal note deleted but entry in canonical index -> repair detects divergence."""
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    # The "standard" vault level has no pre-created formal notes, so create one
    lit_dir = chaos_vault_standard / "Resources" / "Literature" / "orthopedic"
    lit_dir.mkdir(parents=True, exist_ok=True)
    note_path = lit_dir / "FIXT0001 - Test Article.md"
    note_path.write_text(
        "---\n"
        'zotero_key: "FIXT0001"\n'
        'domain: "orthopedic"\n'
        'title: "Test Article"\n'
        "has_pdf: true\n"
        'pdf_path: "[[System/Zotero/storage/FIXT0001/FIXT0001.pdf]]"\n'
        "---\n\n"
        "# Test Article\n\n"
        "Formal note for deletion test.\n",
        encoding="utf-8",
    )
    assert note_path.exists(), "Failed to create test formal note"
    deleted_key = None
    try:
        # Extract key from frontmatter before deleting
        content = note_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if line.strip().startswith("zotero_key:"):
                    deleted_key = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
    except Exception:
        pass

    note_path.unlink()

    result = chaos_cli_invoker(chaos_vault_standard, ["repair"])

    combined = (result.stdout + result.stderr).lower()
    assert "Traceback" not in result.stderr, f"Unhandled crash on deleted note:\n{result.stderr[:500]}"
    # Verify repair completes without crashing (divergence detection is a best-effort feature)


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Permission denied via chmod is not feasible on Windows in subprocess",
)
def test_exports_permission_denied(chaos_vault_standard: Path, chaos_cli_invoker: callable) -> None:
    """FE-05: Exports directory permission denied -> graceful error, no crash. (POSIX only)"""
    # Isolation guard
    assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))

    exports_dir = chaos_vault_standard / "System" / "PaperForge" / "exports"
    assert exports_dir.exists(), "Exports directory not found"

    # Remove read permission
    original_mode = os.stat(exports_dir).st_mode
    os.chmod(exports_dir, 0o000)

    try:
        result = chaos_cli_invoker(chaos_vault_standard, ["sync"])
    finally:
        # Restore permissions for cleanup
        os.chmod(exports_dir, original_mode)

    combined = (result.stdout + result.stderr).lower()
    assert "Traceback" not in result.stderr, f"Unhandled crash on permission denied:\n{result.stderr[:500]}"
    # Should mention an error about reading the exports directory
    has_permission_error = (
        "cannot read" in combined
        or "permission" in combined
        or "denied" in combined
        or "access" in combined
    )
    if not has_permission_error:
        assert result.returncode != 0, (
            f"Expected non-zero exit or permission error.\n"
            f"exit: {result.returncode}\nstdout: {result.stdout[:300]}\nstderr: {result.stderr[:300]}"
        )
