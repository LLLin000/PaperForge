from __future__ import annotations

from pathlib import Path

from paperforge.memory.refresh import refresh_paper


def test_refresh_paper_returns_false_when_no_db():
    assert refresh_paper(Path("/nonexistent/vault"), {"zotero_key": "KEY001"}) is False


def test_refresh_paper_returns_false_for_empty_key():
    assert refresh_paper(Path("/nonexistent/vault"), {}) is False


def test_refresh_paper_returns_false_for_missing_key():
    assert refresh_paper(Path("/nonexistent/vault"), {"title": "No Key"}) is False
