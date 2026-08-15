"""Trash / quarantine — the ONLY way PaperForge deletes user data.

2026-08-14 incident: ``shutil.rmtree(Path())`` with ``ignore_errors=True``
recursively deleted the production vault root.  This module is the
fail-closed replacement:

- Deleting means MOVING into ``.paperforge/trash/<timestamp>/<uuid>/`` and
  writing a manifest — never a raw recursive delete.  A wrong move is
  recoverable; a wrong rmtree is data loss.
- ``trash_remove()`` refuses empty paths, ``.``/``..``, non-existent
  targets, the allowed root itself, and anything that resolves OUTSIDE the
  allowed root (junctions/symlinks are resolved first).
- Purge (the only true delete) is restricted to paths strictly inside the
  trash root and requires an explicit ``purge`` call.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRASH_DIRNAME = "trash"
MANIFEST_NAME = "manifest.json"


class DangerousPathError(ValueError):
    """A delete/move target failed the fail-closed capability check."""


def trash_root(vault: Path) -> Path:
    return Path(vault) / ".paperforge" / TRASH_DIRNAME


def _utcnow_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_target(target: Path | None, *, allowed_root: Path) -> Path:
    """Fail-closed capability check.  Returns the RESOLVED target.

    Refuses (raises DangerousPathError):
    - None / empty string / "." / ".."
    - a non-existent path (nothing to trash — callers should skip)
    - the allowed root itself or anything resolving outside it
      (junctions/symlinks are resolved before the containment check)
    """
    if target is None:
        raise DangerousPathError("target must not be None")
    raw = str(target).strip()
    if not raw or raw in (".", ".."):
        raise DangerousPathError(f"empty/current-directory path forbidden: {raw!r}")
    path = Path(raw)
    if not path.exists():
        raise DangerousPathError(f"target does not exist: {path}")
    resolved = path.resolve()
    root = Path(allowed_root).resolve()
    forbidden = {root, root.parent, Path(root.anchor)}
    if resolved in forbidden:
        raise DangerousPathError(f"refusing dangerous target: {resolved}")
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise DangerousPathError(f"target escapes allowed root {root}: {resolved}") from exc
    return resolved


def trash_remove(
    target: Path | None,
    *,
    vault: Path,
    allowed_root: Path,
    operation: str,
    paper_key: str = "",
) -> dict[str, Any] | None:
    """Move *target* into the trash (never delete) and record a manifest.

    Returns the trash record dict (with ``trash_id``) or None when the
    target does not exist.  Raises DangerousPathError when the target
    fails the capability check.  Never uses ignore_errors — a failed move
    raises (the data stays in place, which is the safe failure mode).
    """
    try:
        resolved = validate_target(target, allowed_root=allowed_root)
    except DangerousPathError as exc:
        if str(exc).startswith("target does not exist"):
            return None
        raise

    record_id = uuid.uuid4().hex[:12]
    stamp = _utcnow_z()
    dest_root = trash_root(vault) / stamp / record_id
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / resolved.name

    # Move (not copy+delete, not rmtree).  On failure the data remains at
    # the source — the safe failure mode.
    shutil.move(str(resolved), str(dest))

    manifest = {
        "trash_id": record_id,
        "operation": operation,
        "paper_key": paper_key,
        "original_path": str(resolved),
        "trash_path": str(dest),
        "timestamp": stamp,
        "trashed_at": _utcnow_z(),
    }
    (dest_root / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("trashed %s -> %s (%s)", resolved, dest, operation)
    return manifest


def list_trash(vault: Path) -> list[dict[str, Any]]:
    """Read every trash manifest, newest first."""
    root = trash_root(vault)
    if not root.exists():
        return []
    records: list[dict[str, Any]] = []
    for stamp_dir in sorted(root.iterdir(), reverse=True):
        if not stamp_dir.is_dir():
            continue
        for entry in sorted(stamp_dir.iterdir(), reverse=True):
            manifest = entry / MANIFEST_NAME
            if not manifest.exists():
                continue
            try:
                records.append(json.loads(manifest.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 — corrupt manifest skipped
                logger.warning("trash: unreadable manifest %s", manifest)
    return records


def restore_trash(vault: Path, trash_id: str) -> Path:
    """Move a trashed item back to its original path."""
    for record in list_trash(vault):
        if record.get("trash_id") != trash_id:
            continue
        original = Path(record["original_path"])
        trashed = Path(record["trash_path"])
        if not trashed.exists():
            raise FileNotFoundError(f"trashed item gone: {trashed}")
        if original.exists():
            raise FileExistsError(f"original path already exists: {original}")
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trashed), str(original))
        return original
    raise KeyError(f"no trash record with id {trash_id}")


def purge_trash(vault: Path, *, older_than_days: int | None = None) -> int:
    """The ONLY true delete.  Restricted to paths strictly inside the
    trash root; anything else is refused (fail-closed)."""
    root = trash_root(vault)
    if not root.exists():
        return 0
    root_resolved = root.resolve()
    purged = 0
    for stamp_dir in sorted(root.iterdir()):
        if not stamp_dir.is_dir():
            continue
        if older_than_days is not None:
            try:
                stamp = datetime.strptime(stamp_dir.name, "%Y%m%dT%H%M%SZ")
                age_days = (datetime.now(timezone.utc) - stamp).total_seconds() / 86400
                if age_days < older_than_days:
                    continue
            except ValueError:
                pass  # unparseable stamp dir → purge anyway (it is inside trash)
        try:
            resolved = stamp_dir.resolve()
            if resolved == root_resolved or root_resolved not in resolved.parents:
                logger.warning("trash purge: refusing %s (outside trash root)", resolved)
                continue
            shutil.rmtree(resolved)
            purged += 1
        except OSError as exc:
            logger.warning("trash purge: failed to remove %s: %s", stamp_dir, exc)
    return purged
