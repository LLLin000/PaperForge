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
from paperforge.worker.ocr_banding import LayoutBandEstimate, decide_usable_content
from paperforge.worker.ocr_math import normalize_ocr_math_text
from paperforge.worker.ocr_pdf_spans import _BACKFILL_OVERLAP_REJECT_THRESHOLD, _backfill_coverage_in_existing
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


def _block_font_size(block: dict) -> float | None:
    sig = block.get("span_signature") or {}
    fs = sig.get("font_size")
    if fs is not None:
        return float(fs)
    meta = block.get("span_metadata")
    if isinstance(meta, dict) and meta.get("size") is not None:
        return float(meta["size"])
    if isinstance(meta, list):
        sizes = [
            float(s["size"]) for s in meta
            if isinstance(s, dict) and s.get("size") is not None
        ]
        if sizes:
            return sorted(sizes)[len(sizes) // 2]
    return None


def _is_near_body_flow(
    fn_bbox: list[float],
    body_blocks: list[dict],
    page_height: float,
) -> bool:
    fn_x1, fn_y1, fn_x2, fn_y2 = fn_bbox[0], fn_bbox[1], fn_bbox[2], fn_bbox[3]
    fn_width = max(1.0, fn_x2 - fn_x1)
    if fn_y1 > page_height * 0.82:
        return False
    for body in body_blocks:
        bb = body.get("bbox") or body.get("block_bbox") or []
        if len(bb) < 4:
            continue
        bx1, by1, bx2, by2 = bb[0], bb[1], bb[2], bb[3]
        h_overlap = max(0.0, min(fn_x2, bx2) - max(fn_x1, bx1))
        x_aligned = h_overlap / fn_width >= 0.5
        if not x_aligned:
            continue
        overlaps_y = fn_y1 < by2 and fn_y2 > by1
        gap = fn_y1 - by2
        near_below = 0 <= gap <= page_height * 0.08
        if overlaps_y or near_below:
            return True
    return False


_BOILERPLATE_MARKERS = frozenset({
    "all rights reserved", "downloaded from",
    "published by", "received:", "accepted:",
})

_POSITIVE_CALLOUT_MARKERS = frozenset({
    "correspondence",
    "corresponding author",
    "e-mail",
    "email",
    "department",
    "university",
    "institute",
    "affiliation",
    "address",
    "these authors contributed",
    "contributed equally",
})


def _convert_footnotes_to_callouts(blocks: list[dict]) -> list[dict]:
    body_blocks = [b for b in blocks if b.get("role") == "body_paragraph"]
    body_fonts_by_page: dict[int, list[float]] = {}
    for body in body_blocks:
        p = int(body.get("page", 0) or 0)
        fs = _block_font_size(body)
        if fs is not None:
            body_fonts_by_page.setdefault(p, []).append(fs)
    all_body_fonts = [fs for sizes in body_fonts_by_page.values() for fs in sizes]
    if not all_body_fonts:
        return blocks

    result = list(blocks)
    for i, b in enumerate(result):
        if b.get("role") != "footnote":
            continue
        bbox = b.get("bbox") or b.get("block_bbox") or []
        if len(bbox) < 4:
            continue

        raw_text = str(b.get("text", "") or "")
        text_lower = raw_text.lower()

        if any(m in text_lower for m in _BOILERPLATE_MARKERS):
            continue

        has_positive = any(m in text_lower for m in _POSITIVE_CALLOUT_MARKERS)
        has_symbol = any(sym in raw_text for sym in ("\u2020", "*", "\u2021", "\u00a7"))
        if not (has_positive or has_symbol):
            continue

        fn_page = int(b.get("page", 0) or 0)
        page_body_fonts = body_fonts_by_page.get(fn_page) or all_body_fonts
        body_font_median = sorted(page_body_fonts)[len(page_body_fonts) // 2]
        fn_fs = _block_font_size(b)
        if fn_fs is None or fn_fs >= body_font_median:
            continue

        page_body_blocks = [bb for bb in body_blocks if int(bb.get("page", 0) or 0) == fn_page]
        page_height = max(
            (
                float(bb.get("page_height") or 0)
                for bb in blocks
                if int(bb.get("page", 0) or 0) == fn_page
            ),
            default=0.0,
        ) or 1500.0

        if not _is_near_body_flow(bbox, page_body_blocks, page_height):
            continue

        result[i] = dict(b)
        result[i]["role"] = "structured_insert"
        from paperforge.worker.ocr_decisions import record_decision
        record_decision(
            result[i],
            stage="footnote_to_callout",
            old_role="footnote",
            new_role="structured_insert",
            reason=f"footnote near body flow font={fn_fs:.1f} < body={body_font_median:.1f}",
        )

    return result


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
    # Numbered headings (e.g. "3. 3D printing Scaffolds...") can legitimately be long
    if re.match(r"^\d+(?:\.\d+)*\.?\s", t):
        return False
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


def _ref_number_sort_key(block: dict) -> tuple:
    text = str(block.get("text") or block.get("block_content") or "")
    # Two capture groups — alternation prevents false matches on plain year numbers
    # like "2024" that lack a period/bracket suffix.
    # ponytail: only handles N. / N) / [N] prefix formats.  Unnumbered refs fall
    # through to lexicographic sort — upgrade to column-major sort if needed.
    m = re.match(r"^\s*(?:(\d+)[\.\)]|\[(\d+)\])", text)
    if m:
        return (0, int(m.group(1) or m.group(2)))
    return (1, text)

_TAIL_BACKMATTER_CONTINUATION_PATTERN = re.compile(
    r"^(?:address correspondence|correspondence|e-?mail|email|"
    r"received|accepted|published|available online|"
    r"author contributions?|conflicts? of interest|funding|"
    r"acknowledg(?:e)?ments?)\b",
    re.IGNORECASE,
)


def _is_tail_backmatter_continuation(block: dict) -> bool:
    zone = str(block.get("zone") or "")
    if zone == "tail_nonref_hold_zone":
        return True
    text = str(block.get("text") or block.get("block_content") or "").strip()
    return bool(_TAIL_BACKMATTER_CONTINUATION_PATTERN.match(text))


def _block_column(block: dict, page_width: float) -> int | None:
    bbox = block.get("bbox") or block.get("block_bbox")
    if not bbox or len(bbox) < 4:
        return None
    x_center = (bbox[0] + bbox[2]) / 2
    return 0 if x_center < (page_width / 2.0) else 1


def _should_attach_reference_item_to_ref_section(
    block: dict,
    ref_heading: dict | None,
    *,
    page_width: float,
    ref_bottom: float,
) -> bool:
    bbox = block.get("bbox") or block.get("block_bbox")
    if not bbox or len(bbox) < 4:
        return True
    if ref_heading is None:
        return True

    heading_bbox = ref_heading.get("bbox") or ref_heading.get("block_bbox")
    if not heading_bbox or len(heading_bbox) < 4:
        return True

    block_col = _block_column(block, page_width)
    heading_col = _block_column(ref_heading, page_width)
    if block_col == heading_col:
        return bbox[1] >= ref_bottom
    return True
def _reorder_tail_run(
    tail_blocks: list[dict],
    carried_ref: dict | None = None,
    carried_backmatter: dict | None = None,
    *,
    header_band: float | None = None,
    footer_band: float | None = None,
    band_estimate: LayoutBandEstimate | None = None,
    page_width: float = 1200,
    skip_section_grouping: bool = False,
) -> tuple[list[dict], dict | None, dict | None]:
    """Group tail blocks using geometric ownership and reference zone.

    Non-tail pass blocks (body_paragraph, tail_candidate_body, etc.) are
    emitted first, preserving their natural page order.  Backmatter sections
    (heading + body) are emitted next in column-sorted order.  References
    zone (heading + all items below it) is emitted last.  Body blocks are
    attached to the nearest backmatter heading above them in the same column,
    falling back to absolute proximity with a cross-column penalty.

    When ``skip_section_grouping=True`` (pages without a reference heading),
    backmatter section grouping is bypassed entirely — blocks are emitted
    in column-sorted order with reference items grouped at the end.

    When blocks lack bbox data, falls back to FIFO matching for backward
    compatibility.
    """
    # Backward-compatible bridge: when no band_estimate is provided,
    # create one from the raw header_band/footer_band parameters.
    if band_estimate is None:
        band_estimate = LayoutBandEstimate(
            header_band=header_band,
            footer_band=footer_band,
            status="ACCEPT" if (header_band is not None or footer_band is not None) else "EMPTY",
            method="runtime_selected",
            accepted_candidates=[],
            excluded_candidates=[],
            support_pages=[],
            warnings=[],
        )

    if not tail_blocks:
        return tail_blocks, carried_ref, carried_backmatter

    # Short-circuit: no section grouping for pages without reference heading.
    # Column-sort is maintained; ref items are grouped at the end.
    if skip_section_grouping:
        ref_roles = frozenset({"reference_heading", "reference_item", "reference_body"})
        backmatter_roles = frozenset({
            "backmatter_body",
            "backmatter_heading",
            "backmatter_boundary_heading",
        })

        non_ref_all = [
            b for b in tail_blocks
            if b.get("role") not in ref_roles
            and b.get("role") not in backmatter_roles
            and b.get("role") != "footnote"
        ]

        refs = [b for b in tail_blocks if b.get("role") in ref_roles]
        refs.sort(key=_ref_number_sort_key)

        backmatter = [b for b in tail_blocks if b.get("role") in backmatter_roles]
        fnotes = [b for b in tail_blocks if b.get("role") == "footnote"]

        tail_backmatter = [b for b in non_ref_all if _is_tail_backmatter_continuation(b)]
        ordinary_non_ref = [b for b in non_ref_all if not _is_tail_backmatter_continuation(b)]

        return (ordinary_non_ref + refs + backmatter + tail_backmatter + fnotes,
                carried_ref, carried_backmatter)

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
    footnote_blocks: list[dict] = []
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
            ref_items.append(block)
        elif role == "backmatter_body":
            body_pool.append(block)
        elif role == "body_paragraph":
            if decide_usable_content(block, band_estimate, context="tail_render_body").usable:
                idx = _find_owning_heading(block, backmatter_sections, page_width) if backmatter_sections else None
                if idx is not None:
                    backmatter_sections[idx]["bodies"].append(block)
                elif _is_tail_backmatter_continuation(block):
                    body_pool.append(block)
                else:
                    non_tail_pass.append(block)
            else:
                non_tail_pass.append(block)
        elif role == "footnote":
            footnote_blocks.append(block)
        else:
            non_tail_pass.append(block)

    # Phase 2 — build references zone
    ref_heading = ref_section.get("heading") if ref_section and ref_section is not carried_ref else None
    ref_bottom: float = 0.0
    if ref_heading:
        rh_bbox = ref_heading.get("bbox") or ref_heading.get("block_bbox")
        if rh_bbox and len(rh_bbox) >= 4:
            ref_bottom = rh_bbox[3]

    # Phase 2.5 — create synthetic ref section when no reference heading
    # exists but reference items are present.  This prevents ref items
    # from scattering through body_pool → orphan_blocks on pages that
    # lack an explicit "References" heading block.
    _needs_synthetic_ref = not ref_heading and bool(ref_items)
    if _needs_synthetic_ref:
        ref_section = {"heading": None, "bodies": []}

    # Phase 3 — assign ref items to zone, backmatter bodies to body pool
    # Phase 3 — assign ref items to zone
    rejected_ref_items: list[dict] = []
    for block in ref_items:
        if ref_heading:
            if _should_attach_reference_item_to_ref_section(
                block,
                ref_heading,
                page_width=page_width,
                ref_bottom=ref_bottom,
            ):
                ref_section["bodies"].append(block)
            else:
                rejected_ref_items.append(block)
        elif _needs_synthetic_ref:
            ref_section["bodies"].append(block)
        else:
            rejected_ref_items.append(block)

    # Phase 4a — container regime body attachment (run before generic
    # body loop so container bodies are matched to their specific child
    # heading rather than falling through to ref-section absorption)
    body_pool = _attach_container_bodies(body_pool, backmatter_sections, page_width, ref_section)

    # Phase 4b — geometric body attachment for remaining bodies
    first_local_anchor_top: float | None = None
    tail_backmatter_blocks: list[dict] = []
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
            continue

        if _is_tail_backmatter_continuation(body):
            tail_backmatter_blocks.append(body)
            continue

        if carried_backmatter is not None:
            bbox = body.get("bbox") or body.get("block_bbox")
            if bbox and len(bbox) >= 4:
                body_top = bbox[1]
                if (first_local_anchor_top is None or body_top < first_local_anchor_top) and (
                    not ref_heading or body_top < ref_bottom
                ):
                    carried_bodies.append(body)
                    continue

        decision = decide_usable_content(body, band_estimate, context="tail_render_backmatter_bodypool")
        if not decision.usable:
            non_tail_pass.append(body)
            continue

        if ref_section is not None and not _needs_synthetic_ref:
            if ref_section is carried_ref:
                ref_section["bodies"].append(body)
                orphan_blocks.append(body)
            else:
                ref_section["bodies"].append(body)
        else:
            orphan_blocks.append(body)

    # Phase 5 — emit: non-tail pass (frontmatter), then backmatter
    # sections sorted by y-position (boundary-level and sub-headings
    # emit in reading order), then reference sections, then footnotes.  The
    # y-sort is applied only to backmatter_sections to avoid carrying
    # cross-page relationship artifacts from previous pages' carried blocks.
    result: list[dict] = []
    result.extend(non_tail_pass)
    result.extend(rejected_ref_items)
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
        if ref_section.get("heading"):
            result.append(ref_section["heading"])
        if ref_section.get("bodies"):
            ref_section["bodies"].sort(key=_ref_number_sort_key)
            result.extend(ref_section["bodies"])
    result.extend(tail_backmatter_blocks)
    result.extend(footnote_blocks)
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



def _force_reference_heading_before_same_page_refs(page_blocks: list[dict]) -> list[dict]:
    """Reorder page blocks so reference_item/reference_body always follow
    the first reference_heading on the same page. Non-ref blocks are unchanged."""
    headings = [b for b in page_blocks if b.get("role") == "reference_heading"]
    if not headings:
        return page_blocks

    ref_roles = {"reference_item", "reference_body"}
    refs = [b for b in page_blocks if b.get("role") in ref_roles]
    if not refs:
        return page_blocks

    first_heading = headings[0]
    heading_idx = page_blocks.index(first_heading)

    before = [b for b in page_blocks[:heading_idx] if b.get("role") not in ref_roles]
    after = [b for b in page_blocks[heading_idx + 1:] if b.get("role") not in ref_roles]

    return before + [first_heading] + sorted(refs, key=_ref_number_sort_key) + after
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

    from paperforge.worker.ocr_banding import estimate_layout_bands, choose_runtime_bands, LayoutBandEstimate

    legacy_header_band, legacy_footer_band = _estimate_noise_bands(blocks)
    robust_estimate = estimate_layout_bands(blocks)
    max_page_height = max((float(b.get("page_height") or 0) for b in blocks), default=0.0)

    header_band, footer_band, runtime_band_source = choose_runtime_bands(
        robust_estimate,
        legacy_header_band,
        legacy_footer_band,
        max_page_height=max_page_height,
    )

    runtime_band_estimate = LayoutBandEstimate(
        header_band=header_band,
        footer_band=footer_band,
        status="ACCEPT" if (header_band is not None or footer_band is not None) else "EMPTY",
        method=f"runtime_{runtime_band_source}",
        accepted_candidates=robust_estimate.accepted_candidates,
        excluded_candidates=robust_estimate.excluded_candidates,
        support_pages=robust_estimate.support_pages,
        warnings=robust_estimate.warnings,
    )

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
        result: list[dict] = []
        by_page: dict[int, list[dict]] = {}
        for block in blocks:
            p = block.get("page")
            if p is None:
                result.append(block)
            else:
                by_page.setdefault(p, []).append(block)
        for page in sorted(by_page):
            result.extend(_force_reference_heading_before_same_page_refs(by_page[page]))
        return result

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
            sorted_blocks = _force_reference_heading_before_same_page_refs(sorted_blocks)
            _page_has_ref_items = any(b.get("role") in {"reference_item", "reference_body"} for b in sorted_blocks)
            _page_has_ref_heading = any(b.get("role") == "reference_heading" for b in sorted_blocks)
            ordered, carried_ref, carried_backmatter = _reorder_tail_run(
                sorted_blocks,
                carried_ref,
                carried_backmatter,
                header_band=header_band,
                footer_band=footer_band,
                band_estimate=runtime_band_estimate,
                page_width=pw,
                skip_section_grouping=_page_has_ref_items and not _page_has_ref_heading,
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
        ref_headings = [b for b in result if b.get("role") == "reference_heading"]
        ref_items = [b for b in result if b.get("role") in {"reference_item", "reference_body"}]
        ref_items.sort(key=_ref_number_sort_key)
        return non_ref + ref_headings + ref_items
    return result


def _render_reader_figure_card(figure: dict) -> list[str]:
    """Render reader figure card. Returns empty when embed note covers it."""
    if _reader_figure_embed_target(figure) is not None:
        return []
    caption_text = figure.get("caption_text", "")
    fn = figure.get("figure_number")
    if not caption_text:
        return []
    lines = [f"> **Figure {fn}**", f"> {caption_text}"]
    return lines


def _reader_figure_embed_target(figure: dict) -> str | None:
    status = str(figure.get("reader_status") or "")
    if status not in {"EXACT_MATCH", "SEQUENCE_MATCH"}:
        return None
    figure_id = figure.get("figure_id", "")
    if figure_id:
        return figure_id
    figure_number = figure.get("figure_number")
    if figure_number is None:
        return None
    return f"figure_{int(figure_number):03d}"


def _reader_covered_figure_ids(reader_figures: list[dict]) -> set[str]:
    covered: set[str] = set()
    for figure in reader_figures:
        embed_target = _reader_figure_embed_target(figure)
        if embed_target:
            covered.add(embed_target)
    return covered


def _page_block_key(
    block_or_page: dict | int | None, block_id: int | str | None = None
) -> tuple[int | None, int | str] | None:
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


def _add_consumed_key(
    keys: set[tuple[int | None, str | int]],
    page: int | None,
    block_id: str | int,
) -> None:
    """Add a per-page consumed block key, keyed by (page, block_id)."""
    if block_id is None or block_id == "":
        return
    keys.add((page, block_id))
    keys.add((page, str(block_id)))


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
    # Build page-block_id index from structured blocks for fallback resolution.
    page_block_ids: dict[int | None, set[str | int]] = {}
    for block in structured_blocks:
        bid = block.get("block_id")
        if bid is None:
            continue
        page = block.get("page")
        page_block_ids.setdefault(page, set()).add(bid)
        page_block_ids.setdefault(page, set()).add(str(bid))

    consumed_table_block_keys: set[tuple[int | None, str | int]] = set()
    for table in table_inventory.get("tables", []):
        table_page = table.get("page")

        # Build explicit page mapping from table inventory fields.
        # These fields know each block's true page and disambiguate
        # cross-page collisions (same block_id on different pages).
        explicit_id_page: dict[str | int, int | None] = {}

        def _map_eid(bid, page):
            if bid is not None and bid != "":
                explicit_id_page[bid] = page
                explicit_id_page[str(bid)] = page

        _map_eid(table.get("caption_block_id"), table_page)

        for seg in table.get("segments", []):
            _map_eid(seg.get("asset_block_id"), seg.get("page") or table_page)

        for note_bid in table.get("note_block_ids", []):
            if note_bid is not None and note_bid != "":
                # Notes may be on a different page — resolve from structured blocks
                note_page = None
                for p, ids in page_block_ids.items():
                    if note_bid in ids or str(note_bid) in ids:
                        note_page = p
                        break
                _map_eid(note_bid, note_page or table_page)

        for br_bid in table.get("bridge_block_ids", []):
            _map_eid(br_bid, table_page)

        for bid in table.get("consumed_block_ids", []):
            if bid is None or bid == "":
                continue
            # Try explicit mapping first (handles cross-page assets and notes)
            page = explicit_id_page.get(bid) or explicit_id_page.get(str(bid))
            if page is not None:
                _add_consumed_key(consumed_table_block_keys, page, bid)
                continue

            # Not in explicit fields — fall back to structured block lookup
            str_bid = str(bid)
            table_ids = page_block_ids.get(table_page, set())
            if bid in table_ids or str_bid in table_ids:
                _add_consumed_key(consumed_table_block_keys, table_page, bid)
            else:
                found = False
                for p, ids in page_block_ids.items():
                    if bid in ids or str_bid in ids:
                        _add_consumed_key(consumed_table_block_keys, p, bid)
                        found = True
                        break
                if not found:
                    _add_consumed_key(consumed_table_block_keys, table_page, bid)
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

    # --- metadata block ---
    journal = resolved_metadata.get("journal", {}).get("value", "")
    year = resolved_metadata.get("year", {}).get("value", 0)
    doi = resolved_metadata.get("doi", {}).get("value", "")

    if authors_display or journal or year or doi:
        lines.append("> [!info]- Paper Metadata")
        if authors_display:
            lines.append(f"> **Authors:** {authors_display}")
        if journal:
            lines.append(f"> **Journal:** {journal}")
        if year:
            lines.append(f"> **Year:** {year}")
        if doi:
            lines.append(f"> **DOI:** {doi}")
        lines.append("")

    # --- abstract ---
    abstract_blocks: list[dict] = []
    if document_structure is not None and getattr(document_structure, "abstract_span", None):
        span = document_structure.abstract_span
        block_by_id = {}
        for block in structured_blocks:
            block_id = block.get("block_id")
            if block_id is not None:
                block_by_id[block_id] = block
                block_by_id[f"p{int(block.get('page', 0) or 0)}:{block_id}"] = block
        abstract_ids = [span.get("heading_block_id"), *span.get("body_block_ids", [])]
        abstract_ids = [bid for bid in abstract_ids if bid]
        if abstract_ids:
            abstract_blocks = [block_by_id[bid] for bid in abstract_ids if bid in block_by_id]
    if not abstract_blocks:
        _ABSTRACT_ROLES_FALLBACK = frozenset({"abstract_heading", "abstract_body"})
        abstract_blocks = [
            b for b in structured_blocks if b.get("role") in _ABSTRACT_ROLES_FALLBACK and b.get("render_default", True)
        ]
    abstract_member_keys = {_page_block_key(block) for block in abstract_blocks if _page_block_key(block) is not None}
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
            if abstract_heading_block_id is not None and (
                block.get("block_id") == abstract_heading_block_id or page_qualified_id == abstract_heading_block_id
            ):
                continue
            text = block.get("text", "")
            if text:
                # Skip highlight bullet continuations incorrectly labeled as abstract
                stripped = text.strip()
                if stripped.startswith(("\u2022", "- ")):
                    continue
                for abstract_line in normalize_ocr_math_text(text).splitlines():
                    if abstract_line.strip():
                        lines.append(abstract_line)
                lines.append("")

    # Build per-page figure/table lookups
    reader_covered_figure_ids = _reader_covered_figure_ids(reader_figures)

    figures_by_page: dict[int, list[dict]] = {}
    for i, fig in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = fig.get("figure_id") or f"figure_{i + 1:03d}"
        if fig_id in reader_covered_figure_ids:
            continue
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
    _emitted_body_text_by_page: dict[int, list[str]] = {}
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
    _heading_prefix_map: dict[tuple, str] = {}
    if heading_font_sizes:
        size_groups: dict[float, list[int]] = {}
        bid_to_block: dict[int, dict] = {}
        for bid, sz in heading_font_sizes.items():
            bucket = round(sz * 2) / 2
            size_groups.setdefault(bucket, []).append(bid)
        for blk in structured_blocks:
            bid_to_block[id(blk)] = blk

        def _bold_font_block(block: dict) -> bool:
            ff = str((block.get("span_signature") or {}).get("font_family_norm") or "")
            bd = block.get("span_signature", {}).get("bold")
            bd = bd if bd else ("-Bd" in ff or "-Bold" in ff)
            return bd

        _heading_prefix_map: dict[tuple, str] = {}
        sorted_sizes = sorted(size_groups.keys(), reverse=True)
        prefixes = ["##", "###", "####", "#####", "######"]
        prefix_idx = 0
        for bucket in sorted_sizes:
            bids = size_groups[bucket]
            bolds = [bid for bid in bids if _bold_font_block(bid_to_block.get(bid, {}))]
            regulars = [bid for bid in bids if bid not in bolds]
            for group in (bolds, regulars):
                if not group:
                    continue
                upper = set()
                lower = set()
                for bid in group:
                    blk = bid_to_block.get(bid)
                    t = str(blk.get("text") or "") if blk else ""
                    if t and sum(1 for c in t if c.isupper()) / max(len(t), 1) > 0.7:
                        upper.add(bid)
                    else:
                        lower.add(bid)
                for subgroup in (upper, lower):
                    if not subgroup:
                        continue
                    p = prefixes[min(prefix_idx, len(prefixes) - 1)]
                    for bid in subgroup:
                        blk = bid_to_block.get(bid)
                        if blk:
                            _heading_prefix_map[(int(blk.get("page", 0) or 0), blk.get("block_id"))] = p
                    prefix_idx += 1

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

    structured_blocks = _convert_footnotes_to_callouts(structured_blocks)

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
            bm_start = getattr(document_structure, "spread_start", None) if document_structure else None
            if role != "frontmatter_noise" or block_page is None or not bm_start or block_page < bm_start:
                continue
        if role in CONSUMED_FRONTMATTER_ROLES and int(block.get("page", 0) or 0) <= 2:
            continue

        # Ownership skip first — table note removal by contract, not by role
        block_id = block.get("block_id")
        if block_id is not None and (
            (block_page, block_id) in consumed_table_block_keys
            or (block_page, str(block_id)) in consumed_table_block_keys
        ):
            continue

        _SKIPPED_BODY_ROLES = {
            "abstract_heading",
            "abstract_body",
            "footnote",
            "frontmatter_noise",
            "frontmatter_support",
            "table_html",
            "table_caption_candidate",
            "figure_caption",
            "figure_inner_text",
        }
        if role in _SKIPPED_BODY_ROLES:
            bm_start = getattr(document_structure, "spread_start", None) if document_structure else None
            if role == "frontmatter_noise" and block_page is not None and bm_start and block_page >= bm_start:
                pass
            else:
                continue

        block_key = _page_block_key(block_page, block_id)
        if block_id is not None and (block_key in consumed_caption_keys or block_id in consumed_caption_ids_unkeyed):
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
            bm_start2 = getattr(document_structure, "spread_start", None) if document_structure else None
            if role != "frontmatter_noise" or block_page is None or not bm_start2 or block_page < bm_start2:
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
            # Emit matched figures and tables on this page before references
            if block_page is not None:
                for fig in figures_by_page.get(block_page, []):
                    if str(fig["figure_id"]).startswith("unmatched_legend_"):
                        continue
                    lines.append(f"![[render/figures/{fig['figure_id']}.md]]")
                    lines.append("")
                figures_by_page.pop(block_page, None)
                for tbl_id in tables_by_page.get(block_page, []):
                    lines.append(f"![[render/tables/{tbl_id}.md]]")
                    lines.append("")
                tables_by_page.pop(block_page, None)
            lines.append(f"## {text}")
            lines.append("")
        elif role in ("subsection_heading", "sub_subsection_heading", "section_heading"):
            last_structured_insert_page = None
            last_structured_insert_bbox = None
            text = _display_heading_text(block, text)
            if role == "section_heading":
                if _should_suppress_frontmatter_heading(text):
                    continue
                if _is_bogus_heading(text):
                    if text:
                        lines.append(text)
                        lines.append("")
                    continue
            key = (int(block.get("page", 0) or 0), block.get("block_id"))
            prefix = _heading_prefix_map.get(key)
            if prefix is None:
                depth = _heading_number_depth_text(text)
                prefix = "##" if depth <= 1 else "###"
            lines.append(f"{prefix} {text}")
            lines.append("")
        elif role == "structured_insert":
            container_text = block.get("_container_text")
            if container_text and isinstance(container_text, str):
                source_text = normalize_ocr_math_text(" ".join(container_text.replace("\n", " ").split()))
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
            tbl_ids_for_page = tables_by_page.get(block_page, [])
            if tbl_ids_for_page:
                tbl_id = tbl_ids_for_page.pop(0)
                lines.append(f"![[render/tables/{tbl_id}.md]]")
                lines.append("")
            elif text:
                lines.append(f"> **Table Caption:** {text}")
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
                if block_page is not None and block.get("_text_source") == "pdf_text_layer_fallback":
                    if any(
                        _backfill_coverage_in_existing(text, existing)
                        >= _BACKFILL_OVERLAP_REJECT_THRESHOLD
                        for existing in _emitted_body_text_by_page.get(block_page, [])
                    ):
                        continue
                _emitted_body_text_by_page.setdefault(block_page if block_page is not None else -1, []).append(text)
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
