"""Low-Memory Global Control Daemon (`ControlDaemon`).

Inspired by mature local supervisor architectures (Watchman, esbuild service,
Calibre Job Server, VS Code Extension Host):
1. **Strict Low-Memory Resident Core (< 30 MB RSS)**:
   - Zero heavy imports (`chromadb`, `fitz`, `torch`, OCR geometry stay out of
     the daemon process).
   - Bounded LRU `workspace_map` (`<= 2048` keys per vault, `<= 4` vaults) +
     automatic `gc.collect()` & cold-cache eviction during idle windows.
2. **Ephemeral Child Worker Supervision (`JobSupervisor`)**:
   - Heavy/long jobs (`sync`, `ocr`, `embed`, `upgrade.heal`) execute in isolated
     child Python processes so the OS reclaims 100% of 300-800 MB RSS upon completion.
   - Relays `#137` NDJSON progress streams into duplex `task.updated` push events
     and supports per-job cooperative `PAPERFORGE_STOP` cancellation without
     killing the resident daemon.
3. **Conflict Arbitration & JIT Preemption**:
   - Exclusive barriers (`upgrade.cutover`, `upgrade.rollback`) preempt background
     `upgrade.heal` workers and reject conflicting background mutations cleanly.
   - Coalesces duplicate `sync` / `upgrade.heal` requests and supports `priority_key`.
4. **Parent-PID & Stdin-EOF Watchdog**:
   - Monitors host process (`PAPERFORGE_PARENT_PID` / `--parent-pid`) so an abrupt
     Obsidian crash reaps child workers and exits within 2s — zero orphan processes.
"""

from __future__ import annotations

import collections
import contextlib
import ctypes
import gc
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

MAX_CACHED_VAULTS = 4
MAX_WORKSPACES_PER_VAULT = 2048
MAX_NOTICES = 100
MAX_RECENT_JOBS = 25
HEAVY_MODULE_PROBES = ("chromadb", "fitz", "pymupdf", "torch", "scipy", "onnxruntime")


def get_process_rss_bytes() -> int:
    """Return current resident set size (RSS) in bytes using stdlib/OS syscalls only."""
    if sys.platform == "win32":
        try:
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            h_proc = ctypes.windll.kernel32.GetCurrentProcess()
            fn = getattr(ctypes.windll.kernel32, "K32GetProcessMemoryInfo", None) or getattr(
                ctypes.windll.psapi, "GetProcessMemoryInfo", None
            )
            if fn is not None and fn(h_proc, ctypes.byref(counters), counters.cb):
                return int(counters.WorkingSetSize)
        except Exception:  # noqa: BLE001
            return 0
        return 0

    if sys.platform.startswith("linux"):
        try:
            statm = Path("/proc/self/statm").read_text(encoding="ascii").split()
            if len(statm) >= 2:
                return int(statm[1]) * int(os.sysconf("SC_PAGE_SIZE"))
        except Exception:  # noqa: BLE001
            return 0

    try:
        import resource

        rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return rss if sys.platform == "darwin" else rss * 1024
    except Exception:  # noqa: BLE001
        return 0


def is_pid_alive(pid: int | None) -> bool:
    """Return True if *pid* is currently alive on Windows or POSIX."""
    if not pid or pid <= 0:
        return True
    if sys.platform == "win32":
        SYNCHRONIZE = 0x00100000
        WAIT_TIMEOUT = 0x00000102
        ERROR_ACCESS_DENIED = 5
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
        if not handle:
            return int(kernel32.GetLastError()) == ERROR_ACCESS_DENIED
        try:
            rc = kernel32.WaitForSingleObject(handle, 0)
            return int(rc) == WAIT_TIMEOUT
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return False


def kill_process_tree(proc: subprocess.Popen[Any]) -> None:
    """Hard-terminate a child worker process tree without touching the daemon."""
    if proc.poll() is not None:
        return
    pid = getattr(proc, "pid", None)
    if sys.platform == "win32" and pid:
        with contextlib.suppress(Exception):
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,
                timeout=5,
                check=False,
            )
            return
    with contextlib.suppress(Exception):
        proc.kill()


@dataclass
class SupervisedJob:
    """Lifecycle record for one ephemeral child worker supervised by ControlDaemon."""

    job_id: str
    vault: str
    kind: str  # "sync" | "ocr" | "embed" | "upgrade.heal" | "custom"
    argv: list[str]
    status: str = "running"  # "running" | "cancelling" | "succeeded" | "failed" | "cancelled"
    current: int = 0
    total: int = 0
    phase: str = ""
    item_id: str = ""
    priority_key: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    exit_code: int | None = None
    error: str = ""
    stderr_tail: str = ""
    pid: int | None = None
    _proc: subprocess.Popen[str] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "vault": self.vault,
            "kind": self.kind,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "phase": self.phase,
            "item_id": self.item_id,
            "priority_key": self.priority_key,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "error": self.error,
            "pid": self.pid,
        }


class ControlDaemon:
    """Low-memory global state, job arbitration, and duplex event push engine."""

    def __init__(
        self,
        *,
        parent_pid: int | None = None,
        push_sink: Callable[[dict[str, Any]], None] | None = None,
        python_exe: str | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._started_at = time.time()
        self._parent_pid = parent_pid
        self._push_sink = push_sink
        self._python_exe = python_exe or sys.executable
        self._event_seq = 0
        self._last_gc_at = 0.0

        # Bounded caches
        self._vault_caches: collections.OrderedDict[str, dict[str, Any]] = collections.OrderedDict()
        self._notices: collections.deque[dict[str, Any]] = collections.deque(maxlen=MAX_NOTICES)
        self._active_jobs: dict[str, SupervisedJob] = {}
        self._recent_jobs: collections.deque[dict[str, Any]] = collections.deque(maxlen=MAX_RECENT_JOBS)
        self._exclusive_barriers: dict[str, str] = {}  # vault_key -> reason
        self._followup_heal_priority: dict[str, str] = {}  # vault_key -> priority_key

    def set_push_sink(self, sink: Callable[[dict[str, Any]], None] | None) -> None:
        with self._lock:
            self._push_sink = sink

    @staticmethod
    def _norm_vault(vault: str | Path) -> str:
        return str(Path(vault).expanduser().resolve())

    def _emit_push(self, event: str, *, vault: str | None = None, data: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._event_seq += 1
            seq = self._event_seq
            sink = self._push_sink
        if sink is None:
            return
        frame: dict[str, Any] = {
            "event": event,
            "seq": seq,
            "ts": time.time(),
            "vault": vault,
            "data": data or {},
        }
        with contextlib.suppress(Exception):
            sink(frame)

    # ── 1. Bounded Warm Vault Cache + Idle Memory Trim ──────────────────────

    def _read_seq(self, vault_root: Path) -> int:
        try:
            from paperforge.services.state_signal import read_state_seq

            return int(read_state_seq(vault_root).get("seq") or 0)
        except Exception:  # noqa: BLE001
            return 0

    def _query_bounded_sqlite(self, vault_root: Path) -> tuple[dict[str, str], dict[str, int]]:
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
                        rows = conn.execute(
                            f"SELECT zotero_key, workspace_relpath FROM workspace_registry LIMIT {MAX_WORKSPACES_PER_VAULT}"
                        ).fetchall()
                        for r in rows:
                            ws_map[str(r[0])] = str(r[1])
                    if "ocr_catalog" in tbls:
                        for r in conn.execute(
                            "SELECT salvage_action, COUNT(*) FROM ocr_catalog GROUP BY salvage_action"
                        ).fetchall():
                            ocr_counts[str(r[0])] = int(r[1])
        except (sqlite3.Error, OSError, ImportError):
            pass
        return ws_map, ocr_counts

    def get_or_refresh_vault(self, vault: str | Path) -> dict[str, Any]:
        vault_root = Path(vault).expanduser().resolve()
        vkey = str(vault_root)
        seq = self._read_seq(vault_root)
        with self._lock:
            entry = self._vault_caches.get(vkey)
            if entry is not None and entry["last_seq"] == seq:
                entry["hits"] += 1
                entry["last_access"] = time.monotonic()
                self._vault_caches.move_to_end(vkey)
                return entry

        ws_map, ocr_counts = self._query_bounded_sqlite(vault_root)
        now_mono = time.monotonic()
        with self._lock:
            entry = self._vault_caches.get(vkey)
            prev_seq = entry["last_seq"] if entry is not None else -1
            if entry is None:
                while len(self._vault_caches) >= MAX_CACHED_VAULTS:
                    self._vault_caches.popitem(last=False)
                entry = {
                    "vault_key": vkey,
                    "last_seq": seq,
                    "workspace_map": ws_map,
                    "ocr_salvage_counts": ocr_counts,
                    "hits": 0,
                    "misses": 1,
                    "refreshed_at": time.time(),
                    "last_access": now_mono,
                }
                self._vault_caches[vkey] = entry
            else:
                entry["misses"] += 1
                entry["last_seq"] = seq
                entry["workspace_map"] = ws_map
                entry["ocr_salvage_counts"] = ocr_counts
                entry["refreshed_at"] = time.time()
                entry["last_access"] = now_mono
                self._vault_caches.move_to_end(vkey)

        if prev_seq >= 0 and seq != prev_seq:
            self._emit_push("state.changed", vault=vkey, data={"seq": seq})
        self._write_heartbeat(vault_root)
        return entry

    def invalidate_vault(self, vault: str | Path | None = None) -> int:
        with self._lock:
            if vault is None:
                n = len(self._vault_caches)
                self._vault_caches.clear()
                return n
            vkey = self._norm_vault(vault)
            return 1 if self._vault_caches.pop(vkey, None) is not None else 0

    def trim_idle_memory(self, idle_seconds: float) -> dict[str, int]:
        """Release cold caches and run cyclic GC when the daemon has been idle."""
        evicted = 0
        now_mono = time.monotonic()
        with self._lock:
            if idle_seconds >= 120.0 and not self._active_jobs:
                stale_keys = [
                    k for k, v in self._vault_caches.items() if (now_mono - float(v.get("last_access", 0.0))) >= 120.0
                ]
                for k in stale_keys:
                    self._vault_caches.pop(k, None)
                    evicted += 1
            should_gc = idle_seconds >= 30.0 and (now_mono - self._last_gc_at) >= 30.0
            if should_gc:
                self._last_gc_at = now_mono
        collected = gc.collect() if should_gc else 0
        return {"evicted_vaults": evicted, "gc_collected": collected}

    # ── 2. Global Structured Notice Center ──────────────────────────────────

    def push_notice(
        self,
        *,
        level: str,
        code: str,
        title: str,
        detail: str = "",
        vault: str | None = None,
    ) -> dict[str, Any]:
        notice = {
            "notice_id": f"ntc_{uuid.uuid4().hex[:10]}",
            "level": level if level in ("info", "success", "warning", "error") else "info",
            "code": code,
            "title": title,
            "detail": detail,
            "vault": self._norm_vault(vault) if vault else None,
            "created_at": time.time(),
            "acked": False,
        }
        with self._lock:
            self._notices.append(notice)
        self._emit_push("notice.push", vault=notice["vault"], data=dict(notice))
        return notice

    def list_notices(self, *, vault: str | None = None, include_acked: bool = False) -> list[dict[str, Any]]:
        vkey = self._norm_vault(vault) if vault else None
        with self._lock:
            out: list[dict[str, Any]] = []
            for n in self._notices:
                if not include_acked and n.get("acked"):
                    continue
                if vkey and n.get("vault") not in (None, vkey):
                    continue
                out.append(dict(n))
            return out

    def ack_notice(self, notice_id: str) -> bool:
        with self._lock:
            for n in self._notices:
                if n.get("notice_id") == notice_id:
                    n["acked"] = True
                    return True
        return False

    # ── 3. Exclusive Barriers & Ephemeral Child Worker Supervision ──────────

    def acquire_exclusive_barrier(self, vault: str | Path, reason: str) -> None:
        """Pause/preempt background healing & block conflicting jobs during cutover/rollback."""
        vkey = self._norm_vault(vault)
        jobs_to_stop: list[str] = []
        with self._lock:
            self._exclusive_barriers[vkey] = reason
            for jid, job in self._active_jobs.items():
                if job.vault == vkey and job.kind == "upgrade.heal":
                    jobs_to_stop.append(jid)
        for jid in jobs_to_stop:
            self.cancel_job(jid, grace_sec=1.5, wait=True)

    def release_exclusive_barrier(self, vault: str | Path) -> None:
        vkey = self._norm_vault(vault)
        with self._lock:
            self._exclusive_barriers.pop(vkey, None)

    @staticmethod
    def _default_argv_for_kind(
        kind: str,
        *,
        priority_key: str | None = None,
        backfill_ocr: bool = False,
    ) -> list[str]:
        if kind == "sync":
            return ["sync", "--json"]
        if kind == "ocr":
            return ["ocr", "--stream"]
        if kind == "embed":
            return ["embed", "build", "--stream"]
        if kind == "upgrade.heal":
            cmd = ["upgrade", "--heal", "--json"]
            if priority_key:
                cmd.extend(["--priority-key", priority_key])
            if backfill_ocr:
                cmd.append("--backfill-ocr")
            return cmd
        raise ValueError(f"Unsupported job kind: {kind!r}")

    def submit_job(
        self,
        vault: str | Path,
        kind: str,
        *,
        argv: list[str] | None = None,
        priority_key: str | None = None,
        backfill_ocr: bool = False,
    ) -> dict[str, Any]:
        vkey = self._norm_vault(vault)
        with self._lock:
            barrier = self._exclusive_barriers.get(vkey)
            if barrier:
                return {
                    "accepted": False,
                    "reason": "vault_upgrade_barrier_active",
                    "barrier": barrier,
                }
            # Coalesce duplicate sync / upgrade.heal on the same vault
            for active in self._active_jobs.values():
                if active.vault == vkey and active.kind == kind and active.status == "running":
                    if kind == "upgrade.heal" and priority_key and priority_key != active.priority_key:
                        self._followup_heal_priority[vkey] = priority_key
                    return {
                        "accepted": True,
                        "coalesced": True,
                        "job": active.to_dict(),
                    }

            resolved_argv = list(argv) if argv else self._default_argv_for_kind(
                kind,
                priority_key=priority_key,
                backfill_ocr=backfill_ocr,
            )
            job_id = f"job_{uuid.uuid4().hex[:10]}"
            job = SupervisedJob(
                job_id=job_id,
                vault=vkey,
                kind=kind,
                argv=resolved_argv,
                priority_key=priority_key,
            )
            self._active_jobs[job_id] = job

        creationflags = 0x08000000 if sys.platform == "win32" else 0
        try:
            proc = subprocess.Popen(
                [self._python_exe, "-m", "paperforge", "--vault", vkey, *resolved_argv],
                cwd=vkey if Path(vkey).is_dir() else None,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                job.status = "failed"
                job.error = str(exc)
                job.finished_at = time.time()
                self._active_jobs.pop(job_id, None)
                self._recent_jobs.append(job.to_dict())
            return {"accepted": False, "reason": "spawn_failed", "error": str(exc)}

        with self._lock:
            job._proc = proc
            job.pid = proc.pid

        self._emit_push("task.updated", vault=vkey, data=job.to_dict())
        self._write_heartbeat(Path(vkey))

        threading.Thread(
            target=self._drain_stderr,
            args=(job, proc),
            daemon=True,
            name=f"pf-job-err-{job_id}",
        ).start()
        threading.Thread(
            target=self._supervise_worker,
            args=(job, proc),
            daemon=True,
            name=f"pf-job-out-{job_id}",
        ).start()
        return {"accepted": True, "coalesced": False, "job": job.to_dict()}

    @staticmethod
    def _drain_stderr(job: SupervisedJob, proc: subprocess.Popen[str]) -> None:
        if proc.stderr is None:
            return
        try:
            for line in proc.stderr:
                job.stderr_tail = (job.stderr_tail + line)[-4000:]
        except Exception:  # noqa: BLE001
            pass

    def _supervise_worker(self, job: SupervisedJob, proc: subprocess.Popen[str]) -> None:
        if proc.stdout is not None:
            try:
                for raw_line in proc.stdout:
                    line = raw_line.strip()
                    if not line or not line.startswith("{"):
                        continue
                    with contextlib.suppress(json.JSONDecodeError):
                        ev = json.loads(line)
                        if isinstance(ev, dict) and ev.get("schema_version") == 1:
                            ev_type = str(ev.get("event") or "")
                            if "current" in ev and ev["current"] is not None:
                                job.current = int(ev["current"])
                            if "total" in ev and ev["total"] is not None:
                                job.total = int(ev["total"])
                            if "phase" in ev and ev["phase"]:
                                job.phase = str(ev["phase"])
                            if "item_id" in ev and ev["item_id"]:
                                job.item_id = str(ev["item_id"])
                            if ev_type == "cancelled":
                                job.status = "cancelled"
                            self._emit_push("task.updated", vault=job.vault, data=job.to_dict())
            except Exception:  # noqa: BLE001
                pass

        rc = proc.wait()
        followup_prio: str | None = None
        with self._lock:
            job.exit_code = int(rc)
            job.finished_at = time.time()
            job._proc = None
            if job.status == "cancelling" or rc == 130:
                job.status = "cancelled"
            elif rc == 0:
                job.status = "succeeded"
            else:
                job.status = "failed"
                job.error = job.stderr_tail.strip()[-300:] or f"exit code {rc}"
            snap = job.to_dict()
            self._active_jobs.pop(job.job_id, None)
            self._recent_jobs.append(snap)
            if job.kind == "upgrade.heal" and job.status == "succeeded":
                followup_prio = self._followup_heal_priority.pop(job.vault, None)

        self._emit_push("task.updated", vault=job.vault, data=snap)
        with contextlib.suppress(Exception):
            self.get_or_refresh_vault(job.vault)
        self._write_heartbeat(Path(job.vault))

        if job.status == "failed":
            self.push_notice(
                level="warning",
                code=f"job.{job.kind}.failed",
                title=f"后台任务未完成 ({job.kind})",
                detail=job.error,
                vault=job.vault,
            )
        elif job.kind == "upgrade.heal" and job.status == "succeeded":
            self.push_notice(
                level="success",
                code="job.upgrade.heal.done",
                title="文献库后台渐进整理已完成",
                vault=job.vault,
            )

        if followup_prio:
            self.submit_job(job.vault, "upgrade.heal", priority_key=followup_prio)

    def cancel_job(self, job_id: str, *, grace_sec: float = 3.0, wait: bool = False) -> dict[str, Any]:
        with self._lock:
            job = self._active_jobs.get(job_id)
            if job is None:
                return {"ok": False, "reason": "not_found", "job_id": job_id}
            proc = job._proc
            job.status = "cancelling"
            snap = job.to_dict()

        self._emit_push("task.updated", vault=job.vault, data=snap)

        def _escalate() -> None:
            if proc is None or proc.poll() is not None:
                return
            with contextlib.suppress(Exception):
                if proc.stdin:
                    proc.stdin.write("PAPERFORGE_STOP\n")
                    proc.stdin.flush()
            deadline = time.monotonic() + max(0.2, grace_sec)
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    return
                time.sleep(0.1)
            kill_process_tree(proc)

        if wait:
            _escalate()
        else:
            threading.Thread(target=_escalate, daemon=True, name=f"pf-cancel-{job_id}").start()
        return {"ok": True, "job_id": job_id, "status": "cancelling"}

    def cancel_all_jobs(self, *, grace_sec: float = 1.5) -> int:
        with self._lock:
            ids = list(self._active_jobs.keys())
        for jid in ids:
            self.cancel_job(jid, grace_sec=grace_sec, wait=True)
        return len(ids)

    def list_jobs(self, *, vault: str | None = None, include_recent: bool = True) -> dict[str, Any]:
        vkey = self._norm_vault(vault) if vault else None
        with self._lock:
            active = [
                j.to_dict() for j in self._active_jobs.values() if vkey is None or j.vault == vkey
            ]
            recent = (
                [dict(r) for r in self._recent_jobs if vkey is None or r.get("vault") == vkey]
                if include_recent
                else []
            )
        return {"active": active, "recent": recent}

    def has_active_jobs(self) -> bool:
        with self._lock:
            return bool(self._active_jobs)

    def check_parent_alive(self) -> bool:
        return is_pid_alive(self._parent_pid)

    def _write_heartbeat(self, vault_root: Path) -> None:
        indexes_dir = vault_root / ".paperforge" / "indexes"
        if not indexes_dir.is_dir():
            return
        with contextlib.suppress(Exception):
            from paperforge.core.io import write_json_atomic

            with self._lock:
                active = [j.to_dict() for j in self._active_jobs.values() if j.vault == str(vault_root)]
            write_json_atomic(
                indexes_dir / ".daemon-state.json",
                {
                    "schema_version": 1,
                    "pid": os.getpid(),
                    "parent_pid": self._parent_pid,
                    "rss_bytes": get_process_rss_bytes(),
                    "active_jobs": active,
                    "updated_at": time.time(),
                },
            )

    def health(self, vault: str | Path | None = None) -> dict[str, Any]:
        rss = get_process_rss_bytes()
        heavy_loaded = [m for m in HEAVY_MODULE_PROBES if m in sys.modules]
        jobs = self.list_jobs(vault=str(vault) if vault else None, include_recent=False)
        notices = self.list_notices(vault=str(vault) if vault else None, include_acked=False)
        with self._lock:
            cached = [
                {
                    "vault": v["vault_key"],
                    "seq": v["last_seq"],
                    "workspace_count": len(v["workspace_map"]),
                    "hits": v["hits"],
                    "misses": v["misses"],
                }
                for v in self._vault_caches.values()
            ]
        return {
            "ok": True,
            "pid": os.getpid(),
            "parent_pid": self._parent_pid,
            "uptime_sec": round(time.time() - self._started_at, 2),
            "rss_bytes": rss,
            "rss_mb": round(rss / (1024 * 1024), 2) if rss else 0.0,
            "heavy_modules_loaded": heavy_loaded,
            "active_jobs": jobs["active"],
            "unacked_notice_count": len(notices),
            "cached_vaults": cached,
        }
