from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json
from paperforge.worker.ocr_scores import score_table_match

_TABLE_NUM_TOKEN = r"(?:[A-Z]\d+(?:\.\d+)?|\d+(?:\.\d+)?|[IVXLCDM]+)"

_TABLE_PREFIX_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table|表|(?:\ufffc|\ufffd\ufffd))\s*"
    rf"(?:S\.?\s*)?({_TABLE_NUM_TOKEN})\b",
    flags=re.IGNORECASE,
)

_CONTINUATION_PATTERN = re.compile(r"\(cont(?:inued)?\.?\)", re.IGNORECASE)
_TRUNCATED_TABLE_ONLY_PATTERN = re.compile(
    rf"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table|表|(?:\ufffc|\ufffd\ufffd))\s*"
    rf"(?:S\.?\s*)?{_TABLE_NUM_TOKEN}\.?"
    rf"(?:\s*\(cont(?:inued)?\.?\))?$",
    re.IGNORECASE,
)


def _match_role(block: dict) -> str:
    """Resolve the role to use for matching: role_candidate > role > seed_role."""
    return str(block.get("role_candidate") or block.get("role") or block.get("seed_role") or "")


def _roman_to_int(roman: str) -> int | None:
    roman_values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    s = roman.strip().upper()
    if not re.fullmatch(r"[IVXLCDM]+", s):
        return None
    total = 0
    prev = 0
    for c in reversed(s):
        val = roman_values.get(c, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total


def _table_has_rotated_content(asset: dict) -> int:
    """Check if a table asset has rotated text content.
    Returns rotation_deg (270) to correct, or 0 if not rotated.
    """
    if not asset:
        return 0
    span = asset.get("span_metadata") or []
    if isinstance(span, dict):
        span = [span]
    if not isinstance(span, list):
        return 0
    for entry in span:
        if not isinstance(entry, dict):
            continue
        d = entry.get("dir")
        if not isinstance(d, (list, tuple)) or len(d) != 2:
            continue
        # dir=[0,-1] → text rotated 90° CW → need 270° to correct
        if abs(float(d[1])) > abs(float(d[0])):
            return 270
    return 0


def _parse_table_number_token(token: str) -> int | None:
    token = token.strip().rstrip(".")
    if re.fullmatch(r"[A-Z]\d+(?:\.\d+)?", token, re.IGNORECASE):
        token = token[1:]
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return int(float(token))
    if re.fullmatch(r"[IVXLCDM]+", token, re.IGNORECASE):
        return _roman_to_int(token)
    return None


def _extract_table_number(text: str) -> int | None:
    m = _TABLE_PREFIX_PATTERN.search(text)
    if not m:
        return None
    return _parse_table_number_token(m.group(1))


def _is_continuation_caption(text: str) -> bool:
    return bool(_CONTINUATION_PATTERN.search(text))


def _extract_base_table_number(text: str) -> int | None:
    cleaned = _CONTINUATION_PATTERN.sub("", text).strip()
    return _extract_table_number(cleaned)


def _is_validation_first_table_candidate(block: dict) -> bool:
    role = _match_role(block)
    if role in {"table_caption", "table_caption_candidate"}:
        return False
    marker_type = (block.get("marker_signature") or {}).get("type") or "none"
    zone = str(block.get("zone", "") or "")
    style_family = str(block.get("style_family", "") or "")
    raw_label = str(block.get("raw_label", "") or "")
    text = str(block.get("text", "") or "")
    if marker_type == "table_number" and zone == "display_zone" and style_family == "table_caption_like":
        return True
    return (
        raw_label == "figure_title" and style_family == "table_caption_like" and _extract_table_number(text) is not None
    )


def _is_insufficient_table_caption_evidence(block: dict) -> bool:
    text = str(block.get("text", "") or "").strip()
    return bool(_TRUNCATED_TABLE_ONLY_PATTERN.fullmatch(text))


def _is_weak_explicit_table_caption(block: dict) -> bool:
    role = _match_role(block)
    if role in {"table_caption", "table_caption_candidate"}:
        return _is_insufficient_table_caption_evidence(block)
    return _is_validation_first_table_candidate(block) and _is_insufficient_table_caption_evidence(block)


def _find_table_caption_continuation(caption: dict, structured_blocks: list[dict]) -> dict | None:
    """Find the block immediately after a weak-truncated table caption that
    looks like a continuation (stolen as figure_caption or similar)."""
    caption_bbox = caption.get("bbox") or [0, 0, 0, 0]
    caption_page = caption.get("page")
    next_idx = None
    for i, block in enumerate(structured_blocks):
        if block.get("page") == caption_page and block.get("block_id") == caption.get("block_id"):
            next_idx = i + 1
            break
    if next_idx is None or next_idx >= len(structured_blocks):
        return None

    next_block = structured_blocks[next_idx]
    bbox = next_block.get("bbox") or [0, 0, 0, 0]

    # Trigger rules from spec
    if bbox[1] - caption_bbox[3] > 25:  # y-gap > 25px
        return None

    next_text = str(next_block.get("text", "") or "")
    # reject if starts with Fig/Figure/Scheme/Plate
    if next_text.lower().startswith(("fig", "figure", "scheme", "plate")):
        return None
    # reject actual table HTML blocks — these are not text continuations
    if next_text.strip().lower().startswith("<table"):
        return None

    # x-overlap check
    x_overlap = max(0, min(caption_bbox[2], bbox[2]) - max(caption_bbox[0], bbox[0]))
    if x_overlap < min(caption_bbox[2] - caption_bbox[0], bbox[2] - bbox[0]) * 0.5:
        left_edge_delta = abs(caption_bbox[0] - bbox[0])
        if left_edge_delta >= 40:
            return None

    return next_block


def _materialize_table_caption(caption: dict, continuation: dict | None) -> tuple[dict, list[str]]:
    """Merge continuation text into caption, return (merged_caption, consumed_ids)."""
    consumed_ids = [caption.get("block_id", "")]
    if continuation is None:
        return caption, consumed_ids

    merged = dict(caption)
    cont_text = str(continuation.get("text", "") or "").strip()
    marker_match = _TABLE_PREFIX_PATTERN.match(cont_text)
    if marker_match is not None:
        cont_text = cont_text[marker_match.end() :].lstrip(" .:-\n\t")
    merged["text"] = ((merged.get("text", "") or "").strip() + " " + cont_text).strip()
    consumed_ids.append(continuation.get("block_id", ""))
    return merged, consumed_ids


def _has_strong_spatial_evidence_for_bare_table(caption: dict, top_candidate_score: dict | None) -> bool:
    if top_candidate_score is None:
        return False
    if top_candidate_score.get("score", 0.0) < 0.75:
        return False
    evidence = top_candidate_score.get("evidence", [])
    spatial_markers = {"x_overlap", "asset_below_caption", "same_page"}
    return spatial_markers.issubset(set(evidence))


def _bare_table_tie_break(score: dict, caption: dict, asset: dict) -> tuple[float, float, float]:
    cb = caption.get("bbox") or [0, 0, 0, 0]
    ab = asset.get("bbox") or [0, 0, 0, 0]
    x_overlap = min(cb[2], ab[2]) - max(cb[0], ab[0]) if len(cb) >= 4 and len(ab) >= 4 else 0.0
    below_gap = max(0.0, ab[1] - cb[3]) if len(cb) >= 4 and len(ab) >= 4 else 9999.0
    return (float(score.get("score", 0.0)), float(x_overlap), -float(below_gap))


def _score_candidate_assets(
    page_assets: list[tuple[int, dict]],
    caption: dict,
    *,
    is_continuation: bool,
) -> list[tuple[int, dict, dict]]:
    scored = [
        (i, asset, score_table_match(caption, asset, is_continuation=is_continuation)) for i, asset in page_assets
    ]
    scored.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
    return scored


def _collect_page_footnote_prior(structured_blocks: list[dict]) -> dict[int, float]:
    by_page: dict[int, list[float]] = {}
    for block in structured_blocks:
        if not (
            str(block.get("role", "") or "") == "footnote"
            and str(block.get("raw_label", "") or "") == "vision_footnote"
        ):
            continue
        bbox = block.get("bbox") or [0, 0, 0, 0]
        if len(bbox) < 4:
            continue
        page = int(block.get("page", 0) or 0)
        if page:
            by_page.setdefault(page, []).append(float(bbox[1]))
    if not by_page:
        return {}
    all_tops_flat = [t for tops in by_page.values() for t in tops]
    global_min = min(all_tops_flat) if all_tops_flat else 0.0
    result: dict[int, float] = {}
    for page in by_page:
        other_tops = [t for p, tops2 in by_page.items() if p != page for t in tops2]
        result[page] = min(other_tops) if other_tops else global_min
    return result


def _looks_like_body_text_below_table(block: dict, table_bbox: list[float]) -> bool:
    bbox = block.get("bbox") or [0, 0, 0, 0]
    if len(bbox) < 4 or len(table_bbox) < 4:
        return False
    block_width = bbox[2] - bbox[0]
    table_width = table_bbox[2] - table_bbox[0]
    text = str(block.get("text", "") or "").strip()
    return block_width >= table_width * 0.9 and len(text.split()) >= 12


def _table_note_falls_into_page_footnote_prior(
    note_bbox: list[float], page: int, prior_by_page: dict[int, float]
) -> bool:
    if page not in prior_by_page or len(note_bbox) < 4:
        return False
    return float(note_bbox[1]) >= float(prior_by_page[page])


def build_table_inventory(structured_blocks: list[dict]) -> dict[str, Any]:
    return build_table_inventory_vnext(structured_blocks)


def build_table_inventory_legacy(structured_blocks: list[dict]) -> dict[str, Any]:
    tables: list[dict] = []
    captions: list[dict] = []
    assets: list[dict] = []
    held_tables: list[dict] = []
    unmatched_captions: list[dict] = []
    unmatched_assets: list[dict] = []

    for block in structured_blocks:
        role = _match_role(block)
        raw_label = str(block.get("raw_label", "") or "").strip()
        if role in {"table_caption", "table_caption_candidate"} or _is_validation_first_table_candidate(block):
            captions.append(block)
        elif role in ("table_asset", "table_html", "media_asset", "figure_asset"):
            if role == "figure_asset" and raw_label != "table":
                continue
            if role == "media_asset":
                bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
                width = (bbox[2] - bbox[0]) if len(bbox) >= 4 else 0
                height = (bbox[3] - bbox[1]) if len(bbox) >= 4 else 0
                if width < 120 or height < 60:
                    continue
                if raw_label not in ("table", "table_image"):
                    aspect = width / max(height, 1)
                    if aspect < 1.5:
                        continue
            if raw_label in {"table", "table_image"} or role == "table_html":
                block["asset_family_hint"] = "table_like"
                block["asset_family_confidence"] = 0.70
                block["asset_family_evidence"] = [f"raw_label:{raw_label}"]
            else:
                block.setdefault("asset_family_hint", "ambiguous")
                block.setdefault("asset_family_confidence", 0.35)
                block.setdefault("asset_family_evidence", ["no_label_signal"])
            assets.append(block)

    used_asset_indices: set[int] = set()
    page_footnote_prior = _collect_page_footnote_prior(structured_blocks)

    _page_max_y: dict[int, float] = {}
    for block in structured_blocks:
        bbox = block.get("bbox") or [0, 0, 0, 0]
        if len(bbox) >= 4:
            page = int(block.get("page", 0) or 0)
            _page_max_y[page] = max(_page_max_y.get(page, 0.0), float(bbox[3]))

    for caption in captions:
        caption_page = caption.get("page", 0)
        caption_text = caption.get("text", "")
        table_num = _extract_table_number(caption_text)
        formal_table_number = _extract_base_table_number(caption_text)
        is_cont = _is_continuation_caption(caption_text)
        is_validation_first_candidate = _is_validation_first_table_candidate(caption)
        is_weak_truncated = _is_insufficient_table_caption_evidence(caption)
        is_weak_explicit_caption = _is_weak_explicit_table_caption(caption)

        if is_validation_first_candidate and is_weak_truncated:
            # Check if same-page table assets exist before holding.
            same_page_assets = [
                a for i, a in enumerate(assets) if i not in used_asset_indices and a.get("page", 0) == caption_page
            ]
            if not same_page_assets:
                held_tables.append(
                    {
                        "table_id": f"held_table_{len(held_tables) + 1:03d}",
                        "caption_block_id": caption.get("block_id", ""),
                        "page": caption_page,
                        "caption_text": caption_text,
                        "table_number": table_num,
                        "formal_table_number": formal_table_number,
                        "hold_reason": "insufficient_caption_evidence",
                        "zone": caption.get("zone", ""),
                        "style_family": caption.get("style_family", ""),
                        "marker_signature": caption.get("marker_signature", {}),
                    }
                )
                continue
            # same-page asset exists → fall through into weak-explicit matching
        continuation_ids: list[str] = []
        if is_weak_truncated:
            continuation = _find_table_caption_continuation(caption, structured_blocks)
            materialized_caption, continuation_ids = _materialize_table_caption(caption, continuation)
            caption_text = materialized_caption.get("text", "")
        all_candidates: list[tuple[int, dict, dict]] = []

        if is_weak_explicit_caption:
            candidate_pages = [caption_page - 1, caption_page, caption_page + 1]
            pre_candidates: list[tuple[int, dict, dict]] = []
            for page in candidate_pages:
                if page < 1:
                    continue
                page_assets_list = [
                    (i, asset)
                    for i, asset in enumerate(assets)
                    if i not in used_asset_indices and asset.get("page", 0) == page
                ]
                pre_candidates.extend(_score_candidate_assets(page_assets_list, caption, is_continuation=is_cont))

            # Continuation geometry elevation for cross-page candidates
            for item in pre_candidates:
                _i, asset, score_dict = item
                a_page = int(asset.get("page", 0) or 0)
                if a_page and a_page == caption_page - 1:
                    ab = asset.get("bbox") or [0, 0, 0, 0]
                    cb = caption.get("bbox") or [0, 0, 0, 0]
                    if len(ab) >= 4 and len(cb) >= 4:
                        x_ratio = (min(cb[2], ab[2]) - max(cb[0], ab[0])) / max(1.0, min(cb[2] - cb[0], ab[2] - ab[0]))
                        page_h = max(_page_max_y.values()) if _page_max_y else 1.0
                        if x_ratio >= 0.5 and float(ab[3]) >= page_h * 0.85 and float(cb[1]) <= page_h * 0.15:
                            score_dict["score"] = min(score_dict.get("score", 0.0) + 0.15, 1.0)
                            score_dict.setdefault("evidence", []).append("continuation_geometry_elevation")

            # Tie-break re-sort
            pre_candidates.sort(
                key=lambda item: _bare_table_tie_break(item[2], caption, item[1]),
                reverse=True,
            )

            should_proceed = False
            if pre_candidates:
                top_score = pre_candidates[0][2].get("score", 0.0)
                second_score_pre = pre_candidates[1][2].get("score", 0.0) if len(pre_candidates) > 1 else -1.0
                score_gap = top_score - second_score_pre
                top_evidence = pre_candidates[0][2].get("evidence", [])
                has_strong_spatial = _has_strong_spatial_evidence_for_bare_table(caption, pre_candidates[0][2])
                is_cont_match = "continuation_geometry_elevation" in top_evidence
                is_tie_break_winner = top_score >= 0.5 and score_gap >= 0.2

                if (has_strong_spatial and score_gap >= 0.2) or is_cont_match or is_tie_break_winner:
                    should_proceed = True

            if should_proceed:
                all_candidates = pre_candidates
            else:
                unmatched_captions.append(caption)
                tables.append(
                    {
                        "caption_block_id": caption.get("block_id", ""),
                        "page": caption_page,
                        "caption_text": caption_text,
                        "table_number": table_num,
                        "formal_table_number": formal_table_number,
                        "asset_block_id": "",
                        "asset_bbox": [],
                        "assistive_text": "",
                        "truth_source": "image",
                        "has_asset": False,
                        "segments": [],
                        "is_continuation": is_cont,
                        "continuation_of": None,
                        "match_status": "ambiguous",
                        "candidate_assets": [],
                        "match_score": {
                            "score": 0.0,
                            "matched_asset_id": "",
                            "decision": "ambiguous",
                            "evidence": ["weak_explicit_caption"],
                        },
                    }
                )
                continue

        candidate_pages = [caption_page - 1, caption_page, caption_page + 1]

        if not all_candidates:
            for page in candidate_pages:
                if page < 1:
                    continue
                page_assets = [
                    (i, asset)
                    for i, asset in enumerate(assets)
                    if i not in used_asset_indices and asset.get("page", 0) == page
                ]
                all_candidates.extend(_score_candidate_assets(page_assets, caption, is_continuation=is_cont))

        all_candidates.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
        match_status = "unmatched_caption"
        candidate_assets = [
            {"asset_block_id": asset.get("block_id", ""), "match_score": score}
            for _, asset, score in all_candidates[:3]
        ]

        matched_asset = None
        if all_candidates:
            top_idx, top_asset, top_score = all_candidates[0]
            second_score = all_candidates[1][2].get("score", 0.0) if len(all_candidates) > 1 else -1.0
            if top_score.get("score", 0.0) < 0.4:
                matched_asset = None
                match_status = "unmatched_caption"
            elif top_score.get("score", 0.0) - second_score < 0.15:
                matched_asset = None
                match_status = "ambiguous"
            else:
                matched_asset = top_asset
                used_asset_indices.add(top_idx)
                match_status = "matched" if top_score.get("score", 0.0) >= 0.6 else "matched_low_confidence"

        continuation_of = None
        if is_cont and formal_table_number is not None:
            for t in tables:
                tt = t.get("formal_table_number")
                if tt == formal_table_number and not t.get("is_continuation"):
                    continuation_of = formal_table_number
                    break

        segments: list[dict] = []
        if matched_asset:
            segments.append(
                {
                    "page": matched_asset.get("page", 0),
                    "asset_block_id": matched_asset.get("block_id", ""),
                    "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]),
                    "is_continuation": is_cont,
                }
            )

        note_block_ids: list[str] = []
        note_texts: list[str] = []
        note_bboxes: list[list[float]] = []
        note_band_bbox: list[float] = []
        note_match_reason = ""
        note_confidence = 0.0

        if matched_asset:
            asset_page = matched_asset.get("page", 0)
            asset_bbox = matched_asset.get("bbox", [0, 0, 0, 0])
            asset_bottom = asset_bbox[3] if len(asset_bbox) >= 4 else 0
            candidates: list[dict] = []
            for block in structured_blocks:
                bpage = block.get("page", 0)
                if bpage != asset_page:
                    continue
                brole = str(block.get("role", "") or "")
                braw_label = str(block.get("raw_label", "") or "").strip()
                btext = str(block.get("text", "") or "").strip()
                is_note = (
                    brole == "footnote"
                    or braw_label == "vision_footnote"
                    or (
                        0 < len(btext) < 120
                        and brole
                        not in (
                            "noise",
                            "page_footer",
                            "page_header",
                            "frontmatter_noise",
                            "table_caption",
                            "table_caption_candidate",
                            "table_asset",
                            "media_asset",
                            "figure_caption",
                            "section_heading",
                            "subsection_heading",
                            "reference_heading",
                        )
                    )
                )
                if not is_note:
                    continue
                bbbox = block.get("bbox") or [0, 0, 0, 0]
                if len(bbbox) < 4:
                    note_match_reason = "invalid_bbox"
                    continue
                if bbbox[1] < asset_bottom or bbbox[1] > asset_bottom + 100:
                    note_match_reason = "outside_vertical_range"
                    continue
                if _table_note_falls_into_page_footnote_prior(bbbox, int(asset_page or 0), page_footnote_prior):
                    note_match_reason = "page_footnote_prior_rejected"
                    continue
                if _looks_like_body_text_below_table(block, asset_bbox):
                    note_match_reason = "body_text_like_excluded"
                    continue
                candidates.append(block)

            if not candidates and not note_match_reason:
                note_match_reason = "no_footnote_role"

            if candidates:
                candidates.sort(key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
                note_block_ids = [str(b.get("block_id", "")) for b in candidates if b.get("block_id")]
                note_texts = [
                    str(b.get("text", "") or "").strip() for b in candidates if str(b.get("text", "") or "").strip()
                ]
                note_bboxes = [b.get("bbox", [0, 0, 0, 0]) for b in candidates]
                note_band_bbox = [
                    min(bb[0] for bb in note_bboxes),
                    min(bb[1] for bb in note_bboxes),
                    max(bb[2] for bb in note_bboxes),
                    max(bb[3] for bb in note_bboxes),
                ]
                note_match_reason = "note_band_geometry_match"
                note_confidence = 0.85

        consumed_block_ids = [caption.get("block_id", "")] if matched_asset else []
        if matched_asset:
            consumed_block_ids.append(matched_asset.get("block_id", ""))
        consumed_block_ids.extend(note_block_ids)
        consumed_block_ids.extend(continuation_ids)
        consumed_block_ids = [bid for bid in consumed_block_ids if bid]
        bridge_block_ids = [
            str(block.get("block_id") or "")
            for block in structured_blocks
            if int(block.get("page", 0) or 0) == int(caption_page or 0)
            and block.get("bridge_eligible")
            and str(block.get("layout_region") or "") == "display_zone"
            and block.get("block_id")
        ]

        # Compute rotated table render bbox (if content is rotated)
        _render_bbox = None
        _render_rotation_deg = 0
        if matched_asset:
            _rot = _table_has_rotated_content(matched_asset)
            if _rot:
                cb = caption.get("bbox") or caption.get("block_bbox") or []
                ab = matched_asset.get("bbox") or matched_asset.get("block_bbox") or []
                if len(cb) >= 4 and len(ab) >= 4:
                    _render_bbox = [
                        min(cb[0], ab[0]),
                        min(cb[1], ab[1]),
                        max(cb[2], ab[2]),
                        max(cb[3], ab[3]),
                    ]
                    _render_rotation_deg = _rot

        tables.append(
            {
                "caption_block_id": caption.get("block_id", ""),
                "page": caption_page,
                "caption_text": caption_text,
                "table_number": table_num,
                "formal_table_number": formal_table_number,
                "asset_block_id": matched_asset.get("block_id", "") if matched_asset else "",
                "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]) if matched_asset else [],
                "assistive_text": (matched_asset.get("text", "") or "") if matched_asset else "",
                "truth_source": "image",
                "has_asset": matched_asset is not None,
                "segments": segments,
                "note_block_ids": note_block_ids,
                "note_texts": note_texts,
                "note_bboxes": note_bboxes,
                "note_band_bbox": note_band_bbox,
                "note_match_reason": note_match_reason,
                "note_confidence": note_confidence,
                "bridge_block_ids": bridge_block_ids,
                "consumed_block_ids": consumed_block_ids,
                "is_continuation": is_cont,
                "continuation_of": continuation_of,
                "match_status": match_status,
                "candidate_assets": candidate_assets,
                "match_score": (
                    score_table_match(caption, matched_asset, is_continuation=is_cont)
                    if matched_asset
                    else (
                        all_candidates[0][2]
                        if all_candidates
                        else {"score": 0.0, "matched_asset_id": "", "decision": "ambiguous", "evidence": []}
                    )
                ),
                "render_bbox": _render_bbox,
                "render_rotation_deg": _render_rotation_deg,
                "asset_family_hint": (matched_asset.get("asset_family_hint") if matched_asset else None),
                "asset_family_confidence": (matched_asset.get("asset_family_confidence") if matched_asset else None),
                "asset_family_evidence": (matched_asset.get("asset_family_evidence") if matched_asset else None),
            }
        )

    cap_block_ids_with_asset = {t["caption_block_id"] for t in tables if t["has_asset"]}
    for caption in captions:
        if caption.get("block_id", "") not in cap_block_ids_with_asset:
            already_listed = any(c.get("block_id", "") == caption.get("block_id", "") for c in unmatched_captions)
            if not already_listed:
                unmatched_captions.append(caption)

    for i, asset in enumerate(assets):
        if i not in used_asset_indices:
            unmatched_assets.append(asset)

    return {
        "tables": tables,
        "held_tables": held_tables,
        "unmatched_captions": unmatched_captions,
        "unmatched_assets": unmatched_assets,
        "official_table_count": len([t for t in tables if t["has_asset"] and not t["is_continuation"]]),
    }


def write_back_table_roles(inventory: dict, structured_blocks: list[dict]) -> None:
    """Update structured block roles for matched tables from media_asset to table_html."""
    for table in inventory.get("tables", []):
        asset_bid = table.get("asset_block_id")
        if not asset_bid:
            continue
        for block in structured_blocks:
            if block.get("block_id") == asset_bid and block.get("page") == table.get("page"):
                if block.get("role") in {"media_asset", "table_asset"}:
                    block["role"] = "table_html"
                break


def write_table_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)


def build_table_inventory_vnext(structured_blocks: list[dict]) -> dict[str, Any]:
    from .ocr_pairing_framework import run_pairing_passes
    from .ocr_pairing_state import OwnershipLedger, PipelineState
    from .ocr_table_domain import TableCandidateIndex, TableCorpus, assemble_table_inventory
    from .ocr_table_passes import (
        TableAdjacentPagePass,
        TableFinalAccountingPass,
        TableNotesAttachmentPass,
        TableSamePagePass,
        TableWeakCaptionRecoveryPass,
    )

    corpus = TableCorpus.from_blocks(structured_blocks)
    candidate_index = TableCandidateIndex.from_corpus(corpus)
    state = PipelineState(corpus=corpus, candidate_index=candidate_index, ledger=OwnershipLedger())
    reports = run_pairing_passes(
        state,
        [
            TableWeakCaptionRecoveryPass,
            TableSamePagePass,
            TableAdjacentPagePass,
            TableNotesAttachmentPass,
            TableFinalAccountingPass,
        ],
    )
    inventory = assemble_table_inventory(state, candidate_index)
    inventory["pass_reports"] = [asdict(r) for r in reports]
    return inventory
