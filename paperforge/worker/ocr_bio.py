"""Author biography detection utilities and passes."""

import re

# --- Category patterns ---

_CAREER_POSITION_PATTERN = re.compile(
    r"\b(?:"
    r"is\s+(?:now\s+|currently\s+)?(?:(?:a|an)\s+)?"
    r"(?:assistant\s+professor|associate\s+professor|"
    r"postdoctoral\s+(?:fellow|researcher|research)|"
    r"professor|researcher|scientist|physician|postdoc|fellow|"
    r"ph\.?d\.?\s+student|clinical\s+doctor)|"
    r"receive?d\s+(?:her|his|their)\s+(?:PhD|Doctorate|doctoral|degree)|"
    r"earne?d\s+(?:her|his|their|a)\s+(?:PhD|degree|doctorate)|"
    r"complete?d\s+(?:her|his|their)\s+(?:PhD|doctoral|residency|fellowship)|"
    r"obtaine?d\s+(?:her|his|their)\s+(?:Ph\.?D\.?|Doctorate|doctoral|degree)"
    r")\b",
    re.IGNORECASE,
)

_EDUCATION_PATTERN = re.compile(
    r"\b(?:"
    r"holds?\s+(?:a|an)\s+(?:BSc|MSc|Ph\.?D\.?|degree|diploma)|"
    r"obtaine?d\s+(?:her|his|their)\s+(?:Ph\.?D\.?|degree|doctorate|BSc|MSc)|"
    r"(?:Ph\.?D\.?|MSc|BSc)\s+(?:student|candidate|graduate)|"
    r"(?:MD|PhD|MSc|M\.D\.|Ph\.D\.)\b"
    r")\b",
    re.IGNORECASE,
)

_RESEARCH_INTEREST_PATTERN = re.compile(
    r"\b(?:"
    r"research(?:es|ing)?\s+(?:interests?|focus|areas?|includes?|encompasses?)|"
    r"specializes?\s+in\b|"
    r"focuse?d\s+(?:on|in)\b|"
    r"works?\s+(?:in|at|on)\b|"
    r"her\s+research\s+focus"
    r")\b",
    re.IGNORECASE,
)

_INSTITUTION_PATTERN = re.compile(
    r"\b(?:"
    r"(?:Department|Laboratory|Institute|University|College|School|Center|Hospital)\s+of|"
    r"(?:University|College|Institute)\s+(?:of|at|in)\b"
    r")\b",
    re.IGNORECASE,
)

_PUBLICATION_PATTERN = re.compile(
    r"\b(?:"
    r"authore?d\s+(?:over|more than|\d+)|"
    r"publishe?d\s+(?:over|more than|\d+)|"
    r"has\s+(?:published|authored|co-authored)|"
    r"co-authore?d\s+\d+"
    r")\b",
    re.IGNORECASE,
)


# --- Helper: bbox distance (local, since ocr_scores doesn't export one) ---

def _bbox_distance(a: list[float], b: list[float]) -> float:
    """Minimum distance between two bboxes [x0,y0,x1,y1]. 0 if overlapping."""
    if len(a) < 4 or len(b) < 4:
        return float("inf")
    # Separating axis: no overlap on x or y axis
    if a[2] <= b[0] and a[0] <= b[0] and b[0] - a[2] >= 0:
        dx = b[0] - a[2]
    elif b[2] <= a[0] and b[0] <= a[0] and a[0] - b[2] >= 0:
        dx = a[0] - b[2]
    else:
        dx = 0
    if a[3] <= b[1] and a[1] <= b[1] and b[1] - a[3] >= 0:
        dy = b[1] - a[3]
    elif b[3] <= a[1] and b[1] <= a[1] and a[1] - b[3] >= 0:
        dy = a[1] - b[3]
    else:
        dy = 0
    return float(dx * dx + dy * dy) ** 0.5


# --- Bio text scoring ---

def _bio_text_score(text: str) -> tuple[int, set[str]]:
    """Score 0-5 and return category set.

    Category-weighted: each signal type contributes independently.
    Returns (0, set()) for text too short (<5 words) or too long (>200 words).
    """
    if not text:
        return 0, set()
    words = text.split()
    if len(words) < 5 or len(words) > 200:
        return 0, set()

    categories: set[str] = set()
    score = 0

    if _CAREER_POSITION_PATTERN.search(text):
        score += 3
        categories.add("career_position")

    if _EDUCATION_PATTERN.search(text):
        score += 2
        categories.add("education")

    if _RESEARCH_INTEREST_PATTERN.search(text):
        score += 2
        categories.add("research_interest")

    if _INSTITUTION_PATTERN.search(text):
        score += 1
        categories.add("institution")

    if _PUBLICATION_PATTERN.search(text):
        score += 1
        categories.add("publication")

    return min(score, 5), categories


# --- Formal figure/table prefix guard ---

_FORMAL_OBJECT_PREFIX = re.compile(
    r"^\s*(?:"
    r"Fig\.?|Figure|Supplementary\s+Fig\.?|Supplementary\s+Figure|"
    r"Extended\s+Data\s+Fig\.?|Extended\s+Data\s+Figure|"
    r"Scheme|Table|Supplementary\s+Table"
    r")\s*(?:S\.?\s*)?\d+",
    re.IGNORECASE,
)


def _has_formal_figure_number(text: str) -> bool:
    """True if text starts with a formal figure/table designation."""
    return bool(_FORMAL_OBJECT_PREFIX.search(text.strip()))


# --- Portrait-like image detection ---

def _is_portrait_like(block: dict) -> bool:
    """Check if an image block has portrait-like dimensions."""
    bbox = block.get("bbox")
    if not bbox:
        return False
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    if width <= 0 or height <= 0:
        return False
    aspect = min(width, height) / max(width, height)
    if aspect < 0.4:
        return False
    if width > 400 or height > 400:
        return False
    raw_label = str(block.get("raw_label", "") or "")
    return raw_label not in {"line", "chart", "graph"}


def _any_portrait_like(blocks: list[dict]) -> bool:
    """True if any block in the list is portrait-like."""
    return any(_is_portrait_like(b) for b in blocks)


def _any_bio_text(blocks: list[dict], min_score: int = 3) -> bool:
    """True if any block has bio text score >= min_score."""
    return any(
        _bio_text_score(str(b.get("text", "") or ""))[0] >= min_score
        for b in blocks
    )


# --- Reference format guard ---

def _looks_like_reference(text: str) -> bool:
    """True if text looks like a standard reference entry (not bio)."""
    text_stripped = text.strip()
    has_ref_number = bool(re.match(r"^\[\d+\]\s+", text_stripped))
    if has_ref_number and "et al" in text_stripped.lower():
        return True
    return bool(has_ref_number and re.search(r"\d{4}[,;:]", text_stripped))

# --- Block key helpers ---

def _add_block_keys(key_set: set[tuple[int, str]], block: dict) -> None:
    """Add (page, block_id) to a set from a block dict."""
    page = int(block.get("page", 0) or 0)
    bid = str(block.get("block_id", ""))
    if bid:
        key_set.add((page, bid))


# --- Spatial proximity ---

def _nearby_blocks(
    blocks: list[dict],
    anchor: dict,
    max_distance: float = 120,
    same_page: bool = True,
    anchor_bbox: list[float] | None = None,
    exclude_block_ids: set[str] | None = None,
) -> list[dict]:
    """Return blocks within max_distance of anchor.

    Supports anchor with bbox, cluster_bbox, or explicit anchor_bbox arg.
    """
    anchor_page = int(anchor.get("page", 0) or 0)
    ab = (
        anchor_bbox
        or anchor.get("bbox")
        or anchor.get("cluster_bbox")
        or anchor.get("block_bbox")
        or [0, 0, 0, 0]
    )
    exclude = set(exclude_block_ids or [])

    result = []
    for block in blocks:
        if same_page and int(block.get("page", 0) or 0) != anchor_page:
            continue
        if block is anchor:
            continue
        bid = str(block.get("block_id", ""))
        if bid in exclude:
            continue
        block_bbox = block.get("bbox")
        if not block_bbox:
            continue
        dist = _bbox_distance(ab, block_bbox)
        if dist <= max_distance:
            result.append(block)
    return result


# --- Reference start page resolution ---

def _resolve_ref_start_page(blocks: list[dict]) -> int | None:
    """Find the first page where references begin.

    Prefers reference_heading role, falls back to reference_zone.
    Returns None if no reference zone exists.
    """
    ref_heading_pages = sorted({
        int(b.get("page", 0) or 0)
        for b in blocks
        if b.get("role") == "reference_heading"
    })
    if ref_heading_pages:
        return ref_heading_pages[0]

    ref_zone_pages = sorted({
        int(b.get("page", 0) or 0)
        for b in blocks
        if b.get("zone") == "reference_zone"
    })
    if ref_zone_pages:
        return ref_zone_pages[0]

    return None


# --- Figure match guards ---

def _is_strongly_figure_matched(
    block_key: tuple[int, str],
    figure_inventory: dict,
) -> bool:
    """True if block_key is consumed by a strong (matched) figure."""
    for mf in figure_inventory.get("matched_figures", []):
        legend_page = int(
            mf.get("legend_page", mf.get("page", 0)) or 0
        )
        legend_bid = str(mf.get("legend_block_id", ""))
        if (legend_page, legend_bid) == block_key:
            return True
        for asset in mf.get("matched_assets", []):
            ap = int(asset.get("page", legend_page) or 0)
            abid = str(asset.get("block_id", ""))
            if (ap, abid) == block_key:
                return True
    return False


def _is_protected_strong_figure(fig: dict) -> bool:
    """True if this figure match is too strong to reverse."""
    if fig.get("figure_number") is not None and (fig.get("confidence") or 0) >= 0.5:
        return True
    settlement = str(fig.get("settlement_type") or "")
    if settlement in {"same_page", "grouped_approximate", "composite_parent", "scoped_composite_parent"}:
        return True
    flags = set(fig.get("flags") or [])
    return bool(flags & {"composite_parent_match"})

def _is_reversible_weak_figure_match(fig: dict) -> bool:
    """True if figure match is weak enough to reverse to author_bio (P2+)."""
    if _is_protected_strong_figure(fig):
        return False
    settlement = str(fig.get("settlement_type") or "")
    flags = set(fig.get("flags") or [])
    confidence = float(fig.get("confidence") or 0)

    if settlement in {"sequential", "group_sequential", "sequence_match"}:
        return True
    if flags & {"sequential_match", "group_sequential_match", "sequence_match"}:
        return True
    return confidence < 0.45


# --- Pass B: residual author bio (unmatched_assets + unresolved_clusters) ---

def residual_author_bio_pass(
    figure_inventory: dict,
    blocks: list[dict],
    *,
    include_ambiguous: bool = False,
    include_weak_matched: bool = False,
) -> None:
    """Residual bio detection for figure inventory leftovers.

    P1 scope: unmatched_assets + unresolved_clusters.
    Check portrait-like + nearby bio text.
    Does NOT touch ambiguous_figures or matched_figures (gated by flags).
    """
    if "_pruned_author_bio_artifacts" not in figure_inventory:
        figure_inventory["_pruned_author_bio_artifacts"] = []

    # Build block index by (page, block_id)
    block_by_page_id: dict[tuple[int, str], dict] = {}
    for b in blocks:
        pid = (int(b.get("page", 0) or 0), str(b.get("block_id", "")))
        block_by_page_id[pid] = b

    # --- unmatched_assets ---
    remaining_assets: list[dict] = []
    for asset in figure_inventory.get("unmatched_assets", []):
        if not _is_portrait_like(asset):
            remaining_assets.append(asset)
            continue
        # Check nearby blocks for bio text
        nearby = _nearby_blocks(blocks, asset, max_distance=80, same_page=True)
        if not _any_bio_text(nearby, min_score=3):
            remaining_assets.append(asset)
            continue

        # Move to bio artifacts
        page = int(asset.get("page", 0) or 0)
        bid = str(asset.get("block_id", ""))
        figure_inventory["_pruned_author_bio_artifacts"].append({
            "source": "residual_author_bio_pass",
            "page": page,
            "block_id": bid,
            "old_role": asset.get("role", ""),
            "text_preview": str(asset.get("text", "") or "")[:80],
        })

        # Set block role if block exists
        block_key = (page, bid)
        if block_key in block_by_page_id:
            b = block_by_page_id[block_key]
            b["_object_owner_family"] = "author_bio"
            b["_excluded_from_figure_inventory"] = True
            old_role = b.get("role", "")
            if old_role in {"figure_asset", "media_asset"}:
                b["role"] = "author_bio_asset"
                b["render_default"] = False
                b["index_default"] = False
            from paperforge.worker.ocr_decisions import record_decision
            record_decision(
                b, stage="residual_author_bio_pass",
                old_role=old_role, new_role=b.get("role", old_role),
                reason="unmatched portrait asset with nearby bio text",
            )

    figure_inventory["unmatched_assets"] = remaining_assets

    # --- unresolved_clusters ---
    remaining_clusters: list[dict] = []
    for cluster in figure_inventory.get("unresolved_clusters", []):
        cluster_blocks = [
            block_by_page_id.get((
                int(cluster.get("page", 0) or 0),
                str(bid),
            ))
            for bid in (cluster.get("media_block_ids") or [])
            if block_by_page_id.get((
                int(cluster.get("page", 0) or 0),
                str(bid),
            ))
        ]
        if not _any_portrait_like(cluster_blocks):
            remaining_clusters.append(cluster)
            continue
        # Check nearby blocks for bio text
        cluster_page = int(cluster.get("page", 0) or 0)
        cluster_anchor = {
            "page": cluster_page,
            "cluster_bbox": cluster.get("cluster_bbox") or cluster.get("bbox") or [0, 0, 0, 0],
        }
        nearby = _nearby_blocks(blocks, cluster_anchor, max_distance=80, same_page=True)
        if not _any_bio_text(nearby, min_score=3):
            remaining_clusters.append(cluster)
            continue

        # Move to bio artifacts
        cluster_key = cluster.get("key", "")
        figure_inventory["_pruned_author_bio_artifacts"].append({
            "source": "residual_author_bio_pass",
            "page": cluster_page,
            "block_id": cluster_key or "cluster",
            "old_role": "unresolved_cluster",
            "text_preview": str(cluster.get("text", "") or "")[:80],
        })

        # Tag each portrait block in cluster as author_bio_asset
        for cb in cluster_blocks:
            if _is_portrait_like(cb):
                cb["_object_owner_family"] = "author_bio"
                cb["_excluded_from_figure_inventory"] = True
                old_role = cb.get("role", "")
                if old_role in {"figure_asset", "media_asset"}:
                    cb["role"] = "author_bio_asset"
                    cb["render_default"] = False
                    cb["index_default"] = False

    figure_inventory["unresolved_clusters"] = remaining_clusters

    # --- ambiguous_figures: gated (P2+) ---
    if not include_ambiguous:
        pass  # not touched in P1

    # --- matched_figures reversal: gated (P2+) ---
    if not include_weak_matched:
        pass  # not touched in P1

# --- Pass C: post-ref bio cleanup ---

def post_ref_bio_cleanup(
    figure_inventory: dict,
    blocks: list[dict],
    ref_start_page: int | None = None,
) -> None:
    """Fix pure-text author bios in post-ref region.

    P0 scope: only reference_item/reference_heading in reference_zone.
    Writes affected block keys into figure_inventory["_pruned_author_bio_artifacts"]
    so the downstream prune pass removes them from inventory.
    """
    if ref_start_page is None:
        return

    if "_pruned_author_bio_artifacts" not in figure_inventory:
        figure_inventory["_pruned_author_bio_artifacts"] = []

    for block in blocks:
        page = int(block.get("page", 0) or 0)
        if page < ref_start_page:
            continue

        zone = block.get("zone", "")
        if zone not in {"reference_zone", "tail_nonref_hold_zone", "post_reference_backmatter_zone"}:
            continue

        role = block.get("role", "")
        if role not in {"reference_item", "reference_heading", "figure_caption", "structured_insert_candidate"}:
            continue

        text = str(block.get("text", "") or "")
        if not text:
            continue

        block_key = (page, str(block.get("block_id", "")))

        # Skip if consumed by strong figure match
        if _is_strongly_figure_matched(block_key, figure_inventory):
            continue

        # Skip formal figure/table markers
        if _has_formal_figure_number(text):
            continue

        # Skip if looks like a real reference
        if _looks_like_reference(text):
            continue

        score, categories = _bio_text_score(text)
        if score < 4 or len(categories) < 2:
            continue

        # Override role
        old_role = role
        block["role"] = "backmatter_body"
        block["zone"] = ""        # clear reference_zone so render doesn't interleave with refs
        block["render_default"] = True
        block["_object_owner_family"] = "author_bio"
        block["_excluded_from_figure_inventory"] = True

        from paperforge.worker.ocr_decisions import record_decision
        record_decision(
            block, stage="post_ref_bio_cleanup",
            old_role=old_role, new_role="backmatter_body",
            reason=f"post-ref {role} block with bio signals (score={score}, cats={categories})",
        )

        figure_inventory["_pruned_author_bio_artifacts"].append({
            "source": "post_ref_bio_cleanup",
            "page": page,
            "block_id": block.get("block_id", ""),
            "old_role": old_role,
            "text_preview": text[:80],
        })


# --- Prune figure inventory after bio ---

def prune_figure_inventory_after_bio(figure_inventory: dict) -> None:
    """Remove bio-owned entries from figure_inventory.

    Reads _pruned_author_bio_artifacts from both Pass B and Pass C,
    then removes matching entries from ambiguous_figures and held_figures.
    """
    bio_block_keys: set[tuple[int, str]] = set()
    for artifact in figure_inventory.get("_pruned_author_bio_artifacts", []):
        if "page" in artifact and "block_id" in artifact:
            bio_block_keys.add((
                int(artifact["page"]),
                str(artifact["block_id"]),
            ))

    # Prune ambiguous_figures
    remaining_amb: list[dict] = []
    for amb in figure_inventory.get("ambiguous_figures", []):
        legend_page = int(
            amb.get("legend_page", amb.get("page", 0)) or 0
        )
        legend_bid = str(amb.get("legend_block_id", ""))
        if (legend_page, legend_bid) in bio_block_keys:
            continue
        remaining_amb.append(amb)
    figure_inventory["ambiguous_figures"] = remaining_amb

    # Prune held_figures
    remaining_hf: list[dict] = []
    for hf in figure_inventory.get("held_figures", []):
        hf_page = int(hf.get("page", 0) or 0)
        hf_bid = str(hf.get("legend_block_id", ""))
        if (hf_page, hf_bid) in bio_block_keys:
            continue
        remaining_hf.append(hf)
    figure_inventory["held_figures"] = remaining_hf

    figure_inventory["official_figure_count"] = len(figure_inventory.get("matched_figures", []))
