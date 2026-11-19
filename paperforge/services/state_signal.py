"""Lightweight monotonic state-sequence signal for Obsidian live reactivity.

Writes a tiny atomic JSON counter to ``<paperforge_dir>/indexes/.state-seq.json``
whenever backend state (index, memory, annotations, living memory cards, or note
flags) changes. The Obsidian plugin watches this single file via ``fs.watch``
instead of polling or rewriting dozens of Markdown YAML frontmatters.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_seq_file(seq_path: Path) -> dict[str, Any]:
    default = {"seq": 0, "updated_at": "", "reason": "", "changed_keys": []}
    if not seq_path.exists():
        return default
    try:
        raw = json.loads(seq_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {
                "seq": int(raw.get("seq") or 0),
                "updated_at": str(raw.get("updated_at") or ""),
                "reason": str(raw.get("reason") or ""),
                "changed_keys": list(raw.get("changed_keys") or []),
            }
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return default


def _indexes_dir_for_vault(vault: Path) -> Path | None:
    vault_root = Path(vault).expanduser().resolve()
    try:
        from paperforge.config import paperforge_paths

        return paperforge_paths(vault_root)["paperforge"] / "indexes"
    except Exception:
        for cand in (
            vault_root / ".paperforge" / "indexes",
            vault_root / "System" / "PaperForge" / "indexes",
        ):
            if cand.exists():
                return cand
    return None


def bump_state_seq_in_dir(
    indexes_dir: Path,
    *,
    reason: str = "",
    changed_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Atomically increment ``indexes_dir/.state-seq.json``."""
    indexes_dir = Path(indexes_dir)
    if indexes_dir.name != "indexes":
        return {"seq": 0, "updated_at": "", "reason": "", "changed_keys": []}
    indexes_dir.mkdir(parents=True, exist_ok=True)
    seq_path = indexes_dir / ".state-seq.json"
    lock_path = indexes_dir / ".state-seq.json.lock"
    dedup_keys: list[str] = []
    for k in changed_keys or []:
        ks = str(k).strip()
        if ks and ks not in dedup_keys:
            dedup_keys.append(ks)
    with FileLock(str(lock_path), timeout=10.0):
        prev = _read_seq_file(seq_path)
        payload = {
            "seq": int(prev["seq"]) + 1,
            "updated_at": _utcnow_iso(),
            "reason": str(reason or "").strip(),
            "changed_keys": dedup_keys[:50],
        }
        fd, tmp_name = tempfile.mkstemp(prefix=".state-seq-", suffix=".tmp", dir=indexes_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, seq_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise
    return payload


def bump_state_seq(
    vault: Path,
    *,
    reason: str = "",
    changed_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Increment the vault's ``.state-seq.json`` signal when an indexes dir resolves."""
    idx_dir = _indexes_dir_for_vault(vault)
    if idx_dir is None:
        return {"seq": 0, "updated_at": "", "reason": "", "changed_keys": []}
    return bump_state_seq_in_dir(idx_dir, reason=reason, changed_keys=changed_keys)


def read_state_seq(vault: Path) -> dict[str, Any]:
    """Read the current state sequence counter for *vault*."""
    idx_dir = _indexes_dir_for_vault(vault)
    if idx_dir is None:
        return {"seq": 0, "updated_at": "", "reason": "", "changed_keys": []}
    return _read_seq_file(idx_dir / ".state-seq.json")
