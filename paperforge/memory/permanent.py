from __future__ import annotations

import datetime
import json
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


RECORD_FIELDS = ("excerpt", "usage", "note", "context", "section")


def _error(message: str, kind: str = "validation") -> dict:
    return {"ok": False, "error": message, "error_kind": kind}

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
    source: dict | None = None,
) -> dict:
    if not paper_id:
        return _error("paper_id is required")
    if not excerpt:
        return _error("excerpt is required")

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
    if source is not None:
        from paperforge.memory.record_source import capture_source

        try:
            entry["source"] = capture_source(vault, paper_id, excerpt, source)
        except (ValueError, UnicodeError) as exc:
            return _error(str(exc))
        except OSError as exc:
            return _error(str(exc), "io")

    log_dir = _ensure_logs_dir(vault)
    filepath = log_dir / "reading-log.jsonl"

    try:
        with filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        return _error(str(e), "io")

    return {
        "ok": True, "id": entry_id, "path": str(filepath),
        "provenance": entry.get("source", {}).get("verification", {"status": "unknown", "basis": "none"}),
    }


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


# ── Correction Log ──────────────────────────────────────────────────────────


def get_correction_log_path(vault: Path) -> Path:
    return _logs_dir(vault) / "correction-log.jsonl"


def append_correction(
    vault: Path,
    paper_id: str,
    original_id: str,
    correction: str,
    reason: str = "",
    agent: str = "",
) -> dict:
    """Append a correction record to correction-log.jsonl."""
    if not paper_id:
        return _error("paper_id is required")
    if not original_id:
        return _error("original_id is required")
    if not correction:
        return _error("correction is required")
    try:
        originals = _read_records_strict(
            get_reading_log_path(vault), ("id", "paper_id", "created_at", "excerpt"),
        )
    except (ValueError, UnicodeError) as exc:
        return _error(str(exc))
    except OSError as exc:
        return _error(str(exc), "io")
    if not any(row["id"] == original_id and row["paper_id"] == paper_id for row in originals):
        return _error("Original record does not exist in this paper")

    date_str = datetime.date.today().strftime("%Y%m%d")
    entry_id = f"corr_{date_str}_{secrets.token_hex(4)}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entry: dict[str, object] = {
        "id": entry_id,
        "event_type": "correction",
        "created_at": now,
        "paper_id": paper_id,
        "original_id": original_id,
        "correction": correction,
        "reason": reason,
        "agent": agent,
    }

    log_dir = _ensure_logs_dir(vault)
    filepath = log_dir / "correction-log.jsonl"

    try:
        with filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        return _error(str(e), "io")

    return {"ok": True, "id": entry_id, "path": str(filepath)}


def read_all_corrections(vault: Path) -> list[dict]:
    """Read all correction entries from correction-log.jsonl."""
    filepath = get_correction_log_path(vault)
    return _read_jsonl(filepath)


def get_corrections_for_paper(vault: Path, paper_id: str) -> list[dict]:
    """Get all corrections for a specific paper."""
    all_corrections = read_all_corrections(vault)
    return [c for c in all_corrections if c.get("paper_id") == paper_id]


def record_time(row: dict) -> datetime.datetime:
    parsed = datetime.datetime.fromisoformat(row["created_at"])
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def order_records(rows: list[dict], *, reverse: bool = True) -> list[dict]:
    """Single instant-then-id ordering shared by search/lookup/export/context."""
    rows.sort(key=lambda row: row.get("id", ""))
    rows.sort(key=record_time, reverse=reverse)
    return rows


def _read_records_strict(filepath: Path, required: tuple[str, ...]) -> list[dict]:
    """Refuse incomplete authority reads rather than reporting false clean hits."""
    if not filepath.exists():
        return []
    rows = []
    identities = set()
    for number, line in enumerate(filepath.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Incomplete record read: {filepath.name} line {number}") from exc
        if not isinstance(row, dict) or any(
            not isinstance(row.get(field), str) or not row[field].strip() for field in required
        ):
            raise ValueError(f"Incomplete record: {filepath.name} line {number}")
        try:
            record_time(row)
        except ValueError as exc:
            raise ValueError(f"Invalid created_at: {filepath.name} line {number}") from exc
        if row["id"] in identities:
            raise ValueError(f"Duplicate record identity: {filepath.name} line {number}")
        identities.add(row["id"])
        rows.append(row)
    return rows

def load_record_authority(vault: Path) -> tuple[list[dict], dict[str, list[dict]]]:
    """Strict read of both JSONL authorities with cross-paper correction resolution."""
    notes = _read_records_strict(get_reading_log_path(vault), ("id", "paper_id", "created_at", "excerpt"))
    corrections = _read_records_strict(
        get_correction_log_path(vault), ("id", "paper_id", "created_at", "original_id", "correction"),
    )
    related: dict[str, list[dict]] = {}
    identities = {row["id"]: row["paper_id"] for row in notes}
    for correction in corrections:
        target = correction["original_id"]
        if identities.get(target) != correction["paper_id"]:
            raise ValueError("Correction history contains a missing or cross-paper target")
        related.setdefault(target, []).append(correction)
    return notes, related


def project_record(vault: Path, row: dict, history: list[dict]) -> dict:
    """Effective read of one record: legacy fields pass through, status is live."""
    from paperforge.memory.record_source import source_provenance
    values: dict[str, str] = {}
    for field in RECORD_FIELDS:
        value = row.get(field, "")
        if not isinstance(value, str):
            raise ValueError(f"Invalid {field} in record {row['id']}")
        values[field] = value
    history = sorted(history, key=lambda c: (record_time(c), c.get("id", "")))
    return {
        **row, **values,
        "verified": row.get("verified", False),
        "record_status": "corrected" if history else "active",
        "corrections": history,
        "provenance": source_provenance(vault, row["paper_id"], row["excerpt"], row.get("source")),
    }


def search_reading_records(
    vault: Path, query: str, *, limit: int = 20, paper_id: str | None = None,
    include_history: bool = False,
) -> dict:
    """All casefolded whitespace tokens must occur literally across record fields."""
    query = query.strip()
    tokens = query.casefold().split()
    if not tokens:
        raise ValueError("Search query must not be blank")
    if not 1 <= limit <= 100:
        raise ValueError("Search limit must be between 1 and 100")
    notes, related = load_record_authority(vault)
    matches = []
    for row in notes:
        if paper_id is not None and row["paper_id"] != paper_id:
            continue
        history = related.get(row["id"], [])
        if history and not include_history:
            continue
        projected = project_record(vault, row, history)
        lowered = {field: projected[field].casefold() for field in RECORD_FIELDS}
        if not all(any(token in value for value in lowered.values()) for token in tokens):
            continue
        projected["matched_fields"] = [
            field for field in RECORD_FIELDS if any(token in lowered[field] for token in tokens)]
        matches.append(projected)
    order_records(matches)
    matches = matches[:limit]
    return {
        "query": query, "matches": matches, "count": len(matches),
        "freshness": {"authority": "jsonl", "mode": "read_on_query"},
    }
