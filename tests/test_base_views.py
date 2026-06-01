"""Tests for the 4-view Base generation system (Phase 44: slim base views)."""

from paperforge.worker.base_views import (
    build_base_views,
    substitute_config_placeholders,
)


class TestBuildBaseViews:
    def test_build_base_views_has_4_standard_views(self):
        views = build_base_views("骨科")
        names = {v["name"] for v in views}

        assert names == {"控制面板", "待 OCR", "待深度阅读", "重做OCR"}

    def test_ocr_redo_view_has_correct_columns(self):
        views = build_base_views("骨科")
        redo = next(v for v in views if v["name"] == "重做OCR")

        assert redo["order"] == ["year", "first_author", "title", "ocr_redo", "ocr_status"]
        assert redo["filter"] == 'ocr_status == "done"'

    def test_returns_exactly_4_views(self):
        views = build_base_views("骨科")
        assert len(views) == 4

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
        assert "do_ocr == true" in pending["filter"]
        assert 'ocr_status == "pending"' in pending["filter"]

    def test_deep_reading_pending_filter(self):
        views = build_base_views("骨科")
        pending = next(v for v in views if v["name"] == "待深度阅读")
        assert "analyze == true" in pending["filter"]
        assert 'ocr_status == "done"' in pending["filter"]
        assert 'deep_reading_status == "pending"' in pending["filter"]

    def test_removed_views_not_present(self):
        removed = {"推荐分析", "OCR 完成", "深度阅读完成", "正式卡片", "全记录"}
        views = build_base_views("骨科")
        names = {v["name"] for v in views}
        assert removed.isdisjoint(names), f"Removed views still present: {removed & names}"

    def test_build_base_views_has_no_sort(self):
        views = build_base_views("骨科")
        for v in views:
            assert "sort" not in v, f"View '{v['name']}' should not have sort key"


class TestSubstituteConfigPlaceholders:
    def test_substitutes_literature(self, tmp_path):
        content = "${LITERATURE}/骨科"
        vault = tmp_path / "Vault"
        vault.mkdir()
        lit = vault / "Resources" / "Literature"
        lit.mkdir(parents=True)
        result = substitute_config_placeholders(content, {"literature": lit, "vault": vault})
        assert "${LITERATURE}" not in result
        assert "Resources/Literature" in result

    def test_substitutes_control_dir(self, tmp_path):
        content = "${CONTROL_DIR}/records"
        vault = tmp_path / "Vault"
        vault.mkdir()
        ctrl = vault / "System"
        ctrl.mkdir()
        result = substitute_config_placeholders(content, {"control": ctrl, "vault": vault})
        assert "${CONTROL_DIR}" not in result
        assert "System/records" in result

    def test_substitutes_multiple_placeholders(self, tmp_path):
        content = "${LITERATURE} and ${CONTROL_DIR}"
        vault = tmp_path / "Vault"
        vault.mkdir()
        lit = vault / "LIT"
        ctrl = vault / "CTRL"
        lit.mkdir()
        ctrl.mkdir()
        result = substitute_config_placeholders(
            content, {"literature": lit, "control": ctrl, "vault": vault}
        )
        assert "${LITERATURE}" not in result
        assert "${CONTROL_DIR}" not in result

    def test_unknown_placeholder_unchanged(self):
        content = "${UNKNOWN_PLACEHOLDER}/骨科"
        result = substitute_config_placeholders(content, {})
        assert "${UNKNOWN_PLACEHOLDER}" in result

    def test_backslash_conversion(self, tmp_path):
        content = "${LITERATURE}"
        vault = tmp_path / "Vault"
        vault.mkdir()
        lit = vault / "LR"
        lit.mkdir()
        result = substitute_config_placeholders(content, {"literature": lit, "vault": vault})
        assert "\\" not in result  # Should use forward slash


class TestBaseFilterYAMLSyntax:
    """Verify generated Base YAML uses correct Obsidian Base filter syntax."""

    def test_all_filters_use_double_equals_and_double_quotes(self):
        """Filter values must use == and " for strings, per Obsidian Base docs."""
        views = build_base_views("test")
        for v in views:
            if not v["filter"]:
                continue
            f = v["filter"]
            assert "=" not in f.replace("==", ""), f"single = in filter: {f}"
            assert "'" not in f, f"single quote in filter: {f}"

    def test_rendered_yaml_wraps_filter_in_single_quotes(self):
        """YAML output must wrap filter strings in single quotes to protect double quotes inside."""
        from paperforge.worker.base_views import _render_views_section

        views = build_base_views("test")
        yaml_output = _render_views_section(views)

        for v in views:
            if not v["filter"]:
                continue
            expected_line = f"    filter: '{v['filter']}'"
            assert expected_line in yaml_output, (
                f"Expected YAML line not found: {expected_line}\nGot:\n{yaml_output}"
            )

    def test_no_single_quote_in_rendered_filter_value(self):
        """No single quote inside the filter value (would break YAML single-quote wrapping)."""
        views = build_base_views("test")
        for v in views:
            if not v["filter"]:
                continue
            inner = v["filter"]
            assert "'" not in inner, f"single quote inside filter value: {inner}"
