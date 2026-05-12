from __future__ import annotations

from pathlib import Path

from paperforge.memory.context import get_agent_context


def test_get_agent_context_returns_none_when_no_db():
    assert get_agent_context(Path("/nonexistent/vault")) is None
