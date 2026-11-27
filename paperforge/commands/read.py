"""``paperforge read`` — canonical local-read CLI (#189) + page-range reading."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.services.local_read import read_paper_local

VALID_SOURCES = ("auto", "fulltext", "pdf")
_PAGE_MARKER_RE = re.compile(r"^<!--\s*page\s+(\d+)\s*-->$", re.IGNORECASE)


def _lookup_paper_fallback(vault: Path, key: str) -> dict | None:
    """Resolve paper via SQLite DB first, falling back to formal-library.json if DB is absent."""
    from paperforge.memory.db import get_memory_db_path, open_live_reader
    from paperforge.memory.query import lookup_paper

    db_path = get_memory_db_path(vault)
    if db_path and db_path.exists():
        with open_live_reader(vault, db_path) as conn:
            matches = lookup_paper(conn, key)
            if matches and len(matches) == 1:
                resolved = str(matches[0]["zotero_key"])
                row = conn.execute(
                    "SELECT zotero_key, fulltext_path, pdf_path FROM papers WHERE zotero_key = ?",
                    (resolved,),
                ).fetchone()
                if row:
                    return {
                        "zotero_key": resolved,
                        "fulltext_path": str(row["fulltext_path"] or ""),
                        "pdf_path": str(row["pdf_path"] or ""),
                    }
        return None

    from paperforge.worker.asset_index import read_index

    idx = read_index(vault)
    items = idx.get("items", []) if isinstance(idx, dict) else (idx or [])
    q = str(key or "").strip().lower()
    if not q:
        return None
    matches = [
        it
        for it in items
        if isinstance(it, dict)
        and (
            str(it.get("zotero_key") or "").strip().lower() == q
            or str(it.get("citation_key") or "").strip().lower() == q
            or str(it.get("doi") or "").strip().lower() == q
        )
    ]
    if len(matches) != 1:
        return None
    row = matches[0]
    return {
        "zotero_key": str(row.get("zotero_key") or ""),
        "fulltext_path": str(row.get("fulltext_path") or ""),
        "pdf_path": str(row.get("pdf_path") or ""),
    }


def _resolve_fulltext_path(vault: Path, paper: dict) -> Path | None:
    rel = paper.get("fulltext_path") or ""
    if not rel:
        return None
    candidate = (vault / rel).resolve()
    try:
        candidate.relative_to(vault.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _resolve_pdf_file(vault: Path, paper: dict) -> Path | None:
    locator = paper.get("pdf_path") or ""
    if not locator:
        return None
    from paperforge.config import paperforge_paths
    from paperforge.pdf_resolver import resolve_pdf_path

    zotero_dir = paperforge_paths(vault).get("zotero_dir")
    resolved = resolve_pdf_path(locator, True, vault, zotero_dir)
    if not resolved:
        return None
    p = Path(resolved)
    return p if p.is_file() else None


def _parse_page_spec(spec: str, page_count: int) -> list[int]:
    """Parse 1-based page specification like '1-3', '2', or '1,3-5'."""
    if page_count <= 0:
        return []
    raw = str(spec or "").strip()
    if not raw or raw.lower() == "all":
        return list(range(1, page_count + 1))

    pages: list[int] = []
    seen: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            pieces = token.split("-", 1)
            if len(pieces) != 2 or not pieces[0].strip().isdigit() or not pieces[1].strip().isdigit():
                raise ValueError(f"Invalid --pages range: {token!r}")
            start = int(pieces[0].strip())
            end = int(pieces[1].strip())
            if start < 1 or end < start:
                raise ValueError(f"Invalid --pages range: {token!r}")
            if start > page_count:
                raise ValueError(f"Requested page {start} exceeds page_count={page_count}")
            clamped_end = min(end, page_count)
            for p in range(start, clamped_end + 1):
                if p not in seen:
                    seen.add(p)
                    pages.append(p)
        else:
            if not token.isdigit():
                raise ValueError(f"Invalid --pages value: {token!r}")
            p = int(token)
            if p < 1 or p > page_count:
                raise ValueError(f"Requested page {p} out of range (1..{page_count})")
            if p not in seen:
                seen.add(p)
                pages.append(p)

    if not pages:
        raise ValueError(f"Invalid empty --pages specification: {spec!r}")
    return pages


def _split_fulltext_pages(text: str) -> dict[int, str]:
    """Split OCR fulltext.md by <!-- page N --> markers when present."""
    pages: dict[int, list[str]] = {}
    current_page: int | None = None
    for line in text.splitlines():
        m = _PAGE_MARKER_RE.match(line.strip())
        if m:
            current_page = int(m.group(1))
            pages.setdefault(current_page, [])
            continue
        if current_page is not None:
            pages[current_page].append(line)
    return {p: "\n".join(lines).strip() for p, lines in pages.items()}


def _filter_markdown_section(text: str, section_query: str) -> str:
    """Extract a markdown section matching *section_query* (case-insensitive)."""
    q = section_query.strip().lower()
    if not q:
        return text
    lines = text.splitlines()
    start_idx: int | None = None
    start_level = 7
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            heading_txt = stripped[hashes:].strip().lower()
            if q in heading_txt:
                start_idx = idx
                start_level = hashes
                break
    if start_idx is None:
        return ""
    out = [lines[start_idx]]
    for line in lines[start_idx + 1 :]:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if hashes <= start_level:
                break
        out.append(line)
    return "\n".join(out).strip()


def _clean_pdf_page_text(raw: str) -> str:
    lines = [ln.rstrip() for ln in (raw or "").splitlines()]
    cleaned = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def _read_full_or_pages(
    vault: Path,
    key: str,
    *,
    pages_spec: str = "",
    section: str = "",
    max_chars: int = 40000,
    source: str = "auto",
) -> tuple[dict | None, PFError | None]:
    paper = _lookup_paper_fallback(vault, key)
    if paper is None:
        return None, PFError(
            code=ErrorCode.PATH_NOT_FOUND,
            message="no readable source (paper not found, or no valid fulltext/PDF)",
        )

    ft = _resolve_fulltext_path(vault, paper) if source in ("auto", "fulltext") else None
    pdf = _resolve_pdf_file(vault, paper) if source in ("auto", "pdf") else None
    paper_key = paper["zotero_key"]

    content = ""
    src_label = ""
    page_count = 0
    pages_returned: list[int] = []

    if ft is not None:
        raw_ft = ft.read_text(encoding="utf-8")
        src_label = "ocr_fulltext"
        marked_pages = _split_fulltext_pages(raw_ft)
        if marked_pages:
            page_count = max(marked_pages.keys())
            if pages_spec.strip():
                target_pages = _parse_page_spec(pages_spec, page_count)
                chunks = [
                    f"--- Page {p} ---\n{marked_pages[p]}"
                    for p in target_pages
                    if p in marked_pages
                ]
                pages_returned = [p for p in target_pages if p in marked_pages]
                content = "\n\n".join(chunks)
            else:
                pages_returned = sorted(marked_pages.keys())
                content = raw_ft
        else:
            page_count = 1
            if pdf is not None:
                try:
                    import pymupdf

                    with pymupdf.open(str(pdf)) as doc:
                        page_count = doc.page_count or 1
                except Exception:  # noqa: BLE001
                    pass
            if pages_spec.strip():
                target_pages = _parse_page_spec(pages_spec, page_count)
                pages_returned = target_pages
            else:
                pages_returned = [1]
            content = raw_ft

        if section.strip():
            content = _filter_markdown_section(content, section)

    elif pdf is not None:
        try:
            import pymupdf
        except ImportError:  # pragma: no cover
            import fitz as pymupdf

        src_label = "native_pdf"
        with pymupdf.open(str(pdf)) as doc:
            page_count = doc.page_count
            target_pages = _parse_page_spec(pages_spec, page_count)
            chunks = []
            for p in target_pages:
                text = _clean_pdf_page_text(doc[p - 1].get_text("text") or "")
                chunks.append(f"--- Page {p} ---\n{text}")
            pages_returned = target_pages
            content = "\n\n".join(chunks)

        if section.strip():
            sec_low = section.strip().lower()
            matched_lines: list[str] = []
            capturing = False
            for line in content.splitlines():
                if line.startswith("--- Page "):
                    if capturing:
                        matched_lines.append(line)
                    continue
                if not capturing and sec_low in line.lower():
                    capturing = True
                if capturing:
                    matched_lines.append(line)
            if matched_lines:
                content = "\n".join(matched_lines).strip()
    else:
        return None, PFError(
            code=ErrorCode.PATH_NOT_FOUND,
            message="no readable source (paper not found, or no valid fulltext/PDF)",
        )

    truncated = False
    if max_chars > 0 and len(content) > max_chars:
        content = content[:max_chars]
        truncated = True

    return {
        "paper_key": paper_key,
        "source": src_label,
        "page_count": page_count,
        "pages_returned": pages_returned,
        "content": content,
        "truncated": truncated,
    }, None


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    key = args.key
    find = str(getattr(args, "find", "") or "")
    source = args.source

    if source not in VALID_SOURCES:
        result = PFResult(
            ok=False,
            command="read",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.ACTION_SCOPE_INVALID,
                message=f"invalid --source {source!r}: choose from {', '.join(VALID_SOURCES)}",
            ),
        )
        _emit(result, args.json)
        return 2

    if not find.strip():
        try:
            payload, err = _read_full_or_pages(
                vault,
                key,
                pages_spec=str(getattr(args, "pages", "") or ""),
                section=str(getattr(args, "section", "") or ""),
                max_chars=int(getattr(args, "max_chars", 40000) or 0),
                source=source,
            )
        except ValueError as exc:
            result = PFResult(
                ok=False,
                command="read",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
            )
            _emit(result, args.json)
            return 1
        except Exception as exc:  # noqa: BLE001
            result = PFResult(
                ok=False,
                command="read",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
            _emit(result, args.json)
            return 1

        if err is not None:
            result = PFResult(
                ok=False,
                command="read",
                version=PF_VERSION,
                error=err,
                data={"status": "no_readable_source", "paper_key": key},
            )
            _emit(result, args.json)
            return 1

        result = PFResult(ok=True, command="read", version=PF_VERSION, data=payload)
        _emit(result, args.json)
        return 0

    try:
        payload = read_paper_local(vault, key, find, source=source)
    except Exception as exc:  # noqa: BLE001 — boundary converts to structured error
        result = PFResult(
            ok=False,
            command="read",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        _emit(result, args.json)
        return 1

    if payload["status"] == "no_readable_source":
        result = PFResult(
            ok=False,
            command="read",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message="no readable source (paper not found, or no valid fulltext/PDF)",
            ),
            data={"status": "no_readable_source", "matches": []},
        )
        _emit(result, args.json)
        return 1

    result = PFResult(
        ok=True,
        command="read",
        version=PF_VERSION,
        data=payload,
    )
    _emit(result, args.json)
    return 0


def _emit(result: PFResult, json_output: bool) -> None:
    if json_output:
        print(result.to_json())
    elif result.ok:
        data = result.data or {}
        if "content" in data:
            print(
                f"read: {data.get('paper_key', '')} ({data.get('source', '')}, "
                f"pages={data.get('pages_returned', [])}/{data.get('page_count', 0)})"
            )
            print(data.get("content", ""))
            return
        status = data.get("status", "")
        print(f"read: {status}")
        for m in data.get("matches", []):
            where = (
                f"line {m['line']}"
                if m.get("line") is not None
                else f"page {m['page']}"
            )
            print(f"  [{m['source']} {where}] {m['text'][:300]}")
    else:
        print(f"Error: {result.error.message if result.error else 'unknown'}", file=sys.stderr)
