from __future__ import annotations

import math

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class PrimarySamePagePass:
    name = "primary_same_page"

    def _collect_proposals(self, state):
        from . import ocr_figures

        proposals = []

        _numbered_count_by_page: dict[int, int] = {}
        _short_caption_count_by_page: dict[int, int] = {}
        _page_blocks_map: dict[int, list[dict]] = {}
        _page_height_map: dict[int, float] = {}
        for _leg in state.candidate_index.deduped_legends:
            _lp = _resource_page(_leg)
            if _lp is not None:
                if ocr_figures._extract_figure_number(str(_leg.get("text", ""))) is not None:
                    _numbered_count_by_page[_lp] = _numbered_count_by_page.get(_lp, 0) + 1
                if ocr_figures._is_short_numbered_figure_caption(_leg):
                    _short_caption_count_by_page[_lp] = _short_caption_count_by_page.get(_lp, 0) + 1
        for _b in state.corpus.blocks:
            _bp = _resource_page(_b)
            if _bp is not None:
                _page_blocks_map.setdefault(_bp, []).append(_b)
                _bbox = _b.get("bbox") or [0, 0, 0, 0]
                _page_height_map[_bp] = max(_page_height_map.get(_bp, 0), _bbox[3])

        for legend in state.candidate_index.deduped_legends:
            page = _resource_page(legend)
            if page is None:
                continue
            if ocr_figures._is_previous_page_legend_locator(legend):
                continue
            if legend.get("_figure_continuation"):
                continue
            page_groups = [g for g in state.candidate_index.candidate_groups if _resource_page(g) == page]
            for group in page_groups:
                # Multiple short numbered captions cannot claim an entire shared
                # multi-asset cluster; let GroupSequentialPass split it by asset.
                _gt = group.get("group_type", "")
                _n_assets = len(group.get("media_blocks", []))
                if (
                    _gt == "distance_cluster"
                    and _n_assets >= 2
                    and _short_caption_count_by_page.get(page, 0) > 1
                    and ocr_figures._is_short_numbered_figure_caption(legend)
                ):
                    continue
                score = ocr_figures._score_legend_to_group(
                    legend,
                    group,
                    caption_score=ocr_figures.score_figure_caption(
                        legend,
                        nearby_media=True,
                        caption_style_match=False,
                        body_prose_likelihood=False,
                    ),
                    page_width=state.corpus.page_width,
                    page_height=_page_height_map.get(page, 0.0),
                    page_blocks=_page_blocks_map.get(page, []),
                    page_numbered_legend_count=_numbered_count_by_page.get(page, 0),
                )
                if score.get("decision") != "matched":
                    continue
                figure_no = ocr_figures._extract_figure_number(str(legend.get("text", "")))
                proposals.append(
                    ClaimProposal(
                        pass_name=self.name,
                        figure_no=figure_no,
                        claim_type="match",
                        legends=[
                            ResourceRef(kind="legend", page=page, block_id=legend.get("block_id"), figure_no=figure_no)
                        ],
                        assets=[
                            ResourceRef(kind="asset", page=page, block_id=bid)
                            for bid in group.get("asset_block_ids", [])
                        ],
                        groups=[ResourceRef(kind="group", page=page, block_id=None, group_id=group.get("group_id"))],
                        confidence=float(score.get("score", 0.0)),
                        evidence_rank=1,
                        reason="same_page_primary",
                        diagnostics={
                            "evidence": list(score.get("evidence", [])),
                            "legend_block_id": str(legend.get("block_id", "")),
                        },
                    )
                )
        return proposals

    def _materialize_match(self, state, proposal):
        from . import ocr_figures

        legend = proposal.legends[0]
        page = legend.page
        asset_ids = {str(r.block_id) for r in proposal.assets}
        matched_assets = [
            ocr_figures._project_asset_record(a)
            for a in state.corpus.raw_assets
            if _resource_page(a) == page and str(a.get("block_id", "")) in asset_ids
        ]
        legend_text = next(
            str(b.get("text", ""))
            for b in state.candidate_index.deduped_legends
            if _resource_page(b) == page and str(b.get("block_id", "")) == str(legend.block_id)
        )
        figure_no = proposal.figure_no
        marker = ocr_figures._extract_figure_marker(legend_text)
        namespace = marker["namespace"]
        if figure_no is None:
            figure_id = f"figure_unknown_{len(state.matches):03d}"
        else:
            figure_id = ocr_figures._format_figure_id(
                marker["namespace"],
                marker["number"],
                alpha_prefix=marker["alpha_prefix"],
            )
        return {
            "figure_id": figure_id,
            "figure_namespace": namespace,
            "figure_number": proposal.figure_no,
            "legend_block_id": legend.block_id,
            "page": page,
            "text": legend_text,
            "matched_assets": matched_assets,
            "asset_block_ids": sorted(asset_ids),
            "settlement_type": "same_page",
            "confidence": proposal.confidence,
            "match_score": {
                "score": proposal.confidence,
                "decision": "matched",
                "evidence": proposal.diagnostics["evidence"],
            },
            "flags": [],
            "bridge_block_ids": [],
        }

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)
        proposals = self._collect_proposals(state)
        sidecar_candidates = state.candidate_index.sidecar_candidates or {}
        for page, captions in sidecar_candidates.items():
            page = int(page)
            caption_ids = {str(caption.get("block_id", "")) for caption in captions}
            numbered_ids = {
                str(legend.get("block_id", ""))
                for legend in state.candidate_index.deduped_legends
                if _resource_page(legend) == page
                and ocr_figures._extract_figure_number(str(legend.get("text") or "")) is not None
            }
            if len(caption_ids) < 2 or caption_ids != numbered_ids:
                continue

            best_by_caption = {}
            for proposal in proposals:
                legend = proposal.legends[0]
                key = (legend.page, str(legend.block_id))
                if legend.page == page and str(legend.block_id) in caption_ids:
                    current = best_by_caption.get(key)
                    if current is None or proposal.confidence > current.confidence:
                        best_by_caption[key] = proposal
            if not best_by_caption:
                continue

            best_score = max(proposal.confidence for proposal in best_by_caption.values())
            # ponytail: near-equal scores use page order; tune the margin against reviewed PDFs.
            near_best = [
                (key, proposal)
                for key, proposal in best_by_caption.items()
                if best_score - proposal.confidence < 0.15
            ]
            caption_by_id = {str(caption.get("block_id", "")): caption for caption in captions}
            chosen_key, chosen = min(
                near_best,
                key=lambda item: (
                    (caption_by_id[item[0][1]].get("bbox") or [0, 0, 0, 0])[1],
                    item[0][1],
                ),
            )
            ordered_captions = sorted(
                captions,
                key=lambda caption: (caption.get("bbox") or [0, 0, 0, 0])[1],
            )
            page_assets = [
                asset for asset in state.corpus.raw_assets if _resource_page(asset) == page
            ]
            bands = ocr_figures._partition_assets_by_caption_bands(
                ordered_captions,
                page_assets,
                max(
                    (
                        float((block.get("bbox") or [0, 0, 0, 0])[3])
                        for block in state.corpus.blocks
                        if _resource_page(block) == page
                    ),
                    default=1200.0,
                ),
                page_width=state.corpus.page_width,
            )
            band_assets = bands.get(chosen_key[1], [])
            asset_refs = [
                ResourceRef(kind="asset", page=page, block_id=asset.get("block_id"))
                for asset in band_assets
                if asset.get("block_id") is not None
            ]
            if not asset_refs:
                continue

            diagnostics = dict(chosen.diagnostics)
            diagnostics["evidence"] = list(diagnostics.get("evidence") or []) + [
                "sidecar_band_ownership"
            ]
            band_proposal = ClaimProposal(
                pass_name=chosen.pass_name,
                figure_no=chosen.figure_no,
                claim_type=chosen.claim_type,
                legends=chosen.legends,
                assets=asset_refs,
                groups=chosen.groups,
                confidence=chosen.confidence,
                evidence_rank=chosen.evidence_rank,
                reason="same_page_sidecar_band",
                diagnostics=diagnostics,
            )
            proposals = [
                proposal
                for proposal in proposals
                if not (
                    proposal.legends[0].page == page
                    and str(proposal.legends[0].block_id) in caption_ids
                )
            ]
            proposals.append(band_proposal)

        shared_groups = {}
        for proposal in proposals:
            if proposal.claim_type != "match" or len(proposal.legends) != 1:
                continue
            group_refs = [group for group in proposal.groups if group.group_id]
            if len(group_refs) == 1:
                key = (proposal.legends[0].page, group_refs[0].group_id)
                shared_groups.setdefault(key, []).append(proposal)

        replaced = set()
        band_proposals = []
        for (page, group_id), group_proposals in shared_groups.items():
            by_caption = {}
            for proposal in group_proposals:
                if proposal.figure_no is None:
                    continue
                caption_id = str(proposal.legends[0].block_id)
                current = by_caption.get(caption_id)
                if current is None or proposal.confidence > current.confidence:
                    by_caption[caption_id] = proposal
            if len(by_caption) < 2:
                continue

            asset_sets = {
                frozenset(str(asset.block_id) for asset in proposal.assets)
                for proposal in by_caption.values()
            }
            if len(asset_sets) != 1 or not next(iter(asset_sets)):
                continue
            group_asset_ids = next(iter(asset_sets))
            captions = {
                str(caption.get("block_id")): caption
                for caption in state.candidate_index.deduped_legends
                if _resource_page(caption) == page
                and str(caption.get("block_id")) in by_caption
            }
            if len(captions) != len(by_caption):
                continue
            page_assets = [
                asset for asset in state.corpus.raw_assets if _resource_page(asset) == page
            ]
            page_height = max(
                (
                    float((block.get("bbox") or [0, 0, 0, 0])[3])
                    for block in state.corpus.blocks
                    if _resource_page(block) == page
                ),
                default=1200.0,
            )
            bands = ocr_figures._partition_assets_by_caption_bands(
                sorted(captions.values(), key=lambda caption: (caption.get("bbox") or [0, 0, 0, 0])[1]),
                page_assets,
                page_height,
                page_width=state.corpus.page_width,
            )
            partitioned = {
                caption_id: [
                    str(asset.get("block_id"))
                    for asset in bands.get(caption_id, [])
                    if asset.get("block_id") is not None
                ]
                for caption_id in by_caption
            }
            assigned_ids = [
                asset_id for asset_ids in partitioned.values() for asset_id in asset_ids
            ]
            if (
                any(not asset_ids or not set(asset_ids).issubset(group_asset_ids) for asset_ids in partitioned.values())
                or set(assigned_ids) != group_asset_ids
                or len(assigned_ids) != len(set(assigned_ids))
            ):
                continue

            for caption_id, proposal in by_caption.items():
                diagnostics = dict(proposal.diagnostics)
                diagnostics["evidence"] = list(diagnostics.get("evidence") or []) + [
                    "shared_group_caption_band_ownership"
                ]
                band_proposals.append(
                    ClaimProposal(
                        pass_name=proposal.pass_name,
                        figure_no=proposal.figure_no,
                        claim_type=proposal.claim_type,
                        legends=proposal.legends,
                        assets=[
                            ResourceRef(kind="asset", page=page, block_id=asset_id)
                            for asset_id in partitioned[caption_id]
                        ],
                        groups=proposal.groups,
                        confidence=proposal.confidence,
                        evidence_rank=proposal.evidence_rank,
                        reason="same_page_shared_group_band",
                        diagnostics=diagnostics,
                    )
                )
            replaced.update(id(proposal) for proposal in group_proposals)

        if replaced:
            proposals = [
                proposal for proposal in proposals if id(proposal) not in replaced
            ] + band_proposals

        report.proposals.extend(proposals)
        for proposal in sorted(proposals, key=lambda p: (p.evidence_rank, -p.confidence, -(p.figure_no or -1))):
            conflict = state.ledger.try_claim_assets(
                proposal.assets, owner=proposal.legends[0], reason=proposal.reason
            )
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue
            state.accept_match(proposal, self._materialize_match(state, proposal))
            report.accepted.append(proposal)

        return report


class CrossPageReservationPass:
    name = "cross_page_reservation"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        unmatched_legends = [
            legend
            for legend in state.candidate_index.deduped_legends
            if not any(
                str(match.get("legend_block_id", "")) == str(legend.get("block_id", ""))
                and (
                    match.get("legend_page")
                    if match.get("legend_page") is not None
                    else match.get("page")
                ) == _resource_page(legend)
                for match in state.matches
            )
        ]

        def group_evidence(group: dict) -> dict:
            group_page = _resource_page(group)
            assets = [
                {
                    "page": _resource_page(asset) or group_page,
                    "block_id": str(asset.get("block_id")),
                    "bbox": list(asset.get("bbox") or []),
                }
                for asset in group.get("media_blocks", [])
                if asset.get("block_id") is not None
            ]
            return {
                "group_id": group.get("group_id"),
                "page": group_page,
                "bbox": list(group.get("cluster_bbox") or []),
                "assets": assets,
            }

        def hold(legend: dict, groups: list[dict], reason: str) -> None:
            candidate_groups = [group_evidence(group) for group in groups]
            candidate_assets = [
                asset for candidate in candidate_groups for asset in candidate["assets"]
            ]
            state.hold_legend({
                "page": _resource_page(legend),
                "legend_page": _resource_page(legend),
                "legend_block_id": str(legend.get("block_id", "")),
                "text": str(legend.get("text") or ""),
                "legend_bbox": list(legend.get("bbox") or []),
                "association_status": "HOLD",
                "hold_reason": reason,
                "candidate_groups": candidate_groups,
                "candidate_assets": candidate_assets,
                "candidate_asset_ids": [
                    asset["block_id"] for asset in candidate_assets
                ],
                "evidence": ["page_gap", reason],
            })

        def group_is_unclaimed(group: dict) -> bool:
            group_page = _resource_page(group)
            asset_ids = group.get("asset_block_ids") or [
                asset.get("block_id") for asset in group.get("media_blocks", [])
            ]
            return not any(
                block_id is not None
                and state.ledger.owner_of_asset(
                    page=int(_resource_page(group) or 0), block_id=str(block_id)
                )
                is not None
                for block_id in asset_ids
            )
        for legend in unmatched_legends:
            page = _resource_page(legend)
            if page is None:
                continue
            forward_groups = [
                group
                for group in state.candidate_index.candidate_groups
                if _resource_page(group) == page + 1
                and state.ledger.can_claim_group(ResourceRef(
                    kind="group",
                    page=_resource_page(group),
                    block_id=None,
                    group_id=group.get("group_id"),
                ))
            ]
            if not forward_groups:
                continue

            if len(forward_groups) > 1:
                hold(legend, forward_groups, "competing_forward_groups")
                continue
            group = forward_groups[0]
            if not group_is_unclaimed(group):
                hold(legend, [group], "forward_group_assets_already_owned")
                continue
            group_page = _resource_page(group)
            competing_captions = [
                candidate
                for candidate in unmatched_legends
                if _resource_page(candidate) == page
                and str(candidate.get("block_id", "")) != str(legend.get("block_id", ""))
            ]
            local_captions = [
                candidate
                for candidate in unmatched_legends
                if _resource_page(candidate) == group_page
            ]
            if competing_captions or local_captions:
                hold(legend, [group], "competing_caption_candidates")
                continue

            group_ref = ResourceRef(
                kind="group", page=group_page, block_id=None, group_id=group.get("group_id")
            )
            candidate_group = group_evidence(group)
            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=None,
                claim_type="reserve",
                legends=[
                    ResourceRef(
                        kind="legend", page=page, block_id=legend.get("block_id"), figure_no=None
                    )
                ],
                assets=[],
                groups=[group_ref],
                confidence=0.6,
                evidence_rank=2,
                reason="forward_cross_page_candidate",
                diagnostics={
                    "evidence": ["page_gap", "same_page_miss"],
                    "caption_text": str(legend.get("text") or ""),
                    "legend_bbox": list(legend.get("bbox") or []),
                    "candidate_group": candidate_group,
                },
            )
            report.proposals.append(proposal)
            state.ledger.reserve_group(group_ref, reason=proposal.reason)
            state.accept_reservation(proposal)
            report.accepted.append(proposal)
        return report


class CrossPageSettlementPass:
    name = "cross_page_settlement"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        for reservation in state.reservations:
            if (
                reservation.get("status") != "RESERVED"
                or reservation.get("association_status") == "RESOLVED"
            ):
                continue

            legend = reservation["legends"][0]
            group = reservation["groups"][0]
            legend_page = int(legend["page"])
            legend_id = str(legend["block_id"])
            legend_block = next(
                (
                    item
                    for item in state.candidate_index.deduped_legends
                    if _resource_page(item) == legend_page
                    and str(item.get("block_id", "")) == legend_id
                ),
                {},
            )
            caption_text = str(legend_block.get("text") or "").strip()
            caption_bbox = legend_block.get("bbox") or []
            from . import ocr_figures

            def valid_bbox(bbox):
                try:
                    if len(bbox) < 4:
                        return False
                    x1, y1, x2, y2 = (float(value) for value in bbox[:4])
                except (TypeError, ValueError):
                    return False
                return (
                    all(math.isfinite(value) for value in (x1, y1, x2, y2))
                    and x2 > x1
                    and y2 > y1
                )

            caption_verified = bool(
                caption_text
                and ocr_figures._extract_figure_number(caption_text) is not None
                and valid_bbox(caption_bbox)
            )

            def match_caption_page(match):
                page = match.get("legend_page")
                if page is None:
                    page = match.get("page")
                try:
                    return int(page) if page is not None else None
                except (TypeError, ValueError):
                    return None

            matches = [
                match
                for match in state.matches
                if str(match.get("legend_block_id", "")) == legend_id
                and match_caption_page(match) == legend_page
            ]

            def has_resolved_assets(match):
                assets = match.get("matched_assets") or []
                declared_ids = {
                    str(block_id)
                    for block_id in match.get("asset_block_ids", [])
                    if block_id not in (None, "")
                }
                asset_ids = set()
                asset_keys = set()
                if not assets or not match.get("figure_id") or not declared_ids:
                    return False
                for asset in assets:
                    page = asset.get("page")
                    block_id = asset.get("block_id")
                    bbox = asset.get("bbox") or []
                    if page is None or block_id in (None, "") or not valid_bbox(bbox):
                        return False
                    try:
                        page = int(page)
                    except (TypeError, ValueError):
                        return False
                    if page < 1 or (page, str(block_id)) in asset_keys:
                        return False
                    asset_keys.add((page, str(block_id)))
                    asset_ids.add(str(block_id))
                return declared_ids == asset_ids

            resolved_matches = [
                match for match in matches if caption_verified and has_resolved_assets(match)
            ]
            resolved_match_ids = {id(match) for match in resolved_matches}
            invalid_matches = [match for match in matches if id(match) not in resolved_match_ids]
            if not caption_verified:
                hold_reason = "caption_not_verified"
            elif len({match.get("figure_id") for match in resolved_matches}) > 1:
                invalid_matches.extend(resolved_matches)
                resolved_matches = []
                hold_reason = "multiple_matches_for_caption"
            elif resolved_matches:
                hold_reason = ""
            else:
                hold_reason = "asset_evidence_invalid" if matches else "reservation_unresolved"

            invalid_match_ids = {id(match) for match in invalid_matches}
            if invalid_match_ids:
                state.matches[:] = [match for match in state.matches if id(match) not in invalid_match_ids]

            if resolved_matches:
                for match in resolved_matches:
                    match["association_status"] = "RESOLVED"
                    match["delivery_status"] = "PENDING"
                reservation.update(
                    {
                        "status": "RESERVED",
                        "association_status": "RESOLVED",
                        "delivery_allowed": True,
                        "delivery_status": "PENDING",
                        "resolved_by": list(dict.fromkeys(
                            str(match.get("settlement_type") or "") for match in resolved_matches
                        )),
                        "resolved_figure_id": resolved_matches[0].get("figure_id"),
                        "resolved_caption": {
                            "page": legend_page,
                            "block_id": legend_id,
                            "text": caption_text,
                            "bbox": [float(value) for value in caption_bbox[:4]],
                        },
                        "resolved_assets": [
                            {
                                "page": int(asset["page"]),
                                "block_id": str(asset["block_id"]),
                                "bbox": [float(value) for value in asset["bbox"][:4]],
                            }
                            for match in resolved_matches
                            for asset in match.get("matched_assets", [])
                        ],
                    }
                )
            else:
                diagnostics = reservation.get("diagnostics") or {}
                candidate_group = diagnostics.get("candidate_group") or {
                    "group_id": group.get("group_id"),
                    "page": group.get("page"),
                    "bbox": None,
                    "assets": [],
                }
                reservation.update(
                    {
                        "status": "HOLD",
                        "association_status": "HOLD",
                        "delivery_allowed": False,
                        "delivery_status": "NOT_DELIVERABLE",
                        "hold_reason": hold_reason,
                    }
                )
                state.hold_legend(
                    {
                        "association_status": "HOLD",
                        "page": legend_page,
                        "legend_page": legend_page,
                        "legend_block_id": legend_id,
                        "text": str(legend_block.get("text") or diagnostics.get("caption_text") or ""),
                        "legend_bbox": list(legend_block.get("bbox") or diagnostics.get("legend_bbox") or []),
                        "hold_reason": hold_reason,
                        "candidate_groups": [candidate_group],
                        "candidate_asset_ids": [
                            asset.get("block_id")
                            for asset in candidate_group.get("assets", [])
                            if asset.get("block_id") is not None
                        ],
                        "evidence": list(diagnostics.get("evidence") or []),
                    }
                )

            group_ref = ResourceRef(
                kind="group",
                page=int(group["page"]),
                block_id=None,
                group_id=group.get("group_id"),
            )
            state.ledger.release_group_reservation(
                group_ref,
                reason=f"cross_page_settlement_{reservation.get('association_status', reservation['status']).lower()}",
            )
            state.diagnostics.append(
                {
                    "event": "reservation_settled",
                    "status": reservation.get("association_status", reservation["status"]),
                    "reservation_status": reservation["status"],
                    "legend_page": legend_page,
                    "legend_block_id": legend_id,
                    "group_page": group.get("page"),
                    "group_id": group.get("group_id"),
                }
            )
        return report


class ContinuationCaptionPass:
    name = "continuation_caption"

    def _collect_proposals(self, state):
        from . import ocr_figures

        proposals = []
        for legend in state.candidate_index.deduped_legends:
            if not legend.get("_figure_continuation"):
                continue
            page = _resource_page(legend)
            if page is None:
                continue
            base_number = legend.get("_continuation_base_number")
            if base_number is None:
                continue

            # Compute base marker from cleaned text (without continuation marker)
            cleaned = ocr_figures._FIGURE_CONTINUATION_PATTERN.sub("", str(legend.get("text", ""))).strip()
            marker = ocr_figures._extract_figure_marker(cleaned)

            # --- Same-page: match by geometry ---
            page_groups = [g for g in state.candidate_index.candidate_groups if _resource_page(g) == page]
            for group in page_groups:
                score = ocr_figures._score_legend_to_group(
                    legend,
                    group,
                    caption_score=ocr_figures.score_figure_caption(
                        legend, nearby_media=True, caption_style_match=False, body_prose_likelihood=False,
                    ),
                    page_width=state.corpus.page_width,
                )
                if score.get("decision") != "matched":
                    continue
                proposals.append(
                    ClaimProposal(
                        pass_name=self.name,
                        figure_no=base_number,
                        claim_type="match",
                        legends=[
                            ResourceRef(
                                kind="legend", page=page, block_id=legend.get("block_id"), figure_no=base_number
                            )
                        ],
                        assets=[
                            ResourceRef(kind="asset", page=page, block_id=bid)
                            for bid in group.get("asset_block_ids", [])
                        ],
                        groups=[
                            ResourceRef(
                                kind="group", page=page, block_id=None, group_id=group.get("group_id")
                            )
                        ],
                        confidence=float(score.get("score", 0.85)),
                        evidence_rank=0,
                        reason="continuation_same_page",
                        diagnostics={
                            "evidence": list(score.get("evidence", [])),
                            "legend_block_id": str(legend.get("block_id", "")),
                            "base_number": base_number,
                            "namespace": marker["namespace"],
                            "alpha_prefix": marker["alpha_prefix"],
                        },
                    )
                )

            # --- Cross-page: page +/- 1, no strong interruption ---
            if not proposals:
                for offset in (-1, 1):
                    np = page + offset
                    if np < 0:
                        continue
                    if ocr_figures._has_strong_interruption(np, state.corpus.blocks):
                        continue
                    np_groups = [
                        g for g in state.candidate_index.candidate_groups if _resource_page(g) == np
                    ]
                    for group in np_groups:
                        proposals.append(
                            ClaimProposal(
                                pass_name=self.name,
                                figure_no=base_number,
                                claim_type="match",
                                legends=[
                                    ResourceRef(
                                        kind="legend", page=page, block_id=legend.get("block_id"), figure_no=base_number
                                    )
                                ],
                                assets=[
                                    ResourceRef(kind="asset", page=np, block_id=bid)
                                    for bid in group.get("asset_block_ids", [])
                                ],
                                groups=[
                                    ResourceRef(
                                        kind="group", page=np, block_id=None, group_id=group.get("group_id")
                                    )
                                ],
                                confidence=0.7,
                                evidence_rank=0,
                                reason="continuation_cross_page",
                                diagnostics={
                                    "evidence": [],
                                    "legend_block_id": str(legend.get("block_id", "")),
                                    "base_number": base_number,
                                    "namespace": marker["namespace"],
                                    "alpha_prefix": marker["alpha_prefix"],
                                    "group_page": np,
                                },
                            )
                        )
        return proposals

    def _materialize_match(self, state, proposal):
        from . import ocr_figures

        legend = proposal.legends[0]
        page = legend.page
        legend_text = ""
        for leg in state.candidate_index.deduped_legends:
            if str(leg.get("block_id", "")) == str(legend.block_id) and _resource_page(leg) == page:
                legend_text = str(leg.get("text", ""))
                break
        if not legend_text:
            for leg in state.candidate_index.deduped_legends:
                if str(leg.get("block_id", "")) == str(legend.block_id):
                    legend_text = str(leg.get("text", ""))
                    break
        marker = ocr_figures._extract_figure_marker(legend_text)
        namespace = marker["namespace"]
        base_number = proposal.figure_no
        # Determine what the base figure matches to
        base_figure_id = ocr_figures._format_figure_id(
            namespace,
            base_number,
            alpha_prefix=marker["alpha_prefix"],
        )
        asset_ids = {str(r.block_id) for r in proposal.assets}
        asset_pages = {r.page for r in proposal.assets}
        matched_assets = [
            ocr_figures._project_asset_record(a)
            for a in state.corpus.raw_assets
            if str(a.get("block_id", "")) in asset_ids
            and (_resource_page(a) in asset_pages or not asset_pages)
        ]
        return {
            "figure_id": base_figure_id,
            "figure_namespace": namespace,
            "figure_number": base_number,
            "legend_block_id": legend.block_id,
            "page": page,
            "text": legend_text,
            "matched_assets": matched_assets,
            "asset_block_ids": sorted(asset_ids),
            "settlement_type": proposal.reason,
            "confidence": proposal.confidence,
            "match_score": {
                "score": proposal.confidence,
                "decision": "matched",
                "evidence": proposal.diagnostics.get("evidence", []),
            },
            "flags": ["continuation"],
            "bridge_block_ids": [],
            "continued_from": base_figure_id,
            "is_continuation": True,
        }

    def run(self, state):
        report = PassReport(pass_name=self.name)
        proposals = self._collect_proposals(state)
        report.proposals.extend(proposals)

        for proposal in sorted(proposals, key=lambda p: (p.evidence_rank, -p.confidence, -(p.figure_no or -1))):
            conflict = state.ledger.try_claim_assets(proposal.assets, owner=proposal.legends[0], reason=proposal.reason)
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue
            state.accept_match(proposal, self._materialize_match(state, proposal))
            report.accepted.append(proposal)

        return report
