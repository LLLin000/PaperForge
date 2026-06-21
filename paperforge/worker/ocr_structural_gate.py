from __future__ import annotations

import re
from dataclasses import dataclass, field

VERIFY_REQUIRED = {
    "paper_title",
    "authors",
    "abstract_heading",
    "abstract_body",
    "keywords",
    "section_heading",
    "subsection_heading",
    "reference_heading",
    "reference_item",
    "figure_caption",
    "table_caption",
    "table_html",
}

_SAFE_PRESERVED_ROLES = {
    "frontmatter_noise",
    "frontmatter_support",
    "structured_insert",
    "non_body_insert",
    "backmatter_body",
    "body_paragraph",
    "ocr_raw_error",
}


@dataclass
class VerifiedRoleDecision:
    role: str
    status: str
    source: str
    evidence: list[str] = field(default_factory=list)
    seed_role: str = "unknown_structural"
    role_candidate: str | None = None
    render_default: bool | None = None

    def as_block_fields(self) -> dict:
        fields = {
            "role": self.role,
            "role_verification_status": self.status,
            "role_source": self.source,
            "role_evidence": list(self.evidence),
            "seed_role": self.seed_role,
        }
        if self.role_candidate is not None:
            fields["role_candidate"] = self.role_candidate
        if self.render_default is not None:
            fields["render_default"] = self.render_default
        return fields


@dataclass
class RoleGateContext:
    source_frontmatter_anchor_ids: dict[str, set[str | int]] = field(default_factory=dict)
    abstract_span: dict | None = None
    reference_zone: dict | None = None
    accepted_heading_block_ids: set[str | int] = field(default_factory=set)
    accepted_caption_block_ids: set[str | int] = field(default_factory=set)
    accepted_table_block_ids: set[str | int] = field(default_factory=set)


def _duplicate_block_ids(blocks: list[dict]) -> set[str]:
    counts: dict[str, int] = {}
    for block in blocks:
        block_id = block.get("block_id")
        if block_id is None:
            continue
        key = str(block_id)
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _artifact_block_id(block: dict, duplicate_ids: set[str]) -> str | int | None:
    block_id = block.get("block_id")
    if block_id is None:
        return None
    if str(block_id) in duplicate_ids:
        return f"p{int(block.get('page', 0) or 0)}:{block_id}"
    return block_id


def _bid(block: dict) -> str | int | None:
    return block.get("block_id")


def _page_bid(block: dict) -> str:
    return f"p{int(block.get('page', 0) or 0)}:{block.get('block_id')}"


def _artifact_membership_contains(block: dict, ids: set) -> bool:
    block_id = _bid(block)
    if block_id in ids:
        return True
    return _page_bid(block) in ids


def accept_role(role: str, seed_role: str, source: str, evidence: list[str]) -> VerifiedRoleDecision:
    return VerifiedRoleDecision(role=role, status="ACCEPT", source=source, evidence=evidence, seed_role=seed_role)


def hold_role(seed_role: str, reason: str) -> VerifiedRoleDecision:
    return VerifiedRoleDecision(
        role="unknown_structural",
        status="HOLD",
        source="structural_gate",
        evidence=[reason],
        seed_role=seed_role,
        role_candidate=seed_role,
        render_default=False,
    )


def resolve_verified_role(block: dict, context: RoleGateContext) -> VerifiedRoleDecision:
    current_role = str(block.get("role") or "unassigned")
    seed_role = str(block.get("seed_role") or current_role or "unknown_structural")
    proposal = seed_role if current_role in {"", "unassigned"} else current_role
    block_id = _bid(block)

    if (
        current_role not in {"", "unassigned", "unknown_structural"}
        and current_role not in VERIFY_REQUIRED
        and (seed_role not in VERIFY_REQUIRED or current_role in _SAFE_PRESERVED_ROLES)
        and not (current_role in {"frontmatter_noise"} and seed_role in VERIFY_REQUIRED)
    ):
        return accept_role(
            current_role,
            seed_role,
            "non_structural_normalized_role",
            ["pre-gate normalized non-structural role preserved"],
        )

    if proposal == "paper_title" or seed_role == "paper_title":
        if block_id in context.source_frontmatter_anchor_ids.get("title", set()):
            return accept_role(
                "paper_title", seed_role, "source_frontmatter_title_anchor", ["matched source title anchor"]
            )
        # Zone-based fallback: title-like block on the first-surviving page's
        # frontmatter_main_zone with title-appropriate raw_label is accepted
        # even without source anchor — handles preproof-drop papers where the
        # real title appears on page 2.
        raw_label = str(block.get("raw_label") or "")
        if block.get("zone") == "frontmatter_main_zone" and raw_label in {"doc_title", "paragraph_title"}:
            return accept_role(
                "paper_title", seed_role, "frontmatter_zone_title",
                [f"title accepted via frontmatter_main_zone + {raw_label} label"],
            )
        return hold_role(seed_role, "paper title seed lacks source-backed title anchor")
    # Structural signal: raw_label=doc_title on page 2 → paper_title (title repeat)
    # Accept if confirmed by source anchor or by frontmatter_main_zone context.
    if block.get("raw_label") == "doc_title" and (block.get("page") or 0) == 2:
        block_id = _artifact_block_id(block, context._duplicate_block_ids) if hasattr(context, "_duplicate_block_ids") else block.get("block_id")
        if block_id and block_id in context.source_frontmatter_anchor_ids.get("title", set()):
            return accept_role(
                "paper_title",
                seed_role,
                "doc_title_label_page2_repeat",
                ["doc_title labeled block on page 2 matches source title anchor"],
            )
        if block.get("zone") == "frontmatter_main_zone":
            return accept_role(
                "paper_title",
                seed_role,
                "doc_title_label_page2_zone",
                ["doc_title labeled block on page 2 accepted via frontmatter_main_zone"],
            )
        return hold_role(
            seed_role,
            "page-2 doc_title without source anchor verification",
        )
    # Source-anchor override: if block_id matches a source anchor, accept the
    # anchored role regardless of seed_role (OCR may have missed the label).
    # Must also match page to avoid block_id=2 on page 7 matching page-1 anchor.
    block_page = block.get("page")
    for anchored_field in ("authors",):
        anchor_ids = context.source_frontmatter_anchor_ids.get(anchored_field, set())
        if block_id in anchor_ids and seed_role != anchored_field:
            # Determine anchor page from page-qualified IDs (e.g. "p1:2")
            anchor_page = None
            for aid in anchor_ids:
                if isinstance(aid, str) and aid.startswith("p") and ":" in aid:
                    try:
                        anchor_page = int(aid.split(":")[0][1:])
                    except (ValueError, IndexError):
                        pass
            # Only accept if no page info available OR block is on anchor's page
            if anchor_page is None or block_page == anchor_page:
                return accept_role(
                    anchored_field,
                    seed_role,
                    f"source_frontmatter_{anchored_field}_anchor_override",
                    [f"block matched source {anchored_field} anchor (OCR label override)"],
                )
    if proposal == "authors" or seed_role == "authors":
        if block_id in context.source_frontmatter_anchor_ids.get("authors", set()):
            return accept_role(
                "authors", seed_role, "source_frontmatter_authors_anchor", ["matched source authors anchor"]
            )
        # Zone-based fallback: author block in frontmatter_main_zone on first
        # surviving page — handles preproof-drop papers.
        if block.get("zone") == "frontmatter_main_zone" and block.get("raw_label") == "text":
            return accept_role(
                "authors", seed_role, "frontmatter_zone_authors",
                ["authors accepted via frontmatter_main_zone + text label"],
            )
        return hold_role(seed_role, "authors seed lacks source-backed authors anchor")
    if proposal == "keywords" or seed_role == "keywords":
        if _artifact_membership_contains(block, set((context.abstract_span or {}).get("keyword_block_ids", []))):
            return accept_role(
                "keywords", seed_role, "abstract_span_keyword_boundary", ["keywords follow accepted abstract span"]
            )
        return hold_role(seed_role, "keywords seed lacks abstract-span keyword boundary")

    # Abstract heading/body verification via abstract_span
    if proposal == "abstract_heading" or seed_role == "abstract_heading":
        span = context.abstract_span or {}
        if span.get("heading_block_id") in {block_id, _page_bid(block)}:
            return accept_role(
                "abstract_heading", seed_role, "abstract_span_heading", ["abstract heading matched span"]
            )
        if span.get("status") == "MISSING":
            return accept_role(
                "abstract_heading", seed_role, "abstract_span_missing_fallback",
                ["abstract heading accepted from seed (no span to verify)"],
            )
        return hold_role(seed_role, "abstract heading not in abstract_span")
    if proposal == "abstract_body" or seed_role == "abstract_body":
        span = context.abstract_span or {}
        if _artifact_membership_contains(block, set(span.get("body_block_ids", []))):
            return accept_role("abstract_body", seed_role, "abstract_span_body", ["abstract body matched span"])
        if span.get("status") == "MISSING":
            return accept_role(
                "abstract_body", seed_role, "abstract_span_missing_fallback",
                ["abstract body accepted from seed (no span to verify)"],
            )
        # If block is already body-like, fallback to body_paragraph
        if current_role == "body_paragraph" or block.get("zone") == "body_zone":
            return VerifiedRoleDecision(
                role="body_paragraph",
                status="ACCEPT",
                source="structural_gate_fallback",
                evidence=["abstract body rejected, falling back to body_paragraph"],
                seed_role=seed_role,
                render_default=True,
            )
        return hold_role(seed_role, "abstract body not in abstract_span")

    # Reference heading/item verification via reference_zone
    if proposal == "reference_heading" or seed_role == "reference_heading":
        zone = context.reference_zone or {}
        if zone.get("heading_block_id") in {block_id, _page_bid(block)}:
            return accept_role(
                "reference_heading", seed_role, "reference_zone_heading", ["reference heading matched zone"]
            )
        return hold_role(seed_role, "reference heading not in reference_zone")
    if proposal == "reference_item" or seed_role == "reference_item":
        zone = context.reference_zone or {}
        if _artifact_membership_contains(block, set(zone.get("item_block_ids", []))):
            return accept_role("reference_item", seed_role, "reference_zone_item", ["reference item matched zone"])
        if current_role == "reference_item" and not zone.get("item_block_ids"):
            return accept_role(
                "reference_item", seed_role, "reference_zone_fallback",
                ["reference item accepted (pre-gate resolution, empty zone)"],
            )
        # Fallback: if block is body-like, fallback to body_paragraph
        if current_role == "body_paragraph" or block.get("zone") == "body_zone":
            return VerifiedRoleDecision(
                role="body_paragraph",
                status="ACCEPT",
                source="structural_gate_fallback",
                evidence=["reference item rejected, falling back to body_paragraph"],
                seed_role=seed_role,
                render_default=True,
            )
        return hold_role(seed_role, "reference item not in reference_zone")

    # Section/subsection heading verification via accepted_heading_block_ids or body zone evidence
    if proposal in {"section_heading", "subsection_heading"} or seed_role in {"section_heading", "subsection_heading"}:
        marker_type = str(((block.get("marker_signature") or {}).get("type")) or "none")
        if _artifact_membership_contains(block, set(context.accepted_heading_block_ids)):
            return accept_role(proposal, seed_role, "accepted_heading", ["heading verified by heading artifact"])
        if marker_type in {
            "canonical_section_name",
            "heading_arabic",
            "heading_decimal",
            "heading_roman",
            "heading_alpha",
            "heading_numbered",
        }:
            return accept_role(
                proposal,
                seed_role,
                "heading_marker_evidence",
                [f"heading verified by marker evidence: {marker_type}"],
            )
        if block.get("zone") in {"body_zone", "tail_body_zone"}:
            return accept_role(proposal, seed_role, "body_zone_heading", ["heading accepted via body zone evidence"])
        return hold_role(seed_role, f"{proposal} lacks heading artifact evidence")

    if proposal == "figure_caption" or seed_role == "figure_caption":
        if _artifact_membership_contains(block, set(context.accepted_caption_block_ids)):
            return accept_role(
                "figure_caption",
                seed_role,
                "accepted_figure_caption_artifact",
                ["figure caption matched accepted figure artifact"],
            )
        if current_role == "figure_caption_candidate":
            return VerifiedRoleDecision(
                role="figure_caption_candidate",
                status="CANDIDATE",
                source="pre_object_figure_caption_candidate",
                evidence=["figure caption preserved for figure inventory synthesis"],
                seed_role=seed_role,
                role_candidate="figure_caption",
                render_default=False,
            )
        return VerifiedRoleDecision(
            role="figure_caption_candidate",
            status="CANDIDATE",
            source="pre_object_figure_caption_candidate",
            evidence=["figure caption seed requires figure inventory verification"],
            seed_role=seed_role,
            role_candidate="figure_caption",
            render_default=False,
        )

    if proposal == "table_caption" or seed_role == "table_caption":
        if _artifact_membership_contains(block, set(context.accepted_table_block_ids)):
            return accept_role(
                "table_caption",
                seed_role,
                "accepted_table_caption_artifact",
                ["table caption matched accepted table artifact"],
            )
        _marker = str(((block.get("marker_signature") or {}).get("type")) or "")
        _zone = str(block.get("zone") or "")
        _text = str(block.get("text") or "").strip()
        if _marker in {"figure_number", "table_number"} or (
            _zone == "display_zone" and _text.lower().startswith(("fig", "figure", "table"))
        ):
            return accept_role(
                "table_caption",
                seed_role,
                "text_evidence_table_caption",
                ["table caption accepted via text-prefix + marker/zone evidence"],
            )
        return VerifiedRoleDecision(
            role="table_caption_candidate",
            status="CANDIDATE",
            source="pre_object_table_caption_candidate",
            evidence=["table caption seed requires table inventory verification"],
            seed_role=seed_role,
            role_candidate="table_caption",
            render_default=False,
        )

    if proposal in VERIFY_REQUIRED or seed_role in VERIFY_REQUIRED:
        return hold_role(seed_role, f"{proposal} requires structural verifier")
    source = "non_structural_seed" if current_role in {"", "unassigned"} else "non_structural_normalized_role"
    return accept_role(proposal, seed_role, source, ["non-structural role accepted"])


def build_document_abstract_span(blocks: list[dict], context: dict) -> dict:
    duplicate_ids = _duplicate_block_ids(blocks)
    support_ids = set(context.get("frontmatter_support_zone_ids", set()))
    support_ids |= set(context.get("publisher_sidebar_zone_ids", set()))
    support_ids |= set(context.get("correspondence_zone_ids", set()))
    support_ids |= set(context.get("affiliation_zone_ids", set()))
    main_ids = set(context.get("frontmatter_main_zone_ids", set()))
    body_start_id = context.get("body_start_block_id")
    heading_index = next(
        (
            idx
            for idx, block in enumerate(blocks)
            if block.get("seed_role") == "abstract_heading" or re.sub(r"\s+", "", str(block.get("text", "")).strip().lower()) == "abstract"
        ),
        None,
    )
    if heading_index is None:
        return {
            "heading_block_id": None,
            "body_block_ids": [],
            "excluded_support_block_ids": [],
            "status": "MISSING",
            "stop_reason": "missing_heading",
            "confidence": 0.0,
        }
    body_ids: list = []
    excluded: list = []
    stop_reason = "document_end"
    heading_page = int(blocks[heading_index].get("page", 0) or 0)
    leading_body_ids: list = []
    for block in reversed(blocks[:heading_index]):
        block_page = int(block.get("page", 0) or 0)
        if block_page != heading_page:
            break
        block_id = _artifact_block_id(block, duplicate_ids)
        seed_role = block.get("seed_role", "")
        text = str(block.get("text", "") or "").strip().lower()
        if block_id in support_ids:
            excluded.insert(0, block_id)
            continue
        if seed_role in {"abstract_body", "body_paragraph"} and text and not text.startswith(("keywords", "key words", "highlights")):
            leading_body_ids.insert(0, block_id)
            continue
        break
    body_ids.extend(leading_body_ids)
    accepted_inside_abstract = {"abstract_body", "body_paragraph", "section_heading", "subsection_heading"}
    _EXCLUDED_FRONTMATTER_SEED_ROLES = frozenset(
        {
            "authors",
            "email",
            "affiliation",
            "doi",
            "correspondence",
            "highlights",
            "author_contribution",
            "data_availability",
        }
    )
    _EXCLUDED_FRONTMATTER_PREFIXES = (
        "doi",
        "submitted",
        "accepted",
        "published",
        "open access",
        "distributed under",
        "corresponding author",
        "academic editor",
        "subjects",
    )
    _STRUCTURED_ABSTRACT_HEADS = frozenset(
        {
            "background",
            "objective",
            "methods",
            "results",
            "conclusions",
            "purpose",
            "design",
            "setting",
            "patients",
            "participants",
            "intervention",
            "measurements",
            "main outcome measures",
            "findings",
            "interpretation",
            "introduction",
        }
    )
    for block in blocks[heading_index + 1 :]:
        block_id = _artifact_block_id(block, duplicate_ids)
        if block_id == body_start_id or block.get("block_id") == body_start_id:
            stop_reason = "body_start"
            break
        text = str(block.get("text", "") or "").strip().lower()
        intro_text = text.lstrip("0123456789. ")
        seed_role = block.get("seed_role", "")
        if seed_role in _EXCLUDED_FRONTMATTER_SEED_ROLES:
            excluded.append(block_id)
            continue
        if text.startswith(_EXCLUDED_FRONTMATTER_PREFIXES):
            excluded.append(block_id)
            continue
        if block.get("seed_role") in {"section_heading", "subsection_heading"} and intro_text.startswith(
            "introduction"
        ):
            stop_reason = "intro_like_heading"
            break
        if text.startswith(("keywords", "key words")):
            stop_reason = "keywords"
            break
        if text.startswith("highlights"):
            stop_reason = "highlights"
            break
        if block_id in support_ids:
            excluded.append(block_id)
            continue
        if any(text.startswith(h) for h in _STRUCTURED_ABSTRACT_HEADS):
            if block.get("seed_role") in {"section_heading", "subsection_heading", "abstract_body", "body_paragraph"}:
                body_ids.append(block_id)
                continue
            stop_reason = "structured_abstract_head"
            break
        block_page = int(block.get("page", 0) or 0)
        if main_ids and heading_page == 1 and block_page == heading_page and block_id not in main_ids:
            continue
        if block.get("seed_role") in accepted_inside_abstract:
            body_ids.append(block_id)
    return {
        "heading_block_id": _artifact_block_id(blocks[heading_index], duplicate_ids),
        "body_block_ids": body_ids,
        "excluded_support_block_ids": excluded,
        "status": "ACCEPT" if body_ids else "HOLD",
        "stop_reason": stop_reason,
        "confidence": 0.9 if body_ids else 0.2,
    }


def _matches_zone_id(block: dict, zone_ids: set) -> bool:
    bid = block.get("block_id")
    page = block.get("page", 0)
    return bid in zone_ids or f"p{page}:{bid}" in zone_ids


def _is_reference_anchor(block: dict) -> bool:
    role = block.get("role") or block.get("seed_role")
    if role in {"reference_heading", "reference_item"}:
        return True
    seed = block.get("seed_role")
    if seed in {"reference_heading", "reference_item"}:
        return True
    return False


def _is_reference_like(block: dict) -> bool:
    if _is_reference_anchor(block):
        return True
    role = block.get("role") or ""
    if role in {"reference_item", "reference_heading"}:
        return True
    seed = block.get("seed_role") or ""
    if seed == "reference_item":
        return True
    return False


def _block_sort_key(block: dict) -> tuple:
    page = int(block.get("page", 0) or 0)
    bbox = block.get("bbox") or [0, 0, 0, 0]
    col = 0 if len(bbox) < 4 else (0 if float(bbox[0]) < 600 else 1)
    y = float(bbox[1]) if len(bbox) >= 2 else 0.0
    x = float(bbox[0]) if len(bbox) >= 1 else 0.0
    return (page, col, y, x)


def _fill_gap_between_anchors(
    blocks: list[dict],
    anchor_before: dict,
    anchor_after: dict,
    duplicate_ids: set[str],
) -> list:
    gap_ids: list = []
    b_before = _block_sort_key(anchor_before)
    b_after = _block_sort_key(anchor_after)
    for block in blocks:
        key = _block_sort_key(block)
        if not (b_before < key < b_after):
            continue
        role = block.get("role") or block.get("seed_role")
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        skip_roles = {"section_heading", "subsection_heading", "sub_subsection_heading",
                       "backmatter_heading", "backmatter_body", "figure_caption",
                       "figure_asset", "media_asset", "table_caption", "table_html",
                       "table_asset", "structured_insert", "non_body_insert",
                       "frontmatter_support", "noise", "frontmatter_noise"}
        if role in skip_roles:
            continue
        if _is_reference_like(block):
            artifact_id = _artifact_block_id(block, duplicate_ids)
            if artifact_id is not None:
                gap_ids.append(artifact_id)
    return gap_ids


def _build_ordered_reference_items(
    blocks: list[dict],
    anchor_ids: set,
    duplicate_ids: set[str],
    heading_id: str | int | None = None,
    region_ids: set | None = None,
) -> list:
    """Build reference item_ids from ordered reference anchors with bounded gap repair."""
    anchors: list[dict] = []
    for block in blocks:
        artifact_id = _artifact_block_id(block, duplicate_ids)
        if artifact_id is None:
            continue
        if heading_id is not None and artifact_id == heading_id:
            continue
        in_anchor = artifact_id in anchor_ids
        in_region = region_ids and _matches_zone_id(block, region_ids)
        if (in_anchor or in_region) and _is_reference_anchor(block):
            anchors.append(block)

    if not anchors:
        return []

    anchors.sort(key=_block_sort_key)

    result: list = []
    anchor_ids_result: set = set()
    for i, anchor in enumerate(anchors):
        aid = _artifact_block_id(anchor, duplicate_ids)
        if aid is None or aid in anchor_ids_result:
            continue
        anchor_ids_result.add(aid)
        result.append(aid)
        if i + 1 < len(anchors):
            next_anchor = anchors[i + 1]
            next_key = _block_sort_key(next_anchor)
            gap = _fill_gap_between_anchors(blocks, anchor, next_anchor, duplicate_ids)
            for gid in gap:
                if gid not in result and gid != heading_id:
                    result.append(gid)

    return result


def build_verified_reference_zone_from_artifacts(blocks: list[dict], artifacts: dict) -> dict:
    duplicate_ids = _duplicate_block_ids(blocks)
    def _obj_get(obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    anchor = artifacts.get("reference_family_anchor") or {}
    region_bus = artifacts.get("region_bus") or {}
    tail_spread = artifacts.get("tail_spread") or {}
    numbering = artifacts.get("reference_numbering_family") or {}
    region_ids = set(_obj_get(region_bus, "reference_zone_ids", set()))
    # Expand region_ids with all blocks that carry reference_zone label
    # or reference_item role from per-block assignment (parallel to region_bus).
    for block in blocks:
        if block.get("zone") == "reference_zone" and _is_reference_anchor(block):
            artifact_id = _artifact_block_id(block, duplicate_ids)
            if artifact_id is not None:
                region_ids.add(artifact_id)
                region_ids.add(str(artifact_id))
    accepted_numbering_ids = set(_obj_get(numbering, "accepted_item_ids", set()))
    end_before = _obj_get(tail_spread, "reference_end_before_block_id")
    before_tail = set()
    if end_before:
        if isinstance(end_before, int):
            for block in blocks:
                if int(block.get("page", 0) or 0) < end_before:
                    before_tail.add(_artifact_block_id(block, duplicate_ids))
        else:
            for block in blocks:
                artifact_id = _artifact_block_id(block, duplicate_ids)
                raw_block_id = block.get("block_id")
                if artifact_id == end_before or raw_block_id == end_before:
                    break
                before_tail.add(artifact_id)
    item_ids = []
    for item_id in _obj_get(anchor, "item_block_ids", []):
        if region_ids and item_id not in region_ids:
            matching = [b for b in blocks if b.get("block_id") == item_id]
            if not matching or not _matches_zone_id(matching[0], region_ids):
                continue
        if before_tail and item_id not in before_tail:
            continue
        if accepted_numbering_ids and item_id not in accepted_numbering_ids:
            continue
        matched_block = next((b for b in blocks if b.get("block_id") == item_id), None)
        item_ids.append(_artifact_block_id(matched_block, duplicate_ids) if matched_block is not None else item_id)

    heading_id = _obj_get(anchor, "heading_block_id")

    # When anchor doesn't provide item_block_ids, build from region_bus
    # reference_zone_ids and then extend through ordered reference anchors
    # with bounded gap repair instead of greedy continuation.
    if not item_ids and region_ids:
        anchor_ids: set = set()
        for block in blocks:
            if _matches_zone_id(block, region_ids) and _is_reference_anchor(block):
                artifact_id = _artifact_block_id(block, duplicate_ids)
                if artifact_id is not None:
                    anchor_ids.add(artifact_id)
        item_ids = _build_ordered_reference_items(
            blocks, anchor_ids, duplicate_ids, heading_id, region_ids
        )

    if not heading_id and region_ids:
        for block in blocks:
            if _matches_zone_id(block, region_ids) and str(block.get("text", "") or "").strip().lower() in {
                "references",
                "bibliography",
            }:
                heading_id = _artifact_block_id(block, duplicate_ids)
                break
    if not heading_id:
        for block in blocks:
            if block.get("seed_role") == "reference_heading":
                heading_id = _artifact_block_id(block, duplicate_ids)
                break

    # Avoid including the heading block among items when fallback extraction
    # matched all region blocks (both heading and items).
    if heading_id is not None and heading_id in item_ids:
        item_ids.remove(heading_id)

    # Extend reference items through ordered reference-anchor sequence
    # with bounded gap repair, not greedy continuation.
    if item_ids:
        item_ids = _build_ordered_reference_items(
            blocks, set(item_ids), duplicate_ids, heading_id, region_ids
        )

    zone = {
        "heading_block_id": heading_id,
        "item_block_ids": item_ids,
        "status": "ACCEPT" if heading_id and item_ids else "HOLD",
        "evidence": ["reference zone from anchor, region bus, tail boundary, and numbering continuity"],
    }
    if zone.get("status") == "HOLD":
        zone["item_block_ids"] = []
        zone["heading_block_id"] = None
    return zone


def compute_role_gate_health(decisions: list[VerifiedRoleDecision]) -> dict:
    corrected = sum(1 for d in decisions if d.seed_role in VERIFY_REQUIRED and d.status != "ACCEPT")
    final_unverified = sum(1 for d in decisions if d.role in VERIFY_REQUIRED and d.status != "ACCEPT")
    passthrough = sum(1 for d in decisions if d.role in VERIFY_REQUIRED and d.source == "non_structural_seed")
    abstract_outside = sum(1 for d in decisions if d.seed_role == "abstract_body" and d.role != "abstract_body")
    reference_outside = sum(1 for d in decisions if d.seed_role == "reference_item" and d.role != "reference_item")
    status = "degraded" if final_unverified > 0 or passthrough > 0 else "healthy"
    return {
        "status": status,
        "corrected_structural_seed_count": corrected,
        "held_structural_seed_count": corrected,
        "final_unverified_structural_role_count": final_unverified,
        "seed_role_passthrough_count": passthrough,
        "abstract_body_outside_span_count": abstract_outside,
        "reference_item_outside_reference_zone_count": reference_outside,
    }
