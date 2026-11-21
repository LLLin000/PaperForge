"""Persistent single-process JSON-RPC stdio daemon (`paperforge daemon --stdio`).

Eliminates repeated Windows/POSIX Python startup latency (~300-600ms) AND
maintains a warm per-vault ``DaemonEngineSession`` (cached ``workspace_registry``
lookups + ``state_seq`` invalidation) so interactive queries avoid redundant
filesystem scans while preserving identical ``cli.main`` exit codes, stdout,
stderr, and stdin-secret behavior.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class _VaultSessionCache:
    """In-memory warm cache for one vault, invalidated whenever ``state_seq`` changes."""

    vault_key: str
    last_seq: int = -1
    workspace_map: dict[str, str] = field(default_factory=dict)
    ocr_salvage_counts: dict[str, int] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0
    refreshed_at: float = 0.0


class DaemonEngineSession:
    """Thread-safe warm VaultEngine cache hosted inside the long-lived daemon process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vaults: dict[str, _VaultSessionCache] = {}

    @staticmethod
    def _norm_vault(vault: str | Path) -> str:
        return str(Path(vault).expanduser().resolve())

    def _current_seq(self, vault_root: Path) -> int:
        try:
            from paperforge.services.state_signal import read_state_seq

            return int(read_state_seq(vault_root).get("seq") or 0)
        except Exception:  # noqa: BLE001
            return 0

    def _load_warm_state(self, vault_root: Path) -> tuple[dict[str, str], dict[str, int]]:
        ws_map: dict[str, str] = {}
        ocr_counts: dict[str, int] = {}
        try:
            from paperforge.memory.db import get_memory_db_path, open_live_reader

            db_path = get_memory_db_path(vault_root)
            if db_path.is_file():
                with open_live_reader(vault_root, db_path) as conn:
                    tbls = {
                        str(r[0])
                        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    }
                    if "workspace_registry" in tbls:
                        for row in conn.execute(
                            "SELECT zotero_key, workspace_relpath FROM workspace_registry"
                        ).fetchall():
                            ws_map[str(row[0])] = str(row[1])
                    if "ocr_catalog" in tbls:
                        for row in conn.execute(
                            "SELECT salvage_action, COUNT(*) FROM ocr_catalog GROUP BY salvage_action"
                        ).fetchall():
                            ocr_counts[str(row[0])] = int(row[1])
        except (sqlite3.Error, OSError, ImportError):
            pass
        return ws_map, ocr_counts

    def get_or_refresh(self, vault: str | Path) -> _VaultSessionCache:
        vault_root = Path(vault).expanduser().resolve()
        vkey = str(vault_root)
        seq = self._current_seq(vault_root)
        with self._lock:
            entry = self._vaults.get(vkey)
            if entry is not None and entry.last_seq == seq:
                entry.hits += 1
                return entry
            ws_map, ocr_counts = self._load_warm_state(vault_root)
            if entry is None:
                entry = _VaultSessionCache(vault_key=vkey)
                self._vaults[vkey] = entry
            entry.misses += 1
            entry.last_seq = seq
            entry.workspace_map = ws_map
            entry.ocr_salvage_counts = ocr_counts
            entry.refreshed_at = time.time()
            return entry

    def invalidate(self, vault: str | Path | None = None) -> int:
        with self._lock:
            if vault is None:
                count = len(self._vaults)
                self._vaults.clear()
                return count
            vkey = self._norm_vault(vault)
            return 1 if self._vaults.pop(vkey, None) is not None else 0

    def status(self, vault: str | Path | None = None) -> dict[str, Any]:
        if vault is not None:
            cache = self.get_or_refresh(vault)
            return {
                "vault": cache.vault_key,
                "seq": cache.last_seq,
                "workspace_count": len(cache.workspace_map),
                "ocr_salvage_counts": dict(cache.ocr_salvage_counts),
                "cache_hits": cache.hits,
                "cache_misses": cache.misses,
            }
        with self._lock:
            return {
                "cached_vaults": [
                    {
                        "vault": c.vault_key,
                        "seq": c.last_seq,
                        "workspace_count": len(c.workspace_map),
                        "cache_hits": c.hits,
                        "cache_misses": c.misses,
                    }
                    for c in self._vaults.values()
                ]
            }


_ENGINE_SESSION = DaemonEngineSession()


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
    session: DaemonEngineSession | None = None,
) -> dict[str, Any]:
    """Execute one RPC request in-process and capture exit code/stdout/stderr."""
    eng = session or _ENGINE_SESSION
    req_id = req.get("id")
    op = str(req.get("op") or "").strip().lower()
    if op == "ping":
        return {"id": req_id, "ok": True, "exit_code": 0, "stdout": "pong", "stderr": ""}
    if op == "shutdown":
        return {"id": req_id, "ok": True, "exit_code": 0, "stdout": "", "stderr": "", "_shutdown": True}
    if op == "engine.status":
        vault_arg = req.get("vault")
        payload = eng.status(vault_arg)
        return {
            "id": req_id,
            "ok": True,
            "exit_code": 0,
            "stdout": json.dumps(payload, ensure_ascii=False),
            "stderr": "",
        }
    if op == "engine.resolve_key":
        vault_arg = req.get("vault")
        key = str(req.get("key") or "").strip()
        if not vault_arg or not key:
            return {"id": req_id, "ok": False, "exit_code": 2, "stdout": "", "stderr": "vault and key required"}
        cache = eng.get_or_refresh(vault_arg)
        rel = cache.workspace_map.get(key)
        return {
            "id": req_id,
            "ok": True,
            "exit_code": 0,
            "stdout": json.dumps({"key": key, "workspace_relpath": rel, "seq": cache.last_seq}),
            "stderr": "",
        }
    if op == "engine.invalidate":
        cleared = eng.invalidate(req.get("vault"))
        return {
            "id": req_id,
            "ok": True,
            "exit_code": 0,
            "stdout": json.dumps({"cleared": cleared}),
            "stderr": "",
        }

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

    if isinstance(vault, str) and vault.strip():
        eng.get_or_refresh(vault)

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

    if isinstance(vault, str) and vault.strip():
        eng.get_or_refresh(vault)

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
