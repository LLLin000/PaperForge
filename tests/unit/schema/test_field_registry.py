from __future__ import annotations

from pathlib import Path

from paperforge.schema import (
    get_field_info,
    get_owner_fields,
    load_field_registry,
)

HERE = Path(__file__).resolve().parent
REGISTRY_PATH = HERE.parent.parent.parent / "paperforge" / "schema" / "field_registry.yaml"


class TestLoadFieldRegistry:
    def test_valid_path_returns_non_empty(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        assert isinstance(reg, dict)
        assert len(reg) > 0

    def test_nonexistent_path_returns_empty(self) -> None:
        reg = load_field_registry(Path("/nonexistent/path.yaml"))
        assert reg == {}

    def test_default_path_works(self) -> None:
        reg = load_field_registry()
        assert isinstance(reg, dict)
        assert len(reg) > 0


class TestRegistryOwners:
    def test_has_all_three_owners(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        assert "frontmatter" in reg
        assert "index_entry" in reg
        assert "ocr_meta" in reg
        assert len(reg) == 3


class TestFrontmatterFields:
    def test_has_required_fields(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        fm = get_owner_fields(reg, "frontmatter")
        required = {"zotero_key", "domain", "title", "has_pdf"}
        for field in required:
            assert field in fm, f"Missing required frontmatter field: {field}"
            assert fm[field]["required"] is True, f"{field} should be required"

    def test_all_expected_fields_present(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        fm = get_owner_fields(reg, "frontmatter")
        expected = {
            "zotero_key", "domain", "title", "year", "doi",
            "collection_path", "has_pdf", "pdf_path", "supplementary",
            "fulltext_md_path", "recommend_analyze", "analyze",
            "do_ocr", "ocr_status", "deep_reading_status", "path_error",
        }
        assert set(fm.keys()) == expected


class TestGetOwnerFields:
    def test_returns_correct_owner(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        fm = get_owner_fields(reg, "frontmatter")
        assert "zotero_key" in fm
        assert fm["zotero_key"]["type"] == "str"

    def test_unknown_owner_returns_empty(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        assert get_owner_fields(reg, "nonexistent") == {}


class TestGetFieldInfo:
    def test_known_field_returns_metadata(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        info = get_field_info(reg, "frontmatter", "zotero_key")
        assert info is not None
        assert info["type"] == "str"
        assert info["required"] is True
        assert info["public"] is True

    def test_unknown_field_returns_none(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        info = get_field_info(reg, "frontmatter", "nonexistent_field")
        assert info is None

    def test_unknown_owner_field_returns_none(self) -> None:
        reg = load_field_registry(REGISTRY_PATH)
        info = get_field_info(reg, "nonexistent", "zotero_key")
        assert info is None
