"""Git-index-style (size, mtime_ns, ctime_ns) -> SHA-256 fingerprint cache.

Avoids re-reading large PDFs and OCR artifacts on read-only probe/lineage checks
while guarding against sub-second filesystem timestamp ambiguity ("racy-git"
2-second window) and keeping all cache state strictly outside vault directories.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import threading
import time
from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path

#: Never trust cached mtime/size for files modified within the last 2 seconds.
RACY_WINDOW_NS = 2_000_000_000
_MEMORY_MAX_ENTRIES = 8192
_COMPOSITE_PREFIX = "concat::"

_LOCK = threading.Lock()
_MEM_CACHE: OrderedDict[str, tuple[int, int, int, str]] = OrderedDict()


def resolve_user_cache_dir() -> Path:
    """Return user-local cache directory outside any vault."""
    override = os.environ.get("PAPERFORGE_CACHE_DIR", "").strip()
    if override:
        return Path(override)
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app:
            return Path(local_app) / "PaperForge" / "cache"
        return Path.home() / "AppData" / "Local" / "PaperForge" / "cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "PaperForge"
    xdg_cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(xdg_cache) if xdg_cache else (Path.home() / ".cache")
    return base / "paperforge"


def _stat_cache_db_path() -> Path:
    return resolve_user_cache_dir() / "stat_cache_v1.sqlite3"


def _mem_get(key: str, sig: tuple[int, int, int]) -> str | None:
    with _LOCK:
        entry = _MEM_CACHE.get(key)
        if entry is None:
            return None
        if entry[:3] != sig:
            _MEM_CACHE.pop(key, None)
            return None
        _MEM_CACHE.move_to_end(key)
        return entry[3]


def _mem_put(key: str, sig: tuple[int, int, int], digest: str) -> None:
    with _LOCK:
        _MEM_CACHE[key] = (sig[0], sig[1], sig[2], digest)
        _MEM_CACHE.move_to_end(key)
        while len(_MEM_CACHE) > _MEMORY_MAX_ENTRIES:
            _MEM_CACHE.popitem(last=False)


def _db_connect() -> sqlite3.Connection:
    db_path = _stat_cache_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=2.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS file_stat_hashes (
            cache_key TEXT PRIMARY KEY,
            size_bytes INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            ctime_ns INTEGER NOT NULL,
            sha256 TEXT NOT NULL
        );
        """
    )
    return conn


def _db_get(key: str, sig: tuple[int, int, int]) -> str | None:
    try:
        db_path = _stat_cache_db_path()
        if not db_path.is_file():
            return None
        conn = _db_connect()
        try:
            row = conn.execute(
                "SELECT size_bytes, mtime_ns, ctime_ns, sha256 "
                "FROM file_stat_hashes WHERE cache_key = ?",
                (key,),
            ).fetchone()
        finally:
            conn.close()
        if row and (int(row[0]), int(row[1]), int(row[2])) == sig:
            return str(row[3])
    except (sqlite3.Error, OSError):
        return None
    return None


def _db_put(key: str, sig: tuple[int, int, int], digest: str) -> None:
    try:
        conn = _db_connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_stat_hashes
                    (cache_key, size_bytes, mtime_ns, ctime_ns, sha256)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key, sig[0], sig[1], sig[2], digest),
            )
            conn.commit()
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        pass


def _stream_sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cached_sha256_hex(path: Path) -> str:
    """Return SHA-256 hex digest for *path*, backed by a racy-git-safe stat cache."""
    resolved = Path(path).resolve()
    st = resolved.stat()
    now_ns = time.time_ns()
    is_racy = abs(now_ns - st.st_mtime_ns) < RACY_WINDOW_NS
    sig = (int(st.st_size), int(st.st_mtime_ns), int(getattr(st, "st_ctime_ns", 0)))
    key = str(resolved)

    if not is_racy:
        cached = _mem_get(key, sig)
        if cached is not None:
            return cached
        cached = _db_get(key, sig)
        if cached is not None:
            _mem_put(key, sig, cached)
            return cached

    digest = _stream_sha256_hex(resolved)
    if not is_racy:
        _mem_put(key, sig, digest)
        _db_put(key, sig, digest)
    return digest


def cached_concat_sha256_hex(paths: Sequence[Path]) -> str | None:
    """Return SHA-256 over the exact concatenation of *paths*, or ``None`` if any is missing."""
    resolved_paths: list[Path] = []
    stats: list[os.stat_result] = []
    for raw in paths:
        resolved = Path(raw).resolve()
        if not resolved.is_file():
            return None
        resolved_paths.append(resolved)
        stats.append(resolved.stat())

    now_ns = time.time_ns()
    all_non_racy = all(abs(now_ns - st.st_mtime_ns) >= RACY_WINDOW_NS for st in stats)

    # Pack all constituent stat stamps into a deterministic single key + aggregate sig.
    composite_key = _COMPOSITE_PREFIX + "|".join(str(p) for p in resolved_paths)
    total_size = sum(int(st.st_size) for st in stats)
    max_mtime = max((int(st.st_mtime_ns) for st in stats), default=0)
    mix_ctime = 0
    for st in stats:
        mix_ctime = (mix_ctime * 1315423911 + int(st.st_mtime_ns) + int(st.st_size)) & ((1 << 62) - 1)
    agg_sig = (total_size, max_mtime, mix_ctime)

    if all_non_racy:
        cached = _mem_get(composite_key, agg_sig)
        if cached is not None:
            return cached
        cached = _db_get(composite_key, agg_sig)
        if cached is not None:
            _mem_put(composite_key, agg_sig, cached)
            return cached

    digest = hashlib.sha256()
    for p in resolved_paths:
        with p.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    hex_digest = digest.hexdigest()

    if all_non_racy:
        _mem_put(composite_key, agg_sig, hex_digest)
        _db_put(composite_key, agg_sig, hex_digest)
    return hex_digest


def clear_memory_cache() -> None:
    """Clear in-process stat cache entries (intended for tests)."""
    with _LOCK:
        _MEM_CACHE.clear()
