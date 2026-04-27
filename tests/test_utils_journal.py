"""Unit tests for _utils.py journal database functions.

Covers: load_journal_db, lookup_impact_factor

NOTE: _utils._JOURNAL_DB is a module-level cache. Tests must reset it
between scenarios by setting _utils._JOURNAL_DB = None before each test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.worker import _utils


def _make_vault(tmp_path: Path) -> Path:
    """Create minimal vault with paperforge.json."""
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
        "skill_dir": ".opencode/skills",
    }
    (vault / "paperforge.json").write_text(json.dumps(cfg), encoding="utf-8")
    return vault


def _reset_cache() -> None:
    """Reset the module-level _JOURNAL_DB cache between tests."""
    _utils._JOURNAL_DB = None


class TestLoadJournalDb:
    """load_journal_db(vault: Path) -> dict[str, dict]"""

    def test_loads_valid_zoterostyle(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        zstyle_dir = vault / "99_System" / "Zotero"
        zstyle_dir.mkdir(parents=True)
        zstyle_path = zstyle_dir / "zoterostyle.json"
        data = {"Journal A": {"rank": {"sciif": "5.2"}}}
        zstyle_path.write_text(json.dumps(data), encoding="utf-8")

        result = _utils.load_journal_db(vault)
        assert result == data

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        result = _utils.load_journal_db(vault)
        assert result == {}

    def test_malformed_json_returns_empty(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        zstyle_dir = vault / "99_System" / "Zotero"
        zstyle_dir.mkdir(parents=True)
        (zstyle_dir / "zoterostyle.json").write_text("{broken", encoding="utf-8")

        result = _utils.load_journal_db(vault)
        assert result == {}

    def test_cache_returns_same_object(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        zstyle_dir = vault / "99_System" / "Zotero"
        zstyle_dir.mkdir(parents=True)
        zstyle_path = zstyle_dir / "zoterostyle.json"
        zstyle_path.write_text(json.dumps({"J": {}}), encoding="utf-8")

        first = _utils.load_journal_db(vault)
        second = _utils.load_journal_db(vault)
        assert first is second  # same cached object


class TestLookupImpactFactor:
    """lookup_impact_factor(journal_name, extra, vault) -> str"""

    def test_finds_sciif_in_db(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        zstyle_dir = vault / "99_System" / "Zotero"
        zstyle_dir.mkdir(parents=True)
        zstyle_path = zstyle_dir / "zoterostyle.json"
        zstyle_path.write_text(
            json.dumps({"J Bone Joint Surg Am": {"rank": {"sciif": "5.2"}}}),
            encoding="utf-8",
        )

        # Pre-warm cache
        _utils.load_journal_db(vault)

        result = _utils.lookup_impact_factor("J Bone Joint Surg Am", "", vault)
        assert result == "5.2"

    def test_fallback_to_extra_field(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        extra = "Some text \u5f71\u54cd\u56e0\u5b50: 3.14 more text"
        result = _utils.lookup_impact_factor("Unknown Journal", extra, vault)
        assert result == "3.14"

    def test_extra_field_chinese_colon(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        result = _utils.lookup_impact_factor("Unknown", "\u5f71\u54cd\u56e0\u5b50\uff1a2.718", vault)
        assert result == "2.718"

    def test_empty_journal_returns_empty(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        result = _utils.lookup_impact_factor("", "anything", vault)
        assert result == ""

    def test_no_match_returns_empty(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        result = _utils.lookup_impact_factor("Nonexistent Journal", "", vault)
        assert result == ""

    def test_db_rank_sciif_int_converted_to_str(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        zstyle_dir = vault / "99_System" / "Zotero"
        zstyle_dir.mkdir(parents=True)
        zstyle_path = zstyle_dir / "zoterostyle.json"
        zstyle_path.write_text(
            json.dumps({"Test J": {"rank": {"sciif": 4}}}, ensure_ascii=False),
            encoding="utf-8",
        )
        _utils.load_journal_db(vault)

        result = _utils.lookup_impact_factor("Test J", "", vault)
        assert result == "4"

    def test_db_rank_sciif_missing_falls_to_extra(self, tmp_path: Path) -> None:
        _reset_cache()
        vault = _make_vault(tmp_path)
        zstyle_dir = vault / "99_System" / "Zotero"
        zstyle_dir.mkdir(parents=True)
        zstyle_path = zstyle_dir / "zoterostyle.json"
        zstyle_path.write_text(
            json.dumps({"Test J": {"rank": {"not_sciif": "x"}}}),
            encoding="utf-8",
        )
        _utils.load_journal_db(vault)

        result = _utils.lookup_impact_factor("Test J", "\u5f71\u54cd\u56e0\u5b50: 1.5", vault)
        assert result == "1.5"
