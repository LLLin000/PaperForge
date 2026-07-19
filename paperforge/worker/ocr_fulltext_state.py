from __future__ import annotations

import datetime as dt
import os
import re
import tempfile
from pathlib import Path
from typing import Literal

from paperforge.worker.ocr_artifacts import _sha256_hexdigest

_DRIFT = Literal["MATCHED", "DRIFTED", "UNKNOWN"]
_BACKUP_RE = re.compile(r"^fulltext\.pre-rebuild\.(\d{8}T\d{6}Z)(?:\.(\d{3}))?\.md$")


def compute_disk_fulltext_hash(path: Path) -> str:
    return _sha256_hexdigest(path.read_bytes())


def get_fulltext_drift_state(fulltext_path: Path, machine_hash: str | None) -> _DRIFT:
    if not machine_hash or not fulltext_path.exists():
        return "UNKNOWN"
    try:
        current = compute_disk_fulltext_hash(fulltext_path)
    except OSError:
        return "UNKNOWN"
    return "MATCHED" if current == machine_hash else "DRIFTED"


def create_pre_rebuild_backup(fulltext_path: Path, now_utc: dt.datetime) -> tuple[str, str] | None:
    if not fulltext_path.exists():
        return None
    backups_dir = fulltext_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_utc.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_bytes = fulltext_path.read_bytes()
    source_hash = _sha256_hexdigest(source_bytes)
    for seq in range(1000):
        suffix = "" if seq == 0 else f".{seq:03d}"
        name = f"fulltext.pre-rebuild.{stamp}{suffix}.md"
        candidate = backups_dir / name
        if candidate.exists():
            continue
        candidate.write_bytes(source_bytes)
        if compute_disk_fulltext_hash(candidate) != source_hash:
            raise IOError(f"Backup verification failed for {candidate}")
        return now_utc.astimezone(dt.timezone.utc).isoformat(), str(candidate.relative_to(fulltext_path.parent)).replace("\\", "/")
    raise RuntimeError("Backup sequence overflow for one UTC second")


def prune_pre_rebuild_backups(backups_dir: Path, keep: int = 5) -> list[Path]:
    if not backups_dir.exists():
        return []
    matches = sorted(
        (p for p in backups_dir.glob("fulltext.pre-rebuild.*.md") if _BACKUP_RE.match(p.name)),
        key=lambda p: p.name,
    )
    doomed = matches[:-keep] if len(matches) > keep else []
    for path in doomed:
        path.unlink(missing_ok=True)
    return doomed


def atomic_replace_text(target: Path, content: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(tmp_path, target)
        return target
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
