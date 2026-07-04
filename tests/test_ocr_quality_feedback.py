"""Tests for the OCR quality feedback sidecar module."""

from __future__ import annotations

from pathlib import Path

import pytest

SCHEMA_VERSION = "ocr_quality_feedback_v1"
SAMPLE_MARK = {
    "marked_by": "test",
    "overall": "correct",
    "result_hash": "hash-abc",
    "fulltext_hash": "fulltext-abc",
    "use_cases": {"reading": "ok", "qa": "ok", "figure_table_reasoning": "ok"},
    "issue_tags": [],
    "notes": "",
}


def _make_feedback(marks: list | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "paper_id": "test-paper",
        "marks": marks or [],
    }


# ---------------------------------------------------------------------------
# C1: write + read roundtrip
# ---------------------------------------------------------------------------


def test_write_read_roundtrip(tmp_path: Path) -> None:
    from paperforge.worker.ocr_quality_feedback import read_feedback, write_feedback

    path = tmp_path / "ocr_quality_feedback.json"
    feedback = _make_feedback([{**SAMPLE_MARK, "notes": "roundtrip"}])

    write_feedback(path, feedback)
    loaded = read_feedback(path)

    assert loaded is not None
    assert loaded["paper_id"] == "test-paper"
    assert len(loaded["marks"]) == 1
    assert loaded["marks"][0]["notes"] == "roundtrip"
    assert loaded["marks"][0]["overall"] == "correct"
def test_write_feedback_requires_result_hash(tmp_path: Path) -> None:
    """write_feedback raises ValueError when a mark lacks result_hash."""
    from paperforge.worker.ocr_quality_feedback import write_feedback

    bad_mark = dict(SAMPLE_MARK)
    del bad_mark["result_hash"]
    feedback = _make_feedback(marks=[bad_mark])
    path = tmp_path / "feedback.json"
    with pytest.raises(ValueError, match="result_hash"):
        write_feedback(path, feedback)


# ---------------------------------------------------------------------------
# C3: append_mark adds, does not replace
# ---------------------------------------------------------------------------


def test_append_mark_grows_marks_list(tmp_path: Path) -> None:
    from paperforge.worker.ocr_quality_feedback import (
        append_mark,
        read_feedback,
    )

    path = tmp_path / "ocr_quality_feedback.json"

    first = append_mark(
        path,
        {**SAMPLE_MARK, "notes": "first"},
        current_result_hash="hash-a",
        current_fulltext_hash="ft-a",
    )
    assert len(first["marks"]) == 1

    second = append_mark(
        path,
        {**SAMPLE_MARK, "notes": "second"},
        current_result_hash="hash-b",
        current_fulltext_hash="ft-b",
    )
    assert len(second["marks"]) == 2

    # Persisted marks reflect the append
    loaded = read_feedback(path)
    assert loaded is not None
    assert len(loaded["marks"]) == 2
    assert loaded["marks"][0]["notes"] == "first"
    assert loaded["marks"][1]["notes"] == "second"

    # Each mark carries its own hashes
    assert loaded["marks"][0]["result_hash"] == "hash-a"
    assert loaded["marks"][1]["result_hash"] == "hash-b"


# ---------------------------------------------------------------------------
# C4: stale hash → status "stale"
# ---------------------------------------------------------------------------


def test_stale_hash_returns_stale_status(tmp_path: Path) -> None:
    from paperforge.worker.ocr_quality_feedback import (
        append_mark,
        resolve_human_validation,
    )

    path = tmp_path / "ocr_quality_feedback.json"

    # Current run uses hash "abc" so mark is fresh
    append_mark(
        path,
        {**SAMPLE_MARK, "overall": "correct"},
        current_result_hash="abc",
        current_fulltext_hash="ft-abc",
    )

    # Now pipeline produces a different hash → mark is stale
    feedback = _make_feedback([{
        **SAMPLE_MARK,
        "overall": "correct",
        "result_hash": "abc",
        "fulltext_hash": "ft-abc",
    }])
    state = resolve_human_validation(feedback, "new-hash-xyz")

    assert state["status"] == "stale"
    assert state["mark_count"] == 1
    assert state["latest_mark"] is not None
    assert state["latest_mark"]["result_hash"] == "abc"


# ---------------------------------------------------------------------------
# C5: resolve_human_validation works without UI (all four status paths)
# ---------------------------------------------------------------------------


def test_resolve_human_validation_all_statuses(tmp_path: Path) -> None:
    from paperforge.worker.ocr_quality_feedback import resolve_human_validation

    # -- unreviewed: no marks --
    result = resolve_human_validation(_make_feedback([]), "hash-current")
    assert result["status"] == "unreviewed"
    assert result["mark_count"] == 0
    assert result["latest_mark"] is None

    # -- confirmed: overall "correct" --
    feedback = _make_feedback([{
        **SAMPLE_MARK,
        "overall": "correct",
        "result_hash": "hash-current",
        "fulltext_hash": "ft-c",
    }])
    result = resolve_human_validation(feedback, "hash-current")
    assert result["status"] == "confirmed"
    assert result["mark_count"] == 1

    # -- confirmed: overall "usable_with_minor_issues" --
    feedback = _make_feedback([{
        **SAMPLE_MARK,
        "overall": "usable_with_minor_issues",
        "result_hash": "hash-current",
        "fulltext_hash": "ft-u",
    }])
    result = resolve_human_validation(feedback, "hash-current")
    assert result["status"] == "confirmed"

    # -- disputed: overall "bad" --
    feedback = _make_feedback([{
        **SAMPLE_MARK,
        "overall": "bad",
        "result_hash": "hash-current",
        "fulltext_hash": "ft-b",
    }])
    result = resolve_human_validation(feedback, "hash-current")
    assert result["status"] == "disputed"

    # -- stale overrides confirmed --
    feedback = _make_feedback([{
        **SAMPLE_MARK,
        "overall": "correct",
        "result_hash": "old-hash",
        "fulltext_hash": "ft-o",
    }])
    result = resolve_human_validation(feedback, "new-hash")
    assert result["status"] == "stale"

    # -- stale overrides disputed --
    feedback = _make_feedback([{
        **SAMPLE_MARK,
        "overall": "bad",
        "result_hash": "old-hash",
        "fulltext_hash": "ft-o",
    }])
    result = resolve_human_validation(feedback, "new-hash")
    assert result["status"] == "stale"
