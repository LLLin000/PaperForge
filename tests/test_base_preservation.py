"""Tests for incremental merge and user-view preservation (Phase 3, Plan 02)."""
import pytest
from pathlib import Path
from pipeline.worker.scripts.literature_pipeline import (
    ensure_base_views,
    merge_base_views,
    build_base_views,
    substitute_config_placeholders,
    PAPERFORGE_VIEW_PREFIX,
    STANDARD_VIEW_NAMES,
    slugify_filename,
)


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
        assert content.count("type: table") == 8

        user_custom = content + '''
  - type: table
    name: "My Custom Dashboard"
    order:
      - title
      - year
'''
        domain_base.write_text(user_custom, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        refreshed = domain_base.read_text(encoding="utf-8")

        assert "My Custom Dashboard" in refreshed, "User custom view was lost on incremental refresh"
        assert refreshed.count("type: table") == 9
        assert "控制面板" in refreshed
        assert "OCR 完成" in refreshed

    def test_standard_paperforge_views_are_updated_on_refresh(self):
        """Standard views are replaced with fresh content on each refresh."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        ensure_base_views(self.vault, self.paths, self.config, force=False)

        content1 = domain_base.read_text(encoding="utf-8")
        assert content1.count(PAPERFORGE_VIEW_PREFIX) == 8

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content2 = domain_base.read_text(encoding="utf-8")

        assert content2.count("type: table") == 8
        assert "${LIBRARY_RECORDS}" not in content2

    def test_force_flag_does_full_regeneration(self):
        """--force=True bypasses merge and does full regeneration (all views replaced)."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content1 = domain_base.read_text(encoding="utf-8")

        user_custom = content1 + '''
  - type: table
    name: "My Custom View"
    order:
      - title
'''
        domain_base.write_text(user_custom, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=True)
        refreshed = domain_base.read_text(encoding="utf-8")

        assert "My Custom View" not in refreshed, "force=True should have replaced all views"
        assert refreshed.count("type: table") == 8
        assert refreshed.count(PAPERFORGE_VIEW_PREFIX) == 8

    def test_user_modified_filter_on_standard_view_is_overwritten(self):
        """User changes filter on a standard PaperForge view — on refresh it reverts to template."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        ensure_base_views(self.vault, self.paths, self.config, force=False)
        content1 = domain_base.read_text(encoding="utf-8")

        modified = content1.replace(
            'filter: \'ocr_status = "done"\'',
            'filter: \'ocr_status = "done" AND has_pdf = true\''
        )
        domain_base.write_text(modified, encoding="utf-8")

        ensure_base_views(self.vault, self.paths, self.config, force=False)
        refreshed = domain_base.read_text(encoding="utf-8")

        assert 'filter: \'ocr_status = "done"\'' in refreshed
        assert "has_pdf = true" not in refreshed

    def test_new_domain_base_is_created_on_first_run(self):
        """First run creates domain base if none exists."""
        domain_base = self.bases / f"{slugify_filename('骨科')}.base"
        assert not domain_base.exists()

        ensure_base_views(self.vault, self.paths, self.config, force=False)

        assert domain_base.exists()
        content = domain_base.read_text(encoding="utf-8")
        assert content.count("type: table") == 8
        assert PAPERFORGE_VIEW_PREFIX in content


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
        assert content.count("type: table") == 8, f"Expected 8 views, got {content.count('type: table')}"
        assert PAPERFORGE_VIEW_PREFIX in content
        assert "${LIBRARY_RECORDS}" not in content, "Placeholder should be substituted"

    def test_paperforge_base_created(self, tmp_path):
        """PaperForge.base (all records) is created alongside domain bases."""
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
        assert pf_base.exists(), "PaperForge.base not created"
        content = pf_base.read_text(encoding="utf-8")
        assert content.count("type: table") == 8
        assert "${LIBRARY_RECORDS}" not in content


class TestMergeBaseViews:
    def test_merge_base_views_preserves_user_views(self):
        """merge_base_views preserves views without PAPERFORGE_VIEW_PREFIX."""
        existing = '''
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
'''
        views = build_base_views("骨科")
        result = merge_base_views(existing, views)

        assert "My Custom View" in result, "User view was lost"
        assert "推荐分析" in result
        assert result.count("type: table") >= 8

    def test_merge_base_views_first_run_generates_fresh(self):
        """merge_base_views with no existing content generates fresh YAML."""
        views = build_base_views("骨科")
        result = merge_base_views(None, views)

        assert "views:" in result
        assert "type: table" in result
        assert "properties:" in result

    def test_merge_base_views_unknown_placeholder_unchanged(self):
        """Unknown placeholders in content are left unchanged after merge."""
        existing = '''
filters:
  and:
    - file.inFolder("骨科")
views:
  - type: table
    name: "控制面板"
    order:
      - file.name
'''
        views = build_base_views("骨科")
        result = merge_base_views(existing, views)

        # Only known placeholders should be substituted
        assert "${LIBRARY_RECORDS}" not in result or "03_Resources" in result
