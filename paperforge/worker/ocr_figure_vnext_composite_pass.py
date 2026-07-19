from __future__ import annotations

from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


def _is_legend_matched(legend_block_id: str, matches: list[dict]) -> bool:
    return any(m.get("legend_block_id") == legend_block_id for m in matches)


def _numbered_legends_on_page(page: int, legends: list[dict], extract_fn) -> list[dict]:
    """Return legends on *page* that have a numeric figure number."""
    result = []
    for leg in legends:
        leg_page = _resource_page(leg)
        if leg_page != page:
            continue
        num = extract_fn(str(leg.get("text", "")))
        if num is not None:
            result.append(leg)
    return result


class CompositeParentPass:
    """For each unmatched numbered legend, if a composite_parent_candidate
    exists on the same page with sufficient confidence (>=0.60) and >=2 child
    groups, claim all child group assets as a single multi-panel figure.
    """

    name = "composite_parent"

    def run(self, state):
        from . import ocr_figures

        report = PassReport(pass_name=self.name)
        consumed_parent_keys: set[str] = set()  # track by group_id

        for legend in state.candidate_index.deduped_legends:
            legend_page = _resource_page(legend)
            if legend_page is None:
                continue

            legend_text = str(legend.get("text", ""))
            figure_no = ocr_figures._extract_figure_number(legend_text)
            if figure_no is None:
                continue  # only numbered legends

            legend_block_id = str(legend.get("block_id", ""))
            if _is_legend_matched(legend_block_id, state.matches):
                continue

            # --- find composite parent candidates on same page ---
            page_parents = [
                cp
                for cp in state.candidate_index.composite_parent_candidates
                if cp.get("page") == legend_page
                and cp.get("group_id", "") not in consumed_parent_keys
            ]
            if not page_parents:
                continue

            page_parents.sort(key=lambda cp: cp.get("parent_confidence", 0), reverse=True)
            best_parent = page_parents[0]
            parent_conf = float(best_parent.get("parent_confidence", 0.0))

            if parent_conf < 0.60:
                continue

            # --- competing caption veto ---
            same_page_numbered = _numbered_legends_on_page(
                legend_page, state.candidate_index.deduped_legends,
                ocr_figures._extract_figure_number,
            )
            has_competing = len(same_page_numbered) > 1

            # --- resolve child groups ---
            child_group_ids = set(best_parent.get("child_group_ids", []))
            all_child_groups = [
                g for g in state.candidate_index.candidate_groups
                if str(g.get("group_id", "")) in child_group_ids
            ]

            # Band-scoping: when competing captions exist, only keep child
            # groups whose best_caption_band_id matches this legend.
            if has_competing:
                matching_band_groups = [
                    g for g in all_child_groups
                    if str((g.get("assist") or {}).get("best_caption_band_id") or "")
                       == legend_block_id
                ]
                if len(matching_band_groups) >= 2:
                    effective_groups = matching_band_groups
                else:
                    continue  # competing captions, not scoped -> skip
            else:
                effective_groups = all_child_groups

            # --- effective child group count check ---
            is_dense = best_parent.get("parent_subtype") == "dense_composite"
            fragment_count = int(best_parent.get("fragment_count", 0) or 0)
            dense_single_group_ok = is_dense and len(effective_groups) == 1 and fragment_count >= 4

            if len(effective_groups) < 2 and not dense_single_group_ok:
                continue

            # --- collect asset block ids (ordered, deduplicated) ---
            asset_block_ids = list(dict.fromkeys(
                bid
                for group in effective_groups
                for bid in group.get("asset_block_ids", [])
            ))
            if not asset_block_ids:
                continue

            # --- build proposal ---
            asset_refs = [
                ResourceRef(kind="asset", page=legend_page, block_id=bid)
                for bid in asset_block_ids
            ]
            group_refs = [
                ResourceRef(
                    kind="group", page=legend_page, block_id=None,
                    group_id=str(g.get("group_id", "")),
                )
                for g in effective_groups
            ]
            legend_ref = ResourceRef(
                kind="legend", page=legend_page,
                block_id=legend_block_id, figure_no=figure_no,
            )

            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=figure_no,
                claim_type="composite_parent",
                legends=[legend_ref],
                assets=asset_refs,
                groups=group_refs,
                confidence=parent_conf,
                evidence_rank=1,
                reason="composite_parent",
                diagnostics={
                    "evidence": ["composite_parent"],
                    "legend_block_id": legend_block_id,
                },
            )
            report.proposals.append(proposal)

            # --- claim assets ---
            conflict = state.ledger.try_claim_assets(
                proposal.assets, owner=legend_ref, reason=proposal.reason,
            )
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue

            # --- materialise match record and accept ---
            match_record = self._build_match_record(state, proposal, figure_no)
            state.accept_match(proposal, match_record)
            report.accepted.append(proposal)
            consumed_parent_keys.add(best_parent.get("group_id", ""))

        return report

    @staticmethod
    def _build_match_record(state, proposal: ClaimProposal, figure_no: int) -> dict:
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
            if str(b.get("block_id", "")) == legend.block_id
        )
        namespace = ocr_figures._extract_figure_namespace(legend_text)
        figure_id = ocr_figures._format_figure_id(namespace, figure_no)

        return {
            "figure_id": figure_id,
            "figure_namespace": namespace,
            "figure_number": figure_no,
            "legend_block_id": legend.block_id,
            "page": page,
            "text": legend_text,
            "matched_assets": matched_assets,
            "asset_block_ids": sorted(asset_ids),
            "settlement_type": "composite_parent",
            "confidence": proposal.confidence,
            "match_score": {
                "score": proposal.confidence,
                "decision": "matched",
                "evidence": ["composite_parent"],
            },
            "flags": ["composite_parent_match"],
            "bridge_block_ids": [],
        }
