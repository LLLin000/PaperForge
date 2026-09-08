"""paperforge.commands.note — ``paperforge note set-flag``.

Final-leaf-census corrective (Ticket 07 step 6): the dashboard workflow
toggles (``do_ocr``/``analyze``) previously mutated the note frontmatter
through Obsidian's ``processFrontMatter`` — a frontend semantic mutation
on Python's own literature notes. Python is the authority over its notes:
the toggle now routes through this narrow surface, and the thin client
never touches note files.
"""

from __future__ import annotations

import argparse

# Fail-closed field allowlist — no arbitrary frontmatter key injection.
ALLOWED_FIELDS = ("do_ocr", "analyze")


def _err(version: str, message: str):
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult

    return PFResult(
        ok=False,
        command="note",
        version=version,
        error=PFError(code=ErrorCode.VALIDATION_ERROR, message=message),
    )


def run(args: argparse.Namespace) -> int:
    """Set a boolean workflow flag on the canonical note frontmatter."""
    from paperforge import __version__
    from paperforge.config import resolve_vault

    field = args.field
    if field not in ALLOWED_FIELDS:
        result = _err(
            __version__,
            f"field must be one of {', '.join(ALLOWED_FIELDS)}; got {field!r}",
        )
        print(result.to_json())
        return 1
    value = (
        args.value.strip().lower() in ("true", "1", "yes")
        if isinstance(args.value, str)
        else bool(args.value)
    )

    try:
        vault = resolve_vault(cli_vault=getattr(args, "vault", None))
        from paperforge.worker.asset_index import read_index

        index = read_index(vault)
        items = index.get("items", []) if isinstance(index, dict) else (
            index if isinstance(index, list) else []
        )
        entry = next(
            (
                it
                for it in items
                if str(it.get("zotero_key", "")).lower()
                == str(args.key).lower()
            ),
            None,
        )
        if entry is None:
            result = _err(__version__, f"unknown paper key: {args.key}")
            print(result.to_json())
            return 1
        note_rel = entry.get("note_path") or ""
        note_rel = note_rel.replace("\\", "/").strip()
        if note_rel.startswith("[[") and note_rel.endswith("]]"):
            note_rel = note_rel[2:-2]
        note = vault / note_rel
        if not note_rel or not note.exists():
            result = _err(
                __version__,
                f"note file not found for {args.key}: {note_rel or '<missing>'}",
            )
            print(result.to_json())
            return 1

        from paperforge.adapters.obsidian_frontmatter import (
            read_frontmatter_dict,
            set_frontmatter_flag,
        )

        text = note.read_text(encoding="utf-8")
        if not text.startswith("---"):
            result = _err(
                __version__, f"note has no frontmatter: {note_rel}"
            )
            print(result.to_json())
            return 1
        fm = read_frontmatter_dict(text)
        if fm.get(field) is value:
            # Idempotent no-op — still authoritative, no write.
            data = {
                "intent": "note-set-flag",
                "key": entry.get("zotero_key"),
                "field": field,
                "value": value,
                "note_path": note_rel,
                "changed": False,
            }
            from paperforge.core.result import PFResult

            result = PFResult(
                ok=True, command="note", version=__version__, data=data
            )
            print(result.to_json())
            return 0
        note.write_text(set_frontmatter_flag(text, field, value), encoding="utf-8")
        data = {
            "intent": "note-set-flag",
            "key": entry.get("zotero_key"),
            "field": field,
            "value": value,
            "note_path": note_rel,
            "changed": True,
        }
        from paperforge.core.result import PFResult

        result = PFResult(
            ok=True, command="note", version=__version__, data=data
        )
        print(result.to_json())
        return 0
    except Exception as exc:
        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError, PFResult

        result = PFResult(
            ok=False,
            command="note",
            version=__version__,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        print(result.to_json())
        return 1
