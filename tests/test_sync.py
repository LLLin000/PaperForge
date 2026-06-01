def test_frontmatter_note_writes_ocr_redo_false_by_default():
    from paperforge.worker.sync import frontmatter_note

    entry = {
        "title": "Test Paper",
        "zotero_key": "ABCD1234",
        "citation_key": "test2024",
        "year": "2024",
        "journal": "Test Journal",
        "first_author": "Smith",
        "domain": "test",
        "doi": "",
        "pmid": "",
        "collections": [],
        "collection_tags": [],
        "impact_factor": "",
        "abstract": "",
        "has_pdf": False,
        "do_ocr": False,
        "analyze": False,
        "ocr_status": "pending",
        "deep_reading_status": "pending",
        "pdf_path": "",
        "fulltext_path": "",
    }

    result = frontmatter_note(entry)
    assert "ocr_redo: false" in result


def test_frontmatter_note_preserves_ocr_redo_true():
    from paperforge.worker.sync import frontmatter_note

    entry = {
        "title": "Test Paper",
        "zotero_key": "ABCD1234",
        "citation_key": "test2024",
        "year": "2024",
        "journal": "Test Journal",
        "first_author": "Smith",
        "domain": "test",
        "doi": "",
        "pmid": "",
        "collections": [],
        "collection_tags": [],
        "impact_factor": "",
        "abstract": "",
        "has_pdf": False,
        "do_ocr": False,
        "analyze": False,
        "ocr_status": "pending",
        "deep_reading_status": "pending",
        "pdf_path": "",
        "fulltext_path": "",
    }

    result = frontmatter_note(entry, preserved_ocr_redo=True)
    assert "ocr_redo: true" in result
    assert "ocr_redo: false" not in result
