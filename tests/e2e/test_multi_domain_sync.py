"""E2E test: multi-domain sync — separate collections sync to separate domain directories."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.e2e


def test_multi_domain_sync(e2e_cli_invoker: tuple) -> None:
    """Verify that syncing multiple Zotero collections creates domain-separated notes."""
    invoker, vault = e2e_cli_invoker

    result = invoker(["sync"])
    assert result.returncode == 0, f"First sync failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"

    lit_dir = vault / "Resources" / "Literature"

    # Both domain directories exist
    ortho_dir = lit_dir / "orthopedic"
    sports_dir = lit_dir / "sports_medicine"
    assert ortho_dir.exists(), f"Orthopedic domain directory not found: {ortho_dir}"
    assert sports_dir.exists(), f"Sports_medicine domain directory not found: {sports_dir}"

    # Both have formal notes (in subdirectories)
    ortho_notes = list(ortho_dir.rglob("*.md"))
    sports_notes = list(sports_dir.rglob("*.md"))
    assert len(ortho_notes) >= 1, f"No formal notes in orthopedic: {ortho_dir}"
    assert len(sports_notes) >= 1, f"No formal notes in sports_medicine: {sports_dir}"

    # Canonical index has items from both domains
    index_path = vault / "System" / "PaperForge" / "indexes" / "formal-library.json"
    assert index_path.exists(), f"Canonical index not found: {index_path}"

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(index["items"]) >= 2, f"Expected >= 2 items, got {len(index['items'])}"

    domains = {item["domain"] for item in index["items"]}
    assert "orthopedic" in domains, "Orthopedic domain missing from index"
    assert "sports_medicine" in domains, "Sports_medicine domain missing from index"

    # Verify note_path points to correct domain directories
    for item in index["items"]:
        assert "note_path" in item, f"Entry missing note_path: {item.get('zotero_key', '?')}"
        expected_prefix = f"Resources/Literature/{item['domain']}/"
        assert item["note_path"].startswith(
            expected_prefix
        ), f"note_path '{item['note_path']}' does not start with '{expected_prefix}'"

    # Sync is idempotent
    result2 = invoker(["sync"])
    assert result2.returncode == 0, f"Second sync failed:\nstdout:{result2.stdout}\nstderr:{result2.stderr}"

    index2 = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(index2["items"]) == len(index["items"]), (
        f"Item count changed after second sync: {len(index['items'])} -> {len(index2['items'])}"
    )
