"""Tests for the 8-view Base generation system (Phase 3, Plan 01)."""

from paperforge.worker.base_views import (
    build_base_views,
    substitute_config_placeholders,
)


class TestBuildBaseViews:
    def test_returns_exactly_8_views(self):
        views = build_base_views("骨科")
        assert len(views) == 8

    def test_all_view_names_present(self):
        views = build_base_views("骨科")
        names = [v["name"] for v in views]
        expected = ["控制面板", "推荐分析", "待 OCR", "OCR 完成", "待深度阅读", "深度阅读完成", "正式卡片", "全记录"]
        assert names == expected

    def test_each_view_has_required_keys(self):
        views = build_base_views("骨科")
        for v in views:
            assert "name" in v
            assert "order" in v
            assert "filter" in v
            assert isinstance(v["order"], list)
            assert len(v["order"]) > 0

    def test_control_panel_has_no_filter(self):
        views = build_base_views("骨科")
        cp = next(v for v in views if v["name"] == "控制面板")
        assert cp["filter"] is None

    def test_pending_ocr_filter(self):
        views = build_base_views("骨科")
        pending = next(v for v in views if v["name"] == "待 OCR")
        assert "lifecycle = 'pdf_ready'" in pending["filter"]

    def test_ocr_done_filter(self):
        views = build_base_views("骨科")
        done = next(v for v in views if v["name"] == "OCR 完成")
        assert "lifecycle = 'fulltext_ready'" in done["filter"]

    def test_deep_reading_pending_filter(self):
        views = build_base_views("骨科")
        pending = next(v for v in views if v["name"] == "待深度阅读")
        assert "lifecycle = 'fulltext_ready'" in pending["filter"]

    def test_build_base_views_includes_lifecycle_columns(self):
        views = build_base_views("骨科")
        for v in views:
            assert "lifecycle" in v["order"], f"View '{v['name']}' missing lifecycle"
            assert "next_step" in v["order"], f"View '{v['name']}' missing next_step"
            # Most views include maturity_level; "待 OCR" skips it since OCR isn't done yet
            if v["name"] not in ("待 OCR",):
                assert "maturity_level" in v["order"], f"View '{v['name']}' missing maturity_level"

    def test_build_base_views_removes_old_columns(self):
        views = build_base_views("骨科")
        old_fields = {"has_pdf", "do_ocr", "analyze", "ocr_status"}
        for v in views:
            order_set = set(v["order"])
            assert old_fields.isdisjoint(order_set), f"View '{v['name']}' still contains old fields"

    def test_build_base_views_filters_use_lifecycle(self):
        views = build_base_views("骨科")
        for v in views:
            if v["filter"] is not None:
                assert "lifecycle " in v["filter"], f"View '{v['name']}' filter does not use lifecycle"

    def test_build_base_views_has_sort(self):
        views = build_base_views("骨科")
        for v in views:
            assert "sort" in v, f"View '{v['name']}' missing sort key"
            assert isinstance(v["sort"], list)
            assert len(v["sort"]) == 1
            assert v["sort"][0] == {"field": "lifecycle", "direction": "asc"}

    def test_properties_yaml_updated(self):
        from paperforge.worker.base_views import merge_base_views
        # Access the PROPERTIES_YAML constant by inspecting fresh Base output
        fresh = merge_base_views(None, build_base_views("骨科"))
        assert "lifecycle:" in fresh
        assert "maturity_level:" in fresh
        assert "next_step:" in fresh
        assert "has_pdf:" not in fresh
        assert "do_ocr:" not in fresh
        assert "analyze:" not in fresh
        assert "ocr_status:" not in fresh


class TestSubstituteConfigPlaceholders:
    def test_substitutes_library_records(self, tmp_path):
        content = "${LIBRARY_RECORDS}/骨科"
        vault = tmp_path / "Vault"
        vault.mkdir()
        lib_rec = vault / "03_Resources" / "LiteratureControl" / "library-records"
        lib_rec.mkdir(parents=True)
        result = substitute_config_placeholders(content, {"library_records": lib_rec, "vault": vault})
        assert "${LIBRARY_RECORDS}" not in result
        assert "03_Resources/LiteratureControl/library-records" in result

    def test_substitutes_multiple_placeholders(self, tmp_path):
        content = "${LIBRARY_RECORDS} and ${LITERATURE}"
        vault = tmp_path / "Vault"
        vault.mkdir()
        lib_rec = vault / "LR"
        lit = vault / "LIT"
        lib_rec.mkdir()
        lit.mkdir()
        result = substitute_config_placeholders(
            content, {"library_records": lib_rec, "literature": lit, "vault": vault}
        )
        assert "${LIBRARY_RECORDS}" not in result
        assert "${LITERATURE}" not in result

    def test_unknown_placeholder_unchanged(self):
        content = "${UNKNOWN_PLACEHOLDER}/骨科"
        result = substitute_config_placeholders(content, {})
        assert "${UNKNOWN_PLACEHOLDER}" in result

    def test_backslash_conversion(self, tmp_path):
        content = "${LIBRARY_RECORDS}"
        vault = tmp_path / "Vault"
        vault.mkdir()
        lib_rec = vault / "LR"
        lib_rec.mkdir()
        result = substitute_config_placeholders(content, {"library_records": lib_rec, "vault": vault})
        assert "\\" not in result  # Should use forward slash
