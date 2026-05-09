from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.adapters.bbt import (
    _identify_main_pdf,
    _normalize_attachment_path,
    collection_fields,
    extract_authors,
    load_export_rows,
    resolve_item_collection_paths,
)


class TestNormalizeAttachmentPath:
    def test_storage_prefix_passthrough(self) -> None:
        result = _normalize_attachment_path("storage:ABCD1234/file.pdf")
        assert result == ("storage:ABCD1234/file.pdf", "storage:ABCD1234/file.pdf", "ABCD1234")

    def test_storage_prefix_backslash_normalization(self) -> None:
        result = _normalize_attachment_path("storage:ABCD1234\\file.pdf")
        assert result == ("storage:ABCD1234/file.pdf", "storage:ABCD1234\\file.pdf", "ABCD1234")

    def test_absolute_windows_path_with_zotero_storage(self) -> None:
        result = _normalize_attachment_path(r"D:\Zotero\storage\ABCD1234\paper.pdf")
        assert result == ("storage:ABCD1234/paper.pdf", r"D:\Zotero\storage\ABCD1234\paper.pdf", "ABCD1234")

    def test_absolute_windows_path_not_in_zotero(self) -> None:
        result = _normalize_attachment_path(r"D:\other\paper.pdf")
        assert result == ("absolute:D:\\other\\paper.pdf", r"D:\other\paper.pdf", "")

    def test_bare_relative_path(self) -> None:
        result = _normalize_attachment_path("EFGH5678/doc.pdf")
        assert result == ("storage:EFGH5678/doc.pdf", "EFGH5678/doc.pdf", "EFGH5678")

    def test_chinese_filename(self) -> None:
        result = _normalize_attachment_path(r"D:\Zotero\storage\ABCD1234\中文论文.pdf")
        assert result == ("storage:ABCD1234/中文论文.pdf", r"D:\Zotero\storage\ABCD1234\中文论文.pdf", "ABCD1234")

    def test_path_with_spaces(self) -> None:
        result = _normalize_attachment_path(r"D:\Zotero\storage\ABCD1234\my paper.pdf")
        assert result == ("storage:ABCD1234/my paper.pdf", r"D:\Zotero\storage\ABCD1234\my paper.pdf", "ABCD1234")

    def test_empty_path_returns_empty(self) -> None:
        assert _normalize_attachment_path("") == ("", "", "")
        assert _normalize_attachment_path(None) == ("", "", "")
        assert _normalize_attachment_path("   ") == ("", "", "")


class TestIdentifyMainPdf:
    def test_single_pdf_becomes_main(self) -> None:
        atts = [{"contentType": "application/pdf", "title": "Full Text", "path": "storage:K/key.pdf"}]
        main, supp = _identify_main_pdf(atts)
        assert main is atts[0]
        assert supp == []

    def test_title_pdf_is_selected(self) -> None:
        atts = [
            {"contentType": "application/pdf", "title": "PDF", "path": "storage:K/main.pdf"},
            {"contentType": "application/pdf", "title": "Supplement", "path": "storage:K/supp.pdf"},
        ]
        main, supp = _identify_main_pdf(atts)
        assert main["title"] == "PDF"
        assert len(supp) == 1
        assert supp[0]["title"] == "Supplement"

    def test_largest_file_by_size(self) -> None:
        atts = [
            {"contentType": "application/pdf", "title": "Small", "size": 100},
            {"contentType": "application/pdf", "title": "Large", "size": 999999},
        ]
        main, supp = _identify_main_pdf(atts)
        assert main["title"] == "Large"
        assert len(supp) == 1

    def test_shortest_title_when_sizes_equal(self) -> None:
        atts = [
            {"contentType": "application/pdf", "title": "A Longer Title Here", "size": 500},
            {"contentType": "application/pdf", "title": "Short", "size": 500},
        ]
        main, supp = _identify_main_pdf(atts)
        assert main["title"] == "Short"

    def test_no_attachments_returns_none(self) -> None:
        main, supp = _identify_main_pdf([])
        assert main is None
        assert supp == []

    def test_no_pdf_attachments(self) -> None:
        atts = [{"contentType": "text/html", "title": "Snapshot"}]
        main, supp = _identify_main_pdf(atts)
        assert main is None
        assert supp == []

    def test_no_size_field_falls_back_to_shortest_title(self) -> None:
        atts = [
            {"contentType": "application/pdf", "title": "Long Title Document"},
            {"contentType": "application/pdf", "title": "AB"},
        ]
        main, supp = _identify_main_pdf(atts)
        assert main["title"] == "AB"

    def test_first_pdf_fallback(self) -> None:
        atts = [
            {"contentType": "application/pdf", "title": "First"},
            {"contentType": "application/pdf", "title": "Second"},
        ]
        main, supp = _identify_main_pdf(atts)
        assert main["title"] == "First"

    def test_non_dict_item_skipped(self) -> None:
        atts = [
            {"contentType": "application/pdf", "title": "PDF", "path": "storage:K/main.pdf"},
            "not a dict",
        ]
        main, supp = _identify_main_pdf(atts)
        assert main is not None
        assert main["title"] == "PDF"


class TestExtractAuthors:
    def test_single_author(self) -> None:
        item = {"creators": [{"creatorType": "author", "firstName": "John", "lastName": "Doe"}]}
        assert extract_authors(item) == ["John Doe"]

    def test_multiple_authors(self) -> None:
        item = {
            "creators": [
                {"creatorType": "author", "firstName": "Alice", "lastName": "Smith"},
                {"creatorType": "author", "firstName": "Bob", "lastName": "Jones"},
            ]
        }
        assert extract_authors(item) == ["Alice Smith", "Bob Jones"]

    def test_skips_non_author_creators(self) -> None:
        item = {
            "creators": [
                {"creatorType": "author", "firstName": "Only", "lastName": "Author"},
                {"creatorType": "editor", "firstName": "Not", "lastName": "Included"},
            ]
        }
        assert extract_authors(item) == ["Only Author"]

    def test_empty_creators(self) -> None:
        assert extract_authors({"creators": []}) == []

    def test_missing_creators_key(self) -> None:
        assert extract_authors({}) == []

    def test_author_with_no_first_name(self) -> None:
        item = {"creators": [{"creatorType": "author", "lastName": "Doe"}]}
        assert extract_authors(item) == ["Doe"]

    def test_author_with_no_last_name(self) -> None:
        item = {"creators": [{"creatorType": "author", "firstName": "John"}]}
        assert extract_authors(item) == ["John"]

    def test_author_with_name_field(self) -> None:
        item = {"creators": [{"creatorType": "author", "name": "Institutional Author"}]}
        assert extract_authors(item) == ["Institutional Author"]


class TestCollectionFields:
    def test_single_path(self) -> None:
        result = collection_fields(["骨科/脊柱"])
        assert result["collections"] == ["骨科/脊柱"]
        assert "骨科" in result["collection_tags"]
        assert "脊柱" in result["collection_tags"]
        assert result["collection_group"] == ["骨科/脊柱"]

    def test_multiple_paths(self) -> None:
        paths = ["骨科/脊柱/颈椎", "骨科/脊柱"]
        result = collection_fields(paths)
        assert len(result["collections"]) == 2
        assert "骨科" in result["collection_tags"]
        assert "脊柱" in result["collection_tags"]
        assert "颈椎" in result["collection_tags"]

    def test_empty_list(self) -> None:
        result = collection_fields([])
        assert result["collections"] == []
        assert result["collection_tags"] == []
        assert result["collection_group"] == []

    def test_nested_path(self) -> None:
        result = collection_fields(["骨科/脊柱/颈椎/后路"])
        assert result["collections"] == ["骨科/脊柱/颈椎/后路"]
        assert result["collection_tags"] == ["骨科", "脊柱", "颈椎", "后路"]

    def test_duplicate_tags_deduplicated(self) -> None:
        result = collection_fields(["骨科/脊柱", "骨科/创伤"])
        assert result["collection_tags"] == ["骨科", "脊柱", "创伤"]

    def test_primary_is_deepest_path(self) -> None:
        result = collection_fields(["运动医学/膝关节", "运动医学"])
        assert result["collection_group"] == ["运动医学/膝关节"]

    def test_whitespace_in_paths(self) -> None:
        result = collection_fields([" 骨科 / 脊柱 "])
        assert "骨科" in result["collection_tags"]
        assert "脊柱" in result["collection_tags"]


class TestResolveItemCollectionPaths:
    def test_single_collection(self) -> None:
        item = {"collections": ["col1"]}
        lookup = {"path_by_key": {"col1": "骨科/脊柱"}, "paths_by_item_id": {}}
        assert resolve_item_collection_paths(item, lookup) == ["骨科/脊柱"]

    def test_multiple_collections(self) -> None:
        item = {"collections": ["col1", "col2"]}
        lookup = {
            "path_by_key": {"col1": "骨科/脊柱", "col2": "运动医学/膝关节"},
            "paths_by_item_id": {},
        }
        result = resolve_item_collection_paths(item, lookup)
        assert "骨科/脊柱" in result
        assert "运动医学/膝关节" in result

    def test_item_id_paths(self) -> None:
        item = {"itemID": 42}
        lookup = {"path_by_key": {}, "paths_by_item_id": {42: ["骨科/创伤"]}}
        assert resolve_item_collection_paths(item, lookup) == ["骨科/创伤"]

    def test_combined_collections_and_item_id(self) -> None:
        item = {"collections": ["col1"], "itemID": 42}
        lookup = {
            "path_by_key": {"col1": "骨科/脊柱"},
            "paths_by_item_id": {42: ["骨科/脊柱/颈椎"]},
        }
        result = resolve_item_collection_paths(item, lookup)
        assert "骨科/脊柱" in result
        assert "骨科/脊柱/颈椎" in result

    def test_empty_item(self) -> None:
        item = {}
        lookup = {"path_by_key": {}, "paths_by_item_id": {}}
        assert resolve_item_collection_paths(item, lookup) == []

    def test_unknown_key_falls_back_to_key(self) -> None:
        item = {"collections": ["unknown_key"]}
        lookup = {"path_by_key": {}, "paths_by_item_id": {}}
        assert resolve_item_collection_paths(item, lookup) == ["unknown_key"]

    def test_deduplication(self) -> None:
        item = {"collections": ["col1"], "itemID": 1}
        lookup = {
            "path_by_key": {"col1": "骨科/脊柱"},
            "paths_by_item_id": {1: ["骨科/脊柱"]},
        }
        assert resolve_item_collection_paths(item, lookup) == ["骨科/脊柱"]

    def test_no_collections_key(self) -> None:
        item = {"key": "ABC123"}
        lookup = {"path_by_key": {}, "paths_by_item_id": {}}
        assert resolve_item_collection_paths(item, lookup) == []


class TestLoadExportRows:
    def test_valid_json_with_items(self, tmp_path: Path) -> None:
        data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test Article",
                    "creators": [{"creatorType": "author", "firstName": "John", "lastName": "Doe"}],
                    "date": "2023",
                    "DOI": "10.1234/test",
                    "PMID": "12345678",
                    "publicationTitle": "Test Journal",
                    "abstractNote": "An abstract.",
                    "collections": ["col1"],
                    "attachments": [
                        {
                            "path": "storage:ABCD1234/paper.pdf",
                            "contentType": "application/pdf",
                            "title": "PDF",
                        }
                    ],
                }
            ],
            "collections": {"col1": {"name": "骨科", "parent": "", "items": []}},
        }
        path = tmp_path / "export.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        rows = load_export_rows(path)
        assert len(rows) == 1
        assert rows[0]["key"] == "ABC123"
        assert rows[0]["title"] == "Test Article"
        assert rows[0]["authors"] == ["John Doe"]
        assert rows[0]["year"] == "2023"
        assert rows[0]["doi"] == "10.1234/test"
        assert rows[0]["pmid"] == "12345678"
        assert rows[0]["pdf_path"] == "storage:ABCD1234/paper.pdf"
        assert rows[0]["collections"] == ["骨科"]

    def test_list_format_data(self, tmp_path: Path) -> None:
        data = [
            {"key": "ITEM1", "title": "Item 1"},
            {"key": "ITEM2", "title": "Item 2"},
        ]
        path = tmp_path / "list.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        rows = load_export_rows(path)
        assert len(rows) == 2
        assert rows[0]["key"] == "ITEM1"
        assert rows[1]["key"] == "ITEM2"

    def test_empty_json_list(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text("[]", encoding="utf-8")
        assert load_export_rows(path) == []

    def test_file_not_found(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_export_rows(path)

    def test_skips_attachment_notes_and_annotations(self, tmp_path: Path) -> None:
        data = {
            "items": [
                {"key": "ART1", "itemType": "journalArticle", "title": "Real Article", "creators": [], "date": "", "collections": [], "attachments": []},
                {"key": "ATT1", "itemType": "attachment", "title": "An Attachment"},
                {"key": "NOT1", "itemType": "note", "title": "A Note"},
                {"key": "ANN1", "itemType": "annotation", "title": "An Annotation"},
            ],
            "collections": {},
        }
        path = tmp_path / "mixed.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        rows = load_export_rows(path)
        assert len(rows) == 1
        assert rows[0]["key"] == "ART1"

    def test_unsupported_format_raises_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(ValueError, match="Unsupported export format"):
            load_export_rows(path)

    def test_pdf_content_type_fallback(self, tmp_path: Path) -> None:
        data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test",
                    "date": "",
                    "creators": [],
                    "collections": [],
                    "attachments": [
                        {
                            "path": "storage:KEY/file.pdf",
                        }
                    ],
                }
            ],
            "collections": {},
        }
        path = tmp_path / "ctype.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        rows = load_export_rows(path)
        assert rows[0]["attachments"][0]["contentType"] == "application/pdf"

    def test_supplementary_pdfs_separated(self, tmp_path: Path) -> None:
        data = {
            "items": [
                {
                    "key": "ABC123",
                    "itemType": "journalArticle",
                    "title": "Test",
                    "date": "",
                    "creators": [],
                    "collections": [],
                    "attachments": [
                        {"path": "storage:K/main.pdf", "contentType": "application/pdf", "title": "PDF"},
                        {"path": "storage:K/supp1.pdf", "contentType": "application/pdf", "title": "Supplement 1"},
                    ],
                }
            ],
            "collections": {},
        }
        path = tmp_path / "supp.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        rows = load_export_rows(path)
        assert rows[0]["pdf_path"] == "storage:K/main.pdf"
        assert rows[0]["supplementary"] == ["storage:K/supp1.pdf"]
