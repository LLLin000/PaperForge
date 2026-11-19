"""Persistent single-process JSON-RPC stdio daemon (`paperforge daemon --stdio`).

Eliminates repeated Windows/POSIX Python startup latency (~300-600ms) for
short interactive queries and mutations while preserving identical ``cli.main``
exit codes, stdout, stderr, and stdin-secret behavior.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
import sys
import threading
import time
from typing import Any


def _redirect_stream_handlers(
    target: io.StringIO,
    source_streams: tuple[object, ...],
) -> list[tuple[logging.StreamHandler[Any], Any]]:
    """Temporarily point active logging StreamHandlers at *target*."""
    changed: list[tuple[logging.StreamHandler[Any], Any]] = []
    seen_handlers: set[int] = set()
    loggers: list[logging.Logger] = [logging.getLogger(), logging.getLogger("paperforge")]
    for obj in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(obj, logging.Logger):
            loggers.append(obj)
    for lgr in loggers:
        for handler in list(getattr(lgr, "handlers", [])):
            hid = id(handler)
            if hid in seen_handlers or not isinstance(handler, logging.StreamHandler):
                continue
            seen_handlers.add(hid)
            old_stream = handler.stream
            if old_stream in source_streams or old_stream is None:
                handler.setStream(target)
                changed.append((handler, old_stream))
    return changed


def _restore_stream_handlers(
    saved: list[tuple[logging.StreamHandler[Any], Any]],
) -> None:
    for handler, old_stream in saved:
        with contextlib.suppress(Exception):
            handler.setStream(old_stream)


def _execute_request(
    req: dict[str, Any],
    *,
    real_stdout: Any,
    real_stderr: Any,
) -> dict[str, Any]:
    """Execute one RPC request in-process and capture exit code/stdout/stderr."""
    req_id = req.get("id")
    op = str(req.get("op") or "").strip().lower()
    if op == "ping":
        return {"id": req_id, "ok": True, "exit_code": 0, "stdout": "pong", "stderr": ""}
    if op == "shutdown":
        return {"id": req_id, "ok": True, "exit_code": 0, "stdout": "", "stderr": "", "_shutdown": True}

    raw_argv = req.get("argv")
    if not isinstance(raw_argv, list) or not all(isinstance(x, str) for x in raw_argv):
        return {
            "id": req_id,
            "ok": False,
            "exit_code": 2,
            "stdout": "",
            "stderr": "daemon request requires string list 'argv'",
        }
    argv = list(raw_argv)
    if argv and argv[0] == "daemon":
        return {
            "id": req_id,
            "ok": False,
            "exit_code": 2,
            "stdout": "",
            "stderr": "Nested daemon invocation is not supported",
        }
    vault = req.get("vault")
    if isinstance(vault, str) and vault.strip() and "--vault" not in argv:
        argv = ["--vault", vault, *argv]

    req_stdin = req.get("stdin")
    stdin_text = req_stdin if isinstance(req_stdin, str) else ""

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    in_buf = io.StringIO(stdin_text)

    from paperforge import cli
    from paperforge.core import timing

    orig_stdin, orig_stdout, orig_stderr = sys.stdin, sys.stdout, sys.stderr
    saved_handlers = _redirect_stream_handlers(err_buf, (orig_stdout, orig_stderr, real_stdout, real_stderr))
    exit_code = 0
    try:
        sys.stdin = in_buf
        sys.stdout = out_buf
        sys.stderr = err_buf
        timing.reset()
        try:
            exit_code = int(cli.main(argv))
        except SystemExit as exc:
            if exc.code is None:
                exit_code = 0
            elif isinstance(exc.code, int):
                exit_code = int(exc.code)
            else:
                print(str(exc.code), file=err_buf)
                exit_code = 1
        except Exception as exc:  # noqa: BLE001 — isolate request failures from daemon lifetime
            print(f"{type(exc).__name__}: {exc}", file=err_buf)
            exit_code = 1
    finally:
        sys.stdin = orig_stdin
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        _restore_stream_handlers(saved_handlers)

    return {
        "id": req_id,
        "exit_code": exit_code,
        "stdout": out_buf.getvalue(),
        "stderr": err_buf.getvalue(),
    }


def serve_stdio(idle_timeout: int = 300) -> int:
    """Serve newline-delimited JSON RPC calls over stdin/stdout until EOF, shutdown, or idle timeout."""
    real_stdin = sys.stdin
    real_stdout = sys.stdout
    real_stderr = sys.stderr

    state_lock = threading.Lock()
    state = {"last_activity": time.monotonic(), "busy": False, "stop": False}

    if idle_timeout and idle_timeout > 0:
        def _watchdog() -> None:
            while not state["stop"]:
                time.sleep(1.0)
                with state_lock:
                    if state["stop"]:
                        return
                    if not state["busy"] and (time.monotonic() - state["last_activity"]) >= idle_timeout:
                        os._exit(0)

        threading.Thread(target=_watchdog, daemon=True, name="paperforge-daemon-idle").start()

    try:
        while True:
            raw_line = real_stdin.readline()
            if not raw_line:
                break
            line = raw_line.strip()
            if not line:
                continue
            with state_lock:
                state["last_activity"] = time.monotonic()
                state["busy"] = True
            try:
                try:
                    req = json.loads(line)
                    if not isinstance(req, dict):
                        raise ValueError("request must be a JSON object")
                    resp = _execute_request(req, real_stdout=real_stdout, real_stderr=real_stderr)
                except Exception as exc:  # noqa: BLE001
                    resp = {
                        "id": None,
                        "exit_code": 2,
                        "stdout": "",
                        "stderr": f"Invalid daemon request: {exc}",
                    }
            finally:
                with state_lock:
                    state["busy"] = False
                    state["last_activity"] = time.monotonic()

            should_shutdown = bool(resp.pop("_shutdown", False))
            real_stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            real_stdout.flush()
            if should_shutdown:
                break
    finally:
        with state_lock:
            state["stop"] = True
    return 0


def run(args: argparse.Namespace) -> int:
    """CLI handler for ``paperforge daemon``."""
    idle_timeout = int(getattr(args, "idle_timeout", 300) or 0)
    return serve_stdio(idle_timeout=idle_timeout)
