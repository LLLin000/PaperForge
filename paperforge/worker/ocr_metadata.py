from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


def extract_frontmatter_candidates(blocks_structured_path: Path) -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "title": None,
        "authors_text": None,
        "doi_candidates": [],
    }

    if not blocks_structured_path.exists():
        return candidates

    with blocks_structured_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                block = json.loads(line)
            except json.JSONDecodeError:
                continue

            role = block.get("role", "")
            text = block.get("text", "").strip()

            if role == "paper_title":
                candidates["title"] = text
            elif role == "authors":
                candidates["authors_text"] = text
            elif role in ("affiliation",):
                if "affiliation_blocks" not in candidates:
                    candidates["affiliation_blocks"] = []
                candidates["affiliation_blocks"].append(text)
            elif role == "doi" and text:
                candidates["doi_candidates"].append(text)
            elif role == "frontmatter_heading":
                if "frontmatter_headings" not in candidates:
                    candidates["frontmatter_headings"] = []
                candidates["frontmatter_headings"].append(text)

    return candidates


def resolve_metadata(
    source_metadata: dict[str, Any],
    frontmatter_candidates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if frontmatter_candidates is None:
        frontmatter_candidates = {}

    resolved: dict[str, Any] = {}

    # --- title ---
    zotero_title = source_metadata.get("title", "")
    ocr_title = frontmatter_candidates.get("title", "")
    title_entry: dict[str, Any] = {
        "value": zotero_title or ocr_title,
        "source": "zotero" if zotero_title else ("ocr_frontmatter" if ocr_title else "unknown"),
    }
    title_entry["confidence"] = 0.99 if zotero_title else (0.7 if ocr_title else 0.3)
    alternatives = []
    if ocr_title and ocr_title != zotero_title:
        alternatives.append({
            "value": ocr_title,
            "source": "ocr_frontmatter",
            "confidence": 0.7,
        })
    if alternatives:
        title_entry["alternatives"] = alternatives
    resolved["title"] = title_entry

    # --- authors ---
    zotero_authors = source_metadata.get("authors", [])
    ocr_authors_text = frontmatter_candidates.get("authors_text", "")
    ocr_author_list = (
        [a.strip() for a in re.split(r",\s+(?=[A-Z])", ocr_authors_text) if a.strip()]
        if ocr_authors_text else []
    )

    if isinstance(zotero_authors, list) and len(zotero_authors) > 0:
        resolved["authors"] = {
            "value": zotero_authors,
            "source": "zotero",
            "confidence": 0.99,
        }
    elif ocr_author_list:
        resolved["authors"] = {
            "value": ocr_author_list,
            "source": "ocr_frontmatter",
            "confidence": 0.6,
        }
    else:
        resolved["authors"] = {
            "value": [],
            "source": "unknown",
            "confidence": 0.3,
        }

    # --- year ---
    zotero_year = source_metadata.get("year", 0)
    if zotero_year:
        resolved["year"] = {
            "value": zotero_year,
            "source": "zotero",
            "confidence": 0.99,
        }
    else:
        resolved["year"] = {
            "value": 0,
            "source": "unknown",
            "confidence": 0.3,
        }

    # --- journal ---
    zotero_journal = source_metadata.get("journal", "")
    if zotero_journal:
        resolved["journal"] = {
            "value": zotero_journal,
            "source": "zotero",
            "confidence": 0.99,
        }
    else:
        resolved["journal"] = {
            "value": "",
            "source": "unknown",
            "confidence": 0.3,
        }

    # --- DOI ---
    zotero_doi = source_metadata.get("doi", "")
    if zotero_doi:
        resolved["doi"] = {
            "value": zotero_doi,
            "source": "zotero",
            "confidence": 0.99,
        }
    else:
        doi_candidates = frontmatter_candidates.get("doi_candidates", [])
        if doi_candidates:
            resolved["doi"] = {
                "value": doi_candidates[0],
                "source": "ocr_frontmatter",
                "confidence": 0.6,
                "alternatives": [
                    {
                        "value": d,
                        "source": "ocr_frontmatter",
                        "confidence": 0.5,
                    }
                    for d in doi_candidates[1:]
                ],
            }
        else:
            resolved["doi"] = {
                "value": "",
                "source": "unknown",
                "confidence": 0.3,
            }

    # --- raw_frontmatter ---
    raw_fm: dict[str, Any] = {}
    if frontmatter_candidates.get("authors_text"):
        raw_fm["author_block"] = frontmatter_candidates["authors_text"]
    if frontmatter_candidates.get("affiliation_blocks"):
        raw_fm["affiliation_block"] = "\n".join(frontmatter_candidates["affiliation_blocks"])
    if resolved.get("title", {}).get("source") == "ocr_frontmatter" and frontmatter_candidates.get("title"):
        raw_fm["title_block"] = frontmatter_candidates["title"]
    if raw_fm:
        resolved["raw_frontmatter"] = raw_fm

    return resolved


def write_resolved_metadata(dst: Path, resolved: dict[str, Any]) -> None:
    write_json(dst, resolved)
