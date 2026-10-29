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


# ── Lean vector contract (ChromaDB removed) ───────────────────────────────


def test_vector_extras_exclude_chromadb() -> None:
    """No ChromaDB anywhere: not in the runtime probe, not in extras."""
    from pathlib import Path

    import tomllib

    from paperforge.setup import runtime

    assert "chromadb" not in runtime.VECTOR_CAPABILITY_IMPORTS
    assert "chromadb" not in runtime.VECTOR_RUNTIME_PROBE

    repo_root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]
    assert extras["vector"] == ["openai>=1.0.0", "socksio>=1.0.0", "sqlite-vec>=0.1.0"]
    assert "legacy-vector" not in extras


def test_vec_lifecycle_imports_without_chromadb() -> None:
    """The vec0 lifecycle imports without ChromaDB; no Chroma symbols remain."""
    import subprocess
    import sys
    from pathlib import Path

    script = """
import sys

class _BlockChroma:
    def find_spec(self, name, path=None, target=None):
        if name == "chromadb" or name.startswith("chromadb."):
            raise ModuleNotFoundError("blocked for test: " + name)
        return None

sys.meta_path.insert(0, _BlockChroma())

import paperforge.embedding as embedding

assert embedding.delete_paper_vectors is not None
assert embedding.delete_paper_vectors_in_conn is not None
assert not hasattr(embedding, "ChromaBackend")
assert not hasattr(embedding, "get_collection")
assert not hasattr(embedding, "get_vector_db_path")
assert not hasattr(embedding, "migrate_chroma_to_vec0")
assert "chromadb" not in sys.modules
print("ok")
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout
