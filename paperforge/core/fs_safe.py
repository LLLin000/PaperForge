"""Filesystem traversal helpers resilient to Windows reserved names and OS quirks."""

from __future__ import annotations

import os
from pathlib import Path

_WIN_RESERVED_NAMES = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
)

DEFAULT_SKIP_DIRS = frozenset({".obsidian", ".trash", ".git", "node_modules"})
LITERATURE_SKIP_DIRS = DEFAULT_SKIP_DIRS | frozenset({"assets", "ai", "render", "figures", "tables"})


def chunked_io_map(
    fn,
    items,
    *,
    chunk_size: int = 64,
    max_workers: int | None = None,
    min_parallel: int = 64,
) -> list:
    """Apply *fn* over *items* using chunk-batched threads to avoid per-file GIL contention."""
    seq = list(items)
    if not seq:
        return []
    if len(seq) < min_parallel:
        return [fn(item) for item in seq]
    from concurrent.futures import ThreadPoolExecutor

    step = max(1, int(chunk_size))
    chunks = [seq[i : i + step] for i in range(0, len(seq), step)]
    workers = min(max_workers or adaptive_io_workers(), len(chunks))

    def _run_chunk(batch: list) -> list:
        return [fn(item) for item in batch]

    out: list = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for part in pool.map(_run_chunk, chunks):
            out.extend(part)
    return out


def adaptive_io_workers(default_cap: int = 8) -> int:
    """Return a gentle bounded I/O worker count for cold file scans.

    Respects ``PAPERFORGE_IO_WORKERS`` (clamped to ``1..16``) and otherwise
    scales conservatively with CPU count (capped at *default_cap*) so low-spec
    laptops, HDDs, and cloud-synced drives are never saturated.
    """
    raw = os.environ.get("PAPERFORGE_IO_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(16, int(raw)))
        except ValueError:
            pass
    cpus = os.cpu_count() or 4
    return min(default_cap, max(2, cpus))


def is_windows_reserved_name(name: str) -> bool:
    """Return True if *name* matches a Windows DOS reserved device name (e.g. ``nul``, ``CON.txt``)."""
    cleaned = str(name or "").rstrip(". ").strip()
    if not cleaned:
        return False
    stem = cleaned.split(".", 1)[0].lower()
    return stem in _WIN_RESERVED_NAMES


def safe_is_dir(path: Path) -> bool:
    """Return True if *path* is an existing directory, guarding Windows reserved names and OSError."""
    if is_windows_reserved_name(path.name):
        return False
    try:
        return path.is_dir()
    except OSError:
        return False


def safe_is_file(path: Path) -> bool:
    """Return True if *path* is an existing regular file, guarding Windows reserved names and OSError."""
    if is_windows_reserved_name(path.name):
        return False
    try:
        return path.is_file()
    except OSError:
        return False


def safe_iterdir(path: Path) -> list[Path]:
    """List direct child Paths of *path* sorted by name, skipping Windows reserved names and OSError."""
    if is_windows_reserved_name(path.name):
        return []
    entries: list[Path] = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if is_windows_reserved_name(entry.name):
                    continue
                entries.append(Path(entry.path))
    except OSError:
        return []
    entries.sort(key=lambda p: p.name)
    return entries


def safe_rglob(
    root: Path,
    suffix: str = ".md",
    skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS,
) -> list[Path]:
    """Recursively collect files matching *suffix* under *root*, skipping reserved names and junctions."""
    if not safe_is_dir(root):
        return []
    norm_suffix = suffix.lower()
    matched: list[Path] = []
    try:
        for dirpath_str, dirnames, filenames in os.walk(str(root), followlinks=False):
            kept_dirs = [
                d
                for d in sorted(dirnames)
                if d not in skip_dirs and not is_windows_reserved_name(d)
            ]
            dirnames[:] = kept_dirs
            base = Path(dirpath_str)
            for fname in sorted(filenames):
                if is_windows_reserved_name(fname):
                    continue
                if norm_suffix and not fname.lower().endswith(norm_suffix):
                    continue
                matched.append(base / fname)
    except OSError:
        return sorted(matched)
    matched.sort()
    return matched
