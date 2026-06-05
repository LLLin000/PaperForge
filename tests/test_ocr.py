from pathlib import Path


def test_ocr_redo_papers_dry_run_no_changes(tmp_path):
    from paperforge.worker.ocr import ocr_redo_papers

    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    note = literature / "test note.md"
    note.write_text(
        """---
zotero_key: "ABCD1234"
title: "Test"
ocr_redo: true
ocr_status: done
fulltext_md_path: "[[old_path]]"
---
""",
        encoding="utf-8",
    )

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
    note.write_text(
        """---
zotero_key: "AB12CD34"
title: "Test"
ocr_redo: true
do_ocr: false
ocr_status: done
fulltext_md_path: "[[old_path]]"
---
""",
        encoding="utf-8",
    )

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
    assert "ocr_redo: false" in content
    assert 'ocr_status: "done"' in content
    assert 'fulltext_md_path: ""' in content
    assert "do_ocr: true" in content
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
    note.write_text(
        """---
zotero_key: "ZXCV1234"
title: "Test"
ocr_redo: true
do_ocr: false
ocr_status: done
---
""",
        encoding="utf-8",
    )

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(ocr_worker, "run_ocr", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(ocr_worker, "refresh_index_entry", lambda _vault, _key: None)

    try:
        rc = ocr_worker.ocr_redo_papers(vault, dry_run=False, verbose=True)
        assert rc == 1
    finally:
        monkeypatch.undo()

    content = note.read_text(encoding="utf-8")
    assert "ocr_redo: true" in content
    assert 'ocr_status: "pending"' in content


def test_ocr_redo_rebuilds_phase1_artifacts(tmp_path: Path) -> None:
    """Verify ocr redo produces all Phase 1 artifacts."""
    from paperforge.worker import ocr as ocr_worker

    key = "REDO0012"
    vault = tmp_path / "vault"
    vault.mkdir()
    literature = vault / "Resources" / "Literature" / "test_domain"
    literature.mkdir(parents=True)

    workspace = literature / f"{key} - Test"
    workspace.mkdir()
    note = workspace / f"{key}.md"
    note.write_text(
        f"""---
zotero_key: "{key}"
title: "Test"
ocr_redo: true
do_ocr: false
ocr_status: done
fulltext_md_path: "[[old_path]]"
---
""",
        encoding="utf-8",
    )

    (workspace / "fulltext.md").write_text("old workspace copy\n", encoding="utf-8")

    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / key
    ocr_dir.mkdir()
    (ocr_dir / "fulltext.md").write_text("old canonical content\n", encoding="utf-8")

    def fake_run_ocr(vault_arg, verbose=False, no_progress=False, selected_keys=None):
        new_dir = ocr_root / key
        (new_dir / "json").mkdir(parents=True, exist_ok=True)
        (new_dir / "raw").mkdir(parents=True, exist_ok=True)
        (new_dir / "canonical").mkdir(parents=True, exist_ok=True)
        (new_dir / "structure").mkdir(parents=True, exist_ok=True)
        fulltext = "<!-- page 1 -->\n" + ("A" * 700)
        (new_dir / "fulltext.md").write_text(fulltext, encoding="utf-8")
        (new_dir / "json" / "result.json").write_text("{" + ('"x":1,' * 600) + '"done":true}', encoding="utf-8")
        (new_dir / "raw" / "raw_meta.json").write_text('{"ocr_provider":"PaddleOCR"}', encoding="utf-8")
        (new_dir / "raw" / "source_metadata.json").write_text(f'{{"zotero_key":"{key}"}}', encoding="utf-8")
        (new_dir / "canonical" / "blocks.raw.jsonl").write_text(f'{{"paper_id":"{key}","page":1}}\n', encoding="utf-8")
        (new_dir / "structure" / "blocks.structured.jsonl").write_text(
            f'{{"paper_id":"{key}","role":"body_paragraph"}}\n', encoding="utf-8"
        )
        import json

        meta = {
            "zotero_key": key,
            "ocr_status": "done",
            "page_count": 1,
            "fulltext_md_path": "",
            "markdown_path": f"System/PaperForge/ocr/{key}/fulltext.md",
            "json_path": f"System/PaperForge/ocr/{key}/json/result.json",
            "raw_version": {"ocr_model": "PaddleOCR-VL-1.6"},
            "derived_version": {"renderer_version": "1.0.0-compat"},
        }
        (new_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return 0

    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(ocr_worker, "run_ocr", fake_run_ocr)
    monkeypatch.setattr(ocr_worker, "refresh_index_entry", lambda _vault, _key: None)

    try:
        rc = ocr_worker.ocr_redo_papers(vault, dry_run=False, verbose=True)
        assert rc == 0
    finally:
        monkeypatch.undo()

    # Verify Phase 1 artifacts exist after redo
    assert (ocr_dir / "json" / "result.json").exists()
    assert (ocr_dir / "raw" / "raw_meta.json").exists()
    assert (ocr_dir / "canonical" / "blocks.raw.jsonl").exists()
    assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()

    # Verify compatibility outputs still exist
    assert (ocr_dir / "fulltext.md").exists()

    # Verify ocr_redo flipped to false
    content = note.read_text(encoding="utf-8")
    assert "ocr_redo: false" in content


def test_postprocess_preserves_compatibility_outputs(tmp_path: Path) -> None:
    """Verify that postprocess still writes compat fulltext.md and result.json."""
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "COMPAT1"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text('{"zotero_key":"COMPAT1","ocr_status":"done"}', encoding="utf-8")

    page_num, md_path, json_path, fulltext_md_path = postprocess_ocr_result(vault, "COMPAT1", [])

    assert page_num == 0
    assert (ocr_dir / "fulltext.md").exists()
    assert (ocr_dir / "json" / "result.json").exists()
    assert isinstance(md_path, str)
    assert isinstance(json_path, str)
    assert isinstance(fulltext_md_path, str)


def test_postprocess_writes_phase1_artifacts(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "ABCD1234"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"ABCD1234","ocr_status":"done","ocr_model":"PaddleOCR-VL-1.6"}',
        encoding="utf-8",
    )

    page_num, _, _, _ = postprocess_ocr_result(vault, "ABCD1234", [])
    assert page_num == 0
    assert (ocr_dir / "raw" / "raw_meta.json").exists()
    assert (ocr_dir / "raw" / "source_metadata.json").exists()
    assert (ocr_dir / "canonical" / "blocks.raw.jsonl").exists()
    assert (ocr_dir / "structure" / "blocks.structured.jsonl").exists()

    meta = json.loads((ocr_dir / "meta.json").read_text(encoding="utf-8"))
    assert "zotero_key" in meta  # original field preserved
    assert "ocr_status" in meta  # original field preserved
    assert "raw_version" in meta
    assert meta["raw_version"]["ocr_model"] == "PaddleOCR-VL-1.6"
    assert "derived_version" in meta
    assert "renderer_version" in meta["derived_version"]


def test_postprocess_meta_json_preserves_original_fields(tmp_path: Path) -> None:
    """Verify postprocess preserves pre-Phase-1 meta.json fields."""
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "METAORIG"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"METAORIG","ocr_status":"done","ocr_model":"PaddleOCR",'
        '"page_count":3,"source_pdf":"nonexistent.pdf"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "METAORIG", [])

    meta = json.loads((ocr_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("zotero_key") == "METAORIG"
    assert meta.get("ocr_status") == "done"
    assert meta.get("page_count") == 3
    assert "raw_version" in meta
    assert "derived_version" in meta


def test_postprocess_writes_resolved_metadata(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "META001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"META001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "META001", [])

    assert (ocr_dir / "raw" / "raw_meta.json").exists()
    assert (ocr_dir / "raw" / "source_metadata.json").exists()
    # Phase 2: resolved_metadata.json does not exist yet — this test will fail
    # The assertion goes here as a contract test
    assert (ocr_dir / "metadata" / "resolved_metadata.json").exists()


def test_postprocess_writes_figure_inventory(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "FIG001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"FIG001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "FIG001", [])

    # Phase 2: figure_inventory.json does not exist yet -- test will fail
    assert (ocr_dir / "structure" / "figure_inventory.json").exists()


def test_postprocess_writes_table_inventory(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "TBL001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"TBL001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "TBL001", [])

    # Phase 2: table_inventory.json does not exist yet -- will fail
    assert (ocr_dir / "structure" / "table_inventory.json").exists()


def test_postprocess_creates_object_directories(tmp_path: Path) -> None:
    """Verify postprocess creates object directories even with empty results."""
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "OBJ001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"OBJ001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "OBJ001", [])

    # Phase 2: object artifact directories are created during postprocess
    assert (ocr_dir / "render" / "figures").exists()
    assert (ocr_dir / "render" / "tables").exists()
    assert (ocr_dir / "assets" / "figures").exists()
    assert (ocr_dir / "assets" / "tables").exists()
    assert (ocr_dir / "assets" / "orphans").exists()


def test_postprocess_writes_render_fulltext(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "RNDR001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"RNDR001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "RNDR001", [])

    # Phase 3: render/fulltext.md does not exist yet -- this test will fail
    assert (ocr_dir / "render" / "fulltext.md").exists()


def test_postprocess_writes_ocr_health(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "HLTH001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"HLTH001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "HLTH001", [])

    # Phase 3: health/ocr_health.json does not exist yet -- this test will fail
    assert (ocr_dir / "health" / "ocr_health.json").exists()


def test_version_state_classifiable_from_meta_json(tmp_path: Path) -> None:
    import json

    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        json.dumps({"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}),
        encoding="utf-8",
    )
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    ocr_dir = ocr_root / "VST001"
    ocr_dir.mkdir()
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"VST001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )

    _, _, _, _ = postprocess_ocr_result(vault, "VST001", [])

    meta = json.loads((ocr_dir / "meta.json").read_text(encoding="utf-8"))
    from paperforge.worker.ocr_versions import classify_version_state

    state = classify_version_state(
        meta=meta,
        expected_raw={"ocr_model": meta["raw_version"]["ocr_model"], "ocr_provider": "PaddleOCR"},
        expected_derived={"renderer_version": "2.0.0"},
    )
    assert "raw_upgradable" in state
    assert "derived_stale" in state
