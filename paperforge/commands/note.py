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
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotation only
    from pathlib import Path

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


#: Canonical note locations, most authoritative first. `main_note_path` is the
#: workspace note whose slug sync freezes; `note_path` is the legacy flat field
#: and is stale for every workspace-layout paper (#230).
NOTE_PATH_FIELDS = ("main_note_path", "note_path")


def _resolve_note(vault: Path, entry: dict) -> tuple[Path | None, str]:
    """Resolve a paper's note the way the rest of the system does.

    Prefers the canonical path but accepts the legacy one when it is the only
    one that exists, and reports every candidate it tried when neither does —
    an error naming the paths tried is diagnosable; a bare "not found" is not.
    """
    candidates: list[tuple[str, str]] = []
    for field in NOTE_PATH_FIELDS:
        raw = str(entry.get(field) or "").replace("\\", "/").strip()
        if raw.startswith("[[") and raw.endswith("]]"):
            raw = raw[2:-2]
        if raw:
            candidates.append((field, raw))
    for _field, rel in candidates:
        path = vault / rel
        if path.exists():
            return path, rel
    tried = ", ".join(f"{field}={rel}" for field, rel in candidates) or "<missing>"
    return None, tried


def _sync_index_flag(vault: Path, key: str, field: str, value: bool) -> bool:
    """Keep the dashboard's index projection aligned with the canonical note."""
    from paperforge.worker.asset_index import mutate_index

    found = False

    def _patch(current):
        nonlocal found
        if isinstance(current, dict):
            items = current.get("items")
            if not isinstance(items, list):
                return None
        elif isinstance(current, list):
            items = current
        else:
            return None

        for position, item in enumerate(items):
            if not isinstance(item, dict) or str(item.get("zotero_key", "")).lower() != key.lower():
                continue
            found = True
            if item.get(field) is value:
                return None
            updated_items = list(items)
            updated_entry = dict(item)
            updated_entry[field] = value
            updated_items[position] = updated_entry
            if isinstance(current, dict):
                updated = dict(current)
                updated["items"] = updated_items
                return updated
            return updated_items
        return None

    return mutate_index(vault, _patch) or found


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
        from paperforge.worker.asset_index import get_index_path, read_index

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
        note, note_rel = _resolve_note(vault, entry)
        if note is None:
            result = _err(
                __version__,
                f"note file not found for {args.key}: {note_rel}",
            )
            print(result.to_json())
            return 1

        from paperforge.adapters.obsidian_frontmatter import (
            read_frontmatter_dict,
            set_frontmatter_flag,
            split_frontmatter_block,
        )

        from paperforge.core.io import write_text_atomic, write_text_cas
        import hashlib as _hashlib

        orig_bytes = note.read_bytes()
        orig_sha = _hashlib.sha256(orig_bytes).hexdigest()
        # Byte-preserving I/O: read/write with newline translation OFF so
        # the durable note keeps its original CRLF/LF endings on every
        # platform (Path.read_text would translate CRLF away).
        text = orig_bytes.decode("utf-8")
        # Authority validation BEFORE any mutation: an absent or
        # unterminated frontmatter block is a validation failure — never
        # a silent unchanged-file success.
        if split_frontmatter_block(text) is None:
            result = _err(
                __version__,
                f"note has no valid frontmatter block: {note_rel}",
            )
            print(result.to_json())
            return 1
        probe_text = text[1:] if text.startswith("\ufeff") else text
        fm = read_frontmatter_dict(probe_text)
        changed = fm.get(field) is not value
        if changed:
            write_text_cas(
                note,
                set_frontmatter_flag(text, field, value),
                expected_sha256=orig_sha,
                newline="",
            )
        state = "was saved" if changed else "is already set"

        def _index_sync_failure(reason: str) -> str:
            message = f"dashboard index sync failed: {reason}"
            if not changed:
                return f"canonical note flag {state}, but {message}"
            try:
                write_text_atomic(note, text, newline="")
            except Exception as rollback_exc:
                return (
                    f"{message}; canonical note rollback failed: {rollback_exc}; "
                    "the note may still contain the requested value"
                )
            return f"{message}; canonical note was restored"

        try:
            index_synced = _sync_index_flag(
                vault, str(entry.get("zotero_key")), field, value
            )
        except Exception as exc:
            raise RuntimeError(_index_sync_failure(str(exc))) from exc
        if not index_synced:
            current_index = read_index(vault)
            index_path = get_index_path(vault)
            if current_index is None:
                reason = (
                    "index file is missing"
                    if not index_path.exists()
                    else "index JSON is unreadable or invalid"
                )
            else:
                items = (
                    current_index.get("items")
                    if isinstance(current_index, dict)
                    else current_index
                )
                if not isinstance(items, list):
                    reason = "index items structure is invalid"
                elif not any(
                    isinstance(item, dict)
                    and str(item.get("zotero_key", "")).lower()
                    == str(entry.get("zotero_key", "")).lower()
                    for item in items
                ):
                    reason = "target index row is missing"
                else:
                    reason = "target index row was not updated"
            raise RuntimeError(_index_sync_failure(reason))
        try:
            from paperforge.services.state_signal import bump_state_seq

            bump_state_seq(
                vault,
                reason=f"note.{field}",
                changed_keys=[str(entry.get("zotero_key") or "")],
            )
        except Exception:
            pass
        data = {
            "intent": "note-set-flag",
            "key": entry.get("zotero_key"),
            "field": field,
            "value": value,
            "note_path": note_rel,
            "changed": changed,
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
