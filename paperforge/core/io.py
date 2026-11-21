"""Crash-safe atomic file I/O, CAS guards, and tolerant JSONL readers."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_IS_WINDOWS = os.name == "nt"


class CASConflictError(OSError):
    """Raised when a target file changed on disk between read and atomic write."""


def _atomic_replace_with_retry(tmp_path: Path, dst_path: Path, retries: int = 4) -> None:
    """Replace *dst_path* with *tmp_path*, retrying transient Windows AV/indexer locks."""
    for attempt in range(retries):
        try:
            os.replace(str(tmp_path), str(dst_path))
            return
        except PermissionError:
            if attempt >= retries - 1:
                raise
            time.sleep(0.015 * (attempt + 1))


def read_json(path: Path) -> Any:
    """Read and parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def _preserve_or_default_posix_mode(tmp_path: Path, dst_path: Path) -> None:
    """Ensure ``mkstemp`` (0600) preserves existing mode or respects umask on macOS/Linux."""
    if _IS_WINDOWS:
        return
    try:
        if dst_path.exists():
            mode = dst_path.stat().st_mode & 0o777
        else:
            umask = os.umask(0o022)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp_path, mode)
    except OSError:
        pass


def write_text_atomic(path: Path, text: str, *, newline: str | None = None) -> None:
    """Write text atomically (random sibling temp + fsync + POSIX mode + replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _preserve_or_default_posix_mode(tmp_path, path)
        _atomic_replace_with_retry(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write raw bytes atomically (random sibling temp + fsync + POSIX mode + replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _preserve_or_default_posix_mode(tmp_path, path)
        _atomic_replace_with_retry(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_text_cas(
    path: Path,
    text: str,
    *,
    expected_sha256: str | None = None,
    newline: str | None = None,
) -> None:
    """Atomically write *text* only if *path*'s current SHA-256 matches *expected_sha256*."""
    path = Path(path)
    if expected_sha256 is not None and path.is_file():
        current_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if current_sha != expected_sha256:
            raise CASConflictError(
                f"Concurrent modification detected on {path.name}; refusing to overwrite user edits."
            )
    write_text_atomic(path, text, newline=newline)


def write_json_atomic(path: Path, data: Any) -> None:
    """Serialize *data* as JSON and write atomically with fsync."""
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    write_text_atomic(path, payload)


def write_json(path: Path, data: Any) -> None:
    """Write data as JSON atomically, creating parent directories as needed."""
    write_json_atomic(path, data)


def read_jsonl(path: Path, *, strict: bool = False) -> list[dict]:
    """Read newline-delimited JSON, isolating truncated crash lines unless *strict* is True."""
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    rows.append(parsed)
                elif strict:
                    raise ValueError(f"Expected JSON object on line {line_no} of {path}")
            except json.JSONDecodeError:
                if strict:
                    raise
                logger.warning("Skipping malformed JSONL line %d in %s", line_no, path)
    return rows
