from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.events import export_reading_log, write_reading_note


_HEADER_RE = re.compile(r"^## ([A-Z0-9]{8}) \u2014 .+ \d{4}$")
_TITLE_RE = re.compile(r"^\*\*Title:\*\* (.+)")
_SECTION_RE = re.compile(r"^### (.+)")
_INFO_RE = re.compile(r'^\*\*Info:\*\* ["\u201c](.+)["\u201d]$')
_USE_RE = re.compile(r"^\*\*Use:\*\* (.+)")
_NOTE_RE = re.compile(r"^\*\*Note:\*\* (.+)")


def validate_reading_log(filepath: Path) -> dict:
    """Parse a reading-log.md with strict format rules and return validation result."""
    errors: list[dict] = []
    papers_found = 0
    entries_found = 0

    if not filepath.exists():
        return {
            "ok": False,
            "file": str(filepath),
            "errors": [{"line": 0, "field": "file", "message": "File not found"}],
            "papers_found": 0,
            "entries_found": 0,
        }

    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()

    current_paper: str | None = None
    current_section: str | None = None
    has_info = False
    has_use = False

    def _check_section_end(ln: int) -> None:
        nonlocal has_info, has_use
        if current_section is not None:
            if not has_info:
                errors.append({
                    "line": ln, "field": "entry.info",
                    "message": f"Missing **Info:** in section '{current_section}'",
                })
            if not has_use:
                errors.append({
                    "line": ln, "field": "entry.use",
                    "message": f"Missing **Use:** in section '{current_section}'",
                })
        has_info = False
        has_use = False

    for i, line in enumerate(lines):
        ln = i + 1
        stripped = line.strip()
        if not stripped:
            continue

        m = _HEADER_RE.match(stripped)
        if m:
            _check_section_end(ln)
            current_paper = m.group(1)
            current_section = None
            papers_found += 1
            continue

        m = _TITLE_RE.match(stripped)
        if m:
            if current_paper is None:
                errors.append({
                    "line": ln, "field": "paper.title",
                    "message": "**Title:** without paper header",
                })
            continue

        m = _SECTION_RE.match(stripped)
        if m:
            if current_paper is None:
                errors.append({
                    "line": ln, "field": "section",
                    "message": "Section without paper header",
                })
                continue
            _check_section_end(ln)
            current_section = m.group(1)
            entries_found += 1
            continue

        if current_section:
            if _INFO_RE.match(stripped):
                has_info = True
                continue
            if _USE_RE.match(stripped):
                has_use = True
                continue
            if _NOTE_RE.match(stripped):
                continue

    _check_section_end(len(lines) + 1)

    return {
        "ok": len(errors) == 0,
        "file": str(filepath),
        "errors": errors,
        "papers_found": papers_found,
        "entries_found": entries_found,
    }


def import_reading_log(vault: Path, filepath: Path) -> dict:
    """Validate and import a reading-log.md into paper_events."""
    validation = validate_reading_log(filepath)
    if not validation["ok"]:
        return {
            "ok": False,
            "errors": validation["errors"],
            "papers_imported": 0,
            "entries_imported": 0,
        }

    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()

    papers_set: set[str] = set()
    entries_imported = 0
    current_paper: str | None = None
    current_section: str | None = None
    current_excerpt: str | None = None
    current_usage: str | None = None
    current_note: str | None = None

    def _flush_entry() -> None:
        nonlocal papers_set, entries_imported
        nonlocal current_excerpt, current_usage, current_note
        if current_paper and current_section and current_excerpt and current_usage:
            write_reading_note(
                vault, current_paper, current_section,
                current_excerpt, current_usage, current_note or "",
            )
            entries_imported += 1
            papers_set.add(current_paper)
        current_excerpt = None
        current_usage = None
        current_note = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = _HEADER_RE.match(stripped)
        if m:
            _flush_entry()
            current_paper = m.group(1)
            current_section = None
            continue

        m = _SECTION_RE.match(stripped)
        if m:
            _flush_entry()
            current_section = m.group(1)
            continue

        if current_section:
            m = _INFO_RE.match(stripped)
            if m:
                current_excerpt = m.group(1)
                continue
            m = _USE_RE.match(stripped)
            if m:
                current_usage = m.group(1)
                continue
            m = _NOTE_RE.match(stripped)
            if m:
                current_note = m.group(1)
                continue

    _flush_entry()

    return {
        "ok": True,
        "papers_imported": len(papers_set),
        "entries_imported": entries_imported,
    }


def lookup_paper_events(vault: Path, key: str) -> dict:
    """Query paper_events for all reading_note events for a paper, joined with papers table."""
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return {"ok": False, "zotero_key": key, "title": "", "entries": [], "count": 0}

    conn = get_connection(db_path, read_only=True)
    try:
        rows = conn.execute(
            """SELECT e.created_at, e.payload_json, p.title, p.citation_key, p.year
               FROM paper_events e JOIN papers p ON p.zotero_key = e.paper_id
               WHERE e.paper_id = ? AND e.event_type = 'reading_note'
               ORDER BY e.created_at DESC""", (key,),
        ).fetchall()

        title = rows[0]["title"] if rows else ""
        entries = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            entries.append({
                "created_at": row["created_at"],
                "section": payload.get("section", ""),
                "excerpt": payload.get("excerpt", ""),
                "usage": payload.get("usage", ""),
                "note": payload.get("note", ""),
            })

        return {
            "ok": True,
            "zotero_key": key,
            "title": title,
            "entries": entries,
            "count": len(entries),
        }
    finally:
        conn.close()


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

    if args.validate:
        data = validate_reading_log(Path(args.validate))
        result = PFResult(
            ok=data["ok"], command="reading-log", version=PF_VERSION, data=data,
        )
        if args.json:
            print(result.to_json())
        else:
            if data["ok"]:
                print(f"Valid. {data['papers_found']} papers, {data['entries_found']} entries.")
            else:
                print(f"{len(data['errors'])} error(s):")
                for e in data["errors"]:
                    print(f"  line {e['line']}: [{e['field']}] {e['message']}")
        return 0 if data["ok"] else 1

    if args.import_file:
        data = import_reading_log(vault, Path(args.import_file))
        result = PFResult(
            ok=data.get("ok", True), command="reading-log", version=PF_VERSION, data=data,
        )
        if args.json:
            print(result.to_json())
        else:
            if data["ok"]:
                print(f"Imported {data['entries_imported']} entries from {data['papers_imported']} papers.")
            else:
                print(f"Validation failed with {len(data.get('errors', []))} error(s).")
        return 0 if data["ok"] else 1

    if args.lookup:
        data = lookup_paper_events(vault, args.lookup)
        result = PFResult(
            ok=data["ok"], command="reading-log", version=PF_VERSION, data=data,
        )
        if args.json:
            print(result.to_json())
        else:
            if data["ok"]:
                print(f"Paper: {data['title']} ({data['zotero_key']})")
                print(f"  {data['count']} reading notes:")
                for e in data["entries"]:
                    print(f"  [{e['created_at']}] {e['section']}: \"{e['excerpt']}\"")
                    if e["usage"]:
                        print(f"    -> Usage: {e['usage']}")
                    if e["note"]:
                        print(f"    -> Note: {e['note']}")
            else:
                print(f"No entries found for key: {args.lookup}")
        return 0

    if args.paper_id and args.excerpt:
        ok = write_reading_note(
            vault, args.paper_id, args.section or "",
            args.excerpt, args.usage or "", args.note or "",
        )
        result = PFResult(
            ok=ok,
            command="reading-log",
            version=PF_VERSION,
            data={"written": ok},
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message="Failed to write") if not ok else None,
        )
        if args.json:
            print(result.to_json())
        else:
            print("Written." if ok else "Failed.")
        return 0 if ok else 1

    notes = export_reading_log(vault, since=args.since or "", limit=args.limit or 50)
    result = PFResult(
        ok=True,
        command="reading-log",
        version=PF_VERSION,
        data={"notes": notes, "count": len(notes)},
    )

    if args.json:
        print(result.to_json())
    elif args.output:
        lines = []
        last_date = None
        for n in notes:
            date_str = n["created_at"][:10]
            if date_str != last_date:
                last_date = date_str
                lines.append(f"\n## {date_str}")
            author = (n["first_author"] or "").split()[-1] if n["first_author"] else ""
            lines.append(f"\n### {n['citation_key']} \u2014 {author} et al. {n['year']}")
            lines.append(f"- **{n['section']}**\uff1a\"{n['excerpt']}\"")
            if n["usage"]:
                lines.append(f"  \u2192 \u7528\u9014: {n['usage']}")
            if n["note"]:
                lines.append(f"  \u2192 \u5907\u6ce8: {n['note']}")
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        print(f"Exported {len(notes)} notes to {args.output}")
    else:
        print(f"{len(notes)} reading notes.")
    return 0
