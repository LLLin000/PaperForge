from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.config import paperforge_paths
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.permanent import (
    append_project_entry,
    get_project_entries,
    read_all_project_entries,
)


def _render_project_log_md(vault: Path, project: str) -> None:
    """Render project-log.md from JSONL."""
    entries = get_project_entries(vault, project)
    if not entries:
        return

    lines = [f"# Project Log — {project}", ""]
    lines.append("> Auto-generated from project-log.jsonl. Do not edit manually.")
    lines.append("")

    for entry in sorted(entries, key=lambda x: x.get("created_at", ""), reverse=True):
        lines.append(f"## {entry.get('date', '')} — {entry.get('title', '(untitled)')}")
        lines.append(f"**Type:** {entry.get('type', '')}")
        lines.append("")

        if entry.get("decisions"):
            lines.append("### Core Decisions")
            for d in entry["decisions"]:
                lines.append(f"- {d}")
            lines.append("")

        if entry.get("detours"):
            lines.append("### Detours & Corrections")
            for dt in entry["detours"]:
                if isinstance(dt, dict):
                    lines.append(f"- **Wrong:** {dt.get('wrong', '')}")
                    lines.append(f"  **Correction:** {dt.get('correction', '')}")
                    lines.append(f"  **Resolution:** {dt.get('resolution', '')}")
                else:
                    lines.append(f"- {dt}")
            lines.append("")

        if entry.get("reusable"):
            lines.append("### Reusable Methods")
            for r in entry["reusable"]:
                lines.append(f"- {r}")
            lines.append("")

        if entry.get("todos"):
            lines.append("### Todos")
            for t in entry["todos"]:
                done = "x" if t.get("done", False) else " "
                lines.append(f"- [{done}] {t.get('content', '')}")
            lines.append("")

        if entry.get("tags"):
            lines.append(f"**Tags:** {', '.join(entry['tags'])}")

        lines.append("---")
        lines.append("")

    paths = paperforge_paths(vault)
    resource_dir = paths.get("resources")
    if resource_dir:
        output_dir = resource_dir / "Projects" / project
    else:
        output_dir = vault / "Projects" / project
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "project-log.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _read_json_input(args: argparse.Namespace) -> dict:
    payload_str = str(getattr(args, "payload", "") or "").strip()
    input_arg = str(getattr(args, "input", "") or "").strip()
    if input_arg:
        raw = sys.stdin.read() if input_arg == "-" else Path(input_arg).read_text(encoding="utf-8-sig")
        parsed = json.loads(raw)
    elif payload_str:
        parsed = json.loads(payload_str)
    else:
        raise ValueError("--payload or --input <path|-> is required")
    if not isinstance(parsed, dict):
        raise ValueError("JSON payload must be an object")
    return parsed


def _write_methodology_card(vault: Path, payload: dict) -> dict:
    import datetime
    import re
    import secrets
    from paperforge.core.io import write_text_atomic
    from paperforge.services.state_signal import bump_state_seq

    title = str(payload.get("title") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not title:
        raise ValueError("methodology card requires non-empty 'title'")
    if not content:
        raise ValueError("methodology card requires non-empty 'content'")

    raw_id = str(payload.get("id") or "").strip().lower()
    if raw_id:
        slug = re.sub(r"[^a-z0-9_-]+", "-", raw_id).strip("-_")
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        slug = f"method-{datetime.date.today().strftime('%Y%m%d')}-{secrets.token_hex(3)}"

    use_when = str(payload.get("use_when") or payload.get("description") or "").strip()
    project = str(payload.get("project") or "").strip()
    tags = payload.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    paths = paperforge_paths(vault)
    archive_dir = Path(paths["paperforge"]) / "methodology" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    out_path = archive_dir / f"{slug}.md"

    lines = [
        "---",
        f"id: {slug}",
        f"tags: {json.dumps(list(tags), ensure_ascii=False)}",
        f"source_project: {project}",
        "status: active",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if use_when:
        lines.extend(["## Use when", use_when, ""])
    lines.extend([content, ""])
    write_text_atomic(out_path, "\n".join(lines))
    try:
        bump_state_seq(vault, reason="methodology.write")
    except Exception:  # noqa: BLE001
        pass
    return {
        "written": True,
        "id": slug,
        "title": title,
        "path": str(out_path),
    }


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

    if getattr(args, "write_methodology", False):
        try:
            payload = _read_json_input(args)
            if getattr(args, "title", "") and not payload.get("title"):
                payload["title"] = args.title
            if getattr(args, "project", "") and not payload.get("project"):
                payload["project"] = args.project
            result_data = _write_methodology_card(vault, payload)
            result = PFResult(ok=True, command="project-log", version=PF_VERSION, data=result_data)
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            result = PFResult(
                ok=False,
                command="project-log",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
            )
        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print(f"Methodology written: {result.data['id']}" if result.ok else f"Error: {result.error.message}")
        return 0 if result.ok else 1

    if getattr(args, "write", False):
        project = getattr(args, "project", "")

        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --write"))
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
            return 1

        try:
            entry = _read_json_input(args)
            entry["project"] = project
            result_data = append_project_entry(vault, entry)

            _render_project_log_md(vault, project)

            result = PFResult(ok=True, command="project-log", version=PF_VERSION, data=result_data)
        except (json.JSONDecodeError, ValueError, OSError, UnicodeError) as e:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=f"Invalid JSON or input: {e}"))

        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print("Written." if result.ok else f"Error: {result.error.message}")
        return 0 if result.ok else 1

    if getattr(args, "list", False):
        project = getattr(args, "project", "")
        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --list"))
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
            return 1

        entries = get_project_entries(vault, project)
        data = {"project": project, "entries": entries[:getattr(args, "limit", 50)], "count": len(entries)}
        result = PFResult(ok=True, command="project-log", version=PF_VERSION, data=data)

        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print(f"{len(entries)} entries for project '{project}'")
            for e in entries[:5]:
                print(f"  [{e.get('date', '')}] {e.get('type', '')}: {e.get('title', '')}")
        return 0

    if getattr(args, "render", False):
        project = getattr(args, "project", "")
        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --render"))
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
            return 1

        _render_project_log_md(vault, project)
        result = PFResult(ok=True, command="project-log", version=PF_VERSION,
                         data={"rendered": True, "project": project})
        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print(f"Rendered project-log.md for '{project}'")
        return 0

    # Default: show all projects with entry counts
    all_entries = read_all_project_entries(vault)
    project_counts = Counter(e["project"] for e in all_entries if e.get("project"))

    result = PFResult(ok=True, command="project-log", version=PF_VERSION,
                     data={"projects": dict(project_counts)})
    if getattr(args, "json", False):
        print(result.to_json())
    else:
        if project_counts:
            print("Projects with log entries:")
            for proj, cnt in project_counts.most_common():
                print(f"  {proj}: {cnt} entries")
        else:
            print("No project log entries found.")
    return 0
