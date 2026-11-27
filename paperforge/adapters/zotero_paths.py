from __future__ import annotations

import os
from pathlib import Path


def obsidian_wikilink_for_pdf(pdf_path: str, vault_dir: Path, zotero_dir: Path | None = None) -> str:
    text = str(pdf_path or "").strip()
    if text.startswith("absolute:"):
        text = text[len("absolute:") :].strip()
    if not text:
        return ""
    # Handle storage: prefix paths by resolving through zotero_dir
    if text.startswith("storage:") and zotero_dir is not None:
        storage_rel = text[len("storage:") :].replace("\\", "/").lstrip("/")
        absolute_pdf_path = zotero_dir / "storage" / storage_rel.replace("/", os.sep)
        absolute_str = str(absolute_pdf_path)
    elif text.startswith("attachments:"):
        att_rel = text[len("attachments:") :].replace("\\", "/").lstrip("/")
        base_att_dir = None
        try:
            from paperforge.adapters.zotero_sqlite import read_zotero_base_attachment_path

            base_att_dir = read_zotero_base_attachment_path(zotero_dir)
        except Exception:
            base_att_dir = None
        if base_att_dir is not None and att_rel:
            absolute_str = str(base_att_dir / att_rel.replace("/", os.sep))
        else:
            return ""
    else:
        absolute_str = absolutize_vault_path(vault_dir, text, resolve_junction=True)
    if not absolute_str:
        return ""
    absolute_path = Path(absolute_str)
    try:
        relative = absolute_path.relative_to(vault_dir)
    except ValueError:
        # Path outside vault — try to route through any Zotero junction inside vault
        from paperforge.pdf_resolver import resolve_junction

        junction_candidates: list[Path] = []
        if zotero_dir is not None:
            junction_candidates.append(zotero_dir)
        for sub in (".paperforge", "System"):
            cand = vault_dir / sub / "Zotero"
            if cand not in junction_candidates:
                junction_candidates.append(cand)
        for jcand in junction_candidates:
            try:
                jcand.relative_to(vault_dir)
            except ValueError:
                continue
            if not jcand.exists():
                continue
            try:
                real_zotero = resolve_junction(jcand)
                if real_zotero == jcand:
                    continue
                try:
                    rel_to_zotero = absolute_path.relative_to(real_zotero)
                except ValueError:
                    rel_to_zotero = absolute_path.resolve().relative_to(real_zotero.resolve())
                via_junction = jcand / rel_to_zotero
                relative = via_junction.relative_to(vault_dir)
                return f"[[{relative.as_posix()}]]"
            except (ValueError, OSError):
                continue
        return f"[[{absolute_path.as_posix()}]]"
    return f"[[{relative.as_posix()}]]"


def absolutize_vault_path(vault: Path, path: str, resolve_junction: bool = False) -> str:
    text = str(path or "").strip()
    if text.startswith("absolute:"):
        text = text[len("absolute:") :].strip()
    if not text:
        return ""
    candidate = Path(text)
    result = str(candidate) if candidate.is_absolute() else str((vault / text.replace("/", os.sep)).resolve())
    if resolve_junction:
        from paperforge.pdf_resolver import resolve_junction

        result = str(resolve_junction(Path(result)))
    return result


def obsidian_wikilink_for_path(vault: Path, path: str) -> str:
    absolute = absolutize_vault_path(vault, path, resolve_junction=True)
    if not absolute:
        return ""
    absolute_path = Path(absolute)
    try:
        relative = absolute_path.relative_to(vault)
    except ValueError:
        return f"[[{absolute_path.as_posix()}]]"
    return f"[[{relative.as_posix()}]]"
