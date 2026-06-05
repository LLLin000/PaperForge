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
