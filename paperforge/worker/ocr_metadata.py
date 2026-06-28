from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json

_AUTHOR_SUPERSCRIPT_PATTERN = re.compile(r'\$\s*\^\{[^}]*\}')


def _normalize_author_tokens(name: str) -> list[str]:
    """Split author name into tokens, stripping superscripts and punctuation."""
    cleaned = _AUTHOR_SUPERSCRIPT_PATTERN.sub('', name)
    cleaned = re.sub(r'[•·*+†‡§¶#▲▼◄►◆◇○●□■△▽]', '', cleaned)
    return [t.strip('. ,') for t in re.split(r'\s+', cleaned.strip()) if t.strip('. ,')]


def _initials_match(short_name: str, full_name: str) -> bool:
    """Check if 'A. Yoo' initials match 'Ami Yoo' or 'W. H. Marks' matches 'William H. Marks'."""
    short = _normalize_author_tokens(short_name)
    full = _normalize_author_tokens(full_name)
    if not short or not full:
        return False
    short_last = short[-1].lower()
    full_last = full[-1].lower()
    if short_last != full_last:
        return False
    short_given = short[:-1]
    full_given = full[:-1]
    if not short_given or not full_given:
        return True
    if len(short_given) > len(full_given):
        return False
    for s, f in zip(short_given, full_given):
        if not s or not f:
            return False
        if s[0].upper() != f[0].upper():
            return False
    return True


def _normalize_author_name(name: str) -> str:
    """Normalize author name for fuzzy matching — strip special chars."""
    name = re.sub(r'\$\s*\^\{[^}]*\}\$?', '', name)
    name = re.sub(r'[•·∗*†‡§¶#▲▼◄►◆◇○●□■△▽]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


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
    For multiple authors, also supports initial matching (e.g., "A. Yoo" matches "Ami Yoo").
    """
    # Strip trailing labels that OCR sometimes merges into author blocks
    _strip_labels = ("abstract", "keywords", "key words", "highlights", "summary")
    clean_text = block_text
    for label in _strip_labels:
        idx = clean_text.lower().rfind(label)
        if idx > 0:
            clean_text = clean_text[:idx].strip()

    normalized = _normalize_author_name(clean_text).lower()
    normalized = re.sub(r"\$?\^?\{[^}]*\}\$?", "", normalized)
    # Normalize ampersand to "and" before stripping non-word chars
    normalized = normalized.replace("&", " and ")
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
    similarity = len(intersection) / len(union) if union else 0.0

    # Accept if all source names appear in the block (source is subset of block)
    source_subset_match = source_names.issubset(block_names)

    # Initial matching: for each source name, check if any block name shares
    # the same last name and first initial (e.g., "a yoo" matches "ami yoo")
    def _initials_match(sn: str, bn: str) -> bool:
        sn_parts = sn.split()
        bn_parts = bn.split()
        if len(sn_parts) < 2 or len(bn_parts) < 2:
            return False
        # Last name must match exactly
        if sn_parts[-1] != bn_parts[-1]:
            return False
        # First initial: first char of first name
        return sn_parts[0][0] == bn_parts[0][0]

    initial_match_count = sum(
        1 for sn in source_names
        if any(_initials_match(sn, bn) for bn in block_names)
    )
    # Accept if all source names match OR at least 3 initial matches
    # (OCR may truncate authors at end of block)
    initial_match = len(source_names) > 0 and (
        initial_match_count == len(source_names) or initial_match_count >= 3
    )

    return {
        "matched": similarity > 0.5 or source_subset_match or initial_match,
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


def _get_ocr_author_names(structured_blocks: list[dict]) -> list[str]:
    """Extract author names from the OCR authors block."""
    for b in structured_blocks:
        if b.get("role") == "authors":
            text = str(b.get("text", "")).replace('\n', ' ')
            names = []
            for part in re.split(r'[,;]', text):
                name = _AUTHOR_SUPERSCRIPT_PATTERN.sub('', part).strip()
                name = re.sub(r'\s+', ' ', name)
                if name and len(name) > 2:
                    if not re.match(r'^[\d\s]+$', name):
                        names.append(name)
            return names
    return []


def extract_frontmatter_candidates_from_blocks(structured_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "title": None,
        "authors_text": None,
        "doi_candidates": [],
    }

    for block in structured_blocks:
        role = block.get("role", "")
        text = block.get("text", "").strip()

        if role == "paper_title":
            candidates["title"] = text
        elif role == "authors":
            if block.get("_non_body_insert"):
                continue
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


def extract_frontmatter_candidates(blocks_structured_path: Path) -> dict[str, Any]:
    if not blocks_structured_path.exists():
        return {"title": None, "authors_text": None, "doi_candidates": []}

    structured_blocks: list[dict[str, Any]] = []
    with blocks_structured_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                block = json.loads(line)
            except json.JSONDecodeError:
                continue
            structured_blocks.append(block)

    return extract_frontmatter_candidates_from_blocks(structured_blocks)


def _token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-zA-Z0-9]+", a))
    tb = set(re.findall(r"[a-zA-Z0-9]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _align_frontmatter_to_source_metadata(
    source_meta: dict,
    page_blocks: list[dict],
    frontmatter_window: int = 3,
) -> dict:
    """Search blocks within the frontmatter window to localize title/authors.

    Source metadata is canonical truth; OCR blocks provide alignment/localization
    evidence only.  Blocks beyond *frontmatter_window* (default 3 pages) are
    excluded to avoid matching running headers, body text, or reference entries.
    """
    window_blocks = [
        b for b in page_blocks
        if int(b.get("page", 0) or 0) <= frontmatter_window
    ] if page_blocks else page_blocks

    result: dict[str, Any] = {}

    source_title = (source_meta.get("title") or "").strip()
    if source_title:
        result["title"] = {"source": "zotero", "value": source_title}
        for b in window_blocks:
            t = (b.get("text") or b.get("block_content") or "").strip()
            if len(t) >= 5 and (
                t in source_title or source_title in t
                or _token_overlap(t.lower(), source_title.lower()) > 0.6
            ):
                result["title"]["ocr_block_id"] = b.get("block_id")
                result["title"]["ocr_page"] = b.get("page")
                result["title"]["ocr_aligned"] = True
                break

    source_authors = source_meta.get("authors") or []
    if source_authors:
        result["authors"] = {"source": "zotero", "value": source_authors}
        for b in window_blocks:
            t = (b.get("text") or b.get("block_content") or "").strip()
            match = _match_author_block_to_source_authors(t, source_authors)
            if match.get("matched"):
                result["authors"]["ocr_block_id"] = b.get("block_id")
                result["authors"]["ocr_page"] = b.get("page")
                result["authors"]["ocr_aligned"] = True
                break

    source_doi = (source_meta.get("doi") or "").strip()
    if source_doi:
        result["doi"] = {"source": "zotero", "value": source_doi}
        normalized_source_doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", source_doi, flags=re.IGNORECASE)
        for b in window_blocks:
            t = (b.get("text") or b.get("block_content") or "").strip()
            normalized_block = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", t, flags=re.IGNORECASE)
            if normalized_block and normalized_source_doi and normalized_source_doi.lower() in normalized_block.lower():
                result["doi"]["ocr_block_id"] = b.get("block_id")
                result["doi"]["ocr_aligned"] = True
                break

    return result


def build_source_backed_frontmatter_anchors(
    source_meta: dict,
    page_blocks: list[dict],
    frontmatter_window: int = 3,
) -> dict[str, dict[str, Any]]:
    """Build early source-backed OCR anchors for frontmatter localization."""
    aligned = _align_frontmatter_to_source_metadata(
        source_meta,
        page_blocks,
        frontmatter_window=frontmatter_window,
    )

    anchors: dict[str, dict[str, Any]] = {}
    for field in ("title", "authors", "doi"):
        entry = aligned.get(field)
        if not isinstance(entry, dict):
            continue
        anchors[f"{field}_source_anchor"] = {
            "status": "ACCEPT" if entry.get("ocr_aligned") else "SOURCE_ONLY",
            "field": field,
            "source": entry.get("source", "zotero"),
            "value": entry.get("value"),
            "ocr_block_id": entry.get("ocr_block_id"),
            "ocr_page": entry.get("ocr_page"),
            "frontmatter_window": frontmatter_window,
        }
    return anchors


def resolve_metadata(
    source_metadata: dict[str, Any],
    frontmatter_candidates: dict[str, Any] | None = None,
    page_blocks: list[dict] | None = None,
    structured_blocks: list[dict] | None = None,
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
    authors_incomplete = source_metadata.get("authors_incomplete", False)
    authors_source = source_metadata.get("authors_source", "")
    ocr_authors_text = frontmatter_candidates.get("authors_text", "")

    _INST_KEYWORDS = ["university", "department", "institute", "college", "school of"]

    def _is_affiliation_like(t: str) -> bool:
        return any(kw in t.lower() for kw in _INST_KEYWORDS)

    ocr_author_list = (
        [a.strip() for a in re.split(r",\s+(?=[A-Z])", ocr_authors_text) if a.strip()] if ocr_authors_text else []
    )

    if isinstance(zotero_authors, list) and len(zotero_authors) > 0 and not authors_incomplete and authors_source != "paper_note.first_author_fallback":
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
        resolved["authors_display"] = ", ".join(zotero_authors)
    elif structured_blocks and source_metadata.get("first_author"):
        ocr_author_names = _get_ocr_author_names(structured_blocks)
        first_auth = str(source_metadata.get("first_author", ""))
        if ocr_author_names:
            matched = any(_initials_match(first_auth, oa) for oa in ocr_author_names)
            if matched:
                resolved["authors"] = {
                    "value": ocr_author_names,
                    "source": "ocr_blocks_verified_by_first_author",
                    "confidence": 0.85,
                }
                resolved["authors_display"] = ", ".join(ocr_author_names)
            else:
                resolved["authors"] = {
                    "value": [first_auth],
                    "source": "paper_note.first_author_fallback",
                    "confidence": 0.4,
                }
                resolved["authors_incomplete"] = True
                resolved["authors_display"] = first_auth
        else:
            resolved["authors"] = {
                "value": [first_auth],
                "source": "paper_note.first_author_fallback",
                "confidence": 0.4,
            }
            resolved["authors_incomplete"] = True
            resolved["authors_display"] = first_auth
    elif ocr_author_list and not _is_affiliation_like(ocr_authors_text):
        resolved["authors"] = {
            "value": ocr_author_list,
            "source": "ocr_frontmatter",
            "confidence": 0.6,
        }
        resolved["authors_display"] = _clean_author_display(ocr_authors_text)
    else:
        resolved["authors"] = {
            "value": [],
            "source": "unknown",
            "confidence": 0.3,
        }
        resolved["authors_display"] = ""

    # --- frontmatter alignment (OCR localization across all frontmatter pages) ---
    if page_blocks:
        alignment = _align_frontmatter_to_source_metadata(source_metadata, page_blocks)
        if "title" in resolved and "title" in alignment and alignment["title"].get("ocr_aligned"):
            resolved["title"]["ocr_block_id"] = alignment["title"]["ocr_block_id"]
            resolved["title"]["ocr_aligned"] = True
        if "authors" in resolved and "authors" in alignment and alignment["authors"].get("ocr_aligned"):
            resolved["authors"]["ocr_block_id"] = alignment["authors"]["ocr_block_id"]
            resolved["authors"]["ocr_aligned"] = True

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
