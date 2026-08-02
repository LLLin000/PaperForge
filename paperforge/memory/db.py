from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from paperforge.config import paperforge_paths


def get_memory_db_path(vault: Path) -> Path:
    """Return the absolute path to paperforge.db."""
    paths = paperforge_paths(vault)
    index_path = paths.get("index")
    if not index_path:
        raise FileNotFoundError("index path not configured")
    return index_path.parent / "paperforge.db"


class WriterLock:
    """Re-entrant per-thread writer lock backed by a cross-process filelock.

    Top-level mutating commands (embed build, memory build, refresh flows,
    restore-backup, force-rebuild restore) acquire this ONCE.  Nested rw
    connections within the same thread do not re-block (thread-local
    recursion counter).  Never acquire inside ``get_connection`` — embed
    build opens 12+ rw connections per run and would deadlock on the
    non-re-entrant filelock.

    Use as a context manager::

        with writer_lock(vault):
            ...  # whole build/prepare/publish duration
    """

    _local = threading.local()

    def __init__(self, vault: Path, timeout: float = -1) -> None:
        from filelock import FileLock

        db_path = get_memory_db_path(vault)
        self._key = str(db_path.resolve())
        self._lock = FileLock(str(db_path) + ".write.lock", timeout=timeout)
        self._acquired = False

    def __enter__(self) -> "WriterLock":
        # Per-DB-path depth (P1-2): a thread nesting across two different
        # vaults must take each vault's own file lock — a single shared
        # counter would treat the second vault as re-entry and skip its lock.
        depths: dict[str, int] = getattr(self._local, "depths", {})
        depth = depths.get(self._key, 0)
        if depth > 0:
            depths[self._key] = depth + 1
            self._local.depths = depths
            # P0-3: do NOT touch self._acquired on re-entry.  A fresh nested
            # instance starts with _acquired=False; re-entering the SAME
            # instance must keep its first-acquisition ownership True so the
            # outermost __exit__ actually releases the file lock.
            return self
        self._lock.acquire()
        self._acquired = True
        depths[self._key] = 1
        self._local.depths = depths
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        depths: dict[str, int] = getattr(self._local, "depths", {})
        depth = depths.get(self._key, 0)
        if depth > 1:
            depths[self._key] = depth - 1
            self._local.depths = depths
            return
        depths.pop(self._key, None)
        self._local.depths = depths
        if self._acquired:
            self._lock.release()
            self._acquired = False


def get_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection to paperforge.db with WAL mode.

    Args:
        db_path: Path to paperforge.db.
        read_only: If True, open in read-only mode (for queries).
    """
    if read_only:
        uri = "file:" + db_path.as_posix() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Capture freshness BEFORE connect() — sqlite3.connect creates the
        # file, so a post-connect exists() check would always be True and a
        # fresh DB would never get its one-time WAL initialization.
        was_new = not db_path.exists()
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not read_only and was_new:
        # Fresh DB: initialize WAL once.  Existing DBs keep their current
        # journal mode — a shadow publish switches live to DELETE (D1) and a
        # later rw connection must NOT flip it back to WAL (which resurrects
        # -wal/-shm sidecars the publish explicitly cleared).
        conn.execute("PRAGMA journal_mode=WAL;")
    if not read_only:
        conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def ensure_vec_extension(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension if available.

    Enables vec0 virtual table support for vector similarity search.
    Gracefully no-ops when the extension is not installed.
    """
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
        except Exception:
            pass  # extension not available
        finally:
            try:
                conn.enable_load_extension(False)
            except AttributeError:
                pass
    except ImportError:
        pass  # sqlite_vec not installed


_reader_lock_depths = threading.local()


def open_live_reader(vault: Path, db_path: Path | None = None):
    """Open a read-only connection to the live paperforge.db under the
    publication barrier (D1).  All retrieval/status readers MUST go through
    this entry so a shadow publish's brief reader lock actually quiesces them
    (Windows cannot replace a file another process holds open).

    The barrier is re-entrant per thread AND per DB path: nested readers of
    the SAME database (a command that opens it through several layers)
    acquire the thread-level lock once, while a thread that nests across two
    different vaults/databases still takes each database's own lock.  A lock
    *timeout* is NOT a licence to read unlocked — it propagates to the
    caller, which should treat it as a transient retryable failure (a
    publish is in progress).

    Usage::

        with open_live_reader(vault) as conn:
            ...  # read-only queries
    """
    from contextlib import contextmanager
    from filelock import FileLock

    @contextmanager
    def _reader():
        path = db_path or get_memory_db_path(vault)
        key = str(path.resolve())
        depths: dict[str, int] = getattr(_reader_lock_depths, "depths", {})
        depth = depths.get(key, 0)
        barrier = None
        if depth == 0:
            # First (outermost) reader of THIS database in this thread takes
            # the file lock.  Timeout raises filelock.Timeout — intentionally
            # NOT caught: reading without the barrier defeats the publish
            # quiescence.
            barrier = FileLock(str(path) + ".read.lock", timeout=10)
            barrier.acquire()
        depths[key] = depth + 1
        _reader_lock_depths.depths = depths
        try:
            conn = get_connection(path, read_only=True)
            try:
                yield conn
            finally:
                conn.close()
        finally:
            depths[key] = depth
            if barrier is not None:
                barrier.release()

    return _reader()
