from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_QUEUE = ROOT / "project" / "current" / "ocr-v2-active-queue.md"
GENERALIZATION = ROOT / "project" / "current" / "ocr-v2-generalization-boundary.md"
REMAINING = ROOT / "project" / "current" / "ocr-v2-remaining-issues-2026-06-18.md"
REBUILD_AUDIT = ROOT / "project" / "current" / "ocr_rebuild_audit.md"
PM = ROOT / "PROJECT-MANAGEMENT.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_queue_file_exists_and_declares_post_readiness_role() -> None:
    text = _text(ACTIVE_QUEUE)
    assert "ACTIVE QUEUE" in text
    assert "stale trace-vs-expectation fixtures" in text or "post-readiness rebuild hardening" in text


def test_rebuild_audit_declares_it_is_an_evidence_surface() -> None:
    text = _text(REBUILD_AUDIT)
    assert "post-readiness audit surface" in text
    assert "evidence source" in text


def test_remaining_issues_file_is_frozen_as_readiness_cycle_residuals() -> None:
    text = _text(REMAINING)
    assert "readiness-cycle residuals" in text


def test_project_management_points_to_active_queue_not_itself() -> None:
    text = _text(PM)
    assert "active queue" in text.lower()
    assert "ocr-v2-active-queue.md" in text


def test_no_active_truth_file_claims_nothing_remains() -> None:
    for path in [ACTIVE_QUEUE, GENERALIZATION, REMAINING, REBUILD_AUDIT, PM]:
        text = _text(path).lower()
        assert "nothing remains" not in text
        assert "merge now" not in text
