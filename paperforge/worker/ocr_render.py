from __future__ import annotations

import re
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


def _is_bogus_heading(text: str) -> bool:
    t = text.strip()
    if len(t) > 100:
        return True
    if t.count(". ") > 1:
        return True
    return any(v in t.lower().split() for v in ["is", "are", "was", "were", "have", "has", "been"]) and len(t) > 50


def _has_tail_role(block: dict) -> bool:
    return block.get("role") in _TAIL_ROLES


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


def _order_tail_blocks(blocks: list[dict], style_profiles: dict | None = None) -> list[dict]:
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
    document_structure: DocumentStructure | None = None,
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
                    lines.append(normalize_ocr_math_text(text))
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

    unresolved_clusters_by_page: dict[int, list[str]] = {}
    for cluster in figure_inventory.get("unresolved_clusters", []):
        cluster_id = cluster.get("cluster_id", "")
        page = cluster.get("page", 0) or 1
        unresolved_clusters_by_page.setdefault(page, []).append(cluster_id)

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

    if document_structure is None:
        from paperforge.worker.ocr_document import normalize_document_structure

        document_structure, structured_blocks = normalize_document_structure(structured_blocks)

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

        text = normalize_ocr_math_text(block.get("text", ""))
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
                for cluster_id in unresolved_clusters_by_page.get(current_page, []):
                    lines.append(f"![[render/figures/{cluster_id}.md]]")
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
                for cluster_id in unresolved_clusters_by_page.get(p, []):
                    lines.append(f"![[render/figures/{cluster_id}.md]]")
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
        for cluster_id in unresolved_clusters_by_page.get(current_page, []):
            lines.append(f"![[render/figures/{cluster_id}.md]]")
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
            for cluster_id in unresolved_clusters_by_page.get(p, []):
                lines.append(f"![[render/figures/{cluster_id}.md]]")
                lines.append("")
            for tbl_id in tables_by_page.get(p, []):
                lines.append(f"![[render/tables/{tbl_id}.md]]")
                lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_render_outputs(render_root: Path, compat_fulltext: Path, markdown: str) -> None:
    render_root.mkdir(parents=True, exist_ok=True)
    (render_root / "fulltext.md").write_text(markdown, encoding="utf-8")
    compat_fulltext.write_text(markdown, encoding="utf-8")
