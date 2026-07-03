"""GroupSequentialPass — match unmatched legends to distance_cluster/single_asset groups.

Port of legacy ocr_figures.py:4589-4716 group-aware sequential fallback.
Consumes unmatched distance_cluster and single_asset groups that no same-page
legend claimed.  Matches unmatched numbered legends in same-page (scored),
next-page, then previous-page (with guard) order.
"""

from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class GroupSequentialPass:
    """Match unmatched numbered legends to distance_cluster/single_asset groups.

    Prefers same-page (scored via _score_legend_to_group, requires >= 0.5),
    then first next-page group, then previous-page with guard check.
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
        for leg in (state.candidate_index.deduped_legends or []):
            lp = _resource_page(leg)
            if lp is not None:
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

        # ----- 4. Track already-matched legend ids -----
        matched_legend_ids: set[str] = set()
        for m in state.matches:
            lid = m.get("legend_block_id")
            if lid:
                matched_legend_ids.add(str(lid))

        # ----- 5. Process each unmatched numbered legend -----
        deduped_legends = state.candidate_index.deduped_legends or []
        for legend in deduped_legends:
            lid = str(legend.get("block_id", ""))
            if lid in matched_legend_ids:
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

            best_group = None

            # (a) Same-page: score each candidate, take best with score >= 0.5
            if same_page:
                caption_score = ocr_figures.score_figure_caption(
                    legend,
                    nearby_media=True,
                    caption_style_match=False,
                    body_prose_likelihood=False,
                )
                scored = []
                for sg in same_page:
                    sg_result = ocr_figures._score_legend_to_group(
                        legend,
                        sg,
                        caption_score=caption_score,
                        page_width=page_width,
                        page_blocks=page_blocks_map.get(lg_page, []),
                        page_height=page_height_map.get(lg_page, 0.0),
                        page_numbered_legend_count=per_page_legend_count.get(lg_page, 0),
                    )
                    if sg_result.get("decision") == "matched" and sg_result.get("score", 0.0) >= 0.5:
                        scored.append((sg, sg_result.get("score", 0.0)))
                if scored:
                    scored.sort(key=lambda x: x[1], reverse=True)
                    best_group = scored[0][0]

            # (b) Next-page fallback: first group on next page
            if best_group is None and next_page:
                best_group = next_page[0]

            # (c) Previous-page with guard
            if best_group is None and prev_page:
                first_bid = (
                    str(prev_page[0]["asset_block_ids"][0])
                    if prev_page[0].get("asset_block_ids")
                    else ""
                )
                first_asset = assets_by_page_id.get(
                    (int(prev_page[0].get("page", 0) or 0), first_bid)
                )
                if first_asset and ocr_figures._allow_previous_page_sequential_match(legend, first_asset):
                    best_group = prev_page[0]

            if best_group is None:
                continue

            # ----- 6. Collect group assets -----
            group_page = int(best_group.get("page", 0) or 0)
            group_assets = []
            for bid in (best_group.get("asset_block_ids") or []):
                if bid is None:
                    continue
                asset = assets_by_page_id.get((group_page, str(bid)))
                if asset:
                    group_assets.append(asset)

            if not group_assets:
                continue

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
            matched_legend_ids.add(lid)
            report.accepted.append(proposal)

            # Remove claimed group from pool so subsequent legends don't compete
            unmatched_groups = [g for g in unmatched_groups if g is not best_group]

        return report
