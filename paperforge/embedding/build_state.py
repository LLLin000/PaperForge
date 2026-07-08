from __future__ import annotations

import json
from pathlib import Path

def _default_state() -> dict:
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


def _fallback_state() -> dict:
    return {"status": "idle", "current": 0, "total": 0, "paper_id": ""}


def get_vector_build_state_path(vault: Path) -> Path:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    index_dir = (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent
    return index_dir / "vector-build-state.json"


def read_vector_build_state(vault: Path) -> dict:
    path = get_vector_build_state_path(vault)
    if not path.exists():
        return _default_state()
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except Exception:
        # Main file corrupt — try .tmp backup from failed atomic write
        tmp = path.with_suffix(".tmp")
        if tmp.exists():
            try:
                return json.loads(tmp.read_text(encoding="utf-8"))
            except Exception:
                pass
        return _fallback_state()


def write_vector_build_state(vault: Path, state: dict) -> None:
    path = get_vector_build_state_path(vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    content = json.dumps(state, ensure_ascii=False, indent=2)
    tmp.write_text(content, encoding="utf-8")
    try:
        tmp.replace(path)
    except OSError:
        # Windows: target file locked. Write directly; leave .tmp as backup.
        path.write_text(content, encoding="utf-8")

def mark_vector_build_state(vault: Path, **fields) -> dict:
    state = read_vector_build_state(vault)
    state.update(fields)
    write_vector_build_state(vault, state)
    return state
