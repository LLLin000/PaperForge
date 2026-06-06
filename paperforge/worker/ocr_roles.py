from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RoleAssignment:
    role: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)


_HEADING_NUMBER_PATTERN = re.compile(
    r"^\d+(?:\.\d+)*\s+[A-Z]",
)

_FIGURE_PREFIX_PATTERN = re.compile(
    r"^(?:Figure|Fig\.?|Supplementary\s+Figure|Supplementary\s+Fig\.?|"
    r"Extended\s+Data\s+Figure|Extended\s+Data\s+Fig\.?)\s+\d+",
    flags=re.IGNORECASE,
)

_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+\d+",
    flags=re.IGNORECASE,
)

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

_BACKMATTER_HEADINGS = {
    "author contributions",
    "funding",
    "acknowledgments",
    "acknowledgements",
    "conflict of interest",
    "competing interests",
    "data availability",
    "supplementary materials",
    "supplementary material",
    "generative ai statement",
    "declaration of competing interest",
    "ethical statement",
    "ethics statement",
    "institutional review board",
    "credit authorship contribution statement",
    "publisher's note",
}

FRONTMATTER_NOISE = {
    "open access",
    "copyright",
    "citation",
    "keywords",
    "edited by",
    "reviewed by",
    "correspondence",
    "received",
    "accepted",
    "published",
    "present address",
    "these authors have contributed equally",
    "informed consent",
    "orcid",
}

_REFERENCE_PATTERN = re.compile(
    r"^\s*(?:\d+\.\s|[A-Z][A-Za-z'’\-]+\s+et al\.\s*\(\d{4}[a-z]?\)|\([A-Z][A-Za-z'’\-]+\s+et al\.,\s*\d{4}[a-z]?\))",
)

# citation line like "Masante B, Gabetti S, Silva JC, Putame G... and Massai D (2025)"
_CITATION_LINE_PATTERN = re.compile(
    r"^[A-Z][a-z]+\'?[a-z]* [A-Z](?:\.[, ]|[A-Z]\.?,|[,\s])",
)

# author list with superscript affiliation markers like "$^{1,2\dagger}$"
_AUTHOR_AFFILIATION_MARKER = re.compile(r"\$\s*\^\{")


def _has_heading_numbering(text: str) -> bool:
    return bool(_HEADING_NUMBER_PATTERN.match(text.strip()))


def _has_figure_prefix(text: str) -> bool:
    return bool(_FIGURE_PREFIX_PATTERN.match(text.strip()))


def _is_near_figure_media(block: dict, page_blocks: list[dict], max_gap: int = 200) -> bool:
    block_bbox = block.get("block_bbox", [0, 0, 0, 0])
    if not block_bbox or len(block_bbox) < 4:
        return False
    bx1, by1, bx2 = block_bbox[0], block_bbox[1], block_bbox[2]
    for other in page_blocks:
        label = str(other.get("block_label", "") or "").strip()
        if label not in {"image", "chart", "figure"}:
            continue
        ob = other.get("block_bbox", [0, 0, 0, 0])
        if not ob or len(ob) < 4:
            continue
        ox1, oy1, ox2, oy2 = ob[:4]
        h_overlap = bx1 < ox2 and ox1 < bx2
        if not h_overlap:
            continue
        gap = by1 - oy2
        if -max_gap * 0.3 <= gap <= max_gap:
            return True
    return False


def _has_table_prefix(text: str) -> bool:
    return bool(_TABLE_PREFIX_PATTERN.match(text.strip()))


def _looks_like_reference(text: str) -> bool:
    return bool(_REFERENCE_PATTERN.match(text.strip()))


def _is_backmatter_boundary_heading(block: dict, page_num: int, total_pages: int) -> bool:
    text = str(block.get("block_content", "") or block.get("text", "") or "").strip()
    if not text:
        return False

    # Relative tail position instead of absolute page gate
    if total_pages > 0 and (page_num / total_pages) < 0.5:
        return False

    raw_label = str(block.get("block_label", "") or "").strip()

    is_heading_label = raw_label == "paragraph_title"
    span_meta = block.get("span_metadata", {}) or {}
    is_visually_heading = False
    if isinstance(span_meta, dict):
        font_size = span_meta.get("size", 0) or 0
        font_flags = (span_meta.get("flags", "") or "").lower()
        is_visually_heading = ("bold" in font_flags and font_size >= 11) or font_size >= 14
    elif isinstance(span_meta, list):
        sizes = [s.get("size", 0) or 0 for s in span_meta if isinstance(s, dict)]
        bold_flags = any(s.get("flags", 0) & 16 for s in span_meta if isinstance(s, dict))
        avg_size = sum(sizes) / len(sizes) if sizes else 0
        is_visually_heading = bold_flags or avg_size >= 14

    if not (is_heading_label or is_visually_heading):
        return False

    upper = text.upper()
    has_container_words = (
        "ADDITIONAL" in upper or "SUPPLEMENTARY" in upper or "DECLARATION" in upper or "INFORMATION" in upper
    )

    # Span visual signal — boundary headings are typically bold 11pt+
    span_meta = block.get("span_metadata", {}) or {}
    if isinstance(span_meta, dict):
        font_size = span_meta.get("size", 0) or 0
        font_flags = (str(span_meta.get("flags", "") or "")).lower()
        is_visually_heading = ("bold" in font_flags and font_size >= 11) or font_size >= 14
    elif isinstance(span_meta, list):
        sizes = [s.get("size", 0) or 0 for s in span_meta if s.get("size")]
        flags = [s.get("flags", 0) for s in span_meta]
        mean_size = sum(sizes) / len(sizes) if sizes else 0
        is_bold = any(bool(f & 16) for f in flags if isinstance(f, int))
        is_text_bold = any("bold" in (str(s.get("flags", "") or "")).lower() for s in span_meta)
        is_visually_heading = ((is_bold or is_text_bold) and mean_size >= 11) or mean_size >= 14
    else:
        is_visually_heading = False

    if not is_visually_heading and not has_container_words:
        return False

    if len(text) <= 20:
        return False

    lower = text.lower()
    if lower in ("references", "bibliography"):
        return False
    if lower in _BACKMATTER_HEADINGS:
        return False
    return lower not in _BACKMATTER_TITLE_DENY_LIST


def _looks_like_author_list(text: str) -> bool:
    """Check if text looks like a list of author names (not a title or body)."""
    if not text:
        return False
    has_name_comma = bool(re.search(r"[A-Z][a-z]+,\s+[A-Z]", text))
    has_and_name = bool(re.search(r"\band\b\s+[A-Z][a-z]+", text))
    has_author_marker = bool(re.search(r"[\*†‡§¶#]", text))
    has_two_name_pairs = bool(re.search(r"[A-Z][a-z]+\s+[A-Z][a-z]+\s*[·•,;]\s*[A-Z][a-z]+", text))
    has_et_al = "et al" in text.lower()
    return (has_name_comma or has_and_name or has_author_marker or has_two_name_pairs or has_et_al) and len(text) < 500


def _looks_like_affiliation(text: str) -> bool:
    """Check if text looks like an affiliation block."""
    lower_txt = text.lower()
    inst_keywords = [
        "university",
        "department",
        "institute",
        "college",
        "school of",
        "faculty",
        "laboratory",
        "lab",
        "hospital",
        "center",
        "centre",
        "academy",
        "division",
        "initiative",
        "regenerative medicine",
        "research",
        "science",
        "technology",
        "medicine",
        "school of materials",
    ]
    has_inst = any(kw in lower_txt for kw in inst_keywords)
    has_city_country = bool(
        re.search(
            r"(?:,\s*)(?:USA|UK|China|Germany|France|Japan|Italy|Canada|"
            r"Australia|Brazil|India|Korea|Spain|Netherlands|Switzerland|"
            r"Sweden|Norway|Denmark|Austria|Belgium|Finland|Poland|"
            r"Russia|Mexico|Argentina|Singapore|Taiwan|Hong\s*Kong)",
            text,
        )
    )
    has_number_prefix = bool(re.match(r"^[\$\s]*\^?\d+\s*", text))
    has_superscript_number = bool(re.search(r"\$?\^\d+\$?", text))
    return has_inst or (has_city_country and has_number_prefix) or has_superscript_number


def _infer_heading_level(
    text: str,
    font_size: float = 0,
    role_profiles: dict | None = None,
    block: dict | None = None,
) -> str | None:
    """Infer heading level for unnumbered papers using text content heuristics
    and optional role span profiles.
    """
    if not text:
        return "section_heading"

    # Profile-based matching (preferred)
    if role_profiles and block:
        from paperforge.worker.ocr_profiles import extract_block_span_profile, compare_against_role_family
        block_profile = extract_block_span_profile(block)
        if block_profile:
            for candidate_role in (
                "section_heading",
                "subsection_heading",
                "sub_subsection_heading",
            ):
                fam = role_profiles.get(candidate_role)
                if fam and fam.get("quality") in ("strong", "moderate"):
                    match = compare_against_role_family(block_profile, fam)
                    if match["size_compatible"] and match["match_score"] > 0.6:
                        return candidate_role

    # Legacy heuristics (fallback when no profile data)
    upper_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    is_mostly_upper = upper_ratio > 0.7
    sentence_verbs = {" is ", " are ", " was ", " were ", " have ", " has ", " been "}
    has_sentence_verb = any(v in text.lower() for v in sentence_verbs)
    word_count = len(text.split())
    if is_mostly_upper and word_count >= 1 and not has_sentence_verb:
        return "section_heading"
    if word_count >= 2 and not has_sentence_verb:
        return "subsection_heading"
    if word_count == 1 and not has_sentence_verb:
        return "sub_subsection_heading"
    return "section_heading"


def _detect_frontmatter_zone(
    block: dict,
    page_blocks: list[dict],
    page_height: float,
    page_width: float,
    style_profiles: dict | None = None,
) -> str | None:
    """Detect frontmatter zone for a block on page 1.

    Returns one of: ``title_zone``, ``author_zone``, ``affiliation_zone``,
    ``journal_furniture_zone``, ``abstract_zone``, or ``None``.
    """
    page_num = block.get("page", 1) or 1
    if page_num > 1:
        return None

    bbox = block.get("block_bbox", [0, 0, 0, 0])
    if len(bbox) < 4:
        return None

    text = str(block.get("block_content", "") or "").strip()
    if not text:
        return None

    lower_txt = text.lower()
    raw_label = str(block.get("block_label", "") or "").strip()
    x1, y1, x2 = bbox[0], bbox[1], bbox[2]

    # --- abstract_zone ---
    if lower_txt.startswith("abstract") and len(text) < 30:
        return "abstract_zone"

    # --- journal_furniture_zone ---
    furniture_signals = [
        "submitted",
        "accepted",
        "published",
        "received",
        "copyright",
        "©",
        "doi:",
        "doi ",
        "https://doi.org",
        "academic editor",
        "how to cite",
        "to cite this article",
        "creative commons",
        "cc by",
        "cc license",
        "this is an open-access article",
        "reviewed by",
        "edited by",
        "present address",
    ]
    if any(s in lower_txt for s in furniture_signals):
        return "journal_furniture_zone"

    narrow_furniture = [
        "citation:",
        "correspondence",
        "orcid",
        "these authors contributed equally",
        "equal contribution",
        "additional information",
    ]
    if any(s in lower_txt for s in narrow_furniture):
        block_width = x2 - x1
        is_narrow = page_width > 0 and block_width < page_width * 0.35
        is_top_half = page_height > 0 and y1 < page_height * 0.5
        if is_narrow or is_top_half:
            return "journal_furniture_zone"

    # --- title_zone ---
    if page_height > 0 and y1 < page_height * 0.2:
        block_width = x2 - x1
        is_wide_enough = page_width <= 0 or block_width > page_width * 0.4
        if is_wide_enough and lower_txt not in _BACKMATTER_TITLE_DENY_LIST and not _looks_like_author_list(text):
            if raw_label in ("paragraph_title", "doc_title"):
                return "title_zone"
            if raw_label == "text" and len(text) < 80:
                return "title_zone"

    # --- author_zone ---
    if (
        page_height > 0
        and y1 < page_height * 0.4
        and _looks_like_author_list(text)
        and not _looks_like_affiliation(text)
    ):
        return "author_zone"

    # --- affiliation_zone ---
    if page_height > 0 and y1 < page_height * 0.6 and _looks_like_affiliation(text):
        return "affiliation_zone"

    return None


def assign_block_role(
    block: dict,
    page_blocks: list[dict],
    page_width: int = 0,
    page_height: int = 0,
    style_profiles: dict | None = None,
    role_profiles: dict | None = None,
) -> RoleAssignment:
    raw_label = str(block.get("block_label", "") or "").strip()
    text = str(block.get("block_content", "") or "").strip()

    # Figure / table caption patterns override any prior
    if _has_figure_prefix(text):
        if raw_label == "text":
            verb_patterns = ["shows", "illustrates", "depicts", "demonstrates", "presents", "summarizes"]
            has_verb = any(v in text.lower() for v in verb_patterns)
            sentence_markers = [" is ", " are ", " was ", " were "]
            has_sentence = any(m in text.lower() for m in sentence_markers)

            if has_verb and has_sentence:
                return RoleAssignment(
                    role="body_paragraph",
                    confidence=0.6,
                    evidence=[f"body reference to figure, not caption: {text[:60]}"],
                )

            is_long = len(text) > 80
            near_media = _is_near_figure_media(block, page_blocks)
            confidence = 0.9
            evidence_parts = [f"figure prefix matched: {text[:60]}"]
            if is_long:
                confidence = 0.65
                evidence_parts.append("long text, reduced confidence")
            if near_media:
                confidence = min(confidence + 0.25, 0.95)
                evidence_parts.append("near figure media assets")
            return RoleAssignment(
                role="figure_caption",
                confidence=confidence,
                evidence=evidence_parts,
            )
        return RoleAssignment(
            role="figure_caption",
            confidence=0.9,
            evidence=[f"figure prefix matched: {text[:60]}"],
        )

    if _has_table_prefix(text):
        return RoleAssignment(
            role="table_caption",
            confidence=0.9,
            evidence=[f"table prefix matched: {text[:60]}"],
        )

    # --- Page-1 frontmatter zone pre-filter ---
    page_num = block.get("page", 1) or 1
    zone = None
    if page_num == 1 and raw_label in ("paragraph_title", "text"):
        zone = _detect_frontmatter_zone(
            block,
            page_blocks,
            page_height,
            page_width,
            style_profiles,
        )

    if zone == "title_zone":
        lower_stripped = text.strip().lstrip("*•·-–—").lower()
        if lower_stripped not in _BACKMATTER_TITLE_DENY_LIST:
            return RoleAssignment(
                role="paper_title",
                confidence=0.8,
                evidence=[f"page-1 zone title_zone: {text[:60]}"],
            )

    if zone == "author_zone":
        return RoleAssignment(
            role="authors",
            confidence=0.8,
            evidence=[f"page-1 zone author_zone: {text[:60]}"],
        )

    if zone == "affiliation_zone":
        return RoleAssignment(
            role="affiliation",
            confidence=0.8,
            evidence=[f"page-1 zone affiliation_zone: {text[:60]}"],
        )

    if zone == "journal_furniture_zone":
        return RoleAssignment(
            role="frontmatter_noise",
            confidence=0.8,
            evidence=[f"page-1 zone journal_furniture_zone: {text[:60]}"],
        )

    # zone == "abstract_zone" → let existing logic handle

    # Paddle priors
    if raw_label == "paragraph_title":
        stripped = text.strip().lstrip("*•·-–—")
        lower = stripped.lower()
        if lower in FRONTMATTER_NOISE:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.9,
                evidence=[f"frontmatter noise: {text[:60]}"],
            )
        if lower == "abstract":
            return RoleAssignment(
                role="abstract_heading",
                confidence=0.95,
                evidence=["abstract heading"],
            )
        if lower in ("references", "bibliography"):
            return RoleAssignment(
                role="reference_heading",
                confidence=0.9,
                evidence=[f"references heading: {text[:60]}"],
            )
        # Backmatter heading detection (tail-zone + text evidence)
        # Known backmatter phrases on tail pages (page > 1) are unambiguous -
        # full-width headings are common in real papers, so geometric checks
        # are not used here.  Page-1 blocks with these phrases are frontmatter
        # noise (already caught above) or genuine backmatter that fell through.
        if lower in _BACKMATTER_HEADINGS:
            page_num = block.get("page", 1) or 1
            if page_num > 1:
                return RoleAssignment(
                    role="backmatter_heading",
                    confidence=0.8,
                    evidence=[f"backmatter heading on page {page_num}: {text[:60]}"],
                )
            return RoleAssignment(
                role="section_heading",
                confidence=0.5,
                evidence=[f"backmatter heading text on page 1, treated as section: {text[:60]}"],
            )
        # Backmatter boundary container heading (e.g. "ADDITIONAL INFORMATION AND DECLARATIONS")
        # Checked after specific heading detection but before numbered/generic fallback.
        _page_num = block.get("page", 1) or 1
        _total_pages = max((b.get("page", 1) or 1) for b in page_blocks) if page_blocks else _page_num
        if _is_backmatter_boundary_heading(block, _page_num, _total_pages):
            return RoleAssignment(
                role="backmatter_boundary_heading",
                confidence=0.7,
                evidence=[f"backmatter boundary heading: {text[:60]}"],
            )
        if _has_heading_numbering(text):
            return RoleAssignment(
                role="section_heading" if re.match(r"^\d+\s", text) else "subsection_heading",
                confidence=0.85,
                evidence=[f"paragraph_title label with numbering: {text[:60]}"],
            )
        bbox = block.get("block_bbox", [0, 0, 0, 0])
        page_num = block.get("page", 1) or 1
        if page_num <= 1:
            if bbox[1] < max(page_height, 1) * 0.25:
                if lower in _BACKMATTER_TITLE_DENY_LIST:
                    return RoleAssignment(
                    role="section_heading" if re.match(r"^\d+\s", text) else "subsection_heading",
                        confidence=0.5,
                        evidence=[f"backmatter title in title zone, treated as heading: {text[:60]}"],
                    )
                return RoleAssignment(
                    role="paper_title",
                    confidence=0.7,
                    evidence=[f"unnumbered paragraph_title in title zone on page 1: {text[:60]}"],
                )
            return RoleAssignment(
                role="section_heading",
                confidence=0.5,
                evidence=[f"unnumbered paragraph_title on page 1 outside title zone: {text[:60]}"],
            )
        level = _infer_heading_level(text)
        return RoleAssignment(
            role=level,
            confidence=0.6,
            evidence=[f"unnumbered paragraph_title, inferred level {level}: {text[:60]}"],
        )

    if raw_label == "figure_title":
        return RoleAssignment(
            role="figure_caption",
            confidence=0.9,
            evidence=[f"figure_title label: {text[:60]}"],
        )

    if raw_label in {"image", "chart", "table"}:
        return RoleAssignment(
            role="media_asset",
            confidence=0.85,
            evidence=[f"media label: {raw_label}"],
        )

    if raw_label == "header":
        return RoleAssignment(
            role="noise",
            confidence=0.9,
            evidence=["header label"],
        )

    if raw_label == "footer":
        return RoleAssignment(
            role="noise",
            confidence=0.9,
            evidence=["footer label"],
        )

    if raw_label == "number":
        return RoleAssignment(
            role="noise",
            confidence=0.9,
            evidence=["page number label"],
        )

    if raw_label == "abstract":
        return RoleAssignment(
            role="abstract_body",
            confidence=0.85,
            evidence=["abstract label from Paddle OCR"],
        )

    if raw_label == "reference_content":
        return RoleAssignment(
            role="reference_item",
            confidence=0.85,
            evidence=[f"reference content label: {text[:60]}"],
        )

    # text with reference-like pattern
    if _looks_like_reference(text):
        return RoleAssignment(
            role="reference_item",
            confidence=0.6,
            evidence=[f"reference-like pattern: {text[:60]}"],
        )

    # text -> body paragraph by default, but with lower confidence
    if raw_label == "text":
        stripped = text.strip().lstrip("*•·-–—_")
        lower_txt = stripped.lower()

        # Check for inline table HTML
        if text.strip().lower().startswith("<table"):
            return RoleAssignment(
                role="table_html",
                confidence=0.95,
                evidence=["inline table HTML"],
            )

        # Check for abstract heading (may appear as text block, not paragraph_title)
        if lower_txt.startswith("abstract") and len(text) < 30:
            return RoleAssignment(
                role="abstract_heading",
                confidence=0.85,
                evidence=[f"abstract heading from text block: {text[:40]}"],
            )

        # Check for copyright
        if "copyright" in lower_txt or "©" in text:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.85,
                evidence=[f"copyright text: {text[:60]}"],
            )

        # Check for email / ORCID / DOI patterns in first-page blocks
        if "@" in text and (".edu" in text.lower() or ".com" in text.lower() or ".org" in text.lower()):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.85,
                evidence=[f"contact/email: {text[:60]}"],
            )

        # Check for frontmatter noise phrases — demoted to weak fallback.
        # Backmatter-referring phrases (supplementary material, publisher's note)
        # are intentionally removed: they are valid backmatter headings and
        # should never suppress body text.  Tail ownership is resolved by
        # the renderer's multi-page tail spread, not by the role layer.
        noise_phrases = [
            "citation:",
            "to cite this article",
            "correspondence",
            "orcid",
            "these authors have contributed",
            "equal contribution",
        ]
        if any(phrase in lower_txt for phrase in noise_phrases):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.8,
                evidence=[f"frontmatter phrase: {text[:60]}"],
            )

        # Citation line like "Masante B, Gabetti S, ... and Surname (2025)"
        if _CITATION_LINE_PATTERN.match(stripped) and " and " in text and ")" in text:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.8,
                evidence=[f"citation line pattern: {text[:60]}"],
            )

        # Author list with superscript affiliation markers → authors, not noise
        # Distinguish from citation lines (which have year in parens) and
        # affiliation blocks (which have institutional keywords)
        has_year_parens = bool(re.search(r"\(\d{4}[a-z]?\)", text))
        has_inst_keyword = any(
            kw in lower_txt for kw in ["department", "university", "institute", "college", "school of"]
        )
        if (
            _AUTHOR_AFFILIATION_MARKER.search(text)
            and "," in text
            and not has_year_parens
            and not has_inst_keyword
            and len(text) < 500
        ):
            return RoleAssignment(
                role="authors",
                confidence=0.8,
                evidence=[f"author list with affiliation markers: {text[:60]}"],
            )

        # Affiliation block starting with superscript
        if _AUTHOR_AFFILIATION_MARKER.match(stripped) and any(
            kw in lower_txt for kw in ["department", "university", "institute", "college", "school of"]
        ):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.85,
                evidence=[f"affiliation block: {text[:60]}"],
            )

        # Keyword content block: short comma-separated list of terms (no full sentence)
        if (
            "," in text
            and not any(w in lower_txt for w in [" is ", " are ", " was ", " were "])
            and len(text.split(",")) >= 3
            and len(text) < 200
        ):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.7,
                evidence=[f"keyword-like block: {text[:60]}"],
            )

        # Existing noise startswith check
        if any(lower_txt.startswith(n) for n in FRONTMATTER_NOISE):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.7,
                evidence=[f"frontmatter noise text: {text[:60]}"],
            )
        if _has_heading_numbering(text) and len(text) < 80 and ". " not in text:
            bbox = block.get("block_bbox", [0, 0, 0, 0])
            x1, y1, x2 = bbox[0], bbox[1], bbox[2]
            block_width = x2 - x1
            in_top_80 = y1 < max(page_height, 1) * 0.8
            wide_enough = block_width > max(page_width, 1) * 0.3
            sentence_verbs = [" is ", " are ", " was ", " were ", " have ", " has ", " been "]
            no_sentence_verbs = not (len(text) > 50 and any(v in text.lower() for v in sentence_verbs))
            if in_top_80 and wide_enough and no_sentence_verbs:
                return RoleAssignment(
                    role="section_heading",
                    confidence=0.65,
                    evidence=[f"numbered text block: {text[:60]}"],
                )
        # References heading from text block
        if lower_txt in ("references", "bibliography") and len(text) < 30:
            return RoleAssignment(
                role="reference_heading",
                confidence=0.8,
                evidence=[f"references heading from text block: {text[:40]}"],
            )

        # Style-aware heading disambiguation — primary signal for unnumbered papers
        if style_profiles is not None and style_profiles:
            from paperforge.worker.ocr_render import _disambiguate_heading_role

            style_suggested = _disambiguate_heading_role(block, style_profiles, role_profiles=role_profiles)
            if style_suggested is not None:
                bbox = block.get("block_bbox", [0, 0, 0, 0])
                in_top_80 = page_height == 0 or (len(bbox) >= 4 and bbox[1] < page_height * 0.8)
                if in_top_80 and len(text) >= 5 and len(text) < 60 and ". " not in text:
                    return RoleAssignment(
                        role=style_suggested,
                        confidence=0.7,
                        evidence=[f"style-aware heading detection: role={style_suggested}, text={text[:40]}"],
                    )

        # Visual heading detection — use span_metadata if available
        span_meta = block.get("span_metadata", {}) or {}
        if isinstance(span_meta, dict):
            font_size = span_meta.get("size", 0) or 0
            font_flags = (str(span_meta.get("flags", "") or "")).lower()
            is_visually_prominent = ("bold" in font_flags and font_size >= 11) or font_size >= 14
        elif isinstance(span_meta, list):
            sizes = [s.get("size", 0) or 0 for s in span_meta if s.get("size")]
            mean_size = sum(sizes) / len(sizes) if sizes else 0
            all_flags = [s.get("flags", 0) for s in span_meta]
            is_bold = any(bool(f & 16) for f in all_flags if isinstance(f, int))
            font_size = mean_size
            font_flags = "bold" if is_bold else "normal"
            is_visually_prominent = (is_bold and mean_size >= 11) or mean_size >= 14
        else:
            font_size = 0
            font_flags = ""
            is_visually_prominent = False
        if is_visually_prominent and len(text) >= 5 and len(text) < 60 and ". " not in text:
            bbox = block.get("block_bbox", [0, 0, 0, 0])
            in_top_80 = page_height == 0 or (len(bbox) >= 4 and bbox[1] < page_height * 0.8)
            if in_top_80:
                heading_level = _infer_heading_level(text, font_size)
                return RoleAssignment(
                    role=heading_level,
                    confidence=0.65,
                    evidence=[f"heading-style text block: size={font_size}, flags={font_flags}, level={heading_level}, text={text[:40]}"],
                )

        # Backmatter boundary container heading detection for text blocks
        _pn2 = block.get("page", 1) or 1
        _tp2 = max((b.get("page", 1) or 1) for b in page_blocks) if page_blocks else _pn2
        if _is_backmatter_boundary_heading(block, _pn2, _tp2):
            return RoleAssignment(
                role="backmatter_boundary_heading",
                confidence=0.7,
                evidence=[f"backmatter boundary heading from text block: {text[:60]}"],
            )

        if len(text) < 20:
            return RoleAssignment(
                role="unknown_structural",
                confidence=0.3,
                evidence=["short text, uncertain role"],
            )
        return RoleAssignment(
            role="body_paragraph",
            confidence=0.6,
            evidence=["default body_paragraph for text label"],
        )

    # fallback
    return RoleAssignment(
        role="unknown_structural",
        confidence=0.2,
        evidence=[f"unrecognized label '{raw_label}'"],
    )
