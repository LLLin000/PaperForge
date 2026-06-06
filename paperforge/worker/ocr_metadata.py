from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


def _clean_author_display(author_text: str) -> str:
    text = author_text
    text = re.sub(r"\$\s+\^", "$^", text)
    text = re.sub(r"\^\s+\{", "^{", text)
    text = re.sub(r"\}\s+\$", "}$", text)
    text = re.sub(r",(\s*)and(\s*)", r", and ", text)
    text = re.sub(r";(\s*)and(\s*)", r"; and ", text)
    text = re.sub(r"([,;:])\1+", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip().strip(";, ")
    return text.strip()


def _match_author_block_to_source_authors(block_text: str, source_authors: list[str]) -> dict:
    """Check if an OCR text block matches the source/Zotero author list.

    Normalizes both sides and computes Jaccard similarity on tokenized names.
    """
    normalized = block_text.lower()
    normalized = re.sub(r"\$?\^?\{[^}]*\}\$?", "", normalized)
    normalized = re.sub(r"[^\w\s,]", "", normalized)
    block_names = set()
    for part in re.split(r",\s*|\s+and\s+", normalized):
        part = part.strip()
        if part:
            block_names.add(part)

    source_names = set()
    for author in source_authors:
        s = author.lower().strip()
        s = re.sub(r"[^\w\s]", "", s)
        if s:
            source_names.add(s)

    if not block_names or not source_names:
        return {
            "matched": False,
            "similarity": 0.0,
            "block_names": sorted(block_names),
            "source_names": sorted(source_names),
        }

    intersection = block_names & source_names
    union = block_names | source_names
    similarity = len(intersection) / len(union)

    return {
        "matched": similarity > 0.5,
        "similarity": similarity,
        "block_names": sorted(block_names),
        "source_names": sorted(source_names),
    }


def _name_likeness_score(text: str) -> int:
    """Score how much the text looks like a human-name list vs affiliation/noise."""
    if not text:
        return 0
    score = 0
    if text.count(",") >= 1:
        score += text.count(",")
    if bool(re.search(r"[A-Z][a-z]+,\s+[A-Z]", text)):
        score += 3
    if bool(re.search(r"\band\b\s+[A-Z]", text)):
        score += 2
    if bool(re.search(r"[\*†‡§¶#]", text)):
        score += 1
    if any(kw in text.lower() for kw in ["university", "department", "institute", "college", "school of"]):
        score -= 5
    return score


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
                if candidates["authors_text"] is None:
                    candidates["authors_text"] = text
                else:
                    current_score = _name_likeness_score(candidates["authors_text"])
                    new_score = _name_likeness_score(text)
                    if new_score > current_score:
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
    _BACKMATTER_TITLE_DENY_LIST = {
        "generative ai statement",
        "acknowledgments",
        "acknowledgements",
        "funding",
        "conflict of interest",
        "competing interests",
        "data availability",
        "supplementary materials",
        "supplementary material",
        "author contributions",
        "declaration of competing interest",
        "credit authorship contribution statement",
        "ethical statement",
        "ethics statement",
        "institutional review board",
    }
    if ocr_title and ocr_title.lower().strip() in _BACKMATTER_TITLE_DENY_LIST:
        ocr_title = ""
    title_entry: dict[str, Any] = {
        "value": zotero_title or ocr_title,
        "source": "zotero" if zotero_title else ("ocr_frontmatter" if ocr_title else "unknown"),
    }
    title_entry["confidence"] = 0.99 if zotero_title else (0.7 if ocr_title else 0.3)
    alternatives = []
    if ocr_title and ocr_title != zotero_title:
        alternatives.append(
            {
                "value": ocr_title,
                "source": "ocr_frontmatter",
                "confidence": 0.7,
            }
        )
    if alternatives:
        title_entry["alternatives"] = alternatives
    resolved["title"] = title_entry

    # --- authors ---
    zotero_authors = source_metadata.get("authors", [])
    ocr_authors_text = frontmatter_candidates.get("authors_text", "")

    _INST_KEYWORDS = ["university", "department", "institute", "college", "school of"]

    def _is_affiliation_like(t: str) -> bool:
        return any(kw in t.lower() for kw in _INST_KEYWORDS)

    ocr_author_list = (
        [a.strip() for a in re.split(r",\s+(?=[A-Z])", ocr_authors_text) if a.strip()] if ocr_authors_text else []
    )

    if isinstance(zotero_authors, list) and len(zotero_authors) > 0:
        authors_entry: dict[str, Any] = {
            "value": zotero_authors,
            "source": "zotero",
            "confidence": 0.99,
        }
        if ocr_authors_text:
            alignment = _match_author_block_to_source_authors(ocr_authors_text, zotero_authors)
            authors_entry["alignment"] = {
                "matched": alignment["matched"],
                "similarity": alignment["similarity"],
            }
        resolved["authors"] = authors_entry
    elif ocr_author_list and not _is_affiliation_like(ocr_authors_text):
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

    # --- authors_display (cleaned string for UI) ---
    if isinstance(zotero_authors, list) and len(zotero_authors) > 0:
        resolved["authors_display"] = ", ".join(zotero_authors)
    elif ocr_authors_text and not _is_affiliation_like(ocr_authors_text):
        resolved["authors_display"] = _clean_author_display(ocr_authors_text)
    else:
        resolved["authors_display"] = ""

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
