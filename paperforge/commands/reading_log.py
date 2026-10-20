from __future__ import annotations

import argparse
import datetime
import json
import re
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.config import paperforge_paths
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import open_live_reader, get_connection, get_memory_db_path
from paperforge.memory.events import write_correction_note
from paperforge.memory.permanent import (
    append_correction,
    append_reading_note,
    load_record_authority,
    order_records,
    project_record,
    record_time,
    search_reading_records,
)

_HEADER_RE = re.compile(r"^## ([A-Z0-9]{8}) \u2014 .+ \d{4}$")
_TITLE_RE = re.compile(r"^\*\*Title:\*\* (.+)")
_SECTION_RE = re.compile(r"^### (.+)")
_HR_RE = re.compile(r"^-{3,}$")
_FIELD_RE = re.compile(r"^\*\*([^:]+):\*\*")

_LABEL_INFO = frozenset({"Info", "信息"})
_LABEL_USE = frozenset({"Use", "用途"})
_LABEL_NOTE = frozenset({"Note", "备注"})


def _strip_quotes(s: str) -> str:
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if len(s) >= 2 and s[0] == '\u201c' and s[-1] == '\u201d':
        return s[1:-1]
    return s


def _parse_reading_log(filepath: Path) -> dict:
    if not filepath.exists():
        return {"ok": False, "papers": [], "errors": [{"line": 0, "field": "file", "message": "File not found"}]}

    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines()

    papers: list[dict] = []
    errors: list[dict] = []

    current_paper: dict | None = None
    current_section: str | None = None
    current_fields: dict = {}
    active_field: str | None = None

    def _flush_section(ln: int = 0):
        nonlocal current_section, current_fields, active_field
        if current_paper is not None and current_section is not None:
            info_val = current_fields.get("info", "")
            use_val = current_fields.get("use", "")
            if not info_val:
                errors.append({"line": ln, "field": "entry.info", "message": f"Missing **Info:** in section '{current_section}'"})
            if not use_val:
                errors.append({"line": ln, "field": "entry.use", "message": f"Missing **Use:** in section '{current_section}'"})
            current_paper["sections"].append({
                "section_name": current_section,
                "info": info_val,
                "use": use_val,
                "note": current_fields.get("note", ""),
            })
        current_section = None
        current_fields = {}
        active_field = None

    def _flush_paper(ln: int = 0):
        nonlocal current_paper
        _flush_section(ln)
        if current_paper:
            papers.append(current_paper)
        current_paper = None

    for i, line in enumerate(lines):
        ln = i + 1
        stripped = line.strip()
        if not stripped:
            continue

        m = _HEADER_RE.match(stripped)
        if m:
            _flush_paper(ln)
            current_paper = {"paper_key": m.group(1), "title": "", "sections": []}
            continue

        m = _TITLE_RE.match(stripped)
        if m and current_paper is not None:
            current_paper["title"] = m.group(1)
            continue

        m = _SECTION_RE.match(stripped)
        if m:
            if current_paper is not None:
                _flush_section(ln)
                current_section = m.group(1)
            continue

        if current_paper is None or current_section is None:
            continue

        if _HR_RE.match(stripped):
            active_field = None
            continue

        fm = _FIELD_RE.match(stripped)
        if fm:
            label = fm.group(1)
            rest = stripped[fm.end():].strip()
            if label in _LABEL_INFO:
                active_field = "info"
                current_fields["info"] = _strip_quotes(rest)
                continue
            if label in _LABEL_USE:
                active_field = "use"
                current_fields["use"] = _strip_quotes(rest) if rest else ""
                continue
            if label in _LABEL_NOTE:
                active_field = "note"
                current_fields["note"] = _strip_quotes(rest) if rest else ""
                continue
            if label == "Title":
                active_field = None
                continue
            active_field = None
            continue

        if active_field:
            existing = current_fields.get(active_field, "")
            if existing:
                current_fields[active_field] = existing + "\n" + stripped
            else:
                current_fields[active_field] = stripped

    _flush_paper(len(lines) + 1)

    return {"ok": len(errors) == 0, "papers": papers, "errors": errors}


def validate_reading_log(filepath: Path) -> dict:
    """Parse a reading-log.md with strict format rules and return validation result."""
    parsed = _parse_reading_log(filepath)
    return {
        "ok": parsed["ok"],
        "file": str(filepath),
        "errors": parsed["errors"],
        "papers_found": len(parsed["papers"]),
        "entries_found": sum(len(p["sections"]) for p in parsed["papers"]),
    }


def import_reading_log(vault: Path, filepath: Path) -> dict:
    """Validate and import a reading-log.md into reading-log.jsonl source of truth."""
    parsed = _parse_reading_log(filepath)
    if not parsed["ok"]:
        return {"ok": False, "errors": parsed["errors"], "papers_imported": 0, "entries_imported": 0}

    papers_set: set[str] = set()
    entries_imported = 0
    errors: list[dict] = []

    for paper in parsed["papers"]:
        for section in paper["sections"]:
            info = section.get("info", "")
            use = section.get("use", "")
            if info and use:
                res = append_reading_note(
                    vault,
                    paper["paper_key"],
                    section["section_name"],
                    excerpt=info,
                    usage=use,
                    note=section.get("note", "") or "",
                )
                if res.get("ok"):
                    entries_imported += 1
                    papers_set.add(paper["paper_key"])
                else:
                    errors.append({
                        "paper_key": paper["paper_key"],
                        "section": section["section_name"],
                        "error": res.get("error", "unknown"),
                    })

    return {
        "ok": len(errors) == 0,
        "papers_imported": len(papers_set),
        "entries_imported": entries_imported,
        "errors": errors,
    }


def lookup_paper_events(vault: Path, key: str) -> dict:
    """Look up all reading notes for a paper from JSONL."""
    notes, related = load_record_authority(vault)
    scoped = [row for row in notes if row["paper_id"] == key]
    order_records(scoped)

    title = ""
    db_path = get_memory_db_path(vault)
    if db_path.exists():
        with open_live_reader(vault, db_path) as conn:
            row = conn.execute(
                "SELECT title FROM papers WHERE zotero_key = ?", (key,),
            ).fetchone()
            if row:
                title = row["title"] or ""

    entries = [project_record(vault, n, related.get(n["id"], [])) for n in scoped]

    return {
        "ok": True,
        "zotero_key": key,
        "title": title,
        "entries": entries,
        "count": len(entries),
    }


def _export_from_jsonl(vault: Path, since: str = "", limit: int = 50) -> list[dict]:
    """Export reading notes from JSONL, enriched with paper metadata from DB."""
    notes, related = load_record_authority(vault)
    order_records(notes)

    if since:
        notes = [n for n in notes if n.get("created_at", "") >= since]
    notes = notes[:limit]

    db_path = get_memory_db_path(vault)
    paper_meta: dict[str, dict] = {}
    if db_path.exists():
        paper_ids = list(set(n.get("paper_id", "") for n in notes if n.get("paper_id")))
        if paper_ids:
            with open_live_reader(vault, db_path) as conn:
                placeholders = ",".join("?" * len(paper_ids))
                rows = conn.execute(
                    f"SELECT zotero_key, citation_key, title, year, first_author "
                    f"FROM papers WHERE zotero_key IN ({placeholders})",
                    paper_ids,
                ).fetchall()
                for row in rows:
                    paper_meta[row["zotero_key"]] = {
                        "citation_key": row["citation_key"],
                        "title": row["title"],
                        "year": row["year"],
                        "first_author": row["first_author"],
                    }

    results = []
    for n in notes:
        projected = project_record(vault, n, related.get(n["id"], []))
        pid = projected["paper_id"]
        meta = paper_meta.get(pid, {})
        results.append({
            **projected,
            "citation_key": meta.get("citation_key", pid),
            "title": meta.get("title", ""),
            "year": meta.get("year", ""),
            "first_author": meta.get("first_author", ""),
        })

    return results


def _render_reading_log_md(vault: Path, project: str = "") -> None:
    """Render reading-log.md from JSONL source of truth.

    Groups notes by paper_id and writes a formatted markdown file.
    If project is specified, writes to <resources>/Projects/<project>/reading-log.md.
    Otherwise writes to <paperforge>/logs/rendered/reading-log.md.
    """
    paths = paperforge_paths(vault)
    notes, related = load_record_authority(vault)
    projected = [project_record(vault, n, related.get(n["id"], [])) for n in notes]

    if not projected:
        print("No reading notes to render.")
        return

    if project:
        projected = [n for n in projected if n.get("project") == project]

    if not projected:
        print(f"No reading notes found{' for project ' + project if project else ''}.")
        return

    grouped: dict[str, list[dict]] = {}
    for n in projected:
        pid = n.get("paper_id", "unknown")
        grouped.setdefault(pid, []).append(n)

    lines: list[str] = []
    heading = f"Reading Log \u2014 {project}" if project else "Reading Log \u2014 All Projects"
    lines.append(f"# {heading}\n")
    lines.append(f"*Generated: {datetime.date.today().isoformat()} | Total entries: {len(projected)}*\n")

    for pid, entries in sorted(grouped.items()):
        lines.append(f"## {pid}\n")
        for entry in sorted(entries, key=lambda e: (e.get("section", ""), record_time(e), e.get("id", ""))):
            section = entry.get("section", "Untitled")
            lines.append(f"### {section}")
            lines.append(f"> {entry.get('excerpt', '')}")
            if entry.get("context"):
                lines.append(">")
                lines.append(f"> {entry.get('context')}")
            lines.append("")
            if entry.get("usage"):
                lines.append(f"- **Usage:** {entry.get('usage')}")
            if entry.get("note"):
                lines.append(f"- **Note:** {entry.get('note')}")
            tag_list = entry.get("tags", [])
            if tag_list:
                lines.append(f"- **Tags:** {', '.join(tag_list)}")
            provenance = entry.get("provenance", {})
            lines.append(
                f"- **Status:** {entry.get('record_status', 'active')} "
                f"(verification: {provenance.get('status', 'unknown')}/{provenance.get('basis', 'none')})")
            if entry.get("corrections"):
                lines.append(f"- **Corrections:** {len(entry['corrections'])} (see correction history)")
            lines.append("")
        lines.append("---\n")

    if project:
        output_dir = paths["resources"] / "Projects" / project
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "reading-log.md"
    else:
        output_dir = paths["paperforge"] / "logs" / "rendered"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "reading-log.md"

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rendered {len(projected)} entries to {output_path}")


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

    if getattr(args, "source_check", None) is not None:
        try:
            notes, related = load_record_authority(vault)
            row = next((row for row in notes if row["id"] == args.source_check), None)
            if row is None or (args.paper and row["paper_id"] != args.paper):
                raise ValueError("Record not found in this paper")
            projected = project_record(vault, row, related.get(row["id"], []))
            provenance = projected["provenance"]
            if provenance["status"] not in ("recorded", "confirmed", "matched"):
                raise ValueError(f"Source requires recheck: {provenance}")
            data = {**(row.get("source") or {}), "provenance": provenance}
            result = PFResult(ok=True, command="reading-log", version=PF_VERSION, data=data)
        except (ValueError, OSError, UnicodeError) as exc:
            result = PFResult(ok=False, command="reading-log", version=PF_VERSION,
                              error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)))
        print(result.to_json() if args.json else result.data if result.ok else result.error.message)
        return 0 if result.ok else 1

    if getattr(args, "search", None) is not None:
        try:
            data = search_reading_records(
                vault, args.search, limit=args.limit if args.limit is not None else 20,
                paper_id=args.paper, include_history=args.include_history,
            )
            result = PFResult(ok=True, command="reading-log", version=PF_VERSION, data=data)
        except (ValueError, OSError, UnicodeError) as exc:
            result = PFResult(
                ok=False, command="reading-log", version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
            )
        print(result.to_json() if args.json else result.data if result.ok else result.error.message)
        return 0 if result.ok else 1

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
        try:
            data = lookup_paper_events(vault, args.lookup)
        except (ValueError, OSError, UnicodeError) as exc:
            result = PFResult(
                ok=False, command="reading-log", version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
            )
            print(result.to_json() if args.json else result.error.message)
            return 1
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

    if args.render:
        try:
            _render_reading_log_md(vault, args.project or "")
        except (ValueError, OSError, UnicodeError) as exc:
            result = PFResult(
                ok=False, command="reading-log", version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
            )
            print(result.to_json() if args.json else result.error.message)
            return 1
        return 0

    if args.correct_id:
        if not args.correction:
            result = PFResult(
                ok=False, command="reading-log", version=PF_VERSION,
                data={},
                error=PFError(code=ErrorCode.VALIDATION_ERROR,
                              message="--correction is required with --correct"),
            )
            if args.json:
                print(result.to_json())
            else:
                print("Error: --correction is required with --correct")
            return 1

        try:
            notes, _related = load_record_authority(vault)
        except (ValueError, OSError, UnicodeError) as exc:
            result = PFResult(
                ok=False, command="reading-log", version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
            )
            print(result.to_json() if args.json else result.error.message)
            return 1
        original = next((n for n in notes if n.get("id") == args.correct_id), None)
        paper_id = original.get("paper_id", "") if original else ""
        if not paper_id:
            result = PFResult(
                ok=False, command="reading-log", version=PF_VERSION,
                data={},
                error=PFError(code=ErrorCode.VALIDATION_ERROR,
                              message=f"Original entry {args.correct_id} not found in JSONL"),
            )
            if args.json:
                print(result.to_json())
            else:
                print(f"Error: Original entry {args.correct_id} not found in reading-log.jsonl")
            return 1

        # Write to JSONL (source of truth)
        jsonl_result = append_correction(
            vault, getattr(args, "paper", None) or paper_id, args.correct_id,
            args.correction, args.reason or "",
        )

        # Also write to paper_events for FTS (best effort).  A writer-lock
        # timeout (shadow rebuild in progress) is transient — report the
        # JSONL write as success with db_indexed=False instead of failing
        # the whole command.
        db_ok = False
        if jsonl_result.get("ok"):
            try:
                db_ok = write_correction_note(
                    vault, paper_id, args.correct_id,
                    args.correction, args.reason or "",
                )
            except Exception:
                db_ok = False

        ok = bool(jsonl_result.get("ok"))
        code = (ErrorCode.INTERNAL_ERROR if jsonl_result.get("error_kind") == "io"
                else ErrorCode.VALIDATION_ERROR)
        result = PFResult(
            ok=ok,
            command="reading-log",
            version=PF_VERSION,
            data={
                "written": ok,
                "jsonl_id": jsonl_result.get("id", ""),
                "db_indexed": db_ok,
            },
            error=PFError(code=code,
                          message=jsonl_result.get("error", "Correction write failed")) if not ok else None,
        )
        if args.json:
            print(result.to_json())
        else:
            if ok:
                print(f"Correction written ({jsonl_result.get('id', '')})."
                      f"{' DB indexed.' if db_ok else ''}")
            else:
                print("Failed.")
        return 0 if ok else 1

    if args.paper_id and args.excerpt:
        tags_list = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None

        try:
            source = json.loads(args.source_json) if getattr(args, "source_json", None) is not None else None
            jsonl_result = append_reading_note(
                vault, args.paper_id, args.section or "",
                args.excerpt, args.usage or "", args.context or "",
                args.note or "", args.project or "", tags_list, source=source,
            )
        except (ValueError, OSError, UnicodeError) as exc:
            jsonl_result = {"ok": False, "error": str(exc)}

        ok = jsonl_result.get("ok", False)
        code = (ErrorCode.INTERNAL_ERROR if jsonl_result.get("error_kind") == "io"
                else ErrorCode.VALIDATION_ERROR)
        result = PFResult(
            ok=ok,
            command="reading-log",
            version=PF_VERSION,
            data={**jsonl_result, "written": ok},
            error=PFError(code=code,
                          message=jsonl_result.get("error", "Failed to write")) if not ok else None,
        )
        if args.json:
            print(result.to_json())
        else:
            if ok:
                print(f"Written. ID: {jsonl_result.get('id', 'unknown')}")
            else:
                print(f"Failed: {jsonl_result.get('error', 'unknown')}")

        if ok and args.project:
            _render_reading_log_md(vault, args.project)

        return 0 if ok else 1

    try:
        notes = _export_from_jsonl(vault, since=args.since or "", limit=args.limit or 50)
    except (ValueError, OSError, UnicodeError) as exc:
        result = PFResult(
            ok=False, command="reading-log", version=PF_VERSION,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
        )
        print(result.to_json() if args.json else result.error.message)
        return 1
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
