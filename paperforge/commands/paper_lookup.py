"""paperforge.commands.paper_lookup — ``paperforge paper-lookup`` gateway command.

Ticket 07 step 5 semantic-boundary corrective: ``--from-path`` resolves a
vault-relative note/PDF/workspace path (or a Base basename) to its CANONICAL
paper identity. The plugin passes only the host fact (the active path);
frontmatter, the canonical index, and workspace-key derivation are Python
authority — the thin client never infers paper identity from files.
"""

from __future__ import annotations

import argparse
import re

from paperforge.retrieval import gateway

_WORKSPACE_KEY_RE = re.compile(r"^([A-Z0-9]{8})(?:\s*-\s*.*)?$", re.IGNORECASE)


def _norm(p: str | None) -> str:
    return (p or "").replace("\\", "/").strip()


def _unwrap_wikilink(p: str | None) -> str:
    m = re.match(r"\[\[([^\]]+)\]\]", p or "")
    return m.group(1) if m else (p or "")


def resolve_paper_context(vault, rel_path: str) -> dict:
    """Resolve a vault-relative path to canonical paper identity.

    Resolution order mirrors the retired TypeScript inference, but every
    branch reads Python-authoritative data (canonical index, literature
    notes, vault config) — never Obsidian host state:
      1. canonical-index ``note_path`` exact match
      2. canonical-index ``pdf_path`` match (wikilink unwrapped)
      3. note frontmatter ``zotero_key`` (Python's own notes)
      4. workspace folder key (matched against index entries — a folder
         key with NO index entry is NOT canonical: fail closed)
      5. Base basename -> literature domain directory
    """
    identity: dict = {"kind": "unknown"}
    rel = _norm(rel_path)
    if not rel:
        return identity

    from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict
    from paperforge.worker.asset_index import read_index

    index = read_index(vault)
    if isinstance(index, dict):
        items = index.get("items", [])
    elif isinstance(index, list):
        items = index  # legacy bare-list format
    else:
        items = []

    for it in items:
        if _norm(_unwrap_wikilink(it.get("note_path"))) == rel:
            return {"kind": "paper", "zotero_key": it.get("zotero_key"), "entry": it}
    for it in items:
        if _norm(_unwrap_wikilink(it.get("pdf_path"))) == rel:
            return {"kind": "paper", "zotero_key": it.get("zotero_key"), "entry": it}

    if rel.lower().endswith(".md"):
        note = vault / rel
        if note.exists():
            try:
                fm = read_frontmatter_dict(note.read_text(encoding="utf-8"))
            except Exception:
                fm = {}
            key = (fm or {}).get("zotero_key")
            if key:
                for it in items:
                    if str(it.get("zotero_key", "")).lower() == str(key).lower():
                        return {
                            "kind": "paper",
                            "zotero_key": it["zotero_key"],
                            "entry": it,
                        }
                return {"kind": "paper", "zotero_key": str(key), "entry": None}

    parts = rel.split("/")
    for seg in reversed(parts[:-1]):
        m = _WORKSPACE_KEY_RE.match(seg)
        if m:
            cand = m.group(1)
            for it in items:
                if str(it.get("zotero_key", "")).lower() == cand.lower():
                    return {
                        "kind": "paper",
                        "zotero_key": it["zotero_key"],
                        "entry": it,
                    }
            # Folder-key without an index entry is not canonical identity.
            return identity

    if rel.lower().endswith(".base"):
        base = parts[-1][: -len(".base")].strip()
        if base:
            from paperforge.config import load_vault_config, paperforge_paths

            paths = paperforge_paths(vault, load_vault_config(vault))
            if (paths["literature"] / base).is_dir():
                return {"kind": "domain", "domain": base}

    return identity


def run(args: argparse.Namespace) -> int:
    """Execute ``paper-lookup`` via the Layer 4 gateway (or --from-path)."""
    from paperforge import __version__
    from paperforge.config import resolve_vault
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult

    if getattr(args, "from_path", None):
        try:
            vault = resolve_vault(cli_vault=getattr(args, "vault", None))
        except FileNotFoundError as exc:
            result = PFResult(
                ok=False,
                command="paper-lookup",
                version=__version__,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
            print(result.to_json())
            return 1
        try:
            data = {"intent": "paper-lookup", "identity": resolve_paper_context(vault, args.from_path)}
            result = PFResult(ok=True, command="paper-lookup", version=__version__, data=data)
        except Exception as exc:
            result = PFResult(
                ok=False,
                command="paper-lookup",
                version=__version__,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
        print(result.to_json())
        return 0 if result.ok else 1

    result = gateway.route_gateway(
        args.vault_path,
        "paper-lookup",
        args.query,
        json_mode=args.json,
        limit=getattr(args, "limit", 5),
    )
    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
