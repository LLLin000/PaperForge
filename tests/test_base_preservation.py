"""Tests for incremental merge and user-view preservation (Phase 3, Plan 02)."""

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
        assert content.count("type: table") == 4

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
        assert refreshed.count("type: table") == 5
        assert "控制面板" in refreshed
        assert "重做OCR" in refreshed

    def test_standard_paperforge_views_are_updated_on_refresh(self):
        """Standard views are replaced with fresh content on each refresh."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        ensure_base_views(self.vault, self.paths, self.config, force=False)

        content1 = domain_base.read_text(encoding="utf-8")
        assert content1.count(PAPERFORGE_VIEW_PREFIX) == 4

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content2 = domain_base.read_text(encoding="utf-8")

        assert content2.count("type: table") == 4
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
        assert refreshed.count("type: table") == 4
        assert refreshed.count(PAPERFORGE_VIEW_PREFIX) == 4

    def test_user_modified_filter_on_standard_view_is_preserved(self):
        """User changes filter on a standard PF view — on refresh it is PRESERVED.

        v3: _sanitize_base_file does NOT touch existing view content.
        User modifications to standard view filters, columns, widths, sort survive refresh.
        Only: duplicate removal, syntax fixes, missing standard views appended.
        """
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content1 = domain_base.read_text(encoding="utf-8")

        ocr_filter_old = 'ocr_status == "pending"'
        ocr_filter_modified = 'ocr_status == "pending" && extra_check == true'

        modified = content1.replace(ocr_filter_old, ocr_filter_modified)
        domain_base.write_text(modified, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        refreshed = domain_base.read_text(encoding="utf-8")

        # v3: existing view content is preserved — user modification survives
        assert ocr_filter_modified in refreshed, "User filter modification should be preserved"
        # force=True should still regenerate (user mods lost when force)
        ensure_base_views(self.vault, self.paths, self.config, force=True)
        force_refreshed = domain_base.read_text(encoding="utf-8")
        assert ocr_filter_old in force_refreshed
        assert ocr_filter_modified not in force_refreshed

    def test_new_domain_base_is_created_on_first_run(self):
        """First run creates domain base if none exists."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        assert not domain_base.exists()

        ensure_base_views(self.vault, self.paths, self.config, force=False)

        assert domain_base.exists()
        content = domain_base.read_text(encoding="utf-8")
        assert content.count("type: table") == 4
        assert PAPERFORGE_VIEW_PREFIX in content

    def test_old_file_without_prefix_gets_views_without_duplication(self):
        """Old base files (no PAPERFORGE_VIEW_PREFIX): existing views preserved, missing standard views appended."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"

        # Simulate old-version file: 2 views without PAPERFORGE_VIEW_PREFIX
        old_content = """filters:
  and:
    - file.inFolder("Resources/Literature/骨科")
    - file.ext == "md"
    - !zotero_key.isEmpty()
properties: {}
views:
  - type: table
    name: "控制面板"
    order:
      - file.name
      - title
  - type: table
    name: "待 OCR"
    order:
      - year
      - title
    filter: 'do_ocr == true && ocr_status == "pending"'
"""
        domain_base.write_text(old_content, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content = domain_base.read_text(encoding="utf-8")

        # Old views preserved as-is (no prefix added to existing); missing views appended with prefix
        assert content.count('name: "控制面板"') == 1
        assert content.count('name: "待 OCR"') == 1
        assert content.count(PAPERFORGE_VIEW_PREFIX) == 2  # Only 待深度阅读 + 重做OCR added
        assert "重做OCR" in content
        assert "待深度阅读" in content

    def test_corrupted_file_with_eight_views_repaired_to_four(self):
        """Post-corruption: 4 old prefix-free views + 4 new PF-prefixed views = 8.
        merge_base_views should replace ALL PF views -> exactly 4, no duplicates.
        This is the actual user state after the V1 bug: each sync appended duplicates."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"

        # Simulate the corrupted state: old prefix-free views + duplicate PF-prefixed views
        corrupted = """filters:
  and:
    - file.inFolder("Resources/Literature/骨科")
    - file.ext == "md"
    - !zotero_key.isEmpty()
properties: {}
views:
  - type: table
    name: "控制面板"
    order:
      - file.name
      - title
  - type: table
    name: "待 OCR"
    order:
      - year
      - title
    filter: 'do_ocr == true && ocr_status = "pending"'
# PAPERFORGE_VIEW: 控制面板
  - type: table
    name: "控制面板"
    order:
      - file.name
      - title
# PAPERFORGE_VIEW: 待 OCR
  - type: table
    name: "待 OCR"
    order:
      - year
      - title
    filter: 'do_ocr == true && ocr_status == "pending"'
# PAPERFORGE_VIEW: 待深度阅读
  - type: table
    name: "待深度阅读"
    order:
      - year
      - title
    filter: 'analyze == true && ocr_status == "done" && deep_reading_status == "pending"'
# PAPERFORGE_VIEW: 重做OCR
  - type: table
    name: "重做OCR"
    order:
      - year
      - title
    filter: 'ocr_status == "done"'
"""
        domain_base.write_text(corrupted, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content = domain_base.read_text(encoding="utf-8")

        # After merge: exactly 4 PF views, zero duplicates
        assert content.count(PAPERFORGE_VIEW_PREFIX) == 4
        assert content.count('name: "控制面板"') == 1, f"Expected 1 控制面板, got {content.count('name: \"控制面板\"')}"
        assert content.count('name: "待 OCR"') == 1
        assert content.count('name: "待深度阅读"') == 1
        assert content.count('name: "重做OCR"') == 1
        assert "重做OCR" in content


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
        assert content.count("type: table") == 4, f"Expected 4 views, got {content.count('type: table')}"
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
    def test_merge_base_views_preserves_user_views(self):
        """merge_base_views preserves views without PAPERFORGE_VIEW_PREFIX."""
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
        assert result.count("type: table") == 5
        assert result.count(PAPERFORGE_VIEW_PREFIX) == 4
        assert "推荐分析" not in result, "Old PF view should be dropped"

    def test_merge_base_views_first_run_generates_fresh(self):
        """merge_base_views with no existing content generates fresh YAML."""
        views = build_base_views("骨科")
        result = merge_base_views(None, views, folder_filter="Resources/Literature/骨科")

        assert "views:" in result
        assert "type: table" in result
        assert "properties:" in result

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

        # Only known placeholders should be substituted
        assert "${LIBRARY_RECORDS}" not in result or "03_Resources" in result

    def test_merge_base_views_preserves_column_widths(self):
        """User-adjusted column widths in PF views survive merge."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
# PAPERFORGE_VIEW: 控制面板
  - type: table
    name: "控制面板"
    widths:
      file.name: 180
      title: 400
      year: 60
    order:
      - file.name
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
        assert "file.name: 180" in result
        assert "title: 400" in result
        assert "year: 60" in result
        assert "year: 55" in result
        assert "title: 380" in result

    def test_merge_base_views_widths_not_injected_when_none_exist(self):
        """Fresh PF views without old widths should not have widths injected."""
        existing = """
filters:
  and:
    - file.inFolder("骨科")
views:
# PAPERFORGE_VIEW: 控制面板
  - type: table
    name: "控制面板"
    order:
      - file.name
      - title
"""
        views = build_base_views("骨科")
        result = merge_base_views(existing, views)

        assert "widths:" not in result
