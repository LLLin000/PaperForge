"""Local research-record provenance. A page locator is never a text match."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path, PureWindowsPath
from typing import Any, cast

from paperforge.worker.asset_index import read_index


def _relative_pdf(vault: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Source must be a vault-relative PDF path using / separators")
    if (Path(value).is_absolute() or PureWindowsPath(value).is_absolute()
            or re.search(r"[:#?\x00-\x1f]", value) or ".." in value.split("/")):
        raise ValueError("Absolute, protocol, traversal and fragment source paths are forbidden")
    resolved = (vault / value).resolve()
    if not resolved.is_relative_to(vault.resolve()) or resolved.suffix.lower() != ".pdf":
        raise ValueError("Source must remain inside this vault and identify a PDF")
    return resolved


def _paper_pdf(vault: Path, paper_id: str, value: object) -> Path:
    requested = _relative_pdf(vault, value)
    index = read_index(vault)
    items = index.get("items", []) if isinstance(index, dict) else index or []
    papers = [item for item in items if item.get("zotero_key") == paper_id]
    if len(papers) != 1:
        raise ValueError("Source paper identity is unavailable or ambiguous in the canonical index")
    canonical = papers[0].get("pdf_path", "")
    if canonical.startswith("[[") and canonical.endswith("]]"):
        canonical = canonical[2:-2]
    # Canonical paths may be absolute; untrusted record paths may not.
    canonical_path = Path(canonical)
    if not canonical_path.is_absolute():
        canonical_path = vault / canonical
    if not canonical or canonical_path.resolve() != requested:
        raise ValueError("Source does not belong to this paper's current canonical PDF")
    return requested


def _normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def _binding(excerpt: str, source: dict[str, Any]) -> str:
    fields = {field: source.get(field) for field in (
        "paper_id", "path", "physical_page", "printed_page", "basis", "anchor", "sha256",
    )}
    fields["excerpt"] = excerpt
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def source_provenance(vault: Path, paper_id: str, excerpt: str, source: object) -> dict[str, Any]:
    if source is None:
        return {"status": "unknown", "basis": "none"}
    if not isinstance(source, dict):
        return {"status": "invalid", "basis": "none", "reason": "Invalid source object"}
    basis = source.get("basis", "recorded")
    try:
        if source.get("paper_id") != paper_id:
            raise ValueError("Source paper linkage differs from the record")
        if basis not in ("recorded", "user_confirmed", "exact_text"):
            raise ValueError("Unsupported verification basis")
        pdf = _paper_pdf(vault, paper_id, source.get("path"))
        page = source.get("physical_page")
        if type(page) is not int or page < 1:
            raise ValueError("Physical page must be a 1-based integer")
        if source.get("binding") != _binding(excerpt, source):
            return {"status": "changed", "basis": basis, "reason": "Excerpt or source position changed; recheck required"}
        if not pdf.is_file():
            return {"status": "unavailable", "basis": basis, "reason": "PDF is missing; recheck required"}
        with pdf.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != source.get("sha256"):
            return {"status": "changed", "basis": basis, "reason": "PDF hash differs or is unbound; recheck required"}
        import pymupdf

        with pymupdf.open(pdf) as doc:
            if page > len(doc):
                raise ValueError("Physical page exceeds current PDF page count")
            if basis == "exact_text":
                anchor = source.get("anchor")
                if not isinstance(anchor, str) or not _normalize(anchor) or _normalize(anchor) != _normalize(excerpt):
                    raise ValueError("Exact anchor must equal the record excerpt after NFC/whitespace normalization")
                needle = _normalize(anchor)
                counts = [_normalize(cast(str, p.get_text("text"))).count(needle) for p in doc]
                evidence = {"normalization": "NFC and Unicode whitespace collapse", "anchor": anchor,
                            "physical_page": page, "sha256": digest, "occurrences": sum(counts)}
                if sum(counts) != 1 or counts[page - 1] != 1:
                    return {"status": "ambiguous" if sum(counts) > 1 else "mismatch", "basis": basis,
                            "reason": "Anchor must occur exactly once in this PDF, on the selected physical page",
                            "evidence": evidence}
                return {"status": "matched", "basis": basis, "evidence": evidence}
        return {"status": "confirmed" if basis == "user_confirmed" else "recorded", "basis": basis,
                "evidence": {"sha256": digest, "physical_page": page}}
    except (ValueError, OSError, RuntimeError) as exc:
        return {"status": "invalid", "basis": basis, "reason": str(exc)}


def capture_source(vault: Path, paper_id: str, excerpt: str, requested: object) -> dict[str, Any]:
    if not isinstance(requested, dict):
        raise ValueError("Source must be a JSON object")
    pdf = _paper_pdf(vault, paper_id, requested.get("path"))
    page = requested.get("physical_page")
    if type(page) is not int or page < 1:
        raise ValueError("Physical page must be a 1-based integer")
    printed = requested.get("printed_page", "")
    source: dict[str, Any] = {"paper_id": paper_id, "path": requested["path"], "physical_page": page,
              "printed_page": "" if printed is None else str(printed),
              "basis": requested.get("basis", "recorded"), "anchor": requested.get("anchor", excerpt),
              "sha256": None}
    if pdf.is_file():
        with pdf.open("rb") as stream:
            source["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    source["binding"] = _binding(excerpt, source)
    provenance = source_provenance(vault, paper_id, excerpt, source)
    if provenance["status"] == "invalid":
        raise ValueError(provenance["reason"])
    source["verification"] = provenance
    return source
