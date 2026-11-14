"""GroupSequentialPass — match unmatched legends to distance_cluster/single_asset groups.

Port of legacy ocr_figures.py:4589-4716 group-aware sequential fallback.
Consumes unmatched distance_cluster and single_asset groups that no same-page
legend claimed. Same-page matches require unambiguous ownership. Forward-page
groups are retained as HOLD evidence; previous-page matches require the guard.
"""

from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None



def _center_distance(block: dict, other: dict) -> float:
    a = block.get("bbox") or block.get("block_bbox") or []
    b = other.get("bbox") or other.get("cluster_bbox") or []
    if len(a) < 4 or len(b) < 4:
        return float("inf")
    return abs((a[0] + a[2] - b[0] - b[2]) / 2) + abs((a[1] + a[3] - b[1] - b[3]) / 2)


def _group_evidence(group: dict, assets_by_page_id: dict) -> dict:
    page = _resource_page(group)
    assets = [
        {
            "page": page,
            "block_id": str(asset["block_id"]),
            "bbox": list(asset.get("bbox") or []),
        }
        for bid in (group.get("asset_block_ids") or [])
        if (asset := assets_by_page_id.get((page, str(bid)))) is not None
    ]
    return {
        "group_id": group.get("group_id"),
        "page": page,
        "bbox": list(group.get("cluster_bbox") or []),
        "assets": assets,
    }


def _record_group_hold(state, legend: dict, groups: list[dict], assets_by_page_id: dict, reason: str) -> None:
    page = _resource_page(legend)
    evidence = [_group_evidence(group, assets_by_page_id) for group in groups]
    candidate_assets = {
        (asset["page"], asset["block_id"]): asset
        for group in evidence
        for asset in group["assets"]
    }
    state.hold_legend(
        {
            "association_status": "HOLD",
            "page": page,
            "legend_page": page,
            "legend_block_id": str(legend.get("block_id", "")),
            "text": str(legend.get("text") or ""),
            "legend_bbox": list(legend.get("bbox") or []),
            "hold_reason": reason,
            "candidate_groups": evidence,
            "candidate_assets": list(candidate_assets.values()),
            "candidate_asset_ids": [asset["block_id"] for asset in candidate_assets.values()],
            "evidence": [reason],
        }
    )


class GroupSequentialPass:
    """Match unmatched numbered legends to distance_cluster/single_asset groups.

    Prefers same-page matches scored via `_score_legend_to_group` (>= 0.5).
    Ambiguous ownership and unverified forward-page groups remain on HOLD;
    previous-page matches retain their boundary guard.
    """

    name = "group_sequential"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)

        # ----- 1. Gather unmatched distance_cluster / single_asset groups -----
        candidate_groups = state.candidate_index.candidate_groups or []
        unmatched_groups = []
        for g in candidate_groups:
            gt = g.get("group_type")
            if gt not in {"distance_cluster", "single_asset"}:
                continue
            # Skip if any group asset is already owned
            has_owned = False
            for bid in (g.get("asset_block_ids") or []):
                if bid is None:
                    continue
                owner = state.ledger.owner_of_asset(
                    page=int(g.get("page", 0) or 0),
                    block_id=str(bid),
                )
                if owner is not None:
                    has_owned = True
                    break
            if has_owned:
                continue
            unmatched_groups.append(g)

        if not unmatched_groups:
            return report

        # Sort by (page, y-top of cluster_bbox) — stable ordering for determinism
        unmatched_groups.sort(
            key=lambda g: (
                int(g.get("page", 0) or 0),
                (g.get("cluster_bbox") or [0, 0, 0, 0])[1],
            )
        )

        # ----- 2. Per-page helpers (page_blocks, page_height, numbered legend count) -----
        page_width = float(getattr(state.corpus, "page_width", 1200))
        blocks = getattr(state.corpus, "blocks", []) or []

        page_blocks_map: dict[int, list[dict]] = {}
        page_height_map: dict[int, float] = {}
        for b in blocks:
            bp = _resource_page(b)
            if bp is not None:
                page_blocks_map.setdefault(bp, []).append(b)
        for pg, blks in page_blocks_map.items():
            max_bottom = max(
                (blk.get("bbox") or [0, 0, 0, 0])[3] for blk in blks
            ) if blks else 0
            page_height_map[pg] = float(max_bottom)

        # Numbered legends per page (used by _score_legend_to_group for same-page scoring)
        per_page_legend_count: dict[int, int] = {}
        per_page_caption_count: dict[int, int] = {}
        for leg in state.candidate_index.deduped_legends or []:
            lp = _resource_page(leg)
            if lp is not None:
                per_page_caption_count[lp] = per_page_caption_count.get(lp, 0) + 1
                text = str(leg.get("text", "") or "")
                if ocr_figures._extract_figure_number(text) is not None:
                    per_page_legend_count[lp] = per_page_legend_count.get(lp, 0) + 1
        # ----- 3. Filtered asset lookup (page, block_id) -> asset dict -----
        raw_assets = getattr(state.corpus, "raw_assets", []) or []
        filtered_assets = ocr_figures._filter_figure_assets(raw_assets)
        assets_by_page_id: dict[tuple[int, str], dict] = {}
        for ast in filtered_assets:
            ap = _resource_page(ast)
            if ap is not None:
                assets_by_page_id[(ap, str(ast.get("block_id", "")))] = ast


        def _unowned_group_assets(group):
            group_page = _resource_page(group)
            return [
                asset
                for bid in (group.get("asset_block_ids") or [])
                if (asset := assets_by_page_id.get((group_page, str(bid)))) is not None
                and state.ledger.owner_of_asset(page=group_page, block_id=str(bid)) is None
            ]

        def _score_same_page(legend, group):
            page = _resource_page(legend)
            return ocr_figures._score_legend_to_group(
                legend,
                group,
                caption_score=ocr_figures.score_figure_caption(
                    legend,
                    nearby_media=True,
                    caption_style_match=False,
                    body_prose_likelihood=False,
                ),
                page_width=page_width,
                page_blocks=page_blocks_map.get(page, []),
                page_height=page_height_map.get(page, 0.0),
                page_numbered_legend_count=per_page_legend_count.get(page, 0),
            )

        # ----- 4. Track already-matched legend ids (page-qualified) -----
        matched_legend_ids: set[tuple] = set()
        for m in state.matches:
            lid = m.get("legend_block_id")
            if lid:
                mp = m.get("legend_page")
                if mp is None:
                    mp = m.get("page")
                matched_legend_ids.add((mp, str(lid)))

        # ----- 5. Process each unmatched numbered legend -----
        deduped_legends = state.candidate_index.deduped_legends or []
        for legend in deduped_legends:
            lid = str(legend.get("block_id", ""))
            lg_page = _resource_page(legend)
            if (lg_page, lid) in matched_legend_ids:
                continue

            lg_page = _resource_page(legend)
            if lg_page is None:
                continue

            cap_text = str(legend.get("text", "") or "")
            fn = ocr_figures._extract_figure_number(cap_text)
            if fn is None:
                continue

            cap_ns = ocr_figures._extract_figure_namespace(cap_text)
            fig_id = ocr_figures._format_figure_id(cap_ns, fn)

            # Partition groups by page
            same_page = [g for g in unmatched_groups if g.get("page") == lg_page]
            next_page = [g for g in unmatched_groups if g.get("page") == lg_page + 1]
            prev_page = [g for g in unmatched_groups if g.get("page") == lg_page - 1]
            margin = max(page_width, page_height_map.get(lg_page, 0.0)) * 0.05

            best_group = None
            same_page_candidates = []
            same_page_competition = False

            # (a) Same-page candidates: geometry resolves close scores; weak
            # margins stay on HOLD instead of taking whichever group sorts first.
            if same_page:
                scored = []
                for sg in same_page:
                    sg_result = _score_same_page(legend, sg)
                    if sg_result.get("decision") == "matched" and sg_result.get("score", 0.0) >= 0.5:
                        scored.append(
                            (sg, float(sg_result.get("score", 0.0)), _center_distance(legend, sg))
                        )
                same_page_candidates = [item[0] for item in scored]
                if scored:
                    page_legends = [
                        item
                        for item in deduped_legends
                        if _resource_page(item) == lg_page
                        and (lg_page, str(item.get("block_id", ""))) not in matched_legend_ids
                        and ocr_figures._extract_figure_number(str(item.get("text", "") or "")) is not None
                    ]
                    # ponytail: fixed 0.15 score / 5% page-scale margins; tune against reviewed PDFs.
                    ordered = sorted(scored, key=lambda item: (item[2], -item[1]))
                    if len(ordered) > 1:
                        by_score = sorted(scored, key=lambda item: item[1], reverse=True)
                        if by_score[0][1] - by_score[1][1] >= 0.15:
                            ordered = by_score
                        elif ordered[1][2] - ordered[0][2] < margin:
                            same_page_competition = True

                    if not same_page_competition:
                        for group, score, _ in ordered:
                            group_assets = _unowned_group_assets(group)
                            split_group = (
                                len(group_assets) >= 2
                                and len(page_legends) >= len(group_assets)
                            )
                            target = (
                                min(group_assets, key=lambda asset: _center_distance(legend, asset))
                                if split_group
                                else group
                            )
                            competing = []
                            for other in page_legends:
                                if str(other.get("block_id", "")) == lid:
                                    continue
                                other_result = _score_same_page(other, group)
                                if (
                                    other_result.get("decision") == "matched"
                                    and other_result.get("score", 0.0) >= 0.5
                                ):
                                    competing.append(
                                        (
                                            float(other_result.get("score", 0.0)),
                                            _center_distance(other, target),
                                        )
                                    )
                            if competing:
                                current_distance = _center_distance(legend, target)
                                other_distance = min(distance for _, distance in competing)
                                strongest_other_score = max(score for score, _ in competing)
                                if (
                                    current_distance + margin >= other_distance
                                    and score < strongest_other_score + 0.15
                                ):
                                    same_page_competition = True
                                    continue
                            best_group = group
                            break

            # A unique multi-asset group can still be split when full captions
            # were too weak for the primary score. Never guess between groups.
            if best_group is None and same_page and not same_page_competition:
                page_legends = [
                    item
                    for item in deduped_legends
                    if _resource_page(item) == lg_page
                    and (lg_page, str(item.get("block_id", ""))) not in matched_legend_ids
                    and ocr_figures._extract_figure_number(str(item.get("text", "") or "")) is not None
                ]
                fallback_groups = [
                    group
                    for group in same_page
                    if group.get("group_type") == "distance_cluster"
                    and len(_unowned_group_assets(group)) >= 2
                    and len(page_legends) >= len(_unowned_group_assets(group))
                ]
                if len(fallback_groups) == 1:
                    best_group = fallback_groups[0]
                elif len(fallback_groups) > 1:
                    same_page_competition = True

            if best_group is None and same_page_competition:
                _record_group_hold(
                    state,
                    legend,
                    same_page_candidates or same_page,
                    assets_by_page_id,
                    "ambiguous_same_page_group_competition",
                )
                continue

            if best_group is None and same_page:
                _record_group_hold(
                    state,
                    legend,
                    same_page,
                    assets_by_page_id,
                    "unresolved_same_page_group",
                )
                continue

            # A following-page group is candidate evidence only; ownership and crop are unresolved.
            if best_group is None and next_page:
                _record_group_hold(
                    state,
                    legend,
                    next_page,
                    assets_by_page_id,
                    "unverified_forward_group",
                )
                continue

            # Previous-page matching remains gated by the existing boundary checks.
            if best_group is None and prev_page:
                first_bid = (
                    str(prev_page[0]["asset_block_ids"][0])
                    if prev_page[0].get("asset_block_ids")
                    else ""
                )
                first_asset = assets_by_page_id.get(
                    (int(prev_page[0].get("page", 0) or 0), first_bid)
                )
                safe_unique_previous_asset = (
                    first_asset
                    and len(prev_page) == 1
                    and per_page_caption_count.get(lg_page, 0) == 1
                    and per_page_caption_count.get(lg_page - 1, 0) == 0
                    and (legend.get("bbox") or [0, 0, 0, 0])[1]
                    <= float(legend.get("page_height") or page_height_map.get(lg_page, 1600)) * 0.2
                    and (first_asset.get("bbox") or [0, 0, 0, 0])[2]
                    - (first_asset.get("bbox") or [0, 0, 0, 0])[0]
                    >= float(first_asset.get("page_width") or page_width) * 0.6
                    and (first_asset.get("bbox") or [0, 0, 0, 0])[3]
                    - (first_asset.get("bbox") or [0, 0, 0, 0])[1]
                    >= float(first_asset.get("page_height") or page_height_map.get(lg_page - 1, 1600)) * 0.5
                    and ocr_figures.score_figure_caption(
                        legend,
                        nearby_media=True,
                        caption_style_match=False,
                        body_prose_likelihood=False,
                    ).get("score", 0.0) >= 0.7
                )
                if first_asset and (
                    ocr_figures._allow_previous_page_sequential_match(legend, first_asset)
                    or safe_unique_previous_asset
                ):
                    best_group = prev_page[0]
            if best_group is None:
                continue

            # ----- 6. Collect still-unowned assets from the selected group -----
            group_page = int(best_group.get("page", 0) or 0)
            group_assets = _unowned_group_assets(best_group)
            if not group_assets:
                _record_group_hold(
                    state,
                    legend,
                    [best_group],
                    assets_by_page_id,
                    "candidate_group_already_claimed",
                )
                continue

            # If captions and assets form a one-to-one group, keep the group
            # available and give each caption only its nearest actual asset.
            _keep_group_in_pool = False
            if len(group_assets) >= 2:
                _page_legends = [
                    item
                    for item in deduped_legends
                    if (lg_page, str(item.get("block_id", ""))) not in matched_legend_ids
                    and _resource_page(item) == lg_page
                    and ocr_figures._extract_figure_number(str(item.get("text", "") or "")) is not None
                ]
                if len(_page_legends) > 1 and len(group_assets) > len(_page_legends):
                    _record_group_hold(
                        state,
                        legend,
                        [best_group],
                        assets_by_page_id,
                        "competing_captions_for_group",
                    )
                    continue
                if len(_page_legends) >= len(group_assets):
                    closest_asset = min(group_assets, key=lambda asset: _center_distance(legend, asset))
                    current_distance = _center_distance(legend, closest_asset)
                    margin = max(page_width, page_height_map.get(lg_page, 0.0)) * 0.05
                    other_distances = [
                        _center_distance(other, closest_asset)
                        for other in _page_legends
                        if str(other.get("block_id", "")) != lid
                    ]
                    if other_distances and current_distance + margin >= min(other_distances):
                        _record_group_hold(
                            state,
                            legend,
                            [best_group],
                            assets_by_page_id,
                            "ambiguous_asset_split",
                        )
                        continue
                    group_assets = [closest_asset]
                    _keep_group_in_pool = True
            # ----- 7. Build proposal and match record -----
            asset_refs = [
                ResourceRef(kind="asset", page=group_page, block_id=str(a.get("block_id", "")))
                for a in group_assets
            ]
            group_ref = ResourceRef(
                kind="group",
                page=group_page,
                block_id=None,
                group_id=str(best_group.get("group_id", "")),
            )
            legend_ref = ResourceRef(
                kind="legend",
                page=lg_page,
                block_id=str(legend.get("block_id", "")),
                figure_no=fn,
                origin="deduped",
            )

            caption_score = ocr_figures.score_figure_caption(
                legend,
                nearby_media=True,
                caption_style_match=False,
                body_prose_likelihood=False,
            )

            match_record = {
                "figure_id": fig_id,
                "figure_namespace": cap_ns,
                "legend_block_id": str(legend.get("block_id", "")),
                "page": group_page,
                "text": cap_text,
                "figure_number": fn,
                "matched_assets": [
                    ocr_figures._project_asset_record(a) for a in group_assets
                ],
                "asset_block_ids": [str(a.get("block_id", "")) for a in group_assets],
                "bridge_block_ids": [],
                "group_type": best_group.get("group_type", ""),
                "group_evidence": (best_group.get("group_evidence") or [])
                + ["group_sequential_fallback"],
                "cluster_bbox": best_group.get("cluster_bbox", [0, 0, 0, 0]),
                "confidence": 0.45,
                "match_score": {
                    "score": 0.45,
                    "decision": "matched",
                    "evidence": ["group_sequential_fallback"],
                },
                "flags": ["group_sequential_match"],
                "caption_score": caption_score,
                "legend_page": lg_page,
                "asset_pages": sorted(
                    {int(a.get("page", 0) or 0) for a in group_assets}
                ),
                "settlement_type": "group_sequential",
            }

            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=fn,
                claim_type="match",
                legends=[legend_ref],
                assets=asset_refs,
                groups=[group_ref],
                confidence=0.45,
                evidence_rank=5,
                reason=(
                    f"GroupSequentialPass matched legend {fig_id} to "
                    f"{best_group.get('group_type', 'unknown')} group"
                ),
            )

            # Try to claim assets — skip if conflict
            conflict = state.ledger.try_claim_assets(
                asset_refs,
                owner=legend_ref,
                reason=f"group_sequential_match_for_{fig_id}",
            )
            if conflict is not None:
                continue

            state.accept_match(proposal, match_record)
            matched_legend_ids.add((lg_page, lid))
            report.accepted.append(proposal)

            # Keep a claimed group visible to later captions so losers get HOLD
            # evidence instead of disappearing into an unclassified gap.
            has_unmatched_sibling = any(
                _resource_page(other) == lg_page
                and (lg_page, str(other.get("block_id", ""))) not in matched_legend_ids
                and ocr_figures._extract_figure_number(str(other.get("text", "") or "")) is not None
                for other in deduped_legends
            )
            if not _keep_group_in_pool and not has_unmatched_sibling:
                unmatched_groups = [g for g in unmatched_groups if g is not best_group]

        return report
