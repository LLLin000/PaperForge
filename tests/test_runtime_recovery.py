
from __future__ import annotations

import json
from pathlib import Path

import paperforge
from paperforge.runtime_pointer import pointer_path, read_pointer


class _OkResult:
    ok = True
    message = "ok"


def test_broken_pointer_recovers_through_repair(tmp_path, monkeypatch) -> None:
    """A pointer at an unusable Python must be replaced by a validated
    pointer at the current interpreter via runtime repair alone."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    ptr_file = pointer_path(home=home)
    ptr_file.parent.mkdir(parents=True, exist_ok=True)
    ptr_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python_path": str(tmp_path / "bare" / "python.exe"),
                "environment_root": str(tmp_path / "bare"),
                "paperforge_version": "0.0.0",
            }
        ),
        encoding="utf-8",
    )

    def fake_verify(path):
        if str(path).endswith("python.exe") and "bare" in str(path):
            return False, ""
        import sys

        return True, paperforge.__version__

    monkeypatch.setattr("paperforge.setup.runtime.verify_runtime_in_child", fake_verify)
    monkeypatch.setattr(
        "paperforge.setup.runtime.ensure_runtime_dependencies",
        lambda **kwargs: _OkResult(),
    )

    from paperforge.worker.runtime_repair import perform_runtime_repair

    result = perform_runtime_repair()
    assert result["ok"] is True

    recovered = read_pointer(home=home)
    assert recovered is not None
    import sys

    assert recovered["python_path"] == sys.executable
    assert recovered["paperforge_version"] == paperforge.__version__
