from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from paperforge.config import paperforge_paths


def _snapshot_dir(vault: Path) -> Path:
    paths = paperforge_paths(vault)
    d = paths["paperforge"] / "indexes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_memory_runtime(vault: Path, *, paper_count_db: int,
                         paper_count_index: int, fresh: bool,
                         needs_rebuild: bool, last_full_build_at: str,
                         schema_version_db: int, fts_ready: bool) -> None:
    snap = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_command": "paperforge memory status --json",
        "paper_count_db": paper_count_db,
        "paper_count_index": paper_count_index,
        "fresh": fresh,
        "needs_rebuild": needs_rebuild,
        "last_full_build_at": last_full_build_at,
        "schema_version_db": schema_version_db,
        "fts_ready": fts_ready,
    }
    path = _snapshot_dir(vault) / "memory-runtime-state.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def write_vector_runtime(vault: Path, *, enabled: bool, mode: str, model: str,
                         deps_installed: bool, deps_missing: list[str] | None,
                         py_version: str, db_exists: bool, chunk_count: int,
                         build_state: dict | None) -> None:
    snap = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_command": "paperforge embed status --json",
        "enabled": enabled,
        "mode": mode,
        "model": model,
        "deps_installed": deps_installed,
        "deps_missing": deps_missing or [],
        "py_version": py_version,
        "db_exists": db_exists,
        "chunk_count": chunk_count,
        "build_state": build_state or {},
    }
    path = _snapshot_dir(vault) / "vector-runtime-state.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")


def write_runtime_health(vault: Path, health_data: dict) -> None:
    path = _snapshot_dir(vault) / "runtime-health.json"
    path.write_text(json.dumps(health_data, ensure_ascii=False, indent=2), encoding="utf-8")
