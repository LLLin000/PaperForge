from __future__ import annotations

from pathlib import Path

from paperforge.memory.refresh import refresh_paper


def test_refresh_paper_returns_false_when_no_db():
    assert refresh_paper(Path("/nonexistent/vault"), "KEY001") is False
