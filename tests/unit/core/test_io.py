from __future__ import annotations

import json

from paperforge.core.io import read_json, write_json, write_json_atomic


def test_write_json_atomic_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "state.json"

    write_json_atomic(path, {"ok": True})

    assert path.exists()
    assert read_json(path) == {"ok": True}


def test_write_json_atomic_replaces_existing_file(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"old": True}), encoding="utf-8")

    write_json_atomic(path, {"new": True})

    assert read_json(path) == {"new": True}
    assert not path.with_suffix(".json.tmp").exists()


def test_write_json_uses_atomic_writer(tmp_path):
    path = tmp_path / "state.json"

    write_json(path, {"value": 1})

    assert read_json(path) == {"value": 1}
    assert not path.with_suffix(".json.tmp").exists()
