"""Tests for the 8-view Base generation system (Phase 39: workflow-gate views)."""

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
        assert "do_ocr = true" in pending["filter"]
        assert "ocr_status = 'pending'" in pending["filter"]

    def test_ocr_done_filter(self):
        views = build_base_views("骨科")
        done = next(v for v in views if v["name"] == "OCR 完成")
        assert "ocr_status = 'done'" in done["filter"]

    def test_deep_reading_pending_filter(self):
        views = build_base_views("骨科")
        pending = next(v for v in views if v["name"] == "待深度阅读")
        assert "analyze = true" in pending["filter"]
        assert "ocr_status = 'done'" in pending["filter"]
        assert "deep_reading_status = 'pending'" in pending["filter"]

    def test_build_base_views_includes_workflow_flags(self):
        views = build_base_views("骨科")
        for v in views:
            order_set = set(v["order"])
            assert "has_pdf" in order_set, f"View '{v['name']}' missing has_pdf"
            if v["name"] not in ("正式卡片",):
                assert "do_ocr" in order_set, f"View '{v['name']}' missing do_ocr"
            if v["name"] not in ("正式卡片", "待 OCR", "OCR 完成"):
                assert "analyze" in order_set, f"View '{v['name']}' missing analyze"

    def test_build_base_views_removes_ghost_columns(self):
        views = build_base_views("骨科")
        ghost_fields = {"lifecycle", "maturity_level", "next_step"}
        for v in views:
            order_set = set(v["order"])
            assert ghost_fields.isdisjoint(order_set), f"View '{v['name']}' still contains ghost lifecycle columns"

    def test_build_base_views_filters_use_workflow_gates(self):
        views = build_base_views("骨科")
        for v in views:
            if v["filter"] is not None:
                assert "lifecycle" not in v["filter"], f"View '{v['name']}' filter uses lifecycle instead of workflow gates"

    def test_build_base_views_has_no_sort(self):
        views = build_base_views("骨科")
        for v in views:
            assert "sort" not in v, f"View '{v['name']}' should not have sort key (lifecycle removed from frontmatter)"

    def test_properties_yaml_updated(self):
        from paperforge.worker.base_views import merge_base_views
        fresh = merge_base_views(None, build_base_views("骨科"))
        assert "lifecycle:" not in fresh
        assert "maturity_level:" not in fresh
        assert "next_step:" not in fresh
        assert "has_pdf:" in fresh
        assert "do_ocr:" in fresh
        assert "analyze:" in fresh
        assert "ocr_status:" in fresh


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
