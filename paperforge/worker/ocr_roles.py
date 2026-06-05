from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RoleAssignment:
    role: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)


_HEADING_NUMBER_PATTERN = re.compile(
    r"^\d+(?:\.\d+)*\s+\w",
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
    "supplementary material",
    "these authors have contributed equally",
    "publisher's note",
}

_REFERENCE_PATTERN = re.compile(
    r"^\s*(?:\d+\.\s|[A-Z][A-Za-z'’\-]+\s+et al\.\s*\(\d{4}[a-z]?\)|\([A-Z][A-Za-z'’\-]+\s+et al\.,\s*\d{4}[a-z]?\))",
)


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
) -> RoleAssignment:
    raw_label = str(block.get("block_label", "") or "").strip()
    text = str(block.get("block_content", "") or "").strip()

    # Figure / table caption patterns override any prior
    if _has_figure_prefix(text):
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
        if _has_heading_numbering(text):
            return RoleAssignment(
                role="section_heading" if re.match(r"^\d+\s", text) else "subsection_heading",
                confidence=0.85,
                evidence=[f"paragraph_title label with numbering: {text[:60]}"],
            )
        return RoleAssignment(
            role="paper_title",
            confidence=0.7,
            evidence=[f"unnumbered paragraph_title, likely paper title: {text[:60]}"],
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
        if any(lower_txt.startswith(n) for n in FRONTMATTER_NOISE):
            return RoleAssignment(
                role="frontmatter_noise",
                confidence=0.7,
                evidence=[f"frontmatter noise text: {text[:60]}"],
            )
        if _has_heading_numbering(text):
            return RoleAssignment(
                role="section_heading" if re.match(r"^\d+\s", text) else "subsection_heading",
                confidence=0.65,
                evidence=[f"numbered text block: {text[:60]}"],
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
