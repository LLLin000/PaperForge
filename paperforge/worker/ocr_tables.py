from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json
from paperforge.worker.ocr_scores import score_table_match

_TABLE_PREFIX_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+(\d+(?:\.\d+)?)",
    flags=re.IGNORECASE,
)

_CONTINUATION_PATTERN = re.compile(r"\(cont(?:inued)?\.?\)", re.IGNORECASE)
_TRUNCATED_TABLE_ONLY_PATTERN = re.compile(
    r"^(?:Table|Supplementary\s+Table|Extended\s+Data\s+Table)\s+\d+(?:\.\d+)?\.?$",
    re.IGNORECASE,
)


def _extract_table_number(text: str) -> int | None:
    m = _TABLE_PREFIX_PATTERN.search(text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


def _is_continuation_caption(text: str) -> bool:
    return bool(_CONTINUATION_PATTERN.search(text))


def _extract_base_table_number(text: str) -> int | None:
    cleaned = _CONTINUATION_PATTERN.sub("", text).strip()
    return _extract_table_number(cleaned)


def _is_validation_first_table_candidate(block: dict) -> bool:
    role = str(block.get("role", "") or "")
    if role in {"table_caption", "table_caption_candidate"}:
        return False
    marker_type = ((block.get("marker_signature") or {}).get("type") or "none")
    zone = str(block.get("zone", "") or "")
    style_family = str(block.get("style_family", "") or "")
    return marker_type == "table_number" and zone == "display_zone" and style_family == "table_caption_like"


def _is_insufficient_table_caption_evidence(block: dict) -> bool:
    text = str(block.get("text", "") or "").strip()
    return bool(_TRUNCATED_TABLE_ONLY_PATTERN.fullmatch(text))


def _is_weak_explicit_table_caption(block: dict) -> bool:
    role = str(block.get("role", "") or "")
    if role not in {"table_caption", "table_caption_candidate"}:
        return False
    return _is_insufficient_table_caption_evidence(block)


def _score_candidate_assets(
    page_assets: list[tuple[int, dict]],
    caption: dict,
    *,
    is_continuation: bool,
) -> list[tuple[int, dict, dict]]:
    scored = [
        (i, asset, score_table_match(caption, asset, is_continuation=is_continuation))
        for i, asset in page_assets
    ]
    scored.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
    return scored


def build_table_inventory(structured_blocks: list[dict]) -> dict[str, Any]:
    tables: list[dict] = []
    captions: list[dict] = []
    assets: list[dict] = []
    held_tables: list[dict] = []
    unmatched_captions: list[dict] = []
    unmatched_assets: list[dict] = []

    for block in structured_blocks:
        role = block.get("role", "")
        raw_label = str(block.get("raw_label", "") or "").strip()
        if role in {"table_caption", "table_caption_candidate"} or _is_validation_first_table_candidate(block):
            captions.append(block)
        elif role in ("table_asset", "media_asset"):
            if role == "media_asset" and raw_label not in ("table",):
                continue
            assets.append(block)

    used_asset_indices: set[int] = set()
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
            held_tables.append({
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
            })
            continue
        if is_weak_explicit_caption:
            unmatched_captions.append(caption)
            tables.append({
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
            })
            continue

        candidate_pages = [caption_page - 1, caption_page, caption_page + 1]

        all_candidates: list[tuple[int, dict, dict]] = []
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
            segments.append({
                "page": matched_asset.get("page", 0),
                "asset_block_id": matched_asset.get("block_id", ""),
                "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]),
                "is_continuation": is_cont,
            })

        note_block_ids: list[str] = []
        if matched_asset:
            asset_page = matched_asset.get("page", 0)
            asset_bbox = matched_asset.get("bbox", [0, 0, 0, 0])
            asset_bottom = asset_bbox[3] if len(asset_bbox) >= 4 else 0
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
                    or (0 < len(btext) < 120
                        and brole not in (
                            "table_caption", "table_caption_candidate",
                            "table_asset", "media_asset",
                            "figure_caption", "section_heading",
                            "subsection_heading", "reference_heading",
                        ))
                )
                if not is_note:
                    continue
                bbbox = block.get("bbox", [0, 0, 0, 0])
                if len(bbbox) < 4:
                    continue
                note_top = bbbox[1]
                if asset_bottom <= note_top <= asset_bottom + 80:
                    note_block_ids.append(block.get("block_id", ""))

        tables.append({
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
            "is_continuation": is_cont,
            "continuation_of": continuation_of,
            "match_status": match_status,
            "candidate_assets": candidate_assets,
            "match_score": (
                score_table_match(caption, matched_asset, is_continuation=is_cont)
                if matched_asset
                else (all_candidates[0][2] if all_candidates else {"score": 0.0, "matched_asset_id": "", "decision": "ambiguous", "evidence": []})
            ),
        })

    cap_block_ids_with_asset = {
        t["caption_block_id"] for t in tables if t["has_asset"]
    }
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
        "official_table_count": len(
            [t for t in tables if t["has_asset"] and not t["is_continuation"]]
        ),
    }


def write_table_inventory(dst: Path, inventory: dict[str, Any]) -> None:
    write_json(dst, inventory)
