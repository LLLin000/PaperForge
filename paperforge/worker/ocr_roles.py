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


def _has_table_prefix(text: str) -> bool:
    return bool(_TABLE_PREFIX_PATTERN.match(text.strip()))


def _looks_like_reference(text: str) -> bool:
    return bool(_REFERENCE_PATTERN.match(text.strip()))


def assign_block_role(
    block: dict,
    page_blocks: list[dict],
    page_width: int = 0,
    page_height: int = 0,
    style_profiles: dict | None = None,
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
            is_long = len(text) > 80

            if (has_verb and has_sentence) or is_long:
                return RoleAssignment(
                    role="body_paragraph",
                    confidence=0.6,
                    evidence=[f"body reference to figure, not caption: {text[:60]}"],
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
                        role="section_heading",
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
        return RoleAssignment(
            role="section_heading",
            confidence=0.6,
            evidence=[f"unnumbered paragraph_title on page {page_num}, treated as heading: {text[:60]}"],
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
                    role="section_heading" if re.match(r"^\d+\s", text) else "subsection_heading",
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

        # Style-aware heading disambiguation (Task 5)
        if style_profiles is not None and style_profiles:
            from paperforge.worker.ocr_render import _disambiguate_heading_role

            style_suggested = _disambiguate_heading_role(block, style_profiles)
            if style_suggested is not None:
                bbox = block.get("block_bbox", [0, 0, 0, 0])
                in_top_80 = page_height == 0 or (len(bbox) >= 4 and bbox[1] < page_height * 0.8)
                if in_top_80 and len(text) >= 5 and len(text) < 60 and ". " not in text:
                    return RoleAssignment(
                        role=style_suggested,
                        confidence=0.65,
                        evidence=[f"style-aware heading detection: role={style_suggested}, text={text[:40]}"],
                    )

        # Visual heading detection: large or bold text blocks (fallback thresholds)
        span_meta = block.get("span_metadata", {}) or {}
        if isinstance(span_meta, dict):
            font_size = span_meta.get("size", 0) or 0
            font_flags = (span_meta.get("flags", "") or "").lower()
        else:
            font_size = 0
            font_flags = ""
        is_visually_prominent = (font_size >= 12 and "bold" in font_flags) or font_size >= 14
        if is_visually_prominent and len(text) >= 5 and len(text) < 60 and ". " not in text:
            bbox = block.get("block_bbox", [0, 0, 0, 0])
            in_top_80 = page_height == 0 or (len(bbox) >= 4 and bbox[1] < page_height * 0.8)
            if in_top_80:
                return RoleAssignment(
                    role="section_heading",
                    confidence=0.65,
                    evidence=[f"heading-style text block: size={font_size}, flags={font_flags}, text={text[:40]}"],
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
