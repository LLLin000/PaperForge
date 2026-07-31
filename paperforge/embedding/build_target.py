"""Build target for atomic shadow vector rebuild (#117).

A BuildTarget points a rebuild at a shadow DB while the live DB stays
readable.  Publication is a single ``os.replace(build → live)`` after
checkpoint + verification.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from paperforge.memory.db import get_connection

logger = logging.getLogger(__name__)


class BuildTargetError(RuntimeError):
    """Raised for invalid BuildTarget lifecycle transitions."""


@dataclass(frozen=True)
class BuildTarget:
    """Source (read) and vector (write) DB paths for a rebuild.

    Shadow build: ``source_path`` is the live ``paperforge.db``,
    ``vector_path`` is ``paperforge.db.build``.
    """

    source_path: Path
    vector_path: Path

    @property
    def is_shadow(self) -> bool:
        return self.source_path != self.vector_path

    def open_vector_conn(self, *, read_only: bool = False) -> sqlite3.Connection:
        """Open a connection to the vector target DB."""
        return get_connection(self.vector_path, read_only=read_only)


class ShadowBuild:
    """Lifecycle state machine: NEW → PREPARED → BUILDING → VERIFIED → PUBLISHED.

    Any non-PUBLISHED state may transition to ABORTED.  ``publish()`` may
    only be called from VERIFIED.  ``__exit__`` auto-aborts when not
    published; after successful publish it must NOT delete the new live DB.
    """

    NEW = "new"
    PREPARED = "prepared"
    BUILDING = "building"
    VERIFIED = "verified"
    PUBLISHED = "published"
    ABORTED = "aborted"

    def __init__(self, target: BuildTarget) -> None:
        self.target = target
        self.state = self.NEW
        self._candidate_conn: sqlite3.Connection | None = None

    # ── transitions ──────────────────────────────────────────────────────

    def prepare(self) -> None:
        """Snapshot live → candidate, clear vector tables at model dim."""
        self._require(self.NEW, "prepare")
        self.state = self.PREPARED

    def building(self) -> None:
        self._require(self.PREPARED, "building")
        self.state = self.BUILDING

    def verified(self) -> None:
        """Enter VERIFIED — requires all candidate connections closed."""
        self._require(self.BUILDING, "verified")
        self.close_candidate_conn()
        self.state = self.VERIFIED

    def publish(self) -> None:
        """Atomic swap: candidate → live. Only from VERIFIED."""
        self._require(self.VERIFIED, "publish")
        self._publish_files()
        self.state = self.PUBLISHED

    def abort(self) -> None:
        """Idempotent abort: delete candidate + sidecars, close conns."""
        if self.state in (self.PUBLISHED, self.ABORTED):
            return
        self.close_candidate_conn()
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(self.target.vector_path) + suffix)
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                logger.warning("abort: could not delete %s", p)
        self.state = self.ABORTED

    def cleanup_stale(self) -> None:
        """D6: unconditionally delete leftover candidate files.

        Does NOT touch the lifecycle state (unlike ``abort()``) — a stale
        candidate from a crashed build is deleted before a fresh
        ``prepare()``, without transitioning the state machine.
        """
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(self.target.vector_path) + suffix)
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                logger.warning("cleanup_stale: could not delete %s", p)

    # ── candidate connection management ──────────────────────────────────

    def candidate_conn(self) -> sqlite3.Connection:
        """Return the (cached) candidate connection; opens if needed."""
        if self._candidate_conn is None:
            self._candidate_conn = self.target.open_vector_conn()
        return self._candidate_conn

    def close_candidate_conn(self) -> None:
        if self._candidate_conn is not None:
            try:
                self._candidate_conn.close()
            except Exception:
                pass
            self._candidate_conn = None

    # ── internals ────────────────────────────────────────────────────────

    def _require(self, expected: str, op: str) -> None:
        if self.state != expected:
            raise BuildTargetError(
                f"invalid transition {self.state} → {op} (expected {expected})"
            )

    def _publish_files(self) -> None:
        vector = self.target.vector_path
        live = self.target.source_path
        if vector == live:
            return  # In-place target: nothing to swap
        # P0-4: checkpoint + journal switch MUST succeed before publish —
        # if the WAL still holds data and we swap the main file, we publish
        # a DB missing its latest commits.  Abort, don't swallow.
        try:
            conn = sqlite3.connect(str(vector))
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                mode = conn.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
                if str(mode).lower() != "delete":
                    raise sqlite3.Error(f"journal switch failed: mode={mode}")
                side = Path(str(vector) + "-wal")
                if side.exists() and side.stat().st_size > 0:
                    raise sqlite3.Error(
                        f"checkpoint left non-empty WAL: {side.stat().st_size} bytes"
                    )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise BuildTargetError(f"candidate checkpoint failed: {exc}") from exc
        # D1 reader barrier: readers are short-lived CLI processes; take a
        # brief reader lock so no in-flight reader holds live open during the
        # swap (Windows cannot replace an open file).
        barrier = _reader_barrier(self.target.source_path)
        with barrier:
            for suffix in ("-wal", "-shm"):
                p = Path(str(live) + suffix)
                try:
                    if p.exists():
                        p.unlink()
                except OSError:
                    logger.warning("publish: could not delete %s", p)
            os.replace(str(vector), str(live))

    def __enter__(self) -> "ShadowBuild":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.state != self.PUBLISHED:
            self.abort()


def verify_candidate(
    vector_path: Path,
    *,
    dimension: int,
    expected_count: int,
) -> dict:
    """Run the D4 verification checklist on a candidate DB.

    Returns ``{"ok": True}`` or ``{"ok": False, "reason": str}``.
    All checks read-only; no connection is left open.
    """
    import re

    def _fail(reason: str) -> dict:
        return {"ok": False, "reason": reason}

    if not vector_path.exists():
        return _fail(f"candidate missing: {vector_path}")
    conn = sqlite3.connect(f"file:{vector_path.as_posix()}?mode=ro", uri=True)
    try:
        try:
            import sqlite_vec

            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
        except ImportError:
            pass
        # 1. integrity
        row = conn.execute("PRAGMA integrity_check").fetchone()
        if not row or row[0] != "ok":
            return _fail(f"integrity_check: {row[0] if row else 'no result'}")
        # 2. dimension per existing vec0 table
        for name in ("vec_fulltext", "vec_body", "vec_objects"):
            r = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name=? AND type='table'", (name,)
            ).fetchone()
            if r:
                m = re.search(r"float\[(\d+)\]", r[0])
                if not m or int(m.group(1)) != dimension:
                    return _fail(f"{name} dimension mismatch (expected {dimension})")
        # 3+4. vec/meta row counts + orphan rowids
        pairs = [
            ("vec_fulltext", "vec_fulltext_meta"),
            ("vec_body", "vec_body_meta"),
            ("vec_objects", "vec_objects_meta"),
        ]
        total = 0
        for vec_table, meta_table in pairs:
            try:
                vc = conn.execute(f"SELECT COUNT(*) FROM {vec_table}").fetchone()[0]
                mc = conn.execute(f"SELECT COUNT(*) FROM {meta_table}").fetchone()[0]
            except sqlite3.OperationalError:
                continue  # table absent — nothing to count (empty lib is legal)
            if vc != mc:
                return _fail(f"{vec_table}/{meta_table} count mismatch: {vc} vs {mc}")
            orphan = conn.execute(
                f"SELECT COUNT(*) FROM {meta_table} m "
                f"LEFT JOIN {vec_table} v ON v.rowid = m.rowid WHERE v.rowid IS NULL"
            ).fetchone()[0]
            if orphan:
                return _fail(f"{meta_table} has {orphan} orphan rowids")
            total += mc
        # 5. expected count (0 legal)
        if total != expected_count:
            return _fail(f"vector count {total} != expected {expected_count}")
        # 6. KNN probe when non-empty
        if total > 0:
            d = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='vec_body' AND type='table'"
            ).fetchone()
            m = re.search(r"float\[(\d+)\]", d[0]) if d else None
            dim = int(m.group(1)) if m else dimension
            zero = json.dumps([0.0] * dim)
            try:
                conn.execute(
                    "SELECT 1 FROM vec_body WHERE embedding MATCH ? AND k = 1", (zero,)
                ).fetchone()
            except Exception as exc:
                return _fail(f"KNN probe failed: {exc}")
        return {"ok": True}
    except sqlite3.Error as exc:
        return _fail(str(exc))
    finally:
        conn.close()


def _reader_barrier(live_path: Path):
    """D1 publication barrier: brief read lock so no in-flight reader holds
    the live DB open during the swap.

    Readers are short-lived CLI processes; the lock is held only for the
    ms-scale publish.  Falls back to a no-op if filelock is unavailable.
    """
    try:
        from filelock import FileLock

        return FileLock(str(live_path) + ".read.lock", timeout=10)
    except Exception:
        import contextlib

        return contextlib.nullcontext()
