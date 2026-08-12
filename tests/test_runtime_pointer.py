"""#174 / #143: Python-owned runtime pointer publication."""

from __future__ import annotations

import json

import pytest

from paperforge.runtime_pointer import (
    POINTER_SCHEMA_VERSION,
    pointer_path,
    publish_pointer,
    read_pointer,
)


def test_publish_then_read_roundtrip(tmp_path, monkeypatch) -> None:
    """publish → read returns the exact schema; python_path defaults to the
    running interpreter."""
    monkeypatch.setenv("PAPERFORGE_TEST_HOME", str(tmp_path))  # unused; explicit home below
    publish_pointer(home=tmp_path)
    ptr = read_pointer(home=tmp_path)
    assert ptr is not None
    assert ptr["schema_version"] == POINTER_SCHEMA_VERSION
    assert ptr["python_path"]
    assert ptr["environment_root"]
    assert ptr["paperforge_version"]


def test_publish_is_atomic(tmp_path) -> None:
    """Publication leaves exactly pointer.json — no stray tmp file — and
    overwrites in place (single writer, os.replace)."""
    first = publish_pointer(home=tmp_path)
    second = publish_pointer(home=tmp_path)
    assert first == second == pointer_path(home=tmp_path)
    leftovers = [p.name for p in tmp_path.rglob("*.tmp")]
    assert leftovers == []


def test_read_pointer_absent_or_corrupt(tmp_path) -> None:
    """Reader is fail-soft: absent file, bad JSON, or wrong schema → None,
    never a crash (reader is the plugin; writer is atomic)."""
    assert read_pointer(home=tmp_path) is None
    pointer_path(home=tmp_path).parent.mkdir(parents=True, exist_ok=True)
    pointer_path(home=tmp_path).write_text("{not json", encoding="utf-8")
    assert read_pointer(home=tmp_path) is None
    pointer_path(home=tmp_path).write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    assert read_pointer(home=tmp_path) is None


def test_read_pointer_requires_full_schema(tmp_path) -> None:
    """Schema v1 requires ALL four fields, typed, non-empty, absolute paths
    for python_path/environment_root; partial pointers are invalid → None."""
    d = pointer_path(home=tmp_path)
    d.parent.mkdir(parents=True, exist_ok=True)
    import os

    base = {
        "schema_version": 1,
        "python_path": os.path.abspath(str(tmp_path / "python.exe")),
        "environment_root": os.path.abspath(str(tmp_path / "env")),
        "paperforge_version": "1.0.0",
    }
    d.write_text(json.dumps(base), encoding="utf-8")
    assert read_pointer(home=tmp_path) is not None
    # missing / wrong-typed / empty field
    for key in ("python_path", "environment_root", "paperforge_version"):
        partial = dict(base)
        del partial[key]
        d.write_text(json.dumps(partial), encoding="utf-8")
        assert read_pointer(home=tmp_path) is None, key
    empty = dict(base, paperforge_version="")
    d.write_text(json.dumps(empty), encoding="utf-8")
    assert read_pointer(home=tmp_path) is None
    # relative path
    rel = dict(base, python_path="relative/python.exe")
    d.write_text(json.dumps(rel), encoding="utf-8")
    assert read_pointer(home=tmp_path) is None
