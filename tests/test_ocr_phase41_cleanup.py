"""Contract tests for OCR Phase 4.1 runtime cleanup semantics."""

from __future__ import annotations


def test_derived_rebuild_does_not_clear_raw_upgradable() -> None:
    from paperforge.worker.ocr_rebuild import _apply_post_rebuild_version_flags

    meta = {
        "derived_stale": True,
        "raw_upgradable": True,
    }

    updated = _apply_post_rebuild_version_flags(meta)

    assert updated["derived_stale"] is False
    assert updated["raw_upgradable"] is True


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
