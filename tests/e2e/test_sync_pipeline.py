"""E2E test: full sync pipeline — BBT JSON -> formal notes -> canonical index -> Base views."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e


def test_full_sync_pipeline(e2e_cli_invoker: tuple) -> None:
    """Verify that `paperforge sync` creates formal notes, canonical index, and Base views."""
    invoker, vault = e2e_cli_invoker

    result = invoker(["sync"])
    assert result.returncode == 0, f"Sync failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"

    # Formal notes exist in the orthopedic domain directory (in subdirectories)
    lit_dir = vault / "Resources" / "Literature"
    assert lit_dir.exists(), f"Literature directory not found: {lit_dir}"
    ortho_dir = lit_dir / "orthopedic"
    assert ortho_dir.exists(), f"Orthopedic domain directory not found: {ortho_dir}"

    # Formal notes are in subdirectories: FIXT0001 - Title/FIXT0001 - Title.md
    note_files = list(ortho_dir.rglob("*.md"))
    assert len(note_files) >= 1, f"No formal notes found in {ortho_dir}"

    # Canonical index exists
    index_path = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    assert index_path.exists(), f"Canonical index not found: {index_path}"

    # Parse index and verify structure
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert "items" in index, "Index missing 'items' key"
    assert len(index["items"]) >= 1, "Index has no items"

    entries = [e for e in index["items"] if e.get("domain") == "orthopedic"]
    assert len(entries) >= 1, "No orthopedic entries in index"
    entry = entries[0]
    assert "zotero_key" in entry, "Entry missing zotero_key"
    assert entry["domain"] == "orthopedic", f"Expected domain 'orthopedic', got '{entry['domain']}'"
    assert "note_path" in entry, "Entry missing note_path"
    assert entry["note_path"] and "orthopedic" in entry["note_path"], (
        f"note_path not pointing to orthopedic: {entry['note_path']}"
    )

    # Base views exist
    base_dir = vault / "Bases"
    assert base_dir.exists(), f"Base directory not found: {base_dir}"
    base_files = list(base_dir.glob("*.base"))
    assert len(base_files) >= 1, f"No .base files in {base_dir}"
