from __future__ import annotations

from paperforge.memory.query import get_memory_status
from tests.conftest import canonical_test_config


def test_get_memory_status_returns_needs_rebuild_when_no_db(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    result = get_memory_status(vault)
    assert result["db_exists"] is False
    assert result["needs_rebuild"] is True


def test_is_lock_failure_distinguishes_busy_from_corruption():
    from paperforge.memory.query import _is_lock_failure

    assert _is_lock_failure(TimeoutError("lock timeout"))
    assert _is_lock_failure(Exception("database is locked"))
    assert _is_lock_failure(Exception("database table is locked: papers"))
    assert not _is_lock_failure(Exception("no such table: papers"))
    assert not _is_lock_failure(Exception("database disk image is malformed"))


def test_get_memory_status_marks_locked_on_barrier_timeout(tmp_path, monkeypatch):
    """A reader-barrier timeout must NOT cascade into schema_ok=False (which
    the probe previously read as memory.db_corrupt — 'retrieval index
    corrupted' while the DB was healthy)."""
    from paperforge.memory.query import get_memory_status

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    db_path = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b"placeholder")

    def _raise_timeout(*a, **k):
        raise TimeoutError("lock timeout")

    monkeypatch.setattr("paperforge.memory.query.open_live_reader", _raise_timeout)
    result = get_memory_status(vault)
    assert result["locked"] is True
    assert result["db_exists"] is True
