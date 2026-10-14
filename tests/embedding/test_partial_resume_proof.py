"""Prove the partial-write resume contract for the vector build."""
from __future__ import annotations

import http.server
import json
import shutil
import socketserver
import subprocess
import threading
from pathlib import Path

import pytest

from paperforge.config import bootstrap_config, set_config
from paperforge.credentials import CredentialKey, store as store_cred
from paperforge.embedding import read_vector_build_state
from paperforge.services.embedding import run_embedding_build

CONTEXT = {}
REPO_ROOT = Path(__file__).resolve().parents[2]
OCR_FIXTURE = REPO_ROOT / "tests" / "sandbox" / "ocr-complete" / "TSTONE001"
EXPORT_FIXTURE = REPO_ROOT / "tests" / "sandbox" / "exports" / "骨科.json"
N = 6
K = 3


class _EmbHandler(http.server.BaseHTTPRequestHandler):
    recorded: list = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            data = {}
        if "/embeddings" in self.path:
            self.__class__.recorded.append(data)
            texts = data.get("input", [])
            if isinstance(texts, str):
                texts = [texts]
            out = {
                "data": [{"embedding": [0.1] * 8, "index": i} for i, _ in enumerate(texts)],
                "model": data.get("model", "text-embedding-3-small"),
            }
            payload = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a, **kw):
        pass


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "resume_vault"
    vault.mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "exports").mkdir(parents=True)
    (vault / "99_System" / "PaperForge" / "ocr").mkdir(parents=True)
    (vault / "03_Resources" / "Literature").mkdir(parents=True)
    bootstrap_config(vault)
    for key, value in {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
        "skill_dir": ".opencode/skills",
    }.items():
        set_config(vault, key, value)

    base_export = json.loads(EXPORT_FIXTURE.read_text(encoding="utf-8"))
    items = []
    for i in range(1, N + 1):
        key = f"TSTONE{i:03d}"
        dst = vault / "99_System" / "PaperForge" / "ocr" / key
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(OCR_FIXTURE, dst)
        item = dict(base_export["items"][0])
        item["key"] = key
        item["itemKey"] = key
        items.append(item)
    base_export["items"] = items
    (vault / "99_System" / "PaperForge" / "exports" / "骨科.json").write_text(
        json.dumps(base_export, ensure_ascii=False), encoding="utf-8"
    )
    return vault


@pytest.fixture
def resumed_vault(tmp_path, monkeypatch):
    import paperforge.credentials as cred

    class _FK:
        class errors:
            class PasswordDeleteError(Exception):
                pass

        def __init__(self):
            self._d = {}

        def get_password(self, s, u):
            return self._d.get((s, u))

        def set_password(self, s, u, p):
            self._d[(s, u)] = p

        def delete_password(self, s, u):
            if (s, u) not in self._d:
                raise self.errors.PasswordDeleteError()
            del self._d[(s, u)]

        def get_keyring(self):
            return "FK"

    monkeypatch.setattr(cred, "_keyring_module", None)
    cred.set_keyring_override(_FK())
    store_cred(CredentialKey(kind="embedding"), "test-key")

    vault = _make_vault(tmp_path)

    handler_cls = type("H", (_EmbHandler,), {})
    handler_cls.recorded = []
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    from paperforge.config import set_config as _sc

    _sc(vault, "vector_db_api_base", f"http://127.0.0.1:{port}/v1")
    _sc(vault, "vector_db_api_model", "text-embedding-3-small")

    CONTEXT[str(vault)] = {"httpd": httpd, "handler": handler_cls}

    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    pf = ["python", "-m", "paperforge", "--vault", str(vault)]
    subprocess.run(pf + ["sync", "--json"], capture_output=True, text=True, encoding="utf-8", env=env)
    subprocess.run(pf + ["memory", "build", "--json"], capture_output=True, text=True, encoding="utf-8", env=env)

    yield vault
    httpd.shutdown()


def test_partial_resume(resumed_vault):
    vault = resumed_vault
    handler = CONTEXT[str(vault)]["handler"]
    records = handler.recorded

    recs_before = len(records)
    stop_flag = {"v": False}

    def on_progress(cur, total, paper_id):
        if cur >= K:
            stop_flag["v"] = True

    run_embedding_build(
        vault,
        [],
        resume=False,
        json=True,
        stop_check=lambda: stop_flag["v"],
        on_progress=on_progress,
    )

    n_after_first = len(records)
    first_paper_requests = n_after_first - recs_before

    before2 = len(records)
    run_embedding_build(vault, [], resume=True, json=True)
    after2 = len(records)
    second_requests = after2 - before2

    per_paper = (first_paper_requests - 1) // K if K else 0
    expected_second = (N - K) * per_paper
    assert second_requests == expected_second, (
        f"second run requests {second_requests} != expected {expected_second}"
    )

    st = read_vector_build_state(vault)
    assert st.get("status") == "completed", st

    CONTEXT[str(vault)]["httpd"].shutdown()
