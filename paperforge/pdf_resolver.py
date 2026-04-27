"""PDF path resolution for Zotero attachments.

Supports absolute, vault-relative, junction/symlink, and Zotero storage-relative paths.
"""

from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_pdf_path(
    pdf_path: str,
    has_pdf: bool,
    vault_root: Path,
    zotero_dir: Path | None = None,
) -> str:
    """Resolve a Zotero PDF path to an absolute, readable file path.

    Args:
        pdf_path: Raw path from Zotero attachment (may be absolute, relative,
            junction, or storage-relative).
        has_pdf: Whether Zotero reports a PDF attachment exists.
        vault_root: Absolute path to the Obsidian vault root.
        zotero_dir: Optional absolute path to the Zotero data directory for
            storage-relative resolution.

    Returns:
        Absolute path string if the PDF is readable, empty string otherwise.
    """
    if not has_pdf or not pdf_path:
        return ""

    raw = pdf_path.strip()
    if not raw:
        return ""

    # Try absolute first
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = resolve_junction(candidate)
        if is_valid_pdf(resolved):
            return str(resolved)
        return ""

    # Try vault-relative
    vault_candidate = (vault_root / raw.replace("/", os.sep)).resolve()
    if is_valid_pdf(vault_candidate):
        return str(vault_candidate)

    # Try junction resolution on vault-relative
    vault_resolved = resolve_junction(vault_candidate)
    if is_valid_pdf(vault_resolved):
        return str(vault_resolved)

    # Try Zotero storage-relative (format: "storage:XXXX/item.pdf")
    if raw.startswith("storage:") and zotero_dir is not None:
        storage_rel = raw[len("storage:") :].lstrip("/")
        storage_candidate = (zotero_dir / storage_rel.replace("/", os.sep)).resolve()
        if is_valid_pdf(storage_candidate):
            return str(storage_candidate)

    logger.error(f"PDF path could not be resolved: {raw}")
    return ""


def resolve_junction(path: Path) -> Path:
    """Resolve Windows junctions and symlinks to their target.

    Uses os.path.realpath as primary resolver. Falls back to ctypes-based
    reparse point resolution on Windows if realpath does not follow the junction.
    """
    if not path.exists():
        return path

    resolved = Path(os.path.realpath(path))
    if resolved != path and resolved.exists():
        return resolved

    # Windows-specific: resolve directory junction reparse points
    if os.name == "nt" and path.is_dir():
        try:
            kernel32 = ctypes.windll.kernel32
            buf = ctypes.create_unicode_buffer(1024)
            handle = kernel32.CreateFileW(str(path), 0, 0, None, 3, 0x02000000, None)
            if handle != -1:
                try:
                    res = kernel32.GetFinalPathNameByHandleW(handle, buf, 1024, 0)
                    if res > 0:
                        target = buf[:res]
                        if target.startswith("\\\\?\\"):
                            target = target[4:]
                        target_path = Path(target)
                        if target_path.exists():
                            return target_path
                finally:
                    kernel32.CloseHandle(handle)
        except Exception:
            pass

    return path


def is_valid_pdf(path: Path) -> bool:
    """Check if path points to an existing, non-empty, readable file."""
    try:
        return path.is_file() and path.stat().st_size > 0
    except (OSError, PermissionError):
        return False
