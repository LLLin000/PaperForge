from __future__ import annotations

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


def _bid(block: dict) -> str | int | None:
    return block.get("block_id")


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

    if current_role not in {"", "unassigned"} and current_role not in VERIFY_REQUIRED:
        return accept_role(
            current_role,
            seed_role,
            "non_structural_normalized_role",
            ["pre-gate normalized non-structural role preserved"],
        )

    if proposal == "paper_title" or seed_role == "paper_title":
        if block_id in context.source_frontmatter_anchor_ids.get("title", set()):
            return accept_role("paper_title", seed_role, "source_frontmatter_title_anchor", ["matched source title anchor"])
        return hold_role(seed_role, "paper title seed lacks source-backed title anchor")
    if proposal == "authors" or seed_role == "authors":
        if block_id in context.source_frontmatter_anchor_ids.get("authors", set()):
            return accept_role("authors", seed_role, "source_frontmatter_authors_anchor", ["matched source authors anchor"])
        return hold_role(seed_role, "authors seed lacks source-backed authors anchor")
    if proposal == "keywords" or seed_role == "keywords":
        if block_id in set((context.abstract_span or {}).get("keyword_block_ids", [])):
            return accept_role("keywords", seed_role, "abstract_span_keyword_boundary", ["keywords follow accepted abstract span"])
        return hold_role(seed_role, "keywords seed lacks abstract-span keyword boundary")

    if proposal in VERIFY_REQUIRED or seed_role in VERIFY_REQUIRED:
        return hold_role(seed_role, f"{proposal} requires structural verifier")
    source = "non_structural_seed" if current_role in {"", "unassigned"} else "non_structural_normalized_role"
    return accept_role(proposal, seed_role, source, ["non-structural role accepted"])


def build_document_abstract_span(blocks: list[dict], context: dict) -> dict:
    support_ids = set(context.get("frontmatter_support_zone_ids", set()))
    support_ids |= set(context.get("publisher_sidebar_zone_ids", set()))
    support_ids |= set(context.get("correspondence_zone_ids", set()))
    support_ids |= set(context.get("affiliation_zone_ids", set()))
    main_ids = set(context.get("frontmatter_main_zone_ids", set()))
    body_start_id = context.get("body_start_block_id")
    heading_index = next(
        (idx for idx, block in enumerate(blocks) if block.get("seed_role") == "abstract_heading" or str(block.get("text", "")).strip().lower() == "abstract"),
        None,
    )
    if heading_index is None:
        return {"heading_block_id": None, "body_block_ids": [], "excluded_support_block_ids": [], "status": "MISSING", "stop_reason": "missing_heading", "confidence": 0.0}
    body_ids: list = []
    excluded: list = []
    stop_reason = "document_end"
    accepted_inside_abstract = {"abstract_body", "body_paragraph", "section_heading", "subsection_heading"}
    for block in blocks[heading_index + 1 :]:
        block_id = block.get("block_id")
        if block_id == body_start_id:
            stop_reason = "body_start"
            break
        text = str(block.get("text", "") or "").strip().lower()
        intro_text = text.lstrip("0123456789. ")
        if block.get("seed_role") in {"section_heading", "subsection_heading"} and intro_text.startswith("introduction"):
            stop_reason = "intro_like_heading"
            break
        if text.startswith(("keywords", "key words")):
            stop_reason = "keywords"
            break
        if block_id in support_ids:
            excluded.append(block_id)
            continue
        if main_ids and block_id not in main_ids:
            continue
        if block.get("seed_role") in accepted_inside_abstract:
            body_ids.append(block_id)
    return {
        "heading_block_id": blocks[heading_index].get("block_id"),
        "body_block_ids": body_ids,
        "excluded_support_block_ids": excluded,
        "status": "ACCEPT" if body_ids else "HOLD",
        "stop_reason": stop_reason,
        "confidence": 0.9 if body_ids else 0.2,
    }


def build_verified_reference_zone_from_artifacts(blocks: list[dict], artifacts: dict) -> dict:
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
    accepted_numbering_ids = set(_obj_get(numbering, "accepted_item_ids", set()))
    end_before = _obj_get(tail_spread, "reference_end_before_block_id")
    before_tail = set()
    if end_before:
        for block in blocks:
            block_id = block.get("block_id")
            if block_id == end_before:
                break
            before_tail.add(block_id)
    item_ids = []
    for item_id in _obj_get(anchor, "item_block_ids", []):
        if region_ids and item_id not in region_ids:
            continue
        if before_tail and item_id not in before_tail:
            continue
        if accepted_numbering_ids and item_id not in accepted_numbering_ids:
            continue
        item_ids.append(item_id)
    heading_id = _obj_get(anchor, "heading_block_id")
    return {
        "heading_block_id": heading_id,
        "item_block_ids": item_ids,
        "status": "ACCEPT" if heading_id and item_ids else "HOLD",
        "evidence": ["reference zone from anchor, region bus, tail boundary, and numbering continuity"],
    }
