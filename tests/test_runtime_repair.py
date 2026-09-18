"""#174 / #143: runtime lifecycle repair — a DISTINCT operation from the
literature repair, with #137 NDJSON + cancellation."""

from __future__ import annotations

import json

from paperforge.worker.runtime_repair import perform_runtime_repair


def test_no_pointer_reports_clean_error(tmp_path, monkeypatch) -> None:
    """No published pointer → the runtime bootstrap must run; not a silent
    success and never a literature-repair fallback."""

    monkeypatch.setattr("paperforge.runtime_pointer.read_pointer", lambda: None)
    result = perform_runtime_repair()
    assert result["ok"] is False
    assert "no runtime pointer" in result["error"]


def test_vector_extras_present_rejects_broken_package_import(monkeypatch) -> None:
    import builtins

    from paperforge.setup import runtime

    real_import = builtins.__import__

    def broken_import(name, *args, **kwargs):
        if name == "openai":
            raise ModuleNotFoundError("missing package file")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)

    assert runtime.vector_extras_present() is False


def test_ndjson_stream_and_republication(tmp_path, monkeypatch, capsys) -> None:
    """With a pointer and extras present: start → phases → result terminal,
    and the pointer is RE-published (Python stays the sole writer)."""
    import contextlib as _cl
    import io as _io

    ptr = {
        "python_path": r"C:\Python311\python.exe",
        "environment_root": r"C:\Python311",
        "paperforge_version": "1.5.15",
    }
    published = {}

    monkeypatch.setattr("paperforge.runtime_pointer.read_pointer", lambda: dict(ptr))
    monkeypatch.setattr("paperforge.setup.runtime.vector_extras_present", lambda: True)

    monkeypatch.setattr("subprocess.run", lambda *a, **k: _FakeCompleted())

    def fake_publish(**kw):
        published.update(kw)

    monkeypatch.setattr("paperforge.runtime_pointer.publish_pointer", fake_publish)
    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        result = perform_runtime_repair(ndjson=True)
    events = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
    ev = [e["event"] for e in events]
    assert ev[0] == "start" and ev[-1] == "result", ev
    assert all(e["operation"] == "foundation.repair" for e in events)
    assert result["ok"] is True
    assert published["paperforge_version"] == "1.5.15"


def test_missing_pointed_extras_repair_the_pointer_target(tmp_path, monkeypatch) -> None:
    """A repair must install into the pointer target, never the caller runtime."""
    import contextlib as _cl
    import io as _io

    ptr = {
        "python_path": r"C:\Python311\python.exe",
        "environment_root": r"C:\Python311",
        "paperforge_version": "1.5.15",
    }
    installs: list[dict[str, str]] = []
    checks = iter([(False, ""), (True, "1.5.15")])

    monkeypatch.setattr("paperforge.runtime_pointer.read_pointer", lambda: dict(ptr))
    monkeypatch.setattr(
        "paperforge.setup.runtime.verify_runtime_in_child",
        lambda _python_path: next(checks),
    )
    monkeypatch.setattr(
        "paperforge.setup.runtime.ensure_runtime_dependencies",
        lambda **kwargs: installs.append(kwargs) or _OkResult(),
    )
    published = {}
    monkeypatch.setattr("paperforge.runtime_pointer.publish_pointer", lambda **kw: published.update(kw))
    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        result = perform_runtime_repair(ndjson=True)

    assert result["ok"] is True
    assert installs == [
        {
            "python_path": r"C:\Python311\python.exe",
            "expected_version": "1.5.15",
        }
    ]
    assert published["paperforge_version"] == "1.5.15"


class _FakeCompleted:
    returncode = 0
    stdout = "1.5.15"


class _OkResult:
    ok = True
    message = "ok"
