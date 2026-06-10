from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RoleAssignment:
    role: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)


_HEADING_NUMBER_PATTERN = re.compile(
    r"^\d+(?:\.\d+)*\.?\s+[A-Z]",
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

_PREPROOF_MARKER = re.compile(
    r"^(?:journal\s+)?pre-?proof\b",
    re.IGNORECASE,
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

_FRONTIERS_FIGURE_TITLE_PATTERN = re.compile(
    r"^FIGURE\s+\d+[A-Za-z]?\s*\|\s+.+",
    flags=re.IGNORECASE,
)

_PANEL_LABEL_PATTERN = re.compile(
    r"^\(?[A-Z]\)?[\.:]?$",
)

_ROMAN_SECTION_PATTERN = re.compile(
    r"^(?:[IVXLCDM]+)\.\s+[A-Z][A-Z0-9 ,;:\-/()]+$",
    re.IGNORECASE,
)

_ALPHA_SUBSECTION_PATTERN = re.compile(
    r"^[A-Z]\.\s+[A-Z][A-Za-z0-9 ,;:\-/()]+$",
)

_COMMON_SECTION_HEADINGS = {
    "introduction",
    "materials and methods",
    "methods",
    "results",
    "results and discussion",
    "discussion",
    "conclusion",
    "conclusions",
}

# citation line like "Masante B, Gabetti S, Silva JC, Putame G... and Massai D (2025)"
_CITATION_LINE_PATTERN = re.compile(
    r"^[A-Z][a-z]+\'?[a-z]* [A-Z](?:\.[, ]|[A-Z]\.?,|[,\s])",
)

# author list with superscript affiliation markers like "$^{1,2\dagger}$"
_AUTHOR_AFFILIATION_MARKER = re.compile(r"\$\s*\^\{")


def _has_heading_numbering(text: str) -> bool:
    return bool(_HEADING_NUMBER_PATTERN.match(text.strip()))


def _heading_number_depth(text: str) -> int:
    match = re.match(r"^(\d+(?:\.\d+)*\.?)\s+", text.strip())
    if not match:
        return 0
    token = match.group(1).rstrip(".")
    return len([part for part in token.split(".") if part])


def is_preproof_marker(text: str) -> bool:
    return bool(_PREPROOF_MARKER.match(text.strip()))


def _has_figure_prefix(text: str) -> bool:
    return bool(_FIGURE_PREFIX_PATTERN.match(text.strip()))


def _is_obviously_formal_figure_caption(text: str, block: dict, page_blocks: list[dict]) -> bool:
    if not _has_figure_prefix(text):
        return False
    verb_patterns = ["shows", "illustrates", "depicts", "demonstrates", "presents", "summarizes"]
    has_verb = any(v in text.lower() for v in verb_patterns)
    sentence_markers = [" is ", " are ", " was ", " were "]
    has_sentence = any(m in text.lower() for m in sentence_markers)
    if has_verb and has_sentence:
        return False
    is_short = len(text) <= 80
    near_media = _is_near_figure_media(block, page_blocks)
    return is_short or near_media


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


def _is_textual_table(text: str) -> bool:
    """Check if a table-formatted block is really a textual list/box.

    Returns True if the text:
    - has no HTML table markup
    - has bullet-like lines (*, -, \u2022, digits.)
    - or has lines that are too varied to be a real table
    """
    if text.lower().startswith("<table"):
        return False
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) == 0:
        return False
    bullet_count = sum(1 for l in lines if l.startswith(("\u2022", "-", "*")) or (l[0].isdigit() and ". " in l[:4]))
    return bullet_count >= 2


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

    if not is_heading_label and not is_visually_heading:
        return False

    upper = text.upper()
    has_container_words = (
        "ADDITIONAL" in upper or "SUPPLEMENTARY" in upper or "DECLARATION" in upper or "INFORMATION" in upper
    )

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
    """Check if text looks like an affiliation block.

    Affiliation blocks typically contain institution names, addresses,
    and superscript markers.  Common academic words like ``science``,
    ``technology``, ``research``, ``medicine`` are NOT used because they
    appear in every body paragraph.
    """
    lower_txt = text.lower()
    # Only genuinely affiliation-specific keywords
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
    ]
    kw_matches = sum(1 for kw in inst_keywords if kw in lower_txt)
    has_inst = kw_matches >= 2 or (kw_matches >= 1 and len(text) < 80)
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
    has_curly_superscript = bool(re.search(r"\$?\^\{", text))
    return (
        has_inst
        or (has_city_country and has_number_prefix)
        or has_superscript_number
        or (has_curly_superscript and has_inst)
        or (has_curly_superscript and has_city_country)
    )


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
        from paperforge.worker.ocr_profiles import compare_against_role_family, extract_block_span_profile

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


def _seems_like_authors(text: str) -> bool:
    parts = [p.strip() for p in text.replace("  ", " ").split(",")]
    if len(parts) >= 2:
        name_count = sum(1 for p in parts if re.search(r"[A-Z][a-z]+\s+[A-Z]", p))
        return name_count >= 2
    return False


def _explicit_scholarly_heading_role(text: str) -> str | None:
    stripped = text.strip().lstrip("*•·-–—")
    lower = stripped.lower()
    if lower in _COMMON_SECTION_HEADINGS:
        return "section_heading"
    if _ROMAN_SECTION_PATTERN.match(stripped):
        return "section_heading"
    if _ALPHA_SUBSECTION_PATTERN.match(stripped):
        return "subsection_heading"
    return None


def _resolve_late_family_context(block: dict, families: dict | None) -> tuple[dict, str, str, str, str]:
    block_id = str(block.get("block_id") or "")
    family_ctx = {}
    if isinstance(families, dict):
        family_ctx = families.get(block_id) or {}

    block_zone = str(block.get("zone") or "")
    block_style_family = str(block.get("style_family") or "")
    block_style_family_authority = str(block.get("style_family_authority") or "")
    zone = block_zone or str(family_ctx.get("zone") or "")
    style_family = block_style_family or str(family_ctx.get("style_family") or "")
    style_family_authority = block_style_family_authority or str(
        family_ctx.get("style_family_authority") or family_ctx.get("authority") or ""
    )
    context_source = "block"
    if (not block_zone or not block_style_family or not block_style_family_authority) and family_ctx:
        context_source = "families"
    return family_ctx, zone, style_family, style_family_authority, context_source


def _looks_like_late_figure_narrative_prose(text: str) -> bool:
    if not text:
        return False
    sentence_count = text.count(". ") + text.count(".\n")
    if sentence_count >= 2:
        return True
    lower = text.lower()
    prose_markers = ["we ", "our ", "this study", "here we", "in this"]
    if any(marker in lower for marker in prose_markers):
        return True
    if re.search(
        r"\b(?:figure|fig\.?)\s+\d+[a-z]?\s+(?:shows|show|shown|demonstrates|demonstrate|illustrates|illustrate|depicts|presents|reveals|indicates|compares|summarizes)\b",
        lower,
    ):
        return True
    return bool(re.search(r"\$?\^\{[^}]+\}\$?", text) and sentence_count >= 1)


def resolve_final_role(
    block: dict,
    anchors: dict | None = None,
    families: dict | None = None,
) -> RoleAssignment:
    """Resolve a late-stage role using normalized zone/family context.

    This is intentionally narrow for the current task: eager role assignment
    remains the seed, but late structural context can override obviously wrong
    body defaults.
    """
    anchors = anchors or {}
    family_ctx, zone, style_family, style_family_authority, context_source = _resolve_late_family_context(
        block, families
    )
    marker_signature = block.get("marker_signature") or {}
    marker_type = str(marker_signature.get("type") or "none")
    current_role = str(block.get("role") or "body_paragraph")
    current_confidence = float(block.get("role_confidence") or 0.6)

    # When role is 'unassigned', fall back to seed_role (the eager assignment
    # stored during assign_block_role).  This ensures late resolution sees a
    # meaningful role rather than the bare sentinel.
    if current_role == "unassigned":
        seed_role = str(block.get("seed_role") or "")
        if seed_role:
            current_role = seed_role
            current_confidence = float(block.get("seed_confidence") or current_confidence)
    body_anchor = anchors.get("body_family_anchor") or {}
    reference_anchor = anchors.get("reference_family_anchor") or {}
    body_anchor_accepted = str(body_anchor.get("status") or "").upper() == "ACCEPT"
    reference_anchor_accepted = str(reference_anchor.get("status") or "").upper() == "ACCEPT"
    in_body_zone = zone == "body_zone"
    strong_legend_authority = style_family_authority in {"figure_marker", "figure_family_anchor"}

    if current_role == "body_paragraph":
        if (
            zone == "reference_zone"
            and reference_anchor_accepted
            and style_family == "reference_like"
            and marker_type
            in {
                "reference_numeric_bracket",
                "reference_numeric_dot",
                "reference_numeric_parenthesis",
                "reference_pattern",
                "citation_line",
            }
        ):
            return RoleAssignment(
                role="reference_item",
                confidence=max(current_confidence, 0.82),
                evidence=[
                    "late role resolution: reference_like family + reference zone",
                    f"style_family_authority={style_family_authority or 'none'}",
                    f"context_source={context_source}",
                ],
            )
        if (
            in_body_zone
            and body_anchor_accepted
            and strong_legend_authority
            and style_family == "legend_like"
            and marker_type == "figure_number"
            and not _looks_like_late_figure_narrative_prose(str(block.get("text") or ""))
        ):
            return RoleAssignment(
                role="figure_caption_candidate",
                confidence=max(current_confidence, 0.78),
                evidence=[
                    "late role resolution: legend_like family + figure_number marker",
                    f"zone={zone or 'unknown'}",
                    f"body_anchor={str(body_anchor.get('status') or 'none').lower()}",
                    f"style_family_authority={style_family_authority or 'none'}",
                    f"context_source={context_source}",
                ],
            )
        if (
            zone == "display_zone"
            and strong_legend_authority
            and style_family == "legend_like"
            and marker_type == "figure_number"
            and not _looks_like_late_figure_narrative_prose(str(block.get("text") or ""))
        ):
            return RoleAssignment(
                role="figure_caption_candidate",
                confidence=max(current_confidence, 0.8),
                evidence=[
                    "late role resolution: display-zone legend candidate from figure family",
                    f"style_family_authority={style_family_authority or 'none'}",
                    f"context_source={context_source}",
                ],
            )

    return RoleAssignment(
        role=current_role,
        confidence=current_confidence,
        evidence=[],
    )


def assign_block_role(
    block: dict,
    page_blocks: list[dict],
    page_width: int = 0,
    page_height: int = 0,
    style_profiles: dict | None = None,
    role_profiles: dict | None = None,
) -> RoleAssignment:
    from paperforge.worker.ocr_document import _page_still_frontmatter

    raw_label = str(block.get("block_label") or block.get("raw_label") or "").strip()
    text = str(block.get("block_content") or block.get("text") or "").strip()

    if _PREPROOF_MARKER.match(text):
        bbox = block.get("block_bbox") or block.get("bbox") or [0, 0, 0, 0]
        y_top = bbox[1] if len(bbox) >= 4 else 0
        page_num = int(block.get("page", 0) or 0)
        page_h = float(block.get("page_height") or page_height or 1700)
        page_w = float(block.get("page_width") or page_width or 1200)
        block_width = (bbox[2] - bbox[0]) if len(bbox) >= 4 else 0

        # Running header on any page — pre-proof text at extreme top is page furniture
        if y_top < page_h * 0.06:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.98,
                evidence=[f"journal pre-proof running header suppressed: p{page_num} y={y_top:.0f}/{page_h:.0f}"],
            )

        # Page 1 cover-page pre-proof is also page furniture
        if page_num == 1 and raw_label == "paragraph_title" and y_top > page_h * 0.08:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.98,
                evidence=[
                    "journal pre-proof marker: page 1, paragraph_title, "
                    f"y={y_top:.0f}/{page_h:.0f}, width={block_width:.0f}/{page_w:.0f}"
                ],
            )

    # Panel label exclusion (single-letter figure labels like A, B, (C), A.)
    if _PANEL_LABEL_PATTERN.match(text):
        return RoleAssignment(
            role="figure_inner_text",
            confidence=0.9,
            evidence=[f"panel label / figure inner text: {text}"],
        )

    # Frontiers figure title check (before general figure/table prefix)
    if raw_label == "figure_title" and _FRONTIERS_FIGURE_TITLE_PATTERN.match(text):
        return RoleAssignment(
            role="figure_caption",
            confidence=0.95,
            evidence=[f"Frontiers figure title pattern: {text[:60]}"],
        )

    if _FRONTIERS_FIGURE_TITLE_PATTERN.match(text):
        return RoleAssignment(
            role="figure_caption",
            confidence=0.9,
            evidence=[f"Frontiers figure title pattern: {text[:60]}"],
        )

    # Figure / table caption patterns override any prior
    if _has_figure_prefix(text):
        if raw_label == "text":
            if _is_obviously_formal_figure_caption(text, block, page_blocks):
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
                role="figure_caption_candidate",
                confidence=0.9,
                evidence=[f"figure caption candidate (body narrative): {text[:60]}"],
            )
        if raw_label == "figure_title":
            return RoleAssignment(
                role="figure_caption_candidate",
                confidence=0.9,
                evidence=[f"figure_title label: {text[:60]}"],
            )
        if _is_obviously_formal_figure_caption(text, block, page_blocks):
            return RoleAssignment(
                role="figure_caption",
                confidence=0.9,
                evidence=[f"figure prefix matched: {text[:60]}"],
            )
        return RoleAssignment(
            role="figure_caption_candidate",
            confidence=0.9,
            evidence=[f"figure caption candidate: {text[:60]}"],
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
    if page_num == 1 and raw_label in ("paragraph_title", "text", "footnote"):
        from paperforge.worker.ocr_document import _detect_frontmatter_zone

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

    # Fallback: page 1 after pre-proof marker — next substantial text block is the real title
    if zone is None and page_num == 1 and raw_label in ("paragraph_title", "text"):
        bbox = block.get("block_bbox") or block.get("bbox") or [0, 0, 0, 0]
        y_top = bbox[1] if len(bbox) >= 4 else 0
        ph = float(block.get("page_height") or page_height or 1700)
        already_has_preproof = any(
            str(b.get("text", "") or b.get("block_content", "") or "").strip().lower().startswith("journal pre")
            for b in page_blocks
            if b is not block
        )
        if already_has_preproof and y_top < ph * 0.35 and len(text) > 40:
            lower_noise = text.strip().lstrip("*•·-–—").lower()
            if lower_noise not in _BACKMATTER_TITLE_DENY_LIST:
                return RoleAssignment(
                    role="paper_title",
                    confidence=0.85,
                    evidence=[f"page-1 title fallback after pre-proof: y={y_top:.0f}/{ph:.0f}"],
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

    # ---- Page-1 frontmatter guard ----
    _pg = block.get("page", 1) or 1
    if _pg == 1 and raw_label in ("doc_title", "paragraph_title", "text"):
        _tv = text
        _lv = _tv.lower().strip().lstrip("*•·-–—")
        block_bbox_local = block.get("block_bbox", [0, 0, 0, 0])
        if _lv in _BACKMATTER_TITLE_DENY_LIST:
            pass  # let existing paragraph_title or fallthrough handle it
        elif raw_label == "doc_title" or (
            raw_label != "text"
            and len(block_bbox_local) >= 4
            and block_bbox_local[1] < page_height * 0.25
            and len(_tv) > 20
            and "abstract" not in _lv[:15]
            and "keywords" not in _lv[:15]
            and "introduction" not in _lv[:15]
        ):
            if len(_tv) > 20 and not _seems_like_authors(_tv):
                return RoleAssignment(
                    role="paper_title",
                    confidence=0.6,
                    evidence=[f"page-1 frontmatter title guard: {_tv[:60]}"],
                )

    # Paddle priors
    if raw_label == "paragraph_title":
        stripped = text.strip().lstrip("*•·-–—")
        lower = stripped.lower()
        if lower in FRONTMATTER_NOISE and _page_still_frontmatter(page_blocks, block.get("page", 1) or 1, page_height):
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
        # Running header guard: article-type labels in running-header
        # position (page > 1, top margin zone) are not section headings.
        _RUNNING_HEADER_LABELS = frozenset(
            {
                "review article",
                "research article",
                "original article",
                "case report",
                "brief communication",
                "rapid communication",
            }
        )
        if lower in _RUNNING_HEADER_LABELS and (block.get("page") or 1) == 1:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.8,
                evidence=[f"page-1 article-type label: {lower}"],
            )
        if lower in _RUNNING_HEADER_LABELS and (block.get("page") or 1) > 1:
            bbox = block.get("block_bbox") or [0, 0, 0, 0]
            _ph = block.get("page_height") or 1700
            if bbox[1] < _ph * 0.12:
                return RoleAssignment(
                    role="noise",
                    confidence=0.8,
                    evidence=[f"running header: {lower}"],
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
                    role="backmatter_heading_candidate",
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
            role_name = "backmatter_boundary_heading"
            confidence = 0.7
            lower_txt = text.lower()
            has_container_words = any(
                w in lower_txt for w in ["additional information", "declaration", "supplementary"]
            )
            span_meta = block.get("span_metadata", {}) or {}
            is_bold = False
            if isinstance(span_meta, dict):
                is_bold = "bold" in (span_meta.get("flags", "") or "").lower()
            elif isinstance(span_meta, list):
                is_bold = any(s.get("flags", 0) & 16 for s in span_meta)
            if not (has_container_words and is_bold):
                role_name = "backmatter_boundary_candidate"
                confidence = 0.5
            return RoleAssignment(
                role=role_name,
                confidence=confidence,
                evidence=[
                    f"backmatter {'boundary heading' if role_name == 'backmatter_boundary_heading' else 'boundary candidate'}: {text[:60]}"
                ],
            )
        # Author-like heading guard: prevent bylines from becoming headings
        _is_author_byline = (
            (re.search(r"&|,.*,", text) or _seems_like_authors(text))
            and len(text.split()) <= 15
            and not _has_heading_numbering(text)
            and not any(
                text.lower().startswith(w)
                for w in ["abstract", "introduction", "methods", "results", "discussion", "conclusion", "references"]
            )
        )
        if _is_author_byline and page_num == 1:
            return RoleAssignment(
                role="authors",
                confidence=0.6,
                evidence=[f"author byline on page 1, assigned as authors: {text[:60]}"],
            )

        if re.search(r"(?:correspondence|orcid|@)", text.lower()) and len(text.split()) <= 20 and page_num == 1:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.5,
                evidence=[f"correspondence/noise on page 1: {text[:60]}"],
            )

        if _has_heading_numbering(text):
            depth = _heading_number_depth(text)
            return RoleAssignment(
                role="section_heading" if depth <= 1 else "subsection_heading",
                confidence=0.85,
                evidence=[f"paragraph_title label with numbering: {text[:60]}"],
            )

        # Page 1 explicit scholarly heading override (Roman numerals, alpha subsections)
        explicit_heading_role = None
        if raw_label == "paragraph_title":
            explicit_heading_role = _explicit_scholarly_heading_role(text)

        if explicit_heading_role:
            page_num = int(block.get("page", 1))
            bbox = block.get("block_bbox") or block.get("bbox") or [0, 0, 0, 0]
            y_top = bbox[1] if len(bbox) >= 4 else 0
            page_height = float(block.get("page_height") or 1700)
            if page_num > 1 or y_top > page_height * 0.25:
                return RoleAssignment(
                    role=explicit_heading_role,
                    confidence=0.9,
                    evidence=[f"explicit scholarly heading: {text[:60]}"],
                )

        bbox = block.get("block_bbox", [0, 0, 0, 0])
        page_num = block.get("page", 1) or 1
        if page_num <= 1:
            if bbox[1] < max(page_height, 1) * 0.25:
                if lower in _BACKMATTER_TITLE_DENY_LIST:
                    depth = _heading_number_depth(text)
                    return RoleAssignment(
                        role="section_heading" if depth <= 1 else "subsection_heading",
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
            confidence=0.85,
            evidence=[f"figure_title label: {text[:60]}"],
        )

    # Textual table check: bullet-point lists mislabeled as "table"
    # must NOT enter media_asset — route to structured_insert_candidate instead.
    if raw_label == "table" and _is_textual_table(text):
        return RoleAssignment(
            role="structured_insert_candidate",
            confidence=0.7,
            evidence=[f"textual table (bullet list) not media_asset: {text[:60]}"],
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
        page_num = block.get("page", 1) or 1
        still_frontmatter = _page_still_frontmatter(page_blocks, page_num, page_height)

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

        # Check for copyright (page 1 only)
        if still_frontmatter and ("copyright" in lower_txt or "©" in text):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.85,
                evidence=[f"copyright text: {text[:60]}"],
            )

        # Check for email / ORCID / DOI patterns (page 1 only)
        if (
            still_frontmatter
            and "@" in text
            and (".edu" in text.lower() or ".com" in text.lower() or ".org" in text.lower())
        ):
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
        if still_frontmatter and any(phrase in lower_txt for phrase in noise_phrases):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.8,
                evidence=[f"frontmatter phrase: {text[:60]}"],
            )

        # Citation line like "Masante B, Gabetti S, ... and Surname (2025)" — page 1 only
        if still_frontmatter and _CITATION_LINE_PATTERN.match(stripped) and " and " in text and ")" in text:
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.8,
                evidence=[f"citation line pattern: {text[:60]}"],
            )

        # Affiliation block starting with superscript (page 1 only)
        if (
            still_frontmatter
            and _AUTHOR_AFFILIATION_MARKER.match(stripped)
            and any(kw in lower_txt for kw in ["department", "university", "institute", "college", "school of"])
        ):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.85,
                evidence=[f"affiliation block: {text[:60]}"],
            )

        # Keyword content block: short comma-separated list of terms (page 1 only)
        if still_frontmatter and (
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

        # Existing noise startswith check (page 1 only)
        if still_frontmatter and any(lower_txt.startswith(n) for n in FRONTMATTER_NOISE):
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
                    evidence=[
                        f"heading-style text block: size={font_size}, flags={font_flags},"
                        f" level={heading_level}, text={text[:40]}"
                    ],
                )

        # Backmatter boundary container heading detection for text blocks
        _pn2 = block.get("page", 1) or 1
        _tp2 = max((b.get("page", 1) or 1) for b in page_blocks) if page_blocks else _pn2
        if _is_backmatter_boundary_heading(block, _pn2, _tp2):
            role_name = "backmatter_boundary_heading"
            confidence = 0.7
            lower_txt = text.lower()
            has_container_words = any(
                w in lower_txt for w in ["additional information", "declaration", "supplementary"]
            )
            span_meta = block.get("span_metadata", {}) or {}
            is_bold = False
            if isinstance(span_meta, dict):
                is_bold = "bold" in (span_meta.get("flags", "") or "").lower()
            elif isinstance(span_meta, list):
                is_bold = any(s.get("flags", 0) & 16 for s in span_meta)
            if not (has_container_words and is_bold):
                role_name = "backmatter_boundary_candidate"
                confidence = 0.5
            return RoleAssignment(
                role=role_name,
                confidence=confidence,
                evidence=[
                    f"backmatter {'boundary heading' if role_name == 'backmatter_boundary_heading' else 'boundary candidate'} from text block: {text[:60]}"
                ],
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


def second_pass_cross_validate(
    block: dict,
    role_profiles: dict,
) -> dict:
    """Second-pass cross-validation for low-confidence role assignments.

    Examines low-confidence blocks against role family profiles.
    Never overrides the assigned role -- only adjusts confidence and
    suggests alternative roles for review.

    Returns:
        {"role": str, "confidence_adjustment": float,
         "role_changed": bool, "suggested_roles": list[str],
         "match_details": dict}
    """
    from paperforge.worker.ocr_profiles import (
        cross_validate_with_span,
        extract_block_span_profile,
    )

    current_role = block.get("role", "")
    current_confidence = block.get("role_confidence", 0.5)

    # Skip if no span data
    block_profile = extract_block_span_profile(block)
    if block_profile is None:
        return {
            "role": current_role,
            "confidence_adjustment": 0.0,
            "role_changed": False,
            "suggested_roles": [],
            "match_details": {},
        }

    # Run cross-validation
    xv_result = cross_validate_with_span(block, current_role, role_profiles)
    adjustment = xv_result["adjustment"]
    suggested_roles = xv_result["suggested_roles"]

    # Don't change role -- only adjust confidence
    # Exception: if suggested_roles has exactly one strong candidate
    # AND current confidence is very low (< 0.3) AND adjustment is strongly negative
    role_changed = False
    if len(suggested_roles) == 1 and current_confidence < 0.3 and adjustment < -0.2:
        # Roles that must never be overridden by second pass
        never_override = {
            "paper_title",
            "abstract_body",
            "reference_heading",
            "reference_item",
            "media_asset",
            "figure_asset",
            "table_html",
            "noise",
            "unknown_structural",
        }
        if current_role in never_override:
            role_changed = False
        elif suggested_roles[0] not in never_override:
            role_changed = True

    return {
        "role": suggested_roles[0] if role_changed else current_role,
        "confidence_adjustment": round(adjustment, 4),
        "role_changed": role_changed,
        "suggested_roles": suggested_roles,
        "match_details": xv_result.get("match_details", {}),
    }
