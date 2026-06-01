def test_ocr_redo_papers_dry_run_no_changes(tmp_path):
    from paperforge.worker.ocr import ocr_redo_papers

    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    note = literature / "test note.md"
    note.write_text("""---
zotero_key: "ABCD1234"
title: "Test"
ocr_redo: true
ocr_status: done
fulltext_md_path: "[[old_path]]"
---
""", encoding="utf-8")

    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "ABCD1234"
    ocr_dir.mkdir()
    (ocr_dir / "fulltext.md").write_text("old ocr content")

    rc = ocr_redo_papers(vault, dry_run=True, verbose=True)
    assert rc == 0

    content = note.read_text(encoding="utf-8")
    assert "ocr_redo: true" in content
    assert (ocr_dir / "fulltext.md").exists()


def test_ocr_redo_papers_invalid_key_rejected(tmp_path):
    from paperforge.worker.ocr import ocr_redo_papers

    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    note = literature / "bad key.md"
    note.write_text("""---
zotero_key: "../../../etc/passwd"
title: "Evil"
ocr_redo: true
---
""")

    rc = ocr_redo_papers(vault, dry_run=False, verbose=True)
    assert rc == 0
    content = note.read_text(encoding="utf-8")
    assert "ocr_redo: true" in content  # Never touched


def test_ocr_redo_papers_updates_frontmatter(tmp_path):
    from paperforge.worker.ocr import ocr_redo_papers

    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    note = literature / "good note.md"
    note.write_text("""---
zotero_key: "AB12CD34"
title: "Test"
ocr_redo: true
ocr_status: done
fulltext_md_path: "[[old_path]]"
---
""", encoding="utf-8")

    rc = ocr_redo_papers(vault, dry_run=False, verbose=True)
    assert rc == 0

    content = note.read_text(encoding="utf-8")
    assert 'ocr_redo: false' in content
    assert 'ocr_status: "pending"' in content
    assert 'fulltext_md_path: ""' in content
