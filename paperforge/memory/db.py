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
        self._lock = FileLock(str(db_path) + ".write.lock", timeout=timeout)
        self._acquired = False

    def __enter__(self) -> "WriterLock":
        depth = getattr(self._local, "depth", 0)
        if depth > 0:
            self._local.depth = depth + 1
            self._acquired = False  # nested: re-entrant, no new file lock
            return self
        self._lock.acquire()
        self._acquired = True
        self._local.depth = 1
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        depth = getattr(self._local, "depth", 0)
        if depth > 1:
            self._local.depth = depth - 1
            return
        self._local.depth = 0
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
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not read_only and not db_path.exists():
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


_reader_lock_depth = threading.local()


def open_live_reader(vault: Path, db_path: Path | None = None):
    """Open a read-only connection to the live paperforge.db under the
    publication barrier (D1).  All retrieval/status readers MUST go through
    this entry so a shadow publish's brief reader lock actually quiesces them
    (Windows cannot replace a file another process holds open).

    The barrier is re-entrant per thread: nested readers (a command that
    opens the DB through several layers) acquire the same thread-level lock
    once.  A lock *timeout* is NOT a licence to read unlocked — it
    propagates to the caller, which should treat it as a transient
    retryable failure (a publish is in progress).

    Usage::

        with open_live_reader(vault) as conn:
            ...  # read-only queries
    """
    from contextlib import contextmanager
    from filelock import FileLock

    @contextmanager
    def _reader():
        path = db_path or get_memory_db_path(vault)
        depth = getattr(_reader_lock_depth, "depth", 0)
        barrier = None
        if depth == 0:
            # First (outermost) reader in this thread takes the file lock.
            # Timeout raises filelock.Timeout — intentionally NOT caught:
            # reading without the barrier defeats the publish quiescence.
            barrier = FileLock(str(path) + ".read.lock", timeout=10)
            barrier.acquire()
        _reader_lock_depth.depth = depth + 1
        try:
            conn = get_connection(path, read_only=True)
            try:
                yield conn
            finally:
                conn.close()
        finally:
            _reader_lock_depth.depth = depth
            if barrier is not None:
                barrier.release()

    return _reader()
