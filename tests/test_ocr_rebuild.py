"""Contract tests for OCR derived-rebuild orchestration (Phase 4)."""

from __future__ import annotations


def test_rebuild_selector_only_targets_derived_stale_papers() -> None:
    """select_papers_for_derived_rebuild must only return papers
    where derived_stale=True, regardless of raw_upgradable status."""
    # This will fail with ModuleNotFoundError until paperforge/worker/ocr_rebuild.py exists
    from paperforge.worker.ocr_rebuild import select_papers_for_derived_rebuild

    papers = [
        {"zotero_key": "A", "derived_stale": True, "raw_upgradable": False},
        {"zotero_key": "B", "derived_stale": False, "raw_upgradable": True},
    ]

    selected = select_papers_for_derived_rebuild(papers)

    assert selected == ["A"]
