from __future__ import annotations

import re
from collections import namedtuple
from pathlib import Path

from paperforge.worker.ocr_roles import FRONTMATTER_NOISE

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


def _normalize_latex(text: str) -> str:
    text = re.sub(r"\$\s+", "$", text)
    text = re.sub(r"\s+\$", "$", text)
    text = re.sub(r"\$\^\{\s+", "$^{", text)
    text = re.sub(r"\s+\}\$", "}$", text)
    return text


def _is_bogus_heading(text: str) -> bool:
    t = text.strip()
    if len(t) > 100:
        return True
    if t.count(". ") > 1:
        return True
    return any(v in t.lower().split() for v in ["is", "are", "was", "were", "have", "has", "been"]) and len(t) > 50


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


def _has_tail_role(block: dict) -> bool:
    return block.get("role") in _TAIL_ROLES


def _get_column(block: dict, page_width: float = 1200) -> int:
    bbox = block.get("bbox") or block.get("block_bbox")
    if bbox and len(bbox) >= 4:
        x_center = (bbox[0] + bbox[2]) / 2
        return 0 if x_center < page_width / 2 else 1
    return 0


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
        col_penalty = 0.0 if h_col == body_col else 10000.0
        candidates.append((i, dist + col_penalty))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


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


def _extract_style_profile(block: dict) -> dict | None:
    span_meta = block.get("span_metadata")
    if not span_meta:
        return None

    # List of per-character spans (future format from PyMuPDF)
    if isinstance(span_meta, list) and len(span_meta) > 0:
        sizes = []
        fonts = set()
        flags_list = []
        colors = []
        for s in span_meta:
            if not isinstance(s, dict):
                continue
            size = s.get("size") or 0
            if size:
                sizes.append(size)
            font = s.get("font", "")
            if font:
                fonts.add(font)
            flags_list.append(s.get("flags", 0) or 0)
            colors.append(s.get("color", 0) or 0)

        if not sizes:
            return None

        return {
            "mean_size": sum(sizes) / len(sizes),
            "max_size": max(sizes),
            "font_families": fonts,
            "is_bold": any(f & 16 for f in flags_list),
            "is_italic": any(f & 4 for f in flags_list),
            "is_colored": any(c != 0 for c in colors),
        }

    # Flat dict format (backward compat with test data)
    if isinstance(span_meta, dict):
        size = span_meta.get("size", 0) or 0
        flags = span_meta.get("flags", "")
        if isinstance(flags, str):
            is_bold = "bold" in flags.lower()
            is_italic = "italic" in flags.lower()
        else:
            is_bold = bool(flags & 16) if flags else False
            is_italic = bool(flags & 4) if flags else False

        if not size and not is_bold:
            return None

        return {
            "mean_size": float(size),
            "max_size": float(size),
            "font_families": set(),
            "is_bold": is_bold,
            "is_italic": is_italic,
            "is_colored": False,
        }

    return None


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


def _disambiguate_heading_role(block: dict, style_profiles: dict) -> str | None:
    profile = _extract_style_profile(block)
    if profile is None:
        return None

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

    # Phase 5 — emit: non-tail pass, then boundary heading first
    # (backmatter container), then sub-sections, then references
    result: list[dict] = []
    result.extend(non_tail_pass)
    result.extend(carried_bodies)
    boundary_secs = [s for s in backmatter_sections if s["heading"].get("role") == "backmatter_boundary_heading"]
    sub_secs = [s for s in backmatter_sections if s["heading"].get("role") != "backmatter_boundary_heading"]
    for sec in boundary_secs + sub_secs:
        h = sec["heading"]
        if h.get("_backmatter_regime") == "container" and h.get("role") == "backmatter_heading":
            h["_container_child"] = True
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
        elif role == "body_paragraph":
            non_tail_pass.append(block)
        elif role == "reference_item":
            if ref_section is not None:
                if ref_section is carried_ref:
                    orphan_ref_items.append(block)
                else:
                    ref_section["bodies"].append(block)
        else:
            non_tail_pass.append(block)

    result: list[dict] = []
    result.extend(non_tail_pass)
    boundary_secs = [s for s in backmatter_sections if s["heading"].get("role") == "backmatter_boundary_heading"]
    sub_secs = [s for s in backmatter_sections if s["heading"].get("role") != "backmatter_boundary_heading"]
    for sec in boundary_secs + sub_secs:
        h = sec["heading"]
        if h.get("_backmatter_regime") == "container" and h.get("role") == "backmatter_heading":
            h["_container_child"] = True
        result.append(h)
        result.extend(sec["bodies"])
    if ref_section is not None and ref_section is not carried_ref:
        result.append(ref_section["heading"])
        result.extend(ref_section["bodies"])
    result.extend(orphan_bodies)
    result.extend(orphan_ref_items)

    return result, ref_section


def _promote_tail_body_candidates(
    blocks: list[dict],
    tail_spread: TailBoundary | None,
    header_band: float | None = None,
    footer_band: float | None = None,
) -> list[dict]:
    """Promote plausible tail bodies from plain body_paragraph blocks.

    Base role assignment should stay conservative.  This pass upgrades only
    those body paragraphs that are geometrically compatible with tail section
    ownership inside the reconciled tail spread.
    """
    if tail_spread is None or tail_spread.spread_start is None or tail_spread.spread_end is None:
        return blocks

    spread_start, spread_end = tail_spread.spread_start, tail_spread.spread_end
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


def _find_best_anchor(
    body: dict,
    anchors: list[dict],
    ref_heading: dict | None = None,
    page_width: float = 1200,
) -> int | None:
    """Find the best backmatter heading anchor for a tail candidate body.

    Prefers same column, then nearest heading above in any column.
    Handles cross-page continuations: an anchor on an earlier page is
    always treated as above the body (regardless of raw Y coordinate).
    Excludes ref_heading.  Returns the anchor index or None.
    """
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
            continue  # anchor on later page → cannot own body

        a_bottom = a_bbox[3]
        if anchor_page == body_page and a_bottom > body_y:
            continue  # anchor below body on same page

        # Cross-page anchors (earlier page) are always valid —
        # raw Y comparison across pages is meaningless.
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


def _assign_tail_spread_ownership(
    blocks: list[dict],
    tail_spread: TailBoundary | None = None,
) -> list[dict]:
    """Assign tail_candidate_body blocks to backmatter anchors across pages.

    When a tail_spread boundary is provided, only tail_candidate_body blocks
    within the spread are eligible for anchor matching.  Blocks outside the
    spread revert to body_paragraph.  Inside the spread, tail_candidate_body
    is replaced with backmatter_body when the block sits below a valid
    backmatter heading (same-column preferred).  Marks spread-assigned bodies
    with _spread_anchor so the page-local reorder pass does not reassign them.
    Unanchored candidates inside the spread stay as tail_candidate_body.
    """
    tail_heading_roles = {"backmatter_heading", "backmatter_boundary_heading"}
    anchors = [b for b in blocks if b.get("role") in tail_heading_roles]
    ref_heading = next((b for b in blocks if b.get("role") == "reference_heading"), None)

    if tail_spread is not None and tail_spread.spread_start is not None and tail_spread.spread_end is not None:
        spread_start, spread_end = tail_spread.spread_start, tail_spread.spread_end
    else:
        spread_start, spread_end = 0, 0

    if not anchors:
        return [{**b, "role": "body_paragraph"} if b.get("role") == "tail_candidate_body" else b for b in blocks]

    result = list(blocks)
    for i, block in enumerate(result):
        if block.get("role") != "tail_candidate_body":
            continue

        block_page = block.get("page", 0) or 0

        # Outside the reconciled tail spread → revert to body_paragraph
        if tail_spread is not None and (block_page < spread_start or block_page > spread_end):
            result[i] = dict(block)
            result[i]["role"] = "body_paragraph"
            continue

        # Inside tail spread (or no spread set): try geometric anchor matching
        pw = block.get("page_width", 0) or 1200
        idx = _find_best_anchor(block, anchors, ref_heading, pw)
        result[i] = dict(block)
        if idx is not None:
            anchor_page = anchors[idx].get("page", 0)
            result[i]["role"] = "backmatter_body"
            result[i]["_spread_anchor"] = anchor_page
        else:
            # If no anchor match inside the spread, revert to plain body.
            result[i]["role"] = "body_paragraph"
    return result


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


def _order_tail_blocks(blocks: list[dict], style_profiles: dict | None = None) -> list[dict]:
    """Fix block reading order on tail pages with mixed-column layout.

    Two-column tail pages can have blocks in non-reading order (e.g.
    left-column References at y=705 placed between right-column Gen AI
    heading at y=154 and Pub note heading at y=297).  This sorts all
    blocks on such pages by (column, y-position), then groups them into
    backmatter sections and a references zone using geometric ownership.

    Before per-page sorting, runs a multi-page tail-spread ownership pass
    that resolves tail_candidate_body blocks against backmatter anchors
    across page boundaries.  Non-tail pages are untouched.
    """
    if not blocks:
        return blocks

    # Step 0: Reconcile tail spread boundary
    tail_spread = _reconcile_tail_spread(blocks)

    # Step 0.25: Classify backmatter form and label tail-spread blocks
    if tail_spread is not None:
        backmatter_form = _classify_backmatter_form(tail_spread, blocks)
        _label_backmatter_regime(tail_spread, backmatter_form, blocks)

    # Step 0.5: only inside the reconciled tail spread, promote plausible
    # body paragraphs into tail candidates using geometry rather than
    # page-level text heuristics.
    header_band, footer_band = _estimate_noise_bands(blocks)
    blocks = _promote_tail_body_candidates(blocks, tail_spread, header_band=header_band, footer_band=footer_band)

    # Step 1: cross-page tail spread ownership (now boundary-aware)
    blocks = _assign_tail_spread_ownership(blocks, tail_spread)

    # Find pages that contain tail blocks and their page widths
    tail_pages: set[int] = set()
    page_widths: dict[int, int] = {}
    for block in blocks:
        if _has_tail_role(block):
            page = block.get("page")
            if page is not None:
                tail_pages.add(page)
        pw = block.get("page_width") or 0
        p = block.get("page")
        if p is not None and pw:
            page_widths.setdefault(p, pw)

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

    return result


def render_fulltext_markdown(
    *,
    structured_blocks: list[dict],
    resolved_metadata: dict,
    figure_inventory: dict,
    table_inventory: dict,
    page_count: int | None = None,
) -> str:
    lines: list[str] = []

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
    abstract_blocks = [
        b
        for b in structured_blocks
        if b.get("role") in ("abstract_heading", "abstract_body") and b.get("render_default", True)
    ]
    if abstract_blocks:
        lines.append("## Abstract")
        lines.append("")
        for block in abstract_blocks:
            if block.get("role") == "abstract_body":
                text = block.get("text", "")
                if text:
                    lines.append(_normalize_latex(text))
                    lines.append("")

    # Build per-page figure/table lookups
    figures_by_page: dict[int, list[str]] = {}
    for i, fig in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = fig.get("figure_id") or f"figure_{i + 1:03d}"
        page = fig.get("page", 0) or 1
        figures_by_page.setdefault(page, []).append(fig_id)

    tables_by_page: dict[int, list[str]] = {}
    for i, tbl in enumerate(table_inventory.get("tables", [])):
        if tbl.get("has_asset"):
            tbl_id = tbl.get("table_id") or f"table_{i + 1:03d}"
            page = tbl.get("page", 0) or 1
            tables_by_page.setdefault(page, []).append(tbl_id)

    emitted_pages: set[int] = set()

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

    style_profiles = _build_heading_style_profiles(structured_blocks)
    ordered_blocks = _order_tail_blocks(structured_blocks, style_profiles=style_profiles)

    for block in ordered_blocks:
        if not block.get("render_default", True):
            continue
        role = block.get("role", "")
        if role in CONSUMED_FRONTMATTER_ROLES and block.get("page") == 1:
            continue
        _SKIPPED_BODY_ROLES = {
            "abstract_heading",
            "abstract_body",
            "figure_caption",
            "table_caption",
            "frontmatter_noise",
            "table_html",
        }
        if role in _SKIPPED_BODY_ROLES:
            continue

        text = _normalize_latex(block.get("text", ""))
        text = re.sub(r"<table[^>]*>.*?</table>", "", text, flags=re.DOTALL | re.IGNORECASE)
        if text.strip().lower().startswith("<table"):
            continue
        block_page = block.get("page")

        if block_page is not None and block_page != current_page:
            # Emit objects for the page we just finished rendering
            if current_page is not None:
                for fig_id in figures_by_page.get(current_page, []):
                    lines.append(f"![[render/figures/{fig_id}.md]]")
                    lines.append("")
                for tbl_id in tables_by_page.get(current_page, []):
                    lines.append(f"![[render/tables/{tbl_id}.md]]")
                    lines.append("")
                emitted_pages.add(current_page)
            # Fill in page markers for skipped pages (no renderable blocks)
            first_new_page = (current_page or 0) + 1
            for p in range(first_new_page, block_page):
                lines.append(f"<!-- page {p} -->")
                lines.append("")
                for fig_id in figures_by_page.get(p, []):
                    lines.append(f"![[render/figures/{fig_id}.md]]")
                    lines.append("")
                for tbl_id in tables_by_page.get(p, []):
                    lines.append(f"![[render/tables/{tbl_id}.md]]")
                    lines.append("")
                emitted_pages.add(p)
            current_page = block_page
            lines.append(f"<!-- page {block_page} -->")
            lines.append("")
            emitted_pages.add(block_page)

        if role == "backmatter_boundary_heading" or role == "backmatter_heading" or role == "reference_heading":
            if block.get("_container_child"):
                lines.append(f"### {text}")
            else:
                lines.append(f"## {text}")
            lines.append("")
        elif role == "section_heading":
            if text.strip().lower() in FRONTMATTER_NOISE:
                continue
            if _is_bogus_heading(text):
                if text:
                    lines.append(text)
                    lines.append("")
            else:
                lines.append(f"## {text}")
                lines.append("")
        elif role == "subsection_heading" or role == "sub_subsection_heading":
            lines.append(f"### {text}")
            lines.append("")
        elif role in ("backmatter_body", "tail_candidate_body", "body_paragraph"):
            if text:
                lines.append(text)
                lines.append("")
        else:
            if text:
                lines.append(text)
                lines.append("")

    # Emit objects for the last rendered page
    if current_page is not None:
        for fig_id in figures_by_page.get(current_page, []):
            lines.append(f"![[render/figures/{fig_id}.md]]")
            lines.append("")
        for tbl_id in tables_by_page.get(current_page, []):
            lines.append(f"![[render/tables/{tbl_id}.md]]")
            lines.append("")
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
            for fig_id in figures_by_page.get(p, []):
                lines.append(f"![[render/figures/{fig_id}.md]]")
                lines.append("")
            for tbl_id in tables_by_page.get(p, []):
                lines.append(f"![[render/tables/{tbl_id}.md]]")
                lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_render_outputs(render_root: Path, compat_fulltext: Path, markdown: str) -> None:
    render_root.mkdir(parents=True, exist_ok=True)
    (render_root / "fulltext.md").write_text(markdown, encoding="utf-8")
    compat_fulltext.write_text(markdown, encoding="utf-8")
