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


def test_migrate_to_workspace_deletes_existing_workspace_fulltext(tmp_path, monkeypatch):
    from paperforge.worker import sync

    vault = tmp_path / "vault"
    literature = vault / "Resources" / "Literature"
    ocr = vault / "PaperForge" / "ocr"
    domain_dir = literature / "test_domain"
    domain_dir.mkdir(parents=True)

    key = "ABCD1234"
    title = "Test Paper"
    flat_note = domain_dir / f"{key} - {title}.md"
    flat_note.write_text(
        "---\n"
        f'title: "{title}"\n'
        f"zotero_key: {key}\n"
        "---\n\n"
        "# Test Paper\n",
        encoding="utf-8",
    )

    workspace_dir = domain_dir / f"{key} - {title}"
    workspace_dir.mkdir()
    (workspace_dir / f"{key}.md").write_text("# Existing note\n", encoding="utf-8")
    (workspace_dir / "fulltext.md").write_text("old workspace fulltext\n", encoding="utf-8")

    monkeypatch.setattr(sync.asset_index, "read_index", lambda _vault: {"items": []})

    paths = {
        "literature": literature,
        "ocr": ocr,
    }

    sync.migrate_to_workspace(vault, paths)

    assert not (workspace_dir / "fulltext.md").exists()
