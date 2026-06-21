from __future__ import annotations

import re

_FIGURE_NUMBER = re.compile(r"\b(?:fig(?:ure)?\.?|extended data fig(?:ure)?\.?|supplementary fig(?:ure)?\.?)\s*\d+", re.I)


def _bbox_x_overlap_ratio(a: list[float], b: list[float]) -> float:
    if len(a) < 4 or len(b) < 4:
        return 0.0
    overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    denom = max(1.0, min(a[2] - a[0], b[2] - b[0]))
    return overlap / denom


def score_figure_caption(
    block: dict,
    *,
    nearby_media: bool = False,
    caption_style_match: bool = False,
    body_prose_likelihood: bool = False,
) -> dict:
    text = str(block.get("text", ""))
    score = 0.0
    evidence: list[str] = []
    if _FIGURE_NUMBER.search(text):
        score += 0.4
        evidence.append("figure_number")
    if nearby_media:
        score += 0.3
        evidence.append("nearby_media")
    if caption_style_match:
        score += 0.2
        evidence.append("caption_style")
    if body_prose_likelihood:
        score -= 0.5
        evidence.append("body_prose_likelihood")
    score = max(0.0, min(1.0, score))
    if score >= 0.7:
        decision = "figure_caption"
    elif score >= 0.4:
        decision = "figure_caption_candidate"
    else:
        decision = "rejected"
    return {"score": score, "decision": decision, "evidence": evidence}


def score_table_match(caption: dict, asset: dict, *, is_continuation: bool = False) -> dict:
    caption_bbox = caption.get("bbox") or caption.get("block_bbox") or [0, 0, 0, 0]
    asset_bbox = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
    score = 0.0
    evidence: list[str] = []
    caption_page = caption.get("page")
    asset_page = asset.get("page")
    same_page = caption_page == asset_page
    if same_page:
        score += 0.35
        evidence.append("same_page")
    elif asset_page is not None and caption_page is not None and asset_page == caption_page - 1:
        score += 0.2
        evidence.append("previous_page")
    if _bbox_x_overlap_ratio(caption_bbox, asset_bbox) >= 0.5:
        score += 0.25
        evidence.append("x_overlap")
    if len(caption_bbox) >= 4 and len(asset_bbox) >= 4:
        if same_page and asset_bbox[1] >= caption_bbox[3]:
            score += 0.25
            evidence.append("asset_below_caption")
        elif asset_page is not None and caption_page is not None and asset_page == caption_page - 1:
            caption_top = caption_bbox[1]
            asset_bottom = asset_bbox[3]
            if caption_top <= 160:
                score += 0.1
                evidence.append("caption_near_top")
            if asset_bottom >= 900:
                score += 0.1
                evidence.append("asset_near_previous_page_bottom")
    if is_continuation and same_page:
        score += 0.15
        evidence.append("continuation_same_page")
    score = max(0.0, min(1.0, score))
    if is_continuation and score >= 0.6:
        decision = "continuation"
    elif score >= 0.6:
        decision = "matched"
    else:
        decision = "ambiguous"
    return {"score": score, "matched_asset_id": asset.get("block_id", ""), "decision": decision, "evidence": evidence}


def score_figure_match(
    legend: dict,
    asset: dict,
    *,
    caption_score: dict | None = None,
    anchor_supported: bool = False,
    caption_text_supported: bool = False,
    family_supported: bool = False,
    zone_supported: bool = False,
) -> dict:
    legend_bbox = legend.get("bbox") or legend.get("block_bbox") or [0, 0, 0, 0]
    asset_bbox = asset.get("bbox") or asset.get("block_bbox") or [0, 0, 0, 0]
    score = 0.0
    evidence: list[str] = []
    has_x_overlap = False

    caption_value = float((caption_score or {}).get("score", 0.0))
    if caption_value < 0.4:
        evidence.append("low_caption_score")
        return {"score": caption_value, "matched_asset_id": asset.get("block_id", ""), "decision": "rejected", "evidence": evidence}

    if legend.get("page") == asset.get("page"):
        score += 0.3
        evidence.append("same_page")
    if _bbox_x_overlap_ratio(legend_bbox, asset_bbox) >= 0.4:
        has_x_overlap = True
        score += 0.25
        evidence.append("x_overlap")
    elif len(legend_bbox) >= 4 and len(asset_bbox) >= 4:
        # Side-by-side: no x_overlap but adjacent columns with shared y-band
        gap = max(0.0, asset_bbox[0] - legend_bbox[2], legend_bbox[0] - asset_bbox[2])
        narrow_w = min(legend_bbox[2] - legend_bbox[0], asset_bbox[2] - asset_bbox[0])
        if gap < narrow_w * 0.3 and gap < 80:
            has_x_overlap = True
            score += 0.20
            evidence.append("adjacent_x")
    if len(legend_bbox) >= 4 and len(asset_bbox) >= 4:
        vertical_gap = min(abs(legend_bbox[1] - asset_bbox[3]), abs(asset_bbox[1] - legend_bbox[3]))
        if vertical_gap <= 300:
            score += 0.2
            evidence.append("nearby_y")
        if asset_bbox[3] <= legend_bbox[1] or asset_bbox[1] >= legend_bbox[3]:
            score += 0.1
            evidence.append("caption_above_or_below")
    score += min(0.15, caption_value * 0.15)
    score = max(0.0, min(1.0, score))
    if anchor_supported:
        score += 0.05
        evidence.append("anchor_supported")
    if caption_text_supported:
        score += 0.05
        evidence.append("caption_text_supported")
    if family_supported:
        score += 0.03
        evidence.append("family_supported")
    if zone_supported:
        score += 0.02
        evidence.append("zone_supported")
    score = max(0.0, min(1.0, score))
    strong_geometry = "same_page" in evidence and "nearby_y" in evidence and "caption_above_or_below" in evidence
    contextual_support = anchor_supported or family_supported or zone_supported
    if score >= 0.6 and (has_x_overlap or (strong_geometry and (contextual_support or caption_text_supported))):
        decision = "matched"
    elif score >= 0.4:
        decision = "ambiguous"
    else:
        decision = "rejected"
    return {"score": score, "matched_asset_id": asset.get("block_id", ""), "decision": decision, "evidence": evidence}


def score_structured_insert(
    block: dict,
    *,
    body_spine_match: bool = False,
    cluster_coherent: bool = False,
) -> dict:
    text = str(block.get("text") or block.get("block_content") or "").strip().lower()
    bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
    page_width = float(block.get("page_width") or 1200)
    score = 0.0
    evidence: list[str] = []

    if block.get("_in_visual_container"):
        score += 0.3
        evidence.append("visual_container")
    if re.match(r"^box\s*\.?\s*\d+\b", text) or "key point" in text or text.startswith("highlights") or text.startswith("sections"):
        score += 0.3
        evidence.append("box_or_summary_keyword")
    if len(bbox) >= 4 and (bbox[2] - bbox[0]) < page_width * 0.45:
        score += 0.15
        evidence.append("narrow_width")
    if cluster_coherent:
        score += 0.15
        evidence.append("cluster_coherent")
    if body_spine_match:
        score -= 0.25
        evidence.append("body_spine_match")

    score = max(0.0, min(1.0, score))
    if score >= 0.7:
        decision = "structured_insert"
    elif score >= 0.4:
        decision = "structured_insert_candidate"
    else:
        decision = "body"
    return {"score": score, "decision": decision, "evidence": evidence}


def score_tail_boundary(
    *,
    forward_body_end: int | None,
    backward_backmatter_start: int | None,
    references_start: dict | None = None,
) -> dict:
    score = 0.0
    reason: list[str] = []
    if forward_body_end is not None and backward_backmatter_start is not None:
        if forward_body_end < backward_backmatter_start:
            score += 0.4
            reason.append("forward_backward_order")
        if backward_backmatter_start - forward_body_end <= 2:
            score += 0.2
            reason.append("adjacent_tail_boundary")
    ref_page = references_start.get("page") if references_start else None
    if ref_page is not None and forward_body_end is not None and ref_page >= forward_body_end:
        score += 0.3
        reason.append("references_after_body")
    score = max(0.0, min(1.0, score))
    return {
        "score": score,
        "body_end_page": forward_body_end or 0,
        "backmatter_start": {"page": backward_backmatter_start} if backward_backmatter_start else {},
        "references_start": references_start or {},
        "reason": reason,
    }
