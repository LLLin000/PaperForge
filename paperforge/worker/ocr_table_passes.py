from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


class TableWeakCaptionRecoveryPass:
    name = "table_weak_caption_recovery"

    def run(self, state):
        from . import ocr_tables

        report = PassReport(pass_name=self.name)
        for record in state.candidate_index.caption_records:
            if not record["is_weak_truncated"]:
                continue
            caption = record["caption"]
            continuation = ocr_tables._find_table_caption_continuation(caption, state.corpus.blocks)
            materialized, continuation_ids = ocr_tables._materialize_table_caption(caption, continuation)
            record["caption"] = materialized
            record["caption_text"] = str(materialized.get("text", "") or "")
            record["continuation_ids"] = continuation_ids
            if record["is_validation_first_candidate"]:
                same_page_assets = state.candidate_index.assets_by_page.get(int(caption.get("page", 0) or 0), [])
                if not same_page_assets:
                    record["status"] = "held"
                    record["held_table"] = {
                        "table_id": f"held_table_{len([r for r in state.candidate_index.caption_records if r.get('status') == 'held']) + 1:03d}",
                        "caption_block_id": record["caption_block_id"],
                        "page": caption.get("page", 0),
                        "caption_text": record["caption_text"],
                        "table_number": record["table_number"],
                        "formal_table_number": record["formal_table_number"],
                        "hold_reason": "insufficient_caption_evidence",
                        "zone": caption.get("zone", ""),
                        "style_family": caption.get("style_family", ""),
                        "marker_signature": caption.get("marker_signature", {}),
                    }
        return report


class TableSamePagePass:
    name = "table_same_page"

    def run(self, state):
        from . import ocr_tables

        report = PassReport(pass_name=self.name)
        for record in state.candidate_index.caption_records:
            if record.get("status") != "pending":
                continue
            caption = record["caption"]
            caption_page = int(caption.get("page", 0) or 0)
            page_assets = [
                (idx, asset)
                for idx, asset in state.candidate_index.assets_by_page.get(caption_page, [])
                if state.ledger.owner_of_asset(page=caption_page, block_id=asset.get("block_id")) is None
            ]
            scored = ocr_tables._score_candidate_assets(page_assets, caption, is_continuation=record["is_continuation"])
            scored.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
            record["candidate_assets"] = [
                {"asset_block_id": asset.get("block_id", ""), "match_score": score}
                for _, asset, score in scored[:3]
            ]
            if not scored:
                continue
            top_idx, top_asset, top_score = scored[0]
            second_score = scored[1][2].get("score", 0.0) if len(scored) > 1 else -1.0
            if top_score.get("score", 0.0) < 0.4 or top_score.get("score", 0.0) - second_score < 0.15:
                continue
            owner = ResourceRef(kind="legend", page=caption_page, block_id=record["caption_block_id"], figure_no=record["formal_table_number"])
            asset_ref = ResourceRef(kind="asset", page=int(top_asset.get("page", 0) or 0), block_id=top_asset.get("block_id"))
            conflict = state.ledger.try_claim_assets([asset_ref], owner=owner, reason=self.name)
            if conflict is not None:
                report.conflicts.append(conflict)
                continue
            match_status = "matched" if top_score.get("score", 0.0) >= 0.6 else "matched_low_confidence"
            state.accept_match(
                ClaimProposal(
                    pass_name=self.name,
                    figure_no=record["formal_table_number"],
                    claim_type="match",
                    legends=[owner],
                    assets=[asset_ref],
                    groups=[],
                    texts=[],
                    confidence=float(top_score.get("score", 0.0)),
                    evidence_rank=0,
                    reason=self.name,
                ),
                {
                    "caption_block_id": record["caption_block_id"],
                    "page": caption_page,
                    "caption_text": record["caption_text"],
                    "table_number": record["table_number"],
                    "formal_table_number": record["formal_table_number"],
                    "asset_block_id": top_asset.get("block_id", ""),
                    "asset_bbox": top_asset.get("bbox", [0, 0, 0, 0]),
                    "assistive_text": str(top_asset.get("text", "") or ""),
                    "truth_source": "image",
                    "has_asset": True,
                    "segments": [
                        {
                            "page": top_asset.get("page", 0),
                            "asset_block_id": top_asset.get("block_id", ""),
                            "asset_bbox": top_asset.get("bbox", [0, 0, 0, 0]),
                            "is_continuation": record["is_continuation"],
                        }
                    ],
                    "note_block_ids": [],
                    "note_texts": [],
                    "note_bboxes": [],
                    "note_band_bbox": [],
                    "note_match_reason": "",
                    "note_confidence": 0.0,
                    "bridge_block_ids": [],
                    "consumed_block_ids": [record["caption_block_id"], top_asset.get("block_id", ""), *record.get("continuation_ids", [])],
                    "is_continuation": record["is_continuation"],
                    "continuation_of": None,
                    "match_status": match_status,
                    "candidate_assets": record["candidate_assets"],
                    "match_score": top_score,
                    "render_bbox": None,
                    "render_rotation_deg": 0,
                    "asset_family_hint": top_asset.get("asset_family_hint"),
                    "asset_family_confidence": top_asset.get("asset_family_confidence"),
                    "asset_family_evidence": top_asset.get("asset_family_evidence"),
                },
            )
            record["status"] = "matched"
        return report


class TableAdjacentPagePass:
    name = "table_adjacent_page"

    def run(self, state):
        from . import ocr_tables

        report = PassReport(pass_name=self.name)
        for record in state.candidate_index.caption_records:
            if record.get("status") != "pending":
                continue
            caption = record["caption"]
            caption_page = int(caption.get("page", 0) or 0)
            candidate_pages = [caption_page - 1, caption_page, caption_page + 1]
            all_candidates = []
            for page in candidate_pages:
                if page < 1:
                    continue
                page_assets = [
                    (idx, asset)
                    for idx, asset in state.candidate_index.assets_by_page.get(page, [])
                    if state.ledger.owner_of_asset(page=page, block_id=asset.get("block_id")) is None
                ]
                all_candidates.extend(ocr_tables._score_candidate_assets(page_assets, caption, is_continuation=record["is_continuation"]))

            for _, asset, score_dict in all_candidates:
                a_page = int(asset.get("page", 0) or 0)
                if a_page == caption_page - 1:
                    ab = asset.get("bbox") or [0, 0, 0, 0]
                    cb = caption.get("bbox") or [0, 0, 0, 0]
                    if len(ab) >= 4 and len(cb) >= 4:
                        x_ratio = (min(cb[2], ab[2]) - max(cb[0], ab[0])) / max(1.0, min(cb[2] - cb[0], ab[2] - ab[0]))
                        page_h = max(state.corpus.page_max_y.values()) if state.corpus.page_max_y else 1.0
                        if x_ratio >= 0.5 and float(ab[3]) >= page_h * 0.85 and float(cb[1]) <= page_h * 0.15:
                            score_dict["score"] = min(score_dict.get("score", 0.0) + 0.15, 1.0)
                            score_dict.setdefault("evidence", []).append("continuation_geometry_elevation")

            all_candidates.sort(key=lambda item: item[2].get("score", 0.0), reverse=True)
            record["candidate_assets"] = [
                {"asset_block_id": asset.get("block_id", ""), "match_score": score}
                for _, asset, score in all_candidates[:3]
            ]
            if not all_candidates:
                record["status"] = "unmatched"
                continue
            top_idx, top_asset, top_score = all_candidates[0]
            second_score = all_candidates[1][2].get("score", 0.0) if len(all_candidates) > 1 else -1.0
            if top_score.get("score", 0.0) < 0.4:
                record["status"] = "unmatched"
                continue
            if top_score.get("score", 0.0) - second_score < 0.15:
                record["status"] = "ambiguous"
                continue
            owner = ResourceRef(kind="legend", page=caption_page, block_id=record["caption_block_id"], figure_no=record["formal_table_number"])
            asset_ref = ResourceRef(kind="asset", page=int(top_asset.get("page", 0) or 0), block_id=top_asset.get("block_id"))
            conflict = state.ledger.try_claim_assets([asset_ref], owner=owner, reason=self.name)
            if conflict is not None:
                report.conflicts.append(conflict)
                continue
            match_status = "matched" if top_score.get("score", 0.0) >= 0.6 else "matched_low_confidence"
            continuation_of = None
            if record["is_continuation"] and record["formal_table_number"] is not None:
                for existing in state.matches:
                    if existing.get("formal_table_number") == record["formal_table_number"] and not existing.get("is_continuation"):
                        continuation_of = record["formal_table_number"]
                        break
            state.accept_match(
                ClaimProposal(
                    pass_name=self.name,
                    figure_no=record["formal_table_number"],
                    claim_type="match",
                    legends=[owner],
                    assets=[asset_ref],
                    groups=[],
                    texts=[],
                    confidence=float(top_score.get("score", 0.0)),
                    evidence_rank=1,
                    reason=self.name,
                ),
                {
                    "caption_block_id": record["caption_block_id"],
                    "page": caption_page,
                    "caption_text": record["caption_text"],
                    "table_number": record["table_number"],
                    "formal_table_number": record["formal_table_number"],
                    "asset_block_id": top_asset.get("block_id", ""),
                    "asset_bbox": top_asset.get("bbox", [0, 0, 0, 0]),
                    "assistive_text": str(top_asset.get("text", "") or ""),
                    "truth_source": "image",
                    "has_asset": True,
                    "segments": [
                        {
                            "page": top_asset.get("page", 0),
                            "asset_block_id": top_asset.get("block_id", ""),
                            "asset_bbox": top_asset.get("bbox", [0, 0, 0, 0]),
                            "is_continuation": record["is_continuation"],
                        }
                    ],
                    "note_block_ids": [],
                    "note_texts": [],
                    "note_bboxes": [],
                    "note_band_bbox": [],
                    "note_match_reason": "",
                    "note_confidence": 0.0,
                    "bridge_block_ids": [],
                    "consumed_block_ids": [record["caption_block_id"], top_asset.get("block_id", ""), *record.get("continuation_ids", [])],
                    "is_continuation": record["is_continuation"],
                    "continuation_of": continuation_of,
                    "match_status": match_status,
                    "candidate_assets": record["candidate_assets"],
                    "match_score": top_score,
                    "render_bbox": None,
                    "render_rotation_deg": 0,
                    "asset_family_hint": top_asset.get("asset_family_hint"),
                    "asset_family_confidence": top_asset.get("asset_family_confidence"),
                    "asset_family_evidence": top_asset.get("asset_family_evidence"),
                },
            )
            record["status"] = "matched"
        return report


class TableNotesAttachmentPass:
    name = "table_notes_attachment"

    def run(self, state):
        from . import ocr_tables

        report = PassReport(pass_name=self.name)
        for table in state.matches:
            if not table.get("has_asset"):
                table.setdefault("note_block_ids", [])
                table.setdefault("note_texts", [])
                table.setdefault("note_bboxes", [])
                table.setdefault("note_band_bbox", [])
                table.setdefault("note_match_reason", "")
                table.setdefault("note_confidence", 0.0)
                table.setdefault("bridge_block_ids", [])
                continue

            asset_page = int(table.get("page", 0) or 0)
            asset_bbox = table.get("asset_bbox", [0, 0, 0, 0])
            asset_bottom = asset_bbox[3] if len(asset_bbox) >= 4 else 0

            candidates = []
            note_match_reason = ""
            for block in state.corpus.blocks:
                if int(block.get("page", 0) or 0) != asset_page:
                    continue
                brole = str(block.get("role", "") or "")
                braw_label = str(block.get("raw_label", "") or "").strip()
                btext = str(block.get("text", "") or "").strip()
                is_note = (
                    brole == "footnote"
                    or braw_label == "vision_footnote"
                    or (
                        0 < len(btext) < 120
                        and brole not in {
                            "noise", "page_footer", "page_header", "frontmatter_noise",
                            "table_caption", "table_caption_candidate",
                            "table_asset", "media_asset", "figure_caption",
                            "section_heading", "subsection_heading", "reference_heading",
                        }
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
                if ocr_tables._table_note_falls_into_page_footnote_prior(bbbox, asset_page, state.corpus.page_footnote_prior):
                    note_match_reason = "page_footnote_prior_rejected"
                    continue
                if ocr_tables._looks_like_body_text_below_table(block, asset_bbox):
                    note_match_reason = "body_text_like_excluded"
                    continue
                candidates.append(block)

            if candidates:
                candidates.sort(key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
                table["note_block_ids"] = [str(b.get("block_id", "")) for b in candidates if b.get("block_id")]
                table["note_texts"] = [str(b.get("text", "") or "").strip() for b in candidates if str(b.get("text", "") or "").strip()]
                table["note_bboxes"] = [b.get("bbox", [0, 0, 0, 0]) for b in candidates]
                table["note_band_bbox"] = [
                    min(bb[0] for bb in table["note_bboxes"]),
                    min(bb[1] for bb in table["note_bboxes"]),
                    max(bb[2] for bb in table["note_bboxes"]),
                    max(bb[3] for bb in table["note_bboxes"]),
                ]
                table["note_match_reason"] = "note_band_geometry_match"
                table["note_confidence"] = 0.85
            else:
                table.setdefault("note_block_ids", [])
                table.setdefault("note_texts", [])
                table.setdefault("note_bboxes", [])
                table.setdefault("note_band_bbox", [])
                table["note_match_reason"] = note_match_reason or "no_footnote_role"
                table.setdefault("note_confidence", 0.0)

            asset_block = next(
                (a for a in state.corpus.raw_assets if str(a.get("block_id", "")) == str(table.get("asset_block_id", "")) and int(a.get("page", 0) or 0) == asset_page),
                None,
            )
            if asset_block is not None:
                rot = ocr_tables._table_has_rotated_content(asset_block)
                if rot:
                    ab = table.get("asset_bbox", [])
                    caption = next(
                        (r["caption"] for r in state.candidate_index.caption_records if r["caption_block_id"] == table.get("caption_block_id")),
                        None,
                    )
                    cb = (caption.get("bbox") or caption.get("block_bbox") or []) if caption else []
                    if len(ab) >= 4 and len(cb) >= 4:
                        table["render_bbox"] = [min(cb[0], ab[0]), min(cb[1], ab[1]), max(cb[2], ab[2]), max(cb[3], ab[3])]
                        table["render_rotation_deg"] = rot

            # Bridge block detection
            table["bridge_block_ids"] = [
                str(block.get("block_id") or "")
                for block in state.corpus.blocks
                if int(block.get("page", 0) or 0) == asset_page
                and block.get("bridge_eligible")
                and str(block.get("layout_region") or "") == "display_zone"
                and block.get("block_id")
            ]

            # Consumed block IDs include notes
            existing_ids = set(table.get("consumed_block_ids") or [])
            for bid in table.get("note_block_ids", []):
                if bid not in existing_ids:
                    table.setdefault("consumed_block_ids", []).append(bid)
        return report


class TableFinalAccountingPass:
    name = "table_final_accounting"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        state.completeness = {
            "total_numbered_tables": len([r for r in state.candidate_index.caption_records if r.get("formal_table_number") is not None]),
            "accounted_for": len([r for r in state.candidate_index.caption_records if r.get("status") in {"matched", "held"}]),
            "details": [
                {"caption_block_id": r["caption_block_id"], "status": r.get("status", "pending")}
                for r in state.candidate_index.caption_records
            ],
        }
        return report
