"""Deterministic paper lookup engine.

Resolves papers by key, DOI, or structured field search from formal-library.json.
Natural language queries are handled by the Agent — this module handles only
deterministic lookups.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PaperMeta:
    """Lightweight paper metadata for structured search results."""

    key: str
    title: str
    domain: str
    year: str = ""
    authors: str = ""
    doi: str = ""
    journal: str = ""
    collection_path: str = ""
    lifecycle: str = ""


@dataclass
class PaperWorkspace:
    """Full workspace paths and metadata for a resolved paper."""

    key: str
    title: str
    domain: str
    formal_note_path: str
    ocr_path: str
    fulltext_path: str
    frontmatter: dict = field(default_factory=dict)
    year: str = ""
    authors: str = ""
    doi: str = ""
    journal: str = ""
    ocr_status: str = ""
    deep_reading_status: str = ""
    analyze: bool = False
    do_ocr: bool = False
    has_pdf: bool = False


class PaperResolver:
    """Deterministic paper lookup from formal-library.json index."""

    def __init__(self, vault: Path):
        self._vault = vault
        self._paths: dict[str, Path] = {}
        self._items: list[dict] = []
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        try:
            from paperforge.config import paperforge_paths

            self._paths = paperforge_paths(self._vault)
        except Exception:
            self._paths = {}
        try:
            from paperforge.worker.asset_index import read_index

            data = read_index(self._vault)
            if isinstance(data, dict):
                self._items = data.get("items", [])
        except Exception:
            self._items = []
        self._loaded = True

    def resolve_key(self, key: str) -> Optional[PaperWorkspace]:
        """Exact match on zotero_key."""
        self._ensure_loaded()
        for entry in self._items:
            if entry.get("zotero_key", "").strip().upper() == key.strip().upper():
                return self._build_workspace(entry)
        return None

    def resolve_doi(self, doi: str) -> Optional[PaperWorkspace]:
        """Exact match on DOI (case-insensitive, normalized)."""
        self._ensure_loaded()
        normalized = self._normalize_doi(doi)
        for entry in self._items:
            entry_doi = self._normalize_doi(entry.get("doi", ""))
            if entry_doi and entry_doi == normalized:
                return self._build_workspace(entry)
        return None

    def search(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        year: Optional[int | str] = None,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> list[PaperWorkspace]:
        """Multi-field search with substring matching, sorted by relevance score.

        All supplied fields must match (AND logic). Each field contributes to
        a relevance score for ranking.
        """
        self._ensure_loaded()
        scored: list[tuple[int, PaperWorkspace]] = []

        title_lower = title.strip().lower() if title else None
        author_lower = author.strip().lower() if author else None
        year_str = str(year).strip() if year is not None else None
        domain_lower = domain.strip().lower() if domain else None

        for entry in self._items:
            score = 0
            entry_title = (entry.get("title") or "").lower()
            entry_authors = _flatten_authors(entry.get("authors", "")).lower()
            entry_year = str(entry.get("year", ""))
            entry_domain = (entry.get("domain") or "").lower()

            if title_lower:
                if title_lower == entry_title:
                    score += 100
                elif title_lower in entry_title:
                    score += 30
                else:
                    continue
            if author_lower:
                if author_lower in entry_authors:
                    score += 50
                else:
                    continue
            if year_str:
                if year_str == entry_year:
                    score += 40
                else:
                    continue
            if domain_lower:
                if domain_lower == entry_domain:
                    score += 20
                elif domain_lower in entry_domain:
                    score += 10
                else:
                    continue

            if score > 0 or not any([title_lower, author_lower, year_str, domain_lower]):
                scored.append((score, self._build_workspace(entry)))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ws for _, ws in scored[:limit]]

    def _build_workspace(self, entry: dict) -> PaperWorkspace:
        """Build a PaperWorkspace from an index entry dict."""
        key = entry.get("zotero_key", "")
        title = entry.get("title", "")
        domain = entry.get("domain", "")
        note_path = entry.get("note_path", "")

        ocr_base = _resolve_ocr_base(self._paths, key)
        fulltext_path = entry.get("fulltext_path", "")
        if not fulltext_path and ocr_base:
            fulltext_path = str(ocr_base / "fulltext.md")

        frontmatter = {}
        if note_path:
            try:
                note_full = self._vault / note_path
                if note_full.exists():
                    from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict

                    frontmatter = read_frontmatter_dict(note_full.read_text(encoding="utf-8"))
            except Exception:
                pass

        authors_raw = entry.get("authors", "")
        if isinstance(authors_raw, list):
            authors_str = "; ".join(authors_raw)
        else:
            authors_str = str(authors_raw)

        return PaperWorkspace(
            key=key,
            title=title,
            domain=domain,
            formal_note_path=note_path,
            ocr_path=str(ocr_base) if ocr_base else "",
            fulltext_path=fulltext_path,
            frontmatter=frontmatter,
            year=str(entry.get("year", "")),
            authors=authors_str,
            doi=entry.get("doi", ""),
            journal=entry.get("journal", ""),
            ocr_status=entry.get("ocr_status", ""),
            deep_reading_status=entry.get("deep_reading_status", ""),
            analyze=bool(entry.get("analyze", False)),
            do_ocr=bool(entry.get("do_ocr", False)),
            has_pdf=bool(entry.get("has_pdf", False)),
        )

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI to lowercase, strip URL prefixes."""
        s = doi.strip().lower()
        s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
        return s


def _resolve_ocr_base(paths: dict[str, Path], key: str) -> Optional[Path]:
    """Get the OCR directory for a given zotero key."""
    ocr_dir = paths.get("ocr")
    if ocr_dir and key:
        candidate = ocr_dir / key
        if candidate.exists():
            return candidate
    return None


def _flatten_authors(authors) -> str:
    """Convert authors (list or str) to a single searchable string."""
    if isinstance(authors, list):
        return "; ".join(authors)
    return str(authors)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _ok_result(command: str, data: dict) -> str:
    """Produce a PFResult-compatible JSON string to stdout."""
    from paperforge import __version__

    result = {
        "ok": True,
        "command": command,
        "version": __version__,
        "data": data,
        "error": None,
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _err_result(command: str, message: str) -> str:
    from paperforge import __version__

    result = {
        "ok": False,
        "command": command,
        "version": __version__,
        "data": None,
        "error": {"code": "INTERNAL_ERROR", "message": message},
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _workspace_to_dict(ws: PaperWorkspace) -> dict:
    return {
        "key": ws.key,
        "title": ws.title,
        "domain": ws.domain,
        "year": ws.year,
        "authors": ws.authors,
        "doi": ws.doi,
        "journal": ws.journal,
        "formal_note_path": ws.formal_note_path,
        "ocr_path": ws.ocr_path,
        "fulltext_path": ws.fulltext_path,
        "ocr_status": ws.ocr_status,
        "deep_reading_status": ws.deep_reading_status,
        "analyze": ws.analyze,
        "do_ocr": ws.do_ocr,
        "has_pdf": ws.has_pdf,
    }


def main():
    parser = argparse.ArgumentParser(description="PaperForge paper resolver")
    sub = parser.add_subparsers(dest="command", required=True)

    rk = sub.add_parser("resolve-key")
    rk.add_argument("key", help="Zotero key (8-char alphanumeric)")
    rk.add_argument("--vault", required=True, help="Path to vault root")

    rd = sub.add_parser("resolve-doi")
    rd.add_argument("doi", help="DOI string")
    rd.add_argument("--vault", required=True, help="Path to vault root")

    sr = sub.add_parser("search")
    sr.add_argument("--title", default=None)
    sr.add_argument("--author", default=None)
    sr.add_argument("--year", default=None)
    sr.add_argument("--domain", default=None)
    sr.add_argument("--limit", type=int, default=20)
    sr.add_argument("--vault", required=True, help="Path to vault root")

    pt = sub.add_parser("paths")
    pt.add_argument("--vault", required=True, help="Path to vault root")

    args = parser.parse_args()

    try:
        vault = Path(args.vault).resolve()
        if not vault.exists():
            print(_err_result(args.command, f"Vault not found: {args.vault}"), file=sys.stdout)
            sys.exit(1)

        resolver = PaperResolver(vault)

        if args.command == "resolve-key":
            ws = resolver.resolve_key(args.key)
            if ws:
                print(_ok_result("resolve-key", {"match": _workspace_to_dict(ws)}), file=sys.stdout)
            else:
                print(
                    json.dumps({
                        "ok": True,
                        "command": "resolve-key",
                        "data": {"match": None, "message": f"No paper found with key: {args.key}"},
                        "error": None,
                    }, ensure_ascii=False, indent=2),
                    file=sys.stdout,
                )

        elif args.command == "resolve-doi":
            ws = resolver.resolve_doi(args.doi)
            if ws:
                print(_ok_result("resolve-doi", {"match": _workspace_to_dict(ws)}), file=sys.stdout)
            else:
                print(
                    json.dumps({
                        "ok": True,
                        "command": "resolve-doi",
                        "data": {"match": None, "message": f"No paper found with DOI: {args.doi}"},
                        "error": None,
                    }, ensure_ascii=False, indent=2),
                    file=sys.stdout,
                )

        elif args.command == "search":
            results = resolver.search(
                title=args.title,
                author=args.author,
                year=args.year,
                domain=args.domain,
                limit=args.limit,
            )
            print(
                _ok_result(
                    "search",
                    {
                        "matches": [_workspace_to_dict(ws) for ws in results],
                        "count": len(results),
                    },
                ),
                file=sys.stdout,
            )

        elif args.command == "paths":
            resolver._ensure_loaded()
            paths_data = {
                "vault_root": str(resolver._vault),
                "index_path": str(resolver._paths.get("index", "")),
                "literature_dir": str(resolver._paths.get("literature", "")),
                "ocr_dir": str(resolver._paths.get("ocr", "")),
            }
            print(_ok_result("paths", paths_data), file=sys.stdout)

    except Exception as exc:
        print(_err_result(args.command, str(exc)), file=sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
