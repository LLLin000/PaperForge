from __future__ import annotations

import logging
import re
import sqlite3
import threading
from pathlib import Path

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)


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


def quarantine_corrupt_db(db_path: Path) -> Path | None:
    """Detect an unreadable/corrupt SQLite file at *db_path* and move it aside.

    Returns the quarantine Path when *db_path* was quarantined, or None when
    *db_path* does not exist or is a valid SQLite database.
    """
    if not db_path.is_file():
        return None
    corrupt = False
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
    except sqlite3.DatabaseError:
        corrupt = True
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    if not corrupt:
        return None

    import shutil
    import time

    ts = time.strftime("%Y%m%dT%H%M%S")
    ns = str(int(time.time_ns() % 1_000_000_000)).zfill(9)
    quarantine_path = db_path.with_name(f"paperforge.corrupt-{ts}-{ns}.db")
    shutil.move(str(db_path), str(quarantine_path))
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                pass
    return quarantine_path


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
        except Exception as exc:
            logger.debug("sqlite_vec load skipped: %s", exc)
        finally:
            try:
                conn.enable_load_extension(False)
            except AttributeError:
                pass
    except ImportError as exc:
        logger.debug("sqlite_vec not installed: %s", exc)


def _rebuild_body_units_fts(conn: sqlite3.Connection) -> None:
    """Rebuild ``body_units_fts`` strictly from ``indexable = 1`` rows."""
    conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('delete-all')")
    conn.execute(
        """INSERT INTO body_units_fts(rowid, unit_id, paper_id, section_path, unit_text)
           SELECT rowid, unit_id, paper_id, section_path, unit_text
           FROM body_units
           WHERE indexable = 1"""
    )


def _rebuild_single_fts(conn: sqlite3.Connection, tbl: str) -> None:
    """Rebuild one external-content FTS5 table according to its indexing contract."""
    if tbl == "body_units_fts":
        _rebuild_body_units_fts(conn)
    else:
        conn.execute(f"INSERT INTO {tbl}({tbl}) VALUES('rebuild')")


_FTS5_OPERATORS = frozenset({"AND", "OR", "NOT", "NEAR"})


def _extract_fts5_probe_token(text: str) -> str | None:
    """Return a single safe ASCII alphanumeric FTS5 token from *text*, or None."""
    for match in re.finditer(r"[A-Za-z][A-Za-z0-9]{4,}", text or ""):
        tok = match.group(0)
        if tok.upper() not in _FTS5_OPERATORS:
            return tok
    return None


def _body_units_fts_content_drifted(conn: sqlite3.Connection, sample_limit: int = 8) -> bool:
    """Sample boundary ``indexable = 1`` rows to catch same-rowid text drift."""
    head = conn.execute(
        "SELECT rowid, unit_text FROM body_units WHERE indexable = 1 ORDER BY rowid ASC LIMIT ?",
        (sample_limit,),
    ).fetchall()
    tail = conn.execute(
        "SELECT rowid, unit_text FROM body_units WHERE indexable = 1 ORDER BY rowid DESC LIMIT ?",
        (sample_limit,),
    ).fetchall()
    sampled: dict[int, str] = {}
    for row in (*head, *tail):
        rid = int(row[0])
        if rid not in sampled:
            sampled[rid] = str(row[1] or "")
    for rid, text in sampled.items():
        tok = _extract_fts5_probe_token(text)
        if not tok:
            continue
        hit = conn.execute(
            "SELECT 1 FROM body_units_fts WHERE rowid = ? AND body_units_fts MATCH ? LIMIT 1",
            (rid, f'"{tok}"'),
        ).fetchone()
        if hit is None:
            return True
    return False


def _fts_integrity_needs_heal(conn: sqlite3.Connection, tbl: str) -> bool:
    """Return True when an external-content FTS5 table fails structural or parity checks."""
    try:
        if tbl == "paper_fts":
            conn.execute("INSERT INTO paper_fts(paper_fts, rank) VALUES('integrity-check', 1)")
            papers_cnt = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            doc_cnt = conn.execute("SELECT COUNT(*) FROM paper_fts_docsize").fetchone()[0]
            return doc_cnt != papers_cnt
        if tbl == "body_units_fts":
            conn.execute("INSERT INTO body_units_fts(body_units_fts) VALUES('integrity-check')")
            idx_cnt = conn.execute("SELECT COUNT(*) FROM body_units WHERE indexable = 1").fetchone()[0]
            doc_cnt = conn.execute("SELECT COUNT(*) FROM body_units_fts_docsize").fetchone()[0]
            if doc_cnt != idx_cnt:
                return True
            drift = conn.execute(
                """SELECT 1 FROM body_units_fts_docsize d
                   LEFT JOIN body_units b ON b.rowid = d.id
                   WHERE b.rowid IS NULL OR b.indexable != 1
                   LIMIT 1"""
            ).fetchone()
            if drift is not None:
                return True
            return _body_units_fts_content_drifted(conn)
        conn.execute(f"INSERT INTO {tbl}({tbl}) VALUES('integrity-check')")
        return False
    except sqlite3.DatabaseError:
        return True


def rebuild_fts_indexes(
    conn: sqlite3.Connection,
    tables: tuple[str, ...] = ("paper_fts", "body_units_fts"),
) -> list[str]:
    """Rebuild existing external-content FTS5 virtual tables non-destructively."""
    existing = {
        str(r[0])
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    rebuilt: list[str] = []
    for tbl in tables:
        if tbl not in existing:
            continue
        _rebuild_single_fts(conn, tbl)
        rebuilt.append(tbl)
    return rebuilt


def _recreate_external_fts_table(conn: sqlite3.Connection, tbl: str) -> None:
    """Recover an external-content FTS5 virtual table whose shadow metadata is corrupt."""
    from paperforge.memory.schema import (
        CREATE_BODY_UNITS_FTS,
        CREATE_PAPER_FTS,
        FTS_TRIGGERS,
    )

    try:
        conn.execute(f"DROP TABLE IF EXISTS {tbl}")
    except sqlite3.DatabaseError:
        for suffix in ("_data", "_idx", "_docsize", "_config", "_content"):
            try:
                conn.execute(f"DROP TABLE IF EXISTS {tbl}{suffix}")
            except sqlite3.DatabaseError as exc:
                logger.debug("ignoring shadow drop error for %s%s: %s", tbl, suffix, exc)
        conn.execute("PRAGMA writable_schema=ON")
        try:
            conn.execute("DELETE FROM sqlite_master WHERE type='table' AND name=?", (tbl,))
        finally:
            conn.execute("PRAGMA writable_schema=RESET")

    if tbl == "paper_fts":
        conn.execute(CREATE_PAPER_FTS)
        for trig_sql in FTS_TRIGGERS:
            conn.execute(trig_sql)
    elif tbl == "body_units_fts":
        conn.execute(CREATE_BODY_UNITS_FTS)
    else:
        raise ValueError(f"Unsupported FTS5 virtual table for recreation: {tbl}")


def check_and_heal_fts(
    conn: sqlite3.Connection,
    tables: tuple[str, ...] = ("paper_fts", "body_units_fts"),
) -> dict[str, list[str]]:
    """Verify FTS5 integrity and non-destructively rebuild any desynced FTS5 table.

    Distinguishes logical external-content FTS5 index desync from physical DB
    corruption so Tier-0 vectors, annotations, and logs are never quarantined.
    """
    existing = {
        str(r[0])
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    checked: list[str] = []
    repaired: list[str] = []
    for tbl in tables:
        if tbl not in existing:
            continue
        checked.append(tbl)
        if _fts_integrity_needs_heal(conn, tbl):
            try:
                _rebuild_single_fts(conn, tbl)
            except sqlite3.DatabaseError:
                _recreate_external_fts_table(conn, tbl)
                _rebuild_single_fts(conn, tbl)
            repaired.append(tbl)
    return {"checked": checked, "repaired": repaired}


def safe_delete_body_units_fts(conn: sqlite3.Connection, paper_id: str) -> bool:
    """Safely remove *paper_id* rows from ``body_units_fts`` before mutating ``body_units``.

    Returns True if the targeted external-content delete succeeded, or False if
    ``body_units_fts`` raised a ``DatabaseError`` (desynced index) and requires
    ``rebuild_fts_indexes(conn, ("body_units_fts",))`` after the mutation.
    """
    try:
        conn.execute(
            """INSERT INTO body_units_fts(body_units_fts, rowid, unit_id, paper_id, section_path, unit_text)
               SELECT 'delete', rowid, unit_id, paper_id, section_path, unit_text
               FROM body_units WHERE paper_id = ? AND indexable = 1""",
            (paper_id,),
        )
        return True
    except sqlite3.DatabaseError:
        return False


_reader_lock_depths = threading.local()


def _recover_hot_journal_if_present(path: Path) -> bool:
    """Roll back an orphaned SQLite hot journal so ``?mode=ro`` readers never fail."""
    journal = Path(str(path) + "-journal")
    try:
        if not journal.is_file() or journal.stat().st_size == 0:
            return False
    except OSError:
        return False
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(path), timeout=2.0)
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
        return True
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


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
            _recover_hot_journal_if_present(path)
            conn = get_connection(path, read_only=True)
            try:
                try:
                    conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
                except sqlite3.OperationalError as exc:
                    if "readonly database" in str(exc).lower():
                        conn.close()
                        _recover_hot_journal_if_present(path)
                        conn = get_connection(path, read_only=True)
                    else:
                        raise
                yield conn
            finally:
                conn.close()
        finally:
            depths[key] = depth
            if barrier is not None:
                barrier.release()

    return _reader()
