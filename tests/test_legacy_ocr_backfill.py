from __future__ import annotations


def test_classify_legacy_ocr_paper_detects_missing_version_state() -> None:
    from paperforge.worker.ocr_versions import classify_legacy_ocr_state

    result = classify_legacy_ocr_state({
        "zotero_key": "LEGACY001",
        "ocr_status": "done",
    })

    assert result["is_legacy"] is True
    assert "raw_version" not in result["missing_keys"]
    assert "derived_version" not in result["missing_keys"]
    # No version state at all
    assert result["can_backfill"] is True


def test_modern_paper_is_not_classified_legacy() -> None:
    from paperforge.worker.ocr_versions import classify_legacy_ocr_state

    result = classify_legacy_ocr_state({
        "zotero_key": "MODERN001",
        "ocr_status": "done",
        "raw_version": {"ocr_provider": "PaddleOCR"},
        "derived_version": {"renderer_version": "2.0.0"},
    })

    assert result["is_legacy"] is False


def test_detect_version_mismatch_still_classified_modern() -> None:
    """A paper with version state but mismatched values is NOT legacy --
    it's a modern paper needing upgrade/stale update, not backfill."""
    from paperforge.worker.ocr_versions import classify_legacy_ocr_state

    result = classify_legacy_ocr_state({
        "zotero_key": "MISMATCH001",
        "ocr_status": "done",
        "raw_version": {"ocr_provider": "OldProvider", "ocr_model": "old"},
        "derived_version": {"renderer_version": "1.0.0"},
    })

    assert result["is_legacy"] is False
    assert result["has_version_state"] is True


def test_backfill_from_result_rebuilds_derived_artifacts(tmp_path) -> None:
    from paperforge.worker.ocr_versions import classify_legacy_ocr_state

    # A legacy paper dir with result.json but no version state
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}',
        encoding="utf-8",
    )
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "LEGACY001"
    ocr_dir.mkdir(parents=True)
    # Has result.json (old OCR) but no version state
    (ocr_dir / "json").mkdir(parents=True)
    (ocr_dir / "json" / "result.json").write_text(
        '{"pages": [{"page": {"text": "legacy text"}}]}',
        encoding="utf-8",
    )

    state = classify_legacy_ocr_state({"zotero_key": "LEGACY001", "ocr_status": "done"}, ocr_dir=ocr_dir)
    assert state["is_legacy"] is True
    assert state["has_result_json"] is True


def test_backfill_from_result_rebuilds_all_derived_artifacts(tmp_path) -> None:
    from paperforge.worker.ocr_rebuild import backfill_from_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}',
        encoding="utf-8",
    )
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "BFL002"
    ocr_dir.mkdir(parents=True)
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"BFL002","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )
    (ocr_dir / "json").mkdir(parents=True)
    (ocr_dir / "json" / "result.json").write_text(
        '{"pages": [{"layoutParsingResults": [{"prunedResult": {"parsing_res_list": []}}]}]}',
        encoding="utf-8",
    )

    result = backfill_from_result(vault, "BFL002")

    assert result["backfill_status"] == "done"
    assert result["paper_key"] == "BFL002"
    # Verify derived artifacts exist
    assert (ocr_dir / "index" / "role-index.json").exists()
    assert (ocr_dir / "health" / "ocr_health.json").exists()
    assert (ocr_dir / "render" / "fulltext.md").exists()
    # Verify backfill metadata
    meta = __import__("json").loads((ocr_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("is_backfilled") is True
    assert "backfilled_at" in meta


def test_backfill_from_result_skips_if_no_result_json(tmp_path) -> None:
    from paperforge.worker.ocr_rebuild import backfill_from_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}',
        encoding="utf-8",
    )
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "NODATA"
    ocr_dir.mkdir(parents=True)
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"NODATA","ocr_status":"done"}',
        encoding="utf-8",
    )

    result = backfill_from_result(vault, "NODATA")

    assert result["backfill_status"] == "skipped_no_result"


def test_backfill_from_result_handles_list_format(tmp_path) -> None:
    """Handle the case where result.json is already a list (current format)."""
    from paperforge.worker.ocr_rebuild import backfill_from_result

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "System", "resources_dir": "Resources"}}',
        encoding="utf-8",
    )
    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "LIST001"
    ocr_dir.mkdir(parents=True)
    (ocr_dir / "meta.json").write_text(
        '{"zotero_key":"LIST001","ocr_status":"done","ocr_model":"PaddleOCR"}',
        encoding="utf-8",
    )
    (ocr_dir / "json").mkdir(parents=True)
    (ocr_dir / "json" / "result.json").write_text(
        '[{"layoutParsingResults": [{"prunedResult": {"parsing_res_list": []}}]}]',
        encoding="utf-8",
    )

    result = backfill_from_result(vault, "LIST001")

    assert result["backfill_status"] == "done"
