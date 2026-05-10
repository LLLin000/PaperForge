from pathlib import Path

from paperforge.doctor.field_validator import (
    validate_entry_fields,
    validate_collection,
    validate_frontmatter_from_file,
)

SAMPLE_REGISTRY = {
    "frontmatter": {
        "zotero_key": {"type": "str", "required": True, "public": True},
        "domain": {"type": "str", "required": True, "public": True},
        "title": {"type": "str", "required": True, "public": True},
        "year": {"type": "str", "required": False, "public": True},
        "doi": {"type": "str", "required": False, "public": True},
        "has_pdf": {"type": "bool", "required": True, "public": True},
        "analyze": {"type": "bool", "required": False, "public": True},
        "ocr_status": {"type": "str", "required": False, "public": True},
    },
}


def test_complete_entry_no_issues():
    entry = {
        "zotero_key": "ABCDEF",
        "domain": "骨科",
        "title": "A Study",
        "year": "2024",
        "doi": "10.1234/test",
        "has_pdf": "true",
        "analyze": "false",
        "ocr_status": "pending",
    }
    issues = validate_entry_fields(entry, "frontmatter", SAMPLE_REGISTRY)
    assert issues == []


def test_missing_required_field():
    entry = {
        "domain": "骨科",
        "title": "A Study",
        "has_pdf": "true",
    }
    issues = validate_entry_fields(entry, "frontmatter", SAMPLE_REGISTRY, "ABCDEF")
    required_errors = [i for i in issues if i["code"] == "MISSING_REQUIRED"]
    assert len(required_errors) == 1
    assert required_errors[0]["severity"] == "error"
    assert required_errors[0]["field"] == "zotero_key"


def test_unknown_field_drift_warning():
    entry = {
        "zotero_key": "ABCDEF",
        "domain": "骨科",
        "title": "A Study",
        "has_pdf": "true",
        "unknown_field": "something",
    }
    issues = validate_entry_fields(entry, "frontmatter", SAMPLE_REGISTRY)
    drift = [i for i in issues if i["code"] == "DRIFT"]
    assert len(drift) == 1
    assert drift[0]["severity"] == "warning"
    assert drift[0]["field"] == "unknown_field"


def test_missing_optional_field():
    entry = {
        "zotero_key": "ABCDEF",
        "domain": "骨科",
        "title": "A Study",
        "has_pdf": "true",
    }
    issues = validate_entry_fields(entry, "frontmatter", SAMPLE_REGISTRY)
    optional_missing = [i for i in issues if i["code"] == "MISSING_OPTIONAL"]
    assert len(optional_missing) > 0
    assert all(i["severity"] == "info" for i in optional_missing)


def test_validate_collection_mixed():
    entries = [
        {"zotero_key": "A1", "domain": "骨科", "title": "T1", "has_pdf": "true"},
        {"zotero_key": "A2", "domain": "骨科", "has_pdf": "true"},
    ]
    result = validate_collection(entries, "frontmatter", SAMPLE_REGISTRY)
    assert result["total_entries"] == 2
    assert result["entries_with_errors"] == 1
    assert "MISSING_REQUIRED" in result["summary"]


def test_validate_frontmatter_valid(tmp_path):
    note = tmp_path / "ABCDEF - Test.md"
    note.write_text(
        "---\nzotero_key: ABCDEF\ndomain: 骨科\ntitle: Test\nhas_pdf: true\n---\n\nSome content",
        encoding="utf-8",
    )
    issues = validate_frontmatter_from_file(note, SAMPLE_REGISTRY)
    required_errors = [i for i in issues if i["severity"] == "error"]
    assert len(required_errors) == 0


def test_validate_frontmatter_no_frontmatter(tmp_path):
    note = tmp_path / "NoFrontmatter.md"
    note.write_text("Just content without frontmatter", encoding="utf-8")
    issues = validate_frontmatter_from_file(note, SAMPLE_REGISTRY)
    assert len(issues) == 1
    assert issues[0]["code"] == "NO_FRONTMATTER"
