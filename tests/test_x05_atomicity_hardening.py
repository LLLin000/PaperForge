"""X05 — I/O/crash atomicity + recovery; never leaves corrupt/half state."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from paperforge.runtime_pointer import publish_pointer, read_pointer, pointer_path


def test_X05_crash_between_tmp_write_and_rename_leaves_prior_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Injection point: crash (hard process death) after temp file is written
    but before os.replace commits. The published pointer must keep the prior
    valid value; no half-written pointer is observed."""
    publish_pointer(home=tmp_path, paperforge_version="1.0.0")
    original = read_pointer(home=tmp_path)
    assert original is not None

    # Simulate a crash (no cleanup) at the rename boundary.
    def _boom(*_a, **_k):
        raise RuntimeError("crash before rename")

    monkeypatch.setattr("os.replace", _boom)
    with pytest.raises(RuntimeError):
        publish_pointer(home=tmp_path, paperforge_version="2.0.0")

    # Recovery: atomicity holds — prior pointer still valid; temp may linger
    # but is never read as a committed pointer.
    assert read_pointer(home=tmp_path) == original
    assert pointer_path(home=tmp_path).read_text(encoding="utf-8").find("1.0.0") != -1


def test_X05_malformed_pointer_never_overrides_valid_state(tmp_path: Path) -> None:
    """Malformed (half-written) pointer is rejected; never a partial dict."""
    path = pointer_path(home=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"schema_version": 1, "python_path": "/x', encoding="utf-8")
    assert read_pointer(home=tmp_path) is None

