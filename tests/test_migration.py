"""Tests for flat-to-workspace note migration (Phase 26, Plan 01).

Covers: migrate_to_workspace(), _build_entry() workspace-aware writing,
idempotency, backward compatibility, and run_index_refresh integration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with paperforge.json for path resolution."""
    vault = tmp_path / "test_vault"
    vault.mkdir(parents=True, exist_ok=True)
    pf_json = vault / "paperforge.json"
    pf_json.write_text(
        json.dumps(
            {
                "version": "1.2.0",
                "vault_config": {
                    "system_dir": "99_System",
                    "resources_dir": "03_Resources",
                    "literature_dir": "Literature",
                    "control_dir": "LiteratureControl",
                    "base_dir": "05_Bases",
                    "skill_dir": ".opencode/skills",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return vault


def _ensure_domain_config(vault: Path) -> None:
    """Create domain config so load_domain_config returns a valid configuration."""
    from paperforge.config import paperforge_paths as _pp

    paths = _pp(vault)
    config_dir = paths["paperforge"] / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "domain-collections.json"
    config_path.write_text(
        json.dumps(
            {
                "collections": {},
                "domains": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_canonical_index(vault: Path, items: list[dict]) -> None:
    """Write a canonical index envelope to the vault."""
    from paperforge.worker.asset_index import atomic_write_index, build_envelope, get_index_path

    idx_path = get_index_path(vault)
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    envelope = build_envelope(items)
    atomic_write_index(idx_path, envelope)


def _create_flat_note(vault: Path, key: str, domain: str, title_slug: str, content: str) -> Path:
    """Create a flat literature note at the legacy path and return the path."""
    from paperforge.worker._utils import pipeline_paths

    paths = pipeline_paths(vault)
    lit_dir = paths["literature"] / domain
    lit_dir.mkdir(parents=True, exist_ok=True)
    flat_path = lit_dir / f"{key} - {title_slug}.md"
    flat_path.write_text(content, encoding="utf-8")
    return flat_path


# ---------------------------------------------------------------------------
# Tests: migrate_to_workspace
# ---------------------------------------------------------------------------


class TestMigrateToWorkspace:
    """Tests for sync.migrate_to_workspace() — flat-to-workspace migration."""

    def _call_migrate(self, vault: Path) -> int:
        """Call migrate_to_workspace with proper paths."""
        from paperforge.worker._utils import pipeline_paths
        from paperforge.worker.sync import migrate_to_workspace

        paths = pipeline_paths(vault)
        return migrate_to_workspace(vault, paths)

    def test_migrate_flat_note_to_workspace(self, tmp_path: Path) -> None:
        """D-11, D-12: Flat note is copied to workspace dir, original preserved."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        # Create index with one entry
        _write_canonical_index(
            vault,
            [
                {
                    "zotero_key": "KEY001",
                    "domain": "骨科",
                    "title": "Test Paper One",
                }
            ],
        )

        # Create flat note
        content = "---\ntitle: Test Paper One\n---\n\n# Test Paper One\n\nSome content here."
        flat_path = _create_flat_note(vault, "KEY001", "骨科", "Test Paper One", content)

        # Migrate
        count = self._call_migrate(vault)

        assert count == 1, "Should have migrated 1 paper"

        # Check workspace dir exists
        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        workspace_dir = paths["literature"] / "骨科" / "KEY001 - Test Paper One"
        assert workspace_dir.is_dir(), "Workspace directory should exist"

        # Check main note in workspace has same content
        main_note = workspace_dir / "KEY001 - Test Paper One.md"
        assert main_note.exists(), "Main note should exist in workspace"
        assert main_note.read_text(encoding="utf-8") == content

        # Check flat note still exists (D-12: copy-not-move)
        assert flat_path.exists(), "Flat note should still exist (copy-not-move)"

    def test_migrate_extracts_deep_reading(self, tmp_path: Path) -> None:
        """D-13: ## 🔍 精读 section is extracted to deep-reading.md."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        _write_canonical_index(
            vault,
            [
                {
                    "zotero_key": "KEY002",
                    "domain": "骨科",
                    "title": "Paper With Deep Reading",
                }
            ],
        )

        # Create flat note with deep-reading content
        content = (
            "---\ntitle: Paper With Deep Reading\n---\n\n"
            "# Paper With Deep Reading\n\n"
            "Some intro text.\n\n"
            "## Normal Section\n\n"
            "Content here.\n\n"
            "## \U0001f50d \u7cbe\u8bfb\n\n"
            "### Pass 1: Overview\n\n"
            "This paper is about X.\n\n"
            "### Pass 2: Details\n\n"
            "The method section describes Y.\n\n"
        )
        _create_flat_note(vault, "KEY002", "骨科", "Paper With Deep Reading", content)

        # Migrate
        count = self._call_migrate(vault)
        assert count == 1

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        workspace_dir = paths["literature"] / "骨科" / "KEY002 - Paper With Deep Reading"

        # Main note preserves the deep-reading section (single source of truth)
        main_note = workspace_dir / "KEY002 - Paper With Deep Reading.md"
        main_content = main_note.read_text(encoding="utf-8")
        assert "## \U0001f50d \u7cbe\u8bfb" in main_content, "Main note preserves deep-reading section"
        assert "Pass 1: Overview" in main_content, "deep-reading content preserved"
        assert "Pass 2: Details" in main_content, "deep-reading content preserved"
        assert not (workspace_dir / "deep-reading.md").exists(), "No separate deep-reading.md should be created"

    def test_migrate_creates_ai_dir(self, tmp_path: Path) -> None:
        """ai/ directory is created inside workspace."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        _write_canonical_index(
            vault,
            [
                {
                    "zotero_key": "KEY003",
                    "domain": "运动医学",
                    "title": "Paper With AI Dir",
                }
            ],
        )

        content = "# Paper With AI Dir\n\nSome content."
        _create_flat_note(vault, "KEY003", "运动医学", "Paper With AI Dir", content)

        count = self._call_migrate(vault)
        assert count == 1

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        workspace_dir = paths["literature"] / "运动医学" / "KEY003 - Paper With AI Dir"
        ai_dir = workspace_dir / "ai"
        assert ai_dir.is_dir(), "ai/ directory should exist"
        # ai/ should be empty
        ai_contents = list(ai_dir.iterdir())
        assert len(ai_contents) == 0, "ai/ directory should be empty after migration"

    def test_migrate_idempotent_skips_existing(self, tmp_path: Path) -> None:
        """D-15: Already-migrated papers are skipped (return count = 0)."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        _write_canonical_index(
            vault,
            [
                {
                    "zotero_key": "KEY004",
                    "domain": "骨科",
                    "title": "Already Migrated",
                }
            ],
        )

        # Create flat note
        content = "# Already Migrated\n\nOriginal content."
        _create_flat_note(vault, "KEY004", "骨科", "Already Migrated", content)

        # First migration
        count1 = self._call_migrate(vault)
        assert count1 == 1

        # Add a content marker to verify it's not overwritten
        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        workspace_dir = paths["literature"] / "骨科" / "KEY004 - Already Migrated"
        marker = workspace_dir / "MARKER.txt"
        marker.write_text("do-not-overwrite", encoding="utf-8")

        # Second migration — should skip
        count2 = self._call_migrate(vault)
        assert count2 == 0, "Second migration should return 0 (nothing new)"

        # Verify marker still exists (workspace not overwritten)
        assert marker.exists(), "Workspace content should not be overwritten"
        assert marker.read_text(encoding="utf-8") == "do-not-overwrite"

    def test_migrate_returns_zero_when_no_index(self, tmp_path: Path) -> None:
        """Legacy flat notes still migrate even before the canonical index exists."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        content = (
            "---\n"
            "title: Legacy Flat Note\n"
            "zotero_key: LEG001\n"
            "do_ocr: false\n"
            "analyze: false\n"
            "---\n\n"
            "# Legacy Flat Note\n\n"
            "## 🔍 精读\n\n"
            "Legacy deep-reading content.\n"
        )
        _create_flat_note(vault, "LEG001", "骨科", "Legacy Flat Note", content)

        count = self._call_migrate(vault)
        assert count == 1

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        workspace_dir = paths["literature"] / "骨科" / "LEG001 - Legacy Flat Note"
        assert workspace_dir.is_dir()
        assert (workspace_dir / "LEG001 - Legacy Flat Note.md").exists()
        assert not (workspace_dir / "deep-reading.md").exists()
        main_content = (workspace_dir / "LEG001 - Legacy Flat Note.md").read_text(encoding="utf-8")
        assert "## 🔍 精读" in main_content

    def test_migrate_promotes_legacy_library_record_flags(self, tmp_path: Path) -> None:
        """Legacy library-record control flags are copied into the workspace note."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        content = "---\ntitle: Legacy Flags\nzotero_key: LEG002\ndo_ocr: false\nanalyze: false\n---\n\n# Legacy Flags\n"
        _create_flat_note(vault, "LEG002", "骨科", "Legacy Flags", content)

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        records_dir = paths["library_records"] / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        (records_dir / "LEG002.md").write_text(
            "---\nzotero_key: LEG002\ndo_ocr: true\nanalyze: true\n---\n",
            encoding="utf-8",
        )

        count = self._call_migrate(vault)
        assert count == 1

        workspace_note = paths["literature"] / "骨科" / "LEG002 - Legacy Flags" / "LEG002 - Legacy Flags.md"
        note_text = workspace_note.read_text(encoding="utf-8")
        assert 'do_ocr: "true"' in note_text
        assert 'analyze: "true"' in note_text

    def test_migrate_legacy_record_false_overrides_stale_true(self, tmp_path: Path) -> None:
        """Legacy library-record false values should override stale true flags in flat notes."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        content = "---\ntitle: Legacy False Flags\nzotero_key: LEG003\ndo_ocr: true\nanalyze: true\n---\n\n# Legacy False Flags\n"
        _create_flat_note(vault, "LEG003", "骨科", "Legacy False Flags", content)

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        records_dir = paths["library_records"] / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        (records_dir / "LEG003.md").write_text(
            "---\nzotero_key: LEG003\ndo_ocr: false\nanalyze: false\n---\n",
            encoding="utf-8",
        )

        count = self._call_migrate(vault)
        assert count == 1

        workspace_note = paths["literature"] / "骨科" / "LEG003 - Legacy False Flags" / "LEG003 - Legacy False Flags.md"
        note_text = workspace_note.read_text(encoding="utf-8")
        assert 'do_ocr: "false"' in note_text
        assert 'analyze: "false"' in note_text

    def test_migrate_uses_frontmatter_title_when_filename_is_noncanonical(self, tmp_path: Path) -> None:
        """Legacy files named only by key should still migrate via frontmatter title."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        lit_dir = paths["literature"] / "骨科"
        lit_dir.mkdir(parents=True, exist_ok=True)
        legacy_path = lit_dir / "LEG004.md"
        legacy_path.write_text(
            "---\ntitle: Noncanonical Legacy Name\nzotero_key: LEG004\n---\n\n# Noncanonical Legacy Name\n",
            encoding="utf-8",
        )

        count = self._call_migrate(vault)
        assert count == 1

        workspace_note = paths["literature"] / "骨科" / "LEG004 - Noncanonical Legacy Name" / "LEG004 - Noncanonical Legacy Name.md"
        assert workspace_note.exists()

    def test_migrate_reconciles_existing_workspace_flags_from_legacy_records(self, tmp_path: Path) -> None:
        """Already-migrated workspace notes are reconciled when they still mirror stale flat-note flags."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        content = "---\ntitle: Existing Workspace\nzotero_key: LEG005\ndo_ocr: true\nanalyze: true\n---\n\n# Existing Workspace\n"
        _create_flat_note(vault, "LEG005", "骨科", "Existing Workspace", content)

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        workspace_dir = paths["literature"] / "骨科" / "LEG005 - Existing Workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        workspace_note = workspace_dir / "LEG005 - Existing Workspace.md"
        workspace_note.write_text(content, encoding="utf-8")

        records_dir = paths["library_records"] / "骨科"
        records_dir.mkdir(parents=True, exist_ok=True)
        (records_dir / "LEG005.md").write_text(
            "---\nzotero_key: LEG005\ndo_ocr: false\nanalyze: false\n---\n",
            encoding="utf-8",
        )

        count = self._call_migrate(vault)
        assert count == 0
        updated_text = workspace_note.read_text(encoding="utf-8")
        assert 'do_ocr: "false"' in updated_text
        assert 'analyze: "false"' in updated_text


# ---------------------------------------------------------------------------
# Tests: _build_entry workspace-aware writing
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_build_entry_item() -> dict:
    """A minimal mock export item for _build_entry tests."""
    return {
        "key": "BLD001",
        "title": "Build Entry Test Paper",
        "authors": ["Test Author"],
        "abstract": "This is a test abstract for build entry.",
        "journal": "Test Journal",
        "year": "2024",
        "doi": "10.1234/test",
        "pmid": "12345678",
        "collections": ["骨科"],
        "attachments": [],
        "creators": [],
        "extra": "",
        "date": "2024",
        "DOI": "",
        "PMID": "",
    }


class TestBuildEntryWorkspaceWrite:
    """Tests for _build_entry() workspace-aware writing logic."""

    def _setup_vault(self, tmp_path: Path) -> tuple[Path, dict, Path]:
        """Set up a minimal vault + return (vault, paths, zotero_dir)."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        zotero_dir = vault / "99_System" / "Zotero"
        zotero_dir.mkdir(parents=True, exist_ok=True)

        return vault, paths, zotero_dir

    def _call_build_entry(
        self, vault: Path, item: dict, paths: dict, zotero_dir: Path
    ) -> dict:
        """Call _build_entry with the given item."""
        from paperforge.worker.asset_index import _build_entry

        return _build_entry(item, vault, paths, "骨科", zotero_dir)

    def test_build_entry_writes_to_workspace_after_migration(
        self, tmp_path: Path, mock_build_entry_item: dict
    ) -> None:
        """After migration, _build_entry writes to workspace path."""
        vault, paths, zotero_dir = self._setup_vault(tmp_path)

        from paperforge.worker._utils import slugify_filename

        key = mock_build_entry_item["key"]
        title_slug = slugify_filename(mock_build_entry_item["title"])

        # Pre-create the workspace dir (simulating migration happened)
        workspace_dir = paths["literature"] / "骨科" / f"{key} - {title_slug}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Call _build_entry
        entry = self._call_build_entry(vault, mock_build_entry_item, paths, zotero_dir)

        # Assert note is written to workspace main_note_path
        main_note_path = workspace_dir / f"{key} - {title_slug}.md"
        assert main_note_path.exists(), "Note should be written to workspace path"

        # Flat note path should NOT exist
        flat_path = paths["literature"] / "骨科" / f"{key} - {title_slug}.md"
        assert not flat_path.exists(), "Flat note should NOT be created when workspace exists"

        # Verify frontmatter is present in written note
        content = main_note_path.read_text(encoding="utf-8")
        assert content.startswith("---"), "Written note should have frontmatter"
        assert "title:" in content, "Frontmatter should contain title"
        assert "zotero_key:" in content, "Frontmatter should contain zotero_key"

        # Verify entry has workspace paths — config-resolved (Phase 46: PATH-01)
        lit_rel = str(paths["literature"].relative_to(vault)).replace("\\", "/")
        expected_root = f"{lit_rel}/骨科/{key} - {title_slug}/"
        assert entry["paper_root"] == expected_root
        assert entry["main_note_path"].startswith(f"{lit_rel}/骨科/{key} - {title_slug}/")
        assert entry["ai_path"] == f"{expected_root}ai/"

    def test_build_entry_flat_fallback_for_unmigrated_paper(
        self, tmp_path: Path, mock_build_entry_item: dict
    ) -> None:
        """When workspace dir does NOT exist, _build_entry creates it (Phase 38)."""
        vault, paths, zotero_dir = self._setup_vault(tmp_path)

        from paperforge.worker._utils import slugify_filename

        key = mock_build_entry_item["key"]
        title_slug = slugify_filename(mock_build_entry_item["title"])

        # Do NOT create workspace dir — simulate unmigrated paper
        flat_dir = paths["literature"] / "骨科"
        flat_dir.mkdir(parents=True, exist_ok=True)

        # Call _build_entry
        entry = self._call_build_entry(vault, mock_build_entry_item, paths, zotero_dir)

        # Phase 38: _build_entry ALWAYS creates workspace dir
        workspace_dir = flat_dir / f"{key} - {title_slug}"
        assert workspace_dir.exists(), "Workspace should be created"
        ws_note = workspace_dir / f"{key} - {title_slug}.md"
        assert ws_note.exists(), "Workspace note should exist"

        # Flat path should NOT exist (no legacy flat note was present)
        flat_path = flat_dir / f"{key} - {title_slug}.md"
        assert not flat_path.exists(), "Flat note should NOT be created (always workspace now)"

        # Verify frontmatter
        content = ws_note.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "title:" in content

    def test_build_entry_new_paper_creates_workspace(
        self, tmp_path: Path, mock_build_entry_item: dict
    ) -> None:
        """Brand new paper creates workspace dir directly (Phase 38)."""
        vault, paths, zotero_dir = self._setup_vault(tmp_path)

        from paperforge.worker._utils import slugify_filename

        key = mock_build_entry_item["key"]
        title_slug = slugify_filename(mock_build_entry_item["title"])

        # Create the parent literature dir (no flat note, no workspace)
        lit_dir = paths["literature"] / "骨科"
        lit_dir.mkdir(parents=True, exist_ok=True)

        # Call _build_entry
        entry = self._call_build_entry(vault, mock_build_entry_item, paths, zotero_dir)

        # Phase 38: workspace dir IS created by _build_entry for new papers
        workspace_dir = lit_dir / f"{key} - {title_slug}"
        assert workspace_dir.exists(), "Workspace dir should be auto-created by _build_entry"
        ws_note = workspace_dir / f"{key} - {title_slug}.md"
        assert ws_note.exists(), "Workspace note should exist"

        # Flat path should NOT exist
        flat_path = lit_dir / f"{key} - {title_slug}.md"
        assert not flat_path.exists(), "Flat note should NOT be created"


# ---------------------------------------------------------------------------
# Tests: run_index_refresh integration
# ---------------------------------------------------------------------------


class TestRunIndexRefreshIntegration:
    """Tests for migrate_to_workspace wiring inside run_index_refresh."""

    def test_run_index_refresh_calls_migrate(self, tmp_path: Path, monkeypatch) -> None:
        """run_index_refresh() calls migrate_to_workspace before build_index."""
        vault = _minimal_vault(tmp_path)
        _ensure_domain_config(vault)

        # Create an empty exports file so export loading doesn't crash
        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        exports_dir = paths["exports"]
        exports_dir.mkdir(parents=True, exist_ok=True)
        (exports_dir / "骨科.json").write_text("[]", encoding="utf-8")

        # Spy on migrate_to_workspace
        migrate_calls = []

        def _spy_migrate(v, p):
            migrate_calls.append((v, p))
            return 0

        monkeypatch.setattr("paperforge.worker.sync.migrate_to_workspace", _spy_migrate)

        # Stub build_index to avoid actual rebuild (which needs real exports)
        monkeypatch.setattr("paperforge.worker.asset_index.build_index", lambda *a, **kw: 0)

        # Call run_index_refresh
        from paperforge.worker.sync import run_index_refresh

        result = run_index_refresh(vault)

        # Assert migrate_to_workspace was called at least once
        assert len(migrate_calls) >= 1, "migrate_to_workspace should be called by run_index_refresh"
        assert result == 0
