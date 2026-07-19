from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    """Extract page number from a block dict (page or page_num)."""
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class ClassicSequentialPass:
    """Last-resort matcher: match unmatched numbered captions to remaining
    ungrouped assets in reading order.

    Ported from legacy ocr_figures.py:4720-4830.
    """

    name = "classic_sequential"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)

        # ---- 1. Compute unmatched numbered legends ----
        matched_legend_ids: set[str] = set()
        for m in state.matches:
            lid = m.get("legend_block_id")
            if lid:
                matched_legend_ids.add(str(lid))

        unmatched_legends = [
            leg for leg in state.candidate_index.deduped_legends
            if str(leg.get("block_id", "")) not in matched_legend_ids
            and ocr_figures._extract_figure_number(
                str(leg.get("text", "") or "")
            ) is not None
        ]
        if not unmatched_legends:
            return report

        # ---- 2. Compute ungrouped unmatched assets ----
        grouped_ids = ocr_figures._grouped_asset_page_ids(
            state.candidate_index.candidate_groups
        )
        ungrouped_unmatched: list[dict] = []
        for ast in state.corpus.raw_assets:
            page = _resource_page(ast)
            if page is None:
                continue
            bid = str(ast.get("block_id", ""))
            if state.ledger.owner_of_asset(page=page, block_id=bid) is not None:
                continue
            if (page, bid) in grouped_ids:
                continue
            ungrouped_unmatched.append(ast)

        if not ungrouped_unmatched:
            return report

        # ---- 3. Sort by reading order (page, then y-position) ----
        sorted_caps = sorted(
            unmatched_legends,
            key=lambda b: (b.get("page", 0) or 0, (b.get("bbox") or [0, 0, 0, 0])[1]),
        )
        sorted_asts = sorted(
            ungrouped_unmatched,
            key=lambda b: (b.get("page", 0) or 0, (b.get("bbox") or [0, 0, 0, 0])[1]),
        )

        # ---- 4. Sequential matching ----
        ai = 0
        for cap in sorted_caps:
            cap_text = str(cap.get("text", "") or "")
            fn = ocr_figures._extract_figure_number(cap_text)
            if fn is None:
                continue
            cap_ns = ocr_figures._extract_figure_namespace(cap_text)

            cp = cap.get("page", 0) or 0

            previous_page_asset: dict | None = None
            future_page_asset: dict | None = None
            scan_index = ai

            while scan_index < len(sorted_asts):
                asset = sorted_asts[scan_index]
                ap = asset.get("page", 0) or 0
                asset_bid = str(asset.get("block_id", ""))
                if asset_bid and state.ledger.owner_of_asset(page=ap, block_id=asset_bid) is not None:
                    scan_index += 1
                    continue
                if ap == cp - 1:
                    previous_page_asset = asset
                    scan_index += 1
                    continue
                if ap >= cp:
                    if ap > cp:
                        future_page_asset = asset
                    break
                scan_index += 1

            chosen_asset: dict | None = None
            if (
                chosen_asset is None
                and previous_page_asset is not None
                and ocr_figures._allow_previous_page_sequential_match(cap, previous_page_asset)
            ):
                chosen_asset = previous_page_asset
            if chosen_asset is None and future_page_asset is not None:
                fap = future_page_asset.get("page", 0) or 0
                if fap >= cp:
                    chosen_asset = future_page_asset

            if chosen_asset is None:
                continue

            asset_bid = str(chosen_asset.get("block_id", ""))
            asset_page = chosen_asset.get("page", 0)

            # Double-check the chosen asset is still unowned (another caption
            # in this pass may have claimed it since the scan).
            if asset_bid and state.ledger.owner_of_asset(
                page=asset_page, block_id=asset_bid
            ) is not None:
                continue

            # Advance ai past the chosen asset (reading-order progression).
            while ai < len(sorted_asts):
                ai_asset = sorted_asts[ai]
                ai += 1
                if (
                    str(ai_asset.get("block_id", "")) == asset_bid
                    and ai_asset.get("page", 0) == asset_page
                ):
                    break

            fig_id = ocr_figures._format_figure_id(cap_ns, fn)

            legend_ref = ResourceRef(
                kind="legend", page=cp, block_id=str(cap.get("block_id", ""))
            )
            asset_ref = ResourceRef(
                kind="asset", page=asset_page, block_id=asset_bid
            )

            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=fn,
                claim_type="match",
                legends=[legend_ref],
                assets=[asset_ref],
                groups=[],
                confidence=0.35,
                evidence_rank=6,
                reason="sequential_match",
                diagnostics={"evidence": ["sequential_fallback"]},
            )

            conflict = state.ledger.try_claim_assets(
                [asset_ref], owner=legend_ref, reason="sequential_match"
            )
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue

            match_record = {
                "figure_id": fig_id,
                "figure_namespace": cap_ns,
                "figure_number": fn,
                "legend_block_id": str(cap.get("block_id", "")),
                "page": asset_page,
                "text": cap_text,
                "matched_assets": [ocr_figures._project_asset_record(chosen_asset)],
                "group_type": "",
                "group_evidence": [],
                "confidence": 0.35,
                "match_score": {
                    "score": 0.35,
                    "decision": "matched",
                    "evidence": ["sequential_fallback"],
                },
                "flags": ["sequential_match"],
                "settlement_type": "sequential",
            }

            state.accept_match(proposal, match_record)
            report.accepted.append(proposal)

        return report


class UnresolvedClusterConsolidation:
    """After classic sequential, build unresolved clusters from remaining
    unmatched assets on pages with rejected legends.

    Multi-panel figures with axis labels or informal captions that were
    rejected as formal legends get consolidated into cluster records so
    downstream consumers can treat them as figure-like entities.

    Ported from legacy ocr_figures.py:4831-4862.
    """

    name = "unresolved_cluster"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)

        # ---- 1. Compute unmatched assets (not owned by ledger) ----
        unmatched_assets: list[dict] = []
        for ast in state.corpus.raw_assets:
            page = _resource_page(ast)
            if page is None:
                continue
            bid = str(ast.get("block_id", ""))
            if state.ledger.owner_of_asset(page=page, block_id=bid) is not None:
                continue
            unmatched_assets.append(ast)

        if not unmatched_assets:
            return report

        # ---- 2. Determine pages with rejected legends ----
        rejected_legends = state.candidate_index.rejected_legends
        if not rejected_legends:
            return report

        rejected_pages: set[int] = {
            int(leg.get("page")) for leg in rejected_legends
            if leg.get("page") is not None
        }

        # ---- 3. Cluster unmatched assets and create unresolved records ----
        page_width = state.corpus.page_width
        for cluster in ocr_figures._media_clusters(unmatched_assets, page_width):
            if len(cluster) < 2:
                continue
            cluster_page = cluster[0].get("page", 0)
            if cluster_page not in rejected_pages:
                continue

            cluster_id = f"unresolved_cluster_{len(state.unresolved) + 1:03d}"
            cluster_ids: list[str] = [str(b.get("block_id", "")) for b in cluster]
            cluster_bboxes = [b.get("bbox", [0, 0, 0, 0]) for b in cluster]

            cluster_dict = {
                "cluster_id": cluster_id,
                "media_block_ids": cluster_ids,
                "cluster_bbox": ocr_figures._cluster_bbox(cluster_bboxes),
                "page": cluster_page,
            }
            state.unresolved.append(cluster_dict)

            # Mark cluster assets as claimed in the ledger so subsequent
            # passes skip them.
            asset_refs = [
                ResourceRef(kind="asset", page=cluster_page, block_id=str(bid))
                for bid in cluster_ids
                if bid
            ]
            owner_ref = ResourceRef(
                kind="group",
                page=cluster_page,
                block_id=None,
                group_id=cluster_id,
            )
            conflict = state.ledger.try_claim_assets(
                asset_refs, owner=owner_ref, reason="unresolved_cluster"
            )
            if conflict is not None:
                report.conflicts.append(conflict)
                continue

            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=None,
                claim_type="unresolved_cluster",
                legends=[],
                assets=asset_refs,
                groups=[owner_ref],
                confidence=0.2,
                evidence_rank=7,
                reason="unresolved_cluster_consolidation",
                diagnostics={"rejected_page": cluster_page},
            )
            report.proposals.append(proposal)
            report.accepted.append(proposal)

        return report
