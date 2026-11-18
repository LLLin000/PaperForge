"""Tests for the 4-view Base generation system (Phase 44: slim base views)."""

from paperforge.worker.base_views import (
    build_base_views,
    substitute_config_placeholders,
)


class TestBuildBaseViews:
    def test_build_base_views_has_single_library_view(self):
        views = build_base_views("骨科")
        names = {v["name"] for v in views}
        assert names == {"文献库"}

    def test_legacy_pipeline_views_removed(self):
        removed = {
            "控制面板",
            "待 OCR",
            "待深度阅读",
            "重做OCR",
            "推荐分析",
            "OCR 完成",
            "深度阅读完成",
            "正式卡片",
            "全记录",
        }
        views = build_base_views("骨科")
        names = {v["name"] for v in views}
        assert removed.isdisjoint(names), f"Removed views still present: {removed & names}"

    def test_returns_exactly_1_view(self):
        views = build_base_views("骨科")
        assert len(views) == 1

    def test_view_has_required_keys_and_no_queue_flags(self):
        views = build_base_views("骨科")
        v = views[0]
        assert v["name"] == "文献库"
        assert isinstance(v["order"], list)
        assert len(v["order"]) > 0
        assert v["filter"] is None
        assert "sort" not in v
        assert v.get("type") == "paperforge-table"
        assert "fulltext_md_path" not in v["order"]
        assert "do_ocr" not in v["order"]
        assert "analyze" not in v["order"]


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


