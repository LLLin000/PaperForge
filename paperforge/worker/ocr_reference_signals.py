from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]+", " ", text)).strip().lower()


@lru_cache(maxsize=1)
def _journal_rows() -> list[dict]:
    raw = resources.files("paperforge.resources").joinpath("nlm_journal_abbreviations.json").read_text(encoding="utf-8")
    return json.loads(raw)


def _has_journal_match(text: str) -> bool:
    norm = _norm(text)
    for row in _journal_rows():
        for field in ("med_abbr", "iso_abbr", "canonical_title"):
            value = _norm(str(row.get(field) or ""))
            if value and value in norm:
                return True
    return False


def score_reference_entry(text: str) -> dict:
    text = str(text or "").strip()
    lower = text.lower()
    has_author_signature = bool(re.search(r"\b[A-Z][a-zA-Z'\-]+\s+[A-Z]{1,3}(?:,|\b)", text))
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", text))
    has_vol_pages = bool(re.search(r"\b\d+\s*\(\d+\)\s*:\s*[A-Za-z0-9\-]+", text) or re.search(r"\b\d+\s*:\s*[A-Za-z0-9\-]+", text))
    has_online = any(token in lower for token in ("[internet]", "available from", "doi:", "pmid:", "pmcid:", "published online", "cited "))
    has_report_markers = any(token in lower for token in ("guideline", "organization", "committee", "available from")) or "[internet]" in lower
    has_number_lead = bool(re.match(r"^\s*(\[\d+\]|\d+[\.)]?)(\s+|$)", text))
    journal_match = _has_journal_match(text)

    family = "unknown"
    confidence = 0.0
    if has_author_signature and has_year and (has_vol_pages or journal_match):
        family = "vancouver_structured_numbered" if has_number_lead else "vancouver_structured_unnumbered"
        confidence = 0.8 if journal_match else 0.65
    elif has_report_markers and has_year:
        family = "book_or_report"
        confidence = 0.7
    elif re.search(r"\b[A-Z][a-zA-Z'\-]+\s+[A-Z].*\((19|20)\d{2}\)", text):
        family = "author_year"
        confidence = 0.6
    return {
        "family": family,
        "confidence": confidence,
        "signals": {
            "author_signature": has_author_signature,
            "year_signature": has_year,
            "volume_issue_pages_signature": has_vol_pages,
            "online_marker_signature": has_online,
            "journal_lexicon_match": journal_match,
        },
    }
