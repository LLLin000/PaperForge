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


def rescue_roles_with_document_context(
    blocks: list[dict],
    role_profiles: dict,
    document_structure: DocumentStructure | None = None,
) -> list[dict]:
    """Apply section-context-aware role rescue rules using document structure.

    Uses the previously-built role style profiles and document boundaries to
    correct common role-assignment errors:

    1. ``frontmatter_noise`` in the body section with body-like font
       → ``body_paragraph``
    2. ``body_paragraph`` in the references section with reference-like font
       → ``reference_item`` (only when confidence < 0.7)
    3. Weak heading (confidence < 0.6) with body-like font → ``body_paragraph``

    Never overrides: strong formal prefixes (Figure, Table), strong numbering,
    or explicit boundary-heading logic.

    Returns a new list of blocks with corrected roles.
    """
    from paperforge.worker.ocr_profiles import (
        compare_against_role_family,
        extract_block_span_profile,
    )
    from paperforge.worker.ocr_roles import _has_heading_numbering

    if document_structure is None:
        document_structure = analyze_document_structure(blocks)

    body_end_page = document_structure.body_end_page
    refs_start = document_structure.references_start
    refs_start_page = refs_start.page if refs_start else None

    result = list(blocks)

    for block in result:
        # --- Rule 1: frontmatter_noise → body_paragraph (body section + body font)
        if block.get("role") == "frontmatter_noise":
            page = block.get("page", 1) or 1
            if body_end_page is not None and page <= body_end_page:
                bp = extract_block_span_profile(block)
                if bp:
                    body_fam = role_profiles.get("body_paragraph", {})
                    if body_fam:
                        match = compare_against_role_family(bp, body_fam)
                        if match["size_compatible"] and match["match_score"] > 0.5:
                            block["role"] = "body_paragraph"
                            block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.1, 1.0)
                            block.setdefault("evidence", []).append("rescue: frontmatter_noise → body_paragraph")

        # --- Rule 2: body_paragraph → reference_item (refs section + ref font)
        role = block.get("role", "")
        if role == "body_paragraph" and block.get("role_confidence", 1.0) < 0.7:
            page = block.get("page", 1) or 1
            if refs_start_page is not None and page >= refs_start_page:
                bp = extract_block_span_profile(block)
                if bp:
                    ref_fam = role_profiles.get("reference_item", {})
                    if ref_fam:
                        match = compare_against_role_family(bp, ref_fam)
                        if match["size_compatible"] and match["match_score"] > 0.5:
                            block["role"] = "reference_item"
                            block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.2, 1.0)
                            block.setdefault("evidence", []).append("rescue: body_paragraph → reference_item")

        # --- Rule 3: weak heading with body font → body_paragraph
        if (
            role in {"section_heading", "subsection_heading", "sub_subsection_heading"}
            and block.get("role_confidence", 1.0) < 0.6
        ):
            text = str(block.get("text", "") or block.get("block_content", "") or "")
            if _has_heading_numbering(text):
                continue
            bp = extract_block_span_profile(block)
            if bp:
                body_fam = role_profiles.get("body_paragraph", {})
                if body_fam:
                    match = compare_against_role_family(bp, body_fam)
                    if match["size_compatible"] and match["match_score"] > 0.5:
                        block["role"] = "body_paragraph"
                        block.setdefault("evidence", []).append("rescue: heading → body_paragraph")

    return result


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


def _get_column(block: dict, page_width: float = 1200) -> int:
    bbox = block.get("bbox") or block.get("block_bbox")
    if bbox and len(bbox) >= 4:
        x_center = (bbox[0] + bbox[2]) / 2
        return 0 if x_center < page_width / 2 else 1
    return 0


def _is_in_usable_content(
    block: dict,
    header_band: float | None,
    footer_band: float | None,
) -> bool:
    bbox = block.get("bbox") or block.get("block_bbox")
    if not bbox or len(bbox) < 4:
        return True
    y1, y2 = bbox[1], bbox[3]
    if header_band is not None and y2 < header_band:
        return False
    return not (footer_band is not None and y1 > footer_band)


def _estimate_noise_bands(
    structured_blocks: list[dict],
) -> tuple[float | None, float | None]:
    header_candidates: list[float] = []
    footer_candidates: list[float] = []

    for block in structured_blocks:
        role = block.get("role", "")
        bbox = block.get("bbox") or block.get("block_bbox")
        if not bbox or len(bbox) < 4:
            continue
        page_height = block.get("page_height", 0) or 0
        if page_height == 0:
            continue
        y2, y1 = bbox[3], bbox[1]

        noise_roles = {"noise", "header", "footer", "number"}
        raw_label = block.get("raw_label", "")
        if role in noise_roles or raw_label in ("header", "footer", "number"):
            if y2 < page_height * 0.15:
                header_candidates.append(y2)
            if y1 > page_height * 0.85:
                footer_candidates.append(y1)

    header_band = max(header_candidates) if header_candidates else None
    footer_band = min(footer_candidates) if footer_candidates else None
    return header_band, footer_band


def _has_same_column_anchor_above(
    body: dict,
    anchors: list[dict],
    page_width: float = 1200,
) -> bool:
    body_bbox = body.get("bbox") or body.get("block_bbox")
    if not body_bbox or len(body_bbox) < 4:
        return False

    body_y = body_bbox[1]
    body_col = _get_column(body, page_width)

    for anchor in anchors:
        anchor_bbox = anchor.get("bbox") or anchor.get("block_bbox")
        if not anchor_bbox or len(anchor_bbox) < 4:
            continue
        if _get_column(anchor, page_width) != body_col:
            continue
        if anchor_bbox[3] <= body_y:
            return True
    return False


def _find_best_anchor(
    body: dict,
    anchors: list[dict],
    ref_heading: dict | None = None,
    page_width: float = 1200,
) -> int | None:
    body_bbox = body.get("bbox") or body.get("block_bbox")
    if not body_bbox or len(body_bbox) < 4:
        return None
    body_y = body_bbox[1]
    body_page = body.get("page", 0) or 0
    body_mid = (body_bbox[0] + body_bbox[2]) / 2
    pw_mid = page_width / 2
    body_col = 0 if body_mid < pw_mid else 1

    best_same: tuple[int, float] | None = None
    best_other: tuple[int, float] | None = None

    for idx, anchor in enumerate(anchors):
        if anchor is ref_heading:
            continue
        a_bbox = anchor.get("bbox") or anchor.get("block_bbox")
        if not a_bbox or len(a_bbox) < 4:
            continue

        anchor_page = anchor.get("page", 0) or 0
        if anchor_page > body_page:
            continue

        a_bottom = a_bbox[3]
        if anchor_page == body_page and a_bottom > body_y:
            continue

        a_mid = (a_bbox[0] + a_bbox[2]) / 2
        a_col = 0 if a_mid < pw_mid else 1

        if anchor_page == body_page:
            dist = body_y - a_bottom
        else:
            page_extent = body.get("page_height", 0) or page_width
            dist = (body_page - anchor_page) * page_extent + max(0.0, page_extent - a_bottom)

        if body_col == a_col:
            if best_same is None or dist < best_same[1]:
                best_same = (idx, dist)
        else:
            if best_other is None or dist < best_other[1]:
                best_other = (idx, dist)

    best = best_same or best_other
    return best[0] if best is not None else None


def _promote_tail_body_candidates(
    blocks: list[dict],
    doc: DocumentStructure | None,
    header_band: float | None = None,
    footer_band: float | None = None,
) -> list[dict]:
    if doc is None or doc.spread_start is None or doc.spread_end is None:
        return blocks

    spread_start, spread_end = doc.spread_start, doc.spread_end
    by_page: dict[int, list[int]] = {}
    for idx, block in enumerate(blocks):
        page = block.get("page")
        if page is not None:
            by_page.setdefault(page, []).append(idx)

    result = [dict(block) for block in blocks]
    for page, indices in by_page.items():
        if page < spread_start or page > spread_end:
            continue

        page_blocks = [result[i] for i in indices]
        local_headings = [
            b for b in page_blocks if b.get("role") in ("backmatter_heading", "backmatter_boundary_heading")
        ]
        ref_heading = next((b for b in page_blocks if b.get("role") == "reference_heading"), None)
        local_anchors = local_headings
        local_tops = []
        for anchor in [*local_headings, *([ref_heading] if ref_heading else [])]:
            bbox = anchor.get("bbox") or anchor.get("block_bbox")
            if bbox and len(bbox) >= 4:
                local_tops.append(bbox[1])
        first_local_anchor_top = min(local_tops) if local_tops else None

        for idx in indices:
            block = result[idx]
            if block.get("role") != "body_paragraph":
                continue
            if not _is_in_usable_content(block, header_band, footer_band):
                continue

            bbox = block.get("bbox") or block.get("block_bbox")
            if not bbox or len(bbox) < 4:
                continue

            promote = False
            page_width = block.get("page_width", 1200) or 1200
            if local_anchors and _has_same_column_anchor_above(block, local_anchors, page_width):
                promote = True
            elif page > spread_start:
                body_top = bbox[1]
                if first_local_anchor_top is None or body_top < first_local_anchor_top:
                    promote = True

            if promote:
                block["role"] = "tail_candidate_body"
                block["evidence"] = list(block.get("evidence") or []) + ["promoted in tail spread from body_paragraph"]

    return result


def _assign_tail_spread_ownership(
    blocks: list[dict],
    doc: DocumentStructure | None = None,
) -> list[dict]:
    tail_heading_roles = {"backmatter_heading", "backmatter_boundary_heading"}
    anchors = [b for b in blocks if b.get("role") in tail_heading_roles]
    ref_heading = next((b for b in blocks if b.get("role") == "reference_heading"), None)

    if doc is not None and doc.spread_start is not None and doc.spread_end is not None:
        spread_start, spread_end = doc.spread_start, doc.spread_end
    else:
        spread_start, spread_end = 0, 0

    if not anchors:
        return [{**b, "role": "body_paragraph"} if b.get("role") == "tail_candidate_body" else b for b in blocks]

    result = list(blocks)
    for i, block in enumerate(result):
        if block.get("role") != "tail_candidate_body":
            continue

        block_page = block.get("page", 0) or 0

        if doc is not None and (block_page < spread_start or block_page > spread_end):
            result[i] = dict(block)
            result[i]["role"] = "body_paragraph"
            continue

        pw = block.get("page_width", 0) or 1200
        idx = _find_best_anchor(block, anchors, ref_heading, pw)
        result[i] = dict(block)
        if idx is not None:
            anchor_page = anchors[idx].get("page", 0)
            result[i]["role"] = "backmatter_body"
            result[i]["_spread_anchor"] = anchor_page
        else:
            result[i]["role"] = "body_paragraph"
    return result


def normalize_document_structure(blocks: list[dict]) -> tuple[DocumentStructure, list[dict]]:
    """Analyze document structure and normalize roles.

    Returns (document_structure, normalized_blocks).
    Normalization includes:
    - backmatter form classification
    - backmatter role normalization after boundary
    - tail body candidate promotion
    - tail spread ownership assignment
    """
    tail_spread = _reconcile_tail_spread(blocks)
    if tail_spread is not None:
        backmatter_form = _classify_backmatter_form(tail_spread, blocks)
        _label_backmatter_regime(tail_spread, backmatter_form, blocks)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
    else:
        backmatter_form = "flat"

    doc_structure = DocumentStructure(
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

    header_band, footer_band = _estimate_noise_bands(blocks)
    blocks = _promote_tail_body_candidates(blocks, doc_structure, header_band=header_band, footer_band=footer_band)
    blocks = _assign_tail_spread_ownership(blocks, doc_structure)

    return doc_structure, blocks
