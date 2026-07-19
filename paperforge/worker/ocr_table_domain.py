from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TableCorpus:
    blocks: list[dict]
    raw_captions: list[dict] = field(default_factory=list)
    raw_assets: list[dict] = field(default_factory=list)
    page_footnote_prior: dict[int, float] = field(default_factory=dict)
    page_max_y: dict[int, float] = field(default_factory=dict)

    @classmethod
    def from_blocks(cls, blocks: list[dict]) -> TableCorpus:
        from . import ocr_tables

        raw_captions = [
            b
            for b in blocks
            if ocr_tables._match_role(b) in {"table_caption", "table_caption_candidate"}
            or ocr_tables._is_validation_first_table_candidate(b)
        ]
        raw_assets = []
        for block in blocks:
            role = ocr_tables._match_role(block)
            raw_label = str(block.get("raw_label", "") or "").strip()
            if role not in ("table_asset", "table_html", "media_asset", "figure_asset"):
                continue
            if role == "figure_asset" and raw_label != "table":
                continue
            raw_assets.append(block)

        page_footnote_prior = ocr_tables._collect_page_footnote_prior(blocks)
        page_max_y: dict[int, float] = {}
        for block in blocks:
            bbox = block.get("bbox") or [0, 0, 0, 0]
            if len(bbox) >= 4:
                page = int(block.get("page", 0) or 0)
                page_max_y[page] = max(page_max_y.get(page, 0.0), float(bbox[3]))

        return cls(
            blocks=blocks,
            raw_captions=raw_captions,
            raw_assets=raw_assets,
            page_footnote_prior=page_footnote_prior,
            page_max_y=page_max_y,
        )


@dataclass
class TableCandidateIndex:
    caption_records: list[dict]
    assets_by_page: dict[int, list[tuple[int, dict]]]

    @classmethod
    def from_corpus(cls, corpus: TableCorpus) -> TableCandidateIndex:
        from . import ocr_tables

        captions = sorted(
            corpus.raw_captions,
            key=lambda block: (
                int(block.get("page", 0) or 0),
                str(block.get("block_id", "")),
            ),
        )
        caption_records = []
        for caption in captions:
            text = str(caption.get("text", "") or "")
            caption_records.append(
                {
                    "caption": caption,
                    "caption_block_id": str(caption.get("block_id", "")),
                    "caption_text": text,
                    "table_number": ocr_tables._extract_table_number(text),
                    "formal_table_number": ocr_tables._extract_base_table_number(text),
                    "is_continuation": ocr_tables._is_continuation_caption(text),
                    "is_validation_first_candidate": ocr_tables._is_validation_first_table_candidate(
                        caption
                    ),
                    "is_weak_truncated": ocr_tables._is_insufficient_table_caption_evidence(
                        caption
                    ),
                    "is_weak_explicit_caption": ocr_tables._is_weak_explicit_table_caption(
                        caption
                    ),
                    "continuation_ids": [],
                    "status": "pending",
                    "candidate_assets": [],
                }
            )

        assets_by_page: dict[int, list[tuple[int, dict]]] = {}
        for idx, asset in enumerate(corpus.raw_assets):
            page = int(asset.get("page", 0) or 0)
            assets_by_page.setdefault(page, []).append((idx, asset))

        return cls(caption_records=caption_records, assets_by_page=assets_by_page)


def assemble_table_inventory(
    state, candidate_index: TableCandidateIndex
) -> dict[str, Any]:
    matched_caption_ids = {
        t.get("caption_block_id", "")
        for t in state.matches
        if t.get("has_asset")
    }
    used_asset_ids = {
        str(t.get("asset_block_id", ""))
        for t in state.matches
        if t.get("has_asset") and t.get("asset_block_id")
    }
    held_tables = [
        record["held_table"]
        for record in candidate_index.caption_records
        if record.get("status") == "held" and "held_table" in record
    ]
    unmatched_captions = [
        record["caption"]
        for record in candidate_index.caption_records
        if record["caption_block_id"] not in matched_caption_ids
        and record.get("status") != "held"
    ]
    # Create has_asset=False table entries for unmatched captions (legacy-compat)
    unmatched_table_entries: list[dict] = []
    for record in candidate_index.caption_records:
        if record["caption_block_id"] in matched_caption_ids or record.get("status") == "held":
            continue
        caption = record["caption"]
        unmatched_table_entries.append(
            {
                "caption_block_id": record["caption_block_id"],
                "page": caption.get("page", 0),
                "caption_text": record["caption_text"],
                "table_number": record["table_number"],
                "formal_table_number": record["formal_table_number"],
                "asset_block_id": None,
                "asset_bbox": [],
                "assistive_text": "",
                "truth_source": "image",
                "has_asset": False,
                "segments": [],
                "note_block_ids": [],
                "note_texts": [],
                "note_bboxes": [],
                "note_band_bbox": [],
                "note_match_reason": "",
                "note_confidence": 0.0,
                "bridge_block_ids": [],
                "consumed_block_ids": [],
                "is_continuation": record["is_continuation"],
                "continuation_of": None,
                "match_score": {"decision": "unmatched", "evidence": [], "matched_asset_id": "", "score": 0.0},
                "match_status": record.get("status", "unmatched_caption"),
                "candidate_assets": record["candidate_assets"],
                "render_bbox": None,
                "render_rotation_deg": 0,
            }
        )

    unmatched_assets = [
        asset
        for page_assets in candidate_index.assets_by_page.values()
        for _, asset in page_assets
        if str(asset.get("block_id", "")) not in used_asset_ids
    ]
    return {
        "tables": list(state.matches) + unmatched_table_entries,
        "held_tables": held_tables,
        "unmatched_captions": unmatched_captions,
        "unmatched_assets": unmatched_assets,
        "official_table_count": len(
            [t for t in state.matches if t.get("has_asset") and not t.get("is_continuation")]
        ),
    }
