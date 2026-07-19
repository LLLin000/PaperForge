from __future__ import annotations

import re

from paperforge.worker.ocr_decisions import record_decision
from paperforge.worker.ocr_roles import _BACKMATTER_TITLE_DENY_LIST

from dataclasses import dataclass, field


@dataclass
class TailSettlementReport:
    promoted_backmatter_heading_ids: list[str] = field(default_factory=list)
    converted_to_backmatter_body_ids: list[str] = field(default_factory=list)
    restored_body_paragraph_ids: list[str] = field(default_factory=list)

    @property
    def applied_count(self) -> int:
        return (
            len(self.promoted_backmatter_heading_ids)
            + len(self.converted_to_backmatter_body_ids)
            + len(self.restored_body_paragraph_ids)
        )

_BACKMATTER_BODY_SIGNALS = re.compile(
    r"\b(?:declare|conflict|interest|funding|support|grant|author|contribut|"
    r"acknowledge|thank|ethic|review|approv|consent|availab|data|material|"
    r"competing|financial|disclos|report|none|no conflict|nothing to declare)\b",
    re.IGNORECASE,
)


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _next_nonempty_block_same_page(blocks: list[dict], idx: int) -> dict | None:
    """Return the next non-empty block on the same page after idx, or None."""
    page = blocks[idx].get("page")
    if page is None:
        return None
    for j in range(idx + 1, len(blocks)):
        if blocks[j].get("page") != page:
            return None
        text = _block_text(blocks[j]).strip()
        if text:
            return blocks[j]
    return None


def _canonical_section_text(block: dict) -> str:
    text = _block_text(block).strip().lower()
    if re.match(r"^(?:\w\s)+\w$", text):
        text = re.sub(r"\s+", "", text)
    return text


def _looks_like_tail_body(block: dict) -> bool:
    """Return True if the block looks like short backmatter body text.

    Heuristics: short paragraphs with backmatter-related vocabulary,
    no section-heading formatting, and a word count below the body spine
    threshold.
    """
    text = _block_text(block).strip()
    if not text:
        return False
    words = text.split()
    if len(words) > 80:
        return False
    role = block.get("role", "")
    if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
        return False
    if _BACKMATTER_BODY_SIGNALS.search(text):
        return True
    return False


def _looks_like_backmatter_body_text(text: str) -> bool:
    lower = text.lower()
    markers = (
        "conflict of interest",
        "declaration",
        "publisher",
        "author contributions",
        "funding",
        "acknowledg",
        "data availability",
        "supplement",
        "ethics",
        "copyright",
    )
    return any(marker in lower for marker in markers)


def promote_backmatter_heading_candidates(blocks: list[dict], report: TailSettlementReport | None = None) -> None:
    """Promote backmatter heading candidates that are followed by tail-like body on the same page."""
    for idx, block in enumerate(blocks):
        is_candidate = (
            block.get("role") == "backmatter_heading_candidate"
            or block.get("seed_role") == "backmatter_heading_candidate"
        )
        if not is_candidate:
            continue
        if block.get("role") == "backmatter_heading":
            continue
        next_body = _next_nonempty_block_same_page(blocks, idx)
        if next_body and next_body.get("role") in {"body_paragraph", "backmatter_body"}:
            if _looks_like_tail_body(next_body):
                old_role = block.get("role")
                block["role"] = "backmatter_heading"
                block.setdefault("role_confidence", 0.6)
                if old_role != block["role"]:
                    record_decision(
                        block,
                        stage="backmatter_candidate_promotion",
                        old_role=old_role,
                        new_role=block["role"],
                        reason="backmatter heading candidate promoted: followed by tail-like body on same page",
                    )
                if report is not None:
                    block_id = str(block.get("block_id") or "")
                    if block_id:
                        report.promoted_backmatter_heading_ids.append(block_id)
                # Convert follower body paragraphs to backmatter_body
                for j in range(idx + 1, len(blocks)):
                    if blocks[j].get("page") != block.get("page"):
                        break
                    if blocks[j].get("role") == "body_paragraph":
                        old_follower_role = blocks[j].get("role")
                        blocks[j]["role"] = "backmatter_body"
                        blocks[j].setdefault("role_confidence", 0.6)
                        if old_follower_role != blocks[j]["role"]:
                            record_decision(
                                blocks[j],
                                stage="backmatter_candidate_promotion",
                                old_role=old_follower_role,
                                new_role=blocks[j]["role"],
                                reason="follower body converted to backmatter_body under confirmed heading",
                            )
                        if report is not None:
                            follower_id = str(blocks[j].get("block_id") or "")
                            if follower_id:
                                report.converted_to_backmatter_body_ids.append(follower_id)
                break  # only promote one candidate per pass


def exclude_tail_nonref_from_body_flow(blocks: list[dict], report: TailSettlementReport | None = None) -> None:
    for i, block in enumerate(blocks):
        effective_role = block.get("role")
        if effective_role == "unassigned":
            effective_role = block.get("seed_role")
        if effective_role != "body_paragraph":
            continue
        if block.get("zone") != "tail_nonref_hold_zone":
            continue

        # Only convert blocks that carry explicit backmatter evidence;
        # preserve ordinary body continuation or body-like prose.
        text = str(block.get("text") or block.get("block_content") or "")
        if not _looks_like_backmatter_body_text(text):
            continue

        old_role = block.get("role")
        block["role"] = "backmatter_body"
        if block.get("seed_role") == "body_paragraph":
            block["seed_role"] = "backmatter_body"
        if old_role != block["role"]:
            record_decision(
                block,
                stage="tail_nonref_exclusion",
                old_role=old_role,
                new_role=block["role"],
                reason="tail non-reference body block excluded from body flow",
            )
        if report is not None:
            block_id = str(block.get("block_id") or "")
            if block_id:
                report.converted_to_backmatter_body_ids.append(block_id)
        block.setdefault("evidence", []).append("tail_nonref_hold_zone excluded from body flow")


def restore_numbered_body_from_tail_hold(blocks: list[dict], report: TailSettlementReport | None = None) -> None:
    active_numbered_body = False
    for block in blocks:
        role = block.get("role")
        text = _canonical_section_text(block)
        marker_type = str(((block.get("marker_signature") or {}).get("type")) or "none")

        if role in {"reference_heading", "backmatter_heading", "backmatter_boundary_heading"}:
            active_numbered_body = False
            continue

        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            active_numbered_body = (
                (
                    marker_type
                    in {"heading_numbered", "heading_arabic", "heading_decimal", "heading_roman", "heading_alpha"}
                    or (
                        block.get("zone") == "tail_nonref_hold_zone"
                        and str(block.get("style_family") or "") == "heading_like"
                    )
                )
                and text not in _BACKMATTER_TITLE_DENY_LIST
            )
            continue

        if role == "backmatter_body" and active_numbered_body:
            block["role"] = "body_paragraph"
            if report is not None:
                block_id = str(block.get("block_id") or "")
                if block_id:
                    report.restored_body_paragraph_ids.append(block_id)


def settle_tail_and_backmatter(
    *,
    structured_blocks: list[dict],
    document_structure: object | None = None,
) -> TailSettlementReport:
    """Run tail settlement: exclude non-reference backmatter from body flow,
    then restore numbered body paragraphs that were incorrectly held as backmatter.

    Returns a TailSettlementReport with accumulated operation counts/ids.
    """
    report = (
        getattr(document_structure, "tail_settlement_report", None)
        if document_structure is not None
        else None
    )
    if report is None:
        report = TailSettlementReport()
        if document_structure is not None:
            document_structure.tail_settlement_report = report
    exclude_tail_nonref_from_body_flow(structured_blocks, report=report)
    restore_numbered_body_from_tail_hold(structured_blocks, report=report)
    return report
