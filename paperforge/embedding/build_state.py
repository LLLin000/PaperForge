from __future__ import annotations

import json
from pathlib import Path


def get_vector_build_state_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    index_dir = (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent
    return index_dir / "vector-build-state.json"


def read_vector_build_state(vault: Path) -> dict:
    path = get_vector_build_state_path(vault)
    if not path.exists():
        return {
            "status": "idle",
            "current": 0,
            "total": 0,
            "paper_id": "",
            "last_update": "",
            "started_at": "",
            "finished_at": "",
            "resume_supported": True,
            "mode": "api",
            "model": "text-embedding-3-small",
            "message": "",
            "pid": 0,
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "idle", "current": 0, "total": 0, "paper_id": ""}


def write_vector_build_state(vault: Path, state: dict) -> None:
    path = get_vector_build_state_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        tmp.replace(path)
    except OSError:
        # Windows: target file may be locked (e.g., Obsidian plugin reading it).
        # Fall back to direct write — atomicity is secondary to avoiding crash.
        path.write_text(tmp.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            tmp.unlink()
        except OSError:
            pass

def mark_vector_build_state(vault: Path, **fields) -> dict:
    state = read_vector_build_state(vault)
    state.update(fields)
    write_vector_build_state(vault, state)
    return state
