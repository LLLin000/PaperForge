"""Integration tests for incremental refresh across worker operations.

Covers:
1. refresh_index_entry preserves unrelated entries, appends new keys, legacy fallback
2. Worker call sites (OCR, deep-reading, repair) trigger incremental refresh
3. Workspace path fields in index entries

Uses real filesystem setup with minimal vaults (same pattern as test_asset_index.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers (matching test_asset_index.py pattern)
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


def _pipeline_paths(vault: Path) -> dict:
    """Get pipeline paths for a test vault."""
    from paperforge.worker._utils import pipeline_paths

    return pipeline_paths(vault)


def _ensure_domain_config(vault: Path, domains: list | None = None) -> None:
    """Create domain config so load_domain_config returns a valid configuration.

    Args:
        vault: Path to the vault root.
        domains: Optional list of domain dicts (export_file, domain pairs).
                 Defaults to empty domain list.
    """
    from paperforge.config import paperforge_paths as _pp

    paths = _pp(vault)
    config_dir = paths["paperforge"] / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "domain-collections.json"
    config_path.write_text(
        json.dumps(
            {
                "collections": {},
                "domains": domains or [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _make_export_item(key: str, title: str) -> dict:
    """Create a minimal BBT export item dict for test fixtures."""
    return {
        "key": key,
        "title": title,
        "creators": [],
        "collections": [],
        "attachments": [],
        "doi": "",
        "pmid": "",
        "date": "",
        "extra": "",
        "abstractNote": "",
        "publicationTitle": "",
        "itemType": "journalArticle",
    }


def _setup_incremental_vault(
    tmp_path: Path, items: list[dict], domain: str = "test_domain"
) -> Path:
    """Set up a vault with a pre-built envelope index and matching BBT export.

    Creates:
        - paperforge.json
        - Domain config with a single domain mapping
        - BBT export file in exports/
        - Literature domain directory (so formal notes can be written)
        - paperforge index directory

    Returns:
        Path to the vault root.
    """
    from paperforge.worker.asset_index import (
        build_envelope,
        get_index_path,
    )

    vault = _minimal_vault(tmp_path)
    _ensure_domain_config(vault, [{"export_file": f"{domain}.json", "domain": domain}])
    paths = _pipeline_paths(vault)

    # Create exports directory with test BBT export file
    exports_dir = paths["exports"]
    exports_dir.mkdir(parents=True, exist_ok=True)
    export_path = exports_dir / f"{domain}.json"
    export_path.write_text(json.dumps(items, indent=2), encoding="utf-8")

    # Create literature domain directory (needed for formal note writing)
    lit_dir = paths["literature"] / domain
    lit_dir.mkdir(parents=True, exist_ok=True)

    # Create paperforge index directory
    index_path = get_index_path(vault)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    return vault


def _write_index(vault: Path, items: list[dict]) -> None:
    """Write an envelope-format index file for testing."""
    from paperforge.worker.asset_index import build_envelope, get_index_path

    envelope = build_envelope(items)
    index_path = get_index_path(vault)
    index_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: refresh_index_entry core behavior
# ---------------------------------------------------------------------------


class TestIncrementalRefreshBehavior:
    """Core behavior of refresh_index_entry with real filesystem setup."""

    def test_incremental_refresh_preserves_unrelated_entries(self, tmp_path: Path) -> None:
        """refresh_index_entry only modifies the targeted entry's fields."""
        items = [
            _make_export_item("AAA", "Paper A"),
            _make_export_item("BBB", "Paper B"),
            _make_export_item("CCC", "Paper C"),
        ]
        vault = _setup_incremental_vault(tmp_path, items)

        # Pre-built index with traceable fields only
        existing = [{"zotero_key": it["key"], "title": it["title"]} for it in items]
        _write_index(vault, existing)

        from paperforge.worker.asset_index import read_index, refresh_index_entry

        # Refresh entry AAA
        refresh_index_entry(vault, "AAA")

        # Read back
        result = read_index(vault)
        assert isinstance(result, dict)
        result_items = result["items"]
        assert len(result_items) == 3

        # AAA should have been updated (has more fields now from export build)
        aaa = next(e for e in result_items if e["zotero_key"] == "AAA")
        assert aaa["has_pdf"] is False
        assert aaa["ocr_status"] == "pending"

        # BBB and CCC should keep their original data (unchanged)
        bbb = next(e for e in result_items if e["zotero_key"] == "BBB")
        assert bbb == {"zotero_key": "BBB", "title": "Paper B"}

        ccc = next(e for e in result_items if e["zotero_key"] == "CCC")
        assert ccc == {"zotero_key": "CCC", "title": "Paper C"}

    def test_incremental_refresh_adds_new_key(self, tmp_path: Path) -> None:
        """refresh_index_entry appends a new key not yet in the index."""
        items = [
            _make_export_item("AAA", "Paper A"),
            _make_export_item("BBB", "Paper B"),
        ]
        vault = _setup_incremental_vault(tmp_path, items)

        # Pre-built index with only AAA
        _write_index(vault, [{"zotero_key": "AAA", "title": "Paper A"}])

        from paperforge.worker.asset_index import read_index, refresh_index_entry

        # Refresh BBB (not yet in index)
        refresh_index_entry(vault, "BBB")

        result = read_index(vault)
        assert isinstance(result, dict)
        keys = [e["zotero_key"] for e in result["items"]]
        assert "AAA" in keys
        assert "BBB" in keys
        assert len(result["items"]) == 2

    def test_incremental_refresh_fallback_on_legacy(self, tmp_path: Path) -> None:
        """refresh_index_entry falls back to build_index when index is legacy format."""
        from paperforge.worker.asset_index import (
            build_envelope,
            get_index_path,
            is_legacy_format,
            read_index,
            refresh_index_entry,
        )

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)

        # Write legacy format index (bare list, not envelope)
        index_path = get_index_path(vault)
        legacy_data = [{"zotero_key": "AAA", "title": "Paper A"}]
        index_path.write_text(json.dumps(legacy_data, indent=2), encoding="utf-8")

        # Verify it's detected as legacy
        pre_data = read_index(vault)
        assert is_legacy_format(pre_data)

        # Refresh triggers detection and fallback
        refresh_index_entry(vault, "AAA")

        # Verify index is now envelope format
        result = read_index(vault)
        assert isinstance(result, dict)
        assert result.get("schema_version") is not None
        assert "items" in result

    def test_incremental_refresh_skips_unknown_key(self, tmp_path: Path) -> None:
        """refresh_index_entry with a key not in any export returns False."""
        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        _write_index(vault, [{"zotero_key": "AAA", "title": "Paper A"}])

        from paperforge.worker.asset_index import refresh_index_entry

        result = refresh_index_entry(vault, "UNKNOWN")
        assert result is False  # No action taken, key not found


# ---------------------------------------------------------------------------
# Tests: Worker call sites
# ---------------------------------------------------------------------------


class TestWorkerCallSites:
    """Structural checks that workers call incremental refresh."""

    def test_ocr_calls_incremental_not_full(self) -> None:
        """OCR post-processing calls refresh_index_entry, not only run_index_refresh."""
        source = Path("paperforge/worker/ocr.py").read_text(encoding="utf-8")
        assert "refresh_index_entry" in source, (
            "ocr.py must import and call refresh_index_entry for incremental refresh"
        )

    def test_deep_reading_calls_incremental(self) -> None:
        """deep_reading.py calls refresh_index_entry."""
        source = Path("paperforge/worker/deep_reading.py").read_text(encoding="utf-8")
        assert "refresh_index_entry" in source, (
            "deep_reading.py must import and call refresh_index_entry"
        )

    def test_repair_calls_incremental(self) -> None:
        """repair.py calls refresh_index_entry."""
        source = Path("paperforge/worker/repair.py").read_text(encoding="utf-8")
        assert "refresh_index_entry" in source, (
            "repair.py must import and call refresh_index_entry for per-paper fixes"
        )


# ---------------------------------------------------------------------------
# Tests: Workspace path fields
# ---------------------------------------------------------------------------


class TestWorkspacePaths:
    """Workspace path fields in index entries."""

    def test_workspace_paths_in_entry(self, tmp_path: Path) -> None:
        """Each entry in the built index contains all 5 workspace path fields."""
        from paperforge.worker.asset_index import (
            build_envelope,
            get_index_path,
            read_index,
            refresh_index_entry,
        )

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)

        # Seed index with minimal entry, then refresh
        _write_index(vault, [{"zotero_key": "AAA", "title": "Paper A"}])
        refresh_index_entry(vault, "AAA")

        result = read_index(vault)
        entry = result["items"][0]

        # All 5 workspace path fields must be present (Phase 22, D-12)
        assert "paper_root" in entry
        assert "main_note_path" in entry
        assert "fulltext_path" in entry
        assert "deep_reading_path" in entry
        assert "ai_path" in entry

        # Paths should be non-empty strings
        assert isinstance(entry["paper_root"], str) and len(entry["paper_root"]) > 0
        assert isinstance(entry["main_note_path"], str) and len(entry["main_note_path"]) > 0
        assert isinstance(entry["fulltext_path"], str) and len(entry["fulltext_path"]) > 0
        assert isinstance(entry["deep_reading_path"], str) and len(entry["deep_reading_path"]) > 0
        assert isinstance(entry["ai_path"], str) and len(entry["ai_path"]) > 0

    def test_path_fields_consistent_after_incremental(self, tmp_path: Path) -> None:
        """After incremental refresh, the targeted entry has consistent path fields."""
        from paperforge.worker.asset_index import (
            read_index,
            refresh_index_entry,
        )

        items = [_make_export_item("AAA", "测试论文")]
        vault = _setup_incremental_vault(tmp_path, items)

        _write_index(vault, [{"zotero_key": "AAA", "title": "测试论文"}])
        refresh_index_entry(vault, "AAA")

        result = read_index(vault)
        entry = result["items"][0]

        # paper_root should be the base directory for all other paths
        paper_root = entry["paper_root"]
        assert paper_root.endswith("/"), "paper_root should end with /"

        # Other paths should be within paper_root (or at least reference it)
        main_note = entry["main_note_path"]
        assert isinstance(main_note, str)

        # Path fields should be consistent: using relative vault paths
        assert "\\" not in paper_root, "paths should use forward slashes"
        assert "\\" not in entry["main_note_path"]
        assert "\\" not in entry["fulltext_path"]
        assert "\\" not in entry["deep_reading_path"]
        assert "\\" not in entry["ai_path"]


# ---------------------------------------------------------------------------
# Tests: Derived state fields (Phase 24)
# ---------------------------------------------------------------------------


class TestDerivedStateFields:
    """Lifecycle, health, maturity, next_step fields in index entries."""

    def test_all_four_fields_present_after_full_build(self, tmp_path: Path) -> None:
        """build_index() produces entries with lifecycle, health, maturity, next_step."""
        from paperforge.worker.asset_index import build_index, read_index

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        build_index(vault)

        result = read_index(vault)
        entry = result["items"][0]

        assert "lifecycle" in entry, "entry must have lifecycle field"
        assert "health" in entry, "entry must have health field"
        assert "maturity" in entry, "entry must have maturity field"
        assert "next_step" in entry, "entry must have next_step field"

    def test_all_four_fields_present_after_incremental_refresh(self, tmp_path: Path) -> None:
        """refresh_index_entry() produces entries with lifecycle, health, maturity, next_step."""
        from paperforge.worker.asset_index import read_index, refresh_index_entry

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        _write_index(vault, [{"zotero_key": "AAA", "title": "Paper A"}])
        refresh_index_entry(vault, "AAA")

        result = read_index(vault)
        entry = result["items"][0]

        assert "lifecycle" in entry
        assert "health" in entry
        assert "maturity" in entry
        assert "next_step" in entry

    def test_lifecycle_is_valid_state(self, tmp_path: Path) -> None:
        """lifecycle field is one of the six valid state strings."""
        from paperforge.worker.asset_index import build_index, read_index

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        build_index(vault)

        entry = read_index(vault)["items"][0]
        valid = {"indexed", "pdf_ready", "fulltext_ready", "deep_read_done", "ai_context_ready"}
        assert entry["lifecycle"] in valid, f"got {entry['lifecycle']}"

    def test_health_has_four_dimensions(self, tmp_path: Path) -> None:
        """health field is a dict with pdf_health, ocr_health, note_health, asset_health."""
        from paperforge.worker.asset_index import build_index, read_index

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        build_index(vault)

        health = read_index(vault)["items"][0]["health"]
        assert isinstance(health, dict), f"health should be dict, got {type(health)}"
        assert "pdf_health" in health
        assert "ocr_health" in health
        assert "note_health" in health
        assert "asset_health" in health
        for v in health.values():
            assert isinstance(v, str) and len(v) > 0, f"health value should be non-empty string"

    def test_maturity_structure(self, tmp_path: Path) -> None:
        """maturity field is a dict with level (int 1-6), level_name (str), checks (6 bools), blocking."""
        from paperforge.worker.asset_index import build_index, read_index

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        build_index(vault)

        mat = read_index(vault)["items"][0]["maturity"]
        assert isinstance(mat, dict)
        assert isinstance(mat["level"], int) and 1 <= mat["level"] <= 6
        assert isinstance(mat["level_name"], str) and len(mat["level_name"]) > 0
        assert isinstance(mat["checks"], dict)
        for check_name in ("metadata", "pdf", "fulltext", "figure", "ai", "review"):
            assert check_name in mat["checks"], f"missing check: {check_name}"
            assert isinstance(mat["checks"][check_name], bool)
        # blocking is a string or None
        assert mat["blocking"] is None or isinstance(mat["blocking"], str)

    def test_next_step_is_valid_action(self, tmp_path: Path) -> None:
        """next_step is one of the six valid action strings."""
        from paperforge.worker.asset_index import build_index, read_index

        items = [_make_export_item("AAA", "Paper A")]
        vault = _setup_incremental_vault(tmp_path, items)
        build_index(vault)

        next_step = read_index(vault)["items"][0]["next_step"]
        valid = {"sync", "ocr", "repair", "/pf-deep", "rebuild index", "ready"}
        assert next_step in valid, f"got {next_step}"
