"""Tests for incremental merge, retired legacy view cleanup, and user-view preservation."""

import pytest

from paperforge.worker.base_views import (
    PAPERFORGE_VIEW_PREFIX,
    build_base_views,
    ensure_base_views,
    merge_base_views,
)
from paperforge.worker.sync import slugify_filename


class TestIncrementalMerge:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.vault = tmp_path / "Vault"
        self.vault.mkdir()
        resources = self.vault / "03_Resources"
        resources.mkdir()
        control = resources / "LiteratureControl"
        control.mkdir()
        literature = resources / "Literature"
        literature.mkdir()
        lr = control / "library-records"
        lr.mkdir()
        (lr / "骨科").mkdir()
        self.bases = self.vault / "bases"
        self.bases.mkdir()
        self.paths = {
            "vault": self.vault,
            "resources": resources,
            "control": control,
            "literature": literature,
            "library_records": lr,
            "bases": self.bases,
        }
        self.config = {"domains": [{"domain": "骨科"}]}

    def test_user_custom_view_is_preserved_after_refresh(self):
        """User adds a custom view, then refresh — custom view must be preserved."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content = domain_base.read_text(encoding="utf-8")
        assert content.count("type: paperforge-table") == 1

        user_custom = (
            content
            + """
  - type: table
    name: "My Custom Dashboard"
    order:
      - title
      - year
"""
        )
        domain_base.write_text(user_custom, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        refreshed = domain_base.read_text(encoding="utf-8")

        assert "My Custom Dashboard" in refreshed, "User custom view was lost on incremental refresh"
        assert refreshed.count("type: paperforge-table") == 1
        assert refreshed.count("type: table") == 1
        assert "文献库" in refreshed

    def test_standard_paperforge_views_are_updated_on_refresh(self):
        """Standard library view stays clean and unique across refreshes."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        ensure_base_views(self.vault, self.paths, self.config, force=False)

        content1 = domain_base.read_text(encoding="utf-8")
        assert content1.count(PAPERFORGE_VIEW_PREFIX) == 1

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content2 = domain_base.read_text(encoding="utf-8")

        assert content2.count("type: paperforge-table") == 1
        assert "${LIBRARY_RECORDS}" not in content2

    def test_force_flag_does_full_regeneration(self):
        """--force=True bypasses merge and does full regeneration (all views replaced)."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content1 = domain_base.read_text(encoding="utf-8")

        user_custom = (
            content1
            + """
  - type: table
    name: "My Custom View"
    order:
      - title
"""
        )
        domain_base.write_text(user_custom, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=True)
        refreshed = domain_base.read_text(encoding="utf-8")

        assert "My Custom View" not in refreshed, "force=True should have replaced all views"
        assert refreshed.count("type: paperforge-table") == 1
        assert refreshed.count(PAPERFORGE_VIEW_PREFIX) == 1

    def test_user_modified_filter_on_standard_view_is_preserved(self):
        """User changes filter on 文献库 — on refresh it is PRESERVED unless force=True."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content1 = domain_base.read_text(encoding="utf-8")

        user_filter = "\n    filter: 'impact_factor >= 5'"
        modified = content1.replace("    order:\n      - title", f"    filter: 'impact_factor >= 5'\n    order:\n      - title")
        assert "impact_factor >= 5" in modified
        domain_base.write_text(modified, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        refreshed = domain_base.read_text(encoding="utf-8")

        assert "impact_factor >= 5" in refreshed, "User filter modification should be preserved"

        ensure_base_views(self.vault, self.paths, self.config, force=True)
        force_refreshed = domain_base.read_text(encoding="utf-8")
        assert "impact_factor >= 5" not in force_refreshed

    def test_new_domain_base_is_created_on_first_run(self):
        """First run creates domain base if none exists."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        assert not domain_base.exists()

        ensure_base_views(self.vault, self.paths, self.config, force=False)

        assert domain_base.exists()
        content = domain_base.read_text(encoding="utf-8")
        assert content.count("type: paperforge-table") == 1
        assert PAPERFORGE_VIEW_PREFIX in content

    def test_legacy_pipeline_views_are_retired_and_replaced_by_single_library_view(self):
        """Legacy 控制面板/待 OCR/待深度阅读/重做OCR views are retired during sanitize while preserving user views."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"

        legacy_content = """filters:
  and:
    - file.inFolder("Resources/Literature/骨科")
    - file.ext == "md"
    - !zotero_key.isEmpty()
properties: {}
views:
# PAPERFORGE_VIEW: 控制面板
  - type: paperforge-table
    name: "控制面板"
    order:
      - file.name
      - title
# PAPERFORGE_VIEW: 待 OCR
  - type: paperforge-table
    name: "待 OCR"
    order:
      - year
      - title
    filter: 'do_ocr == true && ocr_status == "pending"'
# PAPERFORGE_VIEW: 待深度阅读
  - type: paperforge-table
    name: "待深度阅读"
    order:
      - year
      - title
    filter: 'analyze == true && ocr_status == "done" && deep_reading_status == "pending"'
  - type: table
    name: "重点精读集"
    order:
      - title
      - impact_factor
"""
        domain_base.write_text(legacy_content, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content = domain_base.read_text(encoding="utf-8")

        assert content.count(PAPERFORGE_VIEW_PREFIX) == 1
        assert 'name: "文献库"' in content
        assert 'name: "重点精读集"' in content
        assert 'name: "控制面板"' not in content
        assert 'name: "待 OCR"' not in content
        assert 'name: "待深度阅读"' not in content


class TestLiteratureHubBase:
    def test_literature_hub_base_created(self, tmp_path):
        vault = tmp_path / "Vault"
        vault.mkdir()
        resources = vault / "03_Resources"
        resources.mkdir()
        control = resources / "LiteratureControl"
        control.mkdir()
        literature = resources / "Literature"
        literature.mkdir()
        library_records = control / "library-records"
        library_records.mkdir()
        bases = vault / "bases"
        bases.mkdir()

        paths = {
            "vault": vault,
            "resources": resources,
            "control": control,
            "literature": literature,
            "library_records": library_records,
            "bases": bases,
        }
        config = {"domains": [{"domain": "骨科"}, {"domain": "运动医学"}]}

        ensure_base_views(vault, paths, config, force=False)

        hub_base = bases / "Literature Hub.base"
        assert hub_base.exists(), "Literature Hub.base not created"
        content = hub_base.read_text(encoding="utf-8")
        assert content.count("type: paperforge-table") == 1
        assert 'name: "文献库"' in content
        assert PAPERFORGE_VIEW_PREFIX in content
        assert "${LIBRARY_RECORDS}" not in content, "Placeholder should be substituted"

    def test_paperforge_base_not_created(self, tmp_path):
        """PaperForge.base (all records) is NOT created (removed in v1.4.1)."""
        vault = tmp_path / "Vault"
        vault.mkdir()
        resources = vault / "03_Resources"
        resources.mkdir()
        control = resources / "LiteratureControl"
        control.mkdir()
        literature = resources / "Literature"
        literature.mkdir()
        library_records = control / "library-records"
        library_records.mkdir()
        (library_records / "骨科").mkdir()
        bases = vault / "bases"
        bases.mkdir()

        paths = {
            "vault": vault,
            "resources": resources,
            "control": control,
            "literature": literature,
            "library_records": library_records,
            "bases": bases,
        }
        config = {"domains": [{"domain": "骨科"}]}

        ensure_base_views(vault, paths, config, force=False)

        pf_base = bases / "PaperForge.base"
        assert not pf_base.exists(), "PaperForge.base should not be created"


class TestMergeBaseViews:
    def test_merge_base_views_preserves_user_views_and_retires_legacy_pf(self):
        """merge_base_views preserves user views and retires legacy PF views."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
  - type: table
    name: "控制面板"
    order:
      - file.name
# PAPERFORGE_VIEW: 推荐分析
  - type: table
    name: "推荐分析"
    order:
      - year
    filter: 'analyze = true'
  - type: table
    name: "My Custom View"
    order:
      - title
"""
        views = build_base_views("骨科")
        result = merge_base_views(existing, views, folder_filter="Resources/Literature/骨科")

        assert "My Custom View" in result, "User view was lost"
        assert result.count("type: paperforge-table") == 1
        assert result.count("type: table") == 1
        assert result.count(PAPERFORGE_VIEW_PREFIX) == 1
        assert "推荐分析" not in result
        assert "控制面板" not in result

    def test_merge_base_views_first_run_generates_fresh(self):
        """merge_base_views with no existing content generates fresh YAML."""
        views = build_base_views("骨科")
        result = merge_base_views(None, views, folder_filter="Resources/Literature/骨科")

        assert "views:" in result
        assert "type: paperforge-table" in result
        assert "properties:" in result
        assert 'name: "文献库"' in result

    def test_merge_base_views_unknown_placeholder_unchanged(self):
        """Unknown placeholders in content are left unchanged after merge."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
  - type: table
    name: "控制面板"
    order:
      - file.name
"""
        views = build_base_views("骨科")
        result = merge_base_views(existing, views)

        assert "${LIBRARY_RECORDS}" not in result or "03_Resources" in result

    def test_merge_base_views_preserves_column_widths(self):
        """User-adjusted column widths on 文献库 survive merge."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
# PAPERFORGE_VIEW: 文献库
  - type: paperforge-table
    name: "文献库"
    widths:
      title: 400
      year: 60
    order:
      - title
      - year
# PAPERFORGE_VIEW: 重做OCR
  - type: table
    name: "重做OCR"
    widths:
      year: 55
      title: 380
    order:
      - year
      - title
    filter: "ocr_status = 'done'"
"""
        views = build_base_views("骨科")
        result = merge_base_views(existing, views)

        assert "widths:" in result
        assert "title: 400" in result
        assert "year: 60" in result
        assert "重做OCR" not in result

    def test_merge_base_views_widths_not_injected_when_none_exist(self):
        """Fresh PF views without old widths should not have widths injected."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
# PAPERFORGE_VIEW: 文献库
  - type: paperforge-table
    name: "文献库"
    order:
      - title
"""
        views = build_base_views("骨科")
        result = merge_base_views(existing, views)

        assert "widths:" not in result
        assert "columnSize:" not in result

    def test_merge_base_views_preserves_native_column_size_and_sort_property(self):
        """Obsidian native columnSize: survives merge and sort uses property:."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
# PAPERFORGE_VIEW: 文献库
  - type: paperforge-table
    name: "文献库"
    columnSize:
      note.title: 340
      note.year: 64
    order:
      - title
      - year
"""
        views = [
            {
                "type": "paperforge-table",
                "name": "文献库",
                "order": ["title", "year"],
                "filter": None,
                "sort": [{"property": "note.year", "direction": "DESC"}],
            }
        ]
        result = merge_base_views(existing, views)

        assert "columnSize:" in result
        assert "note.title: 340" in result
        assert "note.year: 64" in result
        assert "property: note.year" in result
        assert "field:" not in result

    def test_sanitize_quotes_list_item_unquoted_bang_filter(self):
        """PF-MIG-009: _sanitize_base_file quotes `- !zotero_key.isEmpty()` so .base parses as valid YAML."""
        import yaml
        from paperforge.worker.base_views import _sanitize_base_file, build_base_views

        legacy = (
            "filters:\n"
            "  and:\n"
            '    - file.inFolder("Resources/Literature/Ortho")\n'
            "    - !zotero_key.isEmpty()\n"
            "views:\n"
            "  - type: table\n"
            '    name: "文献库"\n'
            "    order:\n"
            "      - title\n"
        )
        sanitized = _sanitize_base_file(
            legacy, build_base_views("Ortho"), folder_filter="Resources/Literature/Ortho"
        )
        assert '- "!zotero_key.isEmpty()"' in sanitized
        parsed = yaml.safe_load(sanitized)
        assert isinstance(parsed, dict)
        assert "!zotero_key.isEmpty()" in parsed["filters"]["and"]
