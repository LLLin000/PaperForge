from __future__ import annotations

import dataclasses
import re
from collections import namedtuple
from dataclasses import dataclass, field

from paperforge.worker.ocr_roles import (
    _BACKMATTER_TITLE_DENY_LIST,
    _is_near_figure_media,
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
class PageLayoutProfile:
    column_count: int = 1
    column_boundaries: list[float] = field(default_factory=list)
    layout_type: str = "single_column"


@dataclass
class ReadingSegment:
    page: int
    column_index: int
    y_top: float
    y_bottom: float
    block_indices: list[int]
    semantic_hint: str = ""


@dataclass
class ReferenceZone:
    page: int
    column_index: int
    y_start: float
    y_end: float
    block_indices: list[int]


@dataclass
class DocumentStructure:
    body_end_page: int | None = None
    backmatter_start: PagePosition | None = None
    references_start: PagePosition | None = None
    spread_start: int | None = None
    spread_end: int | None = None
    backmatter_form: str = "flat"
    page_layouts: dict[int, PageLayoutProfile] | None = None
    tail_reading_order: list[dict] | None = None
    reference_zones: list[dict] | None = None


def _cluster_page_columns(page_blocks: list[dict], page_width: float) -> list[float]:
    """Cluster block x-centers by column using a gap-based approach.

    Returns one representative x-center per column cluster.
    """
    centers: list[float] = []
    for block in page_blocks:
        bbox = block.get("bbox") or block.get("block_bbox")
        if not bbox or len(bbox) < 4:
            continue
        block_width = bbox[2] - bbox[0]
        if block_width <= 50:
            continue
        x_center = (bbox[0] + bbox[2]) / 2
        centers.append(x_center)

    if not centers:
        return [page_width / 2]

    centers.sort()
    gap_threshold = page_width * 0.15
    clusters: list[list[float]] = [[centers[0]]]

    for c in centers[1:]:
        if c - clusters[-1][-1] > gap_threshold:
            clusters.append([c])
        else:
            clusters[-1].append(c)

    return [sum(cluster) / len(cluster) for cluster in clusters]


def _classify_page_layout(page_blocks: list[dict], page_width: float, page_height: float) -> PageLayoutProfile:
    """Classify a page's layout based on column clusters and role distribution."""
    centers = _cluster_page_columns(page_blocks, page_width)
    column_count = len(centers)

    if column_count == 1:
        return PageLayoutProfile(column_count=1, column_boundaries=centers, layout_type="single_column")

    if column_count == 2:
        col_blocks: dict[int, list[str]] = {0: [], 1: []}
        for block in page_blocks:
            bbox = block.get("bbox") or block.get("block_bbox")
            if not bbox or len(bbox) < 4:
                continue
            x_center = (bbox[0] + bbox[2]) / 2
            col = 0 if x_center < page_width / 2 else 1
            col_blocks[col].append(block.get("role", ""))

        body_roles = {
            "body_paragraph",
            "section_heading",
            "subsection_heading",
            "sub_subsection_heading",
        }

        col_has_body: dict[int, bool] = {}
        col_has_tail: dict[int, bool] = {}
        for col_idx, roles in col_blocks.items():
            col_has_body[col_idx] = bool(set(roles) & body_roles)
            col_has_tail[col_idx] = bool(set(roles) & _TAIL_ROLES)

        one_side_body = col_has_body[0] and not col_has_tail[0]
        other_side_tail = not col_has_body[1] and col_has_tail[1]
        swapped = col_has_body[1] and not col_has_tail[1]
        swapped_tail = not col_has_body[0] and col_has_tail[0]

        if (one_side_body and other_side_tail) or (swapped and swapped_tail):
            return PageLayoutProfile(
                column_count=2,
                column_boundaries=centers,
                layout_type="mixed_tail",
            )

        return PageLayoutProfile(column_count=2, column_boundaries=centers, layout_type="two_column")

    return PageLayoutProfile(
        column_count=column_count,
        column_boundaries=centers,
        layout_type="two_column",
    )


def _build_page_layout_profiles(blocks: list[dict]) -> dict[int, PageLayoutProfile]:
    """Build per-page layout profiles for all pages that have blocks."""
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)

    profiles: dict[int, PageLayoutProfile] = {}
    for page, page_blocks in by_page.items():
        page_width = max((b.get("page_width", 0) or 0) for b in page_blocks) or 1200
        page_height = max((b.get("page_height", 0) or 0) for b in page_blocks) or 1600
        profiles[page] = _classify_page_layout(page_blocks, page_width, page_height)

    return profiles


def _block_bbox(block: dict) -> list[float] | None:
    bbox = block.get("bbox") or block.get("block_bbox")
    return bbox if bbox and len(bbox) >= 4 else None


def _block_y_top(block: dict) -> float:
    bbox = _block_bbox(block)
    return bbox[1] if bbox else 0.0


def _block_y_bottom(block: dict) -> float:
    bbox = _block_bbox(block)
    return bbox[3] if bbox else 0.0


def _classify_segment_hint(blocks: list[dict]) -> str:
    roles = {b.get("role") for b in blocks}
    body_roles = {
        "body_paragraph",
        "section_heading",
        "subsection_heading",
        "sub_subsection_heading",
    }
    backmatter_roles = {
        "backmatter_heading",
        "backmatter_boundary_heading",
        "backmatter_body",
        "tail_candidate_body",
    }
    ref_roles = {"reference_heading", "reference_item"}
    has_body = bool(roles & body_roles)
    has_backmatter = bool(roles & backmatter_roles)
    has_ref = bool(roles & ref_roles)
    count = sum([has_body, has_backmatter, has_ref])
    if count >= 2:
        return "mixed"
    if has_body:
        return "body"
    if has_backmatter:
        return "backmatter"
    if has_ref:
        return "references"
    return ""


def _get_column_index_by_boundaries(x_center: float, boundaries: list[float]) -> int:
    if len(boundaries) <= 1:
        return 0
    midpoints = [(boundaries[i] + boundaries[i + 1]) / 2 for i in range(len(boundaries) - 1)]
    for col, mp in enumerate(midpoints):
        if x_center < mp:
            return col
    return len(boundaries) - 1


def _build_page_reading_segments(
    page_blocks: list[dict],
    page_profile: PageLayoutProfile | None,
    page_idx_offset: int,
) -> list[ReadingSegment]:
    if not page_blocks:
        return []
    page = page_blocks[0].get("page", 0) or 0
    if page_profile is None or page_profile.column_count <= 1:
        sorted_blocks = sorted(enumerate(page_blocks), key=lambda x: _block_y_top(x[1]))
        indices = [page_idx_offset + i for i, _ in sorted_blocks]
        y_top = min(_block_y_top(b) for b in page_blocks)
        y_bottom = max(_block_y_bottom(b) for b in page_blocks)
        hint = _classify_segment_hint(page_blocks)
        return [
            ReadingSegment(
                page=page,
                column_index=0,
                y_top=y_top,
                y_bottom=y_bottom,
                block_indices=indices,
                semantic_hint=hint,
            )
        ]
    boundaries = page_profile.column_boundaries
    col_blocks: dict[int, list[tuple[int, dict]]] = {}
    for i, block in enumerate(page_blocks):
        bbox = _block_bbox(block)
        if bbox:
            x_center = (bbox[0] + bbox[2]) / 2
            col = _get_column_index_by_boundaries(x_center, boundaries)
        else:
            col = 0
        col_blocks.setdefault(col, []).append((i, block))
    segments: list[ReadingSegment] = []
    for col in sorted(col_blocks):
        items = col_blocks[col]
        items.sort(key=lambda x: _block_y_top(x[1]))
        indices = [page_idx_offset + i for i, _ in items]
        col_blocks_only = [b for _, b in items]
        y_top = min(_block_y_top(b) for b in col_blocks_only)
        y_bottom = max(_block_y_bottom(b) for b in col_blocks_only)
        hint = _classify_segment_hint(col_blocks_only)
        segments.append(
            ReadingSegment(
                page=page,
                column_index=col,
                y_top=y_top,
                y_bottom=y_bottom,
                block_indices=indices,
                semantic_hint=hint,
            )
        )
    return segments


def _build_tail_reading_order(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile],
) -> list[ReadingSegment]:
    tail_pages: set[int] = set()
    for block in blocks:
        if block.get("role") in _TAIL_ROLES:
            p = block.get("page")
            if p is not None:
                tail_pages.add(p)
    if not tail_pages:
        return []
    by_page: dict[int, list[tuple[int, dict]]] = {}
    for i, block in enumerate(blocks):
        p = block.get("page")
        if p is not None and p in tail_pages:
            by_page.setdefault(p, []).append((i, block))
    segments: list[ReadingSegment] = []
    for page in sorted(by_page):
        page_items = by_page[page]
        page_items.sort(key=lambda x: x[0])
        page_idx_offset = page_items[0][0]
        page_blocks_only = [item[1] for item in page_items]
        profile = page_layouts.get(page)
        page_segments = _build_page_reading_segments(page_blocks_only, profile, page_idx_offset)
        segments.extend(page_segments)
    return segments


def _detect_reference_zones(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile],
) -> list[ReferenceZone]:
    """Detect local reference zones per page.

    For each page with a ``reference_heading``, creates a ``ReferenceZone``
    scoped to that heading's column.  Only blocks in the same column and
    below the heading's bottom y are included in the zone.
    """
    zones: list[ReferenceZone] = []
    for block in blocks:
        if block.get("role") != "reference_heading":
            continue
        page = block.get("page")
        if page is None:
            continue
        profile = page_layouts.get(page)
        bbox = _block_bbox(block)
        if not bbox:
            continue
        y_start = bbox[3]
        if profile is None or profile.column_count <= 1:
            column_index = 0
        else:
            x_center = (bbox[0] + bbox[2]) / 2
            column_index = _get_column_index_by_boundaries(x_center, profile.column_boundaries)
        zone_indices: list[int] = []
        max_y = y_start
        for j, b in enumerate(blocks):
            if b.get("page") != page:
                continue
            bb = _block_bbox(b)
            if not bb:
                continue
            if profile and profile.column_count > 1:
                bx_center = (bb[0] + bb[2]) / 2
                bcol = _get_column_index_by_boundaries(bx_center, profile.column_boundaries)
                if bcol != column_index:
                    continue
            if bb[1] < y_start - 1:
                continue
            zone_indices.append(j)
            if bb[3] > max_y:
                max_y = bb[3]
        zones.append(
            ReferenceZone(
                page=page,
                column_index=column_index,
                y_start=y_start,
                y_end=max_y,
                block_indices=zone_indices,
            )
        )
    return zones


def _block_in_any_reference_zone(
    block: dict,
    zones: list[ReferenceZone],
    global_index: int,
) -> bool:
    """Check if a block (by global index) falls within any reference zone."""
    return any(global_index in zone.block_indices for zone in zones)


def _detect_forward_body_end(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> int | None:
    """Scan blocks front-to-back and return the last page of stable body.

    Tracks pages with body headings (section_heading, subsection_heading)
    and body_paragraph continuity.  When a page has tail roles
    (backmatter_heading, reference_heading, etc.) and no body content,
    the body is considered to have ended on the preceding clean body page.

    With ``page_layouts``, multi-column pages are checked per-column:
    if any column has body roles without tail roles in that same column,
    body continues even if other columns have tail content.
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

    body_roles = {"body_paragraph", "section_heading", "subsection_heading", "sub_subsection_heading"}
    last_clean_body_page: int | None = None

    for page in pages:
        page_blocks = by_page[page]
        roles = {b.get("role") for b in page_blocks}
        has_body = bool(roles & body_roles)
        has_tail = bool(roles & _TAIL_ROLES)

        if page_layouts and page in page_layouts:
            profile = page_layouts[page]
            if profile.column_count > 1:
                boundaries = profile.column_boundaries
                col_has_body: dict[int, bool] = {}
                col_has_tail: dict[int, bool] = {}
                for block in page_blocks:
                    bbox = _block_bbox(block)
                    if not bbox:
                        continue
                    x_center = (bbox[0] + bbox[2]) / 2
                    col = _get_column_index_by_boundaries(x_center, boundaries)
                    role = block.get("role", "")
                    if role in body_roles:
                        col_has_body[col] = True
                    if role in _TAIL_ROLES:
                        col_has_tail[col] = True

                any_body_without_tail = any(
                    col_has_body.get(col, False) and not col_has_tail.get(col, False)
                    for col in range(profile.column_count)
                )
                if any_body_without_tail:
                    last_clean_body_page = page
                    continue

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

    return last_clean_body_page


def _detect_backward_backmatter_start(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> int | None:
    """Scan blocks backward and return the page where backmatter begins.

    Starting from the last page, looks for the first reference_heading or
    backmatter_heading.  Dense reference pages (>= 4 reference_item blocks)
    are a strong signal.  Short backmatter_body blocks near headings confirm
    the backmatter zone.

    With ``page_layouts``, multi-column pages check for backmatter headings
    rather than relying on the dense-refs heuristic, which can be confused
    by reference-only columns.  Returns None if no backmatter found.
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

        if page_layouts and page in page_layouts:
            profile = page_layouts[page]
            if profile.column_count > 1:
                continue

        dense_refs = sum(1 for b in page_blocks if b.get("role") == "reference_item")
        if dense_refs >= 4:
            return page

    return None


def _detect_references_start(
    blocks: list[dict],
    body_end_page: int | None,
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> int | None:
    """Scan from body end page forward for the first page with a reference
    heading or reference item.

    With ``page_layouts``, uses ``_detect_reference_zones`` internally to
    find the earliest page with a local reference zone.  Falls back to
    page-level scanning when layout data is unavailable.
    Returns None if no references zone is found.
    """
    if body_end_page is None:
        return None
    if page_layouts:
        zones = _detect_reference_zones(blocks, page_layouts)
        if zones:
            earliest = min(z.page for z in zones)
            return max(earliest, body_end_page)
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


def _reconcile_tail_spread(
    blocks: list[dict],
    page_layouts: dict[int, PageLayoutProfile] | None = None,
) -> TailBoundary | None:
    """Reconcile forward and backward scans into a structured TailBoundary.

    Returns a TailBoundary namedtuple or None when no tail spread exists.
    The ``reason`` field provides an explainability trace.
    ``page_layouts`` is passed to layout-aware boundary detection functions.
    """
    forward_end = _detect_forward_body_end(blocks, page_layouts)
    backward_start = _detect_backward_backmatter_start(blocks, page_layouts)
    references_start = _detect_references_start(blocks, forward_end, page_layouts)

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


_BOUNDARY_ROLES = frozenset({"backmatter_boundary_heading", "backmatter_boundary_candidate"})


def _classify_backmatter_form(tail_boundary: TailBoundary, blocks: list[dict]) -> str:
    """Return ``"container"`` (PeerJ-style boundary heading with >= 3
    child sections) or ``"flat"`` (Frontiers-style, no boundary or few
    children).
    """
    if tail_boundary.spread_start is None or tail_boundary.spread_end is None:
        return "flat"

    # Search for boundary headings from body_end_page onwards, not just
    # from spread_start, because the container boundary may lie on the
    # last body page (before backmatter begins) — e.g. ADDITIONAL
    # INFORMATION AND DECLARATIONS on page 10 when spread starts at 11.
    search_start = min(tail_boundary.spread_start, tail_boundary.body_end_page or tail_boundary.spread_start)
    boundary_page = None
    for block in blocks:
        p = block.get("page")
        if (
            p is not None
            and search_start <= p <= tail_boundary.spread_end
            and block.get("role") in _BOUNDARY_ROLES
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
            if block.get("role") in _BOUNDARY_ROLES and p == boundary_page:
                seen_boundary = True
            continue
        if p is not None and p > tail_boundary.spread_end:
            break
        if not seen_boundary:
            if block.get("role") in _BOUNDARY_ROLES:
                seen_boundary = True
            continue
        if block.get("role") == "reference_heading":
            break
        if block.get("role") in ("backmatter_heading", "backmatter_heading_candidate"):
            text = block.get("text", "")
            if len(text) < 40:
                child_count += 1

    return "container" if child_count >= 3 else "flat"


def _effective_tail_start(tail_boundary: TailBoundary, blocks: list[dict]) -> int:
    """Return the effective lower bound for tail analysis.

    Normally ``spread_start``, but for container-form tail spreads the
    boundary heading may lie on the last body page (before the detected
    backmatter start).  In that case the tail analysis should include
    that earlier page so child sections beneath the boundary are not
    orphaned outside the spread.
    """
    effective = tail_boundary.spread_start
    body_end = tail_boundary.body_end_page
    if body_end is not None and body_end < effective:
        for block in blocks:
            p = block.get("page")
            if p is not None and body_end <= p < effective:
                if block.get("role") in _BOUNDARY_ROLES:
                    effective = min(effective, body_end)
                    break
    return effective


def _label_backmatter_regime(tail_boundary: TailBoundary, backmatter_form: str, blocks: list[dict]) -> None:
    """Enrich tail-spread blocks with a ``_backmatter_regime`` field.

    Blocks after a ``backmatter_boundary_heading`` in container mode get
    ``_backmatter_regime = "container"``; everything else in the spread
    gets ``_backmatter_regime = "flat"``.  The enrichment is in-place.
    """
    if tail_boundary.spread_start is None:
        return

    tail_start = _effective_tail_start(tail_boundary, blocks)
    boundary_seen = False
    for block in blocks:
        p = block.get("page")
        if p is not None and p < tail_start:
            continue
        if p is not None and p > tail_boundary.spread_end:
            continue

        if block.get("role") in _TAIL_ROLES:
            if block.get("role") in _BOUNDARY_ROLES:
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
    if tail_boundary is None or tail_boundary.spread_start is None or tail_boundary.spread_end is None:
        return

    tail_start = _effective_tail_start(tail_boundary, blocks)
    boundary_seen = False
    backmatter_started = False
    for block in blocks:
        page = block.get("page")
        if page is None or page < tail_start or page > tail_boundary.spread_end:
            continue

        role = block.get("role")
        if backmatter_form == "container":
            if role in _BOUNDARY_ROLES:
                if boundary_seen:
                    block["role"] = "backmatter_heading"
                else:
                    boundary_seen = True
                backmatter_started = True
                block["_backmatter_regime"] = "container"
                continue

            if not boundary_seen:
                continue
        else:
            if role in _BOUNDARY_ROLES | {"backmatter_heading"}:
                backmatter_started = True
                block["_backmatter_regime"] = "flat"
                if role in _BOUNDARY_ROLES:
                    block["role"] = "backmatter_heading"
                continue
            if not backmatter_started:
                continue

        if role == "reference_heading":
            break

        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            block["role"] = "backmatter_heading"
            block["_backmatter_regime"] = backmatter_form
            block["render_default"] = True
            continue

        if role in {"body_paragraph", "frontmatter_noise"}:
            block["role"] = "backmatter_body"
            block["_backmatter_regime"] = backmatter_form
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

    import re as _re

    # "received"/"published" intentionally excluded — too common in body text
    # ("she received her degree", "published works include...").
    # Only distinctive frontmatter vocabulary is used.
    furniture_signals = [
        "submitted",
        "accepted",
        "copyright",
        "\u00a9",
        "doi:",
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
    if any(_re.search(r"(?<!\w)" + _re.escape(s) + r"(?!\w)", lower_txt) for s in furniture_signals):
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

    Family-level profiles are layered on top of individual-role profiles for
    broader-baseline matching:

    - Non-body insert cluster members are validated against
      ``non_body_insert_family`` vs ``body_family`` — blocks that match
      body better are reinstated.
    - Weak heading/body disambiguation uses ``heading_family`` vs
      ``body_family`` when enough heading data exists.
    - Reference rescue compares against ``reference_family``.

    Never overrides: strong formal prefixes (Figure, Table), strong numbering,
    or explicit boundary-heading logic.

    Returns a new list of blocks with corrected roles.
    """
    from paperforge.worker.ocr_profiles import (
        build_family_profiles,
        compare_against_family,
        compare_against_role_family,
        extract_block_span_profile,
    )
    from paperforge.worker.ocr_roles import _has_heading_numbering

    if document_structure is None:
        document_structure = analyze_document_structure(blocks)

    family_profiles = build_family_profiles(blocks)

    body_end_page = document_structure.body_end_page
    refs_start = document_structure.references_start
    refs_start_page = refs_start.page if refs_start else None

    result = list(blocks)

    for block in result:
        # --- Non-body insert cluster validation via family profiles ---
        if block.get("_non_body_insert"):
            bp = extract_block_span_profile(block)
            should_skip = True  # default: keep flag, skip downstream rules

            # Geometry guard: narrow blocks stay non_body_insert even if font
            # matches body_family — narrowness is structural evidence of being
            # a profile/sidebar card, not a body paragraph.
            bbox = block.get("bbox", [0, 0, 0, 0])
            block_w = (bbox[2] - bbox[0]) if len(bbox) >= 4 else 0
            page_w = block.get("page_width", 0) or 0
            # Use body_family's per-page median_width from the spine, or
            # approximate from page_width.  Blocks narrower than 60% of the
            # expected body width are structurally incompatible with the spine.
            if block_w > 0 and page_w > 0:
                expected_body_min = page_w * 0.35  # ~420px on 1200px-wide page
                if block_w < expected_body_min:
                    # Definitely a narrow insert, not a body paragraph — keep.
                    continue

            if bp and "non_body_insert_family" in family_profiles and "body_family" in family_profiles:
                ni_fam = family_profiles["non_body_insert_family"]
                ni_quality = ni_fam.get("quality", "no_data")
                # Only trust family comparison when non_body_insert_family is
                # well-established (strong quality, low dispersion).  Moderate
                # profiles are unreliable because non_body_insert blocks are
                # naturally heterogeneous (different bio fonts/sizes).
                if ni_quality == "strong":
                    ni_match = compare_against_family(bp, ni_fam)
                    body_match = compare_against_family(bp, family_profiles["body_family"])
                    if body_match["match_score"] > max(ni_match["match_score"], 0.6) and body_match["size_compatible"]:
                        del block["_non_body_insert"]
                        block["role"] = "body_paragraph"
                        block.setdefault("evidence", []).append("rescue_family: non_body_insert → body_paragraph")
                        should_skip = False
            if should_skip:
                continue

        # --- Rule 1: frontmatter_noise → body_paragraph (body section + body font)
        if block.get("role") == "frontmatter_noise":
            page = block.get("page", 1) or 1
            if body_end_page is not None and page <= body_end_page:
                bp = extract_block_span_profile(block)
                if bp:
                    family_rescued = False
                    if "body_family" in family_profiles:
                        body_match = compare_against_family(bp, family_profiles["body_family"])
                        if body_match["size_compatible"] and body_match["match_score"] > 0.5:
                            block["role"] = "body_paragraph"
                            block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.1, 1.0)
                            block.setdefault("evidence", []).append("rescue_family: frontmatter_noise → body_paragraph")
                            family_rescued = True
                    if not family_rescued:
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
            bp = extract_block_span_profile(block)
            if bp:
                ref_rescued = False

                # Zone-based gate (layout-aware, column-scoped)
                ref_zones = document_structure.reference_zones
                p_layouts = document_structure.page_layouts
                in_reference_zone = False

                if ref_zones:
                    block_page = block.get("page", 1) or 1
                    bbox = block.get("bbox") or [0, 0, 0, 0]
                    x_center = (bbox[0] + bbox[2]) / 2 if len(bbox) >= 4 else 0
                    y_center = (bbox[1] + bbox[3]) / 2 if len(bbox) >= 4 else 0
                    p_layout = (p_layouts or {}).get(block_page)

                    for zone_data in ref_zones:
                        if zone_data.get("page") != block_page:
                            continue
                        zone_col = zone_data.get("column_index", 0)
                        if p_layout and p_layout.column_count > 1:
                            bcol = _get_column_index_by_boundaries(x_center, p_layout.column_boundaries)
                            if bcol != zone_col:
                                continue
                        if y_center >= zone_data.get("y_start", 0):
                            in_reference_zone = True
                            break

                page = block.get("page", 1) or 1
                if in_reference_zone or (not ref_zones and refs_start_page is not None and page >= refs_start_page):
                    if "reference_family" in family_profiles and "body_family" in family_profiles:
                        ref_fam_p = family_profiles["reference_family"]
                        if ref_fam_p.get("quality") in ("moderate", "strong"):
                            ref_match = compare_against_family(bp, ref_fam_p)
                            body_match_r = compare_against_family(bp, family_profiles["body_family"])
                            if (
                                ref_match["size_compatible"]
                                and ref_match["match_score"] > body_match_r["match_score"] + 0.1
                            ):
                                block["role"] = "reference_item"
                                block["role_confidence"] = min(block.get("role_confidence", 0.5) + 0.2, 1.0)
                                block.setdefault("evidence", []).append(
                                    "rescue_family: body_paragraph → reference_item"
                                )
                                ref_rescued = True
                    if not ref_rescued:
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
                heading_demoted = False
                if "heading_family" in family_profiles and "body_family" in family_profiles:
                    heading_fam = family_profiles["heading_family"]
                    if heading_fam.get("quality") in ("moderate", "strong"):
                        heading_match = compare_against_family(bp, heading_fam)
                        body_match_h = compare_against_family(bp, family_profiles["body_family"])
                        if (
                            body_match_h["size_compatible"]
                            and body_match_h["match_score"] > heading_match["match_score"] + 0.1
                        ):
                            block["role"] = "body_paragraph"
                            block.setdefault("evidence", []).append("rescue_family: heading → body_paragraph")
                            heading_demoted = True
                if not heading_demoted:
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
    page_layouts = _build_page_layout_profiles(blocks)
    tail_spread = _reconcile_tail_spread(blocks, page_layouts)
    if tail_spread is not None:
        backmatter_form = _classify_backmatter_form(tail_spread, blocks)
        _label_backmatter_regime(tail_spread, backmatter_form, blocks)
        _normalize_backmatter_roles_after_boundary(tail_spread, backmatter_form, blocks)
    else:
        backmatter_form = "flat"

    ds = DocumentStructure(
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
        page_layouts=page_layouts,
    )

    reading_segments = _build_tail_reading_order(blocks, page_layouts)
    ds.tail_reading_order = [dataclasses.asdict(seg) for seg in reading_segments] if reading_segments else None

    ref_zones = _detect_reference_zones(blocks, page_layouts)
    ds.reference_zones = [dataclasses.asdict(z) for z in ref_zones] if ref_zones else None

    return ds


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


def _detect_body_spine(blocks: list[dict]) -> dict[int, dict]:
    """Detect the main body column characteristics per page.

    Returns dict[page_num, {"median_width": float, "median_x": float,
                            "width_range": tuple[float, float]}]
    """
    import statistics

    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        page = block.get("page", 1)
        by_page.setdefault(page, []).append(block)

    all_pages = sorted(by_page.keys())
    if not all_pages:
        return {}

    # Collect body fonts across ALL pages (not just current page) to handle
    # early pages where body_paragraph blocks are themselves non-body inserts.
    all_body_fonts: set[str] = set()
    for page in all_pages:
        for b in by_page[page]:
            if b.get("role") == "body_paragraph":
                bbox = b.get("bbox", [0, 0, 0, 0])
                w = bbox[2] - bbox[0]
                if w >= 400:  # only wide blocks contribute to global font baseline
                    span = b.get("span_metadata") or {}
                    if isinstance(span, list):
                        for s in span:
                            fam = s.get("font", "")
                            if fam:
                                all_body_fonts.add(str(fam).lower())
                    elif isinstance(span, dict):
                        fam = span.get("font", "")
                        if fam:
                            all_body_fonts.add(str(fam).lower())

    per_page_spine: dict[int, dict | None] = {}
    for page in all_pages:
        page_blocks = by_page[page]
        body_blocks = [b for b in page_blocks if b.get("role") == "body_paragraph"]

        if body_blocks:
            widths = []
            x_starts = []
            fonts: set[str] = set()
            for b in body_blocks:
                bbox = b.get("bbox", [0, 0, 0, 0])
                widths.append(bbox[2] - bbox[0])
                x_starts.append(bbox[0])
                span = b.get("span_metadata") or {}
                if isinstance(span, list):
                    for s in span:
                        fam = s.get("font", "")
                        if fam:
                            fonts.add(str(fam).lower())
                elif isinstance(span, dict):
                    fam = span.get("font", "")
                    if fam:
                        fonts.add(str(fam).lower())

            # Robust body spine estimation: use widest cluster only,
            # rejecting narrow blocks (author profiles, etc.) that
            # would contaminate the median
            max_width = max(widths)
            core_widths = [w for w in widths if w >= 0.6 * max_width]
            median_width = statistics.median_low(core_widths) if core_widths else max_width
            median_x = statistics.median_low(x_starts)
            per_page_spine[page] = {
                "median_width": median_width,
                "median_x": median_x,
                "width_range": (median_width * 0.7, median_width * 1.3),
                "fonts": fonts,
                "all_fonts": all_body_fonts,
            }
        else:
            per_page_spine[page] = None

    filled: dict[int, dict] = {}
    prev_val = None
    for page in all_pages:
        if per_page_spine[page] is not None:
            prev_val = per_page_spine[page]
            filled[page] = prev_val
        elif prev_val is not None:
            filled[page] = prev_val
        else:
            next_val = None
            for p in all_pages:
                if p > page and per_page_spine[p] is not None:
                    next_val = per_page_spine[p]
                    break
            filled[page] = (
                prev_val
                or next_val
                or {
                    "median_width": 500,
                    "median_x": 100,
                    "width_range": (350, 650),
                    "fonts": set(),
                    "all_fonts": all_body_fonts,
                }
            )

    return filled


def _detect_non_body_insert_clusters(
    blocks: list[dict],
    body_spine: dict[int, dict],
    page_height: float = 1600,
    page_width: float = 1200,
    body_end_page: int | None = None,
) -> set[int]:
    """Return indices of blocks that belong to early-page non-body insert clusters.

    Detection criteria:
    1. Early document region (relative to body length, not an absolute page number)
    2. Block role is ``body_paragraph``, ``figure_caption``, or ``unknown_structural``
       (NOT frontmatter_noise — those are genuine furniture blocks)
       ``figure_caption`` is included because PaddleOCR sometimes labels narrow
       author-bio side-panel blocks as figure_title/figure_caption.
    Width signal: block width < 70% of body spine median,
      falling back to page_width * 0.5 if median is contaminated
    Font-family signal (secondary): block's font differs from body spine fonts
    Cluster requirement: 2+ candidates on the same page
    """
    indices: set[int] = set()

    # Use a relative early-page bound instead of an absolute page gate
    max_early_page = min(3, max(1, (body_end_page or 12) // 4 + 1))

    def _first_font(block: dict) -> str | None:
        span = block.get("span_metadata") or {}
        if isinstance(span, list):
            for s in span:
                fam = s.get("font", "")
                if fam:
                    return str(fam).lower()
        elif isinstance(span, dict):
            return str(span.get("font", "") or "").lower() or None
        return None

    candidates_by_page: dict[int, list[int]] = {}
    for i, block in enumerate(blocks):
        page = block.get("page", 1)
        if page > max_early_page:
            continue
        # body_paragraph, figure_caption, figure_caption_candidate, and
        # unknown_structural can be non-body inserts — bio/profile blocks that
        # OCR misclassified as body text or figure titles.  frontmatter_noise
        # blocks are genuine furniture, not bios, so they are excluded.
        _INSERT_CANDIDATE_ROLES = {"body_paragraph", "figure_caption", "figure_caption_candidate", "unknown_structural"}
        if block.get("role") not in _INSERT_CANDIDATE_ROLES:
            continue

        bbox = block.get("bbox", [0, 0, 0, 0])

        # Skip blocks without valid bbox (text-less spacers, rule lines)
        if len(bbox) < 4:
            continue
        block_width = bbox[2] - bbox[0]
        if block_width <= 10:
            continue

        spine_key = page if page in body_spine else 1
        spine = body_spine.get(spine_key, {"median_width": 500})
        median_width = spine.get("median_width", 500)
        if not isinstance(median_width, (int, float)) or median_width <= 0:
            median_width = 500

        is_narrow = block_width < 0.7 * median_width or (
            page_width > 0 and median_width < page_width * 0.4 and block_width < page_width * 0.35
        )

        block_font = _first_font(block)
        spine_fonts = spine.get("all_fonts") or spine.get("fonts", set())
        if not isinstance(spine_fonts, set):
            spine_fonts = set(spine_fonts) if spine_fonts else set()
        font_mismatch = bool(block_font and spine_fonts and block_font not in spine_fonts)

        if is_narrow or font_mismatch:
            candidates_by_page.setdefault(page, []).append(i)

    for candidate_indices in candidates_by_page.values():
        if len(candidate_indices) >= 2:
            indices.update(candidate_indices)

    # Second pass: expand to orphan continuation fragments adjacent to
    # detected non-body inserts.  These are body-width blocks (same width
    # as the body spine) that share a font with the insert cluster but
    # were split off by OCR and start with a lowercase letter (no
    # standalone paragraph start).
    if indices:
        insert_fonts: set[str] = set()
        for idx in indices:
            f = _first_font(blocks[idx])
            if f:
                insert_fonts.add(f)
        if insert_fonts:
            for i, block in enumerate(blocks):
                if i in indices:
                    continue
                page = block.get("page", 1)
                if page > max_early_page:
                    continue
                if block.get("role") not in _INSERT_CANDIDATE_ROLES:
                    continue
                text = block.get("text", "")
                if not text or not text[0].islower():
                    continue
                block_font = _first_font(block)
                if block_font and block_font in insert_fonts:
                    # Check adjacency to existing cluster members on the same page
                    for idx in indices:
                        if blocks[idx].get("page") == page and abs(i - idx) <= 2:
                            indices.add(i)
                            break

    return indices


def _looks_like_figure_narrative_prose(text: str) -> bool:
    """Detect narrative prose blocks that start with Fig. but are not formal legends."""
    sentence_count = text.count(". ") + text.count(".\n")
    if sentence_count >= 2:
        return True
    prose_markers = ["we ", "our ", "this study", "here we", "in this"]
    if any(m in text.lower() for m in prose_markers):
        return True
    return bool(re.search(r"\$?\^\{[^}]+\}\$?", text) and sentence_count >= 1)


def _check_caption_style_match(block: dict, blocks: list[dict]) -> bool:
    """Check if block's span style matches known figure_caption blocks."""
    span = block.get("span_metadata") or {}
    if isinstance(span, list):
        span = span[0] if span else {}
    block_size = span.get("size")
    block_font = str(span.get("font", "") or "").lower()
    if block_size is None:
        return False
    caption_sizes: list[float] = []
    caption_fonts: set[str] = set()
    for b in blocks:
        if b.get("role") == "figure_caption":
            s = b.get("span_metadata") or {}
            if isinstance(s, list):
                s = s[0] if s else {}
            sz = s.get("size")
            if sz is not None:
                caption_sizes.append(sz)
            fn = str(s.get("font", "") or "").lower()
            if fn:
                caption_fonts.add(fn)
    if not caption_sizes:
        return False
    size_match = any(abs(block_size - sz) <= 1.0 for sz in caption_sizes)
    font_match = (block_font in caption_fonts) if block_font else True
    return size_match and font_match


def _resolve_ambiguous_candidates(
    blocks: list[dict],
    doc_structure: DocumentStructure,
    page_layouts: dict[int, PageLayoutProfile],
) -> None:
    """Resolve candidate roles from seed pass into final roles using document context.

    Mutates blocks in place.
    """
    body_end_page = doc_structure.body_end_page
    backmatter_start_page: int | None = doc_structure.backmatter_start.page if doc_structure.backmatter_start else None
    references_start_page: int | None = doc_structure.references_start.page if doc_structure.references_start else None
    backmatter_form = doc_structure.backmatter_form

    # Detect container boundary heading (independent of form classification,
    # since form is determined before resolution promotes candidates)
    has_container_boundary = False
    container_boundary_page: int | None = None
    for b in blocks:
        if b.get("role") in _BOUNDARY_ROLES:
            has_container_boundary = True
            container_boundary_page = b.get("page")
            break

    def _child_heading_count(
        start_idx: int,
        page: int,
        col: int,
        boundaries: list[float],
    ) -> float:
        count = 0.0
        for j in range(start_idx + 1, min(start_idx + 10, len(blocks))):
            nb = blocks[j]
            if nb.get("page") != page:
                continue
            if len(boundaries) > 1:
                nbb = nb.get("bbox") or nb.get("block_bbox") or [0, 0, 0, 0]
                nx = (nbb[0] + nbb[2]) / 2
                ncol = _get_column_index_by_boundaries(nx, boundaries)
                if ncol != col:
                    continue
            nr = nb.get("role", "")
            if nr in ("backmatter_heading", "backmatter_heading_candidate"):
                count += 1.0
            elif nr == "backmatter_body":
                count += 0.5
        return count

    for i, block in enumerate(blocks):
        role = block.get("role", "")
        page = block.get("page", 1)
        bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]

        # ---- 2.1 Resolve backmatter_heading_candidate ----
        if role == "backmatter_heading_candidate":
            # Papers with a container boundary heading: headings on earlier
            # pages than the boundary are demoted to body_paragraph.  On the
            # same page, only headings in a different column than the boundary
            # (multi-column layout with independent streams) are kept visible.
            if has_container_boundary and page < container_boundary_page:
                block["role"] = "body_paragraph"
                block["role_confidence"] = 0.5
                continue

            if has_container_boundary and page == container_boundary_page:
                layout = page_layouts.get(page)
                _same_column = True  # single-column → same column
                if layout and layout.column_count > 1:
                    boundaries = layout.column_boundaries
                    x_center = (bbox[0] + bbox[2]) / 2
                    col = _get_column_index_by_boundaries(x_center, boundaries)
                    for b in blocks:
                        if b.get("role") in _BOUNDARY_ROLES and b.get("page") == page:
                            bb = b.get("bbox") or b.get("block_bbox") or [0, 0, 0, 0]
                            bx = (bb[0] + bb[2]) / 2
                            boundary_col = _get_column_index_by_boundaries(bx, boundaries)
                            _same_column = (col == boundary_col)
                            boundary_bottom = bb[3] if len(bb) > 3 else 0
                            break
                    else:
                        boundary_bottom = 0
                if _same_column and bbox[1] < boundary_bottom:
                    block["role"] = "body_paragraph"
                    block["role_confidence"] = 0.5
                    continue
                # Different column on boundary page → container child in
                # multi-column layout (e.g. FUNDING left col, ADDITIONAL
                # INFORMATION right col).  Promote to backmatter_heading.
                block["role"] = "backmatter_heading"
                block["role_confidence"] = 0.5
                continue

            if backmatter_start_page is None:
                block["role"] = "section_heading"
                block["role_confidence"] = 0.5
                block["_suppressed_heading"] = True
                continue

            if page < backmatter_start_page:
                if has_container_boundary and page == container_boundary_page:
                    block["role"] = "backmatter_heading"
                    block["role_confidence"] = 0.5
                else:
                    block["role"] = "section_heading"
                    block["role_confidence"] = 0.5
                    block["_suppressed_heading"] = True
                continue

            if page == backmatter_start_page:
                layout = page_layouts.get(page)
                if layout and layout.column_count > 1:
                    boundaries = layout.column_boundaries
                    x_center = (bbox[0] + bbox[2]) / 2
                    col = _get_column_index_by_boundaries(x_center, boundaries)
                    if col == 0:
                        block["role"] = "section_heading"
                        block["role_confidence"] = 0.5
                        continue
                block["role"] = "backmatter_heading"
                continue

            block["role"] = "backmatter_heading"

        # ---- 2.2 Resolve figure_caption_candidate ----
        if role == "figure_caption_candidate":
            text = block.get("text", "") or ""
            page_blocks = [b for b in blocks if b.get("page") == page]

            near_media = _is_near_figure_media(block, page_blocks)
            caption_style = _check_caption_style_match(block, blocks)
            is_prose = _looks_like_figure_narrative_prose(text)
            in_body_spine = body_end_page is not None and page <= body_end_page

            has_main_figure = bool(re.search(r'(?:Figure|Fig\.?)\s+\d+(?:\.\d+)?(?![a-z0-9])', text))
            has_subfigure_letter = bool(re.search(r'(?:Figure|Fig\.?)\s+\d+[a-z]', text))

            # Subfigure references (Fig. 26c) with narrative prose in body
            # spine are body mentions — hard reject regardless of style.
            if has_subfigure_letter and in_body_spine and is_prose:
                block["role"] = "body_paragraph"
                continue

            if near_media or caption_style or has_main_figure:
                block["role"] = "figure_caption"
                continue

            if in_body_spine and is_prose:
                block["role"] = "body_paragraph"
                continue

    # ---- 3. Activation gates (inline) ----
    for block in blocks:
        role = block.get("role", "")
        page = block.get("page", 1)

        if (
            role in ("backmatter_heading", "backmatter_body")
            and backmatter_start_page is not None
            and page < backmatter_start_page
            and backmatter_form != "container"
        ):
            block["role"] = "body_paragraph"

        if (
            role == "reference_item"
            and references_start_page is not None
            and page < references_start_page
        ):
            block["role"] = "body_paragraph"

        if role == "backmatter_heading_candidate" and body_end_page is not None and page <= body_end_page:
            block["role"] = "body_paragraph"


def _mark_non_body_media(blocks: list[dict]) -> None:
    insert_blocks_by_page: dict[int, list[dict]] = {}
    for block in blocks:
        if block.get("_non_body_insert"):
            page = block.get("page", 1)
            insert_blocks_by_page.setdefault(page, []).append(block)

    if not insert_blocks_by_page:
        return

    for page, inserts in insert_blocks_by_page.items():
        bboxes = []
        for ins in inserts:
            b = ins.get("bbox") or ins.get("block_bbox")
            if b and len(b) >= 4:
                bboxes.append(b)
        if not bboxes:
            continue

        cluster_min_x = min(b[0] for b in bboxes)
        cluster_min_y = min(b[1] for b in bboxes)
        cluster_max_x = max(b[2] for b in bboxes)
        cluster_max_y = max(b[3] for b in bboxes)

        margin = 50
        cluster_min_x -= margin
        cluster_min_y -= margin
        cluster_max_x += margin
        cluster_max_y += margin

        for block in blocks:
            if block.get("page", 1) != page:
                continue
            if block.get("_non_body_media"):
                continue
            role = block.get("role", "")
            if role not in ("figure_asset", "media_asset"):
                continue

            b = block.get("bbox") or block.get("block_bbox")
            if not b or len(b) < 4:
                continue

            cx = (b[0] + b[2]) / 2
            cy = (b[1] + b[3]) / 2

            if cluster_min_x <= cx <= cluster_max_x and cluster_min_y <= cy <= cluster_max_y:
                block["_non_body_media"] = True


def normalize_document_structure(blocks: list[dict]) -> tuple[DocumentStructure, list[dict]]:
    """Analyze document structure and normalize roles.

    Returns (document_structure, normalized_blocks).
    Normalization includes:
    - backmatter form classification
    - backmatter role normalization after boundary
    - tail body candidate promotion
    - tail spread ownership assignment
    """
    page_layouts = _build_page_layout_profiles(blocks)

    tail_spread = _reconcile_tail_spread(blocks, page_layouts)
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
        page_layouts=page_layouts,
    )

    header_band, footer_band = _estimate_noise_bands(blocks)

    reading_segments = _build_tail_reading_order(blocks, page_layouts)
    doc_structure.tail_reading_order = (
        [dataclasses.asdict(seg) for seg in reading_segments] if reading_segments else None
    )

    ref_zones = _detect_reference_zones(blocks, page_layouts)
    doc_structure.reference_zones = [dataclasses.asdict(z) for z in ref_zones] if ref_zones else None

    blocks = _promote_tail_body_candidates(blocks, doc_structure, header_band=header_band, footer_band=footer_band)
    blocks = _assign_tail_spread_ownership(blocks, doc_structure)

    # Detect non-body insert clusters on early pages (relative to body length)
    body_spine = _detect_body_spine(blocks)
    pw = max((b.get("page_width", 0) or 0) for b in blocks) or 1200
    insert_indices = _detect_non_body_insert_clusters(
        blocks,
        body_spine,
        page_width=pw,
        body_end_page=tail_spread.body_end_page if tail_spread else None,
    )
    for idx in insert_indices:
        if idx < len(blocks):
            blocks[idx]["role"] = "non_body_insert"
            blocks[idx]["_non_body_insert"] = True

    _mark_non_body_media(blocks)
    _resolve_ambiguous_candidates(blocks, doc_structure, page_layouts)

    return doc_structure, blocks
