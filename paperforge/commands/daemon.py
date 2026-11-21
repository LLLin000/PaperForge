"""Persistent low-memory global control daemon (`paperforge daemon --stdio`).

Eliminates repeated Windows/POSIX Python startup latency (~300-600ms), keeps
resident memory strictly lightweight (< 30 MB RSS) via ``ControlDaemon``
ephemeral child-worker supervision and idle GC trimming, arbitrates conflicting
background jobs, and emits duplex NDJSON server-push notifications over stdout.
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.services.control_daemon import ControlDaemon


@dataclass
class _VaultSessionCache:
    """Backward-compatible projection of one vault's warm cache."""

    vault_key: str
    last_seq: int = -1
    workspace_map: dict[str, str] = field(default_factory=dict)
    ocr_salvage_counts: dict[str, int] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0
    refreshed_at: float = 0.0


class DaemonEngineSession:
    """Thread-safe facade backed by ``ControlDaemon`` bounded caches."""

    def __init__(self, control: ControlDaemon | None = None) -> None:
        self.control = control or ControlDaemon()

    def get_or_refresh(self, vault: str | Path) -> _VaultSessionCache:
        raw = self.control.get_or_refresh_vault(vault)
        return _VaultSessionCache(
            vault_key=raw["vault_key"],
            last_seq=raw["last_seq"],
            workspace_map=dict(raw["workspace_map"]),
            ocr_salvage_counts=dict(raw["ocr_salvage_counts"]),
            hits=raw["hits"],
            misses=raw["misses"],
            refreshed_at=raw["refreshed_at"],
        )

    def invalidate(self, vault: str | Path | None = None) -> int:
        return self.control.invalidate_vault(vault)

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
        h = self.control.health()
        return {
            "cached_vaults": [
                {
                    "vault": c["vault"],
                    "seq": c["seq"],
                    "workspace_count": c["workspace_count"],
                    "cache_hits": c["hits"],
                    "cache_misses": c["misses"],
                }
                for c in h["cached_vaults"]
            ]
        }


_CONTROL_DAEMON = ControlDaemon()
_ENGINE_SESSION = DaemonEngineSession(_CONTROL_DAEMON)


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


def _json_ok(req_id: Any, payload: Any) -> dict[str, Any]:
    return {
        "id": req_id,
        "ok": True,
        "exit_code": 0,
        "stdout": json.dumps(payload, ensure_ascii=False),
        "stderr": "",
    }


def _json_err(req_id: Any, message: str, exit_code: int = 2) -> dict[str, Any]:
    return {
        "id": req_id,
        "ok": False,
        "exit_code": exit_code,
        "stdout": "",
        "stderr": message,
    }


def _execute_request(
    req: dict[str, Any],
    *,
    real_stdout: Any,
    real_stderr: Any,
    session: DaemonEngineSession | None = None,
) -> dict[str, Any]:
    """Execute one RPC request (control-plane op or CLI argv) and capture response."""
    eng = session or _ENGINE_SESSION
    ctrl = eng.control
    req_id = req.get("id")
    op = str(req.get("op") or "").strip().lower()
    vault_arg = req.get("vault")

    if op == "ping":
        return {"id": req_id, "ok": True, "exit_code": 0, "stdout": "pong", "stderr": ""}
    if op == "shutdown":
        ctrl.cancel_all_jobs(grace_sec=1.0)
        return {"id": req_id, "ok": True, "exit_code": 0, "stdout": "", "stderr": "", "_shutdown": True}

    # ── Global Control Engine RPC ops ──
    if op == "daemon.health":
        return _json_ok(req_id, ctrl.health(vault_arg))
    if op == "daemon.trim":
        return _json_ok(req_id, ctrl.trim_idle_memory(float(req.get("idle_seconds") or 120.0)))
    if op == "engine.status":
        return _json_ok(req_id, eng.status(vault_arg))
    if op == "engine.resolve_key":
        key = str(req.get("key") or "").strip()
        if not vault_arg or not key:
            return _json_err(req_id, "vault and key required")
        cache = eng.get_or_refresh(vault_arg)
        rel = cache.workspace_map.get(key)
        return _json_ok(req_id, {"key": key, "workspace_relpath": rel, "seq": cache.last_seq})
    if op == "engine.invalidate":
        return _json_ok(req_id, {"cleared": eng.invalidate(vault_arg)})

    if op == "job.submit":
        kind = str(req.get("kind") or "").strip()
        if not vault_arg or not kind:
            return _json_err(req_id, "vault and kind required")
        custom_argv = req.get("argv") if isinstance(req.get("argv"), list) else None
        prio = str(req.get("priority_key") or "").strip() or None
        backfill = bool(req.get("backfill_ocr", False))
        try:
            res = ctrl.submit_job(
                vault_arg,
                kind,
                argv=custom_argv,
                priority_key=prio,
                backfill_ocr=backfill,
            )
            return _json_ok(req_id, res)
        except Exception as exc:  # noqa: BLE001
            return _json_err(req_id, str(exc), exit_code=1)

    if op == "job.list":
        return _json_ok(
            req_id,
            ctrl.list_jobs(
                vault=str(vault_arg) if vault_arg else None,
                include_recent=bool(req.get("include_recent", True)),
            ),
        )
    if op == "job.cancel":
        job_id = str(req.get("job_id") or "").strip()
        if not job_id:
            return _json_err(req_id, "job_id required")
        return _json_ok(req_id, ctrl.cancel_job(job_id, wait=bool(req.get("wait", False))))

    if op == "notice.list":
        return _json_ok(
            req_id,
            {
                "notices": ctrl.list_notices(
                    vault=str(vault_arg) if vault_arg else None,
                    include_acked=bool(req.get("include_acked", False)),
                )
            },
        )
    if op == "notice.ack":
        nid = str(req.get("notice_id") or "").strip()
        return _json_ok(req_id, {"acked": ctrl.ack_notice(nid)})
    if op == "notice.push":
        ntc = ctrl.push_notice(
            level=str(req.get("level") or "info"),
            code=str(req.get("code") or "custom"),
            title=str(req.get("title") or ""),
            detail=str(req.get("detail") or ""),
            vault=str(vault_arg) if vault_arg else None,
        )
        return _json_ok(req_id, ntc)

    # ── Standard CLI argv multiplexing ──
    raw_argv = req.get("argv")
    if not isinstance(raw_argv, list) or not all(isinstance(x, str) for x in raw_argv):
        return _json_err(req_id, "daemon request requires string list 'argv'")
    argv = list(raw_argv)
    if argv and argv[0] == "daemon":
        return _json_err(req_id, "Nested daemon invocation is not supported")

    is_exclusive_upgrade = bool(
        argv and argv[0] == "upgrade" and ("--apply" in argv or "--rollback" in argv)
    )

    vault = req.get("vault")
    if isinstance(vault, str) and vault.strip() and "--vault" not in argv:
        argv = ["--vault", vault, *argv]

    if isinstance(vault, str) and vault.strip():
        if is_exclusive_upgrade:
            ctrl.acquire_exclusive_barrier(vault, "upgrade_cutover_or_rollback")
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
        except Exception as exc:  # noqa: BLE001
            print(f"{type(exc).__name__}: {exc}", file=err_buf)
            exit_code = 1
    finally:
        sys.stdin = orig_stdin
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        _restore_stream_handlers(saved_handlers)
        if isinstance(vault, str) and vault.strip() and is_exclusive_upgrade:
            ctrl.release_exclusive_barrier(vault)

    if isinstance(vault, str) and vault.strip():
        eng.get_or_refresh(vault)

    return {
        "id": req_id,
        "exit_code": exit_code,
        "stdout": out_buf.getvalue(),
        "stderr": err_buf.getvalue(),
    }


def serve_stdio(
    idle_timeout: int = 300,
    parent_pid: int | None = None,
    *,
    push_events: bool | None = None,
) -> int:
    """Serve duplex JSON-RPC calls & optional server-push events over stdin/stdout."""
    real_stdin = sys.stdin
    real_stdout = sys.stdout
    real_stderr = sys.stderr

    if parent_pid is None:
        env_ppid = os.environ.get("PAPERFORGE_PARENT_PID", "").strip()
        if env_ppid.isdigit():
            parent_pid = int(env_ppid)

    if push_events is None:
        push_events = os.environ.get("PAPERFORGE_DAEMON_PUSH", "").strip() in ("1", "true", "yes")

    stdout_lock = threading.Lock()
    state_lock = threading.Lock()
    state = {"last_activity": time.monotonic(), "busy": False, "stop": False}

    def _write_frame(frame: dict[str, Any]) -> None:
        line = json.dumps(frame, ensure_ascii=False) + "\n"
        with stdout_lock:
            real_stdout.write(line)
            real_stdout.flush()

    _CONTROL_DAEMON._parent_pid = parent_pid
    _CONTROL_DAEMON.set_push_sink(_write_frame if push_events else None)

    if (idle_timeout and idle_timeout > 0) or (parent_pid and parent_pid > 0):
        def _watchdog() -> None:
            while not state["stop"]:
                time.sleep(1.5)
                with state_lock:
                    if state["stop"]:
                        return
                    busy = bool(state["busy"]) or _CONTROL_DAEMON.has_active_jobs()
                    idle_for = time.monotonic() - float(state["last_activity"])

                if parent_pid and parent_pid > 0 and not _CONTROL_DAEMON.check_parent_alive():
                    _CONTROL_DAEMON.cancel_all_jobs(grace_sec=1.0)
                    os._exit(0)

                if not busy:
                    _CONTROL_DAEMON.trim_idle_memory(idle_for)
                    if idle_timeout and idle_timeout > 0 and idle_for >= idle_timeout:
                        os._exit(0)

        threading.Thread(target=_watchdog, daemon=True, name="paperforge-daemon-watchdog").start()

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
            _write_frame(resp)
            if should_shutdown:
                break
    finally:
        with state_lock:
            state["stop"] = True
        _CONTROL_DAEMON.set_push_sink(None)
        _CONTROL_DAEMON.cancel_all_jobs(grace_sec=1.0)
    return 0


def run(args: argparse.Namespace) -> int:
    """CLI handler for ``paperforge daemon``."""
    idle_timeout = int(getattr(args, "idle_timeout", 300) or 0)
    parent_pid = getattr(args, "parent_pid", None)
    return serve_stdio(idle_timeout=idle_timeout, parent_pid=parent_pid)
