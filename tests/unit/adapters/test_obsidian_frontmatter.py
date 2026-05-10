from __future__ import annotations

from pathlib import Path

from paperforge.adapters.obsidian_frontmatter import (
    _add_missing_frontmatter_fields,
    _extract_section,
    _legacy_control_flags,
    _read_frontmatter_bool_from_text,
    _read_frontmatter_optional_bool_from_text,
    canonicalize_decision,
    candidate_markdown,
    compute_final_collection,
    extract_preserved_deep_reading,
    generate_review,
    has_deep_reading_content,
    read_frontmatter_dict,
    update_frontmatter_field,
)


class TestReadFrontmatterBoolFromText:
    def test_true_returns_true(self) -> None:
        text = "some_key: true\nother: thing"
        assert _read_frontmatter_bool_from_text(text, "some_key") is True

    def test_false_returns_false(self) -> None:
        text = "some_key: false\nother: thing"
        assert _read_frontmatter_bool_from_text(text, "some_key") is False

    def test_missing_returns_default(self) -> None:
        text = "other: thing"
        assert _read_frontmatter_bool_from_text(text, "missing") is False
        assert _read_frontmatter_bool_from_text(text, "missing", True) is True


class TestReadFrontmatterOptionalBoolFromText:
    def test_true_returns_true(self) -> None:
        text = "do_ocr: true"
        assert _read_frontmatter_optional_bool_from_text(text, "do_ocr") is True

    def test_false_returns_false(self) -> None:
        text = "do_ocr: false"
        assert _read_frontmatter_optional_bool_from_text(text, "do_ocr") is False

    def test_missing_returns_none(self) -> None:
        text = "other: thing"
        assert _read_frontmatter_optional_bool_from_text(text, "missing") is None


class TestReadFrontmatterDict:
    def test_valid_yaml(self) -> None:
        text = "---\nkey: value\nnum: 42\n---\nbody"
        result = read_frontmatter_dict(text)
        assert result == {"key": "value", "num": 42}

    def test_malformed_yaml_fallback(self) -> None:
        text = "---\nkey: value\n: : malformed\n---\nbody"
        result = read_frontmatter_dict(text)
        assert "key" not in result or result.get("key") is not None

    def test_no_frontmatter_returns_empty(self) -> None:
        text = "plain text body\nno frontmatter here"
        result = read_frontmatter_dict(text)
        assert result == {}

    def test_nested_values(self) -> None:
        text = "---\nnested:\n  inner: val\n  num: 42\n---"
        result = read_frontmatter_dict(text)
        assert result["nested"]["inner"] == "val"
        assert result["nested"]["num"] == 42


class TestLegacyControlFlags:
    def test_no_library_records_path(self, tmp_path: Path) -> None:
        paths = {"library_records": tmp_path / "nonexistent"}
        result = _legacy_control_flags(paths, "ABCDEFG")
        assert result == {"do_ocr": None, "analyze": None}

    def test_no_record_found(self, tmp_path: Path) -> None:
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        paths = {"library_records": records_dir}
        result = _legacy_control_flags(paths, "NOKEY")
        assert result == {"do_ocr": None, "analyze": None}

    def test_record_read_success(self, tmp_path: Path) -> None:
        records_dir = tmp_path / "records"
        records_dir.mkdir()
        record_file = records_dir / "ABCDEFG.md"
        record_file.write_text("---\ndo_ocr: true\nanalyze: false\n---", encoding="utf-8")
        paths = {"library_records": records_dir}
        result = _legacy_control_flags(paths, "ABCDEFG")
        assert result == {"do_ocr": True, "analyze": False}


class TestComputeFinalCollection:
    def test_user_collection_used_when_present(self) -> None:
        row = {"user_collection": "骨科/脊柱", "user_collection_resolved": "骨科/脊柱/颈椎", "recommended_collection": "骨科/创伤"}
        assert compute_final_collection(row) == "骨科/脊柱/颈椎"

    def test_recommended_fallback(self) -> None:
        row = {"user_collection": "", "user_collection_resolved": "", "recommended_collection": "骨科/创伤"}
        assert compute_final_collection(row) == "骨科/创伤"

    def test_empty_returns_empty(self) -> None:
        row = {"user_collection": "", "user_collection_resolved": "", "recommended_collection": ""}
        assert compute_final_collection(row) == ""


class TestCanonicalizeDecision:
    def test_empty_returns_daidin(self) -> None:
        assert canonicalize_decision("") == "待定"

    def test_daicha_returns_daidin(self) -> None:
        assert canonicalize_decision("待查") == "待定"

    def test_paichu_returns_bunaron(self) -> None:
        assert canonicalize_decision("排除") == "不纳入"

    def test_bunaron_returns_bunaron(self) -> None:
        assert canonicalize_decision("不纳入") == "不纳入"

    def test_naru_returns_naru(self) -> None:
        assert canonicalize_decision("纳入") == "纳入"


class TestCandidateMarkdown:
    def test_complete_row(self) -> None:
        row = {"candidate_id": "C001", "domain": "骨科", "title": "Test Paper", "authors": ["Author A"], "year": 2024}
        result = candidate_markdown(row)
        assert result.startswith("---")
        assert '"C001"' in result
        assert '"Test Paper"' in result

    def test_minimum_row(self) -> None:
        row = {"candidate_id": "C002", "title": "Minimal"}
        result = candidate_markdown(row)
        assert result.startswith("---")
        assert "C002" in result

    def test_missing_optional_fields(self) -> None:
        row = {"candidate_id": "C003", "title": "Partial", "doi": "10.1234/test"}
        result = candidate_markdown(row)
        assert "doi" in result
        assert result.startswith("---")


class TestGenerateReview:
    def test_include_and_exclude(self) -> None:
        candidates = [
            {"candidate_id": "C001", "title": "Keep", "decision": "纳入", "recommended_collection": "骨科/脊柱"},
            {"candidate_id": "C002", "title": "Drop", "decision": "排除"},
        ]
        result = generate_review(candidates)
        assert "Keep" in result
        assert "Drop" in result
        assert "建议纳入：1" in result
        assert "不纳入：1" in result

    def test_empty_list(self) -> None:
        result = generate_review([])
        assert "候选数量：0" in result


class TestExtractPreservedDeepReading:
    def test_with_section(self) -> None:
        text = "some preamble\n## 🔍 精读\nDeep reading content here\nmore content"
        result = extract_preserved_deep_reading(text)
        assert "## 🔍 精读" in result
        assert "Deep reading content" in result

    def test_without_section(self) -> None:
        text = "some content\nno deep reading section"
        result = extract_preserved_deep_reading(text)
        assert result == ""

    def test_empty_text(self) -> None:
        assert extract_preserved_deep_reading("") == ""


class TestHasDeepReadingContent:
    def test_full_content_returns_true(self) -> None:
        text = """preamble
## 🔍 精读
- **Clarity**（清晰度）：The paper clearly describes the method
- **Figure 导读**
  - Figure 1：Shows the main result
- **遗留问题**
  - Need more validation"""
        assert has_deep_reading_content(text) is True

    def test_empty_body_returns_false(self) -> None:
        text = "## 🔍 精读"
        assert has_deep_reading_content(text) is False

    def test_no_deep_reading_section_returns_false(self) -> None:
        text = "no section here"
        assert has_deep_reading_content(text) is False


class TestExtractSection:
    def test_section_extracted(self) -> None:
        body = "Some text\n**Figure 导读**\n- Figure 1: content\n## Next section"
        result = _extract_section(body, r'\*\*Figure 导读\*\*')
        assert result is not None
        assert "Figure 1" in result

    def test_no_match_returns_none(self) -> None:
        body = "no matching header here"
        result = _extract_section(body, r'\*\*Missing\*\*')
        assert result is None


class TestAddMissingFrontmatterFields:
    def test_fields_added(self) -> None:
        content = "---\nexisting: val\n---\nbody"
        result = _add_missing_frontmatter_fields(content, {"new_key": "new_val"})
        assert "new_key:" in result
        assert "existing: val" in result

    def test_all_present_no_change(self) -> None:
        content = "---\nexisting: val\n---\nbody"
        result = _add_missing_frontmatter_fields(content, {"existing": "val"})
        assert result == content

    def test_no_frontmatter_returns_unchanged(self) -> None:
        content = "no frontmatter here"
        result = _add_missing_frontmatter_fields(content, {"key": "val"})
        assert result == content


class TestUpdateFrontmatterField:
    def test_overwrite_existing(self) -> None:
        content = "---\nkey: old\nother: val\n---\nbody"
        result = update_frontmatter_field(content, "key", "new")
        assert '"new"' in result
        assert "old" not in result

    def test_add_new_key(self) -> None:
        content = "---\none: val\n---\nbody"
        result = update_frontmatter_field(content, "new_key", "new_val")
        assert "new_key:" in result
        assert "one: val" in result

    def test_no_frontmatter_returns_unchanged(self) -> None:
        content = "no frontmatter"
        result = update_frontmatter_field(content, "key", "val")
        assert result == content
