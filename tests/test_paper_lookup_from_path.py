"""``paperforge paper-lookup --from-path`` — canonical identity resolver.

Ticket 07 step 5 semantic-boundary corrective: the plugin passes only the
host fact (the active vault-relative path); frontmatter, the canonical
index, and workspace-key derivation are Python authority. The thin client
never infers paper identity from files.
"""

from __future__ import annotations

import json
from pathlib import Path

from paperforge.commands.paper_lookup import resolve_paper_context
from paperforge.worker.asset_index import get_index_path
from tests.conftest import canonical_test_config

LIT = "03_Resources/Literature"


def _seed_vault(vault: Path) -> None:
    """Bootstrap a canonical vault with one indexed paper + a Base domain."""
    canonical_test_config(vault, resources_dir="03_Resources", literature_dir="Literature")
    ws = vault / LIT / "Cardio" / "ABCD1234 - Smith 2020"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "ABCD1234.md").write_text(
        "---\nzotero_key: ABCD1234\ntitle: Test Paper\n---\nbody\n",
        encoding="utf-8",
    )
    # Domain directory + its Base file (Base basename names the domain).
    (vault / LIT / "Cardio").mkdir(parents=True, exist_ok=True)
    (vault / "05_Bases").mkdir(parents=True, exist_ok=True)
    (vault / "05_Bases" / "Cardio.base").write_text("", encoding="utf-8")
    index_path = get_index_path(vault)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "zotero_key": "ABCD1234",
                        "title": "Test Paper",
                        "domain": "Cardio",
                        "note_path": f"{LIT}/Cardio/"
                        "ABCD1234 - Smith 2020/ABCD1234.md",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_resolves_note_path_to_canonical_identity(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_vault(vault)
    identity = resolve_paper_context(
        vault, f"{LIT}/Cardio/ABCD1234 - Smith 2020/ABCD1234.md"
    )
    assert identity["kind"] == "paper"
    assert identity["zotero_key"] == "ABCD1234"
    assert identity["entry"]["title"] == "Test Paper"


def test_resolves_note_frontmatter_even_when_path_is_not_in_index(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_vault(vault)
    ws = vault / LIT / "Cardio" / "ABCD1234 - Smith 2020"
    (ws / "renamed-note.md").write_text(
        "---\nzotero_key: ABCD1234\n---\nbody\n", encoding="utf-8"
    )
    identity = resolve_paper_context(
        vault, f"{LIT}/Cardio/ABCD1234 - Smith 2020/renamed-note.md"
    )
    assert identity["kind"] == "paper"
    assert identity["zotero_key"] == "ABCD1234"


def test_resolves_workspace_folder_key_against_the_index(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_vault(vault)
    pdf = vault / LIT / "Cardio" / "ABCD1234 - Smith 2020" / "paper.pdf"
    pdf.write_bytes(b"%PDF-")
    identity = resolve_paper_context(
        vault, f"{LIT}/Cardio/ABCD1234 - Smith 2020/paper.pdf"
    )
    assert identity["kind"] == "paper"
    assert identity["zotero_key"] == "ABCD1234"


def test_folder_key_without_index_entry_is_not_canonical_fail_closed(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_vault(vault)
    rogue = vault / LIT / "Cardio" / "ZZZZ9999 - Ghost"
    rogue.mkdir(parents=True)
    (rogue / "ghost.md").write_text("---\n---\n", encoding="utf-8")
    identity = resolve_paper_context(
        vault, f"{LIT}/Cardio/ZZZZ9999 - Ghost/ghost.md"
    )
    # The frozen invariant: filename-derived keys are NOT canonical —
    # unknown, never substituted.
    assert identity["kind"] == "unknown"


def test_resolves_base_basename_to_domain(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_vault(vault)
    identity = resolve_paper_context(vault, "05_Bases/Cardio.base")
    assert identity["kind"] == "domain"
    assert identity["domain"] == "Cardio"


def test_unknown_path_stays_unknown(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    _seed_vault(vault)
    identity = resolve_paper_context(vault, "somewhere/else/file.md")
    assert identity["kind"] == "unknown"
