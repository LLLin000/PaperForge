from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass

from paperforge.worker.ocr_roles import (
    _BACKMATTER_TITLE_DENY_LIST,
    _looks_like_affiliation,
    _looks_like_author_list,
)

_TAIL_ROLES = frozenset(
    {
        "backmatter_boundary_heading",
        "backmatter_heading",
        "backmatter_body",
        "tail_candidate_body",
        "reference_heading",
        "reference_item",
    }
)

TailBoundary = namedtuple(
    "TailBoundary",
    [
        "body_end_page",
        "backmatter_start",
        "references_start",
        "spread_start",
        "spread_end",
        "is_clean_separated",
        "reason",
    ],
)


@dataclass
class PagePosition:
    page: int
    y: float


@dataclass
class DocumentStructure:
    body_end_page: int | None = None
    backmatter_start: PagePosition | None = None
    references_start: PagePosition | None = None
    spread_start: int | None = None
    spread_end: int | None = None
    backmatter_form: str = "flat"


def _detect_forward_body_end(blocks: list[dict]) -> int | None:
    """Scan blocks front-to-back and return the last page of stable body.

    Tracks pages with body headings (section_heading, subsection_heading)
    and body_paragraph continuity.  When a page has tail roles
    (backmatter_heading, reference_heading, etc.) and no body content,
    the body is considered to have ended on the preceding clean body page.
    Returns None if no clear body/backmatter boundary is found.
    """
    if not blocks:
        return None
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)
    pages = sorted(by_page.keys())
    if not pages:
        return None

    last_clean_body_page: int | None = None

    for page in pages:
        roles = {b.get("role") for b in by_page[page]}
        has_body = bool(roles & {"body_paragraph", "section_heading", "subsection_heading", "sub_subsection_heading"})
        has_tail = bool(roles & _TAIL_ROLES)

        if has_body and not has_tail:
            last_clean_body_page = page
        elif has_tail:
            if last_clean_body_page is not None:
                return last_clean_body_page
            if not has_body:
                prev_idx = pages.index(page) - 1
                if prev_idx >= 0:
                    return pages[prev_idx]
                return None

    return None


def _detect_backward_backmatter_start(blocks: list[dict]) -> int | None:
    """Scan blocks backward and return the page where backmatter begins.

    Starting from the last page, looks for the first reference_heading or
    backmatter_heading.  Dense reference pages (>= 4 reference_item blocks)
    are a strong signal.  Short backmatter_body blocks near headings confirm
    the backmatter zone.  Returns None if no backmatter found.
    """
    if not blocks:
        return None
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)
    pages = sorted(by_page.keys(), reverse=True)
    if not pages:
        return None

    for page in pages:
        page_blocks = by_page[page]
        roles = {b.get("role") for b in page_blocks}

        if "reference_heading" in roles or "backmatter_heading" in roles or "backmatter_boundary_heading" in roles:
            return page

        dense_refs = sum(1 for b in page_blocks if b.get("role") == "reference_item")
        if dense_refs >= 4:
            return page

    return None


def _detect_references_start(blocks: list[dict], body_end_page: int | None) -> int | None:
    """Scan from body end page forward for the first page with a reference
    heading or reference item.  Returns None if no references zone is found."""
    if body_end_page is None:
        return None
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)
    pages = sorted(p for p in by_page if p >= body_end_page)
    for page in pages:
        roles = {b.get("role") for b in by_page[page]}
        if "reference_heading" in roles or "reference_item" in roles:
            return page
    return None


def _reconcile_tail_spread(blocks: list[dict]) -> TailBoundary | None:
    """Reconcile forward and backward scans into a structured TailBoundary.

    Returns a TailBoundary namedtuple or None when no tail spread exists.
    The ``reason`` field provides an explainability trace.
    """
    forward_end = _detect_forward_body_end(blocks)
    backward_start = _detect_backward_backmatter_start(blocks)
    references_start = _detect_references_start(blocks, forward_end)

    if forward_end is None and backward_start is None:
        return None

    max_page = 0
    for block in blocks:
        p = block.get("page")
        if p is not None and p > max_page:
            max_page = p

    if forward_end is None and backward_start is not None:
        start = max(1, backward_start - 2)
        reason = (
            f"forward body end not detected, backward backmatter start "
            f"at page {backward_start}, references start at page "
            f"{references_start or 'N/A'}"
        )
        return TailBoundary(
            body_end_page=None,
            backmatter_start=backward_start,
            references_start=references_start,
            spread_start=start,
            spread_end=max_page,
            is_clean_separated=False,
            reason=reason,
        )

    if backward_start is None and forward_end is not None:
        return None

    if forward_end is not None and backward_start is not None:
        is_clean = forward_end < backward_start
        if is_clean:
            spread_start = forward_end + 1
            spread_end = backward_start
        else:
            spread_start = backward_start
            spread_end = forward_end
        reason = (
            f"forward body end at page {forward_end}, "
            f"backward backmatter start at page {backward_start}, "
            f"references start at page {references_start or 'N/A'}"
        )
        return TailBoundary(
            body_end_page=forward_end,
            backmatter_start=backward_start,
            references_start=references_start,
            spread_start=spread_start,
            spread_end=spread_end,
            is_clean_separated=is_clean,
            reason=reason,
        )

    return None


def _classify_backmatter_form(tail_boundary: TailBoundary, blocks: list[dict]) -> str:
    """Return ``"container"`` (PeerJ-style boundary heading with >= 3
    child sections) or ``"flat"`` (Frontiers-style, no boundary or few
    children).
    """
    if tail_boundary.spread_start is None or tail_boundary.spread_end is None:
        return "flat"

    boundary_page = None
    for block in blocks:
        p = block.get("page")
        if (
            p is not None
            and tail_boundary.spread_start <= p <= tail_boundary.spread_end
            and block.get("role") == "backmatter_boundary_heading"
        ):
            boundary_page = p
            break

    if boundary_page is None:
        return "flat"

    child_count = 0
    seen_boundary = False
    for block in blocks:
        p = block.get("page")
        if p is not None and (p < boundary_page or (p == boundary_page and not seen_boundary)):
            if block.get("role") == "backmatter_boundary_heading" and p == boundary_page:
                seen_boundary = True
            continue
        if p is not None and p > tail_boundary.spread_end:
            break
        if not seen_boundary:
            if block.get("role") == "backmatter_boundary_heading":
                seen_boundary = True
            continue
        if block.get("role") == "reference_heading":
            break
        if block.get("role") == "backmatter_heading":
            text = block.get("text", "")
            if len(text) < 40:
                child_count += 1

    return "container" if child_count >= 3 else "flat"


def _label_backmatter_regime(tail_boundary: TailBoundary, backmatter_form: str, blocks: list[dict]) -> None:
    """Enrich tail-spread blocks with a ``_backmatter_regime`` field.

    Blocks after a ``backmatter_boundary_heading`` in container mode get
    ``_backmatter_regime = "container"``; everything else in the spread
    gets ``_backmatter_regime = "flat"``.  The enrichment is in-place.
    """
    if tail_boundary.spread_start is None:
        return

    boundary_seen = False
    for block in blocks:
        p = block.get("page")
        if p is not None and p < tail_boundary.spread_start:
            continue
        if p is not None and p > tail_boundary.spread_end:
            continue

        if block.get("role") in _TAIL_ROLES:
            if block.get("role") == "backmatter_boundary_heading":
                boundary_seen = True
            if backmatter_form == "container" and boundary_seen:
                block["_backmatter_regime"] = "container"
            else:
                block["_backmatter_regime"] = "flat"


def _normalize_backmatter_roles_after_boundary(
    tail_boundary: TailBoundary | None,
    backmatter_form: str,
    blocks: list[dict],
) -> None:
    """Normalize mixed roles inside the backmatter region.

    Once the backmatter boundary has been entered, all non-reference headings
    should be treated as backmatter headings and all owned content should stop
    competing with body/frontmatter roles.
    """
    if (
        tail_boundary is None
        or tail_boundary.spread_start is None
        or tail_boundary.spread_end is None
        or backmatter_form != "container"
    ):
        return

    boundary_seen = False
    for block in blocks:
        page = block.get("page")
        if page is None or page < tail_boundary.spread_start or page > tail_boundary.spread_end:
            continue

        role = block.get("role")
        if role == "backmatter_boundary_heading":
            if boundary_seen:
                block["role"] = "backmatter_heading"
                block["_backmatter_regime"] = "container"
            else:
                boundary_seen = True
                block["_backmatter_regime"] = "container"
            continue

        if not boundary_seen:
            continue

        if role == "reference_heading":
            break

        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            block["role"] = "backmatter_heading"
            block["_backmatter_regime"] = "container"
            block["render_default"] = True
            continue

        if role in {"body_paragraph", "frontmatter_noise"}:
            block["role"] = "backmatter_body"
            block["_backmatter_regime"] = "container"
            block["render_default"] = True
            block["index_default"] = True


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

    if lower_txt.startswith("abstract") and len(text) < 30:
        return "abstract_zone"

    furniture_signals = [
        "submitted",
        "accepted",
        "published",
        "received",
        "copyright",
        "\u00a9",
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

    if page_height > 0 and y1 < page_height * 0.2:
        block_width = x2 - x1
        is_wide_enough = page_width <= 0 or block_width > page_width * 0.4
        if is_wide_enough and lower_txt not in _BACKMATTER_TITLE_DENY_LIST and not _looks_like_author_list(text):
            if raw_label in ("paragraph_title", "doc_title"):
                return "title_zone"
            if raw_label == "text" and len(text) < 80:
                return "title_zone"

    if (
        page_height > 0
        and y1 < page_height * 0.4
        and _looks_like_author_list(text)
        and not _looks_like_affiliation(text)
    ):
        return "author_zone"

    if page_height > 0 and y1 < page_height * 0.6 and _looks_like_affiliation(text):
        return "affiliation_zone"

    return None


def _page_still_frontmatter(page_blocks: list[dict], page_num: int, page_height: float) -> bool:
    """Check if page is still in frontmatter regime (no body content yet).

    Uses block labels and vertical position: if any block on a page > 1 has
    body-type labels (figure_title, chart, table) or a text block in the
    lower third, body content has started and frontmatter rules should stop.
    """
    if page_num == 1:
        return True
    for pb in page_blocks:
        label = pb.get("block_label", "")
        if label in ("figure_title", "chart", "table", "reference_content"):
            return False
        bbox = pb.get("block_bbox", [0, 0, 0, 0])
        if label == "text" and len(bbox) >= 4 and bbox[1] > page_height * 0.35:
            return False
    return True


def analyze_document_structure(blocks: list[dict]) -> DocumentStructure:
    """Produce a structured document boundary object.

    Uses the existing _detect_forward_body_end, _detect_backward_backmatter_start,
    etc. internally. Returns a DocumentStructure with all boundary info.
    """
    tail_spread = _reconcile_tail_spread(blocks)
    if tail_spread is not None:
        backmatter_form = _classify_backmatter_form(tail_spread, blocks)
        _label_backmatter_regime(tail_spread, backmatter_form, blocks)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
    else:
        backmatter_form = "flat"

    return DocumentStructure(
        body_end_page=tail_spread.body_end_page if tail_spread else None,
        backmatter_start=PagePosition(page=tail_spread.backmatter_start, y=0.0)
        if tail_spread and tail_spread.backmatter_start is not None
        else None,
        references_start=PagePosition(page=tail_spread.references_start, y=0.0)
        if tail_spread and tail_spread.references_start is not None
        else None,
        spread_start=tail_spread.spread_start if tail_spread else None,
        spread_end=tail_spread.spread_end if tail_spread else None,
        backmatter_form=backmatter_form,
    )
