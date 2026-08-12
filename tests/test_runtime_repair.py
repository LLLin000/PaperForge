"""#174 / #143: runtime lifecycle repair — a DISTINCT operation from the
literature repair, with #137 NDJSON + cancellation."""

from __future__ import annotations

import json

from paperforge.worker.runtime_repair import perform_runtime_repair


def test_no_pointer_reports_clean_error(tmp_path, monkeypatch) -> None:
    """No published pointer → the runtime bootstrap must run; not a silent
    success and never a literature-repair fallback."""
    from paperforge.runtime_pointer import pointer_path

    monkeypatch.setattr("paperforge.runtime_pointer.read_pointer",
                        lambda: None)
    result = perform_runtime_repair()
    assert result["ok"] is False
    assert "no runtime pointer" in result["error"]


def test_ndjson_stream_and_republication(tmp_path, monkeypatch, capsys) -> None:
    """With a pointer and extras present: start → phases → result terminal,
    and the pointer is RE-published (Python stays the sole writer)."""
    import io as _io
    import contextlib as _cl

    from paperforge.worker import runtime_repair as mod

    ptr = {
        "python_path": r"C:\Python311\python.exe",
        "environment_root": r"C:\Python311",
        "paperforge_version": "1.5.15",
    }
    published = {}

    monkeypatch.setattr("paperforge.runtime_pointer.read_pointer",
                        lambda: dict(ptr))
    monkeypatch.setattr("paperforge.setup.runtime.vector_extras_present",
                        lambda: True)

    monkeypatch.setattr("subprocess.run",
                        lambda *a, **k: _FakeCompleted())

    def fake_publish(**kw):
        published.update(kw)

    monkeypatch.setattr("paperforge.runtime_pointer.publish_pointer",
                        fake_publish)
    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        result = perform_runtime_repair(ndjson=True)
    events = [json.loads(l) for l in buf.getvalue().splitlines() if l.strip()]
    ev = [e["event"] for e in events]
    assert ev[0] == "start" and ev[-1] == "result", ev
    assert all(e["operation"] == "foundation.repair" for e in events)
    assert result["ok"] is True
    assert published["paperforge_version"] == "1.5.15"


def test_missing_extras_reen_ensure_republicates(tmp_path, monkeypatch) -> None:
    """Vector extras missing → re-ensure (fresh verify) then re-publish."""
    import io as _io
    import contextlib as _cl

    from paperforge.worker import runtime_repair as mod

    ptr = {
        "python_path": r"C:\Python311\python.exe",
        "environment_root": r"C:\Python311",
        "paperforge_version": "1.5.15",
    }
    monkeypatch.setattr("paperforge.runtime_pointer.read_pointer",
                        lambda: dict(ptr))
    monkeypatch.setattr("paperforge.setup.runtime.vector_extras_present",
                        lambda: False)
    monkeypatch.setattr(
        "paperforge.setup.runtime.ensure_runtime_dependencies",
        lambda: _OkResult(),
    )
    monkeypatch.setattr("subprocess.run",
                        lambda *a, **k: _FakeCompleted())
    published = {}
    monkeypatch.setattr("paperforge.runtime_pointer.publish_pointer",
                        lambda **kw: published.update(kw))
    buf = _io.StringIO()
    with _cl.redirect_stdout(buf):
        result = perform_runtime_repair(ndjson=True)
    assert result["ok"] is True
    assert published["paperforge_version"] == "1.5.15"


class _FakeCompleted:
    returncode = 0
    stdout = "1.5.15"


class _OkResult:
    ok = True
    message = "ok"
