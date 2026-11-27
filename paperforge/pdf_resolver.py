"""PDF path resolution for Zotero attachments.

Supports absolute, vault-relative, junction/symlink, and Zotero storage-relative paths.
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def first_pdf_in_storage_dir(storage_key: str, zotero_dir: Path | None) -> str:
    """First PDF inside a Zotero storage KEY directory, or ''."""
    if not storage_key or zotero_dir is None:
        return ""
    storage_dir = (zotero_dir / "storage" / storage_key).resolve()
    if not storage_dir.exists():
        return ""
    pdfs = sorted(f for f in storage_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf")
    return str(pdfs[0]) if pdfs else ""


_first_pdf_in_storage_dir = first_pdf_in_storage_dir


def _candidate_zotero_dirs(vault_root: Path, zotero_dir: Path | None) -> list[Path]:
    """Candidate Zotero roots including explicit zotero_dir and in-vault junctions."""
    candidates: list[Path] = []
    if zotero_dir is not None:
        candidates.append(zotero_dir)
    for sub in (".paperforge", "System"):
        cand = vault_root / sub / "Zotero"
        if cand not in candidates:
            candidates.append(cand)
    return candidates


def _resolve_base_attachment_dir(zotero_dir: Path | None) -> Path | None:
    try:
        from paperforge.adapters.zotero_sqlite import read_zotero_base_attachment_path

        return read_zotero_base_attachment_path(zotero_dir)
    except Exception:
        return None


def resolve_source_pdf(vault_root: Path, locator: str | None) -> Path | None:
    """Resolve a stored ``source_pdf`` locator to a readable PDF path.

    This is the one resolution both OCR entries (first parse and derived
    rebuild) use, so they read the same PDF evidence: absolute paths,
    ``[[vault]]`` wikilinks, vault-relative paths and ``storage:`` locators
    are all resolved through the configured Zotero data directory.
    """
    if not locator:
        return None
    vault_path = Path(vault_root)
    zotero_dir: Path | None = None
    try:
        from paperforge.config import paperforge_paths

        zotero_dir = paperforge_paths(vault_path).get("zotero_dir")
    except Exception:
        zotero_dir = None
    if zotero_dir is None:
        config_path = vault_path / "paperforge.json"
        if config_path.exists():
            try:
                import json

                config = json.loads(config_path.read_text(encoding="utf-8"))
                vault_cfg = config.get("vault_config") if isinstance(config.get("vault_config"), dict) else {}
                configured = (
                    config.get("zotero_data_dir")
                    or vault_cfg.get("zotero_data_dir")
                    or config.get("zotero_link")
                    or ""
                )
                if configured:
                    cfg_p = Path(configured).expanduser()
                    zotero_dir = cfg_p if cfg_p.is_absolute() else (vault_path / cfg_p)
            except (OSError, ValueError):
                zotero_dir = None
    resolved = resolve_pdf_path(str(locator), True, vault_path, zotero_dir)
    candidate = Path(resolved) if resolved else None
    if candidate is None:
        raw = str(locator).strip()
        if raw.startswith("[[") and raw.endswith("]]"):
            raw = raw[2:-2].strip()
        if raw.startswith("absolute:"):
            raw = raw[len("absolute:") :].strip()
        direct = Path(raw)
        if direct.exists():
            candidate = direct
    if candidate is None:
        return None
    try:
        import pymupdf

        with pymupdf.open(str(candidate)):
            pass
    except Exception:  # noqa: BLE001 — unreadable files are not PDF evidence
        return None
    return candidate


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

    # 2026-08-16: formal-library pdf_path may be a [[wikilink]] locator —
    # strip it so the vault-relative / storage branches below can resolve.
    if raw.startswith("[[") and raw.endswith("]]"):
        raw = raw[2:-2].strip()
    if raw.startswith("absolute:"):
        raw = raw[len("absolute:") :].strip()
    if not raw:
        return ""

    # Try linked-attachment base directory (`attachments:...`)
    if raw.startswith("attachments:"):
        att_rel = raw[len("attachments:") :].replace("\\", "/").lstrip("/")
        base_att_dir = _resolve_base_attachment_dir(zotero_dir)
        if base_att_dir is not None and att_rel:
            att_candidate = (base_att_dir / att_rel.replace("/", os.sep)).resolve()
            if is_valid_pdf(att_candidate):
                return str(att_candidate)
        logger.error(f"PDF path could not be resolved: {raw}")
        return ""

    # Try Zotero storage-relative (format: "storage:XXXX/item.pdf")
    if raw.startswith("storage:"):
        storage_rel = raw[len("storage:") :].replace("\\", "/").lstrip("/")
        storage_key = storage_rel.split("/")[0].strip() if "/" in storage_rel else ""
        for zcand in _candidate_zotero_dirs(vault_root, zotero_dir):
            if storage_rel:
                storage_candidate = (zcand / "storage" / storage_rel.replace("/", os.sep)).resolve()
                if is_valid_pdf(storage_candidate):
                    return str(storage_candidate)
            if storage_key:
                fallback = _first_pdf_in_storage_dir(storage_key, zcand)
                if fallback:
                    return fallback
        logger.error(f"PDF path could not be resolved: {raw}")
        return ""

    # Try absolute first
    candidate = Path(raw)
    if candidate.is_absolute():
        resolved = resolve_junction(candidate)
        if is_valid_pdf(resolved):
            return str(resolved)
        # absolute + exact-name miss → storage KEY dir fallback
        m = re.search(r"storage[/\\]([A-Za-z0-9]{8})", raw, re.IGNORECASE)
        if m:
            for zcand in _candidate_zotero_dirs(vault_root, zotero_dir):
                fallback = _first_pdf_in_storage_dir(m.group(1), zcand)
                if fallback:
                    return fallback

    # Try vault-relative
    vault_candidate = (vault_root / raw.replace("\\", "/").replace("/", os.sep)).resolve()
    if is_valid_pdf(vault_candidate):
        return str(vault_candidate)

    # Try junction resolution on vault-relative
    vault_resolved = resolve_junction(vault_candidate)
    if is_valid_pdf(vault_resolved):
        return str(vault_resolved)

    # vault-relative exact-name miss → the storage KEY directory may hold
    # the PDF under a renamed/restore-shuffled filename (the storage key is
    # the identity anchor, the filename is only a label).
    m = re.search(r"storage[/\\]([A-Za-z0-9]{8})", raw, re.IGNORECASE)
    if m:
        for zcand in _candidate_zotero_dirs(vault_root, zotero_dir):
            fallback = _first_pdf_in_storage_dir(m.group(1), zcand)
            if fallback:
                return fallback

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
