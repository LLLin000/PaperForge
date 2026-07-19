"""OCR object writeback module — post-inventory figure/table ownership claims.

Centralises role writeback, ownership evidence, contained-text tagging, and
object-adjacent text claims that were previously scattered across ocr.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from paperforge.worker.ocr_figures import (
    attach_ownership_conflicts,
    tag_figure_contained_text,
)

PROTECTED_ROLES = frozenset({
    "reference_item",
    "reference_heading",
    "section_heading",
    "paper_title",
    "authors",
    "author_bio",
    "footnote",
    "table_cell",
    "table_caption",
    "figure_caption",
})

@dataclass(frozen=True)
class ObjectOwnershipClaim:
    owner_family: str
    owner_id: str
    owner_role: str
    association_reason: str
    confidence: float
    source_phase: str
    source_block_ids: tuple[str, ...]


@dataclass
class ObjectWritebackReport:
    claims: list[dict]
    applied: list[dict]
    skipped: list[dict]
    conflicts: list[dict]
    consumed_block_ids: dict[str, list[str]]



def _mark_owned(block: dict, *, family: str, owner_id: str, owner_role: str, reason: str) -> None:
    """Stamp ownership-evidence contract onto a structured block."""
    block["_object_owner_family"] = family
    block["_object_owner_id"] = owner_id
    block["_object_owner_role"] = owner_role
    block["_object_association_reason"] = reason
    block["_object_writeback_phase"] = "post_inventory"
    block["_object_consumed"] = True

def _score_side_adjacent_text_claim(block: dict, figure: dict) -> float:
    """Score whether a text block is a side-adjacent figure note.

    Returns confidence in [0, 1]. Threshold 0.9 is applied by caller.
    """
    bbox = block.get("bbox") or [0, 0, 0, 0]
    figure_bbox = figure.get("cluster_bbox") or figure.get("asset_bbox")
    if not figure_bbox or len(figure_bbox) < 4:
        # Fallback: union bbox from matched_assets
        assets = figure.get("matched_assets") or []
        xs, ys = [], []
        for a in assets:
            ab = a.get("bbox") or [0, 0, 0, 0]
            if len(ab) >= 4:
                xs.extend([ab[0], ab[2]])
                ys.extend([ab[1], ab[3]])
        figure_bbox = [min(xs), min(ys), max(xs), max(ys)] if xs else [0, 0, 0, 0]
    if len(bbox) < 4 or len(figure_bbox) < 4:
        return 0.0
    same_page = int(block.get("page", 0) or 0) == int(figure.get("page", 0) or 0)
    if not same_page:
        return 0.0
    y_overlap = max(0, min(bbox[3], figure_bbox[3]) - max(bbox[1], figure_bbox[1]))
    horizontal_gap = min(abs(figure_bbox[0] - bbox[2]), abs(bbox[0] - figure_bbox[2]))
    if y_overlap <= 0 or horizontal_gap > 40:
        return 0.0
    role = str(block.get("role") or "")
    if role in PROTECTED_ROLES:
        return 0.0
    raw_label = str(block.get("raw_label") or "")
    if raw_label != "text":
        return 0.0
    text = str(block.get("text") or "").strip()
    if not text or len(text.split()) > 80:
        return 0.0
    return 0.92

def apply_object_writebacks(
    *, structured_blocks: list[dict], figure_inventory: dict, table_inventory: dict
) -> dict:
    """Apply all post-inventory object writebacks to structured blocks.

    Emits ownership-claim evidence, tracks consumed block ids for renderer
    skip, and is idempotent via the ``_object_writeback_phase`` guard.

    Returns a dict matching ObjectWritebackReport shape for backward compat.
    """
    claims: list[dict] = []
    applied: list[dict] = []
    skipped: list[dict] = []
    consumed_block_ids: dict[str, list[str]] = {}

    block_by_page_and_id: dict[tuple[int, str], dict] = {}
    for b in structured_blocks:
        bid = b.get("block_id")
        page = b.get("page", 0) or 0
        if bid is not None:
            block_by_page_and_id[(int(page), str(bid))] = b

    # --- Figure asset writeback ---
    for fig in figure_inventory.get("matched_figures", []):
        figure_id = str(fig.get("figure_id", ""))
        fig_consumed: list[str] = []
        for asset in fig.get("matched_assets", []):
            asset_bid = str(asset.get("block_id", ""))
            fig_page = int(fig.get("page", 0) or 0)
            block = block_by_page_and_id.get((fig_page, asset_bid))
            if block is None:
                continue
            # Idempotency guard
            if block.get("_object_writeback_phase"):
                continue
            block["role"] = "figure_asset"
            _mark_owned(block, family="figure", owner_id=figure_id, owner_role="asset", reason="matched_asset")
            claim = ObjectOwnershipClaim(
                owner_family="figure",
                owner_id=figure_id,
                owner_role="asset",
                association_reason="matched_asset",
                confidence=1.0,
                source_phase="post_inventory",
                source_block_ids=(asset_bid,),
            )
            claims.append({
                "owner_family": claim.owner_family,
                "owner_id": claim.owner_id,
                "owner_role": claim.owner_role,
                "association_reason": claim.association_reason,
                "confidence": claim.confidence,
                "source_phase": claim.source_phase,
                "source_block_ids": list(claim.source_block_ids),
            })
            applied.append({"block_id": asset_bid, "role": "figure_asset"})
            fig_consumed.append(asset_bid)
        if fig_consumed:
            fig.setdefault("consumed_block_ids", []).extend(fig_consumed)
            consumed_block_ids.setdefault(figure_id, []).extend(fig_consumed)

    # --- Table asset writeback ---
    for tbl in table_inventory.get("tables", []):
        table_id = str(tbl.get("table_id", ""))
        tbl_consumed: list[str] = []
        asset_bid = str(tbl.get("asset_block_id", ""))
        tbl_page = int(tbl.get("page", 0) or 0)
        block = block_by_page_and_id.get((tbl_page, asset_bid))
        if block is not None and not block.get("_object_writeback_phase"):
            block["role"] = "table_html"
            _mark_owned(block, family="table", owner_id=table_id, owner_role="asset", reason="matched_asset")
            claim = ObjectOwnershipClaim(
                owner_family="table",
                owner_id=table_id,
                owner_role="asset",
                association_reason="matched_asset",
                confidence=1.0,
                source_phase="post_inventory",
                source_block_ids=(asset_bid,),
            )
            claims.append({
                "owner_family": claim.owner_family,
                "owner_id": claim.owner_id,
                "owner_role": claim.owner_role,
                "association_reason": claim.association_reason,
                "confidence": claim.confidence,
                "source_phase": claim.source_phase,
                "source_block_ids": list(claim.source_block_ids),
            })
            applied.append({"block_id": asset_bid, "role": "table_html"})
            tbl_consumed.append(asset_bid)
        if tbl_consumed:
            tbl.setdefault("consumed_block_ids", []).extend(tbl_consumed)
            consumed_block_ids.setdefault(table_id, []).extend(tbl_consumed)

    # --- Ownership conflicts (bridging) ---
    attach_ownership_conflicts(figure_inventory, table_inventory)

    # --- Contained text tagging (bridging) ---
    tag_figure_contained_text(structured_blocks, figure_inventory.get("matched_figures", []))

    # --- Contained figure text — route through ownership evidence ---
    for fig in figure_inventory.get("matched_figures", []):
        figure_id = str(fig.get("figure_id", ""))
        fig_page = int(fig.get("page", 0) or 0)
        region = fig.get("cluster_bbox")
        if not region or len(region) < 4:
            # Fallback: union bbox from matched_assets
            assets = fig.get("matched_assets", [])
            bboxes = [
                a.get("bbox", [0, 0, 0, 0])
                for a in assets
                if len(a.get("bbox") or []) >= 4
            ]
            if bboxes:
                region = [min(b[0] for b in bboxes), min(b[1] for b in bboxes),
                          max(b[2] for b in bboxes), max(b[3] for b in bboxes)]
        if not region or len(region) < 4:
            continue
        for block in structured_blocks:
            if block.get("_object_writeback_phase"):
                continue
            if not block.get("_figure_contained"):
                continue
            bid = block.get("block_id")
            if bid is None:
                continue
            block_page = int(block.get("page", 0) or 0)
            if block_page != fig_page:
                continue
            # Check if this block is within this figure's region
            bbox = block.get("bbox") or [0, 0, 0, 0]
            if len(bbox) < 4:
                continue
            fx1, fy1, fx2, fy2 = region[:4]
            bx1, by1, bx2, by2 = bbox[:4]
            if not (bx1 >= fx1 and by1 >= fy1 and bx2 <= fx2 and by2 <= fy2):
                continue
            # Assign ownership
            block["role"] = "figure_inner_text"
            _mark_owned(
                block,
                family="figure",
                owner_id=figure_id,
                owner_role="inner_text",
                reason="contained",
            )
            bid_str = str(bid)
            fig.setdefault("consumed_block_ids", []).append(bid_str)
            fig.setdefault("associated_text_block_ids", []).append(bid_str)
            consumed_block_ids.setdefault(figure_id, []).append(bid_str)
            claim = ObjectOwnershipClaim(
                owner_family="figure",
                owner_id=figure_id,
                owner_role="inner_text",
                association_reason="contained",
                confidence=0.8,
                source_phase="post_inventory",
                source_block_ids=(bid_str,),
            )
            claims.append({
                "owner_family": claim.owner_family,
                "owner_id": claim.owner_id,
                "owner_role": claim.owner_role,
                "association_reason": claim.association_reason,
                "confidence": claim.confidence,
                "source_phase": claim.source_phase,
                "source_block_ids": list(claim.source_block_ids),
            })
            applied.append({"block_id": bid_str, "role": "figure_inner_text"})

    # --- Side-adjacent figure text claims ---
    for fig in figure_inventory.get("matched_figures", []):
        figure_id = str(fig.get("figure_id", ""))
        for block in structured_blocks:
            bid = block.get("block_id")
            if bid is None:
                continue
            # Skip already-owned blocks
            if block.get("_object_writeback_phase"):
                continue
            score = _score_side_adjacent_text_claim(block, fig)
            if score >= 0.9:
                block["role"] = "figure_inner_text"
                _mark_owned(
                    block,
                    family="figure",
                    owner_id=figure_id,
                    owner_role="inner_text",
                    reason="side_adjacent",
                )
                block["_object_association_reason"] = "side_adjacent"
                bid_str = str(bid)
                fig.setdefault("associated_text_block_ids", []).append(bid_str)
                if bid_str not in fig.setdefault("consumed_block_ids", []):
                    fig["consumed_block_ids"].append(bid_str)
                consumed_block_ids.setdefault(figure_id, []).append(bid_str)
                claim = ObjectOwnershipClaim(
                    owner_family="figure",
                    owner_id=figure_id,
                    owner_role="inner_text",
                    association_reason="side_adjacent",
                    confidence=score,
                    source_phase="post_inventory",
                    source_block_ids=(bid_str,),
                )
                claims.append({
                    "owner_family": claim.owner_family,
                    "owner_id": claim.owner_id,
                    "owner_role": claim.owner_role,
                    "association_reason": claim.association_reason,
                    "confidence": claim.confidence,
                    "source_phase": claim.source_phase,
                    "source_block_ids": list(claim.source_block_ids),
                })
                applied.append({"block_id": bid_str, "role": "figure_inner_text"})
            elif score > 0:
                skipped.append({"block_id": str(bid), "score": score, "reason": "below_threshold"})

    # --- Legacy bridging: write_back_figure_roles already handled inline above ---
    # --- Legacy bridging: write_back_table_roles already handled inline above ---

    # --- Aggregate any previously-consumed block ids from inventory ---
    # Ensures idempotent calls still report the full consumed state.
    for fig in figure_inventory.get("matched_figures", []):
        fid = str(fig.get("figure_id", ""))
        for cb in fig.get("consumed_block_ids", []):
            if cb not in consumed_block_ids.get(fid, []):
                consumed_block_ids.setdefault(fid, []).append(cb)
    for tbl in table_inventory.get("tables", []):
        tid = str(tbl.get("table_id", ""))
        for cb in tbl.get("consumed_block_ids", []):
            if cb not in consumed_block_ids.get(tid, []):
                consumed_block_ids.setdefault(tid, []).append(cb)

    return {
        "claims": claims,
        "applied": applied,
        "skipped": skipped,
        "conflicts": figure_inventory.get("ownership_conflicts", []),
        "consumed_block_ids": consumed_block_ids,
        "applied_count": len(applied),
    }
