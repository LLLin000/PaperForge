from __future__ import annotations

import argparse
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.events import export_reading_log, write_reading_note


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

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
