from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from paperforge.worker.ocr_document import (
    _TAIL_ROLES,
    DocumentStructure,
    _estimate_noise_bands,
    _get_column,
    _is_in_usable_content,
)
from paperforge.worker.ocr_math import normalize_ocr_math_text
from paperforge.worker.ocr_roles import FRONTMATTER_NOISE

_BACKMATTER_HEADING_KEYWORDS: frozenset[str] = frozenset(
    {
        "author contributions",
        "data availability",
        "funding",
        "acknowledg",
        "conflict of interest",
        "competing interests",
        "supplementary material",
        "ethics statement",
        "publisher",
        "biographies",
    }
)


def _should_suppress_frontmatter_heading(text: str) -> bool:
    lower = text.strip().lower()
    if not lower:
        return True
    if lower in FRONTMATTER_NOISE:
        return True
    if "published online" in lower:
        return True
    return False


def _display_heading_text(block: dict, text: str) -> str:
    marker_type = str(((block.get("marker_signature") or {}).get("type")) or "none")
    match = re.match(r"^(\d+)\s+(.+)$", text.strip())
    if marker_type == "heading_numbered" and match:
        return f"{match.group(1)}. {match.group(2)}"
    return text


def _is_bogus_heading(text: str) -> bool:
    t = text.strip()
    if len(t) > 100:
        return True
    if t.count(". ") > 1:
        return True
    return any(v in t.lower().split() for v in ["is", "are", "was", "were", "have", "has", "been"]) and len(t) > 50


def _has_tail_role(block: dict) -> bool:
    return block.get("role") in _TAIL_ROLES


def _can_apply_tail_segment_reorder(document_structure: DocumentStructure | None) -> bool:
    if document_structure is None:
        return False
    if not document_structure.tail_reading_order or document_structure.spread_start is None:
        return False
    tail_score = getattr(document_structure, "tail_boundary_score", {}) or {}
    if float(tail_score.get("score", 1.0)) < 0.4:
        return False
    page_layouts = getattr(document_structure, "page_layouts", None) or {}
    for page in range(
        document_structure.spread_start, (document_structure.spread_end or document_structure.spread_start) + 1
    ):
        profile = page_layouts.get(page)
        if profile is not None and float(getattr(profile, "confidence", 1.0)) < 0.4:
            return False
    return True


def _heading_number_depth_text(text: str) -> int:
    match = re.match(r"^(\d+(?:\.\d+)*)", text.strip())
    if not match:
        return 0
    return match.group(1).count(".") + 1


def _table_html_to_lines(text: str) -> list[str]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.IGNORECASE | re.DOTALL)
    lines: list[str] = []
    for row in rows:
        cells = [
            unescape(re.sub(r"<[^>]+>", "", cell)).strip()
            for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL)
        ]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue
        if len(cells) == 1:
            lines.append(cells[0])
        else:
            lines.append(" | ".join(cells))
    return lines


def _find_owning_heading(
    body: dict,
    sections: list[dict],
    page_width: float = 1200,
) -> int | None:
    body_bbox = body.get("bbox") or body.get("block_bbox")
    if not body_bbox or len(body_bbox) < 4:
        return None

    body_y = body_bbox[1]
    body_col = _get_column(body, page_width)
    body_width = body_bbox[2] - body_bbox[0]

    candidates: list[tuple[int, float]] = []
    for i, sec in enumerate(sections):
        h = sec["heading"]
        h_bbox = h.get("bbox") or h.get("block_bbox")
        if not h_bbox or len(h_bbox) < 4:
            continue
        h_bottom = h_bbox[3]
        if h_bottom > body_y:
            continue
        h_col = _get_column(h, page_width)
        dist = body_y - h_bottom
        horizontal_overlap = max(0.0, min(body_bbox[2], h_bbox[2]) - max(body_bbox[0], h_bbox[0]))
        if body_width >= page_width * 0.45 and horizontal_overlap > 0:
            col_penalty = 0.0
        else:
            col_penalty = 0.0 if h_col == body_col else 10000.0
        candidates.append((i, dist + col_penalty))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


from paperforge.worker.ocr_profiles import extract_block_span_profile as _extract_style_profile


def _build_heading_style_profiles(blocks: list[dict]) -> dict:
    heading_roles = frozenset(
        {
            "backmatter_boundary_heading",
            "section_heading",
            "subsection_heading",
            "sub_subsection_heading",
            "backmatter_heading",
            "reference_heading",
        }
    )
    heading_items = []

    for block in blocks:
        if block.get("role") in heading_roles:
            profile = _extract_style_profile(block)
            if profile is not None:
                heading_items.append(
                    {
                        "max_size": profile["max_size"],
                        "mean_size": profile["mean_size"],
                        "profile": profile,
                        "block": block,
                    }
                )

    if len(heading_items) < 3:
        return {}

    # Use max_size for clustering — section headings often have slightly larger
    # first characters, making max_size more discriminating than mean.
    unique_sizes = sorted(set(item["max_size"] for item in heading_items))
    if not unique_sizes:
        return {}

    clusters = []
    current = [unique_sizes[0]]
    for s in unique_sizes[1:]:
        if s <= current[-1] + 2.0:
            current.append(s)
        else:
            clusters.append(current)
            current = [s]
    clusters.append(current)

    # Build full profile data for each cluster
    cluster_items = []
    for cluster_sizes in clusters:
        matching = [item for item in heading_items if any(abs(item["max_size"] - s) <= 2 for s in cluster_sizes)]
        cluster_items.append(matching)

    # Sort clusters by max_size descending to establish hierarchy level
    clusters.sort(key=lambda c: max(c), reverse=True)
    cluster_items.sort(key=lambda items: max(i["max_size"] for i in items), reverse=True)

    keys = ["primary", "subsection", "sub_subsection", "backmatter", "body"]
    result = {}
    for i, (cluster_sizes, items) in enumerate(zip(clusters, cluster_items, strict=False)):
        if i >= len(keys):
            break

        profiles = [item["profile"] for item in items]

        is_bold = any(p["is_bold"] for p in profiles)
        fonts = set()
        for p in profiles:
            fonts.update(p["font_families"])

        # Compute spacing before/after by searching ALL blocks on the same page
        space_before_vals = []
        space_after_vals = []
        for item in items:
            heading_block = item["block"]
            heading_page = heading_block.get("page")
            heading_bbox = heading_block.get("bbox") or heading_block.get("block_bbox")
            if heading_bbox and len(heading_bbox) >= 4 and heading_page is not None:
                h_y1 = heading_bbox[1]
                h_y2 = heading_bbox[3]

                nearest_above_bottom = None
                nearest_below_top = None
                for other in blocks:
                    if other is heading_block:
                        continue
                    if other.get("page") == heading_page:
                        obbox = other.get("bbox") or other.get("block_bbox")
                        if obbox and len(obbox) >= 4:
                            o_y2 = obbox[3]
                            o_y1 = obbox[1]
                            if o_y2 <= h_y1 and (nearest_above_bottom is None or o_y2 > nearest_above_bottom):
                                nearest_above_bottom = o_y2
                            if o_y1 >= h_y2 and (nearest_below_top is None or o_y1 < nearest_below_top):
                                nearest_below_top = o_y1

                if nearest_above_bottom is not None:
                    space_before_vals.append(h_y1 - nearest_above_bottom)
                if nearest_below_top is not None:
                    space_after_vals.append(nearest_below_top - h_y2)

        space_before = sum(space_before_vals) / len(space_before_vals) if space_before_vals else 0.0
        space_after = sum(space_after_vals) / len(space_after_vals) if space_after_vals else 0.0

        result[keys[i]] = {
            "size_min": min(cluster_sizes),
            "size_max": max(cluster_sizes),
            "bold": is_bold,
            "fonts": fonts,
            "space_before": space_before,
            "space_after": space_after,
        }

    return result


def _disambiguate_heading_role(
    block: dict,
    style_profiles: dict,
    role_profiles: dict | None = None,
) -> str | None:
    profile = _extract_style_profile(block)
    if profile is None:
        return None

    # Try role profiles first (persistent, aggregated across papers)
    if role_profiles:
        from paperforge.worker.ocr_profiles import compare_against_role_family

        for candidate_role in (
            "section_heading",
            "subsection_heading",
            "sub_subsection_heading",
            "backmatter_heading",
        ):
            fam = role_profiles.get(candidate_role)
            if fam and fam.get("quality") in ("strong", "moderate"):
                match = compare_against_role_family(profile, fam)
                if match["size_compatible"] and match["match_score"] > 0.6:
                    return candidate_role

    size = profile["mean_size"]
    for role_key, role_name in [
        ("primary", "section_heading"),
        ("subsection", "subsection_heading"),
        ("sub_subsection", "sub_subsection_heading"),
        ("backmatter", "backmatter_heading"),
        ("body", None),
    ]:
        cfg = style_profiles.get(role_key)
        if cfg is None:
            continue
        if cfg["size_min"] <= size <= cfg["size_max"]:
            if role_key == "backmatter":
                if profile["is_bold"]:
                    return role_name
                return None
            elif role_key == "body":
                return None
            return role_name

    return None


def _attach_container_bodies(
    body_pool: list[dict],
    backmatter_sections: list[dict],
    page_width: float,
    ref_section: dict | None,
) -> list[dict]:
    """Attach container-regime bodies to their nearest heading above.

    Bodies with ``_backmatter_regime == "container"`` are matched to the
    nearest backmatter heading (boundary or child) via geometric ownership.
    Bodies that cannot find a heading above them fall through to the boundary
    heading section.  Returns the remaining (non-container) bodies so the
    caller can continue with generic Phase 4 processing.
    """
    remaining: list[dict] = []
    for body in body_pool:
        if body.get("_backmatter_regime") != "container":
            remaining.append(body)
            continue
        idx = _find_owning_heading(body, backmatter_sections, page_width)
        if idx is not None:
            backmatter_sections[idx]["bodies"].append(body)
        else:
            boundary_idx = next(
                (
                    i
                    for i, s in enumerate(backmatter_sections)
                    if s["heading"].get("role") == "backmatter_boundary_heading"
                ),
                None,
            )
            if boundary_idx is not None:
                backmatter_sections[boundary_idx]["bodies"].append(body)
            else:
                remaining.append(body)
    return remaining


def _reorder_tail_run(
    tail_blocks: list[dict],
    carried_ref: dict | None = None,
    carried_backmatter: dict | None = None,
    header_band: float | None = None,
    footer_band: float | None = None,
    page_width: float = 1200,
) -> tuple[list[dict], dict | None, dict | None]:
    """Group tail blocks using geometric ownership and reference zone.

    Non-tail pass blocks (body_paragraph, tail_candidate_body, etc.) are
    emitted first, preserving their natural page order.  Backmatter sections
    (heading + body) are emitted next in column-sorted order.  References
    zone (heading + all items below it) is emitted last.  Body blocks are
    attached to the nearest backmatter heading above them in the same column,
    falling back to absolute proximity with a cross-column penalty.

    When blocks lack bbox data, falls back to FIFO matching for backward
    compatibility.
    """
    if not tail_blocks:
        return tail_blocks, carried_ref

    # Quick check: do blocks have bbox data?  If not, use FIFO fallback.
    has_geo = any(
        block.get("bbox") or block.get("block_bbox")
        for block in tail_blocks
        if block.get("role") in ("backmatter_heading", "reference_heading", "backmatter_body")
    )

    if not has_geo:
        ordered, next_ref = _reorder_tail_run_fifo(tail_blocks, carried_ref)
        return ordered, next_ref, carried_backmatter

    backmatter_sections: list[dict] = []
    ref_section: dict | None = carried_ref
    ref_items: list[dict] = []
    non_tail_pass: list[dict] = []
    orphan_blocks: list[dict] = []
    carried_bodies: list[dict] = []

    # Phase 1 — classify
    body_pool: list[dict] = []
    for block in tail_blocks:
        role = block.get("role")
        if role in ("backmatter_boundary_heading", "backmatter_heading"):
            backmatter_sections.append({"heading": block, "bodies": []})
        elif role == "reference_heading":
            ref_section = {"heading": block, "bodies": []}
        elif role == "reference_item":
            if _is_in_usable_content(block, header_band, footer_band):
                ref_items.append(block)
            else:
                non_tail_pass.append(block)
        elif role == "backmatter_body":
            if _is_in_usable_content(block, header_band, footer_band):
                body_pool.append(block)
            else:
                non_tail_pass.append(block)
        elif role == "body_paragraph":
            if _is_in_usable_content(block, header_band, footer_band):
                idx = _find_owning_heading(block, backmatter_sections, page_width) if backmatter_sections else None
                if idx is not None:
                    backmatter_sections[idx]["bodies"].append(block)
                else:
                    non_tail_pass.append(block)
            else:
                non_tail_pass.append(block)
        else:
            non_tail_pass.append(block)

    # Phase 2 — build references zone
    ref_heading = ref_section.get("heading") if ref_section and ref_section is not carried_ref else None
    ref_bottom: float = 0.0
    if ref_heading:
        rh_bbox = ref_heading.get("bbox") or ref_heading.get("block_bbox")
        if rh_bbox and len(rh_bbox) >= 4:
            ref_bottom = rh_bbox[3]

    # Phase 3 — assign ref items to zone, backmatter bodies to body pool
    for block in ref_items:
        if ref_heading:
            bbox = block.get("bbox") or block.get("block_bbox")
            if bbox and len(bbox) >= 4 and bbox[1] >= ref_bottom:
                ref_section["bodies"].append(block)
            else:
                body_pool.append(block)
        else:
            body_pool.append(block)

    # Phase 4a — container regime body attachment (run before generic
    # body loop so container bodies are matched to their specific child
    # heading rather than falling through to ref-section absorption)
    body_pool = _attach_container_bodies(body_pool, backmatter_sections, page_width, ref_section)

    # Phase 4b — geometric body attachment for remaining bodies
    first_local_anchor_top: float | None = None
    local_heading_tops = []
    for sec in backmatter_sections:
        bbox = sec["heading"].get("bbox") or sec["heading"].get("block_bbox")
        if bbox and len(bbox) >= 4:
            local_heading_tops.append(bbox[1])
    if ref_heading:
        bbox = ref_heading.get("bbox") or ref_heading.get("block_bbox")
        if bbox and len(bbox) >= 4:
            local_heading_tops.append(bbox[1])
    if local_heading_tops:
        first_local_anchor_top = min(local_heading_tops)

    for body in body_pool:
        idx = _find_owning_heading(body, backmatter_sections, page_width)
        if idx is not None:
            backmatter_sections[idx]["bodies"].append(body)
        elif carried_backmatter is not None:
            bbox = body.get("bbox") or body.get("block_bbox")
            if bbox and len(bbox) >= 4:
                body_top = bbox[1]
                if (first_local_anchor_top is None or body_top < first_local_anchor_top) and (
                    not ref_heading or body_top < ref_bottom
                ):
                    carried_bodies.append(body)
                    continue
        elif ref_section is not None:
            if ref_section is carried_ref:
                ref_section["bodies"].append(body)
                orphan_blocks.append(body)
            else:
                ref_section["bodies"].append(body)
        else:
            orphan_blocks.append(body)

    # Phase 5 — emit: non-tail pass (frontmatter), then backmatter
    # sections sorted by y-position (boundary-level and sub-headings
    # emit in reading order), then reference sections.  The y-sort is
    # applied only to backmatter_sections to avoid carrying cross-page
    # relationship artifacts from previous pages' carried blocks.
    result: list[dict] = []
    result.extend(non_tail_pass)
    result.extend(carried_bodies)
    sec_order = sorted(
        backmatter_sections,
        key=lambda s: [
            (s["heading"].get("bbox") or s["heading"].get("block_bbox") or [0, 0, 0, 0])[1],
            (s["heading"].get("bbox") or s["heading"].get("block_bbox") or [0, 0, 0, 0])[0],
        ],
    )
    for sec in sec_order:
        h = sec["heading"]
        result.append(h)
        result.extend(sec["bodies"])
    if ref_section is not None and ref_section is not carried_ref:
        result.append(ref_section["heading"])
        result.extend(ref_section["bodies"])
    result.extend(orphan_blocks)

    next_backmatter = carried_backmatter
    if backmatter_sections:
        next_backmatter = backmatter_sections[-1]["heading"]
    if ref_section is not None and ref_section is not carried_ref:
        next_backmatter = None

    return result, ref_section if ref_section else carried_ref, next_backmatter


def _reorder_tail_run_fifo(
    tail_blocks: list[dict],
    carried_ref: dict | None = None,
) -> tuple[list[dict], dict | None]:
    """FIFO fallback for blocks without bbox data."""
    backmatter_sections: list[dict] = []
    ref_section: dict | None = carried_ref
    heading_queue: list[dict] = []
    orphan_bodies: list[dict] = []
    orphan_ref_items: list[dict] = []
    non_tail_pass: list[dict] = []

    for block in tail_blocks:
        role = block.get("role")
        if role in ("backmatter_boundary_heading", "backmatter_heading"):
            sec = {"heading": block, "bodies": []}
            backmatter_sections.append(sec)
            heading_queue.append(sec)
        elif role == "reference_heading":
            ref_section = {"heading": block, "bodies": []}
        elif role == "backmatter_body":
            if heading_queue:
                heading_queue.pop(0)["bodies"].append(block)
            elif ref_section is not None:
                if ref_section is carried_ref:
                    orphan_ref_items.append(block)
                else:
                    ref_section["bodies"].append(block)
            else:
                orphan_bodies.append(block)
        elif role == "subsection_heading" and backmatter_sections:
            # In FIFO fallback with active backmatter context, subsection
            # headings (e.g. "Grant Disclosures") are container child
            # headings, not generic non-tail pass blocks.
            sec = {"heading": block, "bodies": []}
            backmatter_sections.append(sec)
            heading_queue.append(sec)
        elif role == "body_paragraph":
            non_tail_pass.append(block)
        elif role == "reference_item":
            if ref_section is not None:
                if ref_section is carried_ref:
                    orphan_ref_items.append(block)
                else:
                    ref_section["bodies"].append(block)
            else:
                orphan_ref_items.append(block)
        else:
            non_tail_pass.append(block)

    result: list[dict] = []
    result.extend(non_tail_pass)
    boundary_secs = [s for s in backmatter_sections if s["heading"].get("role") == "backmatter_boundary_heading"]
    sub_secs = [s for s in backmatter_sections if s["heading"].get("role") != "backmatter_boundary_heading"]
    for sec in boundary_secs + sub_secs:
        h = sec["heading"]
        result.append(h)
        result.extend(sec["bodies"])
    if ref_section is not None and ref_section is not carried_ref:
        result.append(ref_section["heading"])
        result.extend(ref_section["bodies"])
    result.extend(orphan_bodies)
    result.extend(orphan_ref_items)

    return result, ref_section


def _sort_blocks_by_column(blocks: list[dict], page_width: int) -> list[dict]:
    """Sort blocks on a page into natural reading order (left col then right
    col, top to bottom within each column), using bbox x/y positions.
    Blocks without bbox data are left in their original relative order.
    """
    midpoint = page_width / 2

    def _column_key(block: dict) -> tuple[int, int, int]:
        bbox = block.get("bbox") or block.get("block_bbox")
        if bbox and len(bbox) >= 4:
            x_center = (bbox[0] + bbox[2]) / 2
            col = 0 if x_center < midpoint else 1
            return (col, bbox[1], bbox[0])
        return (0, 0, 0)

    return sorted(blocks, key=_column_key)


def _order_tail_blocks(
    blocks: list[dict], style_profiles: dict | None = None, *, has_verified_reference_zone: bool = False
) -> list[dict]:
    """Fix block reading order on tail pages with mixed-column layout.

    Two-column tail pages can have blocks in non-reading order (e.g.
    left-column References at y=705 placed between right-column Gen AI
    heading at y=154 and Pub note heading at y=297).  This sorts all
    blocks on such pages by (column, y-position), then groups them into
    backmatter sections and a references zone using geometric ownership.

    Blocks are expected to already have normalized roles.  Non-tail pages
    are untouched.
    """
    if not blocks:
        return blocks

    header_band, footer_band = _estimate_noise_bands(blocks)

    # Find pages that contain tail blocks and their page widths.
    # Skip pages where body_paragraph blocks outnumber tail-role blocks —
    # these are mixed pages (e.g. body continuation + backmatter on same
    # page) where tail reordering would break reading order.
    _body_count: dict[int, int] = {}
    _tail_count: dict[int, int] = {}
    for block in blocks:
        p = block.get("page")
        if p is None:
            continue
        if _has_tail_role(block):
            _tail_count[p] = _tail_count.get(p, 0) + 1
        elif block.get("role") == "body_paragraph":
            _body_count[p] = _body_count.get(p, 0) + 1

    tail_pages: set[int] = set()
    page_widths: dict[int, int] = {}
    for block in blocks:
        page = block.get("page")
        if page is None:
            continue
        if _has_tail_role(block):
            if _body_count.get(page, 0) > _tail_count.get(page, 0):
                continue
            tail_pages.add(page)
        pw = block.get("page_width") or 0
        if pw:
            page_widths.setdefault(page, pw)

    if not tail_pages:
        return blocks

    # Group blocks by page
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        p = block.get("page")
        if p is not None:
            by_page.setdefault(p, []).append(block)

    # For tail pages: column-sort then group into sections using
    # geometric ownership that handles cross-column body attachment
    # and references zone boundaries.
    carried_ref: dict | None = None
    carried_backmatter: dict | None = None
    result: list[dict] = []
    for page in sorted(by_page.keys()):
        page_blocks = by_page[page]
        if page in tail_pages:
            pw = page_widths.get(page, 1200)
            sorted_blocks = _sort_blocks_by_column(page_blocks, pw)
            ordered, carried_ref, carried_backmatter = _reorder_tail_run(
                sorted_blocks,
                carried_ref,
                carried_backmatter,
                header_band=header_band,
                footer_band=footer_band,
                page_width=pw,
            )
            result.extend(ordered)
        else:
            result.extend(page_blocks)

    # When a verified reference_zone artifact is available on
    # the DocumentStructure, the caller handles reference ordering.
    # Fall back to conventional non_ref + refs only when no such
    # artifact exists (legacy callers without document structure).
    if not has_verified_reference_zone:
        ref_roles = frozenset({"reference_heading", "reference_item", "reference_body"})
        non_ref = [b for b in result if b.get("role") not in ref_roles]
        refs = [b for b in result if b.get("role") in ref_roles]
        return non_ref + refs
    return result


def _render_reader_figure_card(figure: dict) -> list[str]:
    lines: list[str] = []
    caption_text = figure.get("caption_text", "")
    fn = figure.get("figure_number")
    if fn is not None and caption_text:
        lines.append(f"> **Figure {fn}**")
    if not caption_text:
        return []
    lines.append(f"> {caption_text}")
    return lines


def _reader_figure_embed_target(figure: dict) -> str | None:
    status = str(figure.get("reader_status") or "")
    figure_number = figure.get("figure_number")
    if status not in {"EXACT_MATCH", "SEQUENCE_MATCH"}:
        return None
    if figure_number is None:
        return None
    return f"figure_{int(figure_number):03d}"


def _page_block_key(block_or_page: dict | int | None, block_id: int | str | None = None) -> tuple[int | None, int | str] | None:
    if isinstance(block_or_page, dict):
        page = block_or_page.get("page")
        bid = block_or_page.get("block_id")
    else:
        page = block_or_page
        bid = block_id
    if bid is None:
        return None
    return (page, bid)


def _emit_page_objects(
    lines: list[str],
    page: int,
    *,
    figures_by_page: dict[int, list[dict]],
    unresolved_clusters_by_page: dict[int, list[str]],
    tables_by_page: dict[int, list[str]],
    reader_figures_by_page: dict[int, list[dict]],
    rendered_reader_figure_ids: set[str],
    emitted_figure_captions: set[str],
) -> None:
    """Emit figure/table/reader objects for a single page.

    Reader figures are primary: when present, legacy matched_figures and
    unresolved_clusters are skipped for that page.
    """
    has_reader = bool(reader_figures_by_page.get(page))

    if not has_reader:
        for fig in figures_by_page.get(page, []):
            if str(fig["figure_id"]).startswith("unmatched_legend_"):
                continue
            lines.append(f"![[render/figures/{fig['figure_id']}.md]]")
            lines.append("")
    if not has_reader:
        for cluster_id in unresolved_clusters_by_page.get(page, []):
            if not cluster_id:
                continue
            lines.append(f"![[render/figures/{cluster_id}.md]]")
            lines.append("")

    for tbl_id in tables_by_page.get(page, []):
        lines.append(f"![[render/tables/{tbl_id}.md]]")
        lines.append("")

    for rf in reader_figures_by_page.get(page, []):
        rfid = rf.get("reader_figure_id")
        if rfid and rfid not in rendered_reader_figure_ids:
            rendered_reader_figure_ids.add(rfid)
            lines.extend(_render_reader_figure_card(rf))
            embed_target = _reader_figure_embed_target(rf)
            if embed_target:
                lines.append(f"![[render/figures/{embed_target}.md]]")
            lines.append("")


def _emit_reader_figures_before_references(
    lines: list[str],
    *,
    start_page: int,
    reader_figures_by_page: dict[int, list[dict]],
    rendered_reader_figure_ids: set[str],
) -> None:
    for page in sorted(p for p in reader_figures_by_page if p >= start_page):
        for rf in reader_figures_by_page.get(page, []):
            rfid = rf.get("reader_figure_id")
            if not rfid or rfid in rendered_reader_figure_ids:
                continue
            rendered_reader_figure_ids.add(rfid)
            lines.extend(_render_reader_figure_card(rf))
            embed_target = _reader_figure_embed_target(rf)
            if embed_target:
                lines.append(f"![[render/figures/{embed_target}.md]]")
            lines.append("")


def render_fulltext_markdown(
    *,
    structured_blocks: list[dict],
    resolved_metadata: dict,
    figure_inventory: dict,
    table_inventory: dict,
    page_count: int | None = None,
    document_structure: DocumentStructure | None = None,
    reader_payload: dict | None = None,
) -> str:
    lines: list[str] = []

    emitted_figure_captions: set[str] = set()

    reader_figures = (reader_payload or {}).get("reader_figures", [])
    consumed_caption_keys: set[tuple[int | None, int | str]] = set()
    consumed_caption_ids_unkeyed: set[int | str] = set()
    for item in (reader_payload or {}).get("consumed_caption_block_ids", []):
        if isinstance(item, dict):
            page = item.get("page")
            block_id = item.get("block_id")
        else:
            block_id = item
            page = None
        if block_id is not None:
            consumed_caption_keys.add((page, block_id))
            if page is None:
                consumed_caption_ids_unkeyed.add(block_id)
    rendered_reader_figure_ids: set[str] = set()

    _block_page_map: dict[int, int] = {}
    for block in structured_blocks:
        bid = block.get("block_id")
        bp = block.get("page")
        if bid is not None and bp is not None:
            _block_page_map[bid] = bp

    reader_figures_by_page: dict[int, list[dict]] = {}
    for rf in reader_figures:
        rfid = rf.get("reader_figure_id")
        if not rfid:
            continue
        page = None
        for item in rf.get("consumed_caption_block_ids", []):
            p = item.get("page") if isinstance(item, dict) else None
            if p is not None:
                page = p
                break
        if page is None:
            for item in rf.get("consumed_asset_block_ids", []):
                p = item.get("page") if isinstance(item, dict) else None
                if p is not None:
                    page = p
                    break
        if page is None:
            page = 1
        reader_figures_by_page.setdefault(page, []).append(rf)

    _block_text_by_bid: dict[str, str] = {}
    for block in structured_blocks:
        bid = block.get("block_id")
        if bid is not None and block.get("text"):
            _block_text_by_bid[str(bid)] = block.get("text", "")

    for rf in reader_figures:
        if not rf.get("caption_text"):
            for cid in rf.get("consumed_caption_block_ids", []):
                cid_str = str(cid)
                if cid_str in _block_text_by_bid:
                    rf["caption_text"] = _block_text_by_bid[cid_str]
                    break

    # --- title ---
    title = resolved_metadata.get("title", {}).get("value", "")
    if title:
        lines.append(f"# {title}")
        lines.append("")

    # --- authors ---
    authors_display = resolved_metadata.get("authors_display", "")
    if not authors_display:
        authors = resolved_metadata.get("authors", {}).get("value", [])
        if authors:
            authors_display = ", ".join(authors)
    if authors_display:
        lines.append(f"**Authors:** {authors_display}")
        lines.append("")

    # --- metadata block ---
    journal = resolved_metadata.get("journal", {}).get("value", "")
    year = resolved_metadata.get("year", {}).get("value", 0)
    doi = resolved_metadata.get("doi", {}).get("value", "")
    meta_parts: list[str] = []
    if journal:
        meta_parts.append(f"**Journal:** {journal}")
    if year:
        meta_parts.append(f"**Year:** {year}")
    if doi:
        meta_parts.append(f"**DOI:** {doi}")
    if meta_parts:
        lines.extend(meta_parts)
        lines.append("")

    # --- abstract ---
    if document_structure is not None and getattr(document_structure, "abstract_span", None):
        span = document_structure.abstract_span
        block_by_id = {}
        for block in structured_blocks:
            block_id = block.get("block_id")
            if block_id is not None:
                block_by_id[block_id] = block
                block_by_id[f"p{int(block.get('page', 0) or 0)}:{block_id}"] = block
        abstract_ids = [span.get("heading_block_id"), *span.get("body_block_ids", [])]
        abstract_blocks = [
            block_by_id[bid]
            for bid in abstract_ids
            if bid in block_by_id
        ]
    else:
        _ABSTRACT_ROLES_FALLBACK = frozenset({"abstract_heading", "abstract_body"})
        abstract_blocks = [
            b for b in structured_blocks if b.get("role") in _ABSTRACT_ROLES_FALLBACK and b.get("render_default", True)
        ]
    abstract_member_keys = {
        _page_block_key(block)
        for block in abstract_blocks
        if _page_block_key(block) is not None
    }
    abstract_member_ids_unkeyed = {
        block.get("block_id")
        for block in abstract_blocks
        if block.get("block_id") is not None and block.get("page") is None
    }
    abstract_heading_block_id = (getattr(document_structure, "abstract_span", None) or {}).get("heading_block_id")
    if abstract_blocks:
        lines.append("## Abstract")
        lines.append("")
        for block in abstract_blocks:
            block_key = _page_block_key(block)
            page_qualified_id = None
            if block.get("block_id") is not None and block.get("page") is not None:
                page_qualified_id = f"p{int(block.get('page', 0) or 0)}:{block.get('block_id')}"
            if block.get("block_id") == abstract_heading_block_id or page_qualified_id == abstract_heading_block_id:
                continue
            text = block.get("text", "")
            if text:
                for abstract_line in normalize_ocr_math_text(text).splitlines():
                    if abstract_line.strip():
                        lines.append(f"> {abstract_line}")
                lines.append("")

    # Build per-page figure/table lookups
    figures_by_page: dict[int, list[dict]] = {}
    for i, fig in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = fig.get("figure_id") or f"figure_{i + 1:03d}"
        page = fig.get("page", 0) or 1
        figures_by_page.setdefault(page, []).append(
            {
                "figure_id": fig_id,
                "caption": str(fig.get("text") or ""),
            }
        )

    tables_by_page: dict[int, list[str]] = {}
    for i, tbl in enumerate(table_inventory.get("tables", [])):
        if tbl.get("has_asset"):
            tbl_id = tbl.get("table_id") or f"table_{i + 1:03d}"
            page = tbl.get("page", 0) or 1
            tables_by_page.setdefault(page, []).append(tbl_id)

    unresolved_clusters_by_page: dict[int, list[str]] = {}
    for idx, cluster in enumerate(figure_inventory.get("unresolved_clusters", [])):
        cluster_id = cluster.get("cluster_id") or f"unresolved_cluster_{idx + 1:03d}"
        page = cluster.get("page", 0) or 1
        unresolved_clusters_by_page.setdefault(page, []).append(cluster_id)

    emitted_pages: set[int] = set()
    last_structured_insert_page: int | None = None
    last_structured_insert_bbox: list[float] | None = None
    pre_reference_reader_figures_emitted = False

    # Compute heading levels from span metadata font sizes when available
    _HEADING_ROLES = {"section_heading", "subsection_heading", "sub_subsection_heading"}
    heading_font_sizes: dict[int, float] = {}
    for i, block in enumerate(structured_blocks):
        if block.get("role") not in _HEADING_ROLES:
            continue
        span = block.get("span_metadata") or {}
        if isinstance(span, list):
            for s in span:
                sz = s.get("size")
                if sz:
                    heading_font_sizes[id(block)] = float(sz)
                    break
        elif isinstance(span, dict):
            sz = span.get("size")
            if sz:
                heading_font_sizes[id(block)] = float(sz)
    block_heading_prefix: dict[int, str] = {}
    if heading_font_sizes:
        size_groups: dict[float, list[int]] = {}
        for bid, sz in heading_font_sizes.items():
            bucket = round(sz * 2) / 2
            size_groups.setdefault(bucket, []).append(bid)
        sorted_sizes = sorted(size_groups.keys(), reverse=True)
        for level_idx, bucket in enumerate(sorted_sizes):
            prefix = "##" if level_idx == 0 else "###"
            for bid in size_groups[bucket]:
                block_heading_prefix[bid] = prefix

    # --- body with anchored figures/tables ---
    # Find the min and max page across ALL blocks (including suppressed)
    all_pages = {b.get("page", 0) for b in structured_blocks if b.get("page") is not None}
    max_page = max(all_pages) if all_pages else 0
    current_page: int | None = None

    CONSUMED_FRONTMATTER_ROLES = frozenset(
        {
            "paper_title",
            "authors",
            "doi",
            "affiliation",
            "email",
            "correspondence",
        }
    )

    if document_structure is None:
        # Fallback compatibility path — shared with test fixtures and legacy
        # callers that pass blocks without pre-computed document structure.
        # normalize_document_structure with sparse synthetic blocks can
        # incorrectly demote backmatter headings (e.g. Funding → body_paragraph)
        # because the activation gates lack full-paper context.  Only run
        # structural analysis for style profiling; do NOT overwrite roles.
        from paperforge.worker.ocr_document import normalize_document_structure

        _, new_blocks = normalize_document_structure([dict(b) for b in structured_blocks])
        for i, block in enumerate(structured_blocks):
            old_role = block.get("role")
            new_role = new_blocks[i].get("role") if i < len(new_blocks) else old_role
            # Never demote tail/candidate roles — those are explicit
            # test-level decisions, not normalization targets.
            _PROTECTED = frozenset(
                {
                    "backmatter_heading",
                    "backmatter_boundary_heading",
                    "backmatter_body",
                    "reference_heading",
                    "reference_item",
                    "table_caption",
                    "table_html",
                    "figure_caption_candidate",
                    "backmatter_heading_candidate",
                    "backmatter_boundary_candidate",
                    "non_body_insert",
                    "structured_insert",
                    "subsection_heading",
                    "sub_subsection_heading",
                    "section_heading",
                    "authors",
                    "paper_title",
                    "abstract_heading",
                    "abstract_body",
                }
            )
            if old_role in _PROTECTED:
                continue
            if old_role == "body_paragraph" and new_role in {"structured_insert", "non_body_insert"}:
                continue
            if old_role != new_role:
                block["role"] = new_role
                block["role_confidence"] = new_blocks[i].get("role_confidence", block.get("role_confidence", 0.5))

    style_profiles = _build_heading_style_profiles(structured_blocks)

    if _can_apply_tail_segment_reorder(document_structure):
        col_indices = {seg.get("column_index", 0) for seg in document_structure.tail_reading_order}
        if len(col_indices) > 1:
            seg_priority: dict[int, int] = {}
            seg_position: dict[int, int] = {}
            for seg_idx, seg in enumerate(document_structure.tail_reading_order):
                for pos, bi in enumerate(seg.get("block_indices", [])):
                    seg_priority[bi] = seg_idx
                    seg_position[bi] = pos

            for i, block in enumerate(structured_blocks):
                block["_ordered_original_index"] = i

            has_ref_zone = bool(getattr(document_structure, "reference_zone", None))
            ordered_blocks = _order_tail_blocks(
                structured_blocks, style_profiles=style_profiles, has_verified_reference_zone=has_ref_zone
            )

            tail_spread_pages = set(range(document_structure.spread_start, document_structure.spread_end + 1))
            page_groups: dict[int, list[dict]] = {}
            page_order: list[int] = []
            for block in ordered_blocks:
                page = block.get("page")
                if page is None:
                    page = -1
                if page not in page_groups:
                    page_groups[page] = []
                    page_order.append(page)
                page_groups[page].append(block)

            reordered: list[dict] = []
            for page in page_order:
                page_blocks = page_groups[page]
                if page not in tail_spread_pages:
                    reordered.extend(page_blocks)
                    continue

                seg_blocks: list[tuple[int, int, int, dict]] = []
                non_segment_blocks: list[tuple[int, dict]] = []
                for pos, block in enumerate(page_blocks):
                    orig = block.get("_ordered_original_index", -1)
                    if orig in seg_priority:
                        seg_blocks.append((seg_priority[orig], seg_position[orig], orig, block))
                    else:
                        non_segment_blocks.append((pos, block))

                seg_blocks.sort(key=lambda x: (x[0], x[1]))
                reordered.extend([b for _, b in non_segment_blocks] + [t[3] for t in seg_blocks])

            ordered_blocks = reordered
        else:
            has_ref_zone = bool(getattr(document_structure, "reference_zone", None))
            ordered_blocks = _order_tail_blocks(
                structured_blocks, style_profiles=style_profiles, has_verified_reference_zone=has_ref_zone
            )
    else:
        has_ref_zone = bool(getattr(document_structure, "reference_zone", None))
        ordered_blocks = _order_tail_blocks(
            structured_blocks, style_profiles=style_profiles, has_verified_reference_zone=has_ref_zone
        )

    for block in ordered_blocks:
        role = block.get("role", "")
        block_page = block.get("page")

        if block_page is not None and block_page != current_page:
            if current_page is not None:
                _emit_page_objects(
                    lines,
                    current_page,
                    figures_by_page=figures_by_page,
                    unresolved_clusters_by_page=unresolved_clusters_by_page,
                    tables_by_page=tables_by_page,
                    reader_figures_by_page=reader_figures_by_page,
                    rendered_reader_figure_ids=rendered_reader_figure_ids,
                    emitted_figure_captions=emitted_figure_captions,
                )
                emitted_pages.add(current_page)
            first_new_page = (current_page or 0) + 1
            for p in range(first_new_page, block_page):
                lines.append(f"<!-- page {p} -->")
                lines.append("")
                _emit_page_objects(
                    lines,
                    p,
                    figures_by_page=figures_by_page,
                    unresolved_clusters_by_page=unresolved_clusters_by_page,
                    tables_by_page=tables_by_page,
                    reader_figures_by_page=reader_figures_by_page,
                    rendered_reader_figure_ids=rendered_reader_figure_ids,
                    emitted_figure_captions=emitted_figure_captions,
                )
                emitted_pages.add(p)
            current_page = block_page
            lines.append(f"<!-- page {block_page} -->")
            lines.append("")
            emitted_pages.add(block_page)
            last_structured_insert_page = None
            last_structured_insert_bbox = None

        if role == "structured_insert":
            pass  # render as callout below
        elif not block.get("render_default", True):
            continue
        if role in CONSUMED_FRONTMATTER_ROLES and block.get("page") == 1:
            continue
        _SKIPPED_BODY_ROLES = {
            "abstract_heading",
            "abstract_body",
            "frontmatter_noise",
            "frontmatter_support",
            "table_html",
            "figure_caption",
            "figure_inner_text",
        }
        if role in _SKIPPED_BODY_ROLES:
            continue

        block_id = block.get("block_id")
        block_key = _page_block_key(block_page, block_id)
        if block_id is not None and (
            block_key in consumed_caption_keys or block_id in consumed_caption_ids_unkeyed
        ):
            continue
        if block_key in abstract_member_keys or block_id in abstract_member_ids_unkeyed:
            continue

        raw_text = block.get("text", "")
        text = normalize_ocr_math_text(raw_text)
        text = re.sub(r"<table[^>]*>.*?</table>", "", text, flags=re.DOTALL | re.IGNORECASE)
        if text.strip().lower().startswith("<table"):
            continue

        if role == "structured_insert":
            pass  # render as callout below
        elif not block.get("render_default", True):
            continue
        if role == "backmatter_boundary_heading" or role == "backmatter_heading":
            last_structured_insert_page = None
            last_structured_insert_bbox = None
            if text and not _should_suppress_frontmatter_heading(text):
                lines.append(f"**{text}**")
                lines.append("")
        elif role == "reference_heading":
            last_structured_insert_page = None
            last_structured_insert_bbox = None
            if not pre_reference_reader_figures_emitted and block_page is not None:
                _emit_reader_figures_before_references(
                    lines,
                    start_page=block_page,
                    reader_figures_by_page=reader_figures_by_page,
                    rendered_reader_figure_ids=rendered_reader_figure_ids,
                )
                pre_reference_reader_figures_emitted = True
            lines.append(f"## {text}")
            lines.append("")
        elif role in ("subsection_heading", "sub_subsection_heading", "section_heading"):
            last_structured_insert_page = None
            last_structured_insert_bbox = None
            text = _display_heading_text(block, text)
            _heading_lower = text.strip().lower()
            if any(kw in _heading_lower for kw in _BACKMATTER_HEADING_KEYWORDS):
                if text and not _should_suppress_frontmatter_heading(text):
                    lines.append(f"**{text}**")
                    lines.append("")
                continue
            if role == "section_heading":
                if _should_suppress_frontmatter_heading(text):
                    continue
                if _is_bogus_heading(text):
                    if text:
                        lines.append(text)
                        lines.append("")
                    continue
                lines.append(f"## {text}")
            else:
                prefix = block_heading_prefix.get(id(block))
                if prefix is None:
                    depth = _heading_number_depth_text(text)
                    prefix = "##" if depth <= 1 else "###"
                lines.append(f"{prefix} {text}")
            lines.append("")
        elif role == "structured_insert":
            container_text = block.get("_container_text")
            if container_text:
                source_text = " ".join(container_text.replace("\n", " ").split())
            else:
                source_text = raw_text
            callout_lines = (
                _table_html_to_lines(source_text)
                if source_text.strip().lower().startswith("<table")
                else source_text.strip().split("\n")
            )
            callout_lines = [line for line in callout_lines if line.strip()]
            if callout_lines:
                bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
                merge_with_previous = False
                if (
                    last_structured_insert_page == block_page
                    and last_structured_insert_bbox is not None
                    and len(bbox) >= 4
                ):
                    prev = last_structured_insert_bbox
                    overlaps_x = bbox[0] <= prev[2] + 40 and bbox[2] >= prev[0] - 40
                    gap_y = bbox[1] - prev[3]
                    merge_with_previous = overlaps_x and gap_y <= 80
                if merge_with_previous and lines and lines[-1] == "":
                    lines.pop()
                if (
                    merge_with_previous
                    and callout_lines
                    and callout_lines[0].lstrip().startswith("•")
                    and lines
                    and lines[-1].startswith("> ")
                    and "•" in lines[-1][2:]
                    and not lines[-1].startswith("> •")
                ):
                    lines.pop()
                if not merge_with_previous:
                    lines.append("> [!NOTE]")
                for cl in callout_lines:
                    lines.append(f"> {cl}")
                if not merge_with_previous:
                    lines.append("")
                last_structured_insert_page = block_page
                last_structured_insert_bbox = bbox if len(bbox) >= 4 else None
        elif role == "table_caption":
            block_zone = str(block.get("zone") or "")
            block_style_family = str(block.get("style_family") or "")
            if block_zone == "display_zone" or block_style_family == "table_caption_like":
                if text:
                    lines.append(f"> **{text}**")
                    lines.append("")
            else:
                if text:
                    lines.append(f"### {text}")
                    lines.append("")
            tbl_ids_for_page = tables_by_page.get(block_page, [])
            if tbl_ids_for_page:
                tbl_id = tbl_ids_for_page.pop(0)
                lines.append(f"![[render/tables/{tbl_id}.md]]")
                lines.append("")
        elif role == "figure_caption":
            if text:
                lines.append(text)
                lines.append("")
        elif role in ("backmatter_body", "tail_candidate_body", "body_paragraph"):
            if last_structured_insert_page is not None:
                lines.append("")
            last_structured_insert_page = None
            last_structured_insert_bbox = None
            if text:
                lines.append(text)
                lines.append("")
        else:
            if last_structured_insert_page is not None:
                lines.append("")
            last_structured_insert_page = None
            last_structured_insert_bbox = None
            if text:
                lines.append(text)
                lines.append("")

    # Emit objects for the last rendered page
    if current_page is not None:
        _emit_page_objects(
            lines,
            current_page,
            figures_by_page=figures_by_page,
            unresolved_clusters_by_page=unresolved_clusters_by_page,
            tables_by_page=tables_by_page,
            reader_figures_by_page=reader_figures_by_page,
            rendered_reader_figure_ids=rendered_reader_figure_ids,
            emitted_figure_captions=emitted_figure_captions,
        )
        emitted_pages.add(current_page)

    # Emit any remaining objects and markers for pages not covered by body transitions
    # (includes pages before, after, and between renderable body pages)
    effective_count = page_count if page_count is not None else max_page
    if current_page is not None:
        for p in range(1, effective_count + 1):
            if p in emitted_pages:
                continue
            if p > (current_page or 0):
                lines.append(f"<!-- page {p} -->")
                lines.append("")
            _emit_page_objects(
                lines,
                p,
                figures_by_page=figures_by_page,
                unresolved_clusters_by_page=unresolved_clusters_by_page,
                tables_by_page=tables_by_page,
                reader_figures_by_page=reader_figures_by_page,
                rendered_reader_figure_ids=rendered_reader_figure_ids,
                emitted_figure_captions=emitted_figure_captions,
            )

    return "\n".join(lines).strip() + "\n"


def write_render_outputs(render_root: Path, compat_fulltext: Path, markdown: str) -> None:
    render_root.mkdir(parents=True, exist_ok=True)
    (render_root / "fulltext.md").write_text(markdown, encoding="utf-8")
    compat_fulltext.write_text(markdown, encoding="utf-8")
