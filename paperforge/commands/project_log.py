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


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

    if getattr(args, "write", False):
        project = getattr(args, "project", "")
        payload_str = getattr(args, "payload", "")

        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --write"))
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
            return 1

        if not payload_str:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--payload is required for --write"))
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
            return 1

        try:
            entry = json.loads(payload_str)
            entry["project"] = project
            result_data = append_project_entry(vault, entry)

            _render_project_log_md(vault, project)

            result = PFResult(ok=True, command="project-log", version=PF_VERSION, data=result_data)
        except json.JSONDecodeError as e:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=f"Invalid JSON: {e}"))

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
