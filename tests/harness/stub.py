"""Loopback PaddleOCR job API for the CLI-host OCR cases.

The H matrix proves the OCR lifecycle against a controlled provider only inside
Obsidian (a TypeScript `node:http` stub in the WebDriver spec), which is one of
the reasons those cases could not leave the host.  This is the same protocol in
stdlib Python, so the real `paperforge ocr run` subprocess can be driven without
a host, a wheel build or WebDriver:

    POST {job_url}                 -> {"data": {"jobId": ...}}
    GET  {job_url}/{job_id}        -> {"data": {"state": running|done|error, ...}}
    GET  {job_url}/batch/{batch}   -> {"data": {job_id: state | {...}}}
    GET  /results/{job_id}.jsonl   -> one {"result": <page>} JSON per line

Shapes mirror `paperforge.providers.paddleocr.PaddleOCRProvider` (the reader of
`json.loads(line)["result"]` in worker/ocr.py) and a REAL payload fixture, so a
case exercises the production parse path instead of a hand-made approximation.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAYLOAD = (
    REPO_ROOT / "tests" / "fixtures" / "ocr_real_papers" / "PJBMGVTF" / "ocr_payload.json"
)

_FILENAME = re.compile(rb'filename="([^"]*)"')
_JOB_PATH = re.compile(r"^/api/v2/ocr/jobs/([^/]+)$")
_BATCH_PATH = re.compile(r"^/api/v2/ocr/jobs/batch/([^/]+)$")
_RESULT_PATH = re.compile(r"^/results/([^/]+)\.jsonl$")


class _StubServer(ThreadingHTTPServer):
    daemon_threads = True
    stub: OcrStub


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib signature
        """Keep CI logs readable: the stub is noisy by design."""
        return

    @property
    def stub(self) -> OcrStub:
        return cast("_StubServer", self.server).stub

    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, value: Any, status: int = 200) -> None:
        self._send(status, json.dumps(value).encode("utf-8"))

    def do_POST(self) -> None:  # noqa: N802 — stdlib contract
        path = self.path.split("?", 1)[0]
        if path.rstrip("/") != "/api/v2/ocr/jobs":
            self._json({"error": "not found"}, status=404)
            return
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""
        match = _FILENAME.search(body)
        filename = match.group(1).decode("utf-8", "replace") if match else ""
        key = Path(filename.replace("\\", "/")).name
        if key.lower().endswith(".pdf"):
            key = key[:-4]
        self._json({"data": {"jobId": self.stub.register(key)}}, status=202)

    def do_GET(self) -> None:  # noqa: N802 — stdlib contract
        path = self.path.split("?", 1)[0]

        result = _RESULT_PATH.match(path)
        if result:
            body = self.stub.result_body(result.group(1))
            if body is None:
                self._json({"error": "unknown job"}, status=404)
                return
            self._send(200, body)
            return

        batch = _BATCH_PATH.match(path)
        if batch:
            self._json({"data": self.stub.batch_states()})
            return

        job = _JOB_PATH.match(path)
        if job:
            state = self.stub.job_state(job.group(1))
            if state is None:
                self._json({"error": "unknown job"}, status=404)
                return
            self._json({"data": state})
            return

        self._json({"error": "not found"}, status=404)


class OcrStub:
    """A scripted provider: every paper's outcome is decided here, not by luck."""

    def __init__(
        self,
        *,
        mode: str = "success",
        done_after: int = 2,
        fail_keys: Iterable[str] = (),
        payload_path: Path | None = None,
        pages: int | None = None,
    ) -> None:
        """``mode``: ``success`` settles every job, ``slow`` never settles one.

        ``fail_keys`` marks papers whose job reports ``state=error`` (the
        provider-side failure the partial-batch case needs).  ``pages`` limits
        how many payload pages are served so it can match the fixture PDF's real
        page count.
        """
        self.mode: str = mode
        self.done_after: int = done_after
        self.fail_keys: set[str] = set(fail_keys)
        source = Path(payload_path) if payload_path else DEFAULT_PAYLOAD
        raw: Any = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"payload must be a list of pages: {source}")
        self._pages: list[Any] = raw[:pages] if pages else raw
        self.counts: dict[str, int] = {}
        self.requests: list[dict[str, str]] = []
        self._jobs: dict[str, str] = {}
        self._observations: dict[str, int] = {}
        self._next_job: int = 0
        self._server: _StubServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ── lifecycle ───────────────────────────────────────────────────────
    def start(self) -> OcrStub:
        server = _StubServer(("127.0.0.1", 0), _Handler)
        server.stub = self
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="ocr-stub", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> OcrStub:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # ── the protocol ────────────────────────────────────────────────────
    @property
    def port(self) -> int:
        if self._server is None:
            raise RuntimeError("stub is not running")
        return int(self._server.server_address[1])

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v2/ocr/jobs"

    def reset_counts(self) -> None:
        with self._lock:
            self.counts = {}
            self.requests = []

    def register(self, key: str) -> str:
        with self._lock:
            self._next_job += 1
            job_id = f"stub-job-{self._next_job}"
            self._jobs[job_id] = key
            self.counts["submit"] = self.counts.get("submit", 0) + 1
            self.requests.append({"method": "POST", "path": "/api/v2/ocr/jobs", "key": key})
            return job_id

    def _observed_state(self, job_id: str) -> dict[str, Any]:
        key = self._jobs.get(job_id, "")
        if key in self.fail_keys:
            return {"state": "error", "errorMsg": f"scripted provider rejection for {key}"}
        if self.mode == "slow":
            return {"state": "running"}
        if self._observations.get(job_id, 0) >= self.done_after:
            return {
                "state": "done",
                "resultUrl": {"jsonUrl": f"http://127.0.0.1:{self.port}/results/{job_id}.jsonl"},
            }
        return {"state": "running"}

    def job_state(self, job_id: str) -> dict[str, Any] | None:
        if job_id not in self._jobs:
            return None
        with self._lock:
            self.counts["poll"] = self.counts.get("poll", 0) + 1
            self.requests.append({"method": "GET", "path": f"/api/v2/ocr/jobs/{job_id}"})
            self._observations[job_id] = self._observations.get(job_id, 0) + 1
            return self._observed_state(job_id)

    def batch_states(self) -> dict[str, Any]:
        with self._lock:
            self.counts["batch"] = self.counts.get("batch", 0) + 1
            self.requests.append({"method": "GET", "path": "/api/v2/ocr/jobs/batch"})
            out: dict[str, Any] = {}
            for job_id in list(self._jobs):
                self._observations[job_id] = self._observations.get(job_id, 0) + 1
                state = self._observed_state(job_id)
                # A failing job carries its message in the batch payload; a
                # healthy one reports the bare state so the worker falls back to
                # the per-job fetch for the result URL.
                out[job_id] = state if state.get("errorMsg") else state["state"]
            return out

    def result_body(self, job_id: str) -> bytes | None:
        if job_id not in self._jobs or self._jobs[job_id] in self.fail_keys:
            return None
        with self._lock:
            self.counts["result"] = self.counts.get("result", 0) + 1
            self.requests.append({"method": "GET", "path": f"/results/{job_id}.jsonl"})
        lines = [json.dumps({"result": page}, ensure_ascii=False) for page in self._pages]
        return ("\n".join(lines) + "\n").encode("utf-8")
