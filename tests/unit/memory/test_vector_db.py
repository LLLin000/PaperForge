from __future__ import annotations

from paperforge.memory.vector_db import (
    get_vector_build_state_path,
    read_vector_build_state,
    write_vector_build_state,
    mark_vector_build_state,
)


def test_vector_build_state_defaults_when_missing(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    state = read_vector_build_state(vault)
    assert state["status"] == "idle"
    assert state["current"] == 0


def test_vector_build_state_roundtrip(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    original = {
        "status": "running", "current": 5, "total": 20,
        "paper_id": "ABC12345", "last_update": "now",
        "started_at": "", "finished_at": "",
        "resume_supported": True, "mode": "local",
        "model": "bge-small", "message": "", "pid": 0,
    }
    write_vector_build_state(vault, original)
    loaded = read_vector_build_state(vault)
    assert loaded == original


def test_mark_vector_build_state_updates_field(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    write_vector_build_state(vault, {"status": "idle", "current": 0, "total": 0})
    mark_vector_build_state(vault, current=10, paper_id="XYZ")
    state = read_vector_build_state(vault)
    assert state["current"] == 10
    assert state["paper_id"] == "XYZ"
