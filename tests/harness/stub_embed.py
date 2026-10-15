"""Loopback OpenAI-compatible embeddings API for the retrieval cases.

The H matrix proves the retrieval lane against a controlled provider only inside
Obsidian; this is the same server in stdlib Python, so `paperforge embed build`,
`memory build` and a deep search can be driven without a host.

    POST {base}/embeddings   {model, input} -> {object: list, data: [...]}

Modes: ``success`` answers one vector per input, ``slow`` never answers (the stop
case needs a build that is genuinely in flight), ``error`` answers with a status.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

_EMBED_PATHS = ("/embeddings", "/v1/embeddings")


class _EmbedServer(ThreadingHTTPServer):
    daemon_threads = True
    stub: EmbedStub | None = None


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 — stdlib signature
        """The stub is noisy by design; keep the case log readable."""
        return

    @property
    def stub(self) -> EmbedStub:
        server = cast("_EmbedServer", self.server)
        if server.stub is None:
            raise RuntimeError("no stub attached to this server")
        return server.stub

    def _json(self, value: Any, status: int = 200) -> None:
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 — stdlib contract
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(length) if length else b""
        if path not in _EMBED_PATHS:
            self.stub.record(path, "", 0)
            self._json({"error": {"message": "not found"}}, status=404)
            return
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {}
        model = str(payload.get("model") or "")
        inputs = payload.get("input")
        items = inputs if isinstance(inputs, list) else [inputs if inputs is not None else ""]
        self.stub.record(path, model, len(items))

        if self.stub.mode == "error":
            self._json(
                {"error": {"message": self.stub.error_message, "type": "invalid_request_error"}},
                status=self.stub.error_status,
            )
            return
        if self.stub.mode == "slow":
            # Hold the request open: the build must be stoppable *in flight*.
            while not self.stub.stopping:
                time.sleep(0.1)
            self._json({"error": {"message": "client went away"}}, status=499)
            return
        if self.stub.delay_s:
            # Answer, but slowly: the build stays observable at its own safe
            # points instead of being stuck inside one HTTP call.
            time.sleep(self.stub.delay_s)

        self._json(
            {
                "object": "list",
                "data": [
                    {
                        "object": "embedding",
                        "index": index,
                        "embedding": self.stub.vector(str(item)),
                    }
                    for index, item in enumerate(items)
                ],
                "model": model,
                "usage": {"prompt_tokens": 1, "total_tokens": len(items)},
            }
        )


class EmbedStub:
    """A scripted embedding provider: deterministic vectors, no network."""

    def __init__(
        self,
        *,
        mode: str = "success",
        dim: int = 1536,
        delay_s: float = 0.0,
        error_status: int = 429,
        error_message: str = "scripted provider rejection",
    ) -> None:
        self.mode: str = mode
        self.dim: int = dim
        self.delay_s: float = delay_s
        self.error_status: int = error_status
        self.error_message: str = error_message
        self.stopping: bool = False
        self.requests: list[dict[str, Any]] = []
        self._server: _EmbedServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ── lifecycle ───────────────────────────────────────────────────────
    def start(self) -> EmbedStub:
        server = _EmbedServer(("127.0.0.1", 0), _Handler)
        server.stub = self
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="embed-stub", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.stopping = True
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> EmbedStub:
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
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def counts(self) -> dict[str, int]:
        with self._lock:
            batched: dict[str, int] = {"requests": len(self.requests), "inputs": 0}
            for row in self.requests:
                batched["inputs"] += int(row.get("input_count") or 0)
            return batched

    def reset(self) -> None:
        with self._lock:
            self.requests = []

    def record(self, path: str, model: str, input_count: int) -> None:
        with self._lock:
            self.requests.append({"path": path, "model": model, "input_count": input_count})

    def vector(self, text: str) -> list[float]:
        """A deterministic unit-ish vector: same input, same numbers, every run.

        Retrieval quality is not the subject of these cases - the substrate, its
        publication and its stop semantics are - so the vector only has to be
        stable, distinct per input, and the configured width.
        """
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [0.0] * self.dim
        for index in range(min(16, self.dim)):
            values[index] = (digest[index] / 255.0) or 0.01
        values[0] = abs(values[0]) + 1.0
        return values
