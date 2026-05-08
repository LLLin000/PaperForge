"""JNY-03: Daily workflow journey test.

Simulates an existing user: established vault with papers -> add new paper -> sync -> verify.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.journey


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _count_formal_notes(vault: Path) -> int:
    """Count formal note markdown files in Resources/Literature/."""
    lit_dir = vault / "Resources" / "Literature"
    if not lit_dir.exists():
        return 0
    return len(list(lit_dir.rglob("*.md")))


def _read_frontmatter(note_path: Path) -> dict:
    """Parse YAML frontmatter from a formal note."""
    content = note_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _compute_file_hash(note_path: Path) -> int:
    """Compute a simple content hash for a note file (frontmatter only)."""
    content = note_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) >= 3:
        # Hash the frontmatter portion
        return hash(parts[1])
    return hash(content)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_existing_user_adds_paper(
    journey_established_vault: tuple[Path, object],
    journey_cli_invoker: callable,
) -> None:
    """Existing user journey: count existing notes -> add new export -> sync -> verify count increased."""
    vault, builder = journey_established_vault

    # Isolation guard
    assert any(x in str(vault).lower() for x in ("tmp", "temp"))

    # -----------------------------------------------------------------------
    # Step 0: Sync first to normalize state (sync all existing exports)
    # -----------------------------------------------------------------------
    result = journey_cli_invoker(vault, ["sync"])
    assert result.returncode == 0, (
        f"Initial sync failed (exit {result.returncode}):\n  stdout: {result.stdout[:300]}\n  stderr: {result.stderr[:300]}"
    )

    lit_dir = vault / "Resources" / "Literature"

    # -----------------------------------------------------------------------
    # Step 1: Count existing formal notes after initial sync and record hashes
    # -----------------------------------------------------------------------
    initial_count = _count_formal_notes(vault)
    assert initial_count >= 1, f"Expected at least 1 existing formal note, found {initial_count}"

    existing_notes = list(lit_dir.rglob("*.md"))
    existing_hashes = {str(n.relative_to(vault)): _compute_file_hash(n) for n in existing_notes}

    # -----------------------------------------------------------------------
    # Step 2: Add a new BBT export with a unique key that won't conflict
    # -----------------------------------------------------------------------
    exports_dir = vault / "System" / "PaperForge" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    new_key = "JOURNEY003"
    new_export = {
        "items": [
            {
                "key": new_key,
                "itemKey": new_key,
                "itemType": "journalArticle",
                "title": "Advanced Techniques in Arthroscopic Surgery",
                "creators": [
                    {"creatorType": "author", "firstName": "Carol", "lastName": "Davis"},
                    {"creatorType": "author", "firstName": "Dan", "lastName": "Martinez"},
                ],
                "publicationTitle": "Arthroscopy: The Journal of Arthroscopic Surgery",
                "date": "2024-09-01",
                "DOI": "10.1016/j.arthro.2024.09.001",
                "attachments": [
                    {"path": f"storage:{new_key}/{new_key}.pdf", "contentType": "application/pdf"}
                ],
                "collections": ["orthopedic"],
            }
        ],
        "collections": {
            "orthopedic": {
                "name": "orthopedic",
                "parent": "",
                "items": [new_key],
            }
        },
    }
    new_export_path = exports_dir / "new_paper.json"
    new_export_path.write_text(json.dumps(new_export, indent=2), encoding="utf-8")

    # Create the Zotero storage directories + mock PDF for the new key
    for subdir in ("storage", ""):
        storage_dir = vault / "System" / "Zotero" / subdir / new_key
        storage_dir.mkdir(parents=True, exist_ok=True)
        (storage_dir / f"{new_key}.pdf").write_text("mock pdf content for new paper", encoding="utf-8")

    # -----------------------------------------------------------------------
    # Step 3: Run paperforge sync again
    # -----------------------------------------------------------------------
    result = journey_cli_invoker(vault, ["sync"])
    assert result.returncode == 0, (
        f"Second sync failed (exit {result.returncode}):\n  stdout: {result.stdout[:500]}\n  stderr: {result.stderr[:500]}"
    )

    # -----------------------------------------------------------------------
    # Step 4: Verify count of formal notes increased by 1
    # -----------------------------------------------------------------------
    new_count = _count_formal_notes(vault)
    assert new_count == initial_count + 1, (
        f"Expected {initial_count + 1} formal notes after second sync, found {new_count}"
    )

    # -----------------------------------------------------------------------
    # Step 5: Verify new note has correct frontmatter and existing notes unchanged
    # -----------------------------------------------------------------------
    current_notes = list(lit_dir.rglob("*.md"))

    # Find the newly created note
    new_note = None
    for n in current_notes:
        rel = str(n.relative_to(vault))
        if rel not in existing_hashes:
            new_note = n
            break

    assert new_note is not None, "Could not find newly created formal note"

    # Verify new note frontmatter
    fm = _read_frontmatter(new_note)
    assert fm.get("zotero_key") == new_key, f"Expected zotero_key {new_key}, got {fm.get('zotero_key')}"
    assert "domain" in fm and fm.get("domain"), f"Missing or empty domain in new note"
    assert "has_pdf" in fm, f"Missing has_pdf in new note"

    # Verify existing notes are unchanged (same frontmatter hash)
    for n in current_notes:
        rel = str(n.relative_to(vault))
        if rel in existing_hashes:
            current_hash = _compute_file_hash(n)
            assert current_hash == existing_hashes[rel], (
                f"Existing note {rel} was modified by sync!\n"
                f"  old hash: {existing_hashes[rel]}\n"
                f"  new hash: {current_hash}"
            )

    # -----------------------------------------------------------------------
    # Step 4: Verify count of formal notes increased by 1
    # -----------------------------------------------------------------------
    new_count = _count_formal_notes(vault)
    assert new_count == initial_count + 1, (
        f"Expected {initial_count + 1} formal notes after sync, found {new_count}"
    )

    # -----------------------------------------------------------------------
    # Step 5: Verify new note has correct frontmatter and existing notes unchanged
    # -----------------------------------------------------------------------
    new_existing_notes = list(lit_dir.rglob("*.md"))

    # Find the newly created note
    new_note = None
    for n in new_existing_notes:
        rel = str(n.relative_to(vault))
        if rel not in existing_hashes:
            new_note = n
            break

    assert new_note is not None, "Could not find newly created formal note"

    # Verify new note frontmatter
    fm = _read_frontmatter(new_note)
    assert fm.get("zotero_key") == new_key, f"Expected zotero_key {new_key}, got {fm.get('zotero_key')}"
    assert "domain" in fm and fm.get("domain"), f"Missing or empty domain in new note"
    assert "has_pdf" in fm, f"Missing has_pdf in new note"
    assert fm.get("ocr_status") in ("pending",), f"Expected pending ocr_status, got {fm.get('ocr_status')}"

    # Verify existing notes are unchanged (same frontmatter hash)
    for n in new_existing_notes:
        rel = str(n.relative_to(vault))
        if rel in existing_hashes:
            current_hash = _compute_file_hash(n)
            assert current_hash == existing_hashes[rel], (
                f"Existing note {rel} was modified by sync!\n"
                f"  old hash: {existing_hashes[rel]}\n"
                f"  new hash: {current_hash}"
            )
