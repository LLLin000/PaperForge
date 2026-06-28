from __future__ import annotations


def test_sync_detects_derived_drift_without_failing_sync(tmp_path) -> None:
    from paperforge.services.sync_service import summarize_ocr_version_actions

    summary = summarize_ocr_version_actions(
        papers=[
            {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
            {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
        ]
    )

    assert summary["derived_rebuild_count"] == 1
    assert summary["raw_upgrade_count"] == 1


def test_sync_runtime_summary_can_schedule_derived_rebuild_without_inline_execution() -> None:
    from paperforge.services.sync_service import summarize_ocr_runtime_followups

    summary = summarize_ocr_runtime_followups(
        papers=[
            {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
            {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
        ]
    )

    assert summary["derived_rebuild_count"] == 1
    assert summary["derived_rebuild_mode"] in {"deferred", "queued", "best_effort"}


def test_dirty_runtime_files_suppress_auto_derived_rebuild() -> None:
    from paperforge.services.sync_service import summarize_ocr_runtime_followups

    with_dirty = summarize_ocr_runtime_followups(
        papers=[
            {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
        ],
        dirty_runtime_files=True,
    )

    assert with_dirty["derived_rebuild_mode"] == "suppressed_dirty_runtime"
    assert with_dirty["suppressed_keys"] == ["A"]


def test_sync_legacy_scan_detects_papers_without_version_state() -> None:
    """Sync's OCR runtime scan should identify legacy papers
    that have ocr_status=done but no version state."""
    from paperforge.services.sync_service import summarize_ocr_runtime_followups

    summary = summarize_ocr_runtime_followups(
        papers=[
            {"zotero_key": "LEGACY", "derived_stale": False, "raw_upgradable": False, "is_legacy": True},
            {"zotero_key": "MODERN", "derived_stale": False, "raw_upgradable": False, "is_legacy": False},
            {"zotero_key": "STALE", "derived_stale": True, "raw_upgradable": False, "is_legacy": False},
        ]
    )

    assert summary["legacy_count"] == 1
    assert summary["legacy_keys"] == ["LEGACY"]
