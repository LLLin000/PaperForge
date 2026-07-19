"""LocatorBridgePass — connects full legend on previous page to visual group
via a locator caption (e.g. "Fig. 5 (See legend on previous page.)").

The pass bridges three components:
1. Full legend on the previous page (unmatched, >=60 chars, same figure number)
2. Visual group on the locator's page (unowned assets above the locator)
3. The locator caption itself

Run AFTER PrimarySamePagePass and cross-page passes but BEFORE generic fallback.
"""

from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class LocatorBridgePass:
    """Fallback pass that bridges a full legend on page N to a visual group
    on page N+1 via a short locator caption.
    """

    name = "locator_bridge"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)

        locators = state.candidate_index.locator_candidates
        if not locators:
            return report

        # --- 1. Build unmatched-by-number lookup ---
        # (namespace, figure_no) -> list[block]
        _unmatched_by_number: dict[tuple[str, int], list[dict]] = {}

        # Collect block_ids already claimed as legends by prior matches
        matched_legend_ids: set[str] = set()
        for m in state.matches:
            lid = m.get("legend_block_id")
            if lid:
                matched_legend_ids.add(str(lid))

        # Scan deduped_legends (formal legends)
        for leg in state.candidate_index.deduped_legends:
            leg_text = str(leg.get("text", "") or "")
            fn = ocr_figures._extract_figure_number(leg_text)
            if fn is None:
                continue
            bid = str(leg.get("block_id", ""))
            if bid in matched_legend_ids:
                continue
            ns = ocr_figures._extract_figure_namespace(leg_text)
            _unmatched_by_number.setdefault((ns, fn), []).append(leg)

        # Scan rejected_legends (may hold full legends misclassified as body_paragraph)
        for leg in state.candidate_index.rejected_legends:
            leg_text = str(leg.get("text", "") or "")
            fn = ocr_figures._extract_figure_number(leg_text)
            if fn is None:
                continue
            bid = str(leg.get("block_id", ""))
            if bid in matched_legend_ids:
                continue
            ns = ocr_figures._extract_figure_namespace(leg_text)
            key = (ns, fn)
            if key in _unmatched_by_number:
                continue
            style = str(leg.get("style_family") or "")
            zone = str(leg.get("zone") or "")
            if style == "legend_like" and zone in ("display_zone", ""):
                _unmatched_by_number.setdefault(key, []).append(leg)

        # --- 2. Process each locator ---
        for locator in locators:
            locator_text = str(locator.get("text", "") or "")
            fn = ocr_figures._extract_figure_number(locator_text)
            if fn is None:
                continue
            ns = ocr_figures._extract_figure_namespace(locator_text)
            locator_page = int(locator.get("page", 0) or 0)
            if locator_page <= 1:
                continue
            prev_page = locator_page - 1

            # --- 2a. Find full legend on previous page ---
            full_legends = _unmatched_by_number.get((ns, fn), [])
            full_legend = None
            for leg in full_legends:
                lp = int(leg.get("page", 0) or 0)
                if lp == prev_page:
                    leg_text = str(leg.get("text", "") or "")
                    if len(leg_text) >= 60 and not ocr_figures._is_previous_page_legend_locator(leg):
                        full_legend = leg
                        break

            if full_legend is None:
                continue

            # --- 2b. Find visual group on locator's page ---
            locator_bbox = locator.get("bbox") or [0, 0, 0, 0]
            locator_top = locator_bbox[1] if len(locator_bbox) >= 4 else 0

            best_group_assets: list[dict] = []

            # Priority: candidate_groups (distance_cluster, composite_parent, etc.)
            scored_groups: list[tuple[tuple[int, int, float], dict, list[str]]] = []
            for g in state.candidate_index.candidate_groups:
                gp = int(g.get("page", 0) or 0)
                if gp != locator_page:
                    continue
                g_bbox = g.get("cluster_bbox") or [0, 0, 0, 0]
                if len(g_bbox) < 4 or g_bbox[3] > locator_top:
                    continue
                g_asset_ids = g.get("asset_block_ids", [])
                g_unowned = [
                    bid
                    for bid in g_asset_ids
                    if state.ledger.owner_of(
                        ResourceRef(kind="asset", page=locator_page, block_id=str(bid))
                    )
                    is None
                ]
                if not g_unowned:
                    continue
                g_type = g.get("group_type", "")
                g_dist = abs(g_bbox[3] - locator_top)
                score = (
                    0 if g_type == "composite_parent" else
                    1 if g_type == "distance_cluster" else
                    2,
                    -len(g_unowned),
                    g_dist,
                )
                scored_groups.append((score, g, g_unowned))

            if scored_groups:
                scored_groups.sort(key=lambda x: x[0])
                _best = scored_groups[0]
                g_unowned = _best[2]
                best_group_assets = [
                    a
                    for a in state.corpus.raw_assets
                    if int(a.get("page", 0) or 0) == locator_page
                    and str(a.get("block_id", "")) in g_unowned
                ]

            # Fallback: tight asset cluster above the locator
            if not best_group_assets:
                page_assets = [
                    a
                    for a in state.corpus.raw_assets
                    if int(a.get("page", 0) or 0) == locator_page
                ]
                above = [
                    a
                    for a in page_assets
                    if (a.get("bbox") or [0, 0, 0, 0])[3] <= locator_top
                    and state.ledger.owner_of(
                        ResourceRef(
                            kind="asset",
                            page=locator_page,
                            block_id=str(a.get("block_id", "")),
                        )
                    )
                    is None
                ]
                if above and ocr_figures._is_tight_asset_cluster(above, locator_top):
                    best_group_assets = above

            if not best_group_assets:
                continue

            # --- 2c. Build match record ---
            figure_no = fn
            figure_id = ocr_figures._format_figure_id(ns, figure_no)

            consumed = [ocr_figures._project_asset_record(a) for a in best_group_assets]
            asset_bboxes = [
                a.get("bbox") or a.get("block_bbox") or [0, 0, 0, 0]
                for a in best_group_assets
            ]
            valid_bboxes = [
                b
                for b in asset_bboxes
                if len(b) >= 4 and b[2] > b[0] and b[3] > b[1]
            ]
            cluster_bbox = (
                ocr_figures._cluster_bbox(valid_bboxes) if valid_bboxes else [0, 0, 0, 0]
            )

            legend_ref = ResourceRef(
                kind="legend",
                page=prev_page,
                block_id=str(full_legend.get("block_id", "")),
                figure_no=figure_no,
            )
            asset_refs = [
                ResourceRef(
                    kind="asset",
                    page=locator_page,
                    block_id=str(a.get("block_id", "")),
                )
                for a in best_group_assets
            ]

            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=figure_no,
                claim_type="match",
                legends=[legend_ref],
                assets=asset_refs,
                groups=[],
                confidence=0.5,
                evidence_rank=3,
                reason="previous_page_legend_locator",
                diagnostics={
                    "locator_block_id": str(locator.get("block_id", "")),
                    "bridge_block_ids": [str(locator.get("block_id", ""))],
                },
            )

            match_record = {
                "figure_id": figure_id,
                "figure_namespace": ns,
                "figure_number": figure_no,
                "legend_block_id": str(full_legend.get("block_id", "")),
                "legend_page": prev_page,
                "text": str(full_legend.get("text", "")),
                "matched_assets": consumed,
                "asset_block_ids": [c["block_id"] for c in consumed],
                "cluster_bbox": cluster_bbox,
                "group_type": "previous_page_locator_bridge",
                "group_evidence": [
                    "explicit_previous_page_locator",
                    "previous_page_full_legend",
                    "same_page_visual_group",
                ],
                "bridge_block_ids": [str(locator.get("block_id", ""))],
                "match_score": {
                    "score": 0.5,
                    "decision": "matched",
                    "evidence": ["previous_page_locator_bridge"],
                },
                "confidence": 0.5,
                "flags": ["previous_page_locator_match"],
                "page": locator_page,
                "locator_block_id": str(locator.get("block_id", "")),
                "locator_page": locator_page,
                "asset_pages": [locator_page],
                "settlement_type": "previous_page_legend_locator",
                "pass_name": self.name,
            }

            conflict = state.ledger.try_claim_assets(
                proposal.assets, owner=proposal.legends[0], reason=proposal.reason
            )
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue

            state.accept_match(proposal, match_record)
            report.accepted.append(proposal)
            report.proposals.append(proposal)

            # Remove used legend key so the legend isn't reused by another locator
            _unmatched_by_number.pop((ns, figure_no), None)

        return report
