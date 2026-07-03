from __future__ import annotations

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
        for legend in state.candidate_index.deduped_legends:
            page = _resource_page(legend)
            if page is None:
                continue
            if ocr_figures._is_previous_page_legend_locator(legend):
                continue
            page_groups = [g for g in state.candidate_index.candidate_groups if _resource_page(g) == page]
            for group in page_groups:
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


class CrossPageReservationPass:
    name = "cross_page_reservation"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        for legend in state.candidate_index.deduped_legends:
            page = _resource_page(legend)
            if page is None:
                continue
            # Skip legends already matched by same-page primary
            if any(str(m.get("legend_block_id", "")) == str(legend.get("block_id", "")) for m in state.matches):
                continue
            # Find forward groups (page > legend page)
            forward_groups = [
                g
                for g in state.candidate_index.candidate_groups
                if _resource_page(g) is not None and _resource_page(g) > page
            ]
            for group in forward_groups[:1]:
                group_ref = ResourceRef(
                    kind="group", page=_resource_page(group), block_id=None, group_id=group.get("group_id")
                )
                if not state.ledger.can_claim_group(group_ref):
                    continue
                proposal = ClaimProposal(
                    pass_name=self.name,
                    figure_no=None,
                    claim_type="reserve",
                    legends=[ResourceRef(kind="legend", page=page, block_id=legend.get("block_id"), figure_no=None)],
                    assets=[],
                    groups=[group_ref],
                    confidence=0.6,
                    evidence_rank=2,
                    reason="forward_cross_page_candidate",
                    diagnostics={"evidence": ["page_gap", "same_page_miss"]},
                )
                report.proposals.append(proposal)
                state.ledger.reserve_group(group_ref, reason=proposal.reason)
                state.accept_reservation(proposal)
                report.accepted.append(proposal)
                break
        return report


class CrossPageSettlementPass:
    name = "cross_page_settlement"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)
        for reservation in state.reservations:
            legend = reservation["legends"][0]
            group = reservation["groups"][0]
            state.ledger.transition_reserved_group_to_claimed(group, owner=legend, reason="cross_page_settlement")

            # Look up the actual legend block to extract namespace/number/alpha_prefix
            legend_text = ""
            for leg in state.candidate_index.deduped_legends:
                if str(leg.get("block_id", "")) == str(legend.block_id):
                    legend_text = str(leg.get("text", ""))
                    break
            marker = ocr_figures._extract_figure_marker(legend_text)
            if marker["number"] is not None and marker["namespace"] == "appendix":
                # Appendix: use schema-derived ID (no collision risk with main).
                figure_id = ocr_figures._format_figure_id(
                    marker["namespace"], marker["number"], alpha_prefix=marker["alpha_prefix"]
                )
                figure_namespace = marker["namespace"]
                figure_number = marker["number"]
            else:
                # Main/supplementary/unnumbered: keep reserved ID to avoid
                # duplication with same-page match AND keep figure_number=None
                # so figure_number filter queries exclude this synthetic match.
                figure_id = f"figure_reserved_{len(state.matches):03d}"
                figure_namespace = marker["namespace"] if marker["number"] else "figure"
                figure_number = reservation["figure_no"]
            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=reservation["figure_no"],
                claim_type="match",
                legends=[legend],
                assets=[],
                groups=[group],
                confidence=0.6,
                evidence_rank=2,
                reason="cross_page_settlement",
                diagnostics={"evidence": ["reservation_claimed"]},
            )
            state.accept_match(
                proposal,
                {
                    "figure_id": figure_id,
                    "figure_namespace": figure_namespace,
                    "figure_number": figure_number,
                    "legend_block_id": legend.block_id,
                    "page": legend.page,
                    "text": legend_text,
                    "matched_assets": [],
                    "asset_block_ids": [],
                    "settlement_type": "cross_page_reservation",
                    "confidence": 0.6,
                    "match_score": {"score": 0.6, "decision": "matched", "evidence": ["reservation_claimed"]},
                    "flags": ["cross_page_reserved"],
                    "bridge_block_ids": [],
                },
            )
            report.accepted.append(proposal)
        return report
