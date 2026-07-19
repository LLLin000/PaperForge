from __future__ import annotations

from pathlib import Path

from paperforge.memory.query import get_memory_status


def test_get_memory_status_returns_needs_rebuild_when_no_db():
    result = get_memory_status(Path("/nonexistent/vault"))
    assert result["db_exists"] is False
    assert result["needs_rebuild"] is True
