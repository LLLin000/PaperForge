from __future__ import annotations

import json
import datetime
import logging
import secrets
from pathlib import Path

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)


def _logs_dir(vault: Path) -> Path:
    paths = paperforge_paths(vault)
    return paths["paperforge"] / "logs"


def _ensure_logs_dir(vault: Path) -> Path:
    log_dir = _logs_dir(vault)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# ── Reading Log ────────────────────────────────────────────────────────────


def get_reading_log_path(vault: Path) -> Path:
    return _logs_dir(vault) / "reading-log.jsonl"


def append_reading_note(
    vault: Path,
    paper_id: str,
    section: str,
    excerpt: str,
    usage: str = "",
    context: str = "",
    note: str = "",
    project: str = "",
    tags: list[str] | None = None,
    agent: str = "",
) -> dict:
    if not paper_id:
        return {"ok": False, "error": "paper_id is required"}
    if not excerpt:
        return {"ok": False, "error": "excerpt is required"}

    date_str = datetime.date.today().strftime("%Y%m%d")
    entry_id = f"rln_{date_str}_{secrets.token_hex(4)}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entry: dict[str, object] = {
        "id": entry_id,
        "created_at": now,
        "paper_id": paper_id,
        "section": section,
        "excerpt": excerpt,
        "usage": usage,
        "context": context,
        "note": note,
        "project": project,
        "tags": tags or [],
        "agent": agent,
        "verified": False,
    }

    log_dir = _ensure_logs_dir(vault)
    filepath = log_dir / "reading-log.jsonl"

    try:
        with filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "id": entry_id, "path": str(filepath)}


def _read_jsonl(filepath: Path) -> list[dict]:
    if not filepath.exists():
        return []
    entries: list[dict] = []
    with filepath.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entries.append(json.loads(stripped))
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping malformed JSON line %d in %s", line_no, filepath
                )
    return entries


def read_all_reading_notes(vault: Path) -> list[dict]:
    filepath = get_reading_log_path(vault)
    return _read_jsonl(filepath)


def get_reading_notes_for_paper(vault: Path, paper_id: str) -> list[dict]:
    all_notes = read_all_reading_notes(vault)
    return [n for n in all_notes if n.get("paper_id") == paper_id]


# ── Project Log ────────────────────────────────────────────────────────────


def get_project_log_path(vault: Path) -> Path:
    return _logs_dir(vault) / "project-log.jsonl"


def append_project_entry(vault: Path, entry: dict) -> dict:
    date_str = datetime.date.today().strftime("%Y%m%d")
    entry_id = f"plog_{date_str}_{secrets.token_hex(4)}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record: dict[str, object] = {
        "id": entry_id,
        "created_at": now,
        "project": entry.get("project", ""),
        "date": entry.get("date", ""),
        "type": entry.get("type", ""),
        "title": entry.get("title", ""),
        "decisions": entry.get("decisions", []),
        "detours": entry.get("detours", []),
        "reusable": entry.get("reusable", []),
        "todos": entry.get("todos", []),
        "related_papers": entry.get("related_papers", []),
        "tags": entry.get("tags", []),
        "agent": entry.get("agent", ""),
    }

    log_dir = _ensure_logs_dir(vault)
    filepath = log_dir / "project-log.jsonl"

    try:
        with filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "id": entry_id, "path": str(filepath)}


def read_all_project_entries(vault: Path) -> list[dict]:
    filepath = get_project_log_path(vault)
    return _read_jsonl(filepath)


def get_project_entries(vault: Path, project: str) -> list[dict]:
    all_entries = read_all_project_entries(vault)
    return [e for e in all_entries if e.get("project") == project]
