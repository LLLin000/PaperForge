"""Canonical local-read service (#189).

Zero-synthesis local reading: KEY + literal query in, structured matches out.
The agent never extracts paths, constructs grep/PyMuPDF shell commands, or
strips wikilinks — canonical resolution, path handling, and literal matching
all live here. Read-only; no network; no vector dependency.

Boundary: this service must NOT import ``paperforge.commands.*`` (control-plane
rule) — it resolves the canonical paper row directly via the memory DB,
the same lookup ``paper-context`` builds on, never by invoking that command.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReadMatch:
    """One literal hit in a canonical source."""

    source: str  # "fulltext" | "pdf"
    text: str
    line: int | None = None  # fulltext line (1-based)
    page: int | None = None  # pdf page (1-based)

    def to_dict(self) -> dict:
        d: dict = {"source": self.source, "text": self.text}
        if self.line is not None:
            d["line"] = self.line
        if self.page is not None:
            d["page"] = self.page
        return d


def _lookup_canonical(vault: Path, key: str) -> dict | None:
    """Canonical paper row (fulltext_path / pdf_path) from the papers table.

    Same authority as ``paper-context``: single unique lookup via
    ``memory.query.lookup_paper``, then the papers row. Returns None when the
    key does not resolve uniquely.
    """
    from paperforge.memory.db import get_memory_db_path, open_live_reader
    from paperforge.memory.query import lookup_paper

    db_path = get_memory_db_path(vault)
    if not db_path or not db_path.exists():
        return None
    with open_live_reader(vault, db_path) as conn:
        matches = lookup_paper(conn, key)
        if not matches or len(matches) != 1:
            return None
        resolved = str(matches[0]["zotero_key"])
        row = conn.execute(
            "SELECT zotero_key, fulltext_path, pdf_path FROM papers WHERE zotero_key = ?",
            (resolved,),
        ).fetchone()
        if not row:
            return None
        return {
            "zotero_key": resolved,
            "fulltext_path": str(row["fulltext_path"] or ""),
            "pdf_path": str(row["pdf_path"] or ""),
        }


def _resolve_fulltext(vault: Path, paper: dict) -> Path | None:
    """Canonical fulltext path: vault-relative (as stored in papers table)."""
    rel = paper.get("fulltext_path") or ""
    if not rel:
        return None
    p = (vault / rel).resolve()
    return p if p.is_file() else None


def _resolve_canonical_pdf(vault: Path, paper: dict) -> Path | None:
    """Canonical PDF via the shared locator resolver (wikilink / vault-relative
    / storage fallback).  Never manual path discovery."""
    locator = paper.get("pdf_path") or ""
    if not locator:
        return None
    from paperforge.pdf_resolver import resolve_pdf_path

    resolved = resolve_pdf_path(locator, True, vault)
    if not resolved:
        return None
    p = Path(resolved)
    return p if p.is_file() else None


def _match_fulltext(path: Path, term: str) -> list[ReadMatch]:
    """Literal case-insensitive substring match, per line."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    low = term.lower()
    out: list[ReadMatch] = []
    for i, line in enumerate(text.splitlines(), 1):
        if low in line.lower():
            out.append(ReadMatch(source="fulltext", text=line.strip(), line=i))
    return out


def _match_pdf(path: Path, term: str) -> list[ReadMatch]:
    """Literal case-insensitive substring match, per page (PyMuPDF)."""
    try:
        import fitz  # noqa: PLC0415 — extraction dependency resolved at call time

        doc = fitz.open(str(path))
    except Exception:  # noqa: BLE001 — unreadable PDF -> no matches from this source
        return []
    low = term.lower()
    out: list[ReadMatch] = []
    try:
        for i, page in enumerate(doc, 1):
            text = page.get_text() or ""
            if low in text.lower():
                out.append(ReadMatch(source="pdf", text=text.strip(), page=i))
    finally:
        doc.close()
    return out


def read_paper_local(
    vault: Path,
    key: str,
    find: str,
    source: str = "auto",
) -> dict:
    """Canonical local literal read.

    Returns:
        {"status": "matched"|"no_match"|"no_readable_source", "matches": [...]}

    - ``matched``: at least one literal hit (fulltext line / pdf page).
    - ``no_match``: source(s) readable but the literal is absent.
    - ``no_readable_source``: key unresolvable OR no valid fulltext/pdf.

    ``source``: "auto" (fulltext + canonical PDF, fulltext hits first),
    "fulltext", or "pdf". Literal matching is case-insensitive substring;
    never regex.
    """
    term = str(find or "").strip()
    paper = _lookup_canonical(vault, key)
    if paper is None or not term:
        return {"status": "no_readable_source", "matches": []}

    matches: list[ReadMatch] = []
    if source in ("auto", "fulltext"):
        ft = _resolve_fulltext(vault, paper)
        if ft is not None:
            matches.extend(_match_fulltext(ft, term))
    if source in ("auto", "pdf"):
        pdf = _resolve_canonical_pdf(vault, paper)
        if pdf is not None:
            matches.extend(_match_pdf(pdf, term))

    if not matches:
        # Distinguish "readable but absent" from "nothing to read".
        if source in ("auto", "fulltext") and _resolve_fulltext(vault, paper) is not None:
            return {"status": "no_match", "matches": []}
        if source in ("auto", "pdf") and _resolve_canonical_pdf(vault, paper) is not None:
            return {"status": "no_match", "matches": []}
        return {"status": "no_readable_source", "matches": []}

    # Fulltext hits first (line order), then pdf (page order); dedupe by
    # (source, text) so an identical line/page is reported once.
    seen: set[tuple[str, str]] = set()
    unique: list[ReadMatch] = []
    for m in matches:
        key_pair = (m.source, m.text)
        if key_pair in seen:
            continue
        seen.add(key_pair)
        unique.append(m)
    return {
        "status": "matched",
        "matches": [m.to_dict() for m in unique],
    }
