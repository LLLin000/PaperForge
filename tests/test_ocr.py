from pathlib import Path


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
    from paperforge.worker import ocr as ocr_worker

    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    workspace = literature / "AB12CD34 - Test"
    workspace.mkdir()
    note = workspace / "AB12CD34.md"
    note.write_text("""---
zotero_key: "AB12CD34"
title: "Test"
ocr_redo: true
do_ocr: false
ocr_status: done
fulltext_md_path: "[[old_path]]"
---
""", encoding="utf-8")

    (workspace / "fulltext.md").write_text("old workspace copy\n", encoding="utf-8")

    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "AB12CD34"
    ocr_dir.mkdir()
    (ocr_dir / "fulltext.md").write_text("old canonical content\n", encoding="utf-8")

    calls = {}

    def fake_run_ocr(vault_arg, verbose=False, no_progress=False, selected_keys=None):
        calls["selected_keys"] = selected_keys
        new_dir = ocr_root / "AB12CD34"
        (new_dir / "json").mkdir(parents=True, exist_ok=True)
        fulltext = "<!-- page 1 -->\n" + ("A" * 700)
        (new_dir / "fulltext.md").write_text(fulltext, encoding="utf-8")
        (new_dir / "json" / "result.json").write_text("{" + ('"x":1,' * 600) + '"done":true}', encoding="utf-8")
        (new_dir / "meta.json").write_text(
            '{"zotero_key":"AB12CD34","ocr_status":"done","page_count":1,"fulltext_md_path":"",'
            '"markdown_path":"System/PaperForge/ocr/AB12CD34/fulltext.md","json_path":"System/PaperForge/ocr/AB12CD34/json/result.json"}',
            encoding="utf-8",
        )
        return 0

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(ocr_worker, "run_ocr", fake_run_ocr)
    monkeypatch.setattr(ocr_worker, "refresh_index_entry", lambda _vault, _key: None)

    try:
        rc = ocr_worker.ocr_redo_papers(vault, dry_run=False, verbose=True)
        assert rc == 0
    finally:
        monkeypatch.undo()

    content = note.read_text(encoding="utf-8")
    assert 'ocr_redo: false' in content
    assert 'ocr_status: "done"' in content
    assert 'fulltext_md_path: ""' in content
    assert 'do_ocr: true' in content
    assert calls["selected_keys"] == {"AB12CD34"}
    assert not (workspace / "fulltext.md").exists()


def test_ocr_redo_papers_keeps_flag_true_when_rerun_not_done(tmp_path):
    from paperforge.worker import ocr as ocr_worker

    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    workspace = literature / "ZXCV1234 - Test"
    workspace.mkdir()
    note = workspace / "ZXCV1234.md"
    note.write_text("""---
zotero_key: "ZXCV1234"
title: "Test"
ocr_redo: true
do_ocr: false
ocr_status: done
---
""", encoding="utf-8")

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(ocr_worker, "run_ocr", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(ocr_worker, "refresh_index_entry", lambda _vault, _key: None)

    try:
        rc = ocr_worker.ocr_redo_papers(vault, dry_run=False, verbose=True)
        assert rc == 1
    finally:
        monkeypatch.undo()

    content = note.read_text(encoding="utf-8")
    assert 'ocr_redo: true' in content
    assert 'ocr_status: "pending"' in content


def test_postprocess_writes_phase1_artifacts(tmp_path: Path) -> None:
    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "ABCD1234"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"ABCD1234","ocr_status":"done"}', encoding="utf-8"
    )

    page_num, _, _, _ = postprocess_ocr_result(vault, "ABCD1234", [])
    assert page_num == 0
    assert (ocr_dir / "raw" / "raw_meta.json").exists()
    assert (ocr_dir / "raw" / "source_metadata.json").exists()
    assert (ocr_dir / "canonical" / "blocks.raw.jsonl").exists()
    assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()
